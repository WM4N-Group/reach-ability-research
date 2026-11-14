"""Offline WM -> Reach condition adapter; never a planner or runtime safety gate.

WM predicts consequences. This adapter emits bound pre/post condition records
for ONE external planner; it never sorts, selects, executes or fabricates a
future robot state from displacement means, stds, event scores or latent codes.
All geometry/error/wrench inputs remain EXTERNAL, conditionally assumed facts.
Exact ID binding prevents reuse across queries; it does not certify provenance.
"""
from preparation_theory import number, path_request

CORE = ('decision_id', 'observation_id', 'candidate_id', 'executor_id', 'target_id')

# Names are this local adapter's aliases, not new claimed WM output schemas.
CONTRACTS = {
    'terminated_push_v2': dict(
        skills=('PUSH',), horizons_s=(.4, .8),
        endpoint='min_horizon_first_PUSH_exit',
        heads=('box_dx', 'box_dy', 'failure_within_horizon'),
        full_future_geometry=False, calibrated_error_bound=False),
    'visual_latent_macro_v1': dict(
        skills=('NAV', 'PUSH', 'CLIMB'), horizons_s=None,
        endpoint='macro_boundary',
        heads=('box_dx_anchor_body', 'box_dy_anchor_body',
               'robot_dx_anchor_body', 'robot_dz_anchor_body',
               'boundary_support_score', 'native_hard_stop_score'),
        full_future_geometry=False, calibrated_error_bound=False),
}


def _ids(record, keys):
    for key in keys:
        value = record.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError('Nonempty identifier required: '+key)
    return {key: record[key] for key in keys}


def _same(actual, expected):
    return isinstance(actual, dict) and all(
        type(actual.get(k)) is type(v) and actual[k] == v for k, v in expected.items())


def candidate_context(candidate):
    context = _ids(candidate, CORE)
    _ids(candidate, ('skill', 'postcondition_endpoint'))
    number(candidate.get('horizon_s'), 'horizon_s')
    if candidate['horizon_s'] <= 0:
        raise ValueError('Positive horizon required')
    shift = number(candidate.get('output_shift_m'), 'output_shift_m')
    if shift > .04:
        raise ValueError('Outside original40mm preparation domain')
    if type(candidate.get('reserve_required')) is not bool:
        raise ValueError('Explicit reserve requirement, not a default pass')
    return dict(context, skill=candidate['skill'], horizon_s=float(candidate['horizon_s']),
                postcondition_endpoint=candidate['postcondition_endpoint'],
                reserve_required=candidate['reserve_required'], output_shift_m=shift)


def forecast_capabilities(candidate, forecast):
    """Match anchor, candidate, execution contract, target and time semantics.

    No prediction values are treated as observed facts or hard constraints.
    Fixed-horizon continuation and stopped-option displacement are different
    estimands; the latter may not be relabelled as the former.
    """
    context = candidate_context(candidate)
    base = dict(status='UNKNOWN', missing=[], geometry_from_heads_available=False,
                uncertainty_is_error_bound=False, execution_authorized=False)
    if forecast is None:
        return dict(base, missing=['forecast'])
    if not _same(forecast.get('binding'), context):
        return dict(base, missing=['matching_forecast_anchor_candidate_executor_target'])
    contract = CONTRACTS.get(forecast.get('contract'))
    if contract is None:
        return dict(base, missing=['known_output_contract'])
    _ids(forecast, ('forecast_id',))
    horizon = number(forecast.get('horizon_s'), 'forecast horizon')
    if horizon != candidate['horizon_s']:
        return dict(base, missing=['matching_horizon'])
    if candidate['skill'] not in contract['skills']:
        return dict(base, missing=['skill_supported_by_output_contract'])
    if contract['horizons_s'] and horizon not in contract['horizons_s']:
        return dict(base, missing=['horizon_supported_by_output_contract'])
    if forecast.get('endpoint') != contract['endpoint']:
        return dict(base, missing=['honest_output_endpoint_semantics'])
    if candidate['postcondition_endpoint'] != contract['endpoint']:
        return dict(base, missing=['postcondition_endpoint_matches_predicted_estimand'])
    return dict(base, status='MATCHED_prediction_contract_only',
                contract=forecast['contract'], forecast_id=forecast['forecast_id'],
                heads=list(contract['heads']),
                missing=['interpretable_future_geometry', 'prospective_error_bounds',
                         'same_output_native_witnesses'],
                model_quality_or_calibration_verified=False,
                absent_geometry_information=['relative_robot_box_pose_or_declared_reference',
                                             'identified_joint_or_point_preparation_path',
                                             'prospective_error_domain',
                                             'same_output_native_support_and_required_reserve'])


