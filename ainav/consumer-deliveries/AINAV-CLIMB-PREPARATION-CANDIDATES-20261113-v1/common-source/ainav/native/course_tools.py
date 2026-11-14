"""AST-extracted original native safety/session/writer helpers; no model/router.

Source and extraction scope are pinned in manifests/source_imports.json.
"""
from copy import deepcopy
from dataclasses import dataclass, replace
import math
from pathlib import Path
from types import SimpleNamespace, MappingProxyType
from .session_factory import BehaviorSessionFactory
from .behavior_authority import BehaviorOption
class NotAdmitted(ValueError):
    pass
def _array(value):
    return value.detach().cpu().numpy() if hasattr(value, 'detach') else value

@dataclass(frozen=True)
class PublicReference:
    """Task-given coordinates, NOT an image/object association or estimated pose.

    One ref per map entry. B/C CLIMB must name their actual bodies. HIGH/FAR
    are static worldbody references (id 0), explicitly not pixel associations.
    CLIMB XY is a reference only: native prepared_machine overwrites approach.
    """
    ref: str
    xy: tuple
    surface_height_m: float
    evidence_ref: str
    climb_surface: str = ''
    body_name: str = 'world'
    far_bank: bool = False

    def __post_init__(self):
        if not self.ref or not self.evidence_ref or (not isinstance(self.xy, tuple)) or (len(self.xy) != 2) or (not all((type(x) in (int, float) and math.isfinite(x) for x in (*self.xy, self.surface_height_m)))) or (self.climb_surface not in ('', 'B', 'HIGH', 'C')):
            raise ValueError('Explicit finite public map reference required')
        expected = {'B': 'wm_object_middle', 'C': 'wm_object_heavy', 'HIGH': 'world'}
        if self.climb_surface and self.body_name != expected[self.climb_surface]:
            raise ValueError('CLIMB reference must retain actual B/C body or static HIGH worldbody')
        if self.far_bank and (self.surface_height_m != 0.6 or self.body_name != 'world'):
            raise ValueError('Only the declared static .6m far bank has a HOLD backend')

    def action_surface_height(self, skill):
        if skill == 'CLIMB':
            if not self.climb_surface:
                raise NotAdmitted('Registered climb destination required')
            return {'B': 0.2, 'HIGH': 0.4, 'C': 0.6}[self.climb_surface]
        return self.surface_height_m

    def public(self):
        return dict(target_ref=self.ref, xy=list(self.xy), surface_height_m=self.surface_height_m, climb_surface=self.climb_surface, far_bank=self.far_bank, reference_kind='declared_task_map_NOT_image_object_association', evidence_ref=self.evidence_ref)

class CourseMonitor:
    """Private observation-only monitor; endpoint remains the original function."""

    def __init__(self, runtime, config, integrated, stall, prefix, native_api):
        self.r, self.config, self.integrated, self.stall = (runtime, config, integrated, stall)
        self.prefix, self.api = (prefix, native_api)
        self.initial_goal_sha = native_api.array_sha(_array(runtime.sim.box_push_target))
        self.retired_history = None

    def prefix_evidence(self):
        p = self.prefix
        if not p.complete or p.abort is None or p.recovery is None or (p.r is not self.r) or (p.native.r is not self.r):
            raise RuntimeError('Actual original failed A and completed protected stow required')
        report = p.recovery.report()
        if not report['original_goal_preserved'] or not report['retired_PUSH_history_preserved'] or self.stall.history_sha(self.r.sim) != p.recovery.retired_history_sha or (self.api.array_sha(_array(self.r.sim.box_push_target)) != self.initial_goal_sha):
            raise RuntimeError('Original A goal/history was not retained')
        self.retired_history = p.recovery.retired_history_sha
        return dict(abort=deepcopy(p.abort), recovery=report, model_contribution=False, model_input=False)

    def check_a(self):
        if self.retired_history is None or self.stall.history_sha(self.r.sim) != self.retired_history or self.api.array_sha(_array(self.r.sim.box_push_target)) != self.initial_goal_sha:
            raise RuntimeError('Retired original A goal/history changed')

    def observe(self, runtime):
        if runtime is not self.r:
            raise ValueError('Monitor must observe the single original runtime')
        self.check_a()
        out = deepcopy(self.integrated.endpoint(runtime, self.config))
        docks = {}
        for name in ('wm_object_middle', 'wm_object_heavy'):
            view = SimpleNamespace(model=runtime.sim.model, data=runtime.sim.data, box_id=runtime.sim.model.body(name).id)
            docks[name] = runtime.staircase.dock_metrics(view)
        docked = all((-0.01 <= m['gap_m'] <= 0.01 for m in docks.values()))
        return dict(out, passed=bool(out['passed'] and docked), actual_B_C_dock_metrics=docks, actual_B_C_docked=docked, model_input=False, original_A_failed=True, retired_A_history_preserved=True, original_endpoint_passed=out['passed'])

