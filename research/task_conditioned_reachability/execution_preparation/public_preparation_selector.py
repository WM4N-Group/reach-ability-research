"""Development selector using the EXISTING AINav finite preparation API.

Pure stdlib; no Data worker/import, simulator, checkpoint, file IO or bind. The
current public interface exposes reference XY but not current base world XY.
Thus it can compute nominal reference geometry, NOT NAV travel/completion costs.
Unknown dynamics lead to explicit abstention or unchanged original-default plan.
Frozen Stage-B source/protocol/worker are not changed by this development module.
"""
from dataclasses import asdict, dataclass, replace
from copy import deepcopy
import math

from .successor_aware_choice import (
    Task, Candidate, Domain, InputSchema, InputValue, DecisionInput, Estimate,
    Costs, evaluate_shared, select_all, digest, need, number, pin,
)

IDS=('original','lateral_plus_0p04','lateral_minus_0p04')
OFFSETS=(0.,.04,-.04)
PAYLOAD_SCHEMA='AINav-finite-CLIMB-preparation-selection-v1'
CONTRACT_SHA='a0d562406bbd3cee57a6c7f57673986d211870d080bc4ed4e0f3bb2e61b62190'
PROFILE_SHA='db43081c7702047844dd7dde6eb7a6b4dbb439b9501925b091c831678e65b697'
PERMISSIONS_SHA='f7823b691fb30537d0556f48aef6d50c01de0a9ec9a946e6fd35d064e7f20b50'
ENTRY_RADIUS_M=.16  # original execution_judge necessary XY envelope, NOT a new gate
NO_MODEL_SHA=digest({'model':'ABSENT_NO_DYNAMIC_COST_OR_NATIVE_ADMISSION_PREDICTOR'})


@dataclass(frozen=True)
class PublicReference:
    """Subset of original registered public reference, never current GT pose.

    Source field is a provenance declaration, not a permission/authenticity proof.
    The actual owner must supply its registered reference, not an audit catalog.
    """
    target_ref: str
    approach_xy: tuple
    source_surface_height_m: float
    registered_climb: bool
    source_ref: str
    def __post_init__(self):
        need(type(self.target_ref) is str and bool(self.target_ref) and
             type(self.source_ref) is str and bool(self.source_ref),'Explicit public registered reference source')
        need(type(self.approach_xy) is tuple and len(self.approach_xy)==2 and
             all(number(v) for v in self.approach_xy),'Finite original public reference XY')
        need(number(self.source_surface_height_m) and self.source_surface_height_m==0.,
             'Existing owner contract is ground-source only')
        need(self.registered_climb is True,'Explicit original registered CLIMB declaration')


@dataclass(frozen=True)
class CompleteSuccessorEstimate:
    """Development predictor result: feasibility is NOT implied by a duration.

    A declared conditional prediction, NOT actual native admission, observed
    outcome, calibrated success probability or permission to train/fit. The
    existing Estimate carries candidate/input/model identities and current gate.
    No Data payload/worker/result schema changes are needed.
    """
    estimate: Estimate
    successor_feasibility: str = 'UNKNOWN'
    successor_scope: str = 'COMPLETE_EXECUTION_AND_ORIGINAL_STOP'
    source_ref: object = None
    role: str = 'PROSPECTIVE_DECLARED_MODEL'
    def __post_init__(self):
        need(type(self.estimate) is Estimate,'Existing candidate/input/model-bound prospective Estimate')
        need(self.role=='PROSPECTIVE_DECLARED_MODEL','No audit outcomes masquerading as complete-successor prediction')
        need(self.successor_feasibility in ('PASS','REFUSED','UNKNOWN'),'Explicit complete-successor feasibility, unknown is not pass')
        need(self.successor_scope=='COMPLETE_EXECUTION_AND_ORIGINAL_STOP',
             'READY/entry/geometry alone is not complete successor execution and original stop')
        need(self.source_ref is None or type(self.source_ref) is str and bool(self.source_ref),
             'Optional predictor provenance is text, not a native/world pointer')
        need(self.successor_feasibility=='UNKNOWN' or self.source_ref is not None,
             'Non-unknown complete successor prediction needs explicit prospective provenance')


@dataclass(frozen=True)
class Problem:
    domain: Domain
    information_schema: InputSchema
    inputs: DecisionInput
    payloads: tuple
    geometry: tuple


