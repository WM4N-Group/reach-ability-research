"""OFFLINE outcome analysis for Data-owned closed Dev captures, never prediction.

Reuse Data journal verification, interval accounting and evaluation validation.
Do not generate labels, launch branches, fit a model, or return a planner action.
Table minima are retrospective references, not an implementable causal policy.
"""
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import importlib
import json
import math
from pathlib import Path
import sys
from .analysis_paths import resolve as analysis_path

DATA_ROOT=Path('/home/yuanyue/main/work/data-team/consumer-deliveries/IROS2027-Common-V9-B-Phase-Capture-Evaluation-CPU-20261112-v1')
PINS={
    'src/phase_capture.py':'1b087ad4684791c11636c663813acd8a397786edc96a6b9318e84aa2193e0465',
    'src/verify_capture.py':'0816f911d361e259fdafc458dd3de96e723abb05584747c25551b4eca60daefd',
    'src/vendor/evaluation_contract.py':'5bbdb098c19997356a85080ec3e0e0b1edbfce229661c5ec25a487a5bca4c33e',
    'src/vendor/exact_acquisition_state.py':'f6a0b40112bfe1425aee5e9ddfa19fd5031cff3f9a44df4a4bc2582004bdf41c',
}
VERSION='go2-piper-mission-v9-ae1c724-full4'
DISTANCES=(.2,.4,.6)


def need(x,message):
    if not x:raise ValueError(message)


def sha(path):return hashlib.sha256(analysis_path(path).read_bytes()).hexdigest()


def read_pinned(path,expected):
    path=analysis_path(path);need(path.is_file() and path.stat().st_size<=8*1024*1024,'Bounded published artifact required')
    raw=path.read_bytes();need(hashlib.sha256(raw).hexdigest()==expected,'Artifact SHA changed; do not silently repin')
    return json.loads(raw)


@contextmanager
def data_components():
    """Only imports sealed passive stdlib modules; avoids module-name collisions."""
    for name,digest in PINS.items():need(sha(DATA_ROOT/name)==digest,'Data component changed; explicit new adapter required')
    names=('phase_capture','verify_capture','vendor','vendor.evaluation_contract','vendor.exact_acquisition_state')
    old_modules={name:sys.modules.pop(name) for name in names if name in sys.modules};old_path=sys.path[:]
    try:
        sys.path.insert(0,str(analysis_path(DATA_ROOT)/'src'))
        phase=importlib.import_module('phase_capture');verification=importlib.import_module('verify_capture')
        evaluation=importlib.import_module('vendor.evaluation_contract')
        yield phase,verification,evaluation
    finally:
        for name in names:sys.modules.pop(name,None)
        sys.modules.update(old_modules);sys.path[:]=old_path
        for name,digest in PINS.items():need(sha(DATA_ROOT/name)==digest,'Read-only Data source changed during analysis')


def consume_closed(*,sidecar,sidecar_pins,evaluation_path,evaluation_sha256,purpose,allow_fixture=False):
    """No synthetic-to-real relabeling or train/norm permission from this adapter.

    Hash-chain verification is evidence-integrity only, not full runtime/command
    qualification. New real sidecar must already be admitted by Data; this
    consumer does not issue or take over its qualification/authorization.
    """
    need(purpose=='offline_dev_outcome_analysis','PRIVATE/LABEL cannot become current planner input or training data')
    sidecar=analysis_path(sidecar);need(set(sidecar_pins)=={'identity.json','closure.json','events.jsonl'},'Independent sidecar identity/closure/journal pins required')
    for name,h in sidecar_pins.items():need(sha(sidecar/name)==h,'Published sidecar changed')
    identity=json.loads((sidecar/'identity.json').read_text());evaluation=read_pinned(evaluation_path,evaluation_sha256)
    need(identity['provenance']!='EXPLICIT_FIXTURE' or allow_fixture,'Explicit fixture opt-in required')
    need(evaluation['schema']=='mission-v9-phase-evaluation-v1' and evaluation['role']=='PRIVATE','Consume owner evaluation, not new success definitions')
    need(evaluation['provenance']==identity['provenance'],'Fixture/capture role mismatch')
    result=_closed_evaluation_core(sidecar,identity,evaluation)
    for name,h in sidecar_pins.items():need(sha(sidecar/name)==h,'Sidecar modified while being consumed')
    need(sha(evaluation_path)==evaluation_sha256,'Evaluation changed during consumption')
    result['source_receipt']=dict(evaluation_path=str(evaluation_path),evaluation_sha256=evaluation_sha256,
                                  sidecar=str(sidecar),sidecar_pins=deepcopy(sidecar_pins))
    return result


