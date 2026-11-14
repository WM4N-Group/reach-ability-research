"""Regression checks for exact fixed-contract binomial limits."""

import math
import unittest

from reconfigurable_navigation.reachability.execution_risk import (
    FullRolloutCoverageRecord,
    calibrate_full_rollout_coverage,
    lower_success_probability,
    minimum_all_successes,
    minimum_all_successes_for_union,
)


class ExecutionRiskTests(unittest.TestCase):
    def test_full_rollout_joint_coverage_needs_59_independent_zero_failure_trials(self):
        contract = "a" * 64
        records = [FullRolloutCoverageRecord(str(i), contract, "full_rollout", True)
                   for i in range(59)]
        self.assertLess(calibrate_full_rollout_coverage(
            records[:58], expected_contract_sha256=contract).joint_coverage_lower_bound, 0.95)
        result = calibrate_full_rollout_coverage(records, expected_contract_sha256=contract)
        self.assertGreaterEqual(result.joint_coverage_lower_bound, 0.95)
        self.assertEqual((result.successes, result.trials, result.confidence_level), (59, 59, 0.95))

    def test_full_rollout_calibration_rejects_duplicate_or_stepwise_records(self):
        contract = "a" * 64
        valid = FullRolloutCoverageRecord("seed-1", contract, "full_rollout", True)
        with self.assertRaisesRegex(ValueError, "unique"):
            calibrate_full_rollout_coverage([valid, valid], expected_contract_sha256=contract)
        with self.assertRaisesRegex(ValueError, "full rollout"):
            calibrate_full_rollout_coverage(
                [FullRolloutCoverageRecord("seed-1", contract, "control_step", True)],
                expected_contract_sha256=contract)
        with self.assertRaisesRegex(ValueError, "frozen contract"):
            calibrate_full_rollout_coverage(
                [FullRolloutCoverageRecord("seed-1", "b" * 64, "full_rollout", True)],
                expected_contract_sha256=contract)
        with self.assertRaisesRegex(ValueError, "Boolean"):
            calibrate_full_rollout_coverage(
                [FullRolloutCoverageRecord("seed-1", contract, "full_rollout", 1)],
                expected_contract_sha256=contract)

    def test_union_budget_counts_each_predeclared_component(self):
        self.assertEqual(minimum_all_successes_for_union(0.95, 1), 59)
        count = minimum_all_successes_for_union(0.95, 10)
        per_component_target = 1.0 - 0.05 / 10
        self.assertGreaterEqual(lower_success_probability(count, count, 0.05 / 10),
                                per_component_target)
        self.assertLess(lower_success_probability(count - 1, count - 1, 0.05 / 10),
                        per_component_target)
        with self.assertRaises(ValueError):
            minimum_all_successes_for_union(0.95, 0)

    def test_all_successes_bound_and_required_sample_count(self):
        self.assertEqual(minimum_all_successes(0.95, 0.05), 59)
        self.assertLess(lower_success_probability(58, 58), 0.95)
        self.assertGreaterEqual(lower_success_probability(59, 59), 0.95)
        self.assertTrue(math.isclose(lower_success_probability(8, 8), 0.05 ** (1 / 8)))

    def test_failures_and_invalid_inputs(self):
        self.assertEqual(lower_success_probability(0, 8), 0.0)
        self.assertLess(lower_success_probability(7, 8), lower_success_probability(8, 8))
        with self.assertRaises(ValueError):
            lower_success_probability(9, 8)
        with self.assertRaises(ValueError):
            lower_success_probability(1, 0)
        with self.assertRaises(ValueError):
            minimum_all_successes(1.0)


if __name__ == "__main__":
    unittest.main()
