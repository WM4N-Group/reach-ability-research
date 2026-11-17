"""One fresh original startup -> first actual arm-admission boundary, never PUSH.

This is a new missing-observation question, not a retry of a closed skill run.
Original startup/world/guards remain owned by the original bounded parent.
"""
import time
from standard_runtime import need, bounded_exception
from push_l0_driver import driver_class as _original_driver_class, CaseLoopError
from l0_witness import OriginalL0Witness as _OriginalL0Witness


def driver_class(*, source_root=None, legacy_base_dir=None, legacy_guard_dir=None,
                 legacy_driver_source=None, enabled=False):
    need(type(enabled) is bool, 'Explicit first-arm-boundary source opt-in')
    if not enabled:
        return None
    Base = _original_driver_class(source_root=source_root, legacy_base_dir=legacy_base_dir,
                                  legacy_guard_dir=legacy_guard_dir,
                                  legacy_driver_source=legacy_driver_source, enabled=True)
    class FirstArmBoundaryDriver(Base):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.boundary_reached = False

        def _connect_execution(self):
            need(self.loop is None and self.executor is None and self.factory is None,
                 'No task session/query/Actor permitted in boundary diagnostic')
            owner = self.startup
            need(owner.r is self.r, 'Actual same startup/runtime owner')
            # Exact original finish preconditions; constructor runs its whole
            # original validate ONCE. Calling finish() would validate twice on PASS.
            need(owner.startup.finished and not owner.startup.failed and
                 owner.startup.original_result['stable'] is True,
                 'Original standalone startup must ACTUALLY settle')
            need(owner.startup.issued == owner.r.step_count >= 2 and len(owner.startup.last_two) == 2 and
                 abs(float(owner.r.sim.data.time)-owner.r.step_count*.005) < 1e-7,
                 'Every actual startup issue accounted; no count backfill')
            need(owner.witness is None and owner.arm_gate_attempts == 0,
                 'First boundary only, no repeated witness/guard')
            owner.phase = 'PREPARED_L0_SETTLE_FINISHED_AWAIT_REGISTERED_PUSH12N'
            witness = _OriginalL0Witness(owner)  # All unchanged validation gates in the actual constructor.
            owner.witness = witness
            owner.phase = 'PREPARED_L0_CURRENT_REGISTERED_PUSH12N_READY'
            need(owner.arm_gate_attempts == 1 and owner.arm_gate_audit['original_guard_calls'] == 1,
                 'Exactly ONE original arm guard invocation, never a second poll')
            self._write_boundary(dict(time_s=float(self.r.sim.data.time),
                event='prepared_L0_live_bias_arm_admission_boundary_reached_NO_SKILL_SELECTED',
                startup=self.startup.report(), task_or_Actor_authorized=False))
            self.boundary_reached = True
            # Do not call Base._connect_execution/connect/factory/EntryJudge/Actor.
    return FirstArmBoundaryDriver


def run_case(driver=None, *, watch=None, budget=None, video=None,
             scope_start_mono=None, enabled=False):
    need(type(enabled) is bool, 'Explicit future first-boundary diagnostic')
    if not enabled:
        return None
    need(driver.r.step_count == 0 and float(driver.r.sim.data.time) == 0.
         and watch.state is budget.state, 'Fresh actual world, never restore/replay')
    calls, error, reason = 0, None, None
    started = time.monotonic()
    try:
        while True:
            watch()
            if driver.boundary_reached:
                reason = 'FIRST_ARM_BOUNDARY_COMPLETED_NO_TASK_OR_ACTOR'
                break
            if (driver.r.step_count >= 2200 or float(driver.r.sim.data.time) >= 11.
                    or calls >= 2400 or time.monotonic()-scope_start_mono >= 300.):
                reason = 'FINITE_BOUNDARY_DIAGNOSTIC_CENSORED'
                break
            need(driver.loop is None and driver.executor is None and driver.factory is None,
                 'Boundary diagnostic never permits task selection/session')
            before = driver.r.step_count
            calls += 1
            try:
                driver.step_one()  # Original external-step/ack startup only.
            finally:
                if driver.r.step_count > before:
                    video.capture_if_due()
            need(driver.r.step_count-before in (0, 1), 'One actual original issue per call')
    except BaseException as exc:
        error = exc
        reason = 'ORIGINAL_STARTUP_OR_FIRST_ARM_GATE_REFUSED_NO_RETRY'
    finally:
        if not budget.finalizing:
            budget.begin_finalization()
    audit = driver.startup.arm_gate_audit
    receipt = dict(driver_calls=calls, stop_reason=reason, full_case_success=False,
        diagnostic_boundary_reached=bool(driver.boundary_reached),
        diagnostic_same_call_sample_complete=bool(audit and audit.get('sample_complete')),
        diagnostic_guard_returned=bool(audit and audit.get('stage') == 'ORIGINAL_GUARD_RETURNED'),
        original_error=None if error is None else bounded_exception(error),
        root_terminal_receipts=[], startup=driver.startup.report(),
        task_steps=driver.r.step_count, task_sim_s=float(driver.r.sim.data.time),
        loop_wall_s=time.monotonic()-started, automatic_retry=False,
        no_task_query_or_option_or_Actor=True, Actor_failure_or_training_need_not_inferred=True)
    if error is not None:
        raise CaseLoopError(receipt, error) from error
    return receipt  # Always non-skill: engineering observation is NOT task success.