def build_problem(reference, *, public_candidates):
    """Call actual owner API, keep its finite semantics and original baseline.

    No release-verifier/wrapper stack. Caller imports the established AINav API
    from its own appropriate source version. No alternative generator or delta.
    """
    need(type(reference) is PublicReference and callable(public_candidates),'Typed public reference and existing owner catalogue API')
    rows=public_candidates(target_ref=reference.target_ref,declared_approach_xy=reference.approach_xy,
        source_surface_height_m=reference.source_surface_height_m,registered_climb=reference.registered_climb)
    need(type(rows) in (tuple,list) and len(rows)==3 and tuple(r['candidate_id'] for r in rows)==IDS,
         'Reuse exactly the original three-candidate pool; no expanded domain')
    payloads=[];geometry=[]
    for row,offset in zip(rows,OFFSETS):
        goal=row['NAV_goal_xy']
        need(type(goal) in (list,tuple) and len(goal)==2 and all(number(v) for v in goal), 'Finite owner NAV reference')
        need(number(row['source_surface_height_m']) and
             row['target_ref']==reference.target_ref and
             tuple(row['original_approach_xy'])==reference.approach_xy and
             tuple(goal)==(reference.approach_xy[0],reference.approach_xy[1]+offset) and
             row['source_surface_height_m']==0. and row['original_CLIMB_READY_goal_unchanged'] is True,
             'Only the published preparation goal changes, never original interaction reference')
        dx=goal[0]-reference.approach_xy[0];dy=goal[1]-reference.approach_xy[1]
        displacement=math.hypot(dx,dy)
        need(math.isfinite(displacement),'Finite static reference displacement')
        payloads.append(dict(schema=PAYLOAD_SCHEMA,target_ref=reference.target_ref,candidate_id=row['candidate_id']))
        geometry.append(dict(candidate_id=row['candidate_id'],NAV_goal_xy=list(goal),
            original_CLIMB_reference_xy=list(reference.approach_xy),
            nominal_reference_displacement_m=displacement,
            nominal_reference_inside_original_XY_disk=displacement<=ENTRY_RADIUS_M,
            nominal_reference_center_margin_m=ENTRY_RADIUS_M-displacement,
            frame='WORLD_REGISTERED_STATIC_REFERENCE_NOT_CURRENT_BASE_POSE',
            geometric_status='NOMINAL_REFERENCE_GEOMETRY_ONLY',
            native_current_feasibility='UNKNOWN',current_NAV_travel_distance_m=None,
            support_collision_or_tracking_bound='UNKNOWN',
            NAV_composite_completion_s=None,full_successor_completion_s=None,
            geometry_margin_is_not_tracking_slack_or_cost=True))
    need(len({tuple(g['NAV_goal_xy']) for g in geometry})==3,
         'Nominal goals numerically alias; do not call payload labels distinct controls')
    schema=InputSchema('AINav:'+PERMISSIONS_SHA+':minimal-registered-reference',(
        ('registered_CLIMB.target_ref','ONLINE_PUBLIC',('HIGH_LEVEL_PLANNER',)),
        ('registered_CLIMB.approach_xy','ONLINE_PUBLIC',('HIGH_LEVEL_PLANNER',)),
        ('registered_CLIMB.source_surface_height_m','ONLINE_PUBLIC',('HIGH_LEVEL_PLANNER',)),
        ('registered_CLIMB.is_declared','ONLINE_PUBLIC',('HIGH_LEVEL_PLANNER',)),
    ))
    task=Task('same-ground-PUSH-then-selected-CLIMB',
        digest({'contract':CONTRACT_SHA,'same_original_interaction_terminal':True}),
        digest({'profile':PROFILE_SHA,'original_gates_unchanged':True}),
        'FRESH_HOST_PREEXECUTION_IMMUTABLE_PREPARATION_PLAN',schema.sha256)
    candidates=tuple(Candidate(p['candidate_id'],task.sha256,PROFILE_SHA,
        'climb_preparation_candidates:selection_from_payload:'+digest(p),
        'DECLARED_PAYLOAD_NOT_PROVEN_MOTOR_DIFFERENCE:'+digest(p),
        'original' if p['candidate_id']=='original' else 'owner_registered_alternative') for p in payloads)
    # Software prototype role: native qualification is independent. Never promote
    # a geometric nominal test into an original online native admission predicate.
    domain=Domain(task,candidates,'original',None,'CPU_TEST_ONLY')
    values=(reference.target_ref,list(reference.approach_xy),reference.source_surface_height_m,True)
    inputs=DecisionInput(task.sha256,schema.sha256,0.,'HIGH_LEVEL_PLANNER',
        tuple(InputValue(field[0],deepcopy(value),'ONLINE_PUBLIC',0.,reference.source_ref)
              for field,value in zip(schema.fields,values)))
    schema.validate(inputs)
    return Problem(domain,schema,inputs,tuple(payloads),tuple(geometry))


