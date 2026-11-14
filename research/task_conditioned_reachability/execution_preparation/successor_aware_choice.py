"""Stage-A successor-aware finite-choice interface, NOT a new search algorithm.

Prospective model estimates and audit-only branch outcomes have separate types
and entry points. No simulation/Actor/WM, execution, fitting or file/network IO.
Source/visibility declarations are contracts, not proof that an arbitrary
external evaluator is trustworthy. Original native admission remains required.
"""
from dataclasses import dataclass, asdict
import hashlib
import json
import math
import time

HEADS=('current_operation_remaining','current_exit_remaining','successor_approach','successor_execution_complete')
METHODS=('original_fixed','direct_strong','current_greedy','successor_aware')


def need(ok,msg):
    if not ok:raise ValueError(msg)


def number(v):return type(v) in (int,float) and math.isfinite(v)


def text(v):return type(v) is str and bool(v)


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def pin(value):return type(value) is str and len(value)==64 and all(c in '0123456789abcdef' for c in value)


@dataclass(frozen=True)
class Task:
    task_id: str
    terminal_predicate_sha256: str
    original_success_gates_sha256: str
    decision_boundary: str
    information_schema_sha256: str
    def __post_init__(self):
        need(text(self.task_id) and text(self.decision_boundary),'Declared same task and decision boundary')
        need(all(pin(x) for x in (self.terminal_predicate_sha256,self.original_success_gates_sha256,self.information_schema_sha256)),
             'Common task region, ORIGINAL success gates, information schema pins')
    @property
    def sha256(self):return digest(asdict(self))


@dataclass(frozen=True)
class Candidate:
    candidate_id: str
    task_sha256: str
    execution_profile_sha256: str
    owner_materialization_ref: str
    control_equivalence_key: str
    mode: str
    def __post_init__(self):
        need(text(self.candidate_id) and text(self.owner_materialization_ref) and text(self.control_equivalence_key),'Owner-bound candidate, not a free actuator command')
        need(pin(self.task_sha256) and pin(self.execution_profile_sha256),'Exact common task/profile')
        need(self.mode in ('original','direct','owner_registered_alternative'),'Explicit candidate mode')
    @property
    def sha256(self):return digest(asdict(self))


@dataclass(frozen=True)
class Domain:
    task: Task
    candidates: tuple
    original_id: str
    direct_id: object = None
    role: str = 'OWNER_PROSPECTIVE_REGISTERED'
    def __post_init__(self):
        need(type(self.task) is Task,'Typed common task')
        need(type(self.candidates) is tuple and 1<=len(self.candidates)<=32,'Explicit bounded finite domain')
        need(all(type(c) is Candidate for c in self.candidates),'Typed candidates')
        ids=[c.candidate_id for c in self.candidates]
        need(len(ids)==len(set(ids)) and self.original_id in ids,'Unique candidates and original baseline')
        need(self.direct_id is None or self.direct_id in ids,'Direct strong baseline only when actually supplied')
        need(next(c for c in self.candidates if c.candidate_id==self.original_id).mode=='original','Original baseline must be the owner original')
        need(self.direct_id is None or next(c for c in self.candidates if c.candidate_id==self.direct_id).mode=='direct','Direct baseline must be explicitly supplied as direct')
        need(len({c.control_equivalence_key for c in self.candidates})==len(ids),'Control aliases are not distinct H1 candidates')
        need(all(c.task_sha256==self.task.sha256 for c in self.candidates),'No different goal region or success gate per method')
        need(len({c.execution_profile_sha256 for c in self.candidates})==1,'Same available control authority/profile for all methods')
        need(self.role in ('OWNER_PROSPECTIVE_REGISTERED','AUDIT_REPLAY_ONLY','CPU_TEST_ONLY'),'Explicit domain role')
    @property
    def sha256(self):return digest(dict(task=self.task.sha256,candidates=[c.sha256 for c in self.candidates],role=self.role))


