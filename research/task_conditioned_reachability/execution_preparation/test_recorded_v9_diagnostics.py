from copy import deepcopy
import unittest
from .recorded_v9_diagnostics import load_recorded_owner_sources,diagnose


class RecordedDiagnosticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.problem,cls.rows=load_recorded_owner_sources()

    def test_actual_public_event_and_contract_correction(self):
        r=diagnose(self.problem,self.rows)
        self.assertEqual(r['contract_version'],'0.1.1');self.assertFalse(r['live_observation'])
        self.assertAlmostEqual(r['public_problem']['query_time_s'],51.675)
        self.assertEqual([r['push_distance_m'] for r in r['rows']],[.2,.4,.6])

    def test_request_gaps_not_outcomes(self):
        r=diagnose(self.problem,self.rows)
        for row,gap in zip(r['rows'],(.4,.2,0.)):
            self.assertAlmostEqual(row['requested_longitudinal_gap_m'],gap)
            self.assertFalse(row['rankable']);self.assertIsNone(row['feasible'])

    def test_single_forecast_not_borrowed_for_other_distances(self):
        r=diagnose(self.problem,self.rows)
        self.assertEqual(r['causal_forecast_rows'],1)
        self.assertIsNone(r['rows'][0]['recorded_forecast_diagnostic'])
        self.assertIsNone(r['rows'][1]['recorded_forecast_diagnostic'])
        self.assertAlmostEqual(r['rows'][2]['recorded_forecast_diagnostic']['nominal_longitudinal_overlap_m'],.05874468213)

    def test_elapsed_not_transferred_to_incompatible_cost_scope(self):
        row=diagnose(self.problem,self.rows)['rows'][2]
        self.assertAlmostEqual(row['recorded_forecast_diagnostic']['predicted_elapsed_s'],20.6788730621)
        self.assertIsNone(row['elapsed_for_required_cost_s'])
        self.assertFalse(row['recorded_forecast_diagnostic']['model_std_as_error_bound_used'])

    def test_wrong_frame_or_observation_refused(self):
        for field,value in (('frame','box_local_X'),('query_input_sha256','another')):
            rows=deepcopy(self.rows);rows[0][field]=value
            with self.assertRaises(ValueError):diagnose(self.problem,rows)

    def test_actual_future_or_live_promotion_refused(self):
        for field,value in (('actual_future_used',True),('instance_kind','LIVE')):
            p=deepcopy(self.problem);p[field]=value
            with self.assertRaises(ValueError):diagnose(p,self.rows)

    def test_unknown_no_dispatch_or_new_inference(self):
        r=diagnose(self.problem,self.rows)
        self.assertIsNone(r['best_candidate']);self.assertFalse(r['physical_dispatch'])
        self.assertFalse(r['full_selector_called']);self.assertEqual(r['new_model_forward_calls'],0)


if __name__=='__main__':unittest.main()
