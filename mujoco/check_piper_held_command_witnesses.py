"""Boundary and state-isolation checks for held-command witness logic."""

from __future__ import annotations

from decimal import Decimal
import unittest

from audit_piper_held_command_witnesses import assess_interval


class WitnessChecks(unittest.TestCase):
    def test_closed_boundary_refutes_only_matching_state(self) -> None:
        observations = [{
            "state_sha256": "state-a", "offset_x": Decimal("-0.01225"),
            "valid": True, "accepted": False, "reason": "arm_tracking_timeout",
            "source_sha256": "report-a",
        }]
        at_boundary = assess_interval(
            "state-a", Decimal("-0.012"), Decimal("0.00025"), observations
        )
        self.assertEqual(at_boundary["decision"], "refuted_by_witness")
        self.assertEqual(at_boundary["witnesses"][0]["source_sha256"], "report-a")
        self.assertEqual(assess_interval(
            "state-b", Decimal("-0.012"), Decimal("0.00025"), observations
        )["decision"], "abstain_no_continuous_certificate")
        self.assertEqual(assess_interval(
            "state-a", Decimal("-0.012"), Decimal("0.000249"), observations
        )["decision"], "abstain_no_continuous_certificate")

    def test_success_samples_never_create_positive_certificate(self) -> None:
        observations = [{
            "state_sha256": "state-a", "offset_x": Decimal("-0.012"),
            "valid": True, "accepted": True, "reason": "completed",
            "source_sha256": "report-a",
        }]
        self.assertEqual(assess_interval(
            "state-a", Decimal("-0.012"), Decimal("0"), observations
        )["decision"], "abstain_no_continuous_certificate")

    def test_unvalidated_same_state_observation_is_rejected(self) -> None:
        observations = [{
            "state_sha256": "state-a", "offset_x": Decimal("-0.01225"),
            "valid": False, "accepted": False, "reason": "arm_tracking_timeout",
            "source_sha256": "report-a",
        }]
        with self.assertRaises(ValueError):
            assess_interval("state-a", Decimal("-0.012"), Decimal("0.00025"), observations)


if __name__ == "__main__":
    unittest.main()
