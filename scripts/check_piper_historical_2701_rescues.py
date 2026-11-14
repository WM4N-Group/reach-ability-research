#!/usr/bin/env python3
"""Small synthetic guards for the bounded historical reader; no real source read."""
import copy
import unittest

from audit_piper_historical_2701_rescues import ENVS, TERMS, selected_native, target_telemetry


def report():
    names = sorted(TERMS)
    return dict(termination_flag_names=names, terminal_states=[dict(env_id=9, episode=1,
        elapsed_seconds=14.08, termination_flags=[n == 'invalid_hand_contact' for n in names])],
        per_env_completions=[1] * 32, per_env_successes=[0] * 32,
        failure_histories=[dict(env_id=9, pre_step_samples=[dict(elapsed_seconds=11.52), dict(elapsed_seconds=14.06)])])


class HistoricalGuards(unittest.TestCase):
    def test_explicit_native_names_not_fixed_position(self):
        _, label = selected_native(report(), 9)
        self.assertFalse(label['value'])
        self.assertEqual(label['native_failure_names'], ['invalid_hand_contact'])
        self.assertIsNone(label['successful_completion_seconds'])

    def test_native_failure_vetoes_same_frame_goal(self):
        r = report();r['terminal_states'][0]['termination_flags'][r['termination_flag_names'].index('box_settled')] = True
        self.assertFalse(selected_native(r, 9)[1]['value'])

    def test_duplicate_or_missing_selected_terminal_rejected(self):
        r = report();r['terminal_states'].append(copy.deepcopy(r['terminal_states'][0]))
        with self.assertRaises(ValueError):selected_native(r, 9)
        with self.assertRaises(ValueError):selected_native(report(), 26)

    def test_counter_disagreement_rejected(self):
        r = report();r['per_env_successes'][9] = 1
        with self.assertRaises(ValueError):selected_native(r, 9)

    def test_other_env_cannot_supply_reset(self):
        r = report();r['trace_env0'] = [dict(elapsed_seconds=0)]
        self.assertFalse(target_telemetry(r, 9)['measured_t0_receipt_in_handed_sources'])
        self.assertEqual(target_telemetry(r, 26)['target_env_history_count'], 0)
        with self.assertRaises(ValueError):target_telemetry(r, 0)
        with self.assertRaises(ValueError):selected_native(r, 0)

    def test_late_suffix_does_not_prove_reset_or_preference(self):
        v = target_telemetry(report(), ENVS[0])
        self.assertEqual(v['target_env_history_first_s'], 11.52)
        self.assertFalse(v['decision_time_features_or_between_arm_t0_difference_verified'])

    def test_unexpected_t0_receipt_requires_review(self):
        r = report();r['initial_states'] = []
        with self.assertRaises(ValueError):target_telemetry(r, 9)
        r = report();r['failure_histories'][0]['pre_step_samples'][0]['elapsed_seconds'] = 0
        with self.assertRaises(ValueError):target_telemetry(r, 9)

    def test_malformed_flag_array_rejected(self):
        r = report();r['terminal_states'][0]['termination_flags'][0] = 0
        with self.assertRaises(ValueError):selected_native(r, 9)


if __name__ == '__main__':
    unittest.main(verbosity=2)
