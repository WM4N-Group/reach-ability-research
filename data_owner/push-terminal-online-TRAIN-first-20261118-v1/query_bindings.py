"""Shared live/prepare call bindings; no lease, thread or world starts here."""
def construct_watch(watch_class,probe,state,health,config):
    watch=watch_class(probe,state=state,token=object(),fast_health=health,
        interval_s=config['resource_poll_s'],max_stale_s=config['resource_oldest_max_age_s'])
    if not (watch.interval==config['resource_poll_s']==.5 and
            watch.max_stale==config['resource_oldest_max_age_s']==2.):
        raise ValueError('Watch constructor did not receive the required .5s/2s configuration')
    return watch,dict(interval_s=watch.interval,max_oldest_age_s=watch.max_stale,
                      read_from_actual_object_before_start=True)

def check_phase_health(health,state,config,phase,option):
    health()
    if option is not None and not (phase=='main' and config['full_original_task_execution'] is True
            and config['boundary_only_no_task_skill'] is False and option.skill=='PUSH'):
        state.fail('Only explicitly authorized full PUSH main may own an option')
    return True
