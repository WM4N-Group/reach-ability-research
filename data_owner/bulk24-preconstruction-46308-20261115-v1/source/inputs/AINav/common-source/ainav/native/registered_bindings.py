"""Executor-only RGBD bindings for the original Go2/Piper three dynamic boxes.

No imports from another checkout and no physics authority. Inject the frozen
primary modules (and their source SHAs); see docs/COURSE_BINDINGS.md for ordering.
Association/preparation is NOT entry admission, an issued command, or success.
"""
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
import math
from types import MappingProxyType
from uuid import uuid4

from .session_factory import NativeTarget, NativeTargetBinding, _sha


class NotAdmitted(ValueError):
    """No proven current native binding; do not substitute another object/skill."""


# Physical identities, NOT a successor table or a public material declaration.
_SOURCES = ('visual_box_proposals', 'native_visual_target_binding',
            'mujoco_selected_target_context', 'native_target_context',
            'mujoco_zyh.observer', 'mujoco_zyh.native_behavior_executor',
            'mujoco_zyh.stall_stow')
_DESCRIPTOR = ('appearance_family', 'pixel_bbox_xyxy', 'pixel_centroid_uv',
               'median_observed_RGB', 'pixel_count', 'geometry_valid')


def _require(condition, message):
    if not condition:
        raise NotAdmitted('not_admitted: ' + message)


def _numpy(value):
    import numpy as np
    if hasattr(value, 'detach'):
        value = value.detach().cpu().numpy()
    return np.asarray(value)


def _xy(value):
    _require(isinstance(value, (tuple, list)) and len(value) == 2 and
             all(type(x) in (int, float) and math.isfinite(x) for x in value),
             'explicit finite executor reference XY required')
    return tuple(float(x) for x in value)


@dataclass(frozen=True)
class _Push:
    target_ref: str
    distance_m: float
    attempt_id: str
    goal_sha256: str
    approach_xy: tuple
    surface_height_m: float
    view: object
    receipt: dict
    history_owner: object
    history_sha256: object
    seal: tuple


