"""Explicit hindsight-table metadata fixtures, not measured/fit/predicted samples."""
import copy
import unittest
from operations.summarize_closed_bulk24_prefix import checked_prefix_count,native_ticks,complete_candidate_tables

class CompleteTablesTests(unittest.TestCase):
    def fixture(self):
        reports={}
        for ordinal,candidate,r,c in [(1,'original',2.,5.),(2,'lateral_plus_0p04',1.,6.),(3,'lateral_minus_0p04',1.5,4.)]:
            reports[ordinal]=dict(physical_features=[float(ordinal),0.]+[0.]*46,
                scalar=dict(ordinal=ordinal,candidate_id=candidate,group_id='FIXTURE',prefix_side='left',
                    new_geometry_definition_sha256='a'*64,current_READY_s=r,full_requested_CLIMB_success_s=c,
                    first_PREPARE_time_s=10.,source_result_passed=True))
        return reports
    def test_hindsight_local_full_reversal_is_not_online_or_hidden_world_proof(self):
        table=complete_candidate_tables(self.fixture())[0]
        self.assertEqual(table['hindsight_local_READY_minimizers'],['lateral_plus_0p04'])
        self.assertEqual(table['hindsight_full_success_minimizers'],['lateral_minus_0p04'])
        self.assertTrue(table['local_and_full_best_disjoint']);self.assertTrue(table['actual_public45_plus_age_exactly_equal'])
        self.assertFalse(table['same_RGBD_or_hidden_world_or_causal_effect_claimed'])
        self.assertTrue(table['not_online_predictions_or_trained_policy_or_method_gain'])
    def test_failed_best_local_candidate_stays_none_not_free_success_or_infinity_cost(self):
        reports=self.fixture();reports[2]['scalar'].update(full_requested_CLIMB_success_s=None,source_result_passed=False)
        table=complete_candidate_tables(reports)[0]
        self.assertTrue(table['at_least_one_local_minimizer_failed'])
        self.assertIsNone(table['rows'][1]['actual_full_CLIMB_success_s'])
        self.assertIsNone(table['observed_full_cost_gap_for_local_minimizers_ticks']['lateral_plus_0p04'])
    def test_two_of_three_candidates_is_not_complete_domain(self):
        reports=self.fixture();del reports[3]
        self.assertEqual(complete_candidate_tables(reports),[])
    def test_no_duplicate_seed_or_mixed_context_replaces_third_candidate(self):
        reports=self.fixture();reports[3]['scalar']['candidate_id']='original'
        with self.assertRaises(ValueError):complete_candidate_tables(reports)
        reports=self.fixture();reports[3]['scalar']['group_id']='OTHER'
        self.assertEqual(complete_candidate_tables(reports),[])
    def test_native_clock_conversion_preserves_exact_tick_ties_not_rounding_off_grid(self):
        self.assertEqual(native_ticks(.1-1e-12),20)
        with self.assertRaises(ValueError):native_ticks(.102)
        for value in (None,True,float('nan'),-1.):
            with self.assertRaises(ValueError):native_ticks(value)
        reports=self.fixture();reports[3]['scalar']['current_READY_s']=1.+1e-12
        table=complete_candidate_tables(reports)[0]
        self.assertEqual(table['hindsight_local_READY_minimizers'],['lateral_plus_0p04','lateral_minus_0p04'])
        self.assertFalse(table['local_and_full_best_disjoint'])
    def test_inconsistent_failure_flag_or_negative_success_time_refused(self):
        reports=self.fixture();reports[2]['scalar']['source_result_passed']=False
        with self.assertRaises(ValueError):complete_candidate_tables(reports)
        reports=self.fixture();reports[2]['scalar']['full_requested_CLIMB_success_s']=.5
        with self.assertRaises(ValueError):complete_candidate_tables(reports)
    def test_explicit_prefix_requires_all_attempts_including_failed_unreached(self):
        manifest=dict(role='FIXED_CLOSED_BULK24_PREFIX_READ_ONLY_NOT_FIT',prefix_count=20,
            attempts=[dict(ordinal=i)for i in range(1,21)])
        self.assertEqual(checked_prefix_count(manifest),20)
        manifest['attempts'].pop(3)
        with self.assertRaises(ValueError):checked_prefix_count(manifest)
    def test_legacy_first_ten_cannot_be_silently_reinterpreted_as_twenty(self):
        manifest=dict(role='FIXED_FIRST_TEN_BULK24_READ_ONLY_NOT_FIT',attempts=[dict(ordinal=i)for i in range(1,11)])
        self.assertEqual(checked_prefix_count(manifest),10)
        manifest['prefix_count']=20
        with self.assertRaises(ValueError):checked_prefix_count(manifest)

if __name__=='__main__':unittest.main()
