"""Pinned native READY handoff/session factory; no model, cost or task router."""
from pathlib import Path
from types import SimpleNamespace, MappingProxyType
from dataclasses import replace
from .session_factory import BehaviorSessionFactory
from .course_tools import NotAdmitted, nav_backend, movement_entry, far_bank_entry
class MovementNAVReadyMachine:
    """Retain the SAME native NAV owner until its original READY handoff.

    Machine.update already commands zero WBC velocity after native NAV arrival.
    Keep executing that unmodified native branch through the regular recorded
    loop instead of reporting success while the next Machine cannot activate.
    No new task, successor, motor command, pose snap or relaxed gate is added.
    """

    def __init__(self, machine, runtime, journal):
        self.native_machine, self.runtime, self.journal = (machine, runtime, journal)
        self.arrival_time_s = None

    def __getattr__(self, name):
        return getattr(self.native_machine, name)

    def update(self):
        self.native_machine.update()
        if self.native_machine.complete and self.arrival_time_s is None:
            self.arrival_time_s = float(self.runtime.sim.data.time)
            self.journal(dict(event='native_NAV_arrival_retained_for_READY_handoff', time_s=self.arrival_time_s, model_input=False, same_original_machine=True, original_zero_velocity_branch=True, automatic_next_skill=False, success_receipt_not_yet_assumed=True))

    @property
    def complete(self):
        if not self.native_machine.complete:
            return False
        try:
            movement_entry(self.runtime)
        except NotAdmitted:
            return False
        return True