class RegisteredBindingResolver:
    """One runtime/episode, matching current pixels to actual compiled geometry.

    ``proposals``, ``geometry`` and ``contexts`` are frozen primary modules, not
    module names to import. ``native_history_sha`` is frozen stall_stow.history_sha.
    ``public_geometry`` optionally declares full cuboid dimensions by actual body;
    otherwise ONLY the executor reads compiled geom_size, never material fields.
    Explicit approach references are caller-owned, not guessed from task stages.
    """

    def __init__(self, runtime, *, proposals, geometry, contexts, native_api,
                 native_history_sha, source_sha256, registry, public_geometry=None,
                 proposal_config=None, thresholds=None):
        registry.verify_compiled(runtime.sim.model)
        self.registry=registry
        self.bodies=tuple(o.body_name for o in registry.objects.values())
        self.candidates=MappingProxyType(registry.body_to_candidate())
        _require(all(_sha(source_sha256.get(k)) for k in _SOURCES),
                 'SHA provenance for all injected native sources required')
        for owner, names in ((proposals, ('propose_visual_candidates', 'single_visible_hypothesis')),
                             (geometry, ('match_geometry', 'BindingThresholds')),
                             (contexts, ('make_target_context',)),
                             (native_api, ('array_sha', 'world_snapshot'))):
            _require(all(callable(getattr(owner, n, None)) for n in names),
                     'frozen primary callable missing')
        _require(callable(native_history_sha), 'native history fingerprint required')
        self.runtime, self.proposals, self.geometry = runtime, proposals, geometry
        self.contexts, self.api, self.native_history_sha = contexts, native_api, native_history_sha
        self.source_sha256 = MappingProxyType(dict(source_sha256))
        if public_geometry is not None:
            _require(set(public_geometry) == set(self.bodies) and
                     _sha(source_sha256.get('public_task_geometry')),
                     'frozen public task geometry/body registry and source SHA required')
            for size in public_geometry.values():
                _require(isinstance(size, (list, tuple)) and len(size) == 3 and
                         all(type(x) in (int, float) and math.isfinite(x) and x > 0 for x in size),
                         'declared finite positive full cuboid dimensions required')
            self.public_geometry = MappingProxyType({k: tuple(v) for k, v in public_geometry.items()})
        else:
            self.public_geometry = None
        self.proposal_config = proposal_config
        self.thresholds = thresholds if thresholds is not None else geometry.BindingThresholds()
        self._refs, self._attempts, self._used_queries = {}, {}, set()
        self._last_tick = -1
        self._last_physical_tick = -1
        self._packet = None
        self._targets = None
        self._query_sha = None
        self._observed, self._pushes, self._climbs = {}, {}, {}
        self.private_provenance = []  # NEVER include in the public query/model log

    def _global_seal(self):
        """Read-only world/FIFO + aliases, including act/ctrl omitted by shared API."""
        r, p = self.runtime, self.runtime.sim
        entries = [id(p.model), id(p.data), id(p.queue), r.step_count,
                   self.api.world_snapshot(r), self.native_history_sha(p)]
        for name in ('act', 'ctrl', 'xpos', 'xmat', 'geom_xpos', 'geom_xmat'):
            entries.append(self.api.array_sha(_numpy(getattr(p.data, name))))
        for name in ('geom_size', 'geom_type', 'geom_bodyid'):
            entries.append(self.api.array_sha(_numpy(getattr(p.model, name))))
        entries.extend((p.base_id, self.api.array_sha(_numpy(p.qids))))
        if hasattr(r, 'wm_candidate_contacts'):
            entries.append(json.dumps(r.wm_candidate_contacts, sort_keys=True, allow_nan=False))
        if hasattr(p.scene, 'sensors'):
            entries.append(tuple(sorted((k, id(v)) for k, v in p.scene.sensors.items())))
        if hasattr(r, 'last'):
            entries.append(self.api.array_sha(_numpy(r.last.array())))
        for owner in (r, p):
            for name in ('push', 'box_id', 'box_name', 'box_y', 'cfg', 'controller',
                         'target_context', 'box_push_target', 'scene'):
                if not hasattr(owner, name):
                    continue
                value = getattr(owner, name)
                scalar = type(value) in (str, int, float, bool, type(None))
                entries.append((id(owner), name, value if scalar else id(value)))
                if name == 'box_push_target':
                    entries.append(self.api.array_sha(_numpy(value)))
                if name in ('scene', 'push'):
                    # Native Runtime.push is a Plugin, not the dict used by old
                    # CPU fixtures. Seal the exact __getitem__ backing table.
                    table = value if isinstance(value, Mapping) else getattr(value, 'modules', None)
                    _require(isinstance(table, Mapping), 'Actual native alias/module table required')
                    entries.append((id(table), tuple(sorted((k, id(v)) for k, v in table.items()))))
                if name == 'cfg':
                    # Runtime.cfg is dict; selected native view.cfg is namespace.
                    table = value if isinstance(value, Mapping) else vars(value)
                    entries.append(tuple(sorted((k, v if type(v) in
                        (str, int, float, bool, type(None)) else id(v)) for k, v in table.items())))
        return tuple(entries)

    def _packet_sha(self, packet):
        return tuple(self.api.array_sha(_numpy(packet[k])) for k in
                     ('rgb', 'depth_m', 'camera_K', 'T_base_optical', 'timestamps_s'))

    def _current(self):
        _require(self._packet is not None, 'observe the actual current packet first')
        _require(self._stamp == self._global_seal(), 'stale world/FIFO or changed global alias')
        _require(self._pixels == self._packet_sha(self._packet), 'observed packet mutated')

    def _catalog(self):
        """Private geometry only. Do NOT call observer.private_catalog (reads mass)."""
        import numpy as np
        p = self.runtime.sim
        R = np.asarray(p.data.xmat[p.base_id]).reshape(3, 3)
        base = np.asarray(p.data.xpos[p.base_id])
        _require(np.isfinite(base).all() and np.isfinite(R).all(), 'missing measured camera parent')
        objects = []
        for body in self.bodies:
            bid = int(p.model.body(body).id)
            gid = int(p.model.geom(body + '_geom').id)
            _require(int(p.model.geom_bodyid[gid]) == bid and int(p.model.geom_type[gid]) == 6,
                     'actual selected cuboid geom required')  # mjGEOM_BOX == 6
            size = (np.asarray(self.public_geometry[body], dtype=np.float64)
                    if self.public_geometry is not None else np.asarray(p.model.geom_size[gid]) * 2)
            _require(size.shape == (3,) and np.isfinite(size).all() and (size > 0).all(),
                     'frozen full cuboid dimensions required')
            center = np.asarray(p.data.geom_xpos[gid])
            rotation = np.asarray(p.data.geom_xmat[gid]).reshape(3, 3)
            objects.append(dict(executor_scene_key=body,
                center_base_xyz_m=((center-base) @ R).tolist(),
                rotation_base_from_object=(R.T @ rotation).tolist(), size_m=size.tolist()))
        return objects

    def observe(self, packet, *, control_tick, physical_tick=None):
        """Witness OnboardObserver.capture's PACKET (not its private catalog).

        Returns only current RGB descriptors and stable opaque refs. A missing,
        depth-invalid, ambiguous or multiply associated object is not returned.
        Build options/query after prepare_push; bind_query then seals their SHA.
        """
        import numpy as np
        # Failure must invalidate the previous frame, including old preparations.
        self._packet, self._targets, self._query_sha = None, None, None
        self._observed, self._pushes, self._climbs = {}, {}, {}
        physical_tick = control_tick*4 if physical_tick is None else physical_tick
        _require(type(control_tick) is int and type(physical_tick) is int
                 and physical_tick//4 == control_tick and physical_tick > self._last_physical_tick,
                 'strictly newer actual physical acquisition tick required')
        stamp = self._global_seal()
        rgb, depth, K, mount, times = (_numpy(packet[k]) for k in
            ('rgb', 'depth_m', 'camera_K', 'T_base_optical', 'timestamps_s'))
        _require(rgb.ndim == 5 and rgb.shape[:2] == (1, 1) and rgb.shape[-1] == 3
                 and rgb.dtype == np.uint8, 'observer RGB [1,1,H,W,3] uint8 required')
        h, w = rgb.shape[2:4]
        _require(depth.shape == (1, 1, h, w, 1) and K.shape == (1, 3, 3)
                 and mount.shape == (1, 4, 4) and times.shape == (1, 1),
                 'exact observer RGBD/K/mount/timestamps_s schema required')
        _require(np.isfinite(times).all() and float(times[0, 0]) == float(self.runtime.sim.data.time),
                 'packet time must equal actual native data.time')
        rgb, depth, K, mount = rgb[0, 0].copy(), depth[0, 0, :, :, 0].copy(), K[0].copy(), mount[0].copy()
        kwargs = {} if self.proposal_config is None else {'config': self.proposal_config}
        result = self.proposals.propose_visual_candidates(rgb, depth, K, mount, **kwargs)
        rgb_sha = hashlib.sha256(rgb.tobytes()).hexdigest()
        _require(result.get('RGB_sha256') == rgb_sha, 'primary proposal RGB mismatch')
        catalog = self._catalog()
        matches = []
        for raw in result['candidates']:
            try:
                proposal = self.proposals.single_visible_hypothesis(
                    result, raw['frame_local_ref'], current_RGB_sha256=rgb_sha)
            except ValueError:
                continue  # no guessed largest fragment, no missing-depth fallback
            found = [obj for obj in catalog if self.geometry.match_geometry(
                proposal, obj, K, mount, (h, w), self.thresholds) is not None]
            if len(found) == 1:
                matches.append((proposal, found[0]['executor_scene_key']))
        # Require one-to-one CURRENT correspondence, never previous-stage memory.
        for proposal, body in matches:
            if sum(b == body for _, b in matches) != 1:
                continue
            ref = self._refs.setdefault(body, 'course-target-' + uuid4().hex)
            self._observed[ref] = (body, proposal)
        _require(stamp == self._global_seal(), 'proposal/matching changed native state')
        self._packet, self._stamp = packet, stamp
        self._pixels, self._rgb_sha = self._packet_sha(packet), rgb_sha
        self._last_tick = control_tick
        self._last_physical_tick = physical_tick
        return tuple(dict(target_ref=ref, RGB_sha256=rgb_sha,
                          descriptor={k: deepcopy(p[k]) for k in _DESCRIPTOR})
                     for ref, (_, p) in self._observed.items())

    def _history(self, view):
        # Original primary fingerprint includes heterogeneous sim.history,
        # applied_commands, targets, episode_length_buf and original [1,3] goal.
        native = self.native_history_sha(view)
        _require(_sha(native), 'invalid native history fingerprint')
        manager = view.target_context.action_manager
        payload = [native]
        for name in ('action', 'prev_action', 'prev_prev_action'):
            payload.append(self.api.array_sha(_numpy(getattr(manager, name))))
        return hashlib.sha256(json.dumps(payload).encode()).hexdigest()

    def _push_seal(self, push):
        v = push.view
        return (id(v), id(v.cfg), v.cfg.push_distance, v.box_id, id(v.controller),
                id(v.target_context), id(v.controller.env), id(v.data), id(v.queue),
                id(v.target_context.cfg), id(v.scene), id(v.target_context.scene),
                v.target_context.body_key, id(v.target_context.scene['box']),
                tuple(sorted(v.target_context.box_push_declared_attempt.items())),
                self.api.array_sha(_numpy(v.box_push_target)),
                id(push.history_owner()), push.history_sha256(),
                getattr(v,'body_braking_reference').sha256 if hasattr(v,'body_braking_reference') else None)

    def prepare_push(self, target_ref, *, distance_m, attempt_id, approach_xy,
                     surface_height_m, goal_xy_m=None, body_braking_goal_xy_m=None):
        """Prospective software context BEFORE constructing the public option.

        Returns ONLY opaque original goal SHA. XY is executor-private, explicitly
        supplied, never an object/goal-ranking rule or a native entry certificate.
        """
        self._current()
        _require(self._query_sha is None, 'prepare before factory.bind_query')
        _require(target_ref in self._observed, 'target absent from current image association')
        _require(isinstance(attempt_id, str) and attempt_id and attempt_id not in self._attempts,
                 'new immutable attempt ID required')
        _require(type(distance_m) in (int, float) and (distance_m in (.2, .4, .6, .8) if goal_xy_m is None else 0<distance_m<=.8),
                 'original registered declared PUSH distance required')
        xy = _xy(approach_xy)
        body = self._observed[target_ref][0]
        from .scene_registry import declared_push_source
        declared_push_source(self.registry,body,surface_height_m)
        _require(body in self.candidates, 'Only registered non-retired objects support a new PUSH attempt')
        candidate = self.candidates[body]
        receipt = self.runtime.wm_candidate_contacts
        _require(receipt['scene_keys'][candidate] == body, 'candidate contact registry/body mismatch')
        self._attempts[attempt_id] = None  # even partial constructors cannot reuse an attempt
        kwargs = dict(declared_push=dict(distance_m=distance_m, declaration_id=attempt_id))
        if goal_xy_m is not None:kwargs['declared_push']['goal_xy_m']=tuple(goal_xy_m)
        if body_braking_goal_xy_m is not None:kwargs['body_braking_goal_xy_m']=_xy(body_braking_goal_xy_m)
        if self.public_geometry is not None:
            size = tuple(self.public_geometry[body])
        else:
            p = self.runtime.sim
            gid = int(p.model.geom(body + '_geom').id)
            size = tuple(float(x) * 2 for x in p.model.geom_size[gid])
        kwargs['cfg_overrides'] = {'box_size': size}
        view, native_receipt = self.contexts.make_target_context(
            self.runtime, receipt, candidate, **kwargs)
        self._current()
        context = view.target_context
        _require(view is not self.runtime.sim and view.data is self.runtime.sim.data
                 and view.queue is self.runtime.sim.queue and view.model is self.runtime.sim.model
                 and view.box_id == int(self.runtime.sim.model.body(body).id)
                 and context.body_key == body and context.scene['box'] is self.runtime.sim.scene[body]
                 and view.scene is context.scene and view.cfg is context.cfg
                 and view.controller is not self.runtime.sim.controller
                 and view.controller.env is context
                 and native_receipt.get('controller_env_is_explicit_context') is True,
                 'actual independent selected target/controller/world/FIFO required')
        goal = _numpy(view.box_push_target)
        _require(goal.shape == (1, 3) and view.cfg.push_distance == distance_m,
                 'native original goal [1,3]/distance mismatch')
        # Actual measured world-X goal rule; a fake receipt cannot prove it.
        import numpy as np
        expected = np.asarray(self.runtime.sim.data.xpos[view.box_id]).copy()
        expected[0] += distance_m
        if goal_xy_m is not None:expected[:2]=goal_xy_m
        _require(np.isfinite(goal).all() and np.allclose(goal[0], expected, rtol=0, atol=1e-6),
                 'original measured declared goal rule mismatch')
        declaration = context.box_push_declared_attempt
        _require(declaration == dict(declaration_id=attempt_id, distance_m=distance_m),
                 'native immutable attempt declaration mismatch')
        owner = (view.controller, context, context.action_manager)
        def history_owner():
            return view if (view.controller is owner[0] and view.target_context is owner[1]
                            and context.action_manager is owner[2]) else None
        fingerprint = lambda: self._history(view)
        push = _Push(target_ref, distance_m, attempt_id, self.api.array_sha(goal), xy,
                     surface_height_m, view, deepcopy(native_receipt), history_owner, fingerprint, ())
        from dataclasses import replace
        push = replace(push, seal=self._push_seal(push))
        self._pushes[attempt_id] = self._attempts[attempt_id] = push
        self.private_provenance.append(dict(attempt_id=attempt_id, target_ref=target_ref,
            original_push_goal_sha256=push.goal_sha256, control_tick=self._last_tick,
            RGB_sha256=self._rgb_sha, source_sha256=dict(self.source_sha256),
            status='software_prebound_not_admitted', model_input=False,
            command_issued=False, native_entry_certified=False))
        return push.goal_sha256

    def declare_climb_reference(self, target_ref, *, surface, approach_xy, surface_height_m):
        """Explicit PUBLIC native reference, not a derived successor/goal.

        ClimbEntry will overwrite task.approach. This is NOT an effective climb
        control knob; no arbitrary XY/height control or HIGH mapping is claimed.
        """
        self._current()
        _require(self._query_sha is None and target_ref in self._observed,
                 'declare reference before query binding, for an observed target')
        body = self._observed[target_ref][0]
        _require((body, surface) in (('wm_object_middle', 'B'), ('wm_object_heavy', 'C')),
                 'no proven native surface for this actual body')
        _require(type(surface_height_m) in (int, float) and math.isfinite(surface_height_m),
                 'explicit public reference height required')
        reference = (surface, _xy(approach_xy), surface_height_m)
        _require(target_ref not in self._climbs or self._climbs[target_ref] == reference,
                 'do not overwrite the same-frame public reference')
        self._climbs[target_ref] = reference

    def targets_for_query(self, runtime, query_sha256):
        self._current()
        _require(runtime is self.runtime and _sha(query_sha256), 'exact runtime/query SHA required')
        if self._query_sha is not None:
            _require(query_sha256 == self._query_sha, 'observe a new frame before another query')
            return self._targets
        _require(query_sha256 not in self._used_queries, 'query replay')
        self._query_sha = query_sha256
        self._used_queries.add(query_sha256)
        self._targets = tuple(NativeTarget(ref, body, int(runtime.sim.model.body(body).id),
            query_sha256, 'rgbd-association:' + hashlib.sha256(json.dumps(
                [query_sha256, self._last_tick, self._pixels, proposal['frame_local_ref'], body],
                sort_keys=True).encode()).hexdigest(), self._climbs.get(ref, ('',))[0])
            for ref, (body, proposal) in self._observed.items())
        return self._targets

    def resolve(self, runtime, option, query_binding):
        self._current()
        q = query_binding
        _require(runtime is self.runtime and q.query_sha256 == self._query_sha
                 and q.data is runtime.sim.data and q.queue is runtime.sim.queue
                 and q.model is runtime.sim.model and q.world == self.api.world_snapshot(runtime)
                 and self._targets is not None and len(q.targets) == len(self._targets)
                 and all(a is b for a, b in zip(q.targets, self._targets))
                 and any(o == option and o.sha256 == option.sha256 for o in q.options),
                 'exact factory query/options/world/FIFO/target registry required')
        _require(not (option.attempt_id and option.skill not in ('PUSH', 'EXIT_PUSH')),
                 'non-PUSH cannot create an attempt')
        targets = [t for t in q.targets if t.target_ref == option.target_ref]
        _require(len(targets) == 1, 'missing current object; never select a substitute')
        target, params = targets[0], dict(option.parameters)
        _require(option.skill in ('PUSH', 'NAV', 'CLIMB'),
                 'HOLD has no backend; EXIT/RECOVER belong to original owner')
        _require('surface_height_m' in params, 'explicit public surface reference required')
        common = dict(query_sha256=q.query_sha256, selected_option_sha256=option.sha256,
            target=target, data=q.data, queue=q.queue, evidence_ref=target.association_evidence_ref)
        if option.skill == 'PUSH':
            p = self._pushes.get(option.attempt_id)
            _require(p is not None and p.target_ref == option.target_ref
                     and p.distance_m == params.get('push_distance_m')
                     and p.surface_height_m == params['surface_height_m']
                     and p.goal_sha256 == option.original_push_goal_sha256
                     and not {'goal_world_x_m', 'goal_world_y_m'} & params.keys(),
                     'exact prebound attempt/target/distance/goal/public parameters required')
            _require(self._push_seal(p) == p.seal, 'prebound view/goal/distance/history changed')
            return NativeTargetBinding(**common, mode='selected_push', approach_xy=p.approach_xy,
                view=p.view, binding_receipt=deepcopy(p.receipt),
                history_owner=p.history_owner, history_sha256=p.history_sha256)
        _require(not option.attempt_id and not option.original_push_goal_sha256
                 and 'push_distance_m' not in params, 'movement cannot own a PUSH attempt')
        if option.skill == 'NAV':
            import numpy as np
            p = runtime.sim
            arm = np.asarray(p.data.qpos[p.qids[12:]])
            _require(arm.shape == (6,) and np.isfinite(arm).all()
                     and float(np.max(np.abs(arm))) < .12,
                     'compact/nonzero-arm NAV needs the actual protected owner/prefix; not implemented')
            _require({'goal_world_x_m', 'goal_world_y_m'} <= params.keys(),
                     'NAV must consume explicit public XY')
            # No compact prefix/previous protected owner is synthesized here.
            return NativeTargetBinding(**common, mode='movement')
        if option.skill == 'CLIMB':
            reference = self._climbs.get(option.target_ref)
            _require(reference is not None and reference[2] == params['surface_height_m']
                     and not {'goal_world_x_m', 'goal_world_y_m'} & params.keys(),
                     'explicit public CLIMB reference missing/mismatched')
            return NativeTargetBinding(**common, mode='movement', approach_xy=reference[1])
        raise NotAdmitted('not_admitted: HOLD has no backend; EXIT/RECOVER belong to original owner')
