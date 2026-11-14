"""Pre-construction scene specification and passive native-decision observation.

No simulator/actor imports or state writes. Offsets apply to the box default
configuration BEFORE gym.make/reset; the native reset jitter/target logic stays.
"""
import copy
import hashlib
import json
import math


def load_scene(protocol_path, seed):
    protocol = json.loads(protocol_path.read_text())
    scenes = [s for s in protocol['scene_specs'] if s['seed'] == seed]
    if len(scenes) != 1:
        raise ValueError('Seed has no unique registered scene; do not substitute it')
    scene = scenes[0]
    offset = scene['box_default_world_x_offset_m']
    if isinstance(offset, bool) or not isinstance(offset, (int,float)) or not math.isfinite(offset) or not -.028 <= offset <= 0.:
        raise ValueError('Scene offset outside fixed zero-to-28mm inward design')
    return copy.deepcopy(scene)


def apply_scene(cfg, seed, protocol_path):
    """Called exactly once on the fresh cfg, after configure and before gym.make."""
    scene = load_scene(protocol_path, seed)
    if getattr(cfg, '_reach_scene_applied', False):
        raise ValueError('Do not accumulate offsets or reapply a scene')
    term = cfg.events.reset_box
    if term.func.__name__ != 'reset_push_box' or term.mode != 'reset':
        raise ValueError('Unexpected native box reset; refusing to change scene')
    before = tuple(cfg.scene.box.init_state.pos)
    if len(before) != 3 or not all(math.isfinite(v) for v in before):
        raise ValueError('Invalid default box position')
    after = (before[0]+scene['box_default_world_x_offset_m'], before[1], before[2])
    cfg.scene.box.init_state.pos = after
    cfg._reach_scene_applied = True
    return dict(scene, box_default_position_before=list(before),box_default_position_after=list(after),
                applied_before_environment_construction=True,
                native_reset_function='reset_push_box', native_reset_unchanged=True,
                actual_initial_state_validated=False,
                note='world-x default offset; not the frozen-query local-x transformation or a claimed mechanism trigger')


def observe_plan(plan, preview, role):
    """Attach a passive witness without changing any command/feasibility field."""
    from native_influence import describe_request, compare_requests
    if role != 'planning':
        return plan
    requests = preview['all_planning_requests']
    baseline = plan['support_only_shift_m']
    common = {a: describe_request(baseline, requests[a]['minimum_shift_m']) for a in ('P2','P3')}
    plan['reach_action_influence'] = dict(query_id=preview['query_id'],evaluation_role=role,
        support_only_shift_m=baseline, actual_selected_shift_m=plan['shift_m'],
        all_same_query_requests=common,
        comparison=compare_requests(baseline,requests['P2']['minimum_shift_m'],requests['P3']['minimum_shift_m']),
        task_success=None,execution_authorized=False,
        scope='passive query-level branch explanation; not a gate or task label')
    return plan
