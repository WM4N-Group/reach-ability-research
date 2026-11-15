"""Private necessary NAV-source evidence at an ACTUAL succeeded CLIMB boundary.

Not ActualCapture/Arrival/PushStow, a controller, NAV admission, a support registry
mutation or proof of a full task. It expires at the next physical step. Read only
from original live owners/commands/contacts; no replay/pose/force injection.
"""
from pathlib import Path
import hashlib
import importlib
import math
import sys
from v4_native_asset import require
from elevated_terminal import deck_normal_loads

PINS = {
    'ainav/native/registered_climb.py': 'fed57c56ad2c13ed5541e7af6f2c2cb31f4dcac0b5e8d8feb05383b22ad3e78a',
    'ainav/native/registered_compact_nav.py': 'bd173adeb4d31f651f5d8d5a9c2e37c6129421aa21c39edd09e5e986ac501361',
    'ainav/native/scene_registry.py': '1d5baefee91a46d0b92f72663eff59b49eb7e7cc18754f95ef036458502566bf',
    'ainav/native/push_stow_witness.py': '44771aa0702eb035d19a87b521f4125879389fdd04eef3159b3dde296133325c',
    'mujoco_zyh/native_behavior_executor.py': '8d42281aa890bd5224f7d8c0bacc2c44d1fa1bda0ba5a89fec8bffa59f701995',
}
_SEAL = object()


def support_reference(object_ref, existing_refs):
    require(isinstance(object_ref, str) and object_ref.isidentifier(), 'Original registered object ref')
    ref = 'climb_nav_source__' + object_ref
    require(ref not in existing_refs, 'New private support ref cannot alias an existing object/surface')
    return ref


def source_readiness(surface, *, feet, total_vertical_load_N, selected_contact_normal_N, base_xy, goal_xy=None):
    """Original NAV support predicate plus REAL selected-object normal loads.

    Pure scalars alone never establish provenance or native admission. A fresh
    physical owner/history/guard/limits is also required by the reader below.
    """
    from ainav.native.registered_compact_nav import validate_support_and_goal
    reasons = []
    x0,x1,y0,y1=surface.bounds_xy_m
    require(len(base_xy)==2 and all(type(v)in(int,float)and math.isfinite(v)for v in base_xy), 'Actual finite current base XY')
    if not (x0<base_xy[0]<x1 and y0<base_xy[1]<y1):
        reasons.append('ORIGINAL_NAV_BASE_OUTSIDE_CURRENT_SUPPORT_REGION')
    # Unknown future goal is NOT current base XY. Use a private geometric
    # centre solely to test this rectangle can admit any original goal margin.
    # The selected public goal is still checked by the original factory/ctor.
    checked_goal=((x0+x1)/2,(y0+y1)/2)if goal_xy is None else goal_xy
    try:
        validate_support_and_goal(surface, feet, total_vertical_load_N, checked_goal)
    except ValueError:
        reasons.append('ORIGINAL_NAV_FOUR_FOOT_12N_HEIGHT_FOOTPRINT_OR_GOAL_MARGIN_NOT_READY')
    require(len(selected_contact_normal_N) == 4 and all(type(v) in (int, float)
            and math.isfinite(v) and v >= 0. for v in selected_contact_normal_N),
            'Four finite actual selected-object normal loads required')
    if min(selected_contact_normal_N) < 12.:
        reasons.append('FOUR_FEET_NOT_EACH_12N_ON_ACTUAL_SELECTED_CLIMB_OBJECT')
    return dict(necessary_source_ready=not reasons, reasons=reasons,
                native_NAV_admitted=False, actual_next_NAV_goal_not_selected=goal_xy is None)


def issued_history_gate(*, time_s, tick, first_command_time_s, previous_tick,
                        entered, latest_matches, two_finite_global18_refs):
    require(type(tick) is int and tick >= 2 and type(previous_tick) is int
            and previous_tick == tick and type(time_s) in (int, float)
            and math.isfinite(time_s) and abs(time_s - tick * .005) <= 1e-7,
            'Actual latest original200Hz issued clock required')
    require(type(first_command_time_s) in (int, float) and math.isfinite(first_command_time_s)
            and .005 <= first_command_time_s <= time_s - .005 + 1e-7,
            'At least two real commands from this original CLIMB session, not constructor seeds')
    require(entered is True and latest_matches is True and two_finite_global18_refs is True,
            'Two actual global18 references/latest issued identity, not synthetic cold history')


