"""One bounded call to the EXISTING host.observe_public at a retired boundary.

Development only; no world/step/HOLD/NAV/goal switch or predictor. Compose this
BEFORE execution of a future qualified host, never into frozen Stage-B. Source
qualification, resource lease, original guard handling and storage accounting
remain the owner runner's job. A Reach request is not native permission.
"""
from copy import deepcopy
import time
import math

MARKER='_ainav_one_public_reobserver'


def need(ok,message):
    if not ok:raise ValueError(message)


def bind_public_reobserver(host, *, expected_host_type=None, enabled=False):
    """Default off touches nothing. Enabled returns a one-call development seam.

    expected_host_type must be the class from the existing verified consumer;
    matching its Python identity alone does NOT perform source qualification.
    """
    need(type(enabled) is bool,'Explicit Boolean opt-in')
    if not enabled:return None
    need(type(host) is expected_host_type,'Exact already qualified Host class')
    need(not hasattr(host,MARKER),'One budget per host; never reinstall/reset')
    root=host.r;sim=root.sim;executor=host.executor;factory=host.factory;coordinator=host.coordinator
    need(host.tick==root.step_count==0 and float(sim.data.time)==0. and not sim.queue
         and executor.option is None and executor.session is None and coordinator.intent is None,
         'Install only on fresh host before prefix; no hot installation')
    need(executor.runtime is root and factory.runtime is root and executor.factory is factory
         and executor.fatal is False and not executor.pending,'Coherent original root/executor/factory, no pending receipts')
    method=host.observe_public
    need(getattr(method,'__func__',None) is expected_host_type.observe_public,'Original bound observation method, no injected callback')
    need(host.observer.r is root and host.resolver.runtime is root,'Original observer/resolver same root Runtime')
    binding=_PublicReobserver(host,method)
    setattr(host,MARKER,binding)
    return binding


