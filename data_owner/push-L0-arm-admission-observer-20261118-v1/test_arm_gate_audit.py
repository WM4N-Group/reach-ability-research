"""New bounded observer fixtures/AST only: no SDK model/world/Actor/guard replay."""
from pathlib import Path
from types import SimpleNamespace as NS
import ast
import importlib.util
import json
import sys
import unittest
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = Path(sys.argv[1]).resolve(strict=True)
sys.argv[1:] = []
sys.path[:0] = [str(ROOT/'push-original-L0-parent-20261118-v1'),
               str(ROOT/'push-original-L0-entry-20261118-v1'), str(ROOT/'push-standard-parent-20261118-v1')]
spec = importlib.util.spec_from_file_location('_future_arm_gate_audit', HERE/'l0_witness.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
observe = module._current_arm_gate_once


def fixture(*, arm_q=None, reason='', error=None):
    q = np.zeros(18)
    if arm_q is not None:
        q[12:] = arm_q
    data = NS(qpos=q, qvel=np.zeros(18), time=6.505)
    model = NS(jnt_range=np.array([[-1., 1.]]*18), joint=lambda i: NS(name='joint'+str(i)))
    p = NS(data=data, model=model, qids=np.arange(18), dids=np.arange(18), jids=np.arange(18))
    runtime = NS(sim=p, step_count=1301)
    owner = NS(arm_gate_attempts=0, arm_gate_audit=None, witness=None)
    class Guard:
        def __init__(self):
            self.calls = []
        def check(self, arg, **kwargs):
            self.calls.append((arg, kwargs))
            if error is not None:
                raise error
            return reason
    return owner, runtime, Guard()


class ArmGateAuditTests(unittest.TestCase):
    def test_default_off_cannot_call_guard_or_admit(self):
        owner, runtime, guard = fixture()
        for enabled in (False, None, 1):
            with self.assertRaises(ValueError):
                observe(owner, runtime, guard, enabled=enabled)
        self.assertEqual(len(guard.calls), 0)
        self.assertEqual(owner.arm_gate_attempts, 0)

    def test_success_exact_original_argument_flags_and_immutable_private_sample(self):
        owner, runtime, guard = fixture(arm_q=[.01]*6)
        self.assertEqual(observe(owner, runtime, guard, enabled=True), '')
        self.assertEqual(len(guard.calls), 1)
        self.assertIsInstance(guard.calls[0][0], np.ndarray)
        np.testing.assert_array_equal(guard.calls[0][0], runtime.sim.data.qpos[12:])
        self.assertEqual(guard.calls[0][1], dict(allow_hand_contact=False, record=True))
        audit = owner.arm_gate_audit
        self.assertTrue(audit['guard_passed'])
        self.assertEqual(audit['task_step'], 1301)
        self.assertEqual(audit['task_sim_s'], 6.505)
        self.assertFalse(audit['model_input'])
        runtime.sim.data.qpos[12:] = .5
        self.assertEqual(audit['actual_arm_q'], [.01]*6)
        json.dumps(audit, allow_nan=False)

    def test_constructor_refusal_keeps_actual_same_call_joint_reason_on_owner(self):
        owner, runtime, guard = fixture(arm_q=[0., 0., .0016, 0., 0., 0.], reason='arm_joint_limit')
        runtime.sim.model.jnt_range[14] = [-1., 0.]
        def construct():
            reason = observe(owner, runtime, guard, enabled=True)
            module.need(not reason, 'Original L0 geometry/contact/arm gate')
            return object()
        with self.assertRaises(ValueError):
            owner.witness = construct()
        self.assertIsNone(owner.witness)
        self.assertEqual(owner.arm_gate_audit['reason_class'], 'ARM_JOINT_LIMIT')
        self.assertEqual(owner.arm_gate_audit['original_reason_text'], 'arm_joint_limit')
        self.assertEqual(owner.arm_gate_audit['outside_hard_limits_with_1mrad_slack'], [False, False, True, False, False, False])
        self.assertEqual(len(guard.calls), 1)

    def test_geometric_reason_is_original_rounded_return_not_new_distance_query(self):
        owner, runtime, guard = fixture(reason='link2:base_link:0.01234m')
        self.assertEqual(observe(owner, runtime, guard, enabled=True), 'link2:base_link:0.01234m')
        self.assertEqual(owner.arm_gate_audit['original_pair'], ['link2', 'base_link'])
        self.assertEqual(owner.arm_gate_audit['original_returned_distance_rounded_m'], .01234)
        self.assertFalse(owner.arm_gate_audit['guard_passed'])
        self.assertEqual(len(guard.calls), 1)

    def test_original_exception_identity_preserved_without_retry(self):
        error = OSError(11, 'synthetic exception, no native resource touched')
        owner, runtime, guard = fixture(error=error)
        with self.assertRaises(OSError) as got:
            observe(owner, runtime, guard, enabled=True)
        self.assertIs(got.exception, error)
        self.assertEqual(owner.arm_gate_audit['guard_error_type'], 'BlockingIOError')
        self.assertEqual(owner.arm_gate_audit['guard_errno'], 11)
        self.assertIsNone(owner.arm_gate_audit['guard_passed'])
        self.assertEqual(len(guard.calls), 1)

        class BrokenErrno(Exception):
            @property
            def errno(self):
                raise RuntimeError('synthetic metadata property failure')
        primary = BrokenErrno('synthetic primary')
        owner, runtime, guard = fixture(error=primary)
        with self.assertRaises(BrokenErrno) as got:
            observe(owner, runtime, guard, enabled=True)
        self.assertIs(got.exception, primary)
        self.assertIsNone(owner.arm_gate_audit['guard_errno'])
        self.assertEqual(len(guard.calls), 1)

    def test_unknown_reason_and_bad_sample_cannot_create_unobservable_success(self):
        owner, runtime, guard = fixture(reason='untrusted\nnot-a-body-pair')
        self.assertEqual(observe(owner, runtime, guard, enabled=True), 'untrusted\nnot-a-body-pair')
        self.assertIsNone(owner.arm_gate_audit['original_reason_text'])
        self.assertEqual(owner.arm_gate_audit['reason_class'], 'UNRECOGNIZED_NONEMPTY_REASON_HASH_ONLY')
        self.assertEqual(len(owner.arm_gate_audit['original_reason_sha256']), 64)
        owner, runtime, guard = fixture(arm_q=[float('nan')]*6)
        with self.assertRaises(RuntimeError):
            observe(owner, runtime, guard, enabled=True)
        self.assertEqual(len(guard.calls), 1)
        self.assertFalse(owner.arm_gate_audit['sample_complete'])
        json.dumps(owner.arm_gate_audit, allow_nan=False)

    def test_full_original_source_inverse_and_single_call_no_world_writes(self):
        before = ast.parse((ROOT/'push-original-L0-parent-20261118-v1/l0_witness.py').read_bytes())
        after = ast.parse((HERE/'l0_witness.py').read_bytes())
        helper = next(n for n in after.body if isinstance(n, ast.FunctionDef) and n.name == '_current_arm_gate_once')
        calls = [n for n in ast.walk(helper) if isinstance(n, ast.Call)]
        self.assertEqual(sum(isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name)
                             and n.func.value.id == 'collision' and n.func.attr == 'check' for n in calls), 1)
        forbidden = ('physics_step', 'step', 'mj_forward', 'mj_kinematics', 'mj_step', 'MjData', 'MjModel', 'infer')
        self.assertFalse(any((isinstance(n.func, ast.Name) and n.func.id in forbidden) or
                             (isinstance(n.func, ast.Attribute) and n.func.attr in forbidden) for n in calls))
        after.body.remove(helper)
        owner = next(n for n in after.body if isinstance(n, ast.ClassDef) and n.name == 'L0StartupOwner')
        init = next(n for n in owner.body if isinstance(n, ast.FunctionDef) and n.name == '__init__')
        init.body = [n for n in init.body if not (isinstance(n, ast.Assign) and any(
            isinstance(t, ast.Attribute) and t.attr in ('arm_gate_attempts', 'arm_gate_audit') for t in n.targets))]
        report = next(n for n in owner.body if isinstance(n, ast.FunctionDef) and n.name == 'report')
        report.body[0].value.keywords = [k for k in report.body[0].value.keywords if k.arg not in ('arm_gate_attempts','arm_gate_audit')]
        witness = next(n for n in after.body if isinstance(n, ast.ClassDef) and n.name == 'OriginalL0Witness')
        validate = next(n for n in witness.body if isinstance(n, ast.FunctionDef) and n.name == 'validate')
        assignment = next(n for n in validate.body if isinstance(n, ast.Assign) and any(isinstance(t,ast.Name) and t.id=='reason' for t in n.targets))
        oldw = next(n for n in before.body if isinstance(n, ast.ClassDef) and n.name == 'OriginalL0Witness')
        oldv = next(n for n in oldw.body if isinstance(n, ast.FunctionDef) and n.name == 'validate')
        olda = next(n for n in oldv.body if isinstance(n, ast.Assign) and any(isinstance(t,ast.Name) and t.id=='reason' for t in n.targets))
        assignment.value = olda.value
        self.assertEqual(ast.dump(before, include_attributes=False), ast.dump(after, include_attributes=False))
        self.assertFalse({'torch','mujoco','OpenGL','pynvml'} & set(sys.modules))


if __name__ == '__main__':
    unittest.main()