def _witness(witness, expected, *, required=True):
    if not required:
        # This requirement is explicitly outside the candidate contract.
        return dict(status='NOT_REQUIRED', required=False)
    if not isinstance(witness, dict) or not _same(witness.get('binding'), expected):
        return dict(status='UNKNOWN', reason='missing_or_different_final_state_frame_path_phase_shift')
    if not all(isinstance(witness.get(k), str) and witness[k].strip()
               for k in ('producer_id', 'rule_id')):
        return dict(status='UNKNOWN', reason='missing_producer_or_rule')
    passed = witness.get('passed')
    if passed is not None and type(passed) is not bool:
        raise ValueError('Witness check must be bool or None')
    return dict(status='CONDITIONAL_PASS' if passed is True else
                       'NOT_CERTIFIED' if passed is False else 'UNKNOWN',
                producer_id=witness['producer_id'], rule_id=witness['rule_id'],
                independently_verified=False)


def assess_conditions(candidate, *, phase, geometry=None, witnesses=None,
                      forecast=None):
    """Evaluate preparation or future-postcondition without making a decision.

    geometry has a fully bound expected context and explicit point trajectories,
    not just a union of knots of unrelated points. Each trajectory contains one
    sample per knot. External error bounds must be bound to that same query.
    Future geometry is a separate declared producer, NOT inferred from WM heads.
    """
    core = candidate_context(candidate)
    if phase not in ('preparation', 'postcondition'):
        raise ValueError('Explicit preparation/postcondition phase required')
    result = dict(schema='offline-wm-reach-conditions-v1', binding=core,
                  phase=phase, status='UNKNOWN', reasons=[], geometry=None,
                  witnesses={}, execution_authorized=False,
                  dynamic_safety_certified=False, actual_feasibility_proven=False,
                  chosen_candidate=None, selection_owner='external_single_high_level_planner',
                  prospective_inputs_independently_verified=False,
                  executor_geometry_compatibility_verified=False)
    expected = dict(core, phase=phase, output_shift_m=float(candidate['output_shift_m']))
    if phase == 'postcondition':
        capability = forecast_capabilities(candidate, forecast)
        result['forecast_capabilities'] = capability
        if capability['status'] != 'MATCHED_prediction_contract_only':
            return dict(result, reasons=capability['missing'])
        expected.update(forecast_id=forecast['forecast_id'],
                        horizon_s=float(candidate['horizon_s']),
                        endpoint=candidate['postcondition_endpoint'])
    if geometry is None:
        return dict(result, reasons=['interpretable_geometry_not_supplied_no_state_fabrication'])
    binding = geometry.get('binding', {})
    if not _same(binding, expected):
        return dict(result, reasons=['geometry_context_mismatch'])
    _ids(binding, ('state_id', 'frame_id', 'path_id'))
    expected.update({key: binding[key] for key in ('state_id', 'frame_id', 'path_id')})
    result['geometry_binding'] = expected
    producer = geometry.get('producer')
    if not isinstance(producer, dict) or not all(
            isinstance(producer.get(k), str) and producer[k].strip()
            for k in ('producer_id', 'artifact_id', 'state_semantics')):
        return dict(result, reasons=['separate_geometry_producer_required'])
    semantics = 'measured_current_state' if phase == 'preparation' else 'externally_declared_nominal_future'
    if producer['state_semantics'] != semantics:
        return dict(result, reasons=['current_or_future_state_semantics_mismatch'])
    # A declaration of external future geometry is a condition, never a claim
    # that current WM heads supply it or that the producer has been validated.
    result['geometry_producer_assumed'] = dict(producer)
    if not _same(geometry.get('bounds_binding'), expected):
        return dict(result, reasons=['error_bounds_not_bound_to_geometry_query'])
    knots = geometry['knots']
    trajectories = geometry['point_trajectories']
    if not isinstance(trajectories, list) or not trajectories:
        raise ValueError('Nonempty identified trajectories required')
    names = set()
    points = []
    for trajectory in trajectories:
        identifier = trajectory.get('point_id')
        if not isinstance(identifier, str) or not identifier.strip() or identifier in names:
            raise ValueError('Unique point trajectory identifiers required')
        names.add(identifier)
        if len(trajectory['points_m']) != len(knots):
            raise ValueError('Each point trajectory must cover all knots')
        for point in trajectory['points_m']:
            if len(point) != 3:
                raise ValueError('Three-vector geometry point required')
            points.append([number(x, 'point', nonnegative=False) for x in point])
    tube = path_request(points, geometry['half_size_m'], geometry['axis'],
                        geometry['inflation_m'], knots, geometry.get('bounds'))
    result['geometry'] = tube
    witnesses = {} if witnesses is None else witnesses
    if not isinstance(witnesses, dict):
        raise ValueError('Witness map required')
    for gate in ('support', 'reserve', 'original_gates'):
        result['witnesses'][gate] = _witness(witnesses.get(gate), expected,
                                           required=(gate != 'reserve' or candidate['reserve_required']))
    needed = tube['required_shift_m']
    states = [w['status'] for w in result['witnesses'].values()]
    if needed is not None and candidate['output_shift_m'] < needed:
        result['reasons'].append('output_below_sufficient_geometry_request')
    if 'NOT_CERTIFIED' in states:
        result['reasons'].append('same_output_native_witness_failed')
    if result['reasons']:
        return dict(result, status='NOT_CERTIFIED_by_declared_conditions')
    if needed is None:
        result['reasons'].append('prospective_error_budget_unknown')
    if 'UNKNOWN' in states:
        result['reasons'].append('same_output_native_witness_unknown')
    if result['reasons']:
        return result
    return dict(result, status='CONDITIONAL_declared_conditions_only')


