"""NEW bounded software-clock checks only. No lease, GPU, Runtime or physics.

argv[1] is the actual immutable original policy directory, not a fixture that
pretends to own a GPU. The old guard is exercised on synthetic scheduling only.
"""
from pathlib import Path
import ast
import hashlib
import importlib.util
import sys
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ORIGINAL = Path(sys.argv[1]).resolve(strict=True)
sys.argv[1:] = []
sys.path.insert(0, str(ORIGINAL))
from scoped_io import StopState, PolicyStop


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


old = load('_cadence_actual_old', ORIGINAL / 'resource_watch.py')
new = load('_cadence_future_only', HERE / 'resource_watch.py')


class Clock:
    def __init__(self):
        self.now = 0.

    def __call__(self):
        return self.now


class Event:
    def __init__(self, clock, delays):
        self.clock = clock
        self.delays = list(delays)
        self.waits = []
        self.stopped = False

    def wait(self, seconds):
        if self.stopped or not self.delays:
            return True
        assert seconds >= 0
        self.waits.append(seconds)
        self.clock.now += seconds + self.delays.pop(0)
        return False

    def set(self):
        self.stopped = True


class Thread:
    def __init__(self, *, target, **kwargs):
        self.target = target

    def start(self):
        pass  # Explicit deterministic software scheduler, not a native thread.

    def join(self, timeout):
        pass

    def is_alive(self):
        return False


def fixture(module, durations, delays, hook=None):
    clock, state, starts = Clock(), StopState(), []
    remaining = list(durations)
    watch = None

    def probe():
        starts.append(clock())
        clock.now += remaining.pop(0)
        if len(starts) > 1 and hook:
            hook(watch)
        return True

    watch = module.ResourceWatch(probe, state=state, token=object(), clock=clock)
    event = Event(clock, delays)
    watch.stop = event
    with patch.object(module.threading, 'Thread', Thread):
        watch.start()
    watch.thread.target()
    return watch, clock, starts, event


class StartCadenceTests(unittest.TestCase):
    def test_same_measured_durations_are_only_a_software_schedule_counterexample(self):
        # Values read from the new main. This is NOT replay of its hardware or
        # proof that a different native schedule would have passed.
        durations = [.424352388, .754078956]
        hook = lambda w: w()  # synthetic concurrent pre-issue check before publish
        original, _, old_starts, _ = fixture(old, durations, [0.], hook)
        candidate, _, starts, event = fixture(new, durations, [0.], hook)
        self.assertIsNotNone(original.state.reason)
        self.assertIn('oldest observation stale', original.state.reason)
        self.assertAlmostEqual(old_starts[1], 1.424352388)
        self.assertIsNone(candidate.state.reason)
        self.assertEqual(starts, [0., 1.])
        self.assertAlmostEqual(event.waits[0], .575647612)
        self.assertEqual(candidate.probe_calls, 2)
        self.assertEqual(candidate.last_observation_stamp[0], 1.)
        self.assertAlmostEqual(candidate.last_observation_stamp[1], 1.754078956)

    def test_late_wake_anchors_next_deadline_to_actual_start_not_backlog(self):
        watch, _, starts, _ = fixture(new, [.1, .2, .1], [.5, 0.])
        self.assertEqual(starts, [0., 1.5, 2.5])
        self.assertIsNone(watch.state.reason)
        self.assertEqual(watch.probe_calls, 3)

    def test_slow_but_under_two_second_probes_remain_serial_without_catchup(self):
        watch, _, starts, event = fixture(new, [1.2, 1.2, 1.2], [0., 0.])
        self.assertEqual(starts, [0., 1.2, 2.4])
        self.assertEqual(event.waits, [0., 0.])
        self.assertIsNone(watch.state.reason)
        self.assertEqual(watch.probe_calls, 3)

    def test_oldest_staleness_is_still_fatal_and_never_refreshed_from_completed(self):
        watch, clock, _, _ = fixture(new, [.2], [])
        pair = watch.last_observation_stamp
        clock.now = pair[0] + 2.000001
        with self.assertRaises(PolicyStop):
            watch()
        self.assertEqual(watch.last_observation_stamp, pair)
        with self.assertRaises(PolicyStop):
            watch.probe_once()
        self.assertEqual(watch.probe_calls, 1)

    def test_overage_and_unknown_probe_failures_cannot_be_retried(self):
        clock, state = Clock(), StopState()
        def slow():
            clock.now += 2.095707215
        watch = new.ResourceWatch(slow, state=state, token=object(), clock=clock)
        with self.assertRaises(PolicyStop):
            watch.start()
        self.assertIsNone(watch.last_observation_stamp)
        self.assertIsNone(watch.thread)
        with self.assertRaises(PolicyStop):
            watch.probe_once()
        self.assertEqual(clock.now, 2.095707215)
        clock, state = Clock(), StopState()
        def fail(watch):
            raise OSError('synthetic unknown read')
        watch, _, starts, _ = fixture(new, [.1, .1], [0., 0.], fail)
        self.assertEqual(starts, [0., 1.])
        self.assertIn('External resource/owner/disk probe failed', watch.state.reason)
        self.assertEqual(watch.probe_calls, 1)

    def test_only_start_method_changed_all_safety_and_pair_code_identical(self):
        original = (ORIGINAL / 'resource_watch.py').read_bytes()
        self.assertEqual(hashlib.sha256(original).hexdigest(),
                         '8cd57028cc4d195e130662832239467b44028894dc6cd1d6784f9ac6d53f57af')
        before, after = ast.parse(original), ast.parse((HERE/'resource_watch.py').read_bytes())
        for tree in (before, after):
            cls = next(n for n in tree.body if isinstance(n, ast.ClassDef))
            cls.body = [n for n in cls.body if not isinstance(n, ast.FunctionDef) or n.name != 'start']
        self.assertEqual(ast.dump(before, include_attributes=False), ast.dump(after, include_attributes=False))


if __name__ == '__main__':
    unittest.main()