def with_public_observation(problem, observation, *, now_s, source_role):
    """Wire actual permitted current measurements into the SAME selector API.

    Existing raw Observation.value in, existing Problem/DecisionInput out; no new
    owner contract or Data log. Stale/missing/clock-ambiguous measurements are
    rejected here so the caller can use information_action's bounded refresh.
    Dynamic measurements never become native admission or future cost estimates.
    At nonzero clock the resulting problem is EVALUATION-ONLY: the current AINav
    binder cannot consume a live replan by pretending it is a fresh-host plan.
    """
    from .public_information import public_snapshot
    need(type(problem) is Problem,'Existing same-domain problem')
    need(all(v.name.startswith('registered_CLIMB.') for v in problem.inputs.values),
         'Attach one fresh snapshot to the original reference problem, not accumulated/reused history')
    snapshot=public_snapshot(observation,now_s=now_s,source_role=source_role)
    need(snapshot['fresh_complete_kinematic_measurement'] is True,
         'Public measurement unresolved: '+snapshot['status']+'; use bounded information_action')
    target=problem.payloads[0]['target_ref'];center=problem.geometry[0]['original_CLIMB_reference_xy']
    declared=observation['declared_map']
    need(type(declared) is dict and type(declared.get('anchors')) is list,
         'Original public declared-map anchor list')
    matches=[a for a in declared['anchors'] if type(a) is dict and a.get('target_ref')==target]
    need(len(matches)==1,'Unique original public task-reference anchor; no nearest/different target')
    xyz=matches[0].get('position_xyz_m')
    need(type(xyz) is list and len(xyz)==3 and all(number(v) for v in xyz) and
         xyz==list(center)+[0.], 'Observation reference/frame differs from the registered same-task reference')
    source='AINav_CURRENT_PUBLIC_OBSERVATION:'+snapshot['source_observation_sha256']
    extra=[]
    for key,value in sorted(snapshot['public_vectors'].items()):
        extra.append(('public_state.'+key,deepcopy(value),'ONLINE_PUBLIC',source))
    for key,value in sorted(snapshot['descriptors'].items()):
        extra.append(('derived_public.'+key,value,'UNKNOWN' if value is None else 'ONLINE_PUBLIC',
                      'DERIVED_ONLY_FROM_PUBLIC_PROPRIO:'+snapshot['source_observation_sha256']))
    fields=problem.information_schema.fields+tuple((name,visibility,('HIGH_LEVEL_PLANNER',))
                                                  for name,_,visibility,_ in extra)
    schema=InputSchema(problem.information_schema.owner_declaration_ref+':current-publisher-45D-and-public-derivations',fields)
    task=replace(problem.domain.task,information_schema_sha256=schema.sha256,
        decision_boundary=('FRESH_HOST_PREEXECUTION_IMMUTABLE_PREPARATION_PLAN' if now_s==0. else
                           'LIVE_PUBLIC_INFORMATION_EVALUATION_ONLY_NO_HOT_INSTALL'))
    candidates=tuple(replace(c,task_sha256=task.sha256) for c in problem.domain.candidates)
    domain=Domain(task,candidates,problem.domain.original_id,problem.domain.direct_id,problem.domain.role)
    values=tuple(deepcopy(problem.inputs.values))+tuple(InputValue(name,value,visibility,
        snapshot['packet_time_s'],provenance) for name,value,visibility,provenance in extra)
    inputs=DecisionInput(task.sha256,schema.sha256,now_s,'HIGH_LEVEL_PLANNER',values)
    schema.validate(inputs)
    return Problem(domain,schema,inputs,deepcopy(problem.payloads),deepcopy(problem.geometry))


