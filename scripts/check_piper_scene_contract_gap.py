"""Focused checks for the scene-contract gap audit's refusal behavior."""

import copy
import unittest

from audit_piper_scene_contract_gap import absent_identity_fields, common, validate_probe


class SceneContractGapChecks(unittest.TestCase):
    def test_identity_gap_must_be_observed_in_reports(self):
        reports = [{"seed": 1}, {"seed": 2}]
        self.assertIn("scene_contract_sha256", absent_identity_fields(reports))
        reports[1]["scene_contract_sha256"] = "a" * 64
        with self.assertRaisesRegex(ValueError, "now contain scene identity fields"):
            absent_identity_fields(reports)

    def test_common_rejects_missing_or_conflicting_values(self):
        reports = [{"task": "piper"}, {"task": "piper"}]
        self.assertEqual(common(reports, "task"), "piper")
        missing = copy.deepcopy(reports)
        del missing[1]["task"]
        with self.assertRaisesRegex(ValueError, "Missing or inconsistent"):
            common(missing, "task")
        reports[1]["task"] = "arx5"
        with self.assertRaisesRegex(ValueError, "Missing or inconsistent"):
            common(reports, "task")

    def test_probe_must_match_loaded_ground_and_control_grid(self):
        probe = {
            "scope": "read_only_loaded_isaac_collision_prim_probe",
            "policy_loaded": False,
            "rollout_executed": False,
            "task": "piper",
            "ground_collision_prims": ["/World/ground/collision"],
            "usd_sha256": "a" * 64,
            "physics_dt_s": 0.005,
            "control_decimation": 4,
        }
        self.assertEqual(validate_probe(probe, "piper", "/World/ground/collision", 0.02),
                         (0.005, 4))
        with self.assertRaisesRegex(ValueError, "ground prim"):
            validate_probe(probe, "piper", "/World/other", 0.02)
        with self.assertRaisesRegex(ValueError, "physics grid"):
            validate_probe(probe, "piper", "/World/ground/collision", 0.01)
        contaminated = copy.deepcopy(probe)
        contaminated["rollout_executed"] = True
        with self.assertRaisesRegex(ValueError, "provenance"):
            validate_probe(contaminated, "piper", "/World/ground/collision", 0.02)


if __name__ == "__main__":
    unittest.main()