def far_bank_entry(runtime, config, integrated):
    """Private safety-only gate BEFORE FarBankStop raises its foot references.

    Allows its native WBC to land a swinging foot, but never on a near bank or
    bridge: every foot XY must already lie over the real far deck, and measured
    support must be on its .6m surface. Not a model score or a success receipt.
    """
    import numpy as np
    p = runtime.sim
    c, g = (config['integrated_case'], integrated.layout(config['integrated_case']))
    ids = [p.model.body(n + '_foot').id for n in ('FR', 'FL', 'RR', 'RL')]
    xyz, loads = (np.asarray(p.data.xpos[ids]), np.asarray(p.forces[ids, 2]))
    cfg = config['far_bank_stop']
    if cfg['surface_height_m'] != 0.6 or cfg['foot_center_height_m'] != 0.622:
        raise NotAdmitted('Original FarBankStop surface/reference required')
    supported = loads > 3.0
    good = np.isfinite(xyz).all() and np.isfinite(loads).all() and np.all(xyz[:, 0] > g['far_deck_front'] + 0.05) and np.all(abs(xyz[:, 1] - c['lane_y_m']) < c['bank_width_m'] / 2) and (np.count_nonzero(supported) >= 3) and np.all(abs(xyz[supported, 2] - 0.622) < 0.04) and np.all((xyz[:, 2] > 0.582) & (xyz[:, 2] < 0.85))
    if not good:
        raise NotAdmitted('Far-bank HOLD requires actual far-deck footprint and loaded support')
    return True

def movement_entry(runtime):
    """Exact read-only original Machine.activate READY, before model admission.

    Native movement NAV enters directly; CLIMB has its own genuine native
    preparation and is checked there again. Never relax .12/.30/.12 to match
    the looser NAV-arrival thresholds or install an unsafe next owner.
    """
    import numpy as np
    p = runtime.sim
    velocity = np.asarray(p.data.qvel[:3])
    arm = np.asarray(p.data.qpos[p.qids[12:]])
    tilt = float(runtime.n.state()[3])
    if velocity.shape != (3,) or arm.shape != (6,) or (not np.isfinite(velocity).all()) or (not np.isfinite(arm).all()) or (not math.isfinite(tilt)) or (float(np.linalg.norm(velocity)) > 0.12) or (tilt > 0.3) or (float(np.max(abs(arm))) > 0.12):
        raise NotAdmitted('Original movement READY requires speed<=.12, tilt<=.30, abs(arm)<=.12')
    return True

def nav_backend(runtime, surface_height_m):
    """Measured original Machine READY, not a task-stage/surface successor rule.

    Native Machine.activate rejects abs(arm)> .12 (equality is admitted). A
    successful original Finish/Climb Stop verifies arm error < .08 about zero,
    so the old B-top .2 / C-top .6 path is movement_session, NOT compact NAV.
    Shared ResumeNavRouter.begin_nav remains registered for 0/.4 only.
    """
    import numpy as np
    arm = np.asarray(runtime.sim.data.qpos[runtime.sim.qids[12:]])
    if arm.shape != (6,) or not np.isfinite(arm).all():
        raise NotAdmitted('Actual finite six-joint NAV READY measurement required')
    if float(np.max(abs(arm))) <= 0.12:
        return 'movement'
    if surface_height_m in (0.0, 0.4):
        return 'compact_nav'
    raise NotAdmitted('Non-READY arm: original NAV requires abs(arm)<=.12; shared compact NAV supports only 0/.4 surfaces')

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
            return MovementNAVReadyBoundary(session, self.runtime, self.executor.journal)
        if option.skill == 'CLIMB' and ref.climb_surface:
            native_option = replace(option, parameters=tuple(sorted((*option.parameters, ('goal_world_x_m', ref.xy[0]), ('goal_world_y_m', ref.xy[1])))))
            return self.api.movement_session(self.runtime, native_option, surface=ref.climb_surface, extra_guards=self.guards)
        raise NotAdmitted('No native backend for selected option')

