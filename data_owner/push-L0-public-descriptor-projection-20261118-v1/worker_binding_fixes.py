"""Prospective SOURCE TEXT fix only; no write/hot patch/worker/AUTH/dispatch.

Apply to a newly owned full-program source before new IDs/freeze, never to the
closed input file. The original lease, physics and native safety remain intact.
"""
OLD_HEALTH="""            if option is not None:
                state.fail('Boundary-only diagnostic forbids every native task option')"""
NEW_HEALTH="""            if option is not None:
                need(phase=='main' and c['full_original_task_execution'] is True
                     and c['boundary_only_no_task_skill'] is False and option.skill=='PUSH',
                     'Only the explicitly authorized full PUSH main may own a task option')"""
OLD_WATCH="        watch=ResourceWatch(probe,state=state,token=object(),fast_health=phase_health).start()"
NEW_WATCH="""        watch=ResourceWatch(probe,state=state,token=object(),fast_health=phase_health,
            interval_s=c['resource_poll_s'],max_stale_s=c['resource_oldest_max_age_s'])
        need(watch.interval==c['resource_poll_s'] and watch.max_stale==2.,
             'Actual ResourceWatch constructor binding, not a config label')
        result['resource_watch_actual_configuration']=dict(interval_s=watch.interval,
            max_oldest_age_s=watch.max_stale,read_from_actual_object_before_start=True)
        watch.start()"""

def patched_worker_source(source=None,*,enabled=False):
    if enabled is not True:return None
    if type(source)is not str or source.count(OLD_HEALTH)!=1 or source.count(OLD_WATCH)!=1:
        raise ValueError('Exact reviewed old full-worker sites required, no fuzzy/live patch')
    updated=source.replace(OLD_HEALTH,NEW_HEALTH,1).replace(OLD_WATCH,NEW_WATCH,1)
    compile(updated,'[PROSPECTIVE SOURCE ONLY NOT RUNNABLE QUALIFICATION]','exec')
    return updated
