"""Finite C/D stepping component for a FUTURE qualified Data worker.

Requires already-constructed original cd_entry driver, genuine owner/watch guard,
ScopeIO and current live camera. Does not create any of them or authorize a run.
Original driver.complete is set only after its original complete-task verifier;
False step return / one skill receipt / forecasts never imply task completion.
"""
from dataclasses import dataclass
import math
import time


@dataclass(frozen=True)
class MainLimits:
    max_commands: int
    max_driver_calls: int
    task_sim_cap_s: float
    scope_wall_cap_s: float
    allowed_skills: tuple

    def __post_init__(self):
        if (type(self.max_commands) is not int or self.max_commands <= 0 or
                type(self.max_driver_calls) is not int or
                self.max_driver_calls <= 0):
            raise ValueError('Explicit finite command and driver-call budgets')
        for x in (self.task_sim_cap_s, self.scope_wall_cap_s):
            if type(x) not in (int, float) or not math.isfinite(x) or x <= 0:
                raise ValueError('Explicit finite positive task-sim and scope-wall caps')
        if (type(self.allowed_skills) is not tuple or not self.allowed_skills or
                len(set(self.allowed_skills)) != len(self.allowed_skills) or
                not set(self.allowed_skills) <= {'NAV', 'PUSH', 'CLIMB'}):
            raise ValueError('Explicit registered skill subset, not blanket permission')


def make_cd_phase_health(original_health=None, driver_reader=None, stop_state=None,
                         allowed_skills=None, *, enabled=False):
    """Replacement for OLD PERF's NAV-only policy in a NEW C/D program only.

    Original RSS/GPU/wall fast-health is called exactly once. No external probe,
    owner timestamp, new lease or fake freshness is created here. Native issue
    remains protected by the original ResourceWatch/indexed pre-issue gate.
    """
    if type(enabled) is not bool:
        raise ValueError('Explicit health opt-in')
    if not enabled:
        return None
    if not callable(original_health) or not callable(driver_reader) or not callable(getattr(stop_state, 'fail', None)):
        raise ValueError('Original health, live driver reader and shared stop latch')
    if type(allowed_skills) is not tuple or not allowed_skills or not set(allowed_skills) <= {'NAV', 'PUSH', 'CLIMB'}:
        raise ValueError('Frozen skill subset')
    allowed = frozenset(allowed_skills)

    def health():
        answer = original_health()
        if answer is not None and answer is not True:
            stop_state.fail('Unknown original fast-health result')
            raise RuntimeError('Shared stop latch failed to raise')
        driver = driver_reader()
        executor = None if driver is None else driver.executor
        option = None if executor is None else executor.option
        if option is not None and option.skill not in allowed:
            stop_state.fail('Current native skill outside frozen C/D task subset')
            raise RuntimeError('Shared stop latch failed to raise')
        return True
    health._data_cd_allowed_skills = allowed
    health._data_cd_stop_state = stop_state
    return health


class LoopError(RuntimeError):
    def __init__(self, receipt, original_error=None):
        super().__init__('C/D loop stopped; sanitized receipt retained, never resume')
        self.receipt = receipt
        self.original_error = original_error  # In-process only; never serialize args/headers.


def _usage(runtime):
    try:
        steps, sim = runtime.step_count, float(runtime.sim.data.time)
        if type(steps) is not int or steps < 0 or not math.isfinite(sim) or sim < 0:
            raise ValueError('Unknown actual clock/count')
        return dict(actual_task_steps=steps, actual_task_sim_s=sim, usage_known=True)
    except Exception:
        return dict(actual_task_steps=None, actual_task_sim_s=None, usage_known=False)


def _counts(driver):
    """Whitelisted public integer counters, no backend identity/__dict__/opener."""
    try:
        backend = driver.planner.baseline.roles.backend
        api = {key: value if type(value) is int and value >= 0 else None
               for key, value in [('calls', backend.calls), ('total_tokens', backend.total_tokens)]}
    except Exception:
        api = dict(calls=None, total_tokens=None)
    factor = {}
    for key in ('legacy_kernel_attempts', 'legacy_kernel_completed', 'legacy_kernel_failed',
                'legacy_kernel_result_changed', 'legacy_callback_choice_events',
                'new_successor_choice_events', 'new_successor_choice_changed_events'):
        try:
            value = driver.journal.counts[key]
            factor[key] = value if type(value) is int and value >= 0 else None
        except Exception:
            factor[key] = None
    return dict(backend_public_counters=api, original_factor_counts=factor)


