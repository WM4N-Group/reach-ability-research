"""New metadata/integration CPU checks only; no repetition of prior seven checks."""
from pathlib import Path
import ast
import importlib.util
import sys
import unittest

HERE = Path(__file__).resolve().parent
ROOT = Path(sys.argv[1]).resolve(strict=True)
sys.argv[1:] = []
sys.path[:0] = [str(HERE), str(ROOT/'push-original-L0-parent-20261118-v1'),
               str(ROOT/'push-original-L0-entry-20261118-v1'), str(ROOT/'push-standard-parent-20261118-v1')]
from probe_history import ProbeHistory


class Clock:
    def __init__(self):
        self.now = 0.

    def __call__(self):
        return self.now


class NewBoundaries(unittest.TestCase):
    def test_default_off_and_explicit_history_bound(self):
        calls = []
        history = ProbeHistory()
        with self.assertRaises(RuntimeError):
            history.call(lambda: calls.append('must not run'))
        self.assertEqual(calls, [])
        for limit in (0, 129, True):
            with self.assertRaises(ValueError):
                ProbeHistory(enabled=True, limit=limit)

    def test_exactly_one_callback_original_value_error_and_bounded_tail(self):
        clock, calls, marker = Clock(), [], object()
        history = ProbeHistory(enabled=True, limit=2, clock=clock)
        def success():
            calls.append('success')
            clock.now += .2
            return marker
        self.assertIs(history.call(success), marker)
        clock.now = 1.
        error = OSError('synthetic primary; no hardware')
        def fail():
            calls.append('error')
            clock.now += .3
            raise error
        with self.assertRaises(OSError) as caught:
            history.call(fail)
        self.assertIs(caught.exception, error)
        clock.now = 2.
        history.call(success)
        s = history.snapshot()
        self.assertEqual(calls, ['success', 'error', 'success'])
        self.assertEqual(s['observed_attempts'], 3)
        self.assertEqual(s['observed_errors'], 1)
        self.assertEqual([r['attempt'] for r in s['tail']], [2, 3])
        self.assertAlmostEqual(s['max_body_wall_s'], .3)
        self.assertAlmostEqual(s['max_body_start_gap_s'], 1.)
        self.assertAlmostEqual(s['max_previous_body_start_to_current_complete_s'], 1.3)
        self.assertTrue(s['never_used_to_refresh_owner_or_admit_commands'])

    def test_metadata_failure_is_visible_and_cannot_replace_primary_exception(self):
        clock = Clock()
        history = ProbeHistory(enabled=True, clock=clock)
        def backwards():
            clock.now = -1.
        with self.assertRaises(ValueError):
            history.call(backwards)
        self.assertEqual(history.snapshot()['recording_failure'], 'ValueError')
        clock.now = 0.
        error = RuntimeError('synthetic original failure')
        def both_fail():
            clock.now = -1.
            raise error
        with self.assertRaises(RuntimeError) as caught:
            history.call(both_fail)
        self.assertIs(caught.exception, error)
        self.assertEqual(history.snapshot()['recording_failure'], 'ValueError')

    def test_actual_original_probe_body_and_controller_safety_inverse_exact(self):
        old = (ROOT/'push-original-L0-parent-20261118-v1/worker.py').read_text()
        new = (HERE/'worker.py').read_text()
        old_tree, new_tree = ast.parse(old), ast.parse(new)
        old_run = next(n for n in old_tree.body if isinstance(n, ast.FunctionDef) and n.name == 'run')
        new_run = next(n for n in new_tree.body if isinstance(n, ast.FunctionDef) and n.name == 'run')
        find = lambda tree: next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == 'probe')
        old_probe, new_probe = find(old_run), find(new_run)
        original = new_probe.body[0]
        self.assertIsInstance(original, ast.FunctionDef)
        self.assertEqual(original.name, 'original_composite_and_ELF')
        self.assertEqual(ast.dump(ast.Module(body=old_probe.body, type_ignores=[]), include_attributes=False),
                         ast.dump(ast.Module(body=original.body, type_ignores=[]), include_attributes=False))
        self.assertEqual(len(new_probe.body), 2)
        self.assertEqual(ast.unparse(new_probe.body[1]), 'return probe_history.call(original_composite_and_ELF)')
        controller = (HERE/'phase_control.py').read_text()
        for a, b in [
            ('PUSH-L0-resource-start-cadence-20261118-v1', 'PUSH-original-independent-L0-20261118-v1'),
            ('PUSH_L0_RESOURCE_START_CADENCE_AUTHORITY_20261118_v1', 'PUSH_ORIGINAL_INDEPENDENT_L0_AUTHORITY_20261118_v1'),
            ('active_PUSH_L0_resource_start_cadence_20261118_v1_scope', 'active_PUSH_original_independent_L0_20261118_v1_scope'),
            ('ORIGINAL_L0_START_CADENCE_FULL_PROGRAM_ACTUAL_CPU_PREPARE_PASS', 'ORIGINAL_L0_FULL_PROGRAM_ACTUAL_CPU_PREPARE_PASS')]:
            controller = controller.replace(a, b)
        self.assertEqual(controller, (ROOT/'push-original-L0-parent-20261118-v1/phase_control.py').read_text())
        self.assertEqual(sum(isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == 'resource_probe'
                             for n in ast.walk(original)), 1)

    def test_worker_import_and_disabled_prepare_never_import_gpu_or_run_old_scope(self):
        before = set(sys.modules)
        spec = importlib.util.spec_from_file_location('_future_cadence_cpu_worker', HERE/'worker.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertIsNone(module.prepare(enabled=False))
        self.assertFalse({'torch', 'mujoco', 'pynvml', 'OpenGL'} & (set(sys.modules)-before))
        self.assertEqual(module.QUESTION,
                         'PUSH_ORIGINAL_L0_REGISTERED_CASE_WITH_START_ANCHORED_RESOURCE_CADENCE')


if __name__ == '__main__':
    unittest.main()