def choose(problem, *, method='successor_aware', evaluator=None, evaluator_sha256=None,
           on_unknown='original_default', max_wall_s=5.):
    """Executable same-domain selector, conditional on actual supplied estimates.

    A future prospective evaluator may use ONLY this explicit public input and
    common candidate. Its external side effects/source must be qualified by its
    implementation owner. No predictor exists by default; original native gates
    still run. The optional seam does NOT authorize training, WM or audit fitting.
    """
    need(type(problem) is Problem,'Existing typed finite problem')
    need(method in ('original_fixed','current_greedy','successor_aware'),'Existing common baselines only; direct stow is shared substrate')
    need(on_unknown in ('original_default','abstain'),'Explicit unknown fallback, not a hidden optimized choice')
    model_supplied=evaluator is not None
    if evaluator is None:
        need(evaluator_sha256 is None,'No invented model identity when predictor is absent')
        model_pin=NO_MODEL_SHA
        def unavailable(inputs,candidate):
            return Estimate(candidate.sha256,inputs.sha256,model_pin,'UNKNOWN','CPU_TEST_ONLY',Costs())
        evaluator=unavailable
    else:
        need(callable(evaluator) and pin(evaluator_sha256),'Explicit prospective evaluator identity')
        model_pin=evaluator_sha256
    supplied=evaluator;successor_rows={}
    def common_evaluation(inputs,candidate):
        # Call the prospective implementation ONCE per candidate for ALL methods.
        # Old cost-only Estimate remains compatible, but future feasibility is
        # conservatively UNKNOWN. No second model/GT call for the full method.
        value=supplied(inputs,candidate)
        if type(value) is Estimate:
            value=CompleteSuccessorEstimate(value)
        need(type(value) is CompleteSuccessorEstimate,'Prospective Estimate or explicit complete-successor prediction only')
        successor_rows[candidate.candidate_id]=value
        return value.estimate
    batch=evaluate_shared(problem.domain,problem.inputs,common_evaluation,
        evaluator_sha256=model_pin,information_schema=problem.information_schema,
        max_evaluations=len(problem.domain.candidates),max_wall_s=max_wall_s)
    methods=select_all(batch)
    rows=dict(batch.rows)
    complete=deepcopy(methods['successor_aware'])
    complete['requires_complete_successor_feasibility_not_READY_only']=True
    eligible=[c.candidate_id for c in problem.domain.candidates if
              c.candidate_id in rows and rows[c.candidate_id].current_feasibility=='PASS']
    # Preserve budget/current-gate unresolved results. Otherwise apply an
    # EXPLICIT full-successor feasibility view of the SAME shared cache. Do not
    # replace failure with a large duration, or omit it from public status rows.
    if not batch.overrun and len(rows)==len(problem.domain.candidates) and eligible and not any(
            r.current_feasibility=='UNKNOWN' for r in rows.values()):
        if any(successor_rows[c].successor_feasibility=='UNKNOWN' for c in eligible):
            complete.update(candidate_id=None,status='UNKNOWN_COMPLETE_SUCCESSOR_FEASIBILITY',objective_upper_s=None)
        else:
            passing=[c for c in eligible if successor_rows[c].successor_feasibility=='PASS']
            costs={c:rows[c].costs.upper(True) for c in passing}
            if not passing:
                complete.update(candidate_id=None,status='NO_PREDICTED_COMPLETE_SUCCESSOR_FEASIBLE_CANDIDATE',objective_upper_s=None)
            elif any(v is None for v in costs.values()):
                complete.update(candidate_id=None,status='UNKNOWN_REQUIRED_COST_HEADS',objective_upper_s=None)
            else:
                chosen=min(passing,key=lambda c:(costs[c],c!=problem.domain.original_id,c))
                complete.update(candidate_id=chosen,status='MINIMUM_COMMON_COST_WITH_EXPLICIT_COMPLETE_SUCCESSOR_FEASIBILITY',
                                objective_upper_s=costs[chosen])
    methods['successor_aware']=complete
    selected=methods[method]['candidate_id']
    # A native/model refusal of original is NEVER converted to original fallback.
    # A missing/overrun row is also not enough evidence to override the budget.
    original=rows.get('original')
    fallback=(selected is None and on_unknown=='original_default' and not batch.overrun and
              original is not None and original.current_feasibility!='REFUSED' and
              (method!='successor_aware' or successor_rows['original'].successor_feasibility!='REFUSED') and
              methods[method]['status'] not in ('NO_CANDIDATE_PASSES_COMMON_EVALUATOR','NO_PREDICTED_COMPLETE_SUCCESSOR_FEASIBLE_CANDIDATE','COMMON_EVALUATION_BUDGET_EXCEEDED'))
    proposal=selected if selected is not None else 'original' if fallback else None
    payload=next((deepcopy(p) for p in problem.payloads if p['candidate_id']==proposal),None)
    if selected is not None:status='CONDITIONAL_SUPPLIED_EVALUATOR_CHOICE_NOT_EXECUTION_AUTHORITY'
    elif fallback:status='KEEP_OWNER_ORIGINAL_DEFAULT_NO_OPTIMIZATION_CLAIM'
    else:status='ABSTAIN_NO_PREPARATION_PLAN'
    return dict(status=status,requested_method=method,optimized_candidate_id=selected,
        proposed_payload=payload,used_original_default_fallback=fallback,
        reason=methods[method]['status'],methods=methods,
        shared_evaluation_count=len(batch.rows),shared_evaluator_sha256=model_pin,
        complete_successor_prediction_status={c:r.successor_feasibility for c,r in successor_rows.items()},
        complete_successor_prediction_source={c:r.source_ref for c,r in successor_rows.items()},
        prediction_source_or_calibration_verified_by_this_function=False,
        known_complete_successor_refusals=[c for c,r in successor_rows.items() if r.successor_feasibility=='REFUSED'],
        duration_is_not_successor_feasibility=True,refusal_not_replaced_by_large_time_penalty=True,
        domain_sha256=problem.domain.sha256,input_sha256=problem.inputs.sha256,
        geometry=deepcopy(list(problem.geometry)),
        information_field_names=[v.name for v in problem.inputs.values],
        information_decision_time_s=problem.inputs.decision_time_s,
        known_cost_heads=('CONDITIONAL_SUPPLIED_ESTIMATE_HEADS_NOT_QUALIFIED_BY_THIS_FUNCTION' if model_supplied else
                          'NO_COMPLETION_TIME_PREDICTOR_FROM_STATIC_OR_CURRENT_KINEMATICS'),
        unresolved_cost_heads=['NAV travel/exit/settling','fresh original CLIMB READY time','complete successor/stop time'],
        units_separated='Reference displacement/margin are meters, never converted to completion seconds',
        same_information_candidates_profile_and_evaluator_budget_for_all_methods=True,
        execution_authorized=False,actual_native_feasibility_or_motor_difference_proven=False,
        full_cost_or_safety_guaranteed=False,old_actual_or_unexecuted_GT_used=False,
        training_WM_or_fit_permission=False,
        execution_binding_phase='Existing AINav binder only BEFORE fresh Host first step; no runtime hot-replanning install')


