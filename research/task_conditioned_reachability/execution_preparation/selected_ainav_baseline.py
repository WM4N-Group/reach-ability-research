"""Source-specific numerical demand pullback for the selected full AINav v6.

Not current five-box scene_* code; no Runtime/host/Actor, selected-history label,
new control variable, model effect, launch API or execution authorization.
"""
import hashlib
import json
import math
from pathlib import Path


BASELINE = 'execution-judged-20261031-v6'
MANIFEST_SHA = '314b6650918cbf88c6bd7166ad3f2d26f9c3b30f92094db98d6f8832f8d1fd8c'
RELEASE_SHA = '3098297041dbfa50dd1928ee81ce28c68d3458ed544cc494dea7374177b7c49e'


def need(condition, message):
    if not condition:
        raise ValueError(message)


def finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def box_center_preimage(goal_x, *, offset=.11, drive_max=.8):
    """Inverse of 0<g+b-x<=D: x in [g+b-D,g+b), NOT current-state evidence."""
    need(all(finite(v) for v in (goal_x, offset, drive_max)) and 0 < offset < drive_max,
         'Explicit finite original goal/drive constants')
    return dict(lower_m=goal_x+offset-drive_max, upper_m=goal_x+offset,
                lower_closed=True, upper_closed=False)


def contains(interval, x):
    need(finite(x), 'Finite position')
    return ((x >= interval['lower_m'] if interval['lower_closed'] else x > interval['lower_m'])
            and (x <= interval['upper_m'] if interval['upper_closed'] else x < interval['upper_m']))


def intersect(a, b):
    low = max(a['lower_m'], b['lower_m']); high = min(a['upper_m'], b['upper_m'])
    lc = all(v['lower_closed'] for v in (a, b) if v['lower_m'] == low)
    uc = all(v['upper_closed'] for v in (a, b) if v['upper_m'] == high)
    if low > high or (low == high and not (lc and uc)):
        return None
    return dict(lower_m=low, upper_m=high, lower_closed=lc, upper_closed=uc)


def interval_stroke_relation(goal_x, center_interval, *, independent_bound_available=False):
    """Supplied-model necessary numerical relation, never full skill readiness.

    No independent bound -> UNKNOWN, even if a nominal interval was supplied.
    A disjoint interval only rejects this numerical stroke under the bound; it
    is not a dynamic/task/global-infeasibility certificate.
    """
    result = dict(scope='FIXED_GOAL_CURRENT_X_NUMERIC_STROKE_ONLY',
                  goal_x_m=goal_x, preimage=box_center_preimage(goal_x),
                  relation='UNKNOWN', actual_native_ready=None, dispatch=False)
    need(type(independent_bound_available) is bool, 'Explicit bound availability')
    if center_interval is None or not independent_bound_available:
        return result
    need(type(center_interval) in (list, tuple) and len(center_interval) == 2
         and all(finite(v) for v in center_interval) and center_interval[0] <= center_interval[1],
         'Explicit finite ordered center interval')
    observed = dict(lower_m=center_interval[0], upper_m=center_interval[1],
                    lower_closed=True, upper_closed=True)
    overlap = intersect(observed, result['preimage'])
    result['conditional_intersection'] = overlap
    result['relation'] = ('NO_NUMERIC_STROKE_MATCH_IN_SUPPLIED_BOUND' if overlap is None else
        'ALL_NUMERIC_STROKES_WITHIN_DOMAIN_IN_SUPPLIED_BOUND'
        if all(contains(result['preimage'], x) for x in center_interval) else
        'PARTIAL_NUMERIC_STROKE_MATCH_IN_SUPPLIED_BOUND')
    return result


