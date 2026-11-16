"""SOFTWARE metadata only: different audit/performance policies are not treatment.

No source manifests, simulation, models, media or actual result files are loaded.
A missing profile must withhold comparison, NOT block or erase an E main result.
"""
import unittest
from .v4_outcome_summary import summarize

SCENE = 'a' * 64
PROFILE = 'c' * 64


def row(arm, **changes):
    r = dict(arm=arm, run_role='V4_FIVE_ARM_TASK_MAIN', source_phase='main',
        source_task_main_dispatch_count=1, scene_sha256=SCENE,
        source_result_sha256='b' * 64, source_result_ref='EXPLICIT_SOFTWARE_NOT_NATIVE',
        task_success=True, resource_censored=False, api_censored=False,
        VLM_calls=0 if arm == 'E' else 1, WM_forward_batches=1 if arm in 'AB' else 0,
        effective_optimizer_choices=1 if arm in 'BD' else 0,
        success_elapsed_sim_s=12. if arm in 'ACE' else 10.,
        complete_elevated_task_evidence=dict(three_original_placements_verified=True,
            original_CLIMB_receipts_verified=True, goal_deck_actual_support_verified=True,
            original_final_stop_and_stow_verified=True, same_world_native_guards_intact=True),
        common_execution_profile_sha256=PROFILE,
        common_execution_profile_ref='EXPLICIT_SOFTWARE_SHARED_FROZEN_CONFIG_NOT_A_REAL_RELEASE')
    r.update(changes)
    return r


class ExecutionProfileComparisonTests(unittest.TestCase):
    def summary(self, rows):
        return summarize(rows, scene_sha256=SCENE)

    def test_different_performance_or_guard_policy_refuses_B_minus_A_delta(self):
        s = self.summary([row('A'), row('B', common_execution_profile_sha256='d'*64)])
        c = s['primary_contrasts']['B-A']
        self.assertEqual(c['status'], 'COMMON_EXECUTION_PROFILE_MISMATCH')
        self.assertIsNone(c['successful_sim_delta'])
        self.assertEqual(s['original_arm_count'], 2)
        self.assertTrue(s['arms']['B']['task_success'])  # Keep literal outcomes.

    def test_same_scene_is_insufficient_for_D_minus_C(self):
        c = self.summary([row('C'), row('D', common_execution_profile_sha256='d'*64)])['primary_contrasts']['D-C']
        self.assertEqual(c['status'], 'COMMON_EXECUTION_PROFILE_MISMATCH')
        self.assertIsNone(c['successful_sim_delta'])

    def test_matching_profile_allows_descriptive_delta_not_generalization(self):
        s = self.summary([row('A'), row('B')]); c = s['primary_contrasts']['B-A']
        self.assertEqual(c['status'], 'SINGLE_DEV_DESCRIPTIVE_ONLY')
        self.assertTrue(c['common_execution_profile_match'])
        self.assertEqual(c['successful_sim_delta'], -2.)
        self.assertFalse(s['statistical_or_WM_causal_advantage_established'])

    def test_missing_one_or_both_profiles_is_unknown_not_assumed_same(self):
        for arms in [('A',), ('B',), ('A','B')]:
            rows = [row('A'), row('B')]
            for r in rows:
                if r['arm'] in arms:
                    del r['common_execution_profile_sha256']
            c = self.summary(rows)['primary_contrasts']['B-A']
            self.assertEqual(c['status'], 'COMMON_EXECUTION_PROFILE_UNVERIFIED')
            self.assertIsNone(c['successful_sim_delta'])

    def test_malformed_digest_or_missing_provenance_does_not_establish_match(self):
        for changes in (dict(common_execution_profile_sha256='x'*64),
                        dict(common_execution_profile_sha256=True),
                        dict(common_execution_profile_sha256='c'*63),
                        dict(common_execution_profile_ref=''),
                        dict(common_execution_profile_ref=None)):
            c = self.summary([row('A'),row('B',**changes)])['primary_contrasts']['B-A']
            self.assertEqual(c['status'], 'COMMON_EXECUTION_PROFILE_UNVERIFIED')

    def test_E_standalone_without_profile_still_kept_not_execution_gate(self):
        r = row('E', task_success=False, success_elapsed_sim_s=None)
        del r['common_execution_profile_sha256']; del r['common_execution_profile_ref']
        s = self.summary([r])
        self.assertEqual(s['original_arm_count'], 1)
        self.assertEqual(s['missing_arms'], list('ABCD'))
        self.assertTrue(s['arms']['E']['method_identity_established'])

    def test_method_identity_missing_cannot_be_repaired_by_common_profile(self):
        c = self.summary([row('A',WM_forward_batches=0),row('B')])['primary_contrasts']['B-A']
        self.assertEqual(c['status'], 'METHOD_CONTRAST_NOT_ESTABLISHED')
        self.assertIsNone(c['successful_sim_delta'])

    def test_failure_and_censor_remain_literal_with_no_success_cost(self):
        s = self.summary([row('A', task_success=False, resource_censored=True,
            success_elapsed_sim_s=None), row('B',common_execution_profile_sha256='d'*64)])
        c = s['primary_contrasts']['B-A']
        self.assertTrue(c['baseline_censored']); self.assertFalse(c['baseline_actual_success'])
        self.assertIsNone(c['successful_sim_delta'])

    def test_same_profile_can_have_distinct_original_artifact_locations(self):
        c = self.summary([row('C'),row('D',common_execution_profile_ref='EXPLICIT_OTHER_COPY_SAME_BYTES')])['primary_contrasts']['D-C']
        self.assertEqual(c['status'], 'SINGLE_DEV_DESCRIPTIVE_ONLY')
        self.assertTrue(c['common_execution_profile_match'])


if __name__ == '__main__':
    unittest.main()
