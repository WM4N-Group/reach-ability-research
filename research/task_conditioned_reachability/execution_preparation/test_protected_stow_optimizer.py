"""Synthetic owner/source-contract tests; no native controller or physics run."""
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import unittest
import ast
import tempfile
from types import ModuleType

from protected_stow_optimizer import transform_stall_source,reference_seconds,choose_protected_path,bind_owned_fork


def owner(q=None,block_direct=False):
    q=np.zeros(6) if q is None else np.asarray(q,float)
    goal=np.array([0.,.18,-.18,0.,0.,0.]);extended=np.array([.3,2.5,-1.3,1.4,-.4,-1.1])
    class Guard:
        def segment(self,start,end):
            return 'synthetic_direct_blocked' if block_direct and np.array_equal(start,q) and np.array_equal(end,goal) else ''
    data=SimpleNamespace(time=10.,qpos=np.r_[np.zeros(7),q],qvel=np.zeros(12))
    sim=SimpleNamespace(data=data,queue=[np.arange(18.)],box_push_target=np.array([[1.7,0.,0.]]))
    return SimpleNamespace(s=sim,reference=q.copy(),velocity=np.zeros(6),compact_goal=goal,
                           phase='UNLOAD_CAPTURE',index=0,native_arrival=None,
                           native=SimpleNamespace(guard=Guard()),waypoints=[extended,goal.copy()])


class ProtectedOptimizerTests(unittest.TestCase):
    def test_original_protected_quintic_time_not_raw_Finish_2point2(self):
        q=np.zeros(6);goal=np.array([0.,2.,0.,0.,0.,0.])
        self.assertEqual(reference_seconds(q,[goal]),[max(.6,1.875*2/.4,(5.78*2/.8)**.5)])
        self.assertEqual(reference_seconds(q,[q]),[.6])

    def test_disabled_arm_preserves_original_path_without_extra_guard_calls(self):
        o=owner();before=[q.copy() for q in o.waypoints]
        o.native.guard.segment=lambda *a: (_ for _ in ()).throw(AssertionError('Must not optimize baseline'))
        out=choose_protected_path(o,np.zeros(6),enabled=False,emit=lambda e:None)
        self.assertFalse(out['changed'])
        for q,w in zip(o.waypoints,before):np.testing.assert_array_equal(q,w)

    def test_selects_same_endpoint_lower_reference_cost_without_mutating_world(self):
        o=owner();before=(o.s.data.qpos.copy(),o.s.data.qvel.copy(),o.s.queue[0].copy(),o.s.box_push_target.copy(),o.reference.copy())
        events=[];r=choose_protected_path(o,np.zeros(6),enabled=True,emit=events.append)
        self.assertTrue(r['changed']);self.assertEqual(len(o.waypoints),1)
        np.testing.assert_array_equal(o.waypoints[-1],o.compact_goal)
        for x,y in zip(before,(o.s.data.qpos,o.s.data.qvel,o.s.queue[0],o.s.box_push_target,o.reference)):np.testing.assert_array_equal(x,y)
        self.assertEqual(len(events),1)
        self.assertFalse(r['complete_F7_upstream_optimization'])

    def test_blocked_shortcut_keeps_original(self):
        o=owner(block_direct=True);r=choose_protected_path(o,np.zeros(6),enabled=True,emit=lambda e:None)
        self.assertFalse(r['changed']);self.assertEqual(len(o.waypoints),2)
        self.assertEqual(r['candidates'][1]['reason'],'synthetic_direct_blocked')

    def test_all_paths_blocked_original_native_failure_remains_not_repaired(self):
        o=owner();o.native.guard.segment=lambda *args:'all_native_paths_blocked'
        r=choose_protected_path(o,np.zeros(6),enabled=True,emit=lambda e:None)
        self.assertFalse(r['changed']);self.assertEqual(r['chosen_mode'],'original')

    def test_snapshot_detects_main_state_or_queue_write_by_bad_evaluator(self):
        for name in ('qpos','queue'):
            o=owner()
            def bad(*args):
                if name=='qpos':o.s.data.qpos[0]+=1.
                else:o.s.queue[0][0]+=1.
                return ''
            o.native.guard.segment=bad
            with self.subTest(name=name),self.assertRaises(RuntimeError):choose_protected_path(o,np.zeros(6),enabled=True,emit=lambda e:None)

    def test_no_optimization_in_arrival_or_mid_segment(self):
        for field,value in [('phase','PROTECTED_STOW'),('index',1),('native_arrival',object())]:
            o=owner();setattr(o,field,value)
            with self.subTest(field=field),self.assertRaises(ValueError):choose_protected_path(o,np.zeros(6),enabled=True,emit=lambda e:None)

    def test_recording_failure_does_not_install_shortcut(self):
        o=owner()
        def fail(e):raise OSError('no evidence storage')
        with self.assertRaises(OSError):choose_protected_path(o,np.zeros(6),enabled=True,emit=fail)
        self.assertEqual(len(o.waypoints),2)

    def test_goal_cannot_be_silently_rewritten(self):
        o=owner();o.waypoints[-1]=np.zeros(6)
        with self.assertRaises(ValueError):choose_protected_path(o,np.zeros(6),enabled=True,emit=lambda e:None)

    def test_exact_frozen_pass_source_hook_is_reversible_and_keeps_native_gates(self):
        root=Path(__file__).resolve().parents[3]
        source=root/'evidence/2026-11-05/phe-old-pass-ablation-plan-v1/frozen-source/stall_stow_v9.py'
        original=source.read_text();changed=transform_stall_source(original)
        self.assertEqual(changed.count('_reach_phe_prepare_path(self, start)'),1)
        self.assertIn('now-self.stable_since>=4.-1e-8',changed)
        self.assertIn('fold_handoff_pending_queue_refused',changed)
        self.assertGreater(changed.index('_reach_phe_prepare_path(self, start)'),changed.index("if not queued['screen_pass']"))


class ForkBindingTests(unittest.TestCase):
    def test_only_new_exact_fork_has_real_bound_caller_no_original_rewrite(self):
        repo=Path(__file__).resolve().parents[3]
        original=(repo/'evidence/2026-11-05/phe-old-pass-ablation-plan-v1/frozen-source/stall_stow_v9.py').read_text()
        changed=transform_stall_source(original)
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);file=root/'stall_stow.py';file.write_text(changed)
            mod=ModuleType('new_owned_stall_fork');mod.__file__=str(file)
            tree=ast.parse(changed);node=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='ProtectedStow')
            exec(compile(ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[])),str(file),'exec'),mod.__dict__)
            r=bind_owned_fork(mod,owned_source_root=root,enabled=False,emit=lambda e:None)
            self.assertTrue(r['hook_bound_to_new_fork'])
            self.assertFalse(mod._reach_phe_prepare_path(None,None)['changed'])
            with self.assertRaises(ValueError):bind_owned_fork(mod,owned_source_root=root,enabled=True,emit=lambda e:None)
            self.assertEqual(file.read_text(),changed)

    def test_unmodified_original_or_source_outside_own_root_rejected(self):
        repo=Path(__file__).resolve().parents[3]
        original=repo/'evidence/2026-11-05/phe-old-pass-ablation-plan-v1/frozen-source/stall_stow_v9.py'
        with tempfile.TemporaryDirectory() as temp:
            mod=ModuleType('original_not_allowed');mod.__file__=str(original)
            with self.assertRaises(ValueError):bind_owned_fork(mod,owned_source_root=temp,enabled=True,emit=lambda e:None)


if __name__=='__main__':unittest.main()
