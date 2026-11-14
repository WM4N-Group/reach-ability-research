"""Single native option execution with causal receipts and explicit handoff.

Opt-in building block, not wired to collect/physics admission yet. Each factory
must create exactly ONE native task. No next-skill table or task-success predicate
exists here. The unchanged runtime owns all stepping and its original queue.
"""
from collections import deque
import hashlib
from .behavior_authority import NativeReceipt


def array_sha(value):
    return hashlib.sha256(str((value.shape, str(value.dtype))).encode() + value.tobytes()).hexdigest()


def world_snapshot(runtime):
    sim = runtime.sim
    return (float(sim.data.time), array_sha(sim.data.qpos), array_sha(sim.data.qvel),
            id(sim.queue), tuple(array_sha(x) for x in sim.queue))


class NativeOptionSession:
    """Wrap an actual native Machine with a single caller-chosen task."""
    def __init__(self, runtime, machine, *, refresh=lambda: None, original_goal=None,
                 make_exit=None, soft_failure=(), check_guards=lambda: None):
        if len(machine.tasks) != 1:
            raise ValueError('Native behavior session must contain exactly one selected task')
        self.runtime, self.machine = runtime, machine
        self.refresh = refresh
        self.original_goal = original_goal
        self.goal_sha = array_sha(original_goal()) if original_goal else None
        self.make_exit = make_exit
        self.soft_failure = soft_failure
        self.check_guards = check_guards
        self.exit = None
        self.failure = None
        self.entered = False
        self.last_two = deque([runtime.last.position.copy(), runtime.last.position.copy()], maxlen=2)

    def sync(self):
        self.machine.r.last = self.runtime.last
        if hasattr(self.runtime, 'step_count'):
            self.machine.r.step_count = self.runtime.step_count
        self.refresh()
        if self.original_goal and array_sha(self.original_goal()) != self.goal_sha:
            raise RuntimeError('Original PUSH goal changed inside an attempt')

    def enter(self):
        if self.entered:
            raise RuntimeError('Native option can only enter once')
        before = world_snapshot(self.runtime)
        self.sync()
        self.machine.enter()
        if world_snapshot(self.runtime) != before:
            raise RuntimeError('Native entry changed physical state or motor queue')
        self.entered = True

    def request_exit(self):
        if (self.make_exit is None or self.exit is not None
                or getattr(self.machine, 'finish', None) is not None):
            raise RuntimeError('Protected exit unavailable or native Finish already owns the arm')
        before = world_snapshot(self.runtime)
        self.sync()
        self.exit = self.make_exit(list(self.last_two))
        if world_snapshot(self.runtime) != before:
            raise RuntimeError('Protected exit construction changed world or queue')

    def update(self):
        self.sync()
        if self.exit is not None:
            self.exit.update()
        elif self.failure is None:
            try:
                self.machine.update()
            except self.soft_failure as exc:
                self.failure = str(exc)
        self.check_guards()

    def command(self):
        self.sync()
        if self.failure is not None and self.exit is None:
            raise RuntimeError('Failed PUSH requires protected handling before another physical command')
        return self.exit.command() if self.exit is not None else self.machine.next_command()

    def after_step(self):
        self.sync()
        self.last_two.append(self.runtime.last.position.copy())
        if self.exit is not None:
            self.exit.after_step()
        else:
            self.machine.after_step()
        self.check_guards()

    @property
    def outcome(self):
        if self.exit is not None:
            return 'protected_exit_complete' if self.exit.complete else 'running'
        if self.failure is not None:
            return 'failed'
        return 'succeeded' if self.machine.complete else 'running'