@dataclass(frozen=True)
class InputValue:
    name: str
    value: object
    visibility: str
    observed_time_s: float
    source_ref: str
    def __post_init__(self):
        need(text(self.name) and text(self.source_ref),'Declared current field source')
        need(self.visibility in ('ONLINE_PUBLIC','ONLINE_NATIVE_LOCAL','AUDIT_ONLY','UNKNOWN'),'Explicit visibility')
        need(number(self.observed_time_s) and self.observed_time_s>=0,'Recorded current field clock')
        need(self.visibility!='UNKNOWN' or self.value is None,'Unknown input is not an invented value')
        digest(self.value)  # finite JSON values only; not a live sim/array pointer


@dataclass(frozen=True)
class DecisionInput:
    task_sha256: str
    information_schema_sha256: str
    decision_time_s: float
    audience: str
    values: tuple
    def __post_init__(self):
        need(pin(self.task_sha256) and pin(self.information_schema_sha256),'Task/information-set identity')
        need(number(self.decision_time_s) and self.decision_time_s>=0,'Prospective decision clock')
        need(self.audience in ('HIGH_LEVEL_PLANNER','REACH_NATIVE_LOCAL'),'No implicit private-to-planner channel')
        need(type(self.values) is tuple and all(type(v) is InputValue for v in self.values),'Typed current observations, not outcome records')
        need(len({v.name for v in self.values})==len(self.values),'Unique state fields')
        for v in self.values:
            need(v.visibility!='AUDIT_ONLY','Private/posterior audit outcomes cannot enter prospective choice')
            need(v.observed_time_s<=self.decision_time_s+1e-9,'No future observation leakage')
            need(self.audience!='HIGH_LEVEL_PLANNER' or v.visibility!='ONLINE_NATIVE_LOCAL','Local native permission is not VLM/planner permission')
    @property
    def sha256(self):return digest(asdict(self))


@dataclass(frozen=True)
class InputSchema:
    owner_declaration_ref: str
    # (field_name, permitted_visibility, permitted_audiences); explicit source
    # ownership/permission must still be checked outside this pure API.
    fields: tuple
    def __post_init__(self):
        need(text(self.owner_declaration_ref) and type(self.fields) is tuple,'Versioned owner information declaration')
        need(all(type(f) is tuple and len(f)==3 and text(f[0]) and
                 f[1] in ('ONLINE_PUBLIC','ONLINE_NATIVE_LOCAL','UNKNOWN') and type(f[2]) is tuple and
                 f[2] and all(a in ('HIGH_LEVEL_PLANNER','REACH_NATIVE_LOCAL') for a in f[2]) for f in self.fields),
             'Explicit field visibility/audience allowlist; audit fields excluded')
        need(len({f[0] for f in self.fields})==len(self.fields),'Unique declared information fields')
        need(all(f[1]!='ONLINE_NATIVE_LOCAL' or 'HIGH_LEVEL_PLANNER' not in f[2] for f in self.fields),
             'Private local values never implicitly become high-level inputs')
    @property
    def sha256(self):return digest(asdict(self))
    def validate(self,inputs):
        need(inputs.information_schema_sha256==self.sha256,'Exact owner information schema')
        allowed={f[0]:f for f in self.fields}
        for value in inputs.values:
            need(value.name in allowed,'Unregistered prospective field: '+value.name)
            field=allowed[value.name]
            need(value.visibility==field[1] and inputs.audience in field[2],'Field visibility/audience exceeds owner declaration')


@dataclass(frozen=True)
class Bounds:
    lower_s: float
    upper_s: float
    quantity: str = 'CONDITIONAL_SIM_COMPLETION_ESTIMATE'
    def __post_init__(self):
        need(number(self.lower_s) and number(self.upper_s) and 0<=self.lower_s<=self.upper_s,'Finite ordered nonnegative seconds')
        need(self.quantity=='CONDITIONAL_SIM_COMPLETION_ESTIMATE','Assigned-reference schedules are not full completion costs')