def planner_record(candidate, preparation, postcondition, *, nominal_cost_s=None, cost_source_id=None):
    """One planner's inputs, never a second local argmin or runtime authority.

    Comparable cost source/candidate set is the planner's contract. None remains
    unknown, never zero; blocked is not physical unreachability. This adapter
    deliberately cannot infer whole-task success from boundary conditions.
    """
    core = candidate_context(candidate)
    rows = (preparation, postcondition)
    for row, phase in zip(rows, ('preparation', 'postcondition')):
        if (not isinstance(row, dict) or row.get('schema') != 'offline-wm-reach-conditions-v1'
                or not _same(row.get('binding'), core) or row.get('phase') != phase
                or row.get('geometry_binding', {}).get('output_shift_m') not in
                   (None, float(candidate['output_shift_m']))):
            raise ValueError('Condition records must bind to the same candidate and phase')
        if row.get('status') not in ('UNKNOWN', 'NOT_CERTIFIED_by_declared_conditions',
                                     'CONDITIONAL_declared_conditions_only'):
            raise ValueError('Unknown condition status')
    cost = None if nominal_cost_s is None else number(nominal_cost_s, 'nominal_cost_s')
    if cost_source_id is not None and (not isinstance(cost_source_id, str) or not cost_source_id.strip()):
        raise ValueError('Nonempty cost source identifier required')
    statuses = [row['status'] for row in rows]
    ready = all(s == 'CONDITIONAL_declared_conditions_only' for s in statuses)
    return dict(schema='offline-single-planner-condition-record-v1', binding=core,
                output_shift_m=float(candidate['output_shift_m']),
                condition_status='NOT_CERTIFIED' if any(s.startswith('NOT_CERTIFIED') for s in statuses)
                else 'CONDITIONAL' if ready else 'UNKNOWN',
                ready_for_conditional_cost_comparison=ready and cost is not None and cost_source_id is not None,
                nominal_cost_s=cost, cost_source_id=cost_source_id, condition_records=list(rows),
                cost_is_validated_task_time=False, selected=False,
                selection_owner='external_single_high_level_planner',
                execution_authorized=False, task_success_predicted=False)