class ActualClimbNavSourceObservation:
    """Same-tick private sample, intentionally not a recognized NAV witness type."""
    def __init__(self, *, _seal, runtime, session, executor, registry, native_witness,
                 source_root, guard, journal):
        require(_seal is _SEAL, 'Only the guarded live reader can create this observation')
        self.r, self.session, self.executor = runtime, session, executor
        self.registry, self.native_witness = registry, native_witness
        self.source_root, self.guard_callback, self.journal = source_root, guard, journal
        self.observed_tick, self.observed_time = runtime.step_count, float(runtime.sim.data.time)
        self._sample()

    def _sample(self):
        require(self.guard_callback() is not False, 'Actual Data owner/resource guard refused')
        import numpy as np
        import mujoco
        from ainav.native.registered_climb import ActualClimbSupportWitness, RegisteredClimbMachine
        from ainav.native.push_stow_witness import require_live_success_boundary
        from ainav.native.scene_registry import RegisteredTerrain, SurfaceSpec
        from mujoco_zyh import native_behavior_executor as api
        r, session, executor, registry = self.r, self.session, self.executor, self.registry
        require(type(session) is api.NativeOptionSession and type(self.native_witness) is ActualClimbSupportWitness
                and isinstance(session.machine, RegisteredClimbMachine), 'Exact original CLIMB owner/session/witness')
        require_live_success_boundary(r, session, executor)
        require(executor.fatal is False and session.entered is True
                and any(value is session for value in executor.sessions), 'Actually installed entered original CLIMB boundary')
        require(self.native_witness.r is r and self.native_witness.session is session
                and self.native_witness.registry is registry, 'Original CLIMB witness belongs to this live source')
        p, machine = r.sim, session.machine
        require(machine.global_runtime is r and all(getattr(machine.r.sim, key) is getattr(p, key)
                for key in ('model', 'data', 'queue')), 'Exact source root/selected world/FIFO')
        before = api.world_snapshot(r)
        self.native_witness.validate(r)
        native = executor.factory.native_option_for(executor.option)
        binding = machine.binding
        require(executor.option.skill == native.skill == 'CLIMB'
                and binding.option_sha256 == native.sha256 and binding.opaque_ref == native.target_ref
                and binding.object_ref == self.native_witness.support_ref
                and binding.object_ref in registry.objects and binding.object_ref not in registry.retired_objects,
                'Actual selected CLIMB native option/body identity')
        obj = registry.objects[binding.object_ref]
        bid = int(p.model.body(obj.body_name).id)
        gid = int(p.model.geom(obj.body_name + '_geom').id)
        require(obj.body_name == binding.body_name and bid == binding.body_id
                and int(p.model.geom_bodyid[gid]) == bid
                and int(p.model.geom_type[gid]) == int(mujoco.mjtGeom.mjGEOM_BOX),
                'Actual selected movable cuboid body/geom, never a static-deck alias')
        geometry = RegisteredTerrain(registry).surface_geometry(p, obj.ref)
        require(abs(geometry['top'] - self.native_witness.height) <= .01,
                'Original CLIMB selected support height changed')
        require(np.allclose(p.model.geom_size[gid], np.asarray(obj.size_m) / 2, rtol=0, atol=1e-10),
                'Original registered body dimensions unchanged')
        refs = set(registry.objects) | set(registry.surfaces)
        ref = support_reference(obj.ref, refs)
        x0, y, length, width = geometry['front'], geometry['lane_y_m'], geometry['length'], geometry['width']
        surface = SurfaceSpec(ref, obj.body_name + '_geom', (x0, x0 + length, y - width / 2, y + width / 2), geometry['top'])
        last_two = tuple(value.copy() for value in session.last_two)
        valid_refs = len(last_two) == 2 and all(value.shape == (18,) and np.isfinite(value).all() for value in last_two)
        issued_history_gate(time_s=float(p.data.time), tick=r.step_count,
            first_command_time_s=executor.first_command_time, previous_tick=executor.previous_tick,
            entered=session.entered, latest_matches=bool(valid_refs and np.array_equal(last_two[-1], r.last.position)),
            two_finite_global18_refs=bool(valid_refs))
        original_guard = machine.native.guard
        require(isinstance(original_guard, r.push['finish'].CollisionGuard)
                and all(getattr(original_guard.sim, key) is getattr(p, key) for key in ('model', 'data', 'queue')),
                'Actual original same-world native collision guard required')
        reason = original_guard.check(p.data.qpos[p.qids[12:]], allow_hand_contact=False, record=True)
        require(not reason, 'Original CLIMB NAV-source arm geometry not ready')
        # Exact original soft/hard intersection, without writing p.soft_limits,
        # robot state, policy history, gains, force arrays or command/FIFO.
        soft = p.robot.data.soft_joint_pos_limits.numpy()[0][[p.robot.joint_names.index(n) for n in r.push['model'].JOINTS]]
        hard = p.model.jnt_range[p.jids[12:]]
        limits = np.column_stack((np.maximum(hard[:, 0], soft[12:, 0]), np.minimum(hard[:, 1], soft[12:, 1])))
        require(limits.shape == (6, 2) and np.isfinite(limits).all() and np.all(limits[:, 0] < limits[:, 1]),
                'Original finite nonempty six-joint soft/hard limits')
        feet = [int(p.model.body(n + '_foot').id) for n in ('FR', 'FL', 'RR', 'RL')]
        require(len(set(feet)) == 4, 'Four exact compiled foot bodies')
        mapping = {g: feet.index(int(p.model.geom_bodyid[g])) for g in range(p.model.ngeom) if int(p.model.geom_bodyid[g]) in feet}
        contacts = []
        for i in range(p.data.ncon):
            contact = p.data.contact[i]
            if gid not in (int(contact.geom1), int(contact.geom2)):
                continue
            force = np.zeros(6)
            mujoco.mj_contactForce(p.model, p.data, i, force)
            contacts.append((int(contact.geom1), int(contact.geom2), [float(v) for v in contact.frame[:3]], float(force[0])))
        loads = deck_normal_loads(mapping, gid, contacts)
        metrics = source_readiness(surface, feet=p.data.xpos[feet].tolist(), total_vertical_load_N=p.forces[feet, 2].tolist(),
            selected_contact_normal_N=loads, base_xy=p.data.qpos[:2].tolist())
        require(api.world_snapshot(r) == before, 'Source observation changed actual world/FIFO')
        self.surface, self.actual_object_ref = surface, obj.ref
        self.last_two, self.original_guard, self.original_limits = last_two, original_guard, limits
        self.selected_contact_normal_N, self.metrics = tuple(loads), metrics
        self.original_option_sha256, self.original_geometry = native.sha256, geometry
        self._world = (p.model, p.data, p.queue)

    def validate_same_tick(self, runtime):
        require(runtime is self.r and runtime.step_count == self.observed_tick
                and float(runtime.sim.data.time) == self.observed_time
                and all(a is b for a, b in zip(self._world, (runtime.sim.model, runtime.sim.data, runtime.sim.queue))),
                'Same-tick source sample expired; not an active NAV/hold ownership transfer')
        self._sample()
        return self.metrics['necessary_source_ready']

    def report(self):
        return dict(kind='actual_CLIMB_stopped_boundary_NAV_source_observation_not_admission',
            time_s=self.observed_time, physical_tick=self.observed_tick, actual_object_ref=self.actual_object_ref,
            original_native_option_sha256=self.original_option_sha256,
            proposed_private_support_ref=self.surface.ref, source_height_m=self.surface.top_z_m,
            selected_object_contact_normal_N=list(self.selected_contact_normal_N),
            **self.metrics, actual_two_issued_global18_refs=True, original_guard_and_joint_limits_retained=True,
            support_registry_not_mutated=True, native_NAV_constructed=False,
            not_cold_capture_or_failed_PUSH_or_HOLD=True, model_input=False)


