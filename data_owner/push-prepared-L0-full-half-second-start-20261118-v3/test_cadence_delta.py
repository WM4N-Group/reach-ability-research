"""Two new AST/byte delta checks only; no old fixture suite or native calls."""
import ast
from pathlib import Path
import unittest
P=Path(__file__).resolve().parent;OLD=P.parent/'push-prepared-L0-full-public-geometry-20261118-v2'
class Delta(unittest.TestCase):
    def test_actual_run_and_control_helpers_unchanged(self):
        for name in ['connect_l0.py','l0_witness.py','lease_site_observer.py','metadata_prepare.py','public_geometry_provenance.py','push_l0_driver.py','registered_arm_ff.py']:self.assertEqual((P/name).read_bytes(),(OLD/name).read_bytes())
        run=lambda p:next(n for n in ast.parse(p.read_text()).body if isinstance(n,ast.FunctionDef)and n.name=='run')
        self.assertEqual(ast.dump(run(P/'worker.py'),include_attributes=False),ast.dump(run(OLD/'worker.py'),include_attributes=False))
    def test_explicit_auth_half_s_and_original_two_s(self):
        text=(P/'worker.py').read_text();self.assertIn("c['resource_poll_s']==.5",text);self.assertIn("c['resource_oldest_max_age_s']==2.",text);self.assertIn("auth['resource_poll_s']==.5",text);self.assertIn("auth['resource_oldest_max_age_s']==2",text)
        self.assertIn('ACTUAL_START_NOMINAL_HALF_S',text);self.assertNotIn("c['resource_poll_s']==1.",text)
if __name__=='__main__':unittest.main()
