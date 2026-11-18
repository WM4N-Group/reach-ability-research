"""Zero-only acceptance handshake at an original successful background probe.

No extra probe, weaker freshness test, RX change exemption, or timer extension.
A failed retirement invalidates zero; normal main uses the unchanged watcher.
"""
from threading import Event


def zero_watch_class(base):
    class ZeroTerminalWatch(base):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.retire_requested = Event()
            self.retired_after_probe = Event()

        def probe_once(self):
            n = self.probe_calls
            super().probe_once()
            # Only an actual, completed original probe may ACK. No new clock or
            # stamp overrides, and the first synchronous probe is never retired.
            if self.thread is not None and self.retire_requested.is_set() and self.probe_calls == n + 1:
                self.stop.set()  # Existing loop won't start another callback.
                self.retired_after_probe.set()

        def retire_for_zero(self):
            # Refuse if the current original observation/health isn't valid.
            self.check(self.token)
            oldest = self.last_observation_stamp[0]
            deadline = oldest + self.max_stale
            requested = self.clock()
            self.retire_requested.set()
            # At most the REMAINING age of the last original observation.
            if not self.retired_after_probe.wait(max(0., deadline - self.clock())):
                self.state.fail('Zero retirement missing actual successful probe before original oldest deadline')
            finished = self.clock()
            if finished > deadline:
                self.state.fail('Zero retirement did not finish within original oldest deadline')
            self.check(self.token)
            pair = self.last_observation_stamp
            if pair[0] <= oldest or not self.stop.is_set():
                self.state.fail('Zero retirement missing newer original observation and stop ACK')
            return dict(requested_monotonic_s=requested, old_oldest_monotonic_s=oldest,
                        original_deadline_monotonic_s=deadline, observed_ack_monotonic_s=finished,
                        original_last_pair=list(pair), successful_original_probe_ack=True)
    return ZeroTerminalWatch
