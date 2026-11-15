"""Explicit startup namespace fixtures, not native source execution or physics."""
import contextlib
from pathlib import Path
import sys
import tempfile
from types import ModuleType,SimpleNamespace
import unittest
from unittest.mock import patch
from . import v4_stow_factor as factor
ROOT=Path(__file__).resolve().parents[3]
STALL=ROOT/'owner_snapshot/native-prefix-20261114/inputs/AINav/common-source/mujoco_zyh/stall_stow.py'

class StowFactorTests(unittest.TestCase):
    def fixture(self):
        directory=tempfile.TemporaryDirectory();self.addCleanup(directory.cleanup)
        root=Path(directory.name);modules=[]
        for i,rel in enumerate(('mujoco_zyh/stall_stow.py','ainav/native/current_stall_stow.py')):
            p=root/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(STALL.read_bytes())
            module=ModuleType('_EXPLICIT_STOW_FACTOR_FIXTURE_'+str(i));module.__file__=str(p)
            exec("class ProtectedStow:\n def update(self):\n  return globals().get('_reach_stow_path_choice_at_capture')\n",vars(module))
            sys.modules[module.__name__]=module;self.addCleanup(sys.modules.pop,module.__name__,None);modules.append(module)
        host=SimpleNamespace(source_root=root,r=SimpleNamespace(step_count=0,
            sim=SimpleNamespace(data=SimpleNamespace(time=0.),queue=[])))
        return host,modules
    def test_A_C_E_default_OFF_and_original_guard_identity_registration(self):
        for arm in ('A','C','E'):
            with self.subTest(arm=arm):
                host,modules=self.fixture();events=[]
                with patch.object(factor,'bind_to_host',side_effect=AssertionError('OFF must never invoke optimizer binder')):
                    out=factor.install_v4_stow_factor(host,arm=arm,emit=events.append)
                self.assertEqual(out['installed_optimization_callbacks'],0)
                self.assertEqual(len(host._stow_installed),2)
                self.assertTrue(all(v is None for v in host._stow_installed.values()))
                self.assertTrue(all(factor.CALLBACK not in vars(m)for m in modules))
                self.assertFalse(host.common_choice_records)
    def test_A_C_E_cannot_force_enable_even_before_source_inspection(self):
        for arm in ('A','C','E'):
            with self.assertRaises(ValueError):factor.install_v4_stow_factor(None,arm=arm,enabled=True,emit=lambda r:None)
    def test_B_D_also_default_OFF_until_explicit_qualified_component_opt_in(self):
        for arm in ('B','D'):
            host,_=self.fixture();out=factor.install_v4_stow_factor(host,arm=arm,emit=lambda r:None)
            self.assertFalse(out['preparation_component_enabled'])
    def test_B_D_opt_in_uses_existing_kernel_but_does_not_claim_full_method(self):
        for arm in ('B','D'):
            host,modules=self.fixture();events=[]
            def fixture_bind(host,module,*,enabled,emit):
                self.assertIs(enabled,True);vars(module)[factor.CALLBACK]=lambda *a:None
                return dict(installed=True,status='EXPLICIT_BINDER_FIXTURE_NOT_NATIVE',execution_authorized=False)
            with patch.object(factor,'bind_to_host',side_effect=fixture_bind)as bind:
                out=factor.install_v4_stow_factor(host,arm=arm,enabled=True,emit=events.append)
            self.assertEqual(bind.call_count,2);self.assertEqual(out['installed_optimization_callbacks'],2)
            self.assertFalse(out['native_or_complete_successor_method_qualified'])
            for module in modules:self.assertIs(host._stow_installed[module.__file__],vars(module)[factor.CALLBACK])
    def test_prior_all_arm_TRUE_callback_is_rejected_not_removed_by_false_bind(self):
        host,modules=self.fixture();sentinel=object();vars(modules[0])[factor.CALLBACK]=sentinel
        with self.assertRaises(ValueError):factor.install_v4_stow_factor(host,arm='E',emit=lambda r:None)
        self.assertIs(vars(modules[0])[factor.CALLBACK],sentinel);self.assertFalse(hasattr(host,'_stow_installed'))
    def test_post_capture_world_or_double_install_cannot_be_rebound(self):
        host,_=self.fixture();host.r.step_count=448;host.r.sim.data.time=2.24
        with self.assertRaises(ValueError):factor.install_v4_stow_factor(host,arm='A',emit=lambda r:None)
        host.r.step_count=0;host.r.sim.data.time=0.
        factor.install_v4_stow_factor(host,arm='A',emit=lambda r:None)
        with self.assertRaises(ValueError):factor.install_v4_stow_factor(host,arm='D',enabled=True,emit=lambda r:None)
    def test_later_hidden_callback_would_fail_unchanged_native_guard_equality(self):
        host,modules=self.fixture();factor.install_v4_stow_factor(host,arm='E',emit=lambda r:None)
        key=modules[0].__file__;self.assertIs(vars(modules[0]).get(factor.CALLBACK),host._stow_installed[key])
        vars(modules[0])[factor.CALLBACK]=object()
        self.assertIsNot(vars(modules[0]).get(factor.CALLBACK),host._stow_installed[key])
    def test_second_alias_source_drift_fails_before_first_alias_install(self):
        host,modules=self.fixture();p=Path(modules[1].__file__);p.write_bytes(p.read_bytes()+b'\n# DRIFT\n')
        with patch.object(factor,'bind_to_host',side_effect=AssertionError('No partial installation')):
            with self.assertRaises(ValueError):factor.install_v4_stow_factor(host,arm='B',enabled=True,emit=lambda r:None)
        self.assertTrue(all(factor.CALLBACK not in vars(m)for m in modules))

if __name__=='__main__':unittest.main()