def run_task(driver=None, *, budget=None, video=None, guard=None, limits=None,
             scope_start_mono=None, enabled=False):
    """One bounded main loop; one available-ScopeIO seal attempt, no cleanup ownership.

    The parent must already enforce original wall signal/watchdog/lease/IO and
    owns all finally-close/encode/report costs. This loop cannot preempt a blocked
    step/kernel/API. Its interval is not all-inclusive phase wall or exclusive CPU.
    Exceptions retain actual count and late original completion, not FAILED labels.
    """
    if type(enabled) is not bool:
        raise ValueError('Explicit loop opt-in')
    if not enabled:
        return None
    entered = time.monotonic()
    try:runtime = driver.r
    except Exception:runtime = None
    observed_scope_start = None
    primary = None
    seal_error = None
    seal_attempted = False
    seal_completed = None
    video_error_types = []
    calls = no_step_calls = unknown_step_calls = issued = 0
    step_wall = []
    task_complete = False
    stop_reason = None
    try:
        if (type(limits) is not MainLimits or not callable(guard) or
                not callable(getattr(budget, 'begin_finalization', None)) or
                not callable(getattr(video, 'capture_if_due', None))):
            raise ValueError('Frozen finite limits, genuine guard, ScopeIO and live recorder required')
        phase_health = getattr(guard, 'fast_health', None)
        if (getattr(guard, 'state', None) is not getattr(budget, 'state', None) or
                getattr(phase_health, '_data_cd_stop_state', None) is not budget.state or
                getattr(phase_health, '_data_cd_allowed_skills', None) != frozenset(limits.allowed_skills)):
            raise ValueError('Original watch, phase-health and ScopeIO must share ONE stop state/skill subset')
        if (type(scope_start_mono) not in (int, float) or not math.isfinite(scope_start_mono) or
                scope_start_mono > entered):
            raise ValueError('Actual parent scope start, not a reset loop-only wall clock')
        observed_scope_start = scope_start_mono
        if driver.arm not in ('C', 'D') or driver.complete is not False:
            raise ValueError('Fresh original C/D driver, no complete/closed resume')
        runtime = driver.r
        usage = _usage(runtime)
        if not usage['usage_known'] or usage['actual_task_steps'] != 0 or usage['actual_task_sim_s'] != 0.:
            raise ValueError('Fresh task-zero actual runtime required')
        while True:
            answer = guard()
            if answer is not None and answer is not True:
                raise ValueError('Unknown owner/watch guard result')
            option = None if driver.executor is None else driver.executor.option
            if option is not None and option.skill not in limits.allowed_skills:
                raise ValueError('Current option outside frozen task skill subset')
            before = _usage(runtime)
            if not before['usage_known']:
                raise ValueError('Actual task accounting unreadable')
            elapsed = time.monotonic() - scope_start_mono
            if not math.isfinite(elapsed) or elapsed < 0:
                raise ValueError('Invalid actual scope wall observation')
            if elapsed >= limits.scope_wall_cap_s:
                stop_reason = 'SCOPE_WALL_CAP';break
            if before['actual_task_steps'] >= limits.max_commands:
                stop_reason = 'COMMAND_CAP';break
            if before['actual_task_sim_s'] + .005 > limits.task_sim_cap_s + 1e-8:
                stop_reason = 'TASK_SIM_CAP';break
            if calls >= limits.max_driver_calls:
                stop_reason = 'DRIVER_CALL_CAP';break
            began = time.monotonic()
            call_error = None
            try:
                driver.step_one()  # Original body/guards unchanged; False can be a no-step transition.
            except BaseException as exc:
                call_error = exc
            finally:
                calls += 1
                after = _usage(runtime)
                if after['usage_known'] and after['actual_task_steps'] > before['actual_task_steps']:
                    issued += after['actual_task_steps'] - before['actual_task_steps']
                    try:
                        video.capture_if_due()  # Current live only, including a last issued step on error.
                    except BaseException as exc:
                        video_error_types.append(type(exc).__name__)
                        if call_error is None:call_error = exc
                    step_wall.append(time.monotonic() - began)
                elif after['usage_known'] and after['actual_task_steps'] == before['actual_task_steps']:
                    no_step_calls += 1
                else:
                    unknown_step_calls += 1
            if call_error is not None:
                raise call_error
            if (not after['usage_known'] or
                    after['actual_task_steps'] - before['actual_task_steps'] not in (0, 1) or
                    abs(after['actual_task_sim_s'] - after['actual_task_steps'] * .005) > 1e-7):
                raise ValueError('Original one-command 200Hz clock/count invariant')
            if driver.complete is True:
                answer = guard()
                if answer is not None and answer is not True:
                    raise ValueError('Owner refused after terminal observation')
                task_complete = True
                break
    except BaseException as exc:
        primary = exc
    finally:
        if callable(getattr(budget, 'begin_finalization', None)):
            seal_attempted = True
            try:
                budget.begin_finalization()  # Irreversible native seal BEFORE parent cleanup.
                seal_completed = budget.state.sealed
                if seal_completed is not True:
                    raise ValueError('Native finalization seal not confirmed')
            except BaseException as exc:seal_error = exc
    finished = time.monotonic()
    try:observed_complete = driver.complete is True
    except Exception:observed_complete = None
    receipt = dict(status=('EXCEPTION_NO_NATIVE_FAILURE_LABEL' if primary or seal_error else
                           'ORIGINAL_TASK_GATE_COMPLETE' if task_complete else 'BUDGET_CENSORED'),
        original_driver_complete_observed=observed_complete,
        accepted_task_complete=task_complete and primary is None and seal_error is None,
        censor_reason=stop_reason, native_failure_label=None, automatic_retry=False,
        driver_calls=calls, no_step_calls=no_step_calls, unknown_step_calls=unknown_step_calls,
        observed_commands_issued=issued, issued_count_is_only_lower_bound=unknown_step_calls > 0,
        loop_wall_s=finished-entered,
        scope_start_to_loop_exit_wall_s=(None if observed_scope_start is None else finished-observed_scope_start),
        excludes_parent_cleanup_encoding_report_wall=True, exclusive_CPU_or_physics_time=False,
        primary_error_type=None if primary is None else type(primary).__name__,
        seal_error_type=None if seal_error is None else type(seal_error).__name__,
        native_seal_attempted=seal_attempted, native_seal_completed=seal_completed,
        video_error_types=video_error_types, step_wall_samples_s=step_wall,
        step_wall_scope='driver.step_one plus due live capture, excludes pre-call guard',
        backend_counters_are_not_total_API_or_billing=True, model_input_allowed=False,
        auxiliary_calibration_not_inferred_from_task_or_old_zero=True,
        parent_still_owns_watch_lease_writer_observer_cleanup=True,
        M1_or_method_gain_or_independent_effect_claimed=False, **_usage(runtime), **_counts(driver))
    if primary is not None or seal_error is not None:
        raise LoopError(receipt, primary or seal_error) from None
    return receipt
