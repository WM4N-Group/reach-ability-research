"""Targeted new monotonic-observation checks only; no native/lease/old-suite run."""
import ast
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / 'perf-resource-policy-20261116-v1'
if not (BASE / 'scoped_io.py').is_file():
    BASE = HERE.parent / 'PERF-01-NAV2000-20261116-v1' / 'policy'
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(HERE))
from controlled_process import ControlledProcess, wall_observation_receipt
from scoped_io import ScopeIO, PolicyStop


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


class StripDiagnosticAssignments(ast.NodeTransformer):
    def visit_Assign(self, node):
        if len(node.targets) == 1:
            target = ast.unparse(node.targets[0])
            if target == 'self._wall_timing' or target.startswith('self._wall_timing[') or target == "result['wall_observation']":
                return None
        return self.generic_visit(node)


class Tests(unittest.TestCase):
    def budget(self, root, cap=1 << 20):
        return ScopeIO(root, cap_bytes=cap, reserve_bytes=1024, max_open=4, text_buffer_bytes=256)

    def child(self, budget, code):
        return ControlledProcess([sys.executable, '-I', '-B', '-c', code], budget,
                                 stdout_path='stdout', stderr_path='stderr', enabled=True)

    def assert_observation(self, receipt):
        wall = receipt['wall_observation']
        s = wall['stamps']
        self.assertLessEqual(s['capture_enter'], s['spawn_begin'])
        self.assertLessEqual(s['spawn_begin'], s['spawn_returned'])
        self.assertLessEqual(s['spawn_returned'], s['finish_enter'])
        self.assertLessEqual(s['finish_enter'], s['reap_observed'])
        self.assertLessEqual(s['reap_observed'], s['drain_join_begin'])
        self.assertLessEqual(s['drain_join_begin'], s['drain_join_end'])
        self.assertLessEqual(s['drain_join_end'], s['receipt_sample'])
        self.assertAlmostEqual(wall['capture_enter_to_receipt_sample_wall_s'],
                               s['receipt_sample'] - s['capture_enter'])
        self.assertFalse(wall['includes_parent_preflight'])
        self.assertFalse(wall['includes_later_parent_receipt_write'])
        self.assertFalse(wall['exact_exec_start_or_exit_time'])
        self.assertFalse(wall['exclusive_child_CPU_time'])
        self.assertTrue(wall['diagnostic_only_not_owner_stamp_or_deadline'])

    def test_success_byte_capture_and_child_final_file_write(self):
        with tempfile.TemporaryDirectory(prefix='data-parent-wall-CPU-') as td:
            root = Path(td)
            marker = root / 'child-final-file'
            code = ("import os,time;os.write(1,b'x'*32768);os.write(2,b'e'*12288);"
                    f"open({str(marker)!r},'wb').write(b'final');time.sleep(.02)")
            before = time.monotonic()
            child = self.child(self.budget(root), code)
            # This delay is parent-side work inside the observed child interval.
            time.sleep(.01)
            receipt = child.finish(timeout_s=3.)
            after = time.monotonic()
            self.assertTrue(receipt['complete'])
            self.assertEqual(marker.read_bytes(), b'final')
            self.assertEqual((root/'stdout').read_bytes(), b'x'*32768)
            self.assertEqual((root/'stderr').read_bytes(), b'e'*12288)
            self.assertEqual(receipt['streams']['stdout']['written_bytes'], 32768)
            self.assertLessEqual(receipt['wall_observation']['capture_enter_to_receipt_sample_wall_s'], after-before)
            self.assertIsNotNone(child.process.returncode)
            self.assert_observation(receipt)
            print(json.dumps(dict(role='SYNTHETIC_CPU_CHILD_NOT_NATIVE', receipt=receipt)))

    def test_nonzero_retains_timing_in_failure_receipt(self):
        with tempfile.TemporaryDirectory() as td:
            child = self.child(self.budget(Path(td)), 'raise SystemExit(7)')
            with self.assertRaises(PolicyStop) as caught:
                child.finish(timeout_s=3.)
            receipt = caught.exception.receipt
            self.assertEqual(receipt['returncode'], 7)
            self.assertFalse(receipt['complete'])
            self.assertFalse(receipt['timed_out'])
            self.assert_observation(receipt)

    def test_timeout_remains_failure_and_reaps_only_own_direct_child(self):
        with tempfile.TemporaryDirectory() as td:
            child = self.child(self.budget(Path(td)), 'import time;time.sleep(3.)')
            with self.assertRaises(PolicyStop) as caught:
                child.finish(timeout_s=.04)
            receipt = caught.exception.receipt
            self.assertTrue(receipt['timed_out'])
            self.assertFalse(receipt['complete'])
            self.assertIsNotNone(child.process.returncode)
            self.assert_observation(receipt)

    def test_budget_refusal_still_latches_failure(self):
        with tempfile.TemporaryDirectory() as td:
            budget = self.budget(Path(td), cap=16384)
            child = self.child(budget, "import os;os.write(1,b'x'*65536)")
            with self.assertRaises(PolicyStop) as caught:
                child.finish(timeout_s=3.)
            receipt = caught.exception.receipt
            self.assertFalse(receipt['complete'])
            self.assertGreater(receipt['streams']['stdout']['refused_bytes'], 0)
            self.assertIsNotNone(budget.state.reason)
            self.assertLessEqual((Path(td)/'stdout').stat().st_size, 16384)
            self.assert_observation(receipt)

    def test_default_off_does_not_open_output_or_launch(self):
        with tempfile.TemporaryDirectory() as td:
            budget = self.budget(Path(td))
            with patch('controlled_process.subprocess.Popen') as spawn:
                with self.assertRaises(ValueError):
                    ControlledProcess(['/bin/true'], budget, stdout_path='out', stderr_path='err')
                spawn.assert_not_called()
            self.assertEqual(list(Path(td).iterdir()), [])

    def test_original_capture_deadline_pipe_and_error_AST_unchanged(self):
        base = next(n for n in ast.parse((BASE/'controlled_process.py').read_text()).body if isinstance(n, ast.ClassDef))
        new = next(n for n in ast.parse((HERE/'controlled_process.py').read_text()).body if isinstance(n, ast.ClassDef))
        self.assertEqual(ast.dump(base), ast.dump(StripDiagnosticAssignments().visit(new)))
        # No authority, Runtime or GPU dependencies were added to this helper.
        self.assertNotIn('torch', sys.modules)
        self.assertNotIn('mujoco', sys.modules)

    def test_missing_reap_is_unknown_not_zero_or_completed(self):
        stamps = dict(capture_enter=10., spawn_begin=11., spawn_returned=12., finish_enter=13.,
                      reap_observed=None, drain_join_begin=14., drain_join_end=15., receipt_sample=16.)
        receipt = wall_observation_receipt(stamps)
        self.assertIsNone(receipt['spawn_to_reap_observation_wall_s'])
        self.assertIsNone(receipt['post_reap_to_receipt_sample_wall_s'])
        self.assertEqual(receipt['capture_enter_to_receipt_sample_wall_s'], 6.)
        stamps['receipt_sample'] = 100.
        self.assertEqual(receipt['stamps']['receipt_sample'], 16.)

    def test_finish_second_call_does_not_repeat_or_renew(self):
        with tempfile.TemporaryDirectory() as td:
            child = self.child(self.budget(Path(td)), 'pass')
            receipt = child.finish(timeout_s=3.)
            stamps = dict(child._wall_timing)
            with self.assertRaises(PolicyStop):
                child.finish(timeout_s=3.)
            self.assertEqual(stamps, child._wall_timing)
            self.assert_observation(receipt)

    def test_original_and_candidate_same_bytes_and_status_for_cpu_child(self):
        original = module(BASE/'controlled_process.py', 'unchanged_process_CPU_reference')
        results = []
        for cls in [original.ControlledProcess, ControlledProcess]:
            with tempfile.TemporaryDirectory() as td:
                root = Path(td)
                child = cls([sys.executable, '-I', '-B', '-c', "import os;os.write(1,b'out');os.write(2,b'err')"],
                            self.budget(root), stdout_path='stdout', stderr_path='stderr', enabled=True)
                receipt = child.finish(timeout_s=3.)
                receipt.pop('wall_observation', None)
                results.append((receipt, (root/'stdout').read_bytes(), (root/'stderr').read_bytes()))
        self.assertEqual(results[0], results[1])


if __name__ == '__main__':
    unittest.main(verbosity=2)
