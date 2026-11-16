"""Only changed integration fences; NOT native/lease/full old-suite evidence."""
import ast
import importlib.util
from pathlib import Path
import sys
import unittest
P = Path(__file__).with_name('worker.py')
OLD = Path('/home/yuanyue/main/work/data-team/development/perf-native-runner-20261116-v4/worker.py')

def tree(path):
    return ast.parse(path.read_text())

def function(root, name):
    return next(n for n in ast.walk(root) if isinstance(n, ast.FunctionDef) and n.name == name)

class Tests(unittest.TestCase):
    def test_actual_default_off_has_no_import_or_file_effect(self):
        spec = importlib.util.spec_from_file_location('changed_v6_cpu_only', P)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        before = set(sys.modules)
        self.assertIsNone(module.prepare('/NO_SUCH_FILE', 'bad'))
        self.assertIsNone(module.run('/NO_SUCH_FILE', 'bad', 'main'))
        self.assertEqual(before, set(sys.modules))
    def test_exact_same_physical_loop_and_NAV_only_health(self):
        old, new = tree(OLD), tree(P)
        for name in ['phase_health']:
            self.assertEqual(ast.dump(function(old, name)), ast.dump(function(new, name)))
        def physical_loop(root):
            return next(n for n in ast.walk(root) if isinstance(n, ast.While)
                        and 'measure_task_steps' in ast.unparse(n.test))
        self.assertEqual(ast.dump(physical_loop(old)), ast.dump(physical_loop(new)))
    def test_partial_handles_recovered_before_original_sealed_cleanup(self):
        source = P.read_text()
        self.assertIn('if runtime is None:runtime=partial.runtime', source)
        self.assertIn('if observer is None:observer=partial.observer', source)
        self.assertLess(source.index('if runtime is None:runtime=partial.runtime'), source.index('budget.begin_finalization()'))
        self.assertIn("entry_sha256=freeze['files'][str(Path(native_entry.__file__))]", source)
        self.assertIn("usage_known=partial_usage['usage_known']", source)
        self.assertIn('runtime is partial.runtime and observer is partial.observer', source)
    def test_real_original_lease_and_watch_preserved_not_replaced_by_timing(self):
        source = P.read_text()
        self.assertEqual(source.count('make_timed_scope_probe(lease,budget'), 1)
        self.assertIn('PerGpuLease(physical_index=0,authority_check=authority).__enter__()', source)
        self.assertIn('ResourceWatch(probe,state=state,token=object(),fast_health=phase_health).start()', source)
        self.assertIn('data_resource_watch_callbacks(watch,epoch=', source)
        self.assertNotIn('make_scope_probe(', source)
        self.assertIn('diagnostic_only_not_owner_freshness=True', source)
        self.assertIn("'timed_probe','partial_constructor'", source)

if __name__ == '__main__':
    unittest.main()
