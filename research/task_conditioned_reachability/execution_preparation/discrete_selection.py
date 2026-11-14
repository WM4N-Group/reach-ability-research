"""Numerical finite-domain selector; a Reach consumer, NOT a new skill ABI.

All rankings are within supplied causal/nominal MODEL evidence. SHA/source
registration binds bytes/identity, not sensor truth or a calibrated error bound.
Historical outcomes and command goals never become terminal predictions.
No native command, planner intent change, fallback, dispatch, or online model.
"""
import math
import hashlib
import json
from pathlib import Path
from .native_domain_v0 import VERSION, candidates

DISTANCES=(.2,.4,.6)
COST_TERMS=('current_preparation','push_including_original_Finish','successor_preparation')


class EvidenceError(ValueError):
    pass


def require(ok,message):
    if not ok:raise EvidenceError(message)


def real(x):
    return type(x) in (int,float) and math.isfinite(x)


def interval(x,*,nonnegative=False):
    require(type(x) in (list,tuple) and len(x)==2 and all(real(v) for v in x),
            'Expected finite two-endpoint interval, not bool/NaN/assumed zero')
    lo,hi=map(float,x)
    require(lo<=hi and (not nonnegative or lo>=0),'Reversed/negative interval')
    return lo,hi


def margin_status(bounds):
    interval(bounds)  # Reject arithmetic overflow as well as malformed inputs.
    if bounds[0]>=0:return 'PASS_IN_SUPPLIED_MODEL'
    if bounds[1]<0:return 'FAIL_IN_SUPPLIED_MODEL'
    return 'UNKNOWN_INTERVAL_STRADDLES_ZERO'


def geometric_relations(box_front,robot_exit,requirements):
    """Longitudinal necessary relations ONLY, not 3D contact/path certificates.

    All coordinates share the explicitly declared axis. Extent, destination and
    reserve have sources in problem context. Box motion during exit must already
    be included in the supplied exit-terminal front, never frozen to push goal.
    """
    if box_front is None:return None
    lo,hi=interval(box_front)
    L=requirements['box_length_m'];H=requirements['destination_front_m']
    reserve=requirements['minimum_overlap_m'];gap=requirements['exit_reference_separation_m']
    support=[lo+L-H-reserve,hi+L-H-reserve]
    rows=dict(longitudinal_support_overlap=dict(margin_m=support,status=margin_status(support)))
    if robot_exit is None:
        rows['exit_reference_separation']=dict(margin_m=None,status='UNKNOWN_MISSING_ROBOT_EXIT')
    else:
        rlo,rhi=interval(robot_exit)
        separation=[lo-rhi-gap,hi-rlo-gap]
        rows['exit_reference_separation']=dict(margin_m=separation,status=margin_status(separation))
    return rows


def validate_problem(domain,problem):
    require(domain['executor_version']==problem.get('executor_version')==VERSION,'Executor mismatch')
    require(domain['decision_variable']['values']==list(DISTANCES),'Do not expand/interpolate domain')
    require(problem.get('object_ref') in domain['objects'],'Fixed supported PUSH object required')
    for field in ('scene_id','current_observation_ref','successor_requirement_id','axis_id'):
        require(type(problem.get(field)) is str and bool(problem[field]),'Missing bound public context '+field)
    require(real(problem.get('query_time_s')) and problem['query_time_s']>=0,'Finite query clock required')
    r=problem['requirements']
    for field in ('box_length_m','destination_front_m','minimum_overlap_m','exit_reference_separation_m'):
        require(real(r.get(field)),'Missing sourced physical-unit requirement '+field)
    require(r['box_length_m']>0 and r['minimum_overlap_m']>=0 and r['exit_reference_separation_m']>=0,
            'Invalid geometry requirement')
    require(type(problem.get('requirement_source_ref')) is str and bool(problem['requirement_source_ref']),
            'Requirement source required; this is not source authenticity certification')
    require(problem.get('objective')=='minimum_supplied_total_cost_upper_s','Explicit seconds-only objective required')


