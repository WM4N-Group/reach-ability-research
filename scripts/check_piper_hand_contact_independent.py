"""Checks for the preregistered hand-contact substep audit."""

import json
from pathlib import Path
import unittest

from audit_piper_hand_contact_independent import (
    substep_only_illegal_steps, summarize_report,
)


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "evidence/2026-10-08/hand-contact-independent-6001-6016-protocol.json"
REPORT_DIR = ROOT.parent / "artifacts/go2-piper/2026-10-08/hand-contact-independent-6001-6016"


class HandContactIndependentChecks(unittest.TestCase):
    def test_substep_only_event_requires_clean_final_substep(self):
        flags = [False, True, False, False, False, False, False, True]
        self.assertEqual(substep_only_illegal_steps(flags), [1])
        with self.assertRaisesRegex(ValueError, "full control steps"):
            substep_only_illegal_steps(flags[:-1])

    def test_first_unseen_seed_is_audit_compatible(self):
        path = REPORT_DIR / "seed6001.json"
        if not path.is_file():
            self.skipTest("Original unseen-seed report is not present in this workspace")
        report = json.loads(path.read_text(encoding="utf-8"))
        protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
        summary = summarize_report(report, protocol)
        self.assertEqual(summary["seed"], 6001)
        self.assertEqual(summary["push_physics_substeps"],
                         4 * report["push_executed_steps"])
        self.assertFalse(summary["substep_only_illegal_control_steps"])
        self.assertIsNotNone(summary["maximum_sensor_to_loaded_point_m"])


if __name__ == "__main__":
    unittest.main()
