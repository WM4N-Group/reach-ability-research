"""Model-free task-conditioned inspection of AINav's declared placement domain.

Blueprint necessary relations only. Not a current pose, runtime admission, new
continuous-goal interface, outcome predictor, task planner or dispatch authority.
The existing owner catalogue/arithmetic/placement contract are consumed, not
reimplemented. Physical execution remains with the existing owner.
"""
from collections import defaultdict
import hashlib
import importlib
import json
import math
from pathlib import Path
import sys


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def need(ok, message):
    if not ok:
        raise ValueError(message)


def number(value):
    return type(value) in (int, float) and math.isfinite(value)


def goal_interval(center_x, *, offset, drive_max):
    """Exact native displacement relaxation: goal in (cx-offset,cx+D-offset].

    These are goal coordinates, not an authorized continuum. Current catalogue
    membership, actual body association and native admission are separate.
    """
    need(all(number(v) for v in (center_x, offset, drive_max)), 'Finite stroke data')
    need(0 < offset < drive_max, 'Positive original offset below original stroke')
    return dict(lower_m=center_x-offset, lower_closed=False,
                upper_m=center_x+drive_max-offset, upper_closed=True)


def in_interval(goal, interval):
    need(number(goal), 'Finite goal coordinate')
    low = goal >= interval['lower_m'] if interval['lower_closed'] else goal > interval['lower_m']
    high = goal <= interval['upper_m'] if interval['upper_closed'] else goal < interval['upper_m']
    return low and high


def aligned_final_interval(goal_x, *, offset, public_tol, dock_tol, native_tol):
    """Axial slice of ORIGINAL placement predicates, NOT a goal-control domain.

    Assumes zero yaw, lane error zero, correct height. Original public/native
    distance tests are strict and dock test is inclusive. No tolerance relaxed.
    """
    need(all(number(v) for v in (goal_x, offset, public_tol, dock_tol, native_tol)),
         'Finite placement data')
    need(min(public_tol, dock_tol, native_tol) > 0, 'Positive placement tolerances')
    # Work relative to the goal to avoid subtraction cancellation in endpoints.
    rel = [(-public_tol, public_tol, False, False), (-dock_tol, dock_tol, True, True),
           (offset-native_tol, offset+native_tol, False, False)]
    lower = max(v[0] for v in rel); upper = min(v[1] for v in rel)
    return dict(reference_goal_x_m=goal_x, lower_error_m=lower, upper_error_m=upper,
                lower_closed=all(v[2] for v in rel if v[0] == lower),
                upper_closed=all(v[3] for v in rel if v[1] == upper),
                aligned_position_only=True, actual_native_ready=None)


def support_projection(box_goal, size, source_bounds, receiver_bounds):
    """Zero-yaw geometric cover, not loaded support, COM or walking safety."""
    need(len(box_goal) == 2 and len(size) == 3 and len(source_bounds) == len(receiver_bounds) == 4,
         'Explicit cuboid/source/receiver geometry')
    need(all(number(v) for v in (*box_goal, *size, *source_bounds, *receiver_bounds))
         and min(size) > 0, 'Finite positive geometry')
    for bounds in (source_bounds, receiver_bounds):
        need(bounds[0] < bounds[1] and bounds[2] < bounds[3], 'Nonempty source/receiver')
    x, y = box_goal; length, width, _ = size
    rear = x-length/2; front = x+length/2
    overlap_x = max(0., min(front, source_bounds[1])-max(rear, source_bounds[0]))
    overlap_y = max(0., min(y+width/2, source_bounds[3])-max(y-width/2, source_bounds[2]))
    return dict(nominal_box_rear_x_m=rear, nominal_box_forward_face_x_m=front,
                source_contact_projection_area_m2=overlap_x*overlap_y,
                source_contact_projection_nonempty=overlap_x*overlap_y > 0,
                source_to_receiver_span_margin_m=source_bounds[1]-rear,
                receiver_lane_margin_m=min(y-width/2-receiver_bounds[2],
                                           receiver_bounds[3]-y-width/2),
                loaded_support_verified=None, collision_free_path_verified=None)