def read_actual_climb_nav_source(*, runtime=None, session=None, executor=None, registry=None,
                                 native_witness=None, source_root=None, guard=None, journal=None, enabled=False):
    require(type(enabled) is bool, 'Explicit owner opt-in')
    if not enabled:
        return None
    require(callable(guard) and callable(journal), 'Actual Data guard/evidence journal')
    require(guard() is not False, 'Actual Data owner/resource guard refused')
    root = Path(source_root).resolve(strict=True)
    for name, pin in PINS.items():
        path = root / name
        require(not path.is_symlink() and hashlib.sha256(path.read_bytes()).hexdigest() == pin,
                'Exact original live source dependency: ' + name)
    sys.path.insert(0, str(root))
    for name in ('ainav.native.registered_climb', 'mujoco_zyh.native_behavior_executor'):
        module = importlib.import_module(name)
        require(Path(module.__file__).resolve() == root / (name.replace('.', '/') + '.py'), 'No ambient source owner')
    observation = ActualClimbNavSourceObservation(_seal=_SEAL, runtime=runtime, session=session,
        executor=executor, registry=registry, native_witness=native_witness,
        source_root=root, guard=guard, journal=journal)
    journal(dict(event='V4_actual_CLIMB_boundary_NAV_source_sample', **observation.report()))
    return observation
