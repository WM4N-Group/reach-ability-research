"""Opt-in adapter for a NEW fresh C/D driver with instance task hooks. Not a dispatcher.

All original native source/actuator checks and Runtime.step body remain. The
instance gets a pre-issue identity gate; metadata-only constructor boundaries
are explicit and cannot issue physical commands. Unexpected later lazy code
installation fails closed; qualify/warm its imports BEFORE sealing, not retry.
"""
from types import MethodType
from indexed_guard import make_indexed_guard,GuardViolation,need,POLICY_ID,OwnerStamp


def install(driver=None,*,enabled=False,files=None,owner_fast=None,owner_refresh=None,tokens=None,policy=None,boundary_only=False):
    need(type(enabled)is bool,'Explicit new-program owner opt-in')
    need(type(boundary_only)is bool,'Explicit no-task terminal-boundary profile')
    if not enabled:return None
    need(driver.r.step_count==0 and float(driver.r.sim.data.time)==0.,'Only a fresh task0 driver, never hot install')
    cls=type(driver);old=cls._native_guards;previous=old.engine
    need(getattr(previous,'state',None)is None and getattr(previous,'_pool',None)is None and
         not getattr(previous,'closed',True)and not getattr(previous,'failed',True),
         'Install before original metadata guard starts, not over a live worker')
    original=previous.original;runtime=driver.r;original_step=runtime.step
    # Preserve callback/step wrapper identities too. Values are references, not
    # id-only tokens; the unchanged native goal-value guards are NOT replaced.
    def actual_tokens(host):
        values=dict(tokens(host));values.update(audit_runtime_step=host.r.step,
            audit_native_guard=type(host)._native_guards,
            audit_constructor=host._connect_execution,
            audit_judgment=host.judge_intent)
        if host.executor is not None:
            values['audit_executor_start']=host.executor.start
            session=host.executor.session
            services=None if session is None else getattr(getattr(session,'machine',None),'services',None)
            if services is not None:values['audit_brake_constructor']=services.begin_brake
        return values
    guard=make_indexed_guard(original,enabled=True,files=files,owner_fast=owner_fast,
        owner_refresh=owner_refresh,tokens=actual_tokens,policy=policy)
    engine=guard.engine;previous.close()
    def gated_step(this,command):
        need(this is runtime,'Foreign runtime issue gate')
        engine.before_issue(driver)
        return original_step(command)  # Exact original physical body/guards.
    runtime.step=MethodType(gated_step,runtime)
    original_connect=driver._connect_execution;original_judge=driver.judge_intent
    def wrap_start(executor):
        source=executor.start
        def start(this,*args,**kwargs):
            need(this is executor,'Foreign executor admission boundary')
            with engine.boundary(driver,'original-executor-start-no-physics'):
                result=source(*args,**kwargs)
                session=this.session
                services=None if session is None else getattr(getattr(session,'machine',None),'services',None)
                if services is not None:
                    constructor=services.begin_brake
                    def begin_brake(service,*a,**kw):
                        need(service is services,'Foreign original brake metadata boundary')
                        with engine.boundary(driver,'original-brake-construction-no-physics'):
                            return constructor(*a,**kw)
                    services.begin_brake=MethodType(begin_brake,services)
                return result
        executor.start=MethodType(start,executor)
    def connect(this,*args,**kwargs):
        need(this is driver,'Foreign driver construction boundary')
        with engine.boundary(driver,'startup-to-arm-boundary-no-task' if boundary_only else 'capture-to-original-execution-no-physics'):
            result=original_connect(*args,**kwargs)
            if boundary_only:
                need(this.executor is None and this.loop is None and this.factory is None
                     and this.boundary_reached is True,
                     'Actual terminal no-task boundary, never a fake executor')
            else:
                wrap_start(this.executor)
            return result
    def judge(this,*args,**kwargs):
        need(this is driver,'Foreign driver intent boundary')
        need(not boundary_only,'Boundary-only diagnostic forbids every intent/query')
        with engine.boundary(driver,'original-intent-binding-no-physics'):
            return original_judge(*args,**kwargs)
    driver._connect_execution=MethodType(connect,driver);driver.judge_intent=MethodType(judge,driver);cls._native_guards=guard
    # No rollback to old guard on error: Data must discard a failed new root.
    cls.source_receipt=dict(cls.source_receipt,
        current_parallel8_full_path_reads_pre_post_no_cross_tick_cache=False,
        original_guard_bytecode_current_modules_callbacks_world_checks_retained=False,
        revised_static_identity_policy=POLICY_ID,static_audit_latency_intentionally_changed=True,
        native_Runtime_step_body_and_dynamic_safety_source_unchanged=True,
        owner_resource_checks_supplied_by_Data_not_disabled=True)
    receipt=engine.seal(driver,label='fully-loaded-task0-before-first-command')
    return dict(receipt,default_off=False,no_physics_Actor_or_model_called=True,
                strict_unplanned_import_exec_refusal=True,native_or_system_speedup_qualified=False)


def data_resource_watch_callbacks(watch,*,epoch):
    """Bridge Data ResourceWatch v1; never invent a new checked_at or probe.

    Its own background worker polls external resources. check(token) enforces
    PID, revocation, capacity/health and max staleness. Both callbacks here only
    ACK that real current result. Data owns starting/closing the watch/lease.
    """
    need(type(epoch)is str and epoch and callable(getattr(watch,'check',None))and
         0<watch.max_stale<=2.,'Data watch epoch and <=2s genuine external freshness required')
    token=watch.token
    def fast(host):
        answer=watch.check(token)
        need(answer is None or answer is True,'Data resource watch refused/returned an unknown result')
        pair=watch.last_observation_stamp  # ONE immutable atomic oldest/completed publication.
        need(type(pair)is tuple and len(pair)==2 and pair[0]<=pair[1],
             'Original successful oldest/completed pair required')
        checked=float(pair[0])  # Never completion/last_ok/fake now as OwnerStamp authority.
        return OwnerStamp(epoch,checked,checked+watch.max_stale,True)
    def acknowledge(host):
        answer=watch.check(token)  # Do NOT run a duplicate full external probe here.
        need(answer is None or answer is True,'Data resource watch refused/returned an unknown result')
    return fast,acknowledge