def receiver_stage(source_top, box_height, receiver_top):
    """Later box->receiver height relation, NOT immediate box entry/readiness."""
    need(all(number(v) for v in (source_top, box_height, receiver_top)), 'Finite layer geometry')
    rise = receiver_top-source_top-box_height
    if abs(rise) < 1e-9:
        skill = 'NAV_SAME_LAYER_HEIGHT_ONLY'
    elif abs(rise-.2) < 1e-9:
        skill = 'CLIMB_UP_020_HEIGHT_ONLY'
    else:
        skill = 'NO_DIRECT_CATALOGUE_NAV_OR_UP020_CLIMB_HEIGHT_MATCH'
    return dict(scope='LATER_FROM_NOMINALLY_MOUNTED_BOX_TO_RECEIVER',
                nominal_rise_m=rise, nominal_skill_height_relation=skill,
                immediate_after_PUSH_successor_is_separate=True,
                support_connection_verified=None, native_ready=None)


def fixed_edge_baselines(row):
    """Same fixed object/source/receiver and SAME current catalogue goal.

    The native relaxation interval does not enlarge the catalogue. Joint affine
    elimination includes g=receiver_front-length/2. No new numerical solver is
    needed for a singleton intersection; unprovided dynamics remain unknown.
    """
    g = row['public_goal_xy_m'][0]
    admitted = row['initial_stroke_necessary_in_blueprint']
    candidates = [g]  # This fixed edge has one original catalogue goal.
    scores = {g: row['declared_public_translation_m']}
    enumerated = min((x for x in candidates if admitted), key=scores.get, default=None)
    affine_goal = row['receiver_front_x_m']-row['object_size_m'][0]/2
    need(abs(g-affine_goal) < 1e-10, 'Exact original catalogue docking equality')
    joint = affine_goal if admitted else None
    return dict(domain='same fixed object/source/receiver original catalogue singleton',
                objective='nominal public box translation only, m; NOT full task cost',
                fixed_geometric_goal=g if admitted else None,
                full_catalogue_enumeration_goal=enumerated,
                sequential_affine_intersection_goal=joint,
                nominal_joint_affine_elimination_goal=joint,
                goals_agree=enumerated == joint == (g if admitted else None),
                genuine_continuous_goal_degrees_of_freedom=0,
                successful_elapsed_s=None, successor_preparation_cost_s=None,
                total_navigation_cost_s=None, dispatch=False)


def load_owner(manifest_path, *, expected_sha256):
    """Explicit current-source pins, not a production package/host selection."""
    manifest_path = Path(manifest_path)
    need(sha(manifest_path) == expected_sha256, 'Inspection manifest drift; explicit review required')
    manifest = json.loads(manifest_path.read_text())
    need(manifest['schema'] == 'reach-ainav-current-source-inspection-v1', 'Explicit inspection scope')
    for item in manifest['source_files']:
        need(sha(item['path']) == item['sha256'], 'Owner source drift; no silent repin')
    need(sha(manifest['public_projection_path']) == manifest['public_projection_sha256'],
         'Public geometry projection drift')
    owner_src = Path(manifest['ainav_source_root'])/'src'
    need('ainav' not in sys.modules, 'Use a clean analysis process; do not override imported owner')
    old_path = sys.path[:]
    try:
        sys.path.insert(0, str(owner_src))
        scene_mod = importlib.import_module('ainav.scene_intents')
        arithmetic = importlib.import_module('ainav.initial_stroke_facts')
        contracts = importlib.import_module('ainav.native.placement_contract')
    finally:
        sys.path[:] = old_path
    expected = {str(Path(v['path']).resolve()): v['sha256'] for v in manifest['source_files']}
    for name, module in tuple(sys.modules.items()):
        if name == 'ainav' or name.startswith('ainav.'):
            path = str(Path(module.__file__).resolve())
            need(path in expected and sha(path) == expected[path], 'Unpinned owner dependency')
    return manifest, scene_mod, arithmetic, contracts


