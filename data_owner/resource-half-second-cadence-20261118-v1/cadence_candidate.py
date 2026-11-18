"""Prospective configuration only: faster real serial probes, SAME oldest<=2s.

Not a worker/controller/AUTH; never apply this to a closed or live scope. Does
not refresh a stamp, call a probe, run physics or promise bounded OS latency.
"""
def candidate(*,enabled=False):
    if enabled is not True:return None
    return dict(resource_probe_schedule='ACTUAL_START_NOMINAL_HALF_S',
        resource_poll_s=.5,resource_oldest_max_age_s=2.,
        successful_atomic_pair_origin='ACTUAL_REAL_PROBE_START_AND_COMPLETION',
        serial_no_queued_catchup=True,original_owner_composite_calls_per_probe=1,
        completion_only_fake_now_pause_age_or_staleness_relaxation=False,
        repeated_long_probe_can_still_correctly_censor=True,
        execution_permission=False,new_complete_program_prepare_own_zero_required=True)
