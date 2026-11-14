import unittest
from .consume_authorized_A import consume


class RealAConsumptionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.r=consume() # one read of COMPLETED results, no model load/filter/forward

    def test_completed_real_prediction_role_not_fixture_or_outcome(self):
        self.assertIn('AUTHORIZED_NEW_CAUSAL_MODEL_PREDICTIONS_UNCALIBRATED',self.r['data_role'])
        self.assertEqual([x['distance_m'] for x in self.r['raw_response_rows']],[.2,.4,.6])
        self.assertTrue(self.r['levels']['model_response_comparison']['all_three_available'])
        self.assertFalse(self.r['actual_outcomes_opened'])

    def test_replay_only_numerical_not_quality(self):
        r=self.r['original06_replay'];self.assertTrue(r['passed'])
        self.assertFalse(r['is_model_quality_or_physical_certificate'])
        self.assertLess(r['heads']['mean']['max_abs_error'],1e-5)

    def test_real_action_response_includes_box_robot_difference(self):
        rows=self.r['raw_response_rows']
        self.assertGreater(rows[0]['relative_box_minus_robot_dx_anchor_body_m'],0.)
        self.assertLess(rows[2]['relative_box_minus_robot_dx_anchor_body_m'],0.)
        self.assertTrue(all(r['relative_displacement_is_not_world_clearance'] for r in rows))
        self.assertEqual(len(self.r['levels']['model_response_comparison']['pairwise_numeric_response']),3)

    def test_three_real_rows_do_not_fix_structural_cost_state_gap(self):
        self.assertFalse(self.r['levels']['successful_time_comparison']['all_three_comparable'])
        self.assertFalse(self.r['levels']['executable_selection']['sufficient'])
        self.assertTrue(self.r['prior_structural_NoGo_confirmed'])
        self.assertIsNone(self.r['online_action']);self.assertFalse(self.r['world_terminal_pose_inferred'])

    def test_Reach_reads_only_no_second_batch(self):
        self.assertFalse(self.r['model_reloaded_by_Reach']);self.assertEqual(self.r['new_forward_calls_by_Reach'],0)
        self.assertFalse(self.r['physical_dispatch']);self.assertFalse(self.r['fit_norm_training'])
        self.assertEqual(self.r['source_execution']['predict_batches'],1)


if __name__=='__main__':unittest.main()
