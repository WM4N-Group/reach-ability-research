"""D3 finite single-first-PUSH receipt stop, no success predicate calls or replay."""
from types import MethodType
import time


def install_first_push_receipt_stop(driver=None, *, enabled=False):
    if type(enabled)is not bool:raise ValueError('Explicit diagnostic opt-in')
    if not enabled:return None
    if driver.r.step_count or driver.tick or driver.coordinator is not None or hasattr(driver,'_D3_receipt_hook'):
        raise ValueError('One fresh task0 original E driver before capture/seal')
    original=driver._connect_execution
    driver._D3_receipt_hook=True
    driver._D3_first_push_terminal=None
    def connect(this):
        if this is not driver or driver.coordinator is not None:raise RuntimeError('No hook rebind/resume')
        result=original()
        coordinator=driver.coordinator;observe=coordinator.observe
        def accepted(current,option,receipt):
            phase=current.phase
            answer=observe(option,receipt)  # Original model/coordinator accept FIRST.
            if phase=='interaction' and option.skill=='PUSH':
                from ainav.native.behavior_authority import NativeReceipt
                if type(receipt)is not NativeReceipt or receipt.option_sha256!=option.sha256:
                    raise RuntimeError('Only actual same original PUSH terminal')
                if receipt.status in ('succeeded','failed','hard_stop','budget_expired'):
                    if driver._D3_first_push_terminal is not None:raise RuntimeError('One first PUSH terminal')
                    driver._D3_first_push_terminal=dict(status=receipt.status,time_s=receipt.time_s,
                        option_sha256=receipt.option_sha256,evidence_ref=receipt.evidence_ref,
                        actual_task_steps=driver.r.step_count,original_acceptance_not_new_success_gate=True)
            return answer
        coordinator.observe=MethodType(accepted,coordinator)
        return result
    driver._connect_execution=MethodType(connect,driver)
    return driver


class D3LoopError(RuntimeError):
    def __init__(self,receipt):
        super().__init__('Original D3 execution stopped; safe receipt retained, no retry')
        self.receipt=receipt


def run_diagnostic(driver=None, *, watch=None,budget=None,video=None,scope_start_mono=None,enabled=False):
    if type(enabled)is not bool:raise ValueError('Explicit D3 loop opt-in')
    if not enabled:return None
    calls=0;reason=None;error=None;video_errors=[]
    start=time.monotonic()
    try:
        if driver.arm!='E' or driver.r.step_count!=0 or float(driver.r.sim.data.time)!=0.:
            raise ValueError('Fresh original E first-PUSH diagnostic only')
        if watch.state is not budget.state:raise ValueError('Original watch/ScopeIO same stop state')
        while True:
            watch()
            terminal=driver._D3_first_push_terminal
            if terminal is not None:
                if driver.r.step_count!=terminal['actual_task_steps']:raise RuntimeError('Command after first accepted PUSH receipt')
                reason='FIRST_ORIGINAL_PUSH_TERMINAL';break
            if (driver.r.step_count>=8000 or float(driver.r.sim.data.time)>=40. or
                    calls>=8128 or time.monotonic()-scope_start_mono>=1200):
                reason='FINITE_CAP_CENSORED';break
            option=None if driver.executor is None else driver.executor.option
            if option is not None and option.skill not in ('NAV','PUSH'):raise RuntimeError('D3 skill boundary')
            before=driver.r.step_count;calls+=1
            try:driver.step_one()
            finally:
                if driver.r.step_count>before:
                    try:video.capture_if_due()
                    except BaseException as exc:video_errors.append(type(exc).__name__);raise
            if driver.r.step_count-before not in (0,1):raise RuntimeError('One original physical issue per step')
            if driver.complete:raise RuntimeError('D3 never claims full E/V4 completion')
    except BaseException as exc:error=exc
    finally:
        if not budget.finalizing:budget.begin_finalization()
    terminal=driver._D3_first_push_terminal
    receipt=dict(driver_calls=calls,original_first_PUSH_terminal_observed=terminal is not None,
        original_first_PUSH_terminal=terminal,stop_reason=reason,primary_error_type=None if error is None else type(error).__name__,
        video_error_types=video_errors,loop_wall_s=time.monotonic()-start,loop_wall_excludes_parent_cleanup_encoding=True,
        native_finalization_sealed=budget.state.sealed,full_task_success_claimed=False,old_E20_cause_claimed=False,
        native_failure_label_not_invented=True,automatic_retry=False,
        original_error_tag=(str(error) if type(error)is RuntimeError and str(error) in {'push_finish_settled_confirmation_lost','push_finish_contact_lost'} else None),
        actual_original_executor_status=None if driver.executor is None else dict(reported_end=driver.executor.reported_end,last_outcome=driver.executor.last_outcome))
    if error is not None:raise D3LoopError(receipt)from None
    return receipt
