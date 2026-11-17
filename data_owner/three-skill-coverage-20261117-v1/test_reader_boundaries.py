"""Two reader-only opt-in/pin refusal checks; no simulator/old test suites."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

P = Path(__file__).with_name('derive_fixed24_coverage.py')
spec = importlib.util.spec_from_file_location('skill_coverage_reader', P)
reader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reader)

class ReaderBoundaries(unittest.TestCase):
    def test_default_off_does_not_open_missing_tree(self):
        self.assertIsNone(reader.derive('/definitely-absent/never-opened', enabled=False))

    def test_changed_parent_release_rejected_before_children(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/reader.PARENT
            p.mkdir()
            (p/'release.json').write_text('{}\n')
            with self.assertRaisesRegex(ValueError, 'Original release/member SHA drift'):
                reader.derive(d, enabled=True)

if __name__ == '__main__':
    unittest.main()