@dataclass(frozen=True)
class Costs:
    current_operation_remaining: object = None
    current_exit_remaining: object = None
    successor_approach: object = None
    successor_execution_complete: object = None
    current_composite_remaining: object = None
    def __post_init__(self):
        need(all(getattr(self,k) is None or type(getattr(self,k)) is Bounds for k in HEADS+('current_composite_remaining',)),'Unknown heads remain None')
        need(self.current_composite_remaining is None or (self.current_operation_remaining is None and self.current_exit_remaining is None),
             'Current composite is an alternative to operation+exit, never double count')
    def upper(self,include_successor):
        if self.current_composite_remaining is not None:current=self.current_composite_remaining.upper_s
        elif self.current_operation_remaining is not None and self.current_exit_remaining is not None:
            current=self.current_operation_remaining.upper_s+self.current_exit_remaining.upper_s
        else:return None
        if not include_successor:return current
        if self.successor_approach is None or self.successor_execution_complete is None:return None
        return current+self.successor_approach.upper_s+self.successor_execution_complete.upper_s


@dataclass(frozen=True)
class Estimate:
    candidate_sha256: str
    input_sha256: str
    evaluator_sha256: str
    current_feasibility: str
    feasibility_scope: str
    costs: Costs
    role: str = 'PROSPECTIVE_DECLARED_MODEL'
    def __post_init__(self):
        need(all(pin(x) for x in (self.candidate_sha256,self.input_sha256,self.evaluator_sha256)),'Bound common evaluation')
        need(self.current_feasibility in ('PASS','REFUSED','UNKNOWN'),'Unknown is never gate pass')
        need(self.feasibility_scope in ('NECESSARY_GEOMETRY_ONLY','NATIVE_FINITE_GUARD','CPU_TEST_ONLY'),'No new dynamic certificate')
        need(type(self.costs) is Costs and self.role=='PROSPECTIVE_DECLARED_MODEL','Not actual branch outcomes or a retrospective oracle')


def evaluate_shared(domain,inputs,evaluator,*,evaluator_sha256,information_schema=None,max_evaluations=32,max_wall_s=5.):
    """Exactly one COMMON evaluator call per candidate for ALL four baselines.

    Wall limit is checked after each external call; this is not an interrupt or
    security sandbox. Any overrun makes the whole batch unrankable. The external
    evaluator's data/side effects require owner qualification independently.
    """
    need(type(domain) is Domain and domain.role!='AUDIT_REPLAY_ONLY','Audit domains cannot be deployed as prospective domains')
    need(type(inputs) is DecisionInput,'Only legal prospective input type')
    need(inputs.task_sha256==domain.task.sha256 and inputs.information_schema_sha256==domain.task.information_schema_sha256,'Same task and information set')
    if domain.role=='OWNER_PROSPECTIVE_REGISTERED':
        need(type(information_schema) is InputSchema,'Production comparison requires explicit owner input schema, not hash alone')
    if information_schema is not None:
        need(type(information_schema) is InputSchema,'Typed owner input schema');information_schema.validate(inputs)
    need(callable(evaluator) and pin(evaluator_sha256),'One explicitly versioned common evaluator')
    need(type(max_evaluations) is int and len(domain.candidates)<=max_evaluations<=32,'No method-specific extra model budget')
    need(number(max_wall_s) and max_wall_s>0,'Finite declared common planning wall limit')
    rows={};start=time.perf_counter();overrun=False
    input_before,domain_before=inputs.sha256,domain.sha256
    for candidate in domain.candidates:
        row=evaluator(inputs,candidate)
        need(inputs.sha256==input_before and domain.sha256==domain_before,'Common evaluator mutated prospective input/domain')
        need(type(row) is Estimate and row.candidate_sha256==candidate.sha256 and row.input_sha256==input_before and row.evaluator_sha256==evaluator_sha256,
             'Evaluator returned another candidate/input/model or audit outcome')
        need(domain.role=='CPU_TEST_ONLY' or row.feasibility_scope!='CPU_TEST_ONLY','Synthetic geometry not qualified production evidence')
        rows[candidate.candidate_id]=row
        if time.perf_counter()-start>max_wall_s:overrun=True;break
    return SharedBatch(domain,input_before,evaluator_sha256,tuple(rows.items()),time.perf_counter()-start,overrun)


@dataclass(frozen=True)
class SharedBatch:
    domain: Domain
    input_sha256: str
    evaluator_sha256: str
    rows: tuple
    evaluator_wall_s: float
    overrun: bool