def evaluate_candidate(problem,distance,effect,*,trusted_sources,allow_synthetic=False):
    row=dict(push_distance_m=distance,status='UNKNOWN',reason=None,relations=None,
             requested_goal_relations=None,cost_interval_s=None,rankable=False,resolved=False,
             entry_model_eligible=None,predicted_next_ready=None,
             actual_next_ready=None,native_entry_ready=None,execution_authorized=False)
    if effect is None:return dict(row,reason='missing_candidate_effect')
    try:
        source=effect['source'];name=source['name'];sha=source['sha256'];tier=source['tier']
        require(trusted_sources.get(name)==sha,'Source not independently registered for this invocation')
        require(source.get('online_use_allowed') is True,'Source role forbids current ranking')
        require(tier not in ('observed_historical','private_evaluation'),'Historical/private outcome is not current prediction')
        require(tier in ('current_causal_prediction','nominal_model','requested_goal_only','synthetic_test'),
                'Unsupported evidence role')
        require(tier!='synthetic_test' or allow_synthetic,'Synthetic data forbidden in real publication path')
        expected=dict(executor_version=problem['executor_version'],scene_id=problem['scene_id'],
                      object_ref=problem['object_ref'],current_observation_ref=problem['current_observation_ref'],
                      query_time_s=problem['query_time_s'],push_distance_m=distance,
                      successor_requirement_id=problem['successor_requirement_id'],axis_id=problem['axis_id'])
        require(effect.get('identity')==expected,'Candidate/observation/goal/axis/time identity mismatch')
        require(real(source.get('information_time_s')) and source['information_time_s']<=problem['query_time_s'],
                'Future information cannot supply a decision-time effect')
        require(type(source.get('assumptions')) is list,'Explicit model assumptions required')
        row['evidence_tier']=tier;row['assumptions']=source['assumptions']
        # Goal relations are explicitly design/command conditions, never outcomes.
        if effect.get('requested_box_front_m') is not None:
            row['requested_goal_relations']=geometric_relations(effect['requested_box_front_m'],None,problem['requirements'])
        if tier=='requested_goal_only':return dict(row,reason='requested_goal_not_predicted_exit_state')
        require(effect.get('geometry_phase')=='after_original_Finish','Do not borrow PUSH endpoint for final EXIT')
        entry=effect.get('entry_model_eligible')
        require(entry is None or type(entry) is bool,'Entry model qualification must be bool or unknown')
        row['entry_model_eligible']=entry
        ready=effect.get('predicted_next_ready')
        require(ready is None or type(ready) is bool,'Predicted ready must be bool or unknown')
        row['predicted_next_ready']=ready
        row['relations']=geometric_relations(effect.get('box_exit_front_m'),effect.get('robot_exit_x_m'),problem['requirements'])
        if entry is False:return dict(row,status='ENTRY_BLOCKED_IN_SUPPLIED_MODEL',reason='entry_model_rejected',resolved=True)
        if ready is False:return dict(row,status='SUCCESSOR_BLOCKED_IN_SUPPLIED_MODEL',reason='supplied_model_next_ready_false',resolved=True)
        if row['relations'] is None:return dict(row,reason='missing_box_exit_front')
        statuses=[v['status'] for v in row['relations'].values()]
        if 'FAIL_IN_SUPPLIED_MODEL' in statuses:
            return dict(row,status='NECESSARY_RELATION_FAILED_IN_SUPPLIED_MODEL',reason='necessary_relation_failed',resolved=True)
        if any(s!='PASS_IN_SUPPLIED_MODEL' for s in statuses):return dict(row,reason='geometry_missing_or_interval_indeterminate')
        if entry is None:return dict(row,reason='entry_qualification_unknown_not_granted_by_enum')
        costs=effect.get('costs')
        if costs is None:return dict(row,reason='missing_seconds_costs')
        require(costs.get('unit')=='s','Cost units must be seconds, not margin/probability/WM potential')
        require(set(costs.get('terms',{}))==set(COST_TERMS),'Explicit nonoverlapping preparation/PUSH+Finish/successor costs required')
        if any(costs['terms'][name] is None for name in COST_TERMS):return dict(row,reason='unknown_cost_term_not_zero')
        bounds=[interval(costs['terms'][name],nonnegative=True) for name in COST_TERMS]
        total=[sum(b[0] for b in bounds),sum(b[1] for b in bounds)]
        require(all(math.isfinite(v) for v in total),'Cost overflow')
        return dict(row,status='EVALUATED_NOMINAL_NECESSARY_RELATIONS_PASS',reason='not_full_chain_feasibility',
                    cost_interval_s=total,rankable=True,resolved=True)
    except (EvidenceError,KeyError,TypeError,AttributeError) as exc:
        return dict(row,status='REJECTED_EVIDENCE',reason=str(exc),rankable=False,resolved=False)


