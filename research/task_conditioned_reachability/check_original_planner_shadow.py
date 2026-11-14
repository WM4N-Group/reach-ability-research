"""Connect existing static task evidence to ORIGINAL A* and NAV action types.

Synthetic geometry input, not a robot rollout. No actor/controller or physics.
"""
import argparse
import copy
import importlib
import json
from pathlib import Path
import sys
import time
import traceback

import numpy as np

from piper_kinematics import REPO, sha, no_physics_steps
from navigation_goal_bridge import MODES, select_shadow_goal, as_original_shadow_action
from run_piper_state_height_study import load_frozen_inputs
from task_height_bound import height_bound
from run_piper_task_study import dump


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', required=True, type=Path)
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error('Never overwrite/retry archived shadow run')
    protocol_path = Path(__file__).with_name('original_planner_route_shadow_protocol_v1.json')
    protocol = json.loads(protocol_path.read_text())
    _, _, cached, contract = load_frozen_inputs()
    state_path = REPO/'evidence/2026-10-20/piper-state-height-static-v1/new_state_queries_and_paths.json'
    rows = json.loads(state_path.read_text())
    for r in copy.deepcopy(cached):
        r['state_height_m'] = .33
        r['height_necessary_bound'] = height_bound(contract, r['target_base_m'], r['task_quaternion_base_wxyz'])
        rows.append(r)
    args.output_dir.mkdir(parents=True)
    (args.output_dir/'protocol.original.json').write_bytes(protocol_path.read_bytes())
    sources = [Path(__file__), protocol_path, state_path,
               Path(__file__).with_name('navigation_goal_bridge.py')]
    source_root = REPO/'mujoco/reconfigurable_navigation'
    sources += [source_root/n for n in ['__init__.py','oracle_planner.py','occupancy.py','representations.py','skills/navigate.py','locomotion_runtime.py']]
    dump(args.output_dir/'source_hashes.json', {str(p.relative_to(REPO)): sha(p) for p in sources})
    start = time.perf_counter()
    routes, proposals, error = [], {}, None
    summary = dict(schema='original-planner-static-shadow-integration-v1', status='NOT_COMPLETED',
                   physical_navigation_rollouts=0, physical_success=None, FK_IK_queries=0,
                   physics_steps=0, actor_runs=0, execution_authorized=False)
    try:
        with no_physics_steps():
            sys.path.insert(0, str(REPO/'mujoco'))
            planner_module = importlib.import_module('reconfigurable_navigation.oracle_planner')
            types = importlib.import_module('reconfigurable_navigation.representations')
            if Path(planner_module.__file__).resolve() != source_root/'oracle_planner.py':
                raise RuntimeError('Wrong original planner source')
            planner = planner_module.OraclePlanner()
            box = types.ObjectState(0, types.ObjectType.MOVABLE_BOX,
                np.array([1.1,0,.1]), np.array([1.2,1.2,.2]), movable=True)
            observation = types.OracleObservation(np.array([0.,0.,.33,0.,0.,0.]),
                np.array([.47,0,.1]), (box,), types.Capability())
            route_by_xy = {}
            unique_xy = sorted({tuple(r['body_position_world_m'][:2]) for r in rows})
            if len(unique_xy) != protocol['resources']['max_unique_Astar_calls']:
                raise RuntimeError('Unexpected unique route count')
            for xy in unique_xy:
                if time.perf_counter()-start > protocol['resources']['max_cpu_wall_s']:
                    raise TimeoutError('Original planner static shadow CPU budget reached')
                path = planner._path_between(observation, np.zeros(2), np.array(xy))
                cost = None if path is None else float(sum(np.linalg.norm(b-a) for a,b in zip(path,path[1:])))
                row = dict(target_xy_world_m=list(xy), route_status='unreachable' if path is None else 'reachable',
                           navigation_cost=cost, cost_unit='1m_normalized_original_grid_path_length',
                           original_Astar_grid_center_path=None if path is None else [p.tolist() for p in path])
                routes.append(row)
                route_by_xy[xy] = row
            dump(args.output_dir/'original_Astar_routes.json', routes)
            cost_source = dict(kind='original_planner_route_cost', sha256=sha(args.output_dir/'original_Astar_routes.json'),
                               scope='original_Astar_on_synthetic_geometry_NOT_actual_rollout', normalization_m=1.)
            for h in [.28,.33,.38]:
                state_id = f'static_synthetic_state_height_{h:.2f}'
                candidates = []
                lookup = {}
                for r in rows:
                    if r['state_height_m'] != h:
                        continue
                    route = route_by_xy[tuple(r['body_position_world_m'][:2])]
                    bound = r['height_necessary_bound']['exclusion_gap_m'] > 0
                    task_status = 'found' if r['task_IK_found'] else 'analytic_model_excluded' if bound else 'bounded_solver_miss_UNKNOWN'
                    candidates.append(dict(candidate_id=r['candidate_id'], observed_state_id=state_id,
                        model_body_height_m=h, target_se2_world=[*r['body_position_world_m'][:2], r['body_yaw_rad']],
                        route_status=route['route_status'], navigation_cost=route['navigation_cost'],
                        task_pose_status=task_status, analytic_necessary_excluded=bound,
                        endpoint_rho=r.get('nominal_path',{}).get('endpoint',{}).get('rho'),
                        path_rho=r.get('nominal_path',{}).get('path',{}).get('rho')))
                    lookup[r['candidate_id']] = r
                packet = dict(schema='reachability-navigation-shadow-query-v1', observed_state_id=state_id,
                    observed_body_height_m=h, data_role='static_synthetic_geometry_NOT_robot_episode',
                    navigation_cost_source=cost_source, candidates=candidates)
                selected = []
                for mode in MODES:
                    result = select_shadow_goal(packet, mode)
                    if result['status'] == 'selected_shadow_proposal':
                        action = as_original_shadow_action(result)
                        if type(action) is not types.SkillAction:
                            raise RuntimeError('Not the canonical ORIGINAL SkillAction type')
                        original = lookup[result['candidate_id']]
                        clearance = original.get('nominal_path',{}).get('samples')
                        result.update(original_action_class_identity_verified=True,
                            original_action_skill=action.skill.name, original_action_target=action.target_pose.tolist(),
                            task_IK_found=original['task_IK_found'],
                            sampled_min_model_clearance_m=None if clearance is None else min(s['clearance']['minimum_clearance'] for s in clearance))
                    selected.append(result)
                proposals[str(h)] = dict(input_packet=packet, selections=selected)
            if 'reconfigurable_navigation.locomotion_runtime' in sys.modules or 'torch' in sys.modules:
                raise RuntimeError('Shadow route check unexpectedly imported actor runtime')
            summary.update(status='PASSED_original_planner_and_NAV_type_STATIC_shadow_only',
                unique_original_Astar_calls=len(routes), reachable_unique_xy=sum(r['route_status']=='reachable' for r in routes),
                unreachable_unique_xy=sum(r['route_status']=='unreachable' for r in routes),
                state_count=3, candidates_per_state=75, actor_runtime_imported=False)
    except Exception as exc:
        error = traceback.format_exc()
        summary.update(status='FAILED_preserve_partial_no_retry', error_type=type(exc).__name__, error=str(exc))
    finally:
        summary['cpu_wall_s'] = time.perf_counter()-start
        if not (args.output_dir/'original_Astar_routes.json').exists():
            dump(args.output_dir/'original_Astar_routes.json', routes)
        dump(args.output_dir/'state_packets_and_shadow_proposals.json', proposals)
        dump(args.output_dir/'summary.json', summary)
        if error:
            (args.output_dir/'error.txt').write_text(error)
        print(json.dumps(summary,indent=2))
        for h, ps in proposals.items():
            for s in ps['selections']:
                print(h,s['mode'],s['candidate_id'],s.get('sampled_min_model_clearance_m'))
    return int(error is not None)


if __name__ == '__main__':
    raise SystemExit(main())
