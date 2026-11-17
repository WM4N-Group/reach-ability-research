"""New source-delta checks ONLY; no old suites/native/world/Actor models."""
import ast
from contextlib import nullcontext
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace, CodeType, FunctionType
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from actor_trace import ActorTrace, INFER_SHA, instrument_callsite
from standard_runtime import ConstructionReceipt, bounded_exception

SOURCE = Path('/home/yuanyue/main/work/ainav/manifests/three_skill_original_contract_intake_20261117_v1/original-SDK-source/switch/runtime.py')


class SourceDelta(unittest.TestCase):
    def setUp(self):
        self.context = dict(root_skill='PUSH', native_phase='policy', task_step=3, task_sim_s=.015)
        self.trace = ActorTrace(lambda: dict(self.context))
        self.calls = []
        class Tensor:
            def __getitem__(self, value): return self
            def cpu(self): return self
            def numpy(self): return self
        self.tensor = Tensor()
        def actor(tensor):
            self.calls.append(tensor)
            return tensor
        self.actor = actor
        self.trace.bind_runtime(SimpleNamespace(nav_actor=lambda x:x, push_actors=[actor, lambda x:x], climb_actor=lambda x:x))
        class Torch:
            def inference_mode(this):return nullcontext()
            def as_tensor(this, value, *, device):
                if value == 'conversion_error':raise ValueError('before actual Actor')
                return self.tensor
        text = SOURCE.read_text()
        compiled = compile(text, str(SOURCE), 'exec', dont_inherit=True)
        code = next(c for c in compiled.co_consts if isinstance(c, CodeType) and c.co_name == 'infer')
        self.original = FunctionType(code, dict(torch=Torch()), 'infer')
        self.infer = instrument_callsite(self.original, source_path=SOURCE, source_sha256=INFER_SHA,
            function_name='infer', actor_expression='actor', trace=self.trace)

    def test_exact_original_call_order_return_and_failure_boundaries(self):
        self.assertIs(self.infer(self.actor, 'ok', 'cpu'), self.tensor)
        self.assertEqual(self.calls, [self.tensor])
        with self.assertRaises(ValueError):self.infer(self.actor, 'conversion_error', 'cpu')
        self.assertEqual(len(self.calls), 1)
        row = self.trace.snapshot()['phases'][0]
        self.assertEqual((row['attempted'], row['returned'], row['raised']), (1, 1, 0))
        self.assertNotIn('_data_actual_actor_call', self.original.__globals__)
        self.assertFalse(self.trace.snapshot()['coverage_complete'])

    def test_raised_actor_once_and_output_conversion_not_mislabeled(self):
        marker = RuntimeError('actual actor')
        def failing(tensor):
            self.calls.append(tensor)
            raise marker
        self.trace.actors[1] = ('PUSH_leg', failing)
        with self.assertRaises(RuntimeError) as result:self.infer(failing, 'ok', 'cpu')
        self.assertIs(result.exception, marker)
        row = self.trace.snapshot()['phases'][0]
        self.assertEqual((row['attempted'], row['returned'], row['raised']), (1, 0, 1))
        class BadOutput:
            def cpu(self):raise ValueError('after Actor returned')
        def returns_bad(_):return BadOutput()
        self.trace.actors[1] = ('PUSH_leg', returns_bad)
        with self.assertRaises(ValueError):self.infer(returns_bad, 'ok', 'cpu')
        row = self.trace.snapshot()['phases'][0]
        self.assertEqual((row['attempted'], row['returned'], row['raised']), (2, 1, 1))

    def test_bounded_phase_no_silent_drop_and_original_reset_once(self):
        self.trace.max_phase_keys = 1
        self.infer(self.actor, 'ok', 'cpu')
        self.context['native_phase'] = 'stow'
        with self.assertRaises(RuntimeError):self.infer(self.actor, 'ok', 'cpu')
        self.assertEqual(len(self.calls), 1)
        marker = object()
        def reset(instance, value):
            self.calls.append((instance, value));return marker
        self.assertIs(self.trace.reset_call('push_enter', reset, marker, 4), marker)
        self.assertEqual(self.calls[-1], (marker, 4))
        self.assertEqual(self.trace.snapshot()['original_history_initializations']['push_enter']['returned'], 1)

    def test_partial_unknown_independent_counters_and_errno_leaf(self):
        receipt = ConstructionReceipt()
        self.assertIsNone(receipt.usage_snapshot()['task_sim_s'])
        receipt.started = True
        receipt.runtime = SimpleNamespace(sim=SimpleNamespace(data=SimpleNamespace(time=.035)), step_count=7)
        usage = receipt.usage_snapshot()
        self.assertEqual((usage['task_steps'], usage['task_sim_s']), (7, .035))
        self.assertIsNone(usage['auxiliary']);self.assertFalse(usage['usage_known'])
        receipt.runtime.wm_auxiliary_calibration = dict(worlds=1, sim_seconds=6.505)
        self.assertTrue(receipt.usage_snapshot()['usage_known'])
        def leaf(depth):
            if depth:return leaf(depth-1)
            raise BlockingIOError(11, 'PRIVATE TEXT MUST NOT BE STORED')
        try:leaf(20)
        except BaseException as exc:report = bounded_exception(exc)
        self.assertEqual(report['errno'], 11)
        self.assertEqual(report['frames'][-1]['function'], 'leaf')
        self.assertEqual(len(report['frames']), 16)
        self.assertGreater(report['omitted_outer_frames'], 0)
        self.assertNotIn('PRIVATE', str(report))


if __name__ == '__main__':unittest.main()