def select_discrete(domain,problem,effects,*,trusted_sources,allow_synthetic=False):
    """Exhaust all 3 legal candidates; unknown does not mean zero or infeasible.

    Completeness means coverage of this supplied MODEL at its stated assumptions,
    not optimality in the world. Even full nominal ranking never releases action.
    """
    validate_problem(domain,problem)
    require(type(effects) is dict and all(type(k) in (float,int) and k in DISTANCES for k in effects),
            'Only exactly exposed candidate distances allowed, no 0.8 or rounding')
    rows=[evaluate_candidate(problem,d,effects.get(d),trusted_sources=trusted_sources,
                             allow_synthetic=allow_synthetic) for d in DISTANCES]
    complete=all(r['resolved'] for r in rows)
    eligible=[r for r in rows if r['rankable']]
    best=min(eligible,key=lambda r:(r['cost_interval_s'][1],r['push_distance_m'])) if eligible else None
    status=('BEST_OF_THREE_IN_SUPPLIED_MODEL' if complete else 'BEST_OF_EVALUATED_SUBSET_IN_SUPPLIED_MODEL') if best else (
        'NO_CANDIDATE_PASSES_NECESSARY_RELATIONS_IN_SUPPLIED_MODEL' if complete else 'UNKNOWN')
    templates=candidates(domain,problem['object_ref'])
    return dict(schema='reach-discrete-numerical-selection-v1',status=status,executor_version=VERSION,
                context={k:problem[k] for k in ('scene_id','object_ref','current_observation_ref','query_time_s','successor_requirement_id','axis_id')},
                candidate_count=3,resolved_count=sum(r['resolved'] for r in rows),
                rankable_count=len(eligible),complete_model_enumeration=complete,
                unknown_candidates=[r['push_distance_m'] for r in rows if not r['resolved']],
                best_evaluated_candidate=(dict(parameter_template=next(t for t in templates if t['parameters']['push_distance_m']==best['push_distance_m']),
                                              cost_interval_s=best['cost_interval_s'],score_upper_s=best['cost_interval_s'][1]) if best else None),
                rows=rows,global_best_in_supplied_model=bool(complete and best),
                full_chain_feasibility_proven=False,actual_next_ready=None,native_entry_ready=None,
                execution_authorized=False,physical_dispatch=False,global_physical_infeasible=False,
                cost_scope='current preparation + PUSH including original Finish + successor preparation; seconds only',
                result_scope='synthetic_test' if allow_synthetic else 'supplied_model_only_not_native_ready')


def select_from_bundle(domain,problem,path,*,expected_sha256,allow_synthetic=False):
    """Consume an explicitly normalized and independently pinned artifact.

    This is a Reach consumer input, NOT a new WM skill contract. A published WM
    artifact needs an explicit reviewed mapping before it can have this layout;
    absent such a mapping do not relabel requested goals or old outcomes.
    """
    path=Path(path)
    require(path.is_file() and path.stat().st_size<=1024*1024,'Bounded source artifact required')
    raw=path.read_bytes();actual=hashlib.sha256(raw).hexdigest()
    require(actual==expected_sha256,'Effect artifact changed; no self-authorized replacement SHA')
    def unique(pairs):
        row={}
        for key,value in pairs:
            require(key not in row,'Duplicate artifact JSON key')
            row[key]=value
        return row
    def invalid(value):raise EvidenceError('Nonfinite artifact JSON token')
    bundle=json.loads(raw,object_pairs_hook=unique,parse_constant=invalid)
    require(bundle.get('schema')=='reach-normalized-effect-input-v1','Explicit reviewed effect mapping required')
    source=bundle['source']
    require(type(bundle.get('records')) is list and len(bundle['records'])<=3,'At most 3 exact candidates')
    effects={}
    for record in bundle['records']:
        require(type(record) is dict and 'source' not in record,'Bundle owns immutable record provenance')
        d=record['identity']['push_distance_m']
        require(d not in effects,'Duplicate candidate effects cannot overwrite another row')
        effects[d]=dict(record,source=dict(source,name=str(path),sha256=actual))
    result=select_discrete(domain,problem,effects,trusted_sources={str(path):expected_sha256},
                           allow_synthetic=allow_synthetic)
    result['source_artifact']=dict(path=str(path),sha256=actual)
    return result
