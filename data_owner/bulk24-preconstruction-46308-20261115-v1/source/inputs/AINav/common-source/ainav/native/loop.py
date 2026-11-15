"""Explicit 200Hz step bridge over the shared native executor.

Native construction, real observation/candidate binding and original physical
monitor are injected from the frozen scene host, not invented by this loop.
Planning pauses simulated time/FIFO; this is NOT a real-robot realtime claim.
"""
from .behavior_authority import NativeReceipt
from ..authority import AinavAuthority
from ..contracts import DecisionBatch, ProtectionRequest


class AinavLoop:
    def __init__(self, *, runtime, executor, planner, batch_provider, snapshot,
                 command_writer, after_step_guard, journal, physical_tick=0):
        if type(physical_tick) is not int or physical_tick < 0:
            raise ValueError('Actual native physical tick required')
        self.runtime, self.executor = runtime, executor
        self.authority = AinavAuthority(planner, executor, journal)
        self.batch_provider, self.snapshot = batch_provider, snapshot
        self.command_writer, self.guard, self.journal = command_writer, after_step_guard, journal
        self.physical_tick, self.stopped = physical_tick, False
        self._update_session = None
        self._next_native_update_tick = None
        self._clock()

    def _clock(self):
        value = float(self.runtime.sim.data.time)
        if abs(value - self.physical_tick * .005) > 1e-7 or value != value:
            raise ValueError('Original native 200Hz clock must match actual physical tick')
        return value

    def _receipts(self):
        for receipt in self.executor.receipts():
            if not isinstance(receipt, NativeReceipt):
                raise ValueError('Only shared actual native receipts allowed')
            self.authority.observe(receipt)

    def _decide(self):
        before = self.snapshot(self.runtime)
        batch = self.batch_provider(self._clock())
        if not isinstance(batch, (DecisionBatch, ProtectionRequest)):
            raise ValueError('Typed task batch or actual native-only safety request required')
        query_time_s = batch.time_s if isinstance(batch, ProtectionRequest) else batch.observation.time_s
        if query_time_s != self._clock():
            raise ValueError('Current actual observation and native-admitted batch required')
        if self.snapshot(self.runtime) != before:
            raise RuntimeError('Observation/admission modified world or motor FIFO')
        self.authority.decide(batch)
        if self.snapshot(self.runtime) != before:
            raise RuntimeError('Planning/installation modified world or motor FIFO')

    def _guard(self):
        if self.guard() is False:
            raise RuntimeError('Original native guard rejected current state')

    def step_one(self):
        if self.stopped:
            raise RuntimeError('Stopped chain cannot be resumed or silently fall back')
        try:
            self._clock()
            self._receipts()
            new = self.authority.active is None
            if new:
                self._decide()
            # The original controller's 20ms clock starts at this actual
            # session's entry tick, not the episode tick%4. A continuation
            # retains its owner and MUST NOT reset this update phase.
            controller_owner=(id(self.executor.session),id(getattr(self.executor.session,'exit',None)))
            if self._update_session != controller_owner:
                self._update_session = controller_owner
                self._next_native_update_tick = self.physical_tick
            if self.physical_tick == self._next_native_update_tick:
                self.executor.update()
                self._next_native_update_tick += 4
                self._receipts()
            if self.authority.active is None:
                return False
            command = self.executor.next_command()
            issued = command.array().copy()
            before = self._clock()
            try:
                self.runtime.step(command)
            finally:
                after = float(self.runtime.sim.data.time)
                if after > before:
                    if abs(after-before-.005) > 1e-7:
                        raise RuntimeError('Runtime advanced more than one original physical tick')
                    self.physical_tick += 1
                    recorded = False
                    try:
                        ref = self.command_writer(issued, self.physical_tick, after)
                        if not isinstance(ref, str) or not ref:
                            raise ValueError('Actual command writer must return primary evidence')
                        recorded = True
                        self.executor.record_issued(issued, self.physical_tick, after, ref)
                    finally:
                        try:
                            if not recorded:
                                self.executor.session.after_step()
                        finally:
                            self._guard()
                    self._receipts()
            if float(self.runtime.sim.data.time) == before:
                raise RuntimeError('No actual physical step was issued')
            return True
        except Exception as error:
            self.stopped = self.authority.blocked = self.executor.fatal = True
            self.journal(dict(event='ainav_chain_hard_stop', error=str(error),
                              actual_physical_tick=self.physical_tick, automatic_retry=False,
                              fixed_route_fallback=False, task_success_inferred=False,
                              native_safety_handling_required=True))
            raise

    def observe_goal(self, monitor):
        if self.stopped:
            raise RuntimeError('Stopped chain cannot claim task success')
        before = self.snapshot(self.runtime)
        value = monitor(self.runtime)
        if self.snapshot(self.runtime) != before:
            self.stopped = self.authority.blocked = self.executor.fatal = True
            raise RuntimeError('Read-only original goal monitor modified physical state')
        if not isinstance(value, dict) or type(value.get('passed')) is not bool:
            raise ValueError('Actual original physical endpoint result required')
        self.journal(dict(event='original_physical_endpoint_observed', result=value,
                          full_course_audit_still_required=True))
        return value