def _closed_evaluation_core(sidecar,identity,evaluation):
    with data_components() as (phase,verification,validator):
        integrity=verification.verify_closed(sidecar)
        validator.validate_evaluation(evaluation['base_evaluation'])
        journal=[json.loads(line) for line in (sidecar/'events.jsonl').read_text().splitlines()]
        bound=[r for r in journal if r['kind']=='CANDIDATE_BOUND'];need(len(bound)==1,'Exactly one immutable selected-goal binding')
        d=bound[0]['distance_m'];need(d in DISTANCES and bound[0]['frame']=='WORLD_POSITIVE_X','No action expansion/frame reinterpretation')
        need(bound[0]['original_goal_sha256']==identity['original_goal_sha256'],'Native goal binding cannot drift')
        events=[r for r in journal if r['kind'] in phase.KINDS]
        expected=phase.timeline_summary(events)
        need(expected==evaluation['stage_intervals'],'Evaluation intervals must match actual closed event clock, not copied outcome times')
        base=evaluation['base_evaluation'];base_id=base['identity']
        need(base_id['role']=='seen_Dev','This adapter only consumes predeclared seen-Dev evaluation, not holdout/training reclassification')
        for name in ('run_id','branch_id','scene_id','executor_version','provenance'):
            need(base_id[name]==identity[name],'Evaluation branch/sidecar identity mismatch')
        native=next((e for e in events if e['kind']=='NATIVE_RECEIPT'),None)
        if base['native_terminal_valid']:
            need(native is not None,'Cannot fabricate native failure/success without original receipt')
            need(base['native_terminal']=={k:native['payload'][k] for k in ('original_option_sha256','original_receipt_sha256','status')},'Original native receipt disagrees with evaluation')
        finish=next((e for e in events if e['kind']=='FINISH_END'),None)
        if evaluation['normal_Finish_complete']['valid']:
            need(finish is not None and evaluation['normal_Finish_complete']['value']==(finish['payload']['phase']=='success'), 'Finish status must match original event')
        # This published schema explicitly does not carry complete actor/source
        # readiness. Do not silently promote a new ready flag under old version.
        need(evaluation['actual_next_ready']['valid'] is False and evaluation['actual_next_ready']['value'] is None,
             'Data-v1 cannot certify full next-ready; a new owner schema/adapter is required')
        result=normalize_evaluation(evaluation,identity,d,phase.sum_disjoint)
        exit_events=[event for event in events if event['kind']=='EXIT_GEOMETRY']
        need(len(exit_events)<=1,'Do not pick a favorable exit state among repeated samples')
        result['observed_exit_projection_diagnostic']=None
        if exit_events:
            event=exit_events[0];payload=event['payload']
            closure=json.loads((sidecar/'closure.json').read_text())
            evidence=[x for x in closure['exact_stage_state_evidence']
                      if x['physical_tick']==event['physical_tick'] and x['compressed_sha256']==payload['private_state_evidence_sha256']]
            need(len(evidence)==1 and payload['sample_physical_tick']==event['physical_tick'], 'Exit projection must join an exact, verified stage-state artifact')
            finish_event=next((x for x in events if x['kind']=='FINISH_END'),None)
            need(finish_event is not None and event['time_s']>=finish_event['time_s'],'No PUSH-end or earlier geometry borrowed as exit')
            result['observed_exit_projection_diagnostic']=exit_projection_diagnostic(payload,
                registered_geometry=registered_B_geometry(),purpose='offline_dev_outcome_analysis')
        result['integrity']=integrity
    return result