class NativeOptionExecutor:
    """Adapter between BehaviorAuthority and the actual 200Hz runtime loop.

    start() only admits/installs an option. First-command receipts are produced
    by record_issued() AFTER the runtime actually advanced physics with that
    command. Interval expiry keeps the same native owner pending replanning;
    switching a running owner is prohibited except explicit protected PUSH exit.
    """
    def __init__(self, runtime, factory, journal):
        self.runtime, self.factory, self.journal = runtime, factory, journal
        self.session = None
        self.option = None
        self.first_command_time = None
        self.previous_tick = None
        self.pending = []
        self.reported_end = False
        self.last_outcome = None
        self.sessions = []  # retain old native histories and per-attempt targets
        self.attempt_sessions = {}
        self.fatal = False

    def receipt(self, status, now, evidence):
        return NativeReceipt(self.option.sha256, now, status,
                             array_sha(self.runtime.last.array()), evidence)

    def start(self, option, decision_id, now):
        if self.fatal:
            raise RuntimeError('Native hard stop permanently revokes task dispatch authority')
        if abs(now - float(self.runtime.sim.data.time)) > 1e-7:
            raise ValueError('Option must be installed at the actual current physics clock')
        if self.pending:
            raise RuntimeError('Actual native receipts must be consumed before another decision')
        if self.option is not None and not self.reported_end:
            raise RuntimeError('Cannot replace an active interval before a native boundary')
        before = world_snapshot(self.runtime)
        continuing = (self.session is not None and self.option is not None
                      and self.last_outcome == 'budget_expired'
                      and (option.skill, option.target_ref, option.attempt_id,
                           option.original_push_goal_sha256) ==
                          (self.option.skill, self.option.target_ref, self.option.attempt_id,
                           self.option.original_push_goal_sha256)
                      and tuple((k, v) for k, v in option.parameters if k != 'requested_interval_s') ==
                          tuple((k, v) for k, v in self.option.parameters if k != 'requested_interval_s'))
        exiting = (self.session is not None and self.option is not None
                   and option.skill in ('EXIT_PUSH', 'RECOVER')
                   and self.option.skill == 'PUSH'
                   and option.target_ref == self.option.target_ref
                   and option.attempt_id == self.option.attempt_id
                   and option.original_push_goal_sha256 == self.option.original_push_goal_sha256
                   and self.last_outcome in ('budget_expired', 'failed'))
        if self.last_outcome == 'failed' and not exiting:
            raise RuntimeError('Failed native owner requires its bound protected exit')
        if exiting:
            self.session.request_exit()
        elif continuing:
            pass  # retains the SAME controller, goal, actor and actual histories
        else:
            if self.session is not None and self.session.outcome == 'running':
                raise RuntimeError('Running native owner needs continuation or protected exit')
            if option.skill in ('EXIT_PUSH', 'RECOVER'):
                raise RuntimeError('Exit/recovery must bind the actual active PUSH attempt')
            if option.attempt_id and option.attempt_id in self.attempt_sessions:
                raise RuntimeError('Retired attempt cannot be reconstructed or reset')
            session = self.factory(option)
            if not isinstance(session, NativeOptionSession):
                raise ValueError('Factory must return an exact single-task native session')
            session.enter()
            self.session = session
            self.sessions.append(session)
            if option.attempt_id:
                self.attempt_sessions[option.attempt_id] = session
        if world_snapshot(self.runtime) != before:
            raise RuntimeError('Option admission modified physical state or motor queue')
        self.option = option
        self.first_command_time = None
        self.reported_end = False
        self.last_outcome = None
        receipt = self.receipt('admitted', now, 'native-option-installed:' + decision_id)
        self.journal(dict(event='native_option_installed', decision_id=decision_id,
                          option_sha256=option.sha256, continuing_same_native_owner=continuing,
                          protected_exit=exiting, physical_command_already_issued=False,
                          source_is_single_task=True))
        return receipt

    def update(self):
        if self.session is None:
            raise RuntimeError('No model-selected native option installed')
        try:
            self.session.update()
        except Exception:
            self.pending.append(self.receipt('hard_stop', float(self.runtime.sim.data.time),
                                             'native-update-hard-stop'))
            self.reported_end = True
            self.last_outcome = 'hard_stop'
            self.fatal = True
            raise
        if self.first_command_time is not None and not self.reported_end:
            status = self.session.outcome
            if status != 'running':
                self.pending.append(self.receipt(status, float(self.runtime.sim.data.time),
                                                 'observed-native-option-outcome'))
                self.reported_end = True
                self.last_outcome = status

    def next_command(self):
        if self.session is None or self.reported_end:
            raise RuntimeError('A new explicit behavior decision is required before more physics')
        return self.session.command()

    def record_issued(self, issued, physical_tick, now, evidence_ref):
        sim = self.runtime.sim
        if (self.option is None or self.reported_end or not evidence_ref
                or abs(now - float(sim.data.time)) > 1e-7
                or abs(now - physical_tick * .005) > 1e-7
                or (self.previous_tick is not None and physical_tick != self.previous_tick + 1)
                or array_sha(issued) != array_sha(self.runtime.last.array())):
            raise ValueError('Consecutive actual issued command/current physics clock receipt required')
        self.previous_tick = physical_tick
        try:
            self.session.after_step()  # actual native collision/Finish checks remain mandatory
        except Exception:
            self.pending.append(self.receipt('hard_stop', now, evidence_ref))
            self.reported_end = True
            self.last_outcome = 'hard_stop'
            self.fatal = True
            raise
        if self.first_command_time is None:
            self.first_command_time = now
            self.pending.append(self.receipt('started', now, evidence_ref))
        status = self.session.outcome
        if status != 'running':
            self.pending.append(self.receipt(status, now, evidence_ref))
            self.reported_end = True
            self.last_outcome = status
        elif now + 1e-7 >= self.first_command_time + self.option.budget_s:
            self.pending.append(self.receipt('budget_expired', now, evidence_ref))
            self.reported_end = True
            self.last_outcome = 'budget_expired'

    def receipts(self):
        result, self.pending = self.pending, []
        return result