NATIVE_SUPPORT_SHA256 = 'b9716741b182a27645a3fcc21badfd411da702c619f4b5ca087af81b1b230035'


def native_plan_digest(plan):
    """Canonical JSON receipt hash; not a signature or physical provenance proof."""
    import hashlib
    import json
    return hashlib.sha256(json.dumps(plan, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


def adapt_native_support_plan(plan, expected_binding, receipt=None):
    """Translate original prospective_support result WITHOUT borrowing grid rows.

    The original plan has no query/state/path ID. A NEW read-only caller receipt
    is therefore required to bind it; historical plan dictionaries alone remain
    UNKNOWN. This function does not create that live receipt or run allocation.
    Receipt records native source SHA, raw-plan hash and consumed output field.
    Original gates outside this helper are ALWAYS unknown from this plan alone.
    """
    _ids(expected_binding, CORE+('state_id', 'frame_id', 'path_id', 'phase'))
    shift = number(expected_binding.get('output_shift_m'), 'native witness shift')
    if shift > .04:
        raise ValueError('Outside original40mm witness domain')
    result = {gate:dict(binding=dict(expected_binding), passed=None,
                        producer_id='offline-native-plan-adapter',
                        rule_id='native-source-'+NATIVE_SUPPORT_SHA256+':'+gate,
                        reason='no_bound_native_call_receipt')
              for gate in ('support', 'reserve', 'original_gates')}
    result['adapter_metadata'] = dict(runtime_call_connected=False,
                                      original_gates_inferred=False,
                                      source_or_receipt_independently_verified=False)
    if receipt is None:
        return result
    if (not isinstance(receipt, dict) or not _same(receipt.get('binding'), expected_binding)
            or receipt.get('native_source_sha256') != NATIVE_SUPPORT_SHA256
            or receipt.get('raw_plan_sha256') != native_plan_digest(plan)):
        return result
    consumer = receipt.get('consumed_output_field')
    if consumer not in ('shift_m', 'push_support_shift_m'):
        return result
    if number(plan.get(consumer), 'consumed native output') != shift:
        return result
    for gate, key in (('support', 'checks'), ('reserve', 'push_reserve_checks')):
        rows = plan.get(key, [])
        if not isinstance(rows, list):
            raise ValueError('Native checks must be a list')
        matches, seen = [], set()
        for row in rows:
            d = number(row.get('shift_m'), 'native checked shift')
            if d > .04 or d in seen:
                raise ValueError('Duplicate or out-of-domain native check')
            seen.add(d)
            if type(row.get('passed')) is not bool:
                raise ValueError('Explicit native passed bool required')
            force = number(row.get('max_force_residual'), 'force residual')
            moment = number(row.get('max_moment_residual'), 'moment residual')
            if row['passed'] != (force <= .5 and moment <= .1):
                raise ValueError('Native bool disagrees with original residual thresholds')
            if d == shift:
                matches.append(row)
        result[gate]['reason'] = 'no_check_at_this_exact_final_output'
        if matches:
            result[gate].update(passed=matches[0]['passed'],
                                checked_shift_m=shift,
                                max_force_residual=matches[0]['max_force_residual'],
                                max_moment_residual=matches[0]['max_moment_residual'],
                                reason='same_output_native_row_only')
    result['original_gates']['reason'] = 'not_supplied_by_prospective_support'
    return result
