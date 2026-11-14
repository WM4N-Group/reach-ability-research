"""Conditional inner optimization for a FIXED skill intent and successor.

Not an outer task planner. Generates preparation plans, derives their nominal
command-schedule costs, and jointly searches base goal / arm reference path /
support reference. Does not load a WM, simulate, issue commands or relax gates.
An explicit executor domain is REQUIRED: a singleton remains a singleton.
Every constraint and future cost is evaluated against the FULL generated plan.
"""
from copy import deepcopy
import hashlib
import itertools
import json
import math

GATES = ('native_lowering', 'same_intent_goal_and_successor',
         'preparation_geometry', 'joint_and_reference_limits',
         'support_and_required_reserve', 'main_skill_entry',
         'successor_entry_and_transfer', 'original_protections_preserved')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


def finite(value, name, *, nonnegative=False):
    if type(value) not in (float, int) or not math.isfinite(value):
        raise ValueError(name+' must be a finite real number')
    if nonnegative and value < 0:
        raise ValueError(name+' must be nonnegative')
    return float(value)


def vector(value, n, name):
    if not isinstance(value, (list, tuple)) or len(value) != n:
        raise ValueError(name+' dimension mismatch')
    return [finite(v, name) for v in value]


def identifier(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('Explicit nonempty '+name+' required')
    return value


def _unique(rows, name):
    if not isinstance(rows, list) or not rows:
        raise ValueError('Explicit nonempty '+name+' required')
    ids = [identifier(row.get('id'), name+' id') for row in rows]
    if len(set(ids)) != len(ids):
        raise ValueError('Duplicate '+name+' id')


def synchronized_time(waypoints, rates):
    """Nominal piecewise-linear synchronized reference time, NOT tracking time.

    Segment k follows q_k+alpha*(q_{k+1}-q_k) with duration
    max_j |delta_j|/rate_j. Positive rates are declared model inputs, not learned
    from success histories or certified measured execution-time predictions.
    """
    if not isinstance(waypoints, list) or len(waypoints) < 2:
        raise ValueError('At least two waypoints required')
    rates = [finite(v, 'reference rate', nonnegative=True) for v in rates]
    if not rates or any(v <= 0 for v in rates):
        raise ValueError('Strictly positive per-coordinate reference rates required')
    q = [vector(row, len(rates), 'waypoint') for row in waypoints]
    durations = [max(abs(b-a)/r for a,b,r in zip(start,end,rates))
                 for start,end in zip(q,q[1:])]
    if not all(math.isfinite(t) for t in durations):
        raise ValueError('Reference duration overflow')
    return durations


def _validate(problem, domain):
    for key in ('request_id','observation_id','executor_id','frame_id','cost_contract_id','source_support_ref'):
        identifier(problem.get(key), key)
    # Intent and successor are immutable opaque task contracts, never selected
    # or rewritten by the preparation optimizer.
    for key in ('intent','successor_requirement','support_requirement'):
        if not isinstance(problem.get(key), dict) or not problem[key]:
            raise ValueError('Explicit immutable '+key+' required')
    for key in ('skill','target_ref'):
        identifier(problem['intent'].get(key), 'intent '+key)
    if problem['intent']['skill'] not in ('PUSH','CLIMB'):
        raise ValueError('This optimizer only prepares an already chosen PUSH/CLIMB')
    identifier(problem['successor_requirement'].get('skill'), 'successor skill')
    vector(problem.get('current_base_se2'), 3, 'current base SE2')
    joint_count = len(problem.get('current_arm_q', []))
    if not joint_count:
        raise ValueError('Current measured arm configuration required')
    vector(problem['current_arm_q'], joint_count, 'current arm')
    if domain.get('executor_id') != problem['executor_id']:
        raise ValueError('Executor domain mismatch; no cross-version alias')
    for key in ('source_id','base_motion_model_source','arm_rate_model_source'):
        identifier(domain.get(key), 'domain '+key)
    for rows,name in ((domain.get('base_goals'),'base goals'),
                      (domain.get('arm_paths'),'arm paths'),
                      (domain.get('support_references'),'support references')):
        _unique(rows,name)
    limit = domain.get('max_plan_evaluations')
    count = math.prod(len(domain[k]) for k in ('base_goals','arm_paths','support_references'))
    if type(limit) is not int or limit < 1 or count > limit:
        raise ValueError('Explicit finite search budget exceeded; no silent truncation or expansion')
    baseline = problem.get('baseline_reference_ids')
    if baseline is not None and (not isinstance(baseline,list) or len(baseline)!=3 or
            any(key not in {r['id'] for r in domain[field]} for key,field in
                zip(baseline,('base_goals','arm_paths','support_references')))):
        raise ValueError('Baseline must refer to one actual preparation in this exact domain')
    speed = finite(domain.get('base_translation_speed_m_s'), 'nominal base speed')
    yaw_rate = finite(domain.get('base_yaw_rate_rad_s'), 'nominal yaw rate')
    if speed <= 0 or yaw_rate <= 0:
        raise ValueError('Positive nominal base translation/yaw rates required')
    if len(domain.get('arm_rates_rad_s', [])) != joint_count:
        raise ValueError('Arm reference rate count mismatch')
    # Query cost is a COMMON external overhead; do not silently omit it when
    # comparing actual wall-time costs or mark a missing measurement as zero.
    overhead = domain.get('common_search_overhead_s')
    if overhead is not None:
        finite(overhead, 'search overhead', nonnegative=True)
        identifier(domain.get('search_overhead_source'), 'overhead source')
    cap = problem.get('preparation_budget_s')
    if cap is not None:
        finite(cap, 'declared preparation budget', nonnegative=True)
    return joint_count


def generate_plans(problem, domain):
    """Generate, not accept a pre-priced feasible table; no unapproved waypoint.

    Base preparation is a declared same-support segment with separate yaw and
    translation phases. Arm paths and support targets come from the executor's
    explicit reference domain. Sequential schedule is intentionally explicit;
    no unsupported concurrent base/arm motion or automatic semantics is added.
    Changing this schedule changes the plan hash and requires new evaluation.
    """
    n = _validate(problem, domain)
    contract = dict(request_id=problem['request_id'], observation_id=problem['observation_id'],
                    executor_id=problem['executor_id'], frame_id=problem['frame_id'],
                    intent_sha256=digest(problem['intent']),
                    successor_sha256=digest(problem['successor_requirement']),
                    support_requirement_sha256=digest(problem['support_requirement']),
                    problem_sha256=digest(problem), domain_sha256=digest(domain))
    origin = vector(problem['current_base_se2'], 3, 'base origin')
    rates = domain['arm_rates_rad_s']
    for base, arm, support in itertools.product(domain['base_goals'], domain['arm_paths'],
                                               domain['support_references']):
        goal = vector(base.get('se2'), 3, 'base goal')
        if base.get('source_support_ref') != problem['source_support_ref']:
            raise ValueError('Preparation cannot silently cross support surfaces')
        # Raw yaw is an explicit unwrapped reference; do not silently wrap a
        # 2pi command into no motion or add an unauthorized winding.
        yaw_time = abs(goal[2]-origin[2])/domain['base_yaw_rate_rad_s']
        translation_time = math.hypot(goal[0]-origin[0], goal[1]-origin[1])/domain['base_translation_speed_m_s']
        waypoints = [vector(q, n, 'arm reference') for q in arm.get('waypoints', [])]
        if not waypoints or waypoints[0] != list(problem['current_arm_q']):
            raise ValueError('Arm path must start at the declared current state')
        durations = synchronized_time(waypoints,rates)
        if not isinstance(support.get('reference'),dict) or not support['reference']:
            raise ValueError('Explicit support reference, not a reserve boolean')
        identifier(support.get('source_id'),'support reference source')
        settle = finite(support.get('nominal_settle_s'), 'support settle time', nonnegative=True)
        total = yaw_time+translation_time+sum(durations)+settle
        if not math.isfinite(total):
            raise ValueError('Nominal schedule overflow')
        payload = dict(binding=contract,
                       intent=deepcopy(problem['intent']),
                       successor_requirement=deepcopy(problem['successor_requirement']),
                       support_requirement=deepcopy(problem['support_requirement']),
                       base=dict(id=base['id'], origin_se2=origin, goal_se2=goal,
                                 source_support_ref=base['source_support_ref'],
                                 nominal_yaw_s=yaw_time, nominal_translation_s=translation_time),
                       arm=dict(id=arm['id'], waypoints=waypoints,
                                segment_nominal_s=durations, terminal_q=waypoints[-1]),
                       support=deepcopy(support),
                       schedule=('base_yaw','base_translation','arm_reference','support_settle'),
                       nominal_preparation_s=total,
                       reference_durations_are_not_measured_tracking_times=True)
        yield dict(payload, plan_sha256=digest(payload))


def optimize_preparation(problem, domain, evaluate):
    """Min nominal prep + main-operation/transfer cost for one fixed intent.

    evaluate(plan) must return a plan-bound constraint report and optional
    nonnegative operation_and_transfer_s. It is called for EACH complete plan,
    including changed support reference / path / base pose. No cached original
    WM forecast is assumed invariant under these changes. Actual native source
    authorization and independent geometric/error validity are outside this
    offline kernel; reports are conditional assumptions, never certificates.
    """
    problem, domain = deepcopy(problem), deepcopy(domain)
    result = dict(schema='conditional-execution-preparation-optimizer-v1',
                  scope='inner preparation only; fixed semantic intent and successor',
                  selected_plan=None, classified=[], conditional_optimal_value_proven=False,
                  optimality_domain='finite explicitly supplied executor reference domain only',
                  unknown_competitor_ids=[], execution_authorized=False,
                  runtime_connected=False, native_executor_modified=False,
                  independent_bounds_or_witnesses_verified=False,
                  mission_success_or_dynamic_safety_proven=False,
                  outer_semantic_selection_changed=False,
                  actual_prediction_reusable_after_preparation=False,
                  fresh_actual_observation_and_native_recheck_required=True,
                  preparation_can_change_WM_consequence=True)
    feasible, unresolved = [], []
    cap = problem.get('preparation_budget_s')
    overhead = domain.get('common_search_overhead_s')
    plans = list(generate_plans(problem,domain))
    result['generated_plan_count'] = len(plans)
    result['optimized_variables'] = dict(
        base_goal_count=len(domain['base_goals']),
        arm_reference_path_count=len(domain['arm_paths']),
        support_reference_count=len(domain['support_references']))
    for plan in plans:
        row = dict(plan_sha256=plan['plan_sha256'],
                   reference_ids=[plan[k]['id'] for k in ('base','arm','support')],
                   nominal_preparation_s=plan['nominal_preparation_s'],
                   nominal_total_s=None,
                   nominal_objective_lower_bound_s=plan['nominal_preparation_s'],
                   status='UNKNOWN', reasons=[])
        if cap is not None and plan['nominal_preparation_s'] > cap:
            row.update(status='OUTSIDE_DECLARED_PREPARATION_BUDGET',
                       reasons=['nominal_preparation_exceeds_explicit_cap'])
            result['classified'].append(row)
            continue
        report = evaluate(deepcopy(plan))
        if (not isinstance(report,dict) or report.get('plan_sha256') != plan['plan_sha256']
                or report.get('problem_sha256') != plan['binding']['problem_sha256']):
            row['reasons'].append('missing_same_full_plan_evaluation')
            unresolved.append(row)
            result['classified'].append(row)
            continue
        identifier(report.get('producer_id'),'constraint/cost producer')
        gates = report.get('gates')
        if not isinstance(gates,dict) or set(gates) != set(GATES):
            raise ValueError('Exact original and successor gate set required')
        if any(v is not None and type(v) is not bool for v in gates.values()):
            raise ValueError('Constraint values must be bool or None')
        row['gates'] = deepcopy(gates)
        row['producer_id'] = report['producer_id']
        if any(v is False for v in gates.values()):
            row.update(status='NOT_CERTIFIED_by_declared_constraints',
                       reasons=[k for k,v in gates.items() if v is False])
        else:
            future_cost = report.get('operation_and_transfer_s')
            if report.get('cost_contract_id') != problem['cost_contract_id']:
                future_cost = None
                row['reasons'].append('same_cost_contract_required')
            if future_cost is not None:
                future_cost = finite(future_cost,'operation/transfer time',nonnegative=True)
                identifier(report.get('cost_source_id'),'operation/transfer cost source')
                row['nominal_total_s'] = plan['nominal_preparation_s']+future_cost
                if not math.isfinite(row['nominal_total_s']):
                    raise ValueError('Nominal total cost overflow')
                row['nominal_objective_lower_bound_s'] = row['nominal_total_s']
                row['cost_source_id'] = report['cost_source_id']
            if any(v is None for v in gates.values()):
                row['reasons'].extend(k for k,v in gates.items() if v is None)
            if future_cost is None:
                row['reasons'].append('same_plan_operation_and_transfer_cost_unknown')
            if row['reasons']:
                unresolved.append(row)
            else:
                row['status'] = 'CONDITIONAL_ELIGIBLE'
                feasible.append((row,plan))
        result['classified'].append(row)
    if not feasible:
        return dict(result,status='UNKNOWN' if unresolved else 'NO_CERTIFIED_DOMAIN_PLAN',
                    reason='not_a_global_physical_infeasibility_proof')
    best, plan = min(feasible,key=lambda pair:(pair[0]['nominal_total_s'],pair[0]['plan_sha256']))
    blockers = [r['plan_sha256'] for r in unresolved
                if r['nominal_objective_lower_bound_s'] < best['nominal_total_s']]
    total = best['nominal_total_s']
    baseline = next((r for r in result['classified'] if
                     r['reference_ids'] == problem.get('baseline_reference_ids')), None)
    saving = (baseline['nominal_total_s']-total if baseline is not None and
              baseline['status']=='CONDITIONAL_ELIGIBLE' else None)
    return dict(result,
                status='CONDITIONAL_best_known_preparation' if blockers
                       else 'CONDITIONAL_finite_domain_optimum',
                selected_plan=deepcopy(plan), nominal_optimal_known_s=total,
                nominal_with_common_search_s=None if overhead is None else total+overhead,
                baseline_preparation=deepcopy(baseline),
                nominal_saving_vs_baseline_s=saving,
                saving_is_measured_task_benefit=False,
                common_search_overhead_s=overhead,
                optimal_nominal_value_s=None if blockers else total,
                conditional_optimal_value_proven=not blockers,
                unknown_competitor_ids=blockers,
                prepare_worthwhile='outer_planner_must_compare_same_goal_full_costs',
                next_actual_command='not_dispatched; native lowering and fresh admission required')