def materialize_fresh_plan(problem, decision, *, selection_from_payload, phase):
    """Consume existing pure owner materializer, NEVER bind/install or issue.

    The caller's phase is a declaration, not proof of actual fresh-host identity;
    the unchanged original bind_to_host must independently enforce that later.
    """
    need(type(problem) is Problem and callable(selection_from_payload),'Original owner pure materializer')
    need(phase=='FRESH_PREEXECUTION','Stable binder does not allow decision-boundary hot installation')
    need(problem.inputs.decision_time_s==0. and
         problem.domain.task.decision_boundary=='FRESH_HOST_PREEXECUTION_IMMUTABLE_PREPARATION_PLAN',
         'Live measured input cannot be relabelled as a fresh-host installation plan')
    need(type(decision) is dict and decision.get('domain_sha256')==problem.domain.sha256 and
         decision.get('input_sha256')==problem.inputs.sha256,'Same public problem decision')
    payload=decision.get('proposed_payload')
    if payload is None:return None
    need(any(payload==p for p in problem.payloads),'Exact existing finite payload, no extra controls')
    selection=selection_from_payload(deepcopy(payload))
    need(asdict(selection)==dict(target_ref=payload['target_ref'],candidate_id=payload['candidate_id']),
         'Original owner immutable selection roundtrip')
    return selection