def normalize_evaluation(evaluation,identity,distance,sum_disjoint):
    """Derived measurements, not a replacement label evaluator.

    Inputs have owner validation above. This pure function is separately tested
    on explicit software fixtures without relabeling them as captured outcomes.
    """
    need(identity['executor_version']==VERSION and identity['contract_version']=='0.1.1','Version-bound evaluation only')
    need(identity['provenance'] in ('EXPLICIT_FIXTURE','QUALIFIED_NEW_CAPTURE'),'No historical audit as new captured branch')
    base=evaluation['base_evaluation'];times=evaluation['stage_intervals']
    push=base['metrics']['PUSH_success'];finish=evaluation['normal_Finish_complete']
    terminal=base['native_terminal'] if base['native_terminal_valid'] else None
    completed=bool(base['command_steps']>0 and base['status']=='COMPLETED' and terminal and terminal['status']=='succeeded' and push==dict(value=True,valid=True)
                   and finish==dict(value=True,valid=True) and base['measured_guard_stop'] is None and not base['censored'])
    q=times.get('query_to_native_receipt');native=times.get('native_push_including_finish');successor=times.get('successor_preparation')
    query_cost=native_cost=handover_cost=repair=None
    missing=[]
    if completed and q is not None and native is not None:
        # Validates original attempt/clock/length, does not add overlapping totals.
        need(q['observed_not_prediction'] is True and native['observed_not_prediction'] is True,'Observed intervals only; no forecast as measured duration')
        sum_disjoint([q]);sum_disjoint([native])
        need(q['clock_id']==native['clock_id'] and q['attempt_id']==native['attempt_id'],'One attempt/clock for measured stage costs')
        need(q['start_s']<=native['start_s'] and abs(q['end_s']-native['end_s'])<1e-9,'Native PUSH is suffix of query->receipt, not another trial')
        query_cost=q['seconds'];native_cost=native['seconds']
        if successor is not None:
            sum_disjoint([successor]);sum_disjoint([q,successor])
            need(successor['observed_not_prediction'] is True,'Observed successor-preparation endpoint required')
            # Includes any real waiting gap after receipt; no zero-fill of it.
            repair=successor['end_s']-q['end_s'];handover_cost=successor['end_s']-q['start_s']
            need(math.isfinite(handover_cost) and repair>=0,'Finite observed handover cost')
        else:missing.append('observed_successor_preparation_end')
    else:missing.append('successful_PUSH_and_normal_Finish_with_matched_stage_intervals')
    return dict(schema='reach-offline-observed-handover-v1',analysis_role='OFFLINE_DEV_EVALUATION_ONLY',
                provenance=identity['provenance'],identity=deepcopy(identity),distance_m=distance,
                status=base['status'],command_steps=base['command_steps'],
                PUSH_and_normal_Finish_complete=completed,native_push_including_Finish_s=native_cost,
                query_to_native_receipt_s=query_cost,receipt_to_successor_preparation_end_s=repair,
                query_to_successor_preparation_end_s=handover_cost,
                comparison_endpoint='OBSERVED_SUCCESSOR_PREPARATION_PROGRAM_END_NOT_ACTOR_READY',
                original_entry_check=deepcopy(evaluation['original_next_entry_check']),actual_next_ready=None,
                full_task_success=deepcopy(base['metrics']['full_task_success']),
                measured_guard_stop=base['measured_guard_stop'] is not None,censored=base['censored'],
                missing_comparable_endpoint=missing,
                early_failure_is_not_faster_success=True,no_Finish_double_count=True,
                evidence_scope='selected PUSH segment, not whole-prefix wall/sim budget',
                online_input_allowed=False,fit_norm_training_allowed=False,execution_authorized=False)