class CourseGuardsAndWriter:

    def _snapshot(self, runtime):
        if runtime is not self.r:
            raise RuntimeError('Foreign runtime snapshot')
        p = runtime.sim
        return (self.api.world_snapshot(runtime), id(p), id(p.model), id(p.data), id(p.controller), id(p.box_push_target), self.api.array_sha(p.data.act), self.api.array_sha(p.data.ctrl))

    def _native_guards(self):
        if self.extra_guards() is False:
            raise RuntimeError('Additional native safety predicate rejected')
        current = (self.r.sim, self.r.sim.model, self.r.sim.data, self.r.sim.queue, self.r.sim.controller, self.r.sim.box_push_target)
        if any((a is not b for a, b in zip(current, self._world))):
            raise RuntimeError('Original world/FIFO/A owner identity changed')
        if self.loop is not None:
            self.monitor.check_a()

    def _contact_guard(self):
        import numpy as np
        import mujoco
        p = self.r.sim
        objects = {p.model.body(v['body']).id: k for k, v in self.integrated.IDENTITY.items()}
        option = self.executor.option
        selected = None
        if option is not None and option.skill in ('PUSH', 'RECOVER', 'EXIT_PUSH'):
            view = self.executor.session.machine.r.sim
            selected = view.box_id
        surfaces = getattr(self.r, 'wm_integrated_climbs', set())
        for i, contact in enumerate(p.data.contact):
            a, b = map(int, p.model.geom_bodyid[[contact.geom1, contact.geom2]])
            obj = a if a in objects else b if b in objects else None
            if obj is None:
                continue
            robot = b if obj == a else a
            ancestor = robot
            while ancestor and ancestor != p.base_id:
                ancestor = int(p.model.body_parentid[ancestor])
            if ancestor != p.base_id:
                continue
            force = np.zeros(6)
            mujoco.mj_contactForce(p.model, p.data, i, force)
            if np.linalg.norm(force[:3]) <= 1.0:
                continue
            if self.loop is None and objects[obj] == 'light':
                continue
            if obj == selected:
                continue
            surface = {'middle': 'B', 'heavy': 'C'}.get(objects[obj])
            if surface in surfaces and robot not in self.r.c.forbidden:
                continue
            raise RuntimeError('integrated_unselected_or_native_forbidden_contact:' + objects[obj])

    def _write_boundary(self, row):
        """Keep native renderer fields on EVERY mixed-rate event row.

        control_tick is only the containing 50Hz group. Physical event time and
        physical_tick remain authoritative; this is never a fabricated sample.
        Original renderer uses the actual stage fields for its text overlay.
        """
        now = float(self.r.sim.data.time)
        tick = int(round(now / 0.005))
        if self.loop is None:
            skill = getattr(self.prefix, 'kind', 'startup')
            phase = getattr(self.prefix, 'phase', 'startup')
        else:
            option, session = (self.executor.option, self.executor.session)
            skill = option.skill.lower() if option is not None else 'await_model'
            phase = getattr(session.machine, 'phase', 'await_model') if session is not None else 'await_model'
        fields = dict(control_tick=tick // 4, physical_tick=tick, skill=skill, phase=phase, stage_source='actual_native_owner_not_task_successor')
        fields.update(row)
        self.writer.boundary(fields)

    def _after_guard(self):
        try:
            self._native_guards()
            self._contact_guard()
        except Exception as exc:
            self._write_boundary(dict(time_s=float(self.r.sim.data.time), physical_tick=self.writer.steps, event='course_guard', passed=False, error=str(exc)))
            raise
        self._write_boundary(dict(time_s=float(self.r.sim.data.time), physical_tick=self.writer.steps, event='course_guard', passed=True))

    def _write_command(self, issued, physical_tick, time_s):
        import numpy as np
        p = self.r.sim
        before, q, dq = self._before
        if abs(time_s - before - 0.005) > 1e-07:
            raise RuntimeError('Command writer must see exactly one actual native step')
        delayed = np.stack([p.queue[-1 - int(lag)][:, j] for j, lag in enumerate(p.delays)], axis=1)
        self.writer.append_command(issued=issued, delayed=delayed, torque=p.torque, raw_torque=p.raw_torque, q_before=q, dq_before=dq, physical_tick=physical_tick, time_s=time_s)
        self._last_issued = issued[0].copy()
        return 'commands:physical_tick=%d' % physical_tick