def compile_option_push_machine(bundle, *, approach_xy, surface_height_m, compact_arm):
    """Pinned entry-reference adaptation; source algorithms/guards unchanged.

    Combines the previously separate compact-arm and elevated-entry adapters.
    Only software reference targets and the declared arm-ready target change.
    No native calibration/constructor/actor inference occurs in this function.
    """
    from pathlib import Path
    from types import ModuleType
    import math
    import sys
    from .resume_nav import NAV_ARM
    root = Path(bundle) / 'switch'
    entry_original = (root / 'push_entry.py').read_text()
    machine_original = (root / 'machine.py').read_text()
    if (len(approach_xy) != 2 or not all(math.isfinite(x) for x in approach_xy)
            or surface_height_m not in (0., .4) or type(compact_arm) is not bool):
        raise ValueError('Registered ground/high-deck approach reference required')
    entry = entry_original
    machine = machine_original
    changes = [
        ('entry', 'self.base_goal=np.array([-.08,runtime.box_y,self.reference[\'height\']])',
         "self.base_goal=np.array([_wm_approach[0],_wm_approach[1],self.reference['height']+_wm_surface])"),
        ('machine', '            from push_entry import PushEntry',
         '            PushEntry = _wm_option_entry')]
    if compact_arm:
        changes += [
            ('entry', 'and np.max(abs(p.data.qpos[p.qids[12:]]))<.08)',
             'and np.max(abs(p.data.qpos[p.qids[12:]]-_wm_NAV_ARM))<.04)'),
            ('entry', '        anchors=self.anchors.copy()',
             '        arm.position[12:]=_wm_NAV_ARM\n        anchors=self.anchors.copy()'),
            ('machine', 'np.max(abs(p.data.qpos[p.qids[12:]]))>.12',
             'np.max(abs(p.data.qpos[p.qids[12:]]-_wm_NAV_ARM))>.04')]
    for where, old, new in changes:
        text = entry if where == 'entry' else machine
        if text.count(old) != 1:
            raise ValueError('Pinned single-option native entry hook mismatch: ' + old)
        text = text.replace(old, new, 1)
        if where == 'entry':
            entry = text
        else:
            machine = text
    restored_entry, restored_machine = entry, machine
    for where, old, new in reversed(changes):
        if where == 'entry':
            restored_entry = restored_entry.replace(new, old, 1)
        else:
            restored_machine = restored_machine.replace(new, old, 1)
    if (restored_entry, restored_machine) != (entry_original, machine_original):
        raise ValueError('Native source hook inverse mismatch')
    module_id = hashlib.sha256(repr((approach_xy, surface_height_m, compact_arm)).encode()).hexdigest()[:12]
    ep = ModuleType('_wm_behavior_entry_' + module_id)
    ep.__file__ = str(root / 'push_entry.py')
    ep.__dict__.update(_wm_approach=tuple(approach_xy), _wm_surface=surface_height_m, _wm_NAV_ARM=NAV_ARM)
    sys.modules[ep.__name__] = ep
    exec(compile(entry, ep.__file__ + '[behavior-reference]', 'exec'), ep.__dict__)
    mp = ModuleType('_wm_behavior_machine_' + module_id)
    mp.__file__ = str(root / 'machine.py')
    mp.__dict__.update(_wm_option_entry=ep.PushEntry, _wm_NAV_ARM=NAV_ARM)
    sys.modules[mp.__name__] = mp
    exec(compile(machine, mp.__file__ + '[single-option]', 'exec'), mp.__dict__)
    receipt = dict(entry_original_sha256=hashlib.sha256(entry_original.encode()).hexdigest(),
                   machine_original_sha256=hashlib.sha256(machine_original.encode()).hexdigest(),
                   entry_adapted_sha256=hashlib.sha256(entry.encode()).hexdigest(),
                   machine_adapted_sha256=hashlib.sha256(machine.encode()).hexdigest(),
                   inverse_restores_exact_original=True, only_declared_reference_hooks=True,
                   approach_xy=list(approach_xy), surface_height_m=surface_height_m,
                   compact_arm=compact_arm, task_success_or_next_skill_added=False,
                   physics_steps=0, actors_forwarded=0)
    return mp.Machine, receipt


