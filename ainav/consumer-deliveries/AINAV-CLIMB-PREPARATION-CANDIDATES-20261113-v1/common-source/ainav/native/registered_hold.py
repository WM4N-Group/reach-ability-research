"""Explicit duration HOLD of an actual completed native owner, not task success."""
from .registered_nav_factory import RegisteredNavMachine
from .registered_climb import RegisteredClimbMachine


class RegisteredHoldMachine:
    def __init__(self,runtime,source_session,witness,*,hold_s):
        import math
        if source_session.runtime is not runtime or source_session.outcome!='succeeded' or not isinstance(source_session.machine,(RegisteredNavMachine,RegisteredClimbMachine)):
            raise ValueError('Actual completed NAV/CLIMB session required; not a fake HOLD pose')
        if not math.isfinite(hold_s) or not 0<hold_s<=10.:raise ValueError('Explicit bounded native hold duration required')
        witness.validate(runtime);self.source_session=source_session;self.witness=witness;self.runtime=runtime
        self.r=source_session.machine.r;self.hold_s=float(hold_s);self.started=float(runtime.sim.data.time)
        self.actual_steps=0;self.complete=False;self.tasks=[dict(skill='hold')]
    @property
    def phase(self):return 'HOLD_VERIFIED' if self.complete else 'HOLD_NATIVE_OWNER'
    @property
    def results(self):return [dict(skill='hold',successful=True,seconds=float(self.runtime.sim.data.time)-self.started,actual_steps=self.actual_steps)] if self.complete else []
    def enter(self):self.source_session.sync();self.source_session.check_guards()
    def update(self):
        self.source_session.update()
        if self.source_session.outcome!='succeeded':raise RuntimeError('Original native owner lost during HOLD')
    def next_command(self):return self.source_session.command()
    def after_step(self):
        self.source_session.after_step();self.actual_steps+=1
        if self.source_session.outcome!='succeeded':raise RuntimeError('Original native owner lost after actual HOLD command')
        if float(self.runtime.sim.data.time)-self.started>=self.hold_s-1e-8:self.complete=True
    def report(self):return dict(kind='explicit_original_native_owner_hold',complete=self.complete,requested_hold_s=self.hold_s,
        actual_elapsed_s=float(self.runtime.sim.data.time)-self.started,actual_steps=self.actual_steps,source_kind=type(self.source_session.machine).__name__,
        original_owner_and_hard_guards_retained=True,task_goal_or_route_success_not_inferred=True,model_input=False)
