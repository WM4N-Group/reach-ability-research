"""Resume NAV from an actually verified stow/arrival, without inventing failure."""
from collections import deque
from .stall_stow import ProtectedStow


class VerifiedStowOwner:
    def __init__(self,runtime,native,stow,last_two,*,reason,original_termination,retained_log_handles=(),abort=None):
        if (not isinstance(stow,ProtectedStow) or not stow.complete or stow.r is not runtime
                or stow.s.data is not runtime.sim.data or stow.s.queue is not runtime.sim.queue):
            raise ValueError('Actual same-world completed protected stow required')
        if not callable(original_termination) or len(last_two)!=2:
            raise ValueError('Actual native hard predicates and two issued references required')
        self.original_termination=original_termination;self.retained_log_handles=tuple(retained_log_handles)
        self.r=runtime;self.native=native;self.recovery=stow;self.last_two=deque([x.copy() for x in last_two],maxlen=2)
        self.reason=reason;self.abort=abort;self.index=0;self.finish=None
    @property
    def complete(self):return self.recovery.complete
    @property
    def phase(self):return self.recovery.phase
    @property
    def kind(self):return 'push'
    @property
    def events(self):return self.recovery.events
    @property
    def results(self):return []
    @property
    def switch_metrics(self):return []
    @property
    def private_log_bytes(self):return sum(f.tell() for f in self.retained_log_handles)
    def update(self):self.recovery.update()
    def next_command(self):return self.recovery.command()
    def after_step(self):self.last_two.append(self.r.last.position.copy());self.recovery.after_step()
    def report(self):return dict(scope='actual verified native handback, no automatic task successor',reason=self.reason,abort=self.abort,recovery=self.recovery.report())
    def close(self):pass
