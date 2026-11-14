import tempfile
from pathlib import Path
import unittest
from .analysis_paths import relocated,resolve


class AnalysisPathTests(unittest.TestCase):
    def test_default_context_does_not_change_old_source_semantics(self):
        self.assertEqual(resolve('/original/path'),Path('/original/path'))

    def test_explicit_relocation_and_strict_no_fallback(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            with relocated({'/old/owner':str(root)},allowed_roots=(root,)):
                self.assertEqual(resolve('/old/owner/abc'),root/'abc')
                with self.assertRaises(ValueError):resolve('/unknown/owner/abc')
                self.assertEqual(resolve(root/'input.json'),root/'input.json')

    def test_mappings_are_context_scoped_even_after_error(self):
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaises(RuntimeError):
                with relocated({'/original/path':t}):raise RuntimeError('unit test')
        self.assertEqual(resolve('/original/path'),Path('/original/path'))

    def test_overlap_and_traversal_not_aliases(self):
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaises(ValueError):
                with relocated({'/old':t,'/old/nested':t}):pass
            with relocated({'/old':t}):
                with self.assertRaises(ValueError):resolve('/old/../another/secret')

    def test_symlink_escape_refused(self):
        with tempfile.TemporaryDirectory() as t, tempfile.TemporaryDirectory() as other:
            root=Path(t);(root/'escape').symlink_to(other,target_is_directory=True)
            with relocated({'/old':t}):
                with self.assertRaises(ValueError):resolve('/old/escape/secret')


if __name__=='__main__':unittest.main()