class _PublicReobserver:
    def __init__(self,host,method):
        self.host=host;self.method=method;self.root=host.r;self.sim=host.r.sim
        self.model=self.sim.model;self.data=self.sim.data;self.queue=self.sim.queue
        self.factory=host.factory;self.executor=host.executor;self.coordinator=host.coordinator
        self.observer=host.observer;self.publisher=host.publisher;self.resolver=host.resolver
        self._used=0;self._broken=False;self._accounting=None

    @property
    def used(self):return self._used

    @property
    def broken(self):return self._broken

    @property
    def accounting(self):return deepcopy(self._accounting)

    def _identity(self):
        h=self.host
        return (h.r is self.root and h.r.sim is self.sim and self.sim.model is self.model
                and self.sim.data is self.data and self.sim.queue is self.queue
                and h.factory is self.factory and h.executor is self.executor
                and h.coordinator is self.coordinator and h.observer is self.observer
                and h.publisher is self.publisher and h.resolver is self.resolver
                and self.observer.r is self.root and self.resolver.runtime is self.root
                and getattr(h.observe_public,'__func__',None) is self.method.__func__
                and getattr(h,MARKER,None) is self)

    def _owner_key(self):
        e=self.executor;c=self.coordinator
        # Session/intent are recorded as identity, never polled for native NN or
        # outcome properties. Previous PUSH may own a distinct TargetBridge.
        loop=self.host.loop;authority=loop.authority
        return (id(loop),id(authority),loop.stopped,loop.physical_tick,id(authority.active),authority.blocked,authority.protection_latched,
                id(e.runtime),id(e.factory),id(e.option),id(e.session),e.reported_end,
                e.last_outcome,e.fatal,tuple(id(v) for v in e.pending),id(c.intent),getattr(c,'phase',None))

    def acquire_if_requested(self,request, *, previous_acquisition_time_s=None):
        """Return original Observation or None; budget spent before callback.

        A failed call also consumes the sole call. Never pad time or loop until
        a winner appears. Even a valid new render can have the SAME physics
        acquisition clock and provide no additional temporal information.
        """
        need(type(request) is dict and type(request.get('request_public_acquisition')) is bool,'Existing Reach information_action request')
        need(not self.broken,'Public acquisition owner is broken; original safety handling required')
        if not request['request_public_acquisition']:return None
        need(self.used==0,'Single public acquisition budget exhausted or broken')
        need(request.get('action')=='REQUEST_ONE_FRESH_EXISTING_PUBLIC_ACQUISITION'
             and request.get('execution_authorized') is False
             and request.get('native_action_or_observation_executed') is False
             and request.get('request_is_not_HOLD_or_NAV_or_retry_or_new_world') is True,
             'Observation request only, never model/native action authority')
        need(self._identity(),'Same installed original owner/world/FIFO/observer/publisher')
        e=self.executor;loop=self.host.loop
        need(loop is not None and self.host.prefix_proof is not None
             and loop.runtime is self.root and loop.executor is e and loop.stopped is False,
             'Original prefix already latched complete and same live loop; no polling native completion')
        need(loop.authority.active is None and loop.authority.blocked is False
             and loop.authority.protection_latched is False,
             'Original authority retired and unblocked, no pending native protection')
        need(e.runtime is self.root and e.factory is self.factory and self.factory.runtime is self.root
             and e.fatal is False and not e.pending,'Same nonfatal owner with receipts already consumed')
        need((e.option is None and e.session is None) or (e.reported_end is True and e.last_outcome in ('succeeded','protected_exit_complete')),
             'Retired successful owner only; no active/budget-expired/failed/protection bypass')
        need(e.session is None or e.session.runtime is self.root,'Previous session same root, proxy/view not collapsed')
        now=float(self.data.time)
        need(math.isfinite(now) and now>=0 and type(self.root.step_count) is int
             and self.root.step_count==self.host.tick==loop.physical_tick
             and abs(now-self.root.step_count*.005)<=1e-7,'Original same-root 200Hz tick/clock')
        if previous_acquisition_time_s is not None:
            need(type(previous_acquisition_time_s) in (int,float) and math.isfinite(previous_acquisition_time_s) and 0<=previous_acquisition_time_s<=now,
                 'Known causal original acquisition clock, no future stamp')
        # Original CourseBindingResolver consumes each physical query tick once.
        # Do NOT capture first and discover a same-tick replay after image IO.
        # No extra physics/HOLD/wait/reset may be used to manufacture freshness.
        need(type(self.resolver._last_physical_tick) is int
             and self.host.tick>self.resolver._last_physical_tick,
             'Original resolver requires strictly newer physical query tick; no same-tick replay')
        h=self.host;before=(h.api.world_snapshot(self.root),self.root.step_count,h.tick,self._owner_key())
        physical_before=self.observer.snapshot()
        frames_before=self.observer.frames;public_before=self.publisher.count
        self._used=1  # Includes exceptions; no retry or replacement observer.
        wall=time.perf_counter();cpu=time.process_time()
        try:
            observation=self.method(now)
            if (not self._identity() or (h.api.world_snapshot(self.root),self.root.step_count,h.tick,self._owner_key())!=before
                    or not self.observer.unchanged(physical_before,self.observer.snapshot())):
                raise RuntimeError('Public acquisition changed physical state/FIFO/clock/owner; DO NOT restore or continue')
            value=observation.value
            need(value['time_s']==now and value['rgb']['time_s']==now,
                 'Existing fresh capture at actual physics clock, never relabel cached data')
            need(self.resolver._last_physical_tick==h.tick,'Original resolver consumed exactly current physical query tick')
            need(self.observer.frames==frames_before+1 and self.publisher.count==public_before+1,
                 'Exactly one original capture/publication, not repeated polling')
            self._accounting=dict(actual_wall_s=time.perf_counter()-wall,actual_process_CPU_s=time.process_time()-cpu,
                actual_sim_elapsed_s=float(self.data.time)-now,actual_issued_steps=self.root.step_count-before[1],
                actual_observer_frames=self.observer.frames-frames_before,actual_publications=self.publisher.count-public_before,
                storage_bytes=None,storage_accounting='EXISTING_OWNER_RUNNER_REQUIRED_NOT_ASSUMED_ZERO',
                returned_acquisition_time_s=value['rgb']['time_s'],
                acquisition_clock_advanced=(None if previous_acquisition_time_s is None else now>previous_acquisition_time_s),
                call_completed=True,request_was_native_permission=False,native_READY_or_success_inferred=False)
            return observation
        except BaseException as error:
            self._broken=True
            self._accounting=dict(actual_wall_s=time.perf_counter()-wall,actual_process_CPU_s=time.process_time()-cpu,
                actual_sim_elapsed_s=float(self.data.time)-now,actual_issued_steps=self.root.step_count-before[1],
                actual_observer_frames=self.observer.frames-frames_before,actual_publications=self.publisher.count-public_before,
                storage_bytes=None,call_completed=False,error_type=type(error).__name__,
                retry_authorized=False,state_rollback_performed=False,owner_must_handle_original_guard_or_mutation_error=True)
            raise
