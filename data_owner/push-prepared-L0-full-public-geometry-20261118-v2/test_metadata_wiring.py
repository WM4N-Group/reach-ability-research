"""New four wiring checks only; stdlib software, no native/old suite rerun."""
import ast,importlib.util
from pathlib import Path
import unittest
P=Path(__file__).resolve().parent
class Wiring(unittest.TestCase):
    def test_metadata_default_off_without_imports_or_paths(self):
        spec=importlib.util.spec_from_file_location('_new_metadata_default_off',P/'metadata_prepare.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
        self.assertIsNone(m.qualify())
    def test_same_26_helper_table_prepare_and_run(self):
        tree=ast.parse((P/'worker.py').read_text());helpers=ast.literal_eval(next(n.value for n in tree.body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='HELPER_NAMES'for t in n.targets)))
        self.assertEqual(len(helpers),26);self.assertEqual(len(set(helpers)),26)
        self.assertIn('public_geometry_provenance',helpers);self.assertIn('metadata_prepare',helpers);self.assertNotIn('boundary_driver',helpers)
        run=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='run')
        self.assertTrue(any(isinstance(n,ast.For)and isinstance(n.iter,ast.Name)and n.iter.id=='HELPER_NAMES'for n in ast.walk(run)))
        self.assertFalse(any(isinstance(n,ast.Call)and isinstance(n.func,ast.Name)and n.func.id=='qualify'for n in ast.walk(run)))
    def test_CLI_actual_prepare_qualifies_and_records_real_metadata(self):
        tree=ast.parse((P/'worker.py').read_text());calls=[n for n in ast.walk(tree)if isinstance(n,ast.Call)and isinstance(n.func,ast.Name)and n.func.id=='qualify']
        self.assertEqual(len(calls),1);self.assertEqual([ast.unparse(a)for a in calls[0].args],['c','f'])
        self.assertTrue(any(isinstance(n,ast.keyword)and n.arg=='metadata_qualification'and isinstance(n.value,ast.Name)and n.value.id=='metadata'for n in ast.walk(tree)))
    def test_controller_requires_actual_metadata_outcome(self):
        text=(P/'phase_control.py').read_text()
        for key in ('original_resolver_missing_pin_negative_rejected','original_resolver_real_declaring_pin_positive_returned','original_backend_factory_executor_constructor_and_attach_ABI_returned','actual_compiled_model_or_physical_witness_verification'):
            self.assertIn('metadata['+repr(key)+']',text)
if __name__=='__main__':unittest.main()