class CourseSessionFactory:
    """Real PUSH resolver plus original movement/compact-NAV/FarBankStop calls.

    Extra dispatch paths are sealed BEFORE planning, not constructed to test an
    entry gate. The native entry callback must be a read-only predicate returning
    an evidence reference or None; software prebinding is NOT native admission.
    """

    def __init__(self, *, runtime, bundle, resolver, api, integrated, monitor, prefix, root, references, guards):
        self.runtime, self.api, self.integrated, self.monitor = (runtime, api, integrated, monitor)
        self.prefix, self.root, self.guards = (prefix, Path(root), guards)
        self.references = MappingProxyType({r.ref: r for r in references})
        if len(self.references) != len(references):
            raise ValueError('Distinct public reference identities required')
        for ref in references:
            bid = int(runtime.sim.model.body(ref.body_name).id)
            if ref.body_name == 'world' and bid != 0:
                raise ValueError('Static public map must use actual worldbody ID 0')
        self.push = BehaviorSessionFactory(runtime, bundle, resolver, guards, native_api=api)
        self.executor = None
        self.options, self.world = ((), None)
        self.used = set()
        self.nav_count = 0
        self.private_provenance = []
        self.retained_protected_owners = []

    def _completed_compact_owner(self):
        """Read-only eligibility: original stow OR an actual succeeded NAV arrival.

        ResumeNavRouter legitimately clears its input recovery.complete while
        transferring authority. Do not forge it back to True or construct a new
        A owner; use the existing, actually verified ProtectedStow arrival.
        """
        if self.prefix.r is not self.runtime:
            raise NotAdmitted('Original protected owner belongs to another world')
        if self.prefix.complete:
            return self.prefix.recovery
        previous = self.executor.session if self.executor is not None else None
        nav = getattr(previous, 'resume_nav', None)
        arrival = getattr(nav, 'arrival', None)
        if self.executor is None or self.executor.last_outcome != 'succeeded' or nav is None or (nav.r is not self.runtime) or (nav.prefix is not self.prefix) or (not nav.complete) or (not isinstance(arrival, self.monitor.stall.ProtectedStow)) or (arrival.r is not self.runtime) or (arrival.s is not self.runtime.sim) or (not arrival.complete) or (arrival.retired_history_sha != self.monitor.retired_history):
            raise NotAdmitted('Actual completed protected NAV arrival owner required')
        self.monitor.check_a()
        proof = arrival.report()
        if not (proof['stow_verified'] and proof['original_goal_preserved'] and proof['retired_PUSH_history_preserved']):
            raise NotAdmitted('Actual arrival must preserve original A goal/history and all stow guards')
        return arrival

    def bind_query(self, query_sha, options):
        self.options, self.world = ((), None)
        options = tuple(options)
        pushes = tuple((o for o in options if o.skill == 'PUSH' and o.attempt_id not in (self.executor.attempt_sessions if self.executor else {})))
        if pushes:
            self.push.bind_query(query_sha, pushes)
        self.options, self.world = (options, self.api.world_snapshot(self.runtime))

    def __call__(self, option):
        if not any((option is o for o in self.options)) or option.sha256 in self.used or self.world != self.api.world_snapshot(self.runtime):
            raise NotAdmitted('Exact same-query prebound option and unchanged world/FIFO required')
        self.monitor.check_a()
        self.used.add(option.sha256)
        if option.skill == 'PUSH':
            return self.push(option)
        ref = self.references.get(option.target_ref)
        if ref is None:
            raise NotAdmitted('Movement/HOLD requires a declared public task-map reference')
        params = dict(option.parameters)
        if params.get('surface_height_m') != ref.action_surface_height(option.skill):
            raise NotAdmitted('Selected surface differs from the public reference')
        expected_keys = {'goal_world_x_m', 'goal_world_y_m', 'surface_height_m'} if option.skill == 'NAV' else {'surface_height_m'}
        if set(params) - {'requested_interval_s'} != expected_keys:
            raise NotAdmitted('Only backend-effective declared parameters are supported')
        if option.skill == 'HOLD':
            if not ref.far_bank:
                raise NotAdmitted('No general ground HOLD backend exists')
            far_bank_entry(self.runtime, self.monitor.config, self.integrated)
            previous = self.executor.session
            if previous is None:
                raise NotAdmitted('FarBankStop requires an actual existing native guard owner')
            stop = self.integrated.FarBankStop(self.runtime, self.monitor.config)
            runtime = self.runtime

            class HoldMachine:
                r = runtime
                tasks = [dict(skill='hold', surface_height=0.6)]
                finish = None

                @property
                def complete(self):
                    return stop.ready

                def enter(self):
                    pass

                def update(self):
                    stop.update()

                def next_command(self):
                    return stop.command()

                def after_step(self):
                    previous.after_step()
            session = self.api.NativeOptionSession(runtime, HoldMachine(), check_guards=self.guards)
            session.far_bank_stop = stop
            return session
        if option.skill == 'NAV':
            if (params.get('goal_world_x_m'), params.get('goal_world_y_m')) != ref.xy:
                raise NotAdmitted('NAV must use selected public XY, never private approach')
            if nav_backend(self.runtime, ref.surface_height_m) == 'compact_nav':
                completed = self._completed_compact_owner()
                if completed is not self.prefix.recovery:
                    self.retained_protected_owners.append(self.prefix.recovery)
                    self.prefix.recovery = completed
                    self.executor.journal(dict(event='actual_protected_arrival_owner_handoff', time_s=float(self.runtime.sim.data.time), original_A_goal_history_preserved=True, existing_verified_arrival_reused=True, completed_flag_fabricated=False, new_A_owner_constructed=False, model_input=False))
                self.nav_count += 1
                nav_root = self.root / ('compact-nav-%04d' % self.nav_count)
                nav_root.mkdir(exist_ok=False)
                session = self.api.compact_nav_session(self.runtime, option, completed_prefix=self.prefix, root=nav_root, extra_guards=self.guards)
                self.private_provenance.append(dict(mode='actual_A_prefix_compact_nav', prefix_id=id(self.prefix), reference_kind='public_task_map', model_input=False))
                return session
            movement_entry(self.runtime)
            session = self.api.movement_session(self.runtime, option, surface='', extra_guards=self.guards)
            session.machine = MovementNAVReadyMachine(session.machine, self.runtime, self.executor.journal)
            return session
        if option.skill == 'CLIMB' and ref.climb_surface:
            native_option = replace(option, parameters=tuple(sorted((*option.parameters, ('goal_world_x_m', ref.xy[0]), ('goal_world_y_m', ref.xy[1])))))
            from .climb_height import MeasuredClimbHeightMachine
            session=self.api.movement_session(self.runtime, native_option, surface=ref.climb_surface, extra_guards=self.guards)
            session.machine=MeasuredClimbHeightMachine(session.machine,self.executor.journal)
            return session
        raise NotAdmitted('No native backend for selected option')
