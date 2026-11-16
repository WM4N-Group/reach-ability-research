"""AST/default-off fences only; not a native/lease/freeze qualification."""
import ast
import importlib.util
from pathlib import Path
import sys
import unittest
P=Path(__file__).with_name('worker.py');spec=importlib.util.spec_from_file_location('data_new_perf_worker',P)
worker=importlib.util.module_from_spec(spec);spec.loader.exec_module(worker)

class Contract(unittest.TestCase):
    def test_default_off_reads_no_config_creates_no_native(self):
        before=set(sys.modules)
        self.assertIsNone(worker.prepare('/does-not-exist','bad'))
        self.assertIsNone(worker.run('/does-not-exist','bad','main'))
        self.assertEqual(before,set(sys.modules))
    def test_new_question_is_NAV_prefix_not_E_brake_retry(self):
        self.assertIn('FIRST_2000_NAV_COMMANDS',worker.QUESTION)
        self.assertNotIn('PREARRIVAL40',worker.QUESTION)
    def test_no_uncontrolled_output_file_open(self):
        tree=ast.parse(P.read_text())
        calls=[n for n in ast.walk(tree)if isinstance(n,ast.Call)and isinstance(n.func,ast.Attribute)and n.func.attr=='open']
        self.assertEqual(len(calls),1)
        self.assertEqual(ast.unparse(calls[0].func),'budget.open')
    def test_full_runner_includes_actual_bindings_and_no_dummy_health(self):
        tree=ast.parse(P.read_text());calls={ast.unparse(n.func)for n in ast.walk(tree)if isinstance(n,ast.Call)}
        for name in ('FDCapture','make_original_fast_health','make_scope_probe','ResourceWatch','load_private_writer',
            'load_controlled_publisher','bind_fresh_observation_outputs','native_entry.construct_cold_components',
            'e_entry.build_E_driver','FrozenFiles.measure','install','encode_raw_master','budget.begin_finalization',
            'finish_accounting','executable_file_maps','write_json','write_png'):
            self.assertIn(name,calls)
    def test_final_helper_really_reconciles_not_only_renamed_API(self):
        roots=[P.parent.parent/'perf-resource-policy-20261116-v1',P.parent.parent/'policy']
        helper=next(r/'runner_outputs.py'for r in roots if(r/'runner_outputs.py').exists())
        tree=ast.parse(helper.read_text());fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='finish_accounting')
        calls={ast.unparse(n.func)for n in ast.walk(fn)if isinstance(n,ast.Call)}
        self.assertIn('budget.reconcile',calls)
    def test_no_training_or_state_replay(self):
        tree=ast.parse(P.read_text());calls={ast.unparse(n.func)for n in ast.walk(tree)if isinstance(n,ast.Call)}
        for name in ('torch.load','runtime.restore','mujoco.mj_step','mujoco.mj_forward','subprocess.Popen'):
            self.assertNotIn(name,calls)

if __name__=='__main__':unittest.main()