def movement_session(runtime, option, *, surface, extra_guards):
    """Construct one real NAV/CLIMB task from the selected public parameters.

    The native module must already be loaded by the frozen runtime constructor.
    Compact-arm NAV after recovery still needs its dedicated protected primitive;
    the original entry gate is retained here and will reject an unsuitable arm.
    """
    import machine
    from .integrated_course import prepared_machine
    if option.skill not in ('NAV', 'CLIMB'):
        raise ValueError('Only explicit movement choices accepted')
    params = dict(option.parameters)
    required = {'goal_world_x_m', 'goal_world_y_m', 'surface_height_m'}
    if not required <= set(params):
        raise ValueError('Explicit declared approach and surface reference required')
    goal = [params['goal_world_x_m'], params['goal_world_y_m']]
    if option.skill == 'NAV':
        task = dict(skill='nav', goal=goal, surface_height=params['surface_height_m'])
    else:
        if surface not in ('B', 'HIGH', 'C'):
            raise ValueError('Registered explicit climb target surface required')
        task = dict(skill='climb', surface=surface, approach=goal)
    cls = prepared_machine(machine.Machine)
    return NativeOptionSession(runtime, cls(runtime, [task]), check_guards=extra_guards)


def selected_push_session(runtime, bundle, option, *, view, binding_receipt, extra_guards):
    """Execute a prebound selected-object attempt with chosen original distance.

    `view` must be prepared before candidate selection, with a prospective cfg and
    measured immutable goal. Only the chosen view is entered. The caller retains
    all unused/retired binding provenance and checks source/query freshness.
    """
    import numpy as np
    from types import SimpleNamespace, MethodType
    from initial_contact_progress_monitor import (ContactProgressConfig,
        ContactProgressSample, InitialContactProgressMonitor)
    from .integrated_course import weak_flags, PushSurfaceView
    from .resume_nav import NAV_ARM
    from .stall_stow import ProtectedStow, SoftStall
    from .failure_capsules import emit
    params = dict(option.parameters)
    if option.skill != 'PUSH' or not {'goal_world_x_m', 'goal_world_y_m', 'surface_height_m', 'push_distance_m'} <= set(params):
        raise ValueError('Explicit PUSH attempt/approach/distance required')
    original_goal = lambda: view.box_push_target.detach().cpu().numpy()
    if (array_sha(original_goal()) != option.original_push_goal_sha256
            or abs(view.cfg.push_distance - params['push_distance_m']) > 1e-8
            or view.controller.env is not view.target_context
            or view.controller.env.cfg is not view.cfg
            or view.data is not runtime.sim.data or view.queue is not runtime.sim.queue
            or binding_receipt.get('controller_env_is_explicit_context') is not True):
        raise ValueError('Chosen attempt must match actual target, controller cfg and shared world/FIFO')
    surface = params['surface_height_m']
    approach = [params['goal_world_x_m'], params['goal_world_y_m']]
    arm = view.data.qpos[view.qids[12:]]
    compact = bool(np.max(abs(arm - NAV_ARM)) < .04)
    cls, hook = compile_option_push_machine(bundle, approach_xy=approach,
                                            surface_height_m=surface, compact_arm=compact)
    proxy = SimpleNamespace(**vars(runtime))
    proxy.sim = view
    proxy.box_y = approach[1]
    proxy.last = runtime.last
    if surface:
        proxy.push = PushSurfaceView(runtime.push, surface)
    proxy.push_enter = MethodType(type(runtime).push_enter, proxy)
    terrain = runtime.staircase
    class AttemptTerrain:
        def __getattr__(self, key):
            return getattr(terrain, key)
        def push_ready(self, sim, native_settled):
            # Full-task docking is a planning/postcondition check. A deliberately
            # shorter native attempt may finish without completing that task.
            return bool(native_settled)
    proxy.staircase = AttemptTerrain()
    native_termination = view.termination
    raw_flags = lambda: weak_flags(view, runtime.push['bridge'].box_push,
                                   native_termination, runtime.push['model'].EFFORT)
    progress = InitialContactProgressMonitor(ContactProgressConfig(window_s=.06))
    state = dict(machine=None, tick=0)
    def termination():
        flags = raw_flags()
        machine = state['machine']
        if machine is None or machine.phase == 'prepare' or machine.finish is not None:
            return flags
        box = runtime.push['bridge'].box_push
        bad = [k for k, v in flags.items() if k != 'box_settled' and v]
        legal = bool(box.hand_contact(view, view.hand_cfg)[0])
        near = bool(np.linalg.norm(view.data.xpos[view.box_id, :2] - original_goal()[0, :2]) < .12)
        decision = progress.observe(ContactProgressSample(state['tick'], float(view.data.time),
            True, bool(view.controller.motion_ready[0]), legal, True,
            float(view.data.xpos[view.box_id, 0]), near, bool(flags['box_settled']), bool(bad)))
        state['tick'] += 1
        if decision.new_soft_abort_request:
            emit(runtime, 'behavior_PUSH_contact_progress_failed', view=view,
                 extra=dict(attempt_id=option.attempt_id,
                            original_goal=original_goal().tolist(),
                            contact_window_s=decision.elapsed_contact_s,
                            dx_m=decision.observed_forward_dx_m), preserve_primary_failure=True)
            raise SoftStall('behavior_PUSH_original_contact_progress_failed')
        return flags
    view.termination = termination
    machine = cls(proxy, [dict(skill='push', approach=approach)])
    state['machine'] = machine
    def refresh():
        view.target_context._env.common_step_counter = runtime.step_count
        view.refresh()
    def guards():
        flags = raw_flags()
        bad = [k for k, v in flags.items() if k != 'box_settled' and v]
        if bad:
            raise RuntimeError('behavior_selected_PUSH_native_guard:' + ','.join(bad))
        extra_guards()
    session = NativeOptionSession(runtime, machine, refresh=refresh,
        original_goal=original_goal,
        make_exit=lambda refs: ProtectedStow(proxy, refs, compact_goal=NAV_ARM),
        soft_failure=(SoftStall,), check_guards=guards)
    session.binding_receipt = binding_receipt
    session.native_hook_receipt = hook
    session.full_task_docking_not_inferred_from_attempt_success = True
    return session