def retrospective_compare(records,*,comparison_scope):
    """Exact finite-table references: never causal planner choices.

    Same public hash or event family is NOT an independent proof of same hidden
    state. A controlled/matched scope needs an external design/equivalence ref;
    otherwise raw rankings are descriptive observations only, no treatment gain.
    """
    need(records,'At least one observed record required')
    need(comparison_scope.get('purpose')=='offline_dev_outcome_analysis','No outcome table as live effect model')
    ids=[(r['identity']['run_id'],r['identity']['attempt_id']) for r in records]
    need(len(ids)==len(set(ids)),'Do not count one attempt twice')
    kinds={r['provenance'] for r in records};need(len(kinds)==1,'Synthetic and captured data must not be pooled')
    for k in ('executor_version','contract_version','scene_id','model_sha256','program_sha256','guard_profile_sha256'):
        need(len({r['identity'][k] for r in records})==1,'Same frozen executor/model/program/profile required for comparison: '+k)
    distances=[r['distance_m'] for r in records];need(all(d in DISTANCES for d in distances),'Unexposed distances')
    # More repetitions are not silently averaged, resampled or selected by outcome.
    need(len(distances)==len(set(distances)),'One predeclared branch per candidate; repeats need a separate design')
    source_refs=comparison_scope.get('state_equivalence_evidence_refs')
    matched=bool(comparison_scope.get('controlled_initial_state_design') is True and type(source_refs) is list and bool(source_refs)
                 and all(isinstance(x,str) and x for x in source_refs))
    basis='DECLARED_CONTROLLED_MODEL_FIXTURE' if kinds=={'EXPLICIT_FIXTURE'} and matched else 'DECLARED_CONTROLLED_DEV_SCOPE_NOT_PROVEN_BY_THIS_ANALYZER' if matched else 'OBSERVATIONAL_UNMATCHED_PREFIX_STATE'
    completed=[r for r in records if r['PUSH_and_normal_Finish_complete']]
    handover=[r for r in completed if r['query_to_successor_preparation_end_s'] is not None]
    operation=[r for r in completed if r['native_push_including_Finish_s'] is not None]
    best_op=min(operation,key=lambda r:(r['native_push_including_Finish_s'],r['distance_m'])) if operation else None
    best_h=min(handover,key=lambda r:(r['query_to_successor_preparation_end_s'],r['distance_m'])) if handover else None
    fixed_distance=comparison_scope.get('fixed_reference_distance_m')
    need(fixed_distance in DISTANCES,'Explicit fixed-distance REFERENCE required; not a new online fallback')
    fixed=next((r for r in records if r['distance_m']==fixed_distance),None)
    full=sorted(distances)==list(DISTANCES) and len(handover)==3
    disagreement=None
    if best_op is not None and best_h is not None and best_op['query_to_successor_preparation_end_s'] is not None:
        disagreement=dict(operation_reference_distance_m=best_op['distance_m'],handover_reference_distance_m=best_h['distance_m'],
            differs=best_op['distance_m']!=best_h['distance_m'],
            observed_endpoint_cost_difference_s=best_op['query_to_successor_preparation_end_s']-best_h['query_to_successor_preparation_end_s'],
            inference='retrospective reference difference, NOT an online policy effect or task success gain')
    def reference(row,key):
        return None if row is None or row.get(key) is None else dict(distance_m=row['distance_m'],cost_s=row[key],source_attempt_id=row['identity']['attempt_id'])
    return dict(schema='reach-offline-finite-handover-comparison-v1',scope_basis=basis,
                matched_state_declared=matched,matched_state_certified_by_analyzer=False,
                all_three_observed_complete_endpoints=full,observed_candidate_distances_m=sorted(distances),
                missing_distances_m=[d for d in DISTANCES if d not in distances],
                missing_handover_endpoint_distances_m=[d for d in DISTANCES if not any(r['distance_m']==d for r in handover)],
                fixed_reference=reference(fixed,'query_to_successor_preparation_end_s'),
                operation_cost_only_retrospective_minimum=reference(best_op,'native_push_including_Finish_s'),
                full_enumeration_retrospective_minimum=reference(best_h,'query_to_successor_preparation_end_s'),
                enumeration_scope='ALL_THREE_MEASURED_COMPLETE_ENDPOINTS' if full else 'MEASURED_COMPLETE_SUBSET_ONLY_NO_MISSING_CANDIDATE_IMPUTATION',
                reference_disagreement=disagreement,
                denominator=dict(attempts=len(records),issued_segments=sum(r['command_steps']>0 for r in records),
                                 PUSH_and_Finish_completions=len(completed),comparable_preparation_endpoints=len(handover),
                                 known_actual_next_ready=0),
                result_role='EXPLICIT_FIXTURE_NOT_ROBOT_DATA' if kinds=={'EXPLICIT_FIXTURE'} else 'OFFLINE_OBSERVED_DEV_NOT_PREDICTED',
                causal_method_gain_established=False,fit_or_training_permitted=False,
                best_online_action=None,execution_authorized=False,
                comparison_endpoint='successor preparation PROGRAM end, not native Actor readiness',
                task_success_rate_effect_established=False)


