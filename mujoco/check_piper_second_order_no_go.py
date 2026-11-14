"""Regression checks for the conditional second-order no-go bound."""

import unittest

from reconfigurable_navigation.reachability.second_order_no_go import evaluate_scalar_no_go


class ScalarNoGoTests(unittest.TestCase):
    def test_delay_alone_can_force_a_violation(self):
        result = evaluate_scalar_no_go(
            margin_upper=0.02, margin_rate_upper=-1.0,
            acceleration_upper_during_delay=0.0,
            acceleration_upper_after_delay=100.0,
            control_delay_s=0.05, horizon_s=0.05,
        )
        self.assertEqual(result.verdict, "conditional_unavoidable_violation")
        self.assertLessEqual(result.witness_time_s, 0.05)
        self.assertFalse(result.contact_authorized)

    def test_best_post_delay_acceleration_still_can_be_too_weak(self):
        result = evaluate_scalar_no_go(
            margin_upper=0.10, margin_rate_upper=-1.0,
            acceleration_upper_during_delay=0.0,
            acceleration_upper_after_delay=2.0,
            control_delay_s=0.02, horizon_s=0.30,
        )
        self.assertEqual(result.verdict, "conditional_unavoidable_violation")
        self.assertLess(result.optimistic_minimum_margin, 0.0)
        self.assertGreater(result.witness_time_s, 0.02)

    def test_positive_optimistic_margin_is_only_undetermined(self):
        result = evaluate_scalar_no_go(
            margin_upper=1.0, margin_rate_upper=0.0,
            acceleration_upper_during_delay=0.0,
            acceleration_upper_after_delay=2.0,
            control_delay_s=0.02, horizon_s=0.30,
        )
        self.assertEqual(result.verdict, "undetermined")
        self.assertFalse(result.contact_authorized)

    def test_segment_interior_minimum_is_checked(self):
        result = evaluate_scalar_no_go(
            margin_upper=0.2, margin_rate_upper=-1.0,
            acceleration_upper_during_delay=0.0,
            acceleration_upper_after_delay=2.0,
            control_delay_s=0.0, horizon_s=1.0,
        )
        self.assertEqual(result.verdict, "conditional_unavoidable_violation")
        self.assertAlmostEqual(result.optimistic_minimum_margin, -0.05)
        self.assertAlmostEqual(result.witness_time_s, 0.5)

    def test_delay_longer_than_horizon_and_invalid_inputs(self):
        result = evaluate_scalar_no_go(
            margin_upper=0.01, margin_rate_upper=-1.0,
            acceleration_upper_during_delay=0.0,
            acceleration_upper_after_delay=100.0,
            control_delay_s=1.0, horizon_s=0.02,
        )
        self.assertEqual(result.verdict, "conditional_unavoidable_violation")
        with self.assertRaises(ValueError):
            evaluate_scalar_no_go(
                margin_upper=float("nan"), margin_rate_upper=0.0,
                acceleration_upper_during_delay=0.0,
                acceleration_upper_after_delay=0.0,
                control_delay_s=0.0, horizon_s=0.1,
            )
        with self.assertRaises(ValueError):
            evaluate_scalar_no_go(
                margin_upper=1.0, margin_rate_upper=-1e308,
                acceleration_upper_during_delay=0.0,
                acceleration_upper_after_delay=0.0,
                control_delay_s=2.0, horizon_s=2.0,
            )


if __name__ == "__main__":
    unittest.main()
