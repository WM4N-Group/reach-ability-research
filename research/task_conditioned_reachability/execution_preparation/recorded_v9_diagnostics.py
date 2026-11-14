"""Consume WM's recorded causal event without offline actual labels or inference.

This is an archived decision-time source diagnostic, NOT a live-state estimate,
not a complete after-Finish model, and not a three-candidate recommendation.
New coordinate semantics are explicitly pinned to contract0.1.1; old API stays.
"""
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys

DOCS=Path('/home/yuanyue/re-nav/GO2-PIPER/docs')
SCRIPTS=Path('/home/yuanyue/re-nav/GO2-PIPER/scripts/piper_world_model')
RELEASE_SHA='0a9df417801a72c335219a926c79a76e0a32bf1180f500b9410d61d033818f65'
CONTRACT_SHA='d5cd295c2bc3f2372f459152fc19e345ea001cf50fbb500471825628f48dd0d5'
READER_SHA='26f3e498b914d37c9902bba155d8d7cc0dc3e97f288dbf91fee83e1341257588'
DEPENDENCY_SHA='48ac58c80d1c09f2693954d4f748dc5ec12aba3ce4d303ee034f5cac10cf8f0a'


def pin(path,expected):
    if hashlib.sha256(path.read_bytes()).hexdigest()!=expected:
        raise ValueError('Published source changed; explicit rebind required')


def load_recorded_owner_sources():
    release=DOCS/'common_v9_effect_source_release_v1.json';pin(release,RELEASE_SHA)
    contract=DOCS/'skill_interface_contract_v0_1_1.json';pin(contract,CONTRACT_SHA)
    c=json.loads(contract.read_text())
    if (c['contract_version']!='0.1.1' or
        c['actions']['PUSH']['parameters']['push_distance_m']['frame']!='registered_world_positive_X_translation_of_selected_box_center'):
        raise ValueError('Do not consume superseded box-local-X interpretation')
    reader=SCRIPTS/'skill_effect_sources_v1/reader.py';pin(reader,READER_SHA)
    pin(SCRIPTS/'skill_interface_v0/reader.py',DEPENDENCY_SHA)
    spec=importlib.util.spec_from_file_location('reach_wm_recorded_v9_owner',reader)
    module=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=module
    old_path=sys.path[:]
    try:
        sys.path.insert(0,str(SCRIPTS));spec.loader.exec_module(module)
        # Owner constructor reads only sealed pre-state, original causal forecast,
        # source/identity receipts; no offline actual-outcome archive is opened.
        source=module.EventEffectSources(release,expected_release_sha256=RELEASE_SHA)
        problem=source.public_problem();rows=source.coverage()
    finally:
        sys.path[:]=old_path
    return problem,rows


def diagnose(problem,rows):
    if (problem.get('instance_kind')!='RECORDED_PRE_DECISION_PUBLIC_STATE_NOT_LIVE' or
        problem.get('contract_version')!='0.1.1' or problem.get('actual_future_used') is not False):
        raise ValueError('Exact recorded public event without actual future required')
    if sorted(row['push_distance_m'] for row in rows)!=[.2,.4,.6]:
        raise ValueError('Exactly 3 exposed source rows required, no invented forecasts')
    result=[]
    for row in rows:
        if (row['frame']!='WORLD_POSITIVE_X' or row['decision_id']!=problem['decision_id'] or
            row['query_input_sha256']!=problem['input_sha256'] or row['object_ref']!=problem['object_ref']):
            raise ValueError('Frame/observation/object identity mismatch')
        goal=row['requested_goal_geometry']
        if goal['provenance']!='REQUEST_GEOMETRY_ONLY_NOT_PREDICTED_TERMINAL':
            raise ValueError('Goal role must remain explicit')
        gap=goal['receiving_front_world_x_m']-goal['requested_forward_face_world_x_m']
        item=dict(push_distance_m=row['push_distance_m'],frame='WORLD_POSITIVE_X',
                  requested_front_world_x_m=goal['requested_front_world_x_m'],
                  requested_forward_face_world_x_m=goal['requested_forward_face_world_x_m'],
                  requested_longitudinal_gap_m=gap,
                  requested_relation='touching_only_no_support_certificate' if abs(gap)<=1e-12 else
                                     'positive_request_gap_not_actual_failure' if gap>0 else
                                     'nominal_request_overlap_not_actual_support',
                  effect_source_status=row['effect']['status'],recorded_forecast_diagnostic=None,
                  after_Finish_state_certified=False,elapsed_for_required_cost_s=None,
                  actual_next_ready=None,rankable=False,feasible=None)
        effect=row['effect']
        if effect['status']=='RECORDED_CAUSAL_FORECAST_EXACT_QUERY_ONLY':
            if effect['other_distances_may_reuse_this_forecast'] is not False or effect['terminal_or_ready_certified'] is not False:
                raise ValueError('No forecast borrowing or readiness promotion')
            value=effect['value'];front=value['box_front_world_x_m'];robotx=value['robot_xy_world_m'][0]
            item['recorded_forecast_diagnostic']=dict(
                predicted_front_world_x_m=front,robot_x_world_m=robotx,
                nominal_longitudinal_overlap_m=front+problem['object_geometry']['length_m']-goal['receiving_front_world_x_m'],
                nominal_relative_coordinate_separation_m=front-robotx,
                predicted_elapsed_s=value['predicted_elapsed_s'],
                elapsed_scope='original terminal option-purpose model, NOT native PUSH+Finish elapsed',
                finite_error_bound=None,model_std_as_error_bound_used=False,
                original_forecast_sha256=effect['source_forecast_sha256'],
                same_recorded_query_only=True,after_Finish_guarantee=False)
        result.append(item)
    return dict(schema='reach-recorded-v9-source-diagnostics-v1',
                contract_version='0.1.1',coordinate_erratum='WORLD +X, not box-local yaw-rotated X',
                public_problem=problem,rows=result,
                causal_forecast_rows=sum(r['recorded_forecast_diagnostic'] is not None for r in result),
                complete_after_Finish_effect_rows=0,
                selection_status='UNKNOWN_MISSING_02_04_EFFECTS_AND_MATCHED_EXIT_COST_READY',
                best_candidate=None,full_selector_called=False,
                reason_not_calling_full_selector='Missing exit-stage/entry/cost requirements; do not fabricate required values',
                source_release_sha256=RELEASE_SHA,corrected_contract_sha256=CONTRACT_SHA,
                live_observation=False,new_model_forward_calls=0,actual_outcome_fields_used=False,
                model_std_calibrated=False,execution_authorized=False,physical_dispatch=False)
