"""Bounded actual watcher fixture, no lease, mapping reader, world or GPU."""
from threading import Event
from zero_retirement import zero_watch_class


def qualify():
    from resource_watch import ResourceWatch
    from scoped_io import StopState, PolicyStop
    watch_cls = zero_watch_class(ResourceWatch)
    for mode in ('match', 'mismatch', 'blocked'):
        state=StopState(); calls=[]; release=Event()
        def probe():
            calls.append(True)
            if len(calls)>1 and mode=='mismatch':state.fail('synthetic real probe mismatch')
            if len(calls)>1 and mode=='blocked' and not release.wait(2):state.fail('fixture deadline')
        # Short fixture clock windows intentionally exercised by the real
        # scheduler. Runtime constructs the separate audited .5s/2s object.
        w=watch_cls(probe,state=state,token=object(),interval_s=.05,max_stale_s=.5)
        w.start()
        try:
            if mode=='match':
                report=w.retire_for_zero()
                assert report['successful_original_probe_ack'] and report['original_last_pair'][0]>report['old_oldest_monotonic_s']
                with state.lock:state.sealed=True
                w.close()
                assert not w.thread.is_alive() and len(calls)==2 and state.reason is None
            else:
                try:w.retire_for_zero()
                except PolicyStop as e:
                    assert ('synthetic real probe mismatch' if mode=='mismatch' else 'missing actual successful probe') in str(e)
                    assert not w.retired_after_probe.is_set() and w.probe_calls==1
                else:raise AssertionError('False zero retirement ACK')
        finally:
            release.set()
            with state.lock:state.sealed=True
            w.close()
    return dict(successful_original_probe_ack_and_join=True,live_mismatch_latched=True,missing_ack_refused=True,CPU_fixture_only=True)
