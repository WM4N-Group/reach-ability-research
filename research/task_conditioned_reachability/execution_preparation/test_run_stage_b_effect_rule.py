"""Offline entrypoint schema/negative tests only, no raw physical logs read."""
from dataclasses import asdict,replace
import unittest
from .run_stage_b_effect_rule import evaluate_serialized
from .successor_aware_choice import Task,Candidate,Domain,ObservedBranch,digest


class OfflineEntryTests(unittest.TestCase):
    def setUp(self):
        task=Task('CPU_SCHEMA_NOT_EXPERIMENT','a'*64,'b'*64,'PREPARE','c'*64)
        ids=('original','lateral_plus_0p04','lateral_minus_0p04')
        self.domain=Domain(task,tuple(Candidate(c,task.sha256,'d'*64,'CPU:'+c,c,
            'original' if c=='original' else 'owner_registered_alternative') for c in ids),'original',None,'CPU_TEST_ONLY')
        self.records=[ObservedBranch(c,task.sha256,'CPU_PAIR_NOT_REAL_INIT_PROOF',digest({'row':c}),
            'SUCCESS','SUCCESS',local,full,full+1.) for c,local,full in zip(ids,(2.,1.,3.),(4.,5.,6.))]

    def test_existing_serialized_domain_and_records_run_full_research_evaluation(self):
        out=evaluate_serialized({'domain':asdict(self.domain)},[asdict(r) for r in self.records])
        self.assertTrue(out['material_strict_reversal_both_gaps_100ms'])
        self.assertFalse(out['physical_H1_proven_by_this_function'])
        self.assertFalse(out['actual_control_and_pairing_provenance_verified'])

    def test_missing_branch_is_incomplete_without_invented_result_hash_or_failure(self):
        out=evaluate_serialized(asdict(self.domain),[asdict(r) for r in self.records[:1]])
        self.assertEqual(out['classification'],'NO_CONCLUSION_INCOMPLETE_TABLE')
        self.assertEqual(out['unavailable_candidate_ids'],['lateral_plus_0p04','lateral_minus_0p04'])
        self.assertEqual(len(out['received_branch_records']),1)
        self.assertIsNone(out['raw_full_domain_replay'])
        self.assertIsNone(out['material_strict_reversal_both_gaps_100ms'])
        self.assertFalse(out['unpublished_result_or_outcome_synthesized'])

    def test_empty_asynchronous_delivery_has_no_synthetic_observed_records(self):
        out=evaluate_serialized(asdict(self.domain),[])
        self.assertEqual(out['received_branch_records'],[])
        self.assertEqual(len(out['unavailable_candidate_ids']),3)

    def test_duplicate_received_branch_rejected_even_while_table_incomplete(self):
        rows=[asdict(self.records[0])]*2
        with self.assertRaisesRegex(ValueError,'Unique observed'):
            evaluate_serialized(asdict(self.domain),rows)

    def test_censored_record_is_preserved_and_blocks_conclusion(self):
        r=list(self.records);r[2]=replace(r[2],chain_outcome='CENSORED',chain_completion_s=None)
        out=evaluate_serialized(asdict(self.domain),[asdict(x) for x in r])
        self.assertEqual(out['classification'],'NO_CONCLUSION_INCOMPLETE_TABLE')
        self.assertEqual(len(out['raw_full_domain_replay']['branch_records']),3)

    def test_partial_delivery_cannot_reduce_the_declared_domain(self):
        domain=asdict(self.domain);domain['candidates']=domain['candidates'][:2]
        with self.assertRaisesRegex(ValueError,'Fixed full N=3'):
            evaluate_serialized(domain,[asdict(self.records[0])])

    def test_wrong_task_or_non_observed_fields_rejected(self):
        rows=[asdict(r) for r in self.records];rows[1]['task_sha256']='e'*64
        with self.assertRaisesRegex(ValueError,'Same task'):evaluate_serialized(asdict(self.domain),rows)
        rows=[asdict(r) for r in self.records];rows[0]['predicted_cost_s']=1.
        with self.assertRaises(TypeError):evaluate_serialized(asdict(self.domain),rows)


if __name__=='__main__':unittest.main()
