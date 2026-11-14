"""Audit-only stage diagnosis of observed successor cost, not policy input.

Names preserve the ORIGINAL report fields: first_clear/handoff/stable_start.
No inference of an Actor activation clock, hidden state, physical cause, new
parameter permission, dynamic guarantee or prediction of an unexecuted policy.
"""
import math


def need(ok,msg):
    if not ok:raise ValueError(msg)


def finite(x):return type(x) in (int,float) and math.isfinite(x)


def optional_time(x):
    if x is None:return None
    need(finite(x) and x>=0,'Finite nonnegative recorded clock');return x


def span(a,b):
    if a is None or b is None:return None
    need(a<=b,'Ordered recorded clocks');return b-a


def extract(raw,records):
    native=[r for r in raw.get('actual_native_results',[]) if r.get('skill')=='climb']
    bindings=[r['payload'] for r in records if r['payload'].get('event')=='intent_native_execution_bound'
              and r['payload'].get('native_option',{}).get('skill')=='CLIMB']
    need(len(native)<=1 and len(bindings)<=1,'Restricted to one original successor CLIMB, never pick one of many')
    report=native[0] if native else {};stop=report.get('stop',{});configuration=stop.get('configuration',{})
    receipts=[]
    if bindings:
        option=bindings[0]['native_option_sha256']
        receipts=[r['payload']['receipt'] for r in records if r['payload'].get('event')=='ainav_native_receipt'
                  and r['payload']['receipt']['option_sha256']==option]
    def unique(values,label):
        need(len(values)<=1,'Unique original '+label);return optional_time(values[0]) if values else None
    first=unique([r.get('time_s') for r in receipts if r.get('status')=='started'],'first motor receipt')
    terminal=unique([r.get('time_s') for r in receipts if r.get('status')=='succeeded'],'terminal receipt')
    confirmed=unique([e.get('time') for e in stop.get('events',[]) if e.get('event')=='stable_confirmed'],'stable-confirmed event')
    clocks=dict(first_motor=first,first_clear=optional_time(stop.get('first_clear_time')),
        handoff=optional_time(stop.get('handoff_time')),stable_start=optional_time(stop.get('stable_start_time')),
        stable_confirmed=confirmed,terminal=terminal)
    order=list(clocks);durations={a+'_to_'+b:span(clocks[a],clocks[b]) for a,b in zip(order,order[1:])}
    window=span(first,terminal)
    complete=all(x is not None for x in durations.values())
    if complete:need(abs(sum(durations.values())-window)<1e-9,'Stage sum must match literal motor window')
    for key,a,b in [('stop_seconds','handoff','stable_start'),('stop_seconds_from_clear','first_clear','stable_start')]:
        actual=span(clocks[a],clocks[b]);recorded=stop.get(key)
        if actual is not None and recorded is not None:
            need(finite(recorded) and abs(recorded-actual)<1e-9,'Original redundant stop-field identity: '+key)
    hold=durations['stable_start_to_stable_confirmed'];verify=durations['stable_confirmed_to_terminal']
    stable_cfg,verify_cfg=configuration.get('stable_seconds'),configuration.get('verify_seconds')
    # Only audit recorded timing vs declared unchanged holds; not a new native
    # admission/success gate. Missing fields remain partial, not task failure.
    residual=None
    if hold is not None and finite(stable_cfg):need(hold>=stable_cfg-1e-8,'Reported stable hold shorter than declaration')
    if verify is not None and finite(verify_cfg):
        need(verify>=verify_cfg-1e-8,'Reported verification shorter than declaration')
        residual=verify-verify_cfg
    return dict(scope_id=raw.get('scope_id'),owner_literal_passed=raw.get('passed'),
        coverage='COMPLETE_RECORDED_BOUNDARIES' if complete else 'PARTIAL_NOT_INFERRED',
        recorded_clocks_s=clocks,observed_intervals_s=durations,literal_motor_window_s=window,
        original_stop_configuration=configuration,observed_excess_over_configured_verify_s=residual,
        native_reported_seconds=report.get('seconds'),actual_Actor_activation_time_s=None,
        not_assigning_motor_start_or_native_seconds_to_Actor_clock=True,
        missing_optional_fields_do_not_relabel_native_success=True)


def compare(baseline,candidate):
    a,b=baseline['observed_intervals_s'],candidate['observed_intervals_s']
    delta={k:b[k]-a[k] if a[k] is not None and b[k] is not None else None for k in a}
    total=(candidate['literal_motor_window_s']-baseline['literal_motor_window_s']
           if candidate['literal_motor_window_s'] is not None and baseline['literal_motor_window_s'] is not None else None)
    complete=all(x is not None for x in delta.values())
    if complete:need(total is not None and abs(sum(delta.values())-total)<1e-9,'Successor penalty decomposition mismatch')
    return dict(schema='reach-observed-successor-CLIMB-stage-delta-v1',role='AUDIT_ONLY_NOT_PLANNER_INPUT_OR_FIT',
        coverage='COMPLETE_RECORDED_BOUNDARIES' if complete else 'PARTIAL_NOT_INFERRED',
        baseline=baseline,candidate=candidate,candidate_minus_baseline_intervals_s=delta,
        total_successor_CLIMB_window_increase_s=total,
        same_original_stop_configuration=(bool(baseline['original_stop_configuration']) and
            baseline['original_stop_configuration']==candidate['original_stop_configuration']),
        actual_state_or_contact_or_global_control_phase_cause_identified=False,
        unexecuted_policy_cost_predicted=False,changed_stop_parameters_or_holds_suggested=False,
        new_physics_or_native_or_model_or_fit_calls=0)
