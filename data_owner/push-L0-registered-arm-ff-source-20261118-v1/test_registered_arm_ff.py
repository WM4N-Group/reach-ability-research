"""Bounded private-CPU SOFTWARE checks, never MuJoCo/Actor/lease/native prepare.

Usage: python -I -B this_file SDK_ROOT PINNED_STARTUP_SOURCE
No physical integration is implemented here; fake state/clock are explicit.
"""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import resource
import sys
import tempfile
import time
import types
import unittest

STARTED = time.perf_counter()
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('_registered_arm_ff_source_candidate', HERE/'registered_arm_ff.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
SDK, STARTUP = map(Path, sys.argv[1:3])
import numpy as np
from types import SimpleNamespace as NS


class Command:
    def __init__(self, position, velocity, kp, kd, feedforward):
        self.position, self.velocity, self.kp, self.kd, self.feedforward = position, velocity, kp, kd, feedforward

    def array(self):
        return np.stack([self.position, self.velocity, self.kp, self.kd, self.feedforward])


def fixture():
    """Explicit NumPy storage only, not actual SDK/model/data/Robot instances."""
    reference = np.linspace(-.3, .3, 18)
    kp, kd = np.arange(18, dtype=float)+10., np.arange(18, dtype=float)*.01+1.
    module = compile((SDK/'push/bridge.py').read_bytes(), str(SDK/'push/bridge.py'), 'exec', dont_inherit=True)
    cls = next(c for c in module.co_consts if isinstance(c, types.CodeType) and c.co_name == 'PushBridge')
    body = next(c for c in cls.co_consts if isinstance(c, types.CodeType) and c.co_name == 'physics_step')
    physics = types.FunctionType(body, dict(np=np, MotorCommand=Command, KP=kp, KD=kd))
    data = NS(time=0., qpos=np.r_[[-.08, 0., .33], np.zeros(22)], qvel=np.zeros(24),
              qfrc_bias=np.linspace(-2., 2., 24))
    sim = NS(model=NS(opt=NS(timestep=.005)), data=data, queue=[],
             targets=reference.copy(), dids=np.arange(6, 24))
    r = NS(step_count=0, sim=sim, Command=Command,
           push={'model': NS(REFERENCE=reference, KP=kp, KD=kd)})
    args = dict(original_physics_step=physics, bridge_path=SDK/'push/bridge.py',
                push_entry_path=SDK/'switch/push_entry.py', startup_source_path=STARTUP, enabled=True)
    return r, args


def state_bytes(r):
    p = r.sim
    return (r.step_count, p.data.time, p.data.qpos.tobytes(), p.data.qvel.tobytes(),
            p.data.qfrc_bias.tobytes(), p.targets.tobytes(), tuple(p.queue))


class Checks(unittest.TestCase):
    def test_01_disabled_no_numpy_or_source_or_IO(self):
        self.assertIsNone(m.prepare(enabled=False))
        with self.assertRaises(ValueError):
            m.prepare(enabled=1)
        # Module-level imports are stdlib; no runtime/source reads on import.
        tree = ast.parse((HERE/'registered_arm_ff.py').read_bytes())
        imports = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
        self.assertFalse(any('numpy' in ast.unparse(n) for n in imports))

    def test_02_exact_original_expression_only_and_no_state_write(self):
        r, args = fixture()
        f = m.prepare(r, **args)
        before = state_bytes(r)
        command = f(r.sim)
        self.assertEqual(before, state_bytes(r))
        a = command.array()
        np.testing.assert_array_equal(a[0], r.sim.targets)
        np.testing.assert_array_equal(a[1], np.zeros(18))
        np.testing.assert_array_equal(a[2], r.push['model'].KP)
        np.testing.assert_array_equal(a[3], r.push['model'].KD)
        np.testing.assert_array_equal(a[4, :12], np.zeros(12))
        np.testing.assert_array_equal(a[4, 12:], r.sim.data.qfrc_bias[r.sim.dids[12:]])
        self.assertIs(type(command), Command)
        self.assertEqual(f.snapshot()['commands_constructed_not_issued'], 1)
        self.assertFalse(f.snapshot()['execution_permission'])

    def test_03_new_live_sample_no_stale_bias_or_mutable_state_alias(self):
        r, args = fixture()
        f = m.prepare(r, **args)
        one = f(r.sim)
        old = one.feedforward.copy()
        r.sim.data.qfrc_bias += 5.
        two = f(r.sim)
        np.testing.assert_array_equal(one.feedforward, old)
        np.testing.assert_array_equal(two.feedforward[12:], r.sim.data.qfrc_bias[r.sim.dids[12:]])
        before = state_bytes(r)
        for a in (two.position, two.velocity, two.kp, two.kd, two.feedforward):
            a[:] = 17.
        self.assertEqual(before, state_bytes(r))

    def test_04_target_and_gains_must_not_sneak_in_a_second_delta(self):
        for name in ('targets', 'KP', 'KD'):
            r, args = fixture()
            f = m.prepare(r, **args)
            array = r.sim.targets if name == 'targets' else getattr(r.push['model'], name)
            array[0] += .001
            with self.assertRaises(ValueError):
                f(r.sim)
            array[0] -= .001
            with self.assertRaises(ValueError):
                f(r.sim)
            self.assertTrue(f.failed)

    def test_05_nan_and_world_alias_changes_latch(self):
        for change in ('bias', 'world'):
            r, args = fixture()
            f = m.prepare(r, **args)
            if change == 'bias':
                r.sim.data.qfrc_bias[r.sim.dids[-1]] = np.nan
            else:
                r.sim.queue = []
            with self.assertRaises(ValueError):
                f(r.sim)
            self.assertTrue(f.failed)
            self.assertEqual(f.constructed, 0)

    def test_06_not_for_predecessor_nonfresh_FIFO_wrong_dt_or_pose(self):
        for what in ('counter', 'clock', 'fifo', 'pose', 'dt'):
            r, args = fixture()
            if what == 'counter': r.step_count = 1
            if what == 'clock': r.sim.data.time = .005
            if what == 'fifo': r.sim.queue.append('already-issued')
            if what == 'pose': r.sim.data.qpos[0] = -1.
            if what == 'dt': r.sim.model.opt.timestep = .01
            with self.assertRaises(ValueError):
                m.prepare(r, **args)

    def test_07_tampered_or_symlink_sources_rejected(self):
        with tempfile.TemporaryDirectory(prefix='data-arm-FF-CPU-source-') as d:
            d = Path(d)
            for key in ('bridge_path', 'push_entry_path', 'startup_source_path'):
                r, args = fixture()
                original = args[key]
                p = d/(key+'.py')
                p.write_bytes(original.read_bytes()+b'\n# tampered software fixture\n')
                args[key] = p
                with self.assertRaises(ValueError):
                    m.prepare(r, **args)
                p.unlink()
                p.symlink_to(original)
                with self.assertRaises(ValueError):
                    m.prepare(r, **args)

    def test_08_changed_physics_body_rejected_not_just_source_path(self):
        r, args = fixture()
        args['original_physics_step'] = lambda self, command=None: None
        with self.assertRaises(ValueError):
            m.prepare(r, **args)

    def test_09_no_native_modules_and_no_qualification(self):
        r, args = fixture()
        f = m.prepare(r, **args)
        f(r.sim)
        self.assertFalse(f.snapshot()['physical_or_skill_qualification'])
        self.assertFalse(any(k == 'mujoco' or k.startswith(('mujoco.', 'torch', 'ainav.')) for k in sys.modules))
        self.assertEqual((r.step_count, r.sim.data.time, r.sim.queue), (0, 0., []))


if __name__ == '__main__':
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
    print(json.dumps(dict(schema='DATA_REGISTERED_ARM_FF_SOURCE_CPU_ONLY_v1',
        at=__import__('datetime').datetime.now().astimezone().isoformat(),
        tests_run=result.testsRun, failures=len(result.failures), errors=len(result.errors),
        passed=result.wasSuccessful(), no_native_modules=True,
        native_prepare_or_world_or_Actor_or_GPU_or_lease_or_dispatch=False,
        software_wall_s=time.perf_counter()-STARTED,
        process_maxrss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
        tested_sources={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in
          (HERE/'registered_arm_ff.py', HERE/'test_registered_arm_ff.py', STARTUP,
           SDK/'push/bridge.py', SDK/'switch/push_entry.py')}), indent=2))
    raise SystemExit(0 if result.wasSuccessful() else 1)
