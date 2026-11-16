"""Unfrozen next-program diagnostics; never supplies an owner/freshness stamp.
Uses exactly one ORIGINAL lease.check(force=True), then disk and reconcile.
No own retry, lease acquisition, extra probe, counter resync, IO or native calls.
"""
from dataclasses import dataclass
import time

@dataclass(frozen=True)
class Attempt:
    started: float
    completed: float
    stages: tuple
    error: str | None

class TimedScopeProbe:
    def __init__(self, lease, budget, min_free_bytes, disk_free):
        if type(min_free_bytes) is not int or min_free_bytes <= 0:
            raise ValueError('Explicit original safety floor required')
        self.lease = lease
        self.budget = budget
        self.min_free_bytes = min_free_bytes
        self.disk_free = disk_free
        self.last_attempt = None

    def __call__(self):
        started = time.monotonic()
        stages = []
        error = None
        def measure(name, action):
            before = time.monotonic()
            try:
                return action()
            finally:
                stages.append((name, before, time.monotonic()))
        try:
            measure('original_held_lease_authority_UUID_GPU_composite',
                    lambda: self.lease.check(force=True))
            free = measure('disk_free', lambda: self.disk_free(self.budget.root))
            if type(free) is not int or free < self.min_free_bytes:
                self.budget.state.fail('Disk free unknown/below safety floor')
            measure('scope_reconcile', self.budget.reconcile)
        except BaseException as exc:
            error = repr(exc)
            raise
        finally:
            # Immutable diagnostic snapshot, never a successful owner observation.
            # ResourceWatch still owns (oldest, completed), age and failure latch.
            self.last_attempt = Attempt(started, time.monotonic(), tuple(stages), error)

def make_timed_scope_probe(lease=None, budget=None, *, min_free_bytes=None,
                          disk_free=None, enabled=False):
    if type(enabled) is not bool:
        raise ValueError('Explicit new-program opt-in')
    if not enabled:
        return None
    return TimedScopeProbe(lease, budget, min_free_bytes, disk_free)