def compact_nav_session(runtime, option, *, completed_prefix, root, extra_guards):
    """Reuse the actual protected resume-NAV primitive as ONE selected option.

    The previous protected PUSH owner and its retired history are reused. It
    performs original arm transfer, loaded capture, NAV actor and arrival capture;
    it does not create a new PUSH attempt or choose a successor after arrival.
    """
    import numpy as np
    from types import MethodType
    from .resume_nav import ResumeNavRouter
    from .integrated_course import compact_hold_command
    if option.skill != 'NAV':
        raise ValueError('Explicit NAV choice required')
    params = dict(option.parameters)
    if not {'goal_world_x_m', 'goal_world_y_m', 'surface_height_m'} <= set(params):
        raise ValueError('Declared public goal and support height required')
    owner = completed_prefix.r
    if owner.sim.data is not runtime.sim.data or owner.sim.queue is not runtime.sim.queue:
        raise ValueError('Completed protected owner must share the unchanged physical world/FIFO')
    before = world_snapshot(runtime)
    nav = ResumeNavRouter(owner, completed_prefix.native, root, completed_prefix=completed_prefix)
    goal = [params['goal_world_x_m'], params['goal_world_y_m']]
    nav.registered_goal_xy = np.asarray(goal, dtype=float)
    nav.declared_surface_height_m = params['surface_height_m']
    nav.wm_original_next_command = nav.next_command
    nav.next_command = MethodType(compact_hold_command, nav)
    class SingleCompactNav:
        def __init__(self):
            self.r = owner
            self.tasks = [dict(skill='nav', goal=goal, surface_height=params['surface_height_m'])]
            self.finish = None
            self.entered = False
        @property
        def complete(self):
            return nav.complete
        def enter(self):
            if self.entered:
                raise RuntimeError('Compact NAV selected option cannot re-enter')
            self.entered = True
        def update(self):
            nav.update()
        def next_command(self):
            return nav.next_command()
        def after_step(self):
            nav.after_step()
    def refresh():
        if owner.sim is not runtime.sim:
            owner.sim.target_context._env.common_step_counter = runtime.step_count
            owner.sim.refresh()
    session = NativeOptionSession(runtime, SingleCompactNav(), refresh=refresh,
        original_goal=lambda: owner.sim.box_push_target.detach().cpu().numpy(),
        check_guards=extra_guards)
    session.resume_nav = nav
    session.reused_completed_prefix = completed_prefix
    if world_snapshot(runtime) != before:
        raise RuntimeError('Protected compact NAV installation changed physical state or queue')
    return session