def evaluate(manifest_path, *, expected_sha256):
    manifest, scene_mod, arithmetic, contracts = load_owner(manifest_path, expected_sha256=expected_sha256)
    raw = json.loads(Path(manifest['public_projection_path']).read_text())
    scene = scene_mod.DeclaredScene.from_transfer(raw)
    original = arithmetic.public_initial_push_arithmetic(scene)
    constants = manifest['source_native_constants']
    need(original['original_library_drive_max_inclusive_m'] == constants['maximum_drive_m'] == .8
         and original['original_library_drive_min_exclusive_m'] == 0.
         and constants['native_stop_offset_m'] == .11, 'Original stroke semantics')
    objects = {o.ref: o for o in scene.objects}; surfaces = {s.ref: s for s in scene.surfaces}
    rows = []
    for item in original['candidates']:
        obj = objects[item['target_ref']]; params = item['parameters']; source = surfaces[obj.support_ref]
        g = (params['goal_world_x_m'], params['goal_world_y_m'])
        receivers = [s for s in scene.surfaces
                     if abs(s.bounds_xy[0]-g[0]-obj.size_m[0]/2) < 1e-9
                     and s.top_z_m+1e-9 >= source.top_z_m+obj.size_m[2]
                     and s.bounds_xy[2]+obj.size_m[1]/2 <= g[1] <= s.bounds_xy[3]-obj.size_m[1]/2]
        need(receivers, 'Original catalogue goal must have its declared receiver')
        contract = contracts.PlacementContract(obj.ref, g, g[0]+obj.size_m[0]/2, obj.size_m,
                                              source.top_z_m, .11, 'declared_native_stop_offset')
        delta = contract.drive_goal_xy_m[0]-obj.center_xy[0]
        need(abs(delta-item['declared_initial_native_drive_m']) < 1e-9, 'Owner goal-to-drive disagreement')
        for receiver in receivers:
            interval = goal_interval(obj.center_xy[0], offset=.11, drive_max=.8)
            row = dict(object_ref=obj.ref, source_ref=obj.support_ref, receiver_ref=receiver.ref,
                       source_height_m=source.top_z_m, receiver_height_m=receiver.top_z_m,
                       object_size_m=list(obj.size_m), initial_center_xy_m=list(obj.center_xy),
                       public_goal_xy_m=list(g), drive_goal_xy_m=list(contract.drive_goal_xy_m),
                       receiver_front_x_m=receiver.bounds_xy[0],
                       declared_public_translation_m=g[0]-obj.center_xy[0],
                       declared_native_drive_m=delta, nominal_goal_relaxation=interval,
                       initial_stroke_necessary_in_blueprint=0 < delta <= .8,
                       current_stroke_necessary=None, native_admitted=None,
                       nominal_goal_realization_assumed=True,
                       nominal_push_approach_xy_m=[obj.center_xy[0]-obj.size_m[0]/2-.58, obj.center_xy[1]],
                       nominal_successor_box_climb_approach_xy_m=[g[0]-obj.size_m[0]/2-1.05, g[1]],
                       nominal_receiver_climb_approach_xy_m=[receiver.bounds_xy[0]-.95,
                                                          (receiver.bounds_xy[2]+receiver.bounds_xy[3])/2],
                       nominal_box_to_receiver_rise_m=receiver.top_z_m-source.top_z_m-obj.size_m[2],
                       axis_aligned_realized_x_error_slice=aligned_final_interval(g[0], offset=.11,
                           public_tol=contract.public_XY_tolerance_m, dock_tol=contract.original_dock_tolerance_m,
                           native_tol=contract.original_native_settled_distance_m),
                       original_placement_contract_sha256=contract.sha256,
                       actual_after_Finish_state=None, actual_successor_ready=None,
                       physical_dispatch=False)
            row['later_receiver_stage'] = receiver_stage(source.top_z_m, obj.size_m[2], receiver.top_z_m)
            row['nominal_receiver_climb_approach_scope'] = 'ONLY_IF_RECEIVER_CLIMB_IS_LATER_SELECTED; not an executed reference'
            row['support_geometry'] = support_projection(g, obj.size_m, source.bounds_xy, receiver.bounds_xy)
            row['same_problem_baselines'] = fixed_edge_baselines(row)
            rows.append(row)
    groups = defaultdict(list)
    for row in rows:
        groups[(row['source_ref'], row['receiver_ref'])].append(row)
    return dict(schema='reach-ainav-target-demand-inspection-v1',
                role='PUBLIC_BLUEPRINT_NOMINAL_SOURCE_INSPECTION_NOT_RUNTIME_ADMISSION',
                independent_of_research_WM=True, frozen_complete_host_selected_by_Reach=False,
                original_catalogue_and_arithmetic_executed=True, catalogue_entries_filtered=False,
                original_arithmetic_candidate_count=len(original['candidates']), rows=rows,
                source_receiver_groups=[dict(source_ref=k[0], receiver_ref=k[1],
                    original_goals=len(v), blueprint_stroke_pass=sum(r['initial_stroke_necessary_in_blueprint'] for r in v),
                    blueprint_stroke_fail=sum(not r['initial_stroke_necessary_in_blueprint'] for r in v))
                    for k, v in sorted(groups.items())],
                physical_steps=0, model_forward_calls=0, API_calls=0, physical_dispatch=False,
                prediction_of_unexecuted_success=None, actual_navigation_improvement=None,
                source_manifest_sha256=expected_sha256)
