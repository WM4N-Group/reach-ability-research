"""CPU label contract for frozen PUSH until its FIRST observed option exit.

Labels, never model inputs. Recovering after an exit does not supply fictitious
continued-PUSH futures. Unknown futures are censored, not padded with zero.
"""
import math

FAILURES=frozenset(('soft_progress_abort','native_hard_protection'))
EXITS=FAILURES|{'native_goal_reached'}


def label_until_exit(*,query_time,horizon,query_xy,measured_horizon_xy=None,exit_event=None,horizon_PUSH_active=False):
    if not all(type(v) in (int,float) and math.isfinite(v) for v in (query_time,horizon)) or horizon not in (.4,.8) or query_time<0:raise ValueError('Registered finite query/.4-or-.8 horizon required')
    def xy(value):
        if not isinstance(value,(list,tuple)) or len(value)!=2 or not all(type(v) in (int,float) and math.isfinite(v) for v in value):raise ValueError('Actual finite measured XY required')
        return [float(v) for v in value]
    origin=xy(query_xy);end=query_time+horizon;failure=False
    if exit_event is not None:
        if set(exit_event)!={'time_s','box_xy','kind','actual_measured','first_exit'}:raise ValueError('Exact immutable first-exit event required')
        t=exit_event['time_s']
        if type(t) not in (int,float) or not math.isfinite(t) or t<=query_time:raise ValueError('Query must be strictly before active-option first exit')
        if exit_event['kind'] not in EXITS or exit_event['actual_measured'] is not True or exit_event['first_exit'] is not True:raise ValueError('Observed first native goal/soft/hard exit only; timeouts are censoring')
        if t<=end+1e-9:
            future=xy(exit_event['box_xy']);end=t;failure=exit_event['kind'] in FAILURES
            return dict(valid=True,dxdy_m=[a-b for a,b in zip(future,origin)],failure_within_horizon=failure,effective_future_time_s=end,label_endpoint='actual_first_PUSH_exit',future_after_exit_used=False)
    if type(horizon_PUSH_active) is not bool:raise ValueError('Explicit actual horizon activity flag required')
    if measured_horizon_xy is not None and exit_event is None and not horizon_PUSH_active:return dict(valid=False,censor_reason='horizon_PUSH_activity_unverified_no_recovery_future_labels',future_after_exit_used=False)
    if measured_horizon_xy is None:return dict(valid=False,censor_reason='active_PUSH_future_not_observed_no_zero_fill',future_after_exit_used=False)
    future=xy(measured_horizon_xy)
    return dict(valid=True,dxdy_m=[a-b for a,b in zip(future,origin)],failure_within_horizon=False,effective_future_time_s=end,label_endpoint='actual_active_PUSH_horizon',future_after_exit_used=False)
