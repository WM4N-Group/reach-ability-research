"""Root relocation/output safety tests. Synthetic files only; no external evidence."""
from pathlib import Path
import argparse
import tempfile
import unittest
from unittest.mock import patch

import evidence_paths as paths
import replay_checker as c


class RootChecks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        for name in ('control', 'run', 'terminal', 'verification', 'candidate'):
            (self.base / name).mkdir()
        self.args = argparse.Namespace(control_root=self.base/'control', run_root=self.base/'run',
            terminal_review_root=self.base/'terminal', verification_root=self.base/'verification')
        self.roots = paths.EvidenceRoots.from_args(self.args)

    def test_missing_root_reports_instead_of_guessing(self):
        self.args.control_root = self.base/'absent'
        with self.assertRaisesRegex(FileNotFoundError, 'Missing external evidence root'):
            paths.EvidenceRoots.from_args(self.args)

    def test_original_locations_use_roles_not_historical_absolute_strings(self):
        expected = self.base/'run/native-small/attempt/controllers/planner-masks-complete.jsonl'
        expected.parent.mkdir(parents=True)
        expected.write_text('synthetic')
        self.assertEqual(self.roots.original_path('payloads'), expected)

    def test_unknown_role_is_rejected(self):
        with self.assertRaises(KeyError):
            self.roots.original_path('untrusted_role')

    def test_missing_file_is_not_regenerated(self):
        with self.assertRaises(FileNotFoundError):
            self.roots.original_path('control_manifest')
        self.assertFalse((self.base/'control/package-manifest.json').exists())

    def test_symlink_escape_is_rejected(self):
        target = self.base/'elsewhere.json'
        target.write_text('synthetic')
        (self.base/'control/package-manifest.json').symlink_to(target)
        with self.assertRaisesRegex(ValueError, 'escapes supplied root'):
            self.roots.original_path('control_manifest')

    def test_output_cannot_touch_inputs_candidate_or_repo(self):
        for root in (self.roots.control, self.roots.run, self.roots.terminal_review,
                     self.roots.verification, self.base/'candidate', paths.REPO_ROOT):
            with self.assertRaises(ValueError):
                self.roots.new_output(root/'never-write.json', self.base/'candidate')

    def test_output_is_external_and_cannot_overwrite(self):
        out = self.base/'fresh-result.json'
        self.assertEqual(self.roots.new_output(out), out)
        out.write_text('sentinel')
        with self.assertRaises(FileExistsError):
            self.roots.new_output(out)
        self.assertEqual(out.read_text(), 'sentinel')

    def test_oracle_anchor_not_weakened_by_relocation(self):
        (self.base/'verification/original_oracle.json').write_text('{}')
        with patch.object(c, 'ROOTS', self.roots), patch.object(c, 'VERIFICATION', self.roots.verification):
            with self.assertRaisesRegex(ValueError, 'oracle SHA mismatch'):
                c.read_contract_and_oracle()

    def test_binding_hash_is_checked_at_relocated_path(self):
        role_names = ('control_manifest', 'run_manifest', 'events', 'payloads', 'prior_pair_index', 'native_frame')
        locations = {
            'control_manifest': self.roots.control/'package-manifest.json',
            'run_manifest': self.roots.run/'run-files-manifest.json',
            'events': self.roots.run/'native-small/attempt/controllers/floor-aware-planning-events.jsonl',
            'payloads': self.roots.run/'native-small/attempt/controllers/planner-masks-complete.jsonl',
            'prior_pair_index': self.roots.terminal_review/'complete_mask_pair_index.json',
            'native_frame': self.roots.terminal_review/'last_native_control_line.jsonl',
        }
        bindings = {}
        for role in role_names:
            p = locations[role]
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text('synthetic-'+role)
            bindings[role] = {'path': '/historical/path/not-read', 'sha256': c.sha(p)}
        with patch.object(c, 'ROOTS', self.roots):
            c.verify_original_bindings({'original_bindings': bindings})
            locations['events'].write_text('tampered')
            with self.assertRaisesRegex(ValueError, 'binding mismatch: events'):
                c.verify_original_bindings({'original_bindings': bindings})


if __name__ == '__main__':
    unittest.main(verbosity=2)
