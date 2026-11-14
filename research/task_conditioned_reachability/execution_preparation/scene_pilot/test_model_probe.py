"""CPU source/authority preflight tests, no model import or live simulation."""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('phe_readonly_model_probe',HERE/'model_probe.py');probe=importlib.util.module_from_spec(spec);spec.loader.exec_module(probe)


class ModelProbePreflight(unittest.TestCase):
    def test_native_reference_list_arithmetic_without_importing_torch_or_model(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'model.py';p.write_text('import forbidden_native_runtime\nREFERENCE = np.array([-.1,.8,-1.5]*4+[0.]*6)\n')
            q=probe.reference_from_source(p)
            self.assertEqual(len(q),18);self.assertEqual(q[-6:],[0.]*6)

    def test_reference_parser_rejects_execution(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'model.py';p.write_text("REFERENCE = np.array(__import__('os').system('false'))\n")
            with self.assertRaises(ValueError):probe.reference_from_source(p)

    def test_no_dynamics_renderer_or_actor_calls_in_driver(self):
        tree=ast.parse((HERE/'model_probe.py').read_text())
        prohibited={'mj_step','mj_step1','mj_step2','Renderer','Runtime','Machine','infer','load_actor','MjSpec'}
        found={n.func.attr if isinstance(n.func,ast.Attribute) else n.func.id for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,(ast.Name,ast.Attribute))}
        self.assertFalse(found&prohibited)
        self.assertIn('mj_kinematics',found);self.assertIn('mj_jacSubtreeCom',found)

    def test_once_claim_and_before_after_input_integrity_present(self):
        text=(HERE/'model_probe.py').read_text()
        self.assertIn("CPU-attempt.claim').open('x')",text)
        self.assertEqual(text.count("for name,digest in p['source_inputs'].items()"),1)
        self.assertIn("for source,digest in p['source_inputs'].items()",text)
        self.assertIn("never",text.lower())

    def test_private_FK_has_own_explicit_budget(self):
        text=(HERE/'model_probe.py').read_text()
        self.assertIn("counter>p['max_FK_calls']",text)
        self.assertIn("lp_count>p['max_LP_solves']",text)
        self.assertIn("actual_ground_contact_verified=False",text)


if __name__=='__main__':unittest.main()