def direct_entry_pullback(goal_x, *, box_length, lane_y, base_xy, radius=.16,
                          push_standoff=.58, offset=.11, drive_max=.8):
    """Exact interval elimination for ORIGINAL direct XY entry + drive relation.

    Axis-aligned compiled geometry, fixed base/lane and no uncertain quantities
    are assumptions. An empty result means no DIRECT mode in this supplied
    geometric model; original same-support NAV preparation can still help.
    It does not output a new NAV target or optimize inside the entry envelope.
    """
    need(type(base_xy) in (list, tuple) and len(base_xy) == 2
         and all(finite(v) for v in (goal_x, box_length, lane_y, *base_xy, radius,
                                    push_standoff, offset, drive_max))
         and box_length > 0 and radius > 0 and push_standoff > 0,
         'Finite declared geometry and positive original preparation constants')
    drive = box_center_preimage(goal_x, offset=offset, drive_max=drive_max)
    dy = base_xy[1]-lane_y
    pose = None
    if abs(dy) <= radius:
        half = math.sqrt(max(0., radius*radius-dy*dy))
        center = base_xy[0]+box_length/2+push_standoff
        pose = dict(lower_m=center-half, upper_m=center+half, lower_closed=True, upper_closed=True)
    return dict(direct_pose_box_center_interval=pose,
                numeric_drive_box_center_interval=drive,
                joint_direct_box_center_interval=intersect(pose, drive) if pose else None,
                assumption='fixed supplied base/lane and axis-aligned compiled half-length',
                original_NAV_preparation_not_ruled_out=True,
                full_source_support_and_native_entry_still_required=True,
                whole_task_infeasible=None, physical_dispatch=False)


def inspect_release(package, *, previous_current_manifest=None):
    """Only necessary pins, no 8525-row historical audit or all-source re-test."""
    package = Path(package)
    release_path = package/'BASELINE_RELEASE_v1.json'
    need(sha(release_path) == RELEASE_SHA, 'Selected release drift; explicit review required')
    release = json.loads(release_path.read_text())
    need(release['chosen_baseline'] == BASELINE and release['host'] ==
         'ainav.native.execution_judged_course.ExecutionJudgedFullCourse', 'Exact selected full host')
    source = package/'reference-source'
    need(sha(source/'ainav-source.json') == MANIFEST_SHA ==
         release['original_reference_manifest_sha256'], 'Original full manifest identity')
    cap_path = package/'PUBLIC_TARGET_CAPABILITIES_v1.json'
    need(sha(cap_path) == release['PUBLIC_TARGET_CAPABILITIES_sha256'], 'Public capability drift')
    cap = json.loads(cap_path.read_text())
    need(cap['kind'] == 'PUBLIC_STATIC_CAPABILITY_BOUNDARIES_NOT_ACTION_PERMISSION_OR_EFFECT_PREDICTION',
         'Do not use PRIVATE historical pose/receipt as current planning input')
    selected_names = ['ainav/__init__.py', 'ainav/native/__init__.py', 'ainav/contracts.py',
        'ainav/intents.py', 'ainav/native/behavior_authority.py', 'ainav/native/execution_judge.py',
        'ainav/native/execution_judged_course.py', 'ainav/native/full_course.py',
        'ainav/native/full_verified_placement.py', 'ainav/native/placement_contract.py',
        'ainav/native/push_support_gate.py', 'ainav/native/intent_execution.py']
    pins = []
    for name in selected_names:
        p = source/name; h = sha(p)
        need(h == release['complete_reference_source_files_sha256'][name], 'Selected source pin changed')
        pins.append(dict(name=name, path=str(p), sha256=h))
    prior = []
    if previous_current_manifest is not None:
        old = json.loads(Path(previous_current_manifest).read_text())
        for row in old['source_files']:
            key = row['path'].split('/src/')[-1]
            h = release['complete_reference_source_files_sha256'].get(key)
            prior.append(dict(name=key, relation='ABSENT_FROM_SELECTED_BASELINE' if h is None else
                              'IDENTICAL' if h == row['sha256'] else 'DIFFERENT'))
    goals = []
    for public in cap['historically_executed_absolute_goals']:
        gx, gy = public['xy_m']
        goals.append(dict(public_goal_xy_m=[gx, gy], source_height_m=public['surface_height_m'],
                          native_drive_reference_xy_m=[gx+.11, gy],
                          numeric_current_box_center_preimage=box_center_preimage(gx),
                          current_box_pose=None, current_pose_bound=None,
                          current_numeric_stroke_relation=interval_stroke_relation(gx, None),
                          actual_after_Finish_state=None, successor_cost_s=None,
                          actual_native_ready=None, dispatch=False))
    return dict(schema='reach-selected-ainav-v6-demand-v1', baseline=BASELINE,
                original_full_manifest_sha256=MANIFEST_SHA, release_sha256=RELEASE_SHA,
                selected_source_subset_pins=pins,
                previous_current_source_comparison=prior, goals=goals,
                previous_five_box_eight_row_table_applies_to_this_host=False,
                full_current_runtime_qualification=False, private_or_raw_historical_records_read=False,
                public_historical_capability_goal_summary_consumed=True,
                new_WM_Runtime_Actor_physics_API_training=0, physical_dispatch=False)
