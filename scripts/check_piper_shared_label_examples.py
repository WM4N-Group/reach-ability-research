"""Check causal windows, censoring and distinct execution/stage outcomes."""
import unittest

from export_piper_shared_label_examples import clearance_window, native_event_window, stage_labels


class SharedLabelChecks(unittest.TestCase):
    def rows(self, count=61):
        return [dict(step=i, time_s=i * 0.02, clearance_m=0.08 - i * 0.0001)
                for i in range(count)]

    def test_inclusive_window_and_query_reference(self):
        result = clearance_window(self.rows(), 0, 0.02, 0.4)
        self.assertTrue(result['valid'])
        self.assertEqual(result['observed_sample_count'], 21)
        self.assertAlmostEqual(result['value'], 0.043)
        self.assertAlmostEqual(result['constant_reference_m'], 0.045)
        self.assertIsNone(result['censor_time_s'])

    def test_incomplete_window_keeps_prefix_but_not_full_target(self):
        result = clearance_window(self.rows(11), 0, 0.02, 0.4)
        self.assertFalse(result['valid'])
        self.assertIsNone(result['value'])
        self.assertFalse(result['horizon_complete'])
        self.assertAlmostEqual(result['observed_prefix_min'], 0.044)
        self.assertEqual(result['censor_time_s'], 0.2)

    def test_error_in_future_does_not_mask_complete_past_window(self):
        rows = self.rows(31)
        self.assertTrue(clearance_window(rows, 0, 0.02, 0.4)['valid'])
        self.assertFalse(clearance_window(rows, 20, 0.02, 0.4)['valid'])

    def test_missing_geometry_is_not_zero_filled(self):
        rows = self.rows()
        rows[10]['clearance_m'] = None
        result = clearance_window(rows, 0, 0.02, 0.4)
        self.assertFalse(result['valid'])
        self.assertEqual(result['observed_sample_count'], 10)

    def test_nonfinite_geometry_masks_window(self):
        rows = self.rows()
        rows[10]['clearance_m'] = float('nan')
        self.assertFalse(clearance_window(rows, 0, 0.02, 0.4)['valid'])

    def test_gap_or_auto_reset_cannot_complete_old_episode(self):
        rows = self.rows()
        rows[10]['step'] = 0
        rows[10]['time_s'] = 0.
        result = clearance_window(rows, 0, 0.02, 0.4)
        self.assertFalse(result['valid'])
        self.assertEqual(result['invalid_reason'], 'missing_sample_or_episode_boundary')

    def test_unaligned_horizon_rejected(self):
        with self.assertRaises(ValueError):
            clearance_window(self.rows(), 0, 0.02, 0.41)

    def test_native_breach_known_even_in_censored_window(self):
        rows = self.rows(11)
        self.assertTrue(native_event_window(rows, 0., 0.4, True)['value'])
        self.assertIsNone(native_event_window(rows, 0., 0.4, False)['value'])
        self.assertFalse(native_event_window(rows, 0., 0.1, True)['value'])

    def report(self, outcome):
        return dict(outcome=outcome, events=[{'time_s':0.1}],
                    control_events=[{'event':'push_activated', 'time_s':0.1}])

    def test_runtime_outcome_unknown_vs_native_negative(self):
        runtime = stage_labels(self.report('runtime_error'), self.rows())
        native = stage_labels(self.report('native_termination_during_push'), self.rows())
        self.assertIsNone(runtime['push_complete']['value'])
        self.assertFalse(native['push_complete']['value'])
        self.assertEqual(runtime['exit_complete']['invalid_reason'], 'not_entered')
        self.assertEqual(native['next_skill_complete']['invalid_reason'], 'not_entered')

    def test_previous_push_success_survives_later_exception(self):
        report = self.report('runtime_error')
        report['control_events'].append({'event':'native_push_settled_exit_requested', 'time_s':0.4})
        result = stage_labels(report, self.rows())
        self.assertTrue(result['push_complete']['value'])
        self.assertIsNone(result['exit_complete']['value'])
        self.assertEqual(result['exit_complete']['invalid_reason'], 'runtime_error_before_observed_stage_outcome')


if __name__ == '__main__':
    unittest.main()
