"""Explain action influence at the actual prospective_entry branch, without FK.

This is an observer, not a new policy, safety gate, simulator, or success label.
Its only exact certificate concerns reuse of the native support plan. A request
that takes the recomputation branch is NOT thereby safe, feasible, or useful.
"""
import ast
import hashlib
import math

ARMS = ('P0', 'P1', 'P2', 'P3')
LIMIT_M = .04

# Deliberately bind the certificate to the executed branch rather than replacing
# the native support search/reserve logic with max(support, geometry).
EXPECTED_SUFFIX = '''minimum=preview['minimum_shift_m']
plan=baseline if minimum<=baseline['shift_m'] else prospective_support(c,robot,joint_ids,joint_names,reserve_for_late_parking=reserve_for_late_parking,nominal_translation_w=nominal_translation_w,minimum_shift_m=minimum)
plan['support_only_shift_m']=baseline['shift_m']
plan['box_approach_preview']=preview
return plan
'''


def verify_native_branch(source_text):
    """Reject drift in the precise native branch used by this explanation."""
    tree = ast.parse(source_text)
    functions = [n for n in tree.body if isinstance(n, ast.FunctionDef)
                 and n.name == 'prospective_entry']
    if len(functions) != 1:
        raise ValueError('Expected exactly one native prospective_entry')
    actual = ast.Module(body=functions[0].body[-5:], type_ignores=[])
    expected = ast.parse(EXPECTED_SUFFIX)
    if ast.dump(actual, include_attributes=False) != ast.dump(expected, include_attributes=False):
        raise ValueError('Native selection branch changed; certificate not applicable')
    return {'schema': 'native-entry-branch-binding-v1',
            'probe_sha256': hashlib.sha256(source_text.encode()).hexdigest(),
            'selection_branch_ast_sha256': hashlib.sha256(
                ast.dump(actual, include_attributes=False).encode()).hexdigest(),
            'verified_scope': 'last five statements of prospective_entry only; '
                              'not support/FK implementation or preconditions'}


def finite_shift(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if not math.isfinite(value) or not 0. <= value <= LIMIT_M:
        return None
    return float(value)


def describe_request(baseline_shift_m, minimum_shift_m):
    """Conditional certificate after upstream native checks have succeeded.

    No epsilon is added: the executed <= branch uses exact float comparison.
    Invalid/missing values are unknown, never a silently feasible zero.
    """
    baseline, request = finite_shift(baseline_shift_m), finite_shift(minimum_shift_m)
    result = dict(baseline_shift_m=baseline, minimum_shift_m=request,
                  selected_shift_m=None, support_headroom_m=None,
                  branch=None, baseline_plan_reused=None,
                  status='unknown', execution_authorized=False,
                  task_success=None, tracking_or_dynamic_safety_certified=False)
    if baseline is None or request is None:
        result['reason'] = 'missing_or_outside_native_0_to_40mm_domain'
        return result
    result['support_headroom_m'] = baseline - request
    if request <= baseline:
        result.update(status='baseline_reuse_proven', branch='reuse_native_baseline',
                      selected_shift_m=baseline, baseline_plan_reused=True,
                      reason='native request<=baseline branch reuses the support plan')
    else:
        result.update(status='native_recomputation_required', branch='recompute_native_support',
                      baseline_plan_reused=False,
                      reason='requires actual native support search and optional push reserve; '
                             'do not approximate by max(baseline, request)')
    return result


def compare_requests(baseline_shift_m, left_request_m, right_request_m):
    left = describe_request(baseline_shift_m, left_request_m)
    right = describe_request(baseline_shift_m, right_request_m)
    # If either leaves the reuse branch, the search may fail or have additional
    # reserve behavior. No counterfactual selection or outcome is manufactured.
    proven = left['baseline_plan_reused'] is True and right['baseline_plan_reused'] is True
    return dict(left=left, right=right,
                same_native_entry_shift_proven=proven,
                selected_shift_delta_m=0. if proven else None,
                status='no_entry_shift_contrast_proven' if proven else 'unknown_contrast',
                scope='same native input/support-plan witness only; not identical '
                      'runtime, future trajectories, task truth, or global unreachability')


def proposal_readiness(baseline_shift_m, left_request_m, right_request_m):
    """Descriptive strata; MUST NOT drop masked/failed trials from a denominator."""
    comparison = compare_requests(baseline_shift_m, left_request_m, right_request_m)
    if comparison['same_native_entry_shift_proven']:
        stratum = 'support_masked_negative_control'
    elif any(x['status'] == 'unknown' for x in (comparison['left'], comparison['right'])):
        stratum = 'invalid_or_missing_input'
    else:
        stratum = 'native_recomputation_needed_not_yet_action_contrast'
    return dict(comparison=comparison, predecision_stratum=stratum,
                action_contrast_demonstrated=False,
                must_keep_registered_failure_and_masked_cases=True,
                dispatch_enabled=False)


def frozen_cloud_translation_window(baseline_shift_m, left_maximum_x_m,
                                    right_maximum_x_m, half_x_m,
                                    inflation_m, world_x_in_box_x):
    """Conditional geometric design window, NOT a new physical initial state.

    Translate the box toward the fixed cloud by delta along its LOCAL x axis.
    Hold robot state, box orientation, reference, waypoints, yz gate and support
    witness fixed. Then each selected maximum increases by delta exactly, so
    m_i(delta)=max(0,(maximum_i+half_x+inflation+delta)/axis_x).

    Return delta where left reuses baseline but right needs native recomputation.
    Neither the support witness nor the same query is guaranteed to remain valid
    if a real episode is restarted with a differently placed box.
    """
    empty = dict(status='unknown', lower_open_m=None, upper_closed_m=None,
                 nominal_midpoint_m=None, execution_authorized=False,
                 physical_state_validated=False, task_success=None,
                 assumptions=['fixed robot/waypoints/reference/box rotation/yz gate',
                              'same support witness; local-box-x translation only'],
                 scope='finite-cloud design algebra only; not a sampled robot case '
                       'or prediction of a restarted episode')
    d0 = finite_shift(baseline_shift_m)
    values = (left_maximum_x_m, right_maximum_x_m, half_x_m, inflation_m, world_x_in_box_x)
    if d0 is None or any(isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) for x in values):
        return empty
    if half_x_m <= 0. or inflation_m < 0. or not .95 <= world_x_in_box_x <= 1.+1e-5:
        return empty
    axis = world_x_in_box_x
    left_numerator = left_maximum_x_m + half_x_m + inflation_m
    right_numerator = right_maximum_x_m + half_x_m + inflation_m
    lower = axis*d0 - right_numerator
    upper = min(axis*d0-left_numerator, axis*LIMIT_M-right_numerator)
    # A box motion toward the cloud is delta>=0. Use a strict positive interior
    # to avoid promoting a float-rounded threshold equality to a trigger.
    interior_lower = max(0.,lower)
    if not interior_lower < upper:
        return dict(empty,status='no_positive_translation_window')
    delta = (interior_lower+upper)/2.
    left_request=max(0.,(left_numerator+delta)/axis)
    right_request=max(0.,(right_numerator+delta)/axis)
    comparison=compare_requests(d0,left_request,right_request)
    if not comparison['left']['baseline_plan_reused'] or comparison['right']['baseline_plan_reused'] is not False:
        return empty
    return dict(empty,status='conditional_finite_cloud_window',lower_open_m=lower,
                upper_closed_m=upper,nonnegative_delta_required=True,
                nominal_midpoint_m=delta,midpoint_requests=comparison)