def consume_lifecycle(*,lifecycle_path,lifecycle_sha256,sidecar,sidecar_pins,purpose,allow_fixture=False):
    """Read closed Data lifecycle including faults, no re-running its fixture.

    An incomplete raw-command journal stays INCOMPLETE_EVIDENCE with the actual
    observed/persisted counters. It does not become not-run or a fast success.
    """
    need(purpose=='offline_dev_outcome_analysis','Outcome labels cannot become online inputs or model fit')
    lifecycle=read_pinned(lifecycle_path,lifecycle_sha256)
    need(lifecycle['schema']=='data-branch-lifecycle-closure-v1','Owner lifecycle schema required')
    if lifecycle['provenance']=='EXPLICIT_FIXTURE':need(allow_fixture,'Fixture opt-in required')
    sidecar=analysis_path(sidecar)
    need(set(sidecar_pins)=={'identity.json','closure.json','events.jsonl'},'Independently pinned closed sidecar required')
    for name,h in sidecar_pins.items():need(sha(sidecar/name)==h,'Owner closed sidecar changed')
    identity=json.loads((sidecar/'identity.json').read_text())
    need(identity['provenance']==lifecycle['provenance'] and identity['branch_id']==lifecycle['branch_id'],'Lifecycle/sidecar role identity mismatch')
    capture=lifecycle['evaluation'];observed=capture['observed_original_issued_count'];persisted=capture['persisted_raw_command_count']
    need(type(observed) is int and type(persisted) is int and observed>=persisted>=0,'Observed/persisted action counters must not be reset')
    with data_components() as (_,verification,__):integrity=verification.verify_closed(sidecar)
    if capture['evaluation_error'] is not None or capture['evaluation'] is None or observed!=persisted:
        for name,h in sidecar_pins.items():need(sha(sidecar/name)==h,'Owner incomplete sidecar changed during analysis')
        need(sha(lifecycle_path)==lifecycle_sha256,'Owner incomplete lifecycle changed')
        return dict(schema='reach-closed-lifecycle-intake-v1',analysis_role='OFFLINE_DEV_EVALUATION_ONLY',
            provenance=identity['provenance'],status='INCOMPLETE_EVIDENCE_NOT_NOT_RUN_OR_SUCCESS',
            observed_issued_count=observed,persisted_issued_count=persisted,
            issued_actions_observed=observed>0,normalized_observation=None,
            original_evaluation_error=capture['evaluation_error'],source_faults=capture['source_faults'],
            integrity=integrity,failures=lifecycle['failures'],execution_authorized=False,
            retrospective_choice_or_cost=None)
    result=_closed_evaluation_core(sidecar,identity,capture['evaluation'])
    need(result['command_steps']==persisted,'Selected command denominator must join capture counters')
    for name,h in sidecar_pins.items():need(sha(sidecar/name)==h,'Owner sidecar changed during analysis')
    need(sha(lifecycle_path)==lifecycle_sha256,'Lifecycle changed during consumption')
    return dict(schema='reach-closed-lifecycle-intake-v1',analysis_role='OFFLINE_DEV_EVALUATION_ONLY',
            provenance=identity['provenance'],status='NORMALIZED_OBSERVED_SCOPE',
            observed_issued_count=observed,persisted_issued_count=persisted,
            issued_actions_observed=observed>0,normalized_observation=result,
            original_evaluation_error=None,source_faults=capture['source_faults'],
            failures=lifecycle['failures'],execution_authorized=False,
            original_source_sha256=lifecycle_sha256,retrospective_choice_or_cost=None)


def handover_tradeoff_table(records):
    """Condition for a retrospective ranking reversal; never fit a predictor.

    N_i=native PUSH+Finish, E_i=query-to-native entry/wait cost, R_i=post-receipt
    successor-preparation cost. C_i=N_i+E_i+R_i. If N_i<N_j but C_i>C_j, the
    omitted E+R difference exceeds the operation-time saving. This algebra is
    standard, not a new theorem; empirical frequency may be zero/unknown.
    """
    eligible=[r for r in records if r['PUSH_and_normal_Finish_complete']
              and r['query_to_successor_preparation_end_s'] is not None
              and r['native_push_including_Finish_s'] is not None]
    rows=[]
    for a in eligible:
        for b in eligible:
            if a['distance_m']==b['distance_m']:continue
            native_advantage=b['native_push_including_Finish_s']-a['native_push_including_Finish_s']
            if native_advantage<=0:continue
            omitted_a=a['query_to_successor_preparation_end_s']-a['native_push_including_Finish_s']
            omitted_b=b['query_to_successor_preparation_end_s']-b['native_push_including_Finish_s']
            rows.append(dict(faster_native_distance_m=a['distance_m'],slower_native_distance_m=b['distance_m'],
                native_time_saving_s=native_advantage,omitted_entry_plus_handover_difference_s=omitted_a-omitted_b,
                observed_completion_order_reversed=omitted_a-omitted_b>native_advantage,
                endpoint='successor preparation program end, not actual Actor readiness',
                offline_table_relation_only=True))
    return rows


