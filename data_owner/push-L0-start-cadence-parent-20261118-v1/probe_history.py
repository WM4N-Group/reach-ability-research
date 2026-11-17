"""Bounded diagnostic timings around ONE original probe, never owner authority.

No hardware imports, thread creation, resource queries or IO. Actual native use
must explicitly enable; injected clocks are software fixtures, not live stamps.
"""
from collections import deque
import math
import threading
import time


class ProbeHistory:
    def __init__(self, *, enabled=False, limit=128, clock=time.monotonic):
        if type(enabled) is not bool or type(limit) is not int or not 1 <= limit <= 128 or not callable(clock):
            raise ValueError('Explicit bounded metadata policy')
        self.enabled = enabled
        self.limit, self.clock = limit, clock
        self.rows = deque(maxlen=limit)
        self.lock = threading.RLock()
        self.count = self.errors = 0
        self.max_wall = self.max_start_gap = self.max_previous_start_to_completion = 0.
        self.previous_start = None
        self.recording_failure = None

    def call(self, original):
        if not self.enabled:
            raise RuntimeError('Probe metadata wrapper disabled; callback not invoked')
        before = self.clock()
        error = None
        try:
            return original()  # Exactly one original real composite, never duplicate/retry.
        except BaseException as exc:
            error = type(exc).__name__
            raise
        finally:
            try:
                self._record(before, self.clock(), error)
            except BaseException as exc:
                self.recording_failure = type(exc).__name__
                if error is None:
                    raise  # Metadata failure on success must stop, not silently resync.
                # Preserve original primary failure; snapshot explicitly shows metadata failure.

    def _record(self, before, after, error):
        if not all(type(v) in (int, float) and math.isfinite(v) for v in (before, after)) or not 0 <= before <= after:
            raise ValueError('Unknown/backwards actual diagnostic clock')
        with self.lock:
            if self.previous_start is not None and before < self.previous_start:
                raise ValueError('Diagnostic call ordering changed')
            self.count += 1
            self.errors += int(error is not None)
            self.max_wall = max(self.max_wall, after-before)
            if self.previous_start is not None:
                self.max_start_gap = max(self.max_start_gap, before-self.previous_start)
                self.max_previous_start_to_completion = max(self.max_previous_start_to_completion, after-self.previous_start)
            self.rows.append(dict(attempt=self.count, started=before, completed=after,
                                  wall_s=after-before, error_type=error))
            self.previous_start = before

    def snapshot(self):
        with self.lock:
            return dict(schema='data-bounded-actual-probe-body-timing-v1', enabled=self.enabled,
                        observed_attempts=self.count, observed_errors=self.errors,
                        tail_limit=self.limit, tail=[dict(row) for row in self.rows],
                        max_body_wall_s=self.max_wall,
                        max_body_start_gap_s=self.max_start_gap,
                        max_previous_body_start_to_current_complete_s=self.max_previous_start_to_completion,
                        recording_failure=self.recording_failure,
                        diagnostic_only_not_ResourceWatch_oldest_completed_pair=True,
                        never_used_to_refresh_owner_or_admit_commands=True,
                        callback_calls_per_attempt=1, output_is_private_not_model_input=True)
