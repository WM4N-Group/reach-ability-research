"""Synthetic mechanism tables only: NOT physical H1 cases or model examples."""
from dataclasses import replace
import unittest
from .successor_aware_choice import Task,Candidate,Domain,ObservedBranch,digest
from .stage_b_effect_rule import EffectRule,describe_mechanism

IDS=('original','lateral_plus_0p04','lateral_minus_0p04')


def domain():
    t=Task('CPU_TABLE_NOT_EXPERIMENT','a'*64,'b'*64,'PREPARE','c'*64)
    cs=tuple(Candidate(c,t.sha256,'d'*64,'CPU:'+c,c,'original' if c=='original' else 'owner_registered_alternative') for c in IDS)
    return Domain(t,cs,'original',None,'CPU_TEST_ONLY')


def rows(d,costs=((2.,4.),(1.,5.),(3.,6.))):
    return tuple(ObservedBranch(cid,d.task.sha256,'CPU_COMMON_INIT_NOT_NATIVE_PAIR',digest({'CPU':cid}),
        'SUCCESS','SUCCESS',current,full,full+10.) for cid,(current,full) in zip(IDS,costs))


class EffectRuleTests(unittest.TestCase):
    def setUp(self):self.d=domain();self.rule=EffectRule()
    def check(self,r):return describe_mechanism(self.d,r,rule=self.rule)

    def test_material_reversal_needs_both_gaps(self):
        out=self.check(rows(self.d));self.assertTrue(out['material_strict_reversal_both_gaps_100ms'])
        self.assertEqual((out['local_advantage_s'],out['full_chain_penalty_s']),(1.,1.))
        self.assertFalse(out['physical_H1_proven_by_this_function']);self.assertFalse(out['online_oracle_or_training_allowed'])

    def test_strict_small_local_gap_not_hidden_or_called_material(self):
        out=self.check(rows(self.d,((1.05,4.),(1.,5.),(3.,6.))))
        self.assertTrue(out['raw_numerical_strict_reversal']);self.assertFalse(out['material_strict_reversal_both_gaps_100ms'])
        self.assertEqual(out['classification'],'STRICT_BUT_SUBTHRESHOLD_REVERSAL_RETAIN_RAW')

    def test_strict_small_full_gap_not_called_material(self):
        out=self.check(rows(self.d,((2.,4.),(1.,4.05),(3.,6.))))
        self.assertTrue(out['raw_numerical_strict_reversal']);self.assertFalse(out['material_strict_reversal_both_gaps_100ms'])

    def test_exact100ms_threshold_with_numerical_epsilon_not_safety_tolerance(self):
        out=self.check(rows(self.d,((1.1,4.),(1.,4.1),(3.,6.))))
        self.assertTrue(out['material_strict_reversal_both_gaps_100ms'])
        self.assertTrue(out['practical_threshold_is_not_native_success_gate'])

    def test_tie_break_is_not_strict_reversal(self):
        out=self.check(rows(self.d,((1.,5.),(1.,4.),(3.,6.))))
        self.assertEqual(out['classification'],'CURRENT_COST_TIE_BROKEN_BY_SUCCESSOR_NOT_STRICT_REVERSAL')
        self.assertFalse(out['material_strict_reversal_both_gaps_100ms'])

    def test_same_winner_negative_preserved(self):
        out=self.check(rows(self.d,((2.,5.),(1.,4.),(3.,6.))))
        self.assertFalse(out['raw_numerical_strict_reversal']);self.assertFalse(out['material_strict_reversal_both_gaps_100ms'])

    def test_failure_switch_separate_not_short_failure_benefit(self):
        r=list(rows(self.d));r[1]=replace(r[1],chain_outcome='FAILED',chain_completion_s=None,spent_sim_s=1.)
        out=self.check(tuple(r));self.assertIn('LITERAL_FAILURE_COMPATIBILITY',out['classification'])
        self.assertIsNone(out['full_chain_penalty_s']);self.assertFalse(out['material_strict_reversal_both_gaps_100ms'])
        self.assertEqual(out['raw_full_domain_replay']['branch_records'][1]['spent_sim_s'],1.)

    def test_censored_third_branch_blocks_h1_not_success_subset(self):
        r=list(rows(self.d));r[2]=replace(r[2],current_outcome='CENSORED',chain_outcome='CENSORED',current_completion_s=None,chain_completion_s=None)
        out=self.check(tuple(r));self.assertIsNone(out['material_strict_reversal_both_gaps_100ms'])
        self.assertEqual(out['classification'],'NO_CONCLUSION_INCOMPLETE_TABLE')

    def test_missing_third_branch_rejected(self):
        with self.assertRaisesRegex(ValueError,'full candidate domain'):self.check(rows(self.d)[:2])

    def test_failed_all_branches_no_invented_success(self):
        r=tuple(replace(r,current_outcome='FAILED',chain_outcome='FAILED',current_completion_s=None,chain_completion_s=None) for r in rows(self.d))
        out=self.check(r);self.assertIsNone(out['local_advantage_s']);self.assertFalse(out['material_strict_reversal_both_gaps_100ms'])

    def test_posthoc_threshold_or_lineage_override_rejected(self):
        for kw in ({'descriptive_gap_threshold_s':.01},{'numerical_epsilon_s':.1},{'Data_preregistration_release_sha256':'e'*64}):
            with self.assertRaisesRegex(ValueError,'Frozen pre-outcome'):EffectRule(**kw)

    def test_cpu_fixture_role_never_promoted_to_experiment(self):
        out=self.check(rows(self.d));self.assertTrue(out['raw_full_domain_replay']['CPU_examples_are_not_H1_experiments'])
        self.assertFalse(out['actual_control_and_pairing_provenance_verified'])
        self.assertFalse(out['new_hypothesis_cases_or_statistical_power_inferred'])


if __name__=='__main__':unittest.main()