def select_all(batch):
    need(type(batch) is SharedBatch,'All methods consume the SAME shared evaluation batch')
    domain=batch.domain;rows=dict(batch.rows)
    def answer(method,selected,status,cost=None):
        return dict(method=method,candidate_id=selected,status=status,objective_upper_s=cost,
            domain_sha256=domain.sha256,input_sha256=batch.input_sha256,evaluator_sha256=batch.evaluator_sha256,
            shared_candidate_evaluations=len(rows),common_evaluator_wall_s=batch.evaluator_wall_s,
            shared_cache_is_not_independent_deployment_runtime=True,
            cost_heads_used=([] if method in ('original_fixed','direct_strong') else
                ['current_composite_OR_operation_plus_exit']+(['successor_approach','successor_execution_complete'] if method=='successor_aware' else [])),
            prospective_choice_is_conditional_on_supplied_model=True,actual_total_cost_or_success_guaranteed=False,
            execution_authorized=False,original_native_gates_required=True,
            no_choice_is_not_global_task_infeasibility=True,physical_H1_or_new_solver_proven=False)
    if batch.overrun or len(rows)!=len(domain.candidates):
        return {m:answer(m,None,'COMMON_EVALUATION_BUDGET_EXCEEDED') for m in METHODS}
    def passed(cid):return rows[cid].current_feasibility=='PASS'
    original=domain.original_id
    result={'original_fixed':answer('original_fixed',original if passed(original) else None,'FIXED_IF_COMMON_GATE_PASS')}
    direct=domain.direct_id
    if direct is None:result['direct_strong']=answer('direct_strong',None,'NOT_APPLICABLE_NO_OWNER_DIRECT_CANDIDATE')
    else:
        chosen=direct if passed(direct) else original if passed(original) else None
        result['direct_strong']=answer('direct_strong',chosen,'DIRECT_IF_PASS_ELSE_ORIGINAL_COMMON_GATE')
    for method,successor in (('current_greedy',False),('successor_aware',True)):
        if any(r.current_feasibility=='UNKNOWN' for r in rows.values()):
            result[method]=answer(method,None,'UNRESOLVED_COMMON_FEASIBILITY');continue
        ids=[c.candidate_id for c in domain.candidates if passed(c.candidate_id)]
        if not ids:result[method]=answer(method,None,'NO_CANDIDATE_PASSES_COMMON_EVALUATOR');continue
        costs={cid:rows[cid].costs.upper(successor) for cid in ids}
        if any(x is None for x in costs.values()):
            result[method]=answer(method,None,'UNKNOWN_REQUIRED_COST_HEADS');continue
        selected=min(ids,key=lambda cid:(costs[cid],cid!=original,cid))
        result[method]=answer(method,selected,'MINIMUM_COMMON_SUPPLIED_COST_UPPER',costs[selected])
    return result


@dataclass(frozen=True)
class ObservedBranch:
    candidate_id: str
    task_sha256: str
    pairing_ref: str
    source_result_sha256: str
    current_outcome: str
    chain_outcome: str
    current_completion_s: object
    chain_completion_s: object
    spent_sim_s: object
    role: str = 'AUDIT_ONLY_OBSERVED_BRANCH'
    def __post_init__(self):
        need(text(self.candidate_id) and text(self.pairing_ref) and pin(self.task_sha256) and pin(self.source_result_sha256),'Exact observed branch/task/pair identity')
        need(self.role=='AUDIT_ONLY_OBSERVED_BRANCH','No observed outcome masquerading as model')
        need(all(x in ('SUCCESS','FAILED','CENSORED','NOT_RUN','UNKNOWN') for x in (self.current_outcome,self.chain_outcome)),'Literal outcome categories')
        for x in (self.current_completion_s,self.chain_completion_s,self.spent_sim_s):
            need(x is None or (number(x) and x>=0),'Observed clocks, missing not zero')
        need(self.current_outcome=='SUCCESS' or self.current_completion_s is None,'Failure elapsed time is not successful current completion time')
        need(self.chain_outcome=='SUCCESS' or self.chain_completion_s is None,'Shorter failure is not chain improvement')
        if self.chain_outcome=='SUCCESS':need(self.current_outcome=='SUCCESS','Successful chain includes current composite success')
        if self.chain_completion_s is not None and self.current_completion_s is not None:need(self.current_completion_s<=self.chain_completion_s,'Same origin and nested terminal endpoints')


