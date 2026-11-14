"""Checks for PhysX shape-offset audit integrity and ground abstention."""

import copy
import json
from pathlib import Path
import tempfile
import unittest

from audit_piper_scene_shape_offsets import audit, check_shape


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "evidence/2026-10-08/scene-shape-offset-readonly-protocol.json"
RAW_DIR = ROOT.parent / "artifacts/go2-piper/2026-10-08/scene-shape-offsets"


class ShapeOffsetAuditChecks(unittest.TestCase):
    def test_shape_tensor_dimensions_are_checked(self):
        shape = {
            "prim_paths": ["/base"], "shape_count": 1,
            "contact_offsets_m": [0.003], "rest_offsets_m": [0.0],
            "material_properties": [[0.5, 0.5, 0.0]],
        }
        check_shape(shape, "/base")
        shape["contact_offsets_m"] = []
        with self.assertRaisesRegex(ValueError, "Unexpected PhysX shape view"):
            check_shape(shape, "/base")

    def test_ground_query_failure_never_becomes_zero_offset(self):
        report_path = RAW_DIR / "scene-shape-offsets.json"
        log_path = RAW_DIR / "probe.log"
        if not report_path.is_file() or not log_path.is_file():
            self.skipTest("Original remote probe artifacts are not present")
        result = audit(PROTOCOL, report_path, log_path)
        self.assertEqual(result["ground_query_status"], "rigid_body_view_error")
        self.assertIsNone(result["ground_runtime_offsets"])
        self.assertIsNone(result["scene_contract_sha256"])
        self.assertFalse(result["contact_authorized"])

        altered = copy.deepcopy(json.loads(report_path.read_text(encoding="utf-8")))
        altered["ground_physx_rigid_view_query"]["offsets"] = {
            "contact_offsets_m": [0.0], "rest_offsets_m": [0.0],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "altered.json"
            path.write_text(json.dumps(altered), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "must not carry offsets"):
                audit(PROTOCOL, path, log_path)


if __name__ == "__main__":
    unittest.main()