def exit_projection_diagnostic(payload,*,registered_geometry,purpose):
    """Offline, original LABEL geometry -> task-related measured projections.

    Not a full contact certificate and never fed to current planner/model.
    Registered native CLIMB B uses box CENTER minus registered length/2;
    min(corner_x) is kept separately and NOT silently substituted for that rule.
    """
    need(purpose=='offline_dev_outcome_analysis','Actual exit LABEL geometry is evaluation-only')
    need(payload['stage']=='AFTER_NORMAL_FINISH' and payload['frame']=='WORLD_POSITIVE_X'
         and payload['derived_from_requested_goal'] is False,'Exact exit phase/frame/role required')
    corner=payload['box_corners_world_xyz_m'];feet=payload['robot_support_footprint_world_xy_m']
    need(len(corner)==8 and all(len(v)==3 and all(type(x) in (float,int) and math.isfinite(x) for x in v) for v in corner),'8 actual corners required')
    need(len(feet)==4 and all(len(v)==2 and all(type(x) in (float,int) and math.isfinite(x) for x in v) for v in feet),'4 actual foot projections required')
    lengths=[registered_geometry[k] for k in ('box_length_m','HIGH_front_m','CLIMB_B_standoff_m','lane_y_m','approach_radius_m','HIGH_dock_tolerance_m')]
    need(all(type(x) in (float,int) and math.isfinite(x) for x in lengths),'Explicit source-bound registered geometry, no guessed thresholds')
    length,H,stand,lane,radius,tol=lengths
    need(registered_geometry.get('source_ref') and length>0 and stand>0 and radius>0 and tol>=0,'Source geometry/reference required')
    xmin=min(p[0] for p in corner);xmax=max(p[0] for p in corner);center=.5*(xmin+xmax)
    native_B_front=center-length/2
    target=[native_B_front-stand,lane]
    base=payload['robot_base_world_xyz_m'];need(len(base)==3 and all(type(x) in (float,int) and math.isfinite(x) for x in base),'Actual base LABEL required')
    distance=math.hypot(base[0]-target[0],base[1]-target[1])
    return dict(role='OFFLINE_LABEL_PROJECTION_NOT_PREDICTION_OR_NATIVE_READY',phase=payload['stage'],
                sample_physical_tick=payload['sample_physical_tick'],source_state_sha256=payload['private_state_evidence_sha256'],
                measured_box_x_projection_m=[xmin,xmax],registered_native_B_center_front_m=native_B_front,
                distinction='native B front=center-registered_length/2; true corner min may differ under box rotation',
                CLIMB_B_original_reference_world_xy_m=target,measured_base_to_original_reference_m=distance,
                direct_approach_margin_m=radius-distance,
                direct_NAV_repair_may_be_needed=distance>radius,whole_PUSH_infeasible=False,
                later_HIGH_actual_corner_projection_gap_m=H-xmax,
                later_HIGH_projection_dock_margin_m=tol-abs(H-xmax),
                B_HIGH_relation_applies_only_when_B_becomes_loaded_source=True,
                foot_footprint_bbox_world_xy_m=[[min(p[0] for p in feet),min(p[1] for p in feet)],
                                               [max(p[0] for p in feet),max(p[1] for p in feet)]],
                source_support_ref=payload['source_support_ref'],
                common_loaded_top_support_and_Actor_gate_verified=False,
                actual_next_ready=None,online_input_allowed=False)


def registered_B_geometry():
    """Use only fixed public source geometry/entry rules, no outcome archive."""
    from .native_climb_continuation import load_requirements
    from .recorded_v9_diagnostics import DOCS,RELEASE_SHA
    release=read_pinned(DOCS/'common_v9_effect_source_release_v1.json',RELEASE_SHA)
    req=load_requirements()
    # The source scene profile is frozen full-4; read length/lane from manifest,
    # HIGH front from the source-derived registered layout, not a future pose.
    manifest=read_pinned(DOCS/'skill_executor_manifest_v0.json','7b467daf8d6eb895bea48f5a68bb96693bc3a8426f8c3123ee8549193b59c1cb')
    return dict(box_length_m=manifest['scene']['profile']['step_length_m'],HIGH_front_m=release['registered_geometry']['high_front'],
                CLIMB_B_standoff_m=req['approach_standoff_m'],lane_y_m=manifest['scene']['profile']['lane_y_m'],
                approach_radius_m=req['limits']['approach_radius_m'],HIGH_dock_tolerance_m=req['later_B_HIGH_docking_tolerance_m'],
                source_ref='source-bound full4 public layout+original CLIMB rules',current_actual_geometry_inferred=False)