def replay_observed(domain,records):
    """Stage B hindsight enumeration/diagnostic upper bound, NEVER deployment.

    All branch outcomes are in the common offline table; no method gets unique
    GT/evaluator calls. Missing/censored candidates prevent an H1 conclusion.
    """
    need(type(domain) is Domain and domain.role in ('AUDIT_REPLAY_ONLY','CPU_TEST_ONLY'),'Explicit offline diagnostic domain')
    need(type(records) is tuple and all(type(r) is ObservedBranch for r in records),'Separate observed outcome records')
    ids=[c.candidate_id for c in domain.candidates];table={r.candidate_id:r for r in records}
    need(len(table)==len(records) and set(table)==set(ids),'Same full candidate domain; no success-subset selection')
    need(all(r.task_sha256==domain.task.sha256 for r in records) and len({r.pairing_ref for r in records})==1,'Same task and declared paired initialization, not hidden-state equality')
    incomplete=any(r.current_outcome in ('CENSORED','NOT_RUN','UNKNOWN') or r.chain_outcome in ('CENSORED','NOT_RUN','UNKNOWN') or
        (r.current_outcome=='SUCCESS' and r.current_completion_s is None) or
        (r.chain_outcome=='SUCCESS' and r.chain_completion_s is None) for r in records)
    local=[r for r in records if r.current_outcome=='SUCCESS' and r.current_completion_s is not None]
    chain=[r for r in records if r.chain_outcome=='SUCCESS' and r.chain_completion_s is not None]
    def best(rows,key):return min(rows,key=lambda r:(getattr(r,key),r.candidate_id!=domain.original_id,r.candidate_id)).candidate_id if rows else None
    greedy=best(local,'current_completion_s') if not incomplete else None
    full=best(chain,'chain_completion_s') if not incomplete else None
    fixed=domain.original_id;direct=domain.direct_id
    # A registered guarded-direct candidate includes its owner-defined precheck
    # fallback in that candidate's policy. Never repair an observed failure by
    # retrospectively choosing original after seeing the failed outcome.
    direct_choice=direct
    reversal=failure_switch=tie_break=None
    if not incomplete and greedy is not None and full is not None:
        g,f=table[greedy],table[full]
        failure_switch=g.chain_outcome=='FAILED' and f.chain_outcome=='SUCCESS'
        reversal=(g.chain_outcome=='SUCCESS' and greedy!=full and
                  g.current_completion_s<f.current_completion_s-1e-9 and f.chain_completion_s<g.chain_completion_s-1e-9)
        tie_break=(g.chain_outcome=='SUCCESS' and greedy!=full and abs(g.current_completion_s-f.current_completion_s)<=1e-9 and f.chain_completion_s<g.chain_completion_s-1e-9)
    choices=dict(original_fixed=fixed,direct_strong=direct_choice,current_greedy=greedy,successor_aware=full)
    return dict(schema='reach-H1-offline-common-domain-replay-v1',role='HINDSIGHT_DIAGNOSTIC_NOT_DEPLOYABLE',
        domain_sha256=domain.sha256,choices=choices,
        status='INCOMPLETE_BRANCH_COVERAGE_NO_H1_CONCLUSION' if incomplete else 'COMPLETE_OBSERVED_TABLE',
        strict_current_vs_chain_cost_rank_reversal=reversal,failure_compatibility_switch=failure_switch,successor_breaks_current_cost_tie=tie_break,
        observed_attempts=len(records),current_successes=sum(r.current_outcome=='SUCCESS' for r in records),chain_successes=sum(r.chain_outcome=='SUCCESS' for r in records),
        branch_records=[asdict(r) for r in records],failed_and_censored_costs_retained=True,
        positive_recorded_preference_change=(bool(reversal or failure_switch) if not incomplete and reversal is not None else None),
        physical_branch_provenance_verified_by_this_pure_function=False,
        CPU_examples_are_not_H1_experiments=domain.role=='CPU_TEST_ONLY',
        cost_accounting_complete=all(r.spent_sim_s is not None for r in records),
        all_unexecuted_branch_results_remain_unknown=True,online_oracle_or_training_allowed=False,
        execution_authorized=False,new_solver_or_generalization_proven=False)
