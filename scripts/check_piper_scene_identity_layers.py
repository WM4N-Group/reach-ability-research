"""Checks that observed identities stay separate from qualified contracts."""

import copy
import json
from pathlib import Path
import unittest

from audit_piper_scene_identity_layers import audit, project_layers
from audit_piper_scene_entry_identification_pilot import SCENE_CORE_FIELDS
from piper_scene_runtime_observation import canonical_sha256


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "evidence/2026-10-08/scene-entry-identification-pilot-5901-5904-protocol.json"
REPORT_DIR = ROOT.parent / "artifacts/go2-piper/2026-10-08/scene-entry-identification-5901-5904"


class SceneIdentityLayerChecks(unittest.TestCase):
    def test_synthetic_instance_change_does_not_change_configuration(self):
        observed = {key: key for key in SCENE_CORE_FIELDS}
        observed.update(schema_version=1, scope="same_rollout_runtime_observation_only",
                        seed=1, unresolved_layers=False, scene_contract_sha256=None,
                        entry_distribution_sha256=None, used_layers=[{
                            "kind": "file", "identifier": "robot.usd", "sha256": "a" * 64,
                        }], stage_export_sha256="b" * 64,
                        robot_mass_kg=[12.0], robot_material=[[0.8, 0.8, 0.0]],
                        box_mass_kg=[5.0], box_material=[[0.9, 0.9, 0.0]])
        report = {
            "seed": 1, "scene_runtime_observation": observed,
            "scene_runtime_observation_sha256": canonical_sha256(observed),
            "nav_actor_sha256": "c" * 64, "push_checkpoint_sha256": "d" * 64,
            "control_sha256": {"push": "e" * 64}, "initial_state": {"box_pos": [1, 0, 0]},
            "outcome": "nav_timeout",
        }
        first = project_layers(report)
        changed = copy.deepcopy(report)
        changed["scene_runtime_observation"]["robot_material"] = [[0.7, 0.7, 0.0]]
        changed["scene_runtime_observation_sha256"] = canonical_sha256(
            changed["scene_runtime_observation"])
        second = project_layers(changed)
        self.assertEqual(first["configuration_sha256"], second["configuration_sha256"])
        self.assertNotEqual(first["instance_observation_sha256"],
                            second["instance_observation_sha256"])
        self.assertIsNone(first["entry_observation_sha256"])

    def test_seen_pilot_remains_observation_only(self):
        if not REPORT_DIR.is_dir():
            self.skipTest("Original pilot reports are not present in this workspace")
        result = audit(PROTOCOL, REPORT_DIR)
        self.assertEqual(result["complete_denominator"], 4)
        self.assertEqual(result["configuration_groups"], 1)
        self.assertEqual(result["instance_observations"], 4)
        self.assertEqual(result["handoff_entry_observations"], 4)
        self.assertIsNone(result["scene_contract_sha256"])
        self.assertIsNone(result["entry_distribution_sha256"])
        self.assertFalse(result["contact_authorized"])

    def test_tampered_observation_and_entry_are_rejected(self):
        if not REPORT_DIR.is_dir():
            self.skipTest("Original pilot reports are not present in this workspace")
        report = json.loads((REPORT_DIR / "seed5901.json").read_text(encoding="utf-8"))
        tampered = copy.deepcopy(report)
        tampered["scene_runtime_observation"]["robot_material"][0][0][0] += 0.01
        with self.assertRaisesRegex(ValueError, "scene observation integrity"):
            project_layers(tampered)
        tampered = copy.deepcopy(report)
        tampered["handoff_entry_observation"]["nav_steps"] += 1
        with self.assertRaisesRegex(ValueError, "handoff entry digest"):
            project_layers(tampered)


if __name__ == "__main__":
    unittest.main()
