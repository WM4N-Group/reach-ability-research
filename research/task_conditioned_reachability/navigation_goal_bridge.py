"""Shadow-only task-conditioned SE2 goal selection for ORIGINAL navigation types.

No controller, runtime, actor, physics, height action, or success label. Caller
must supply actual original-planner navigation costs and state-bound candidates.
Static directional/alignment cost CANNOT silently stand in for J_nav.
"""
from __future__ import annotations

import importlib
import math
from pathlib import Path
import sys

MODES = ('nav_only', 'task_ik', 'endpoint', 'path', 'path_margin', 'path_margin_gate')
REPO = Path(__file__).resolve().parents[2]


def finite(value):
    if type(value) not in (float, int) or not math.isfinite(value):
        raise ValueError('Expected finite scalar')
    return float(value)


def select_shadow_goal(packet, mode='path_margin_gate', margin_weight=.1):
    if mode not in MODES or finite(margin_weight) < 0:
        raise ValueError('Unknown ablation mode or negative margin weight')
    if packet.get('schema') != 'reachability-navigation-shadow-query-v1':
        raise ValueError('Wrong navigation query schema')
    state_id = packet.get('observed_state_id')
    height = finite(packet['observed_body_height_m'])
    if not isinstance(state_id, str) or not state_id or height <= 0:
        raise ValueError('Need bound observed state and positive body height')
    out = dict(mode=mode, observed_state_id=state_id, observed_body_height_m=height,
               execution_authorized=False, status='not_ready', candidate_id=None,
               actual_navigation_success=None, unknown_candidate_ids=[],
               selection_scope='known_model_subset_NOT_global_optimum_or_physical_certificate')
    source = packet.get('navigation_cost_source')
    if not isinstance(source, dict) or source.get('kind') != 'original_planner_route_cost':
        return dict(out, missing=['actual_original_planner_route_cost_and_source'],
                    reason='Static alignment/directional-fraction cost is not J_nav')
    source_hash = source.get('sha256')
    if not isinstance(source_hash, str) or len(source_hash) != 64 or any(c not in '0123456789abcdef' for c in source_hash):
        raise ValueError('Navigation cost source must be SHA-bound')
    rows = packet.get('candidates', [])
    ids = [r['candidate_id'] for r in rows]
    if len(ids) != len(set(ids)):
        raise ValueError('Candidate IDs must be unique')
    eligible, route_unknown, model_unknown = [], [], []
    for r in rows:
        if r['observed_state_id'] != state_id or abs(finite(r['model_body_height_m'])-height) > 1e-9:
            raise ValueError('Candidates must share observed state/height; height is not an action')
        pose = r['target_se2_world']
        if len(pose) != 3:
            raise ValueError('Original NAV target must be SE2 [x,y,yaw], not a height command')
        tuple(finite(v) for v in pose)
        route = r['route_status']
        if route not in ('reachable', 'unreachable', 'unknown'):
            raise ValueError('Unknown route status')
        if route == 'unknown':
            route_unknown.append(r['candidate_id'])
            continue
        if route == 'unreachable':
            continue
        cost = finite(r['navigation_cost'])
        if cost < 0:
            raise ValueError('Navigation cost must be nonnegative under fixed normalization')
        task = r['task_pose_status']
        if task not in ('found', 'bounded_solver_miss_UNKNOWN', 'analytic_model_excluded'):
            raise ValueError('Unknown task pose status')
        excluded = r.get('analytic_necessary_excluded')
        if excluded is not None and type(excluded) is not bool:
            raise ValueError('Analytic exclusion must be bool or unknown')
        if excluded is True and task == 'found':
            raise ValueError('Analytic exclusion contradicts valid task pose; stop, do not dispatch')
        if task == 'bounded_solver_miss_UNKNOWN':
            model_unknown.append(r['candidate_id'])
        if mode != 'nav_only' and task != 'found':
            continue
        rho = 0.
        if mode in ('endpoint', 'path', 'path_margin', 'path_margin_gate'):
            key = 'endpoint_rho' if mode == 'endpoint' else 'path_rho'
            raw = r.get(key)
            if raw is None:
                model_unknown.append(r['candidate_id'])
                continue
            rho = finite(raw)
            if rho < 0:
                continue
        if mode == 'path_margin_gate' and excluded is True:
            continue
        objective = cost - (margin_weight*rho if mode in ('path_margin', 'path_margin_gate') else 0)
        eligible.append((objective, r['candidate_id'], r))
    out['unknown_candidate_ids'] = sorted(set(model_unknown))
    if route_unknown:
        return dict(out, status='unknown_navigation_cost_domain', missing_route_ids=sorted(route_unknown))
    if not eligible:
        return dict(out, status='abstain_no_known_nominal_candidate', eligible_candidates=0)
    objective, cid, chosen = min(eligible, key=lambda x: (x[0], x[1]))
    return dict(out, status='selected_shadow_proposal', candidate_id=cid, objective=objective,
                eligible_candidates=len(eligible), target_se2_world=list(chosen['target_se2_world']),
                navigation_cost_source=source, data_role=packet.get('data_role', 'not_registered_for_execution'),
                original_runtime_safety_gates_must_remain_enabled=True)


def as_original_shadow_action(proposal):
    """Construct ORIGINAL SkillAction(NAV); never call any runtime or authorize it."""
    if proposal.get('status') != 'selected_shadow_proposal' or proposal.get('execution_authorized') is not False:
        raise ValueError('Only non-executing shadow proposals can be exported')
    path = REPO/'mujoco/reconfigurable_navigation/representations.py'
    # Use the canonical original class, not a second dataclass loaded under an alias.
    root = str(REPO/'mujoco')
    inserted = root not in sys.path
    if inserted:
        sys.path.insert(0, root)
    try:
        types = importlib.import_module('reconfigurable_navigation.representations')
    finally:
        if inserted:
            sys.path.remove(root)
    if Path(types.__file__).resolve() != path.resolve():
        raise ValueError('Original NAV type resolved from a different source checkout')
    return types.SkillAction(types.SkillType.NAV, proposal['target_se2_world'])
