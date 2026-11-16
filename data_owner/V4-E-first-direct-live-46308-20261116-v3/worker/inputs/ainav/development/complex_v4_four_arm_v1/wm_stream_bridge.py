"""Default-off current V4 recorder -> Reach causal WM port; no WM/Actor call.

Decorate the fresh driver's actual writer, NOT the observer or original native
methods. Raw recording happens FIRST. Only its original10Hz append_visual and
accepted200Hz append_command enter the port; off-grid planner acquisitions and
private catalogs never do. This does not solve/bootstrap a modelled owner or a
same96x64 semantic association, and confers no method/native admission.
"""
from pathlib import Path
import hashlib,importlib,math
from method_entry import _reach_modules,REACH_PACKAGE
from v4_native_asset import require

PORT_PINS={
 'v4_causal_wm_query.py':'d79f6b00d9b927649abdf0cdf8f5b9357681baf3817838da434e4d00871c8e96',
 'v4_raw_wm_adapter.py':'f89e2cbbdbe53e81fa451c4b85686294c3ad7bb0b00e04728983557052d6674e',
}
EXECUTOR_SHA='8d42281aa890bd5224f7d8c0bacc2c44d1fa1bda0ba5a89fec8bffa59f701995'
PACKET_KEYS={'rgb','depth_m','camera_K','T_base_optical','proprio',
             'actions_previous','action_valid','timestamps_s'}


def _checked_sources(source_root,reach_source_root):
    root,adapters=_reach_modules(reach_source_root);base=root/REACH_PACKAGE.replace('.','/')
    modules={}
    for short,pin in PORT_PINS.items():
        p=base/short
        require(not p.is_symlink()and hashlib.sha256(p.read_bytes()).hexdigest()==pin,
                'Exact Reach causal-input source: '+short)
        module=importlib.import_module(REACH_PACKAGE+'.'+short[:-3])
        require(Path(module.__file__).resolve()==p,'No ambient Reach causal-input module')
        modules[short[:-3]]=module
    original=Path(source_root).resolve(strict=True);p=original/'ainav/native/executor.py'
    require(not p.is_symlink()and hashlib.sha256(p.read_bytes()).hexdigest()==EXECUTOR_SHA,
            'Exact original accepted-command/native owner ABI')
    executor=importlib.import_module('ainav.native.executor')
    require(Path(executor.__file__).resolve()==p,'No ambient native owner ABI')
    return adapters,modules['v4_causal_wm_query'],modules['v4_raw_wm_adapter'],executor


class CurrentWMStreamWriter:
    """Own fresh wrapper; all unrelated writer operations remain original."""
    def __init__(self,host,raw,port,native_api,*,software_fixture):
        self._host,self._raw,self._port,self._native_api=host,raw,port,native_api
        self.software_fixture=software_fixture
        self._owners=[];self._last_tick=0;self._last_visual_tick=None;self._failed=False
        self._commands=self._unmodelled=self._frames=0

    def __getattr__(self,name):return getattr(self._raw,name)

    def _token(self,owner,kind):
        for existing,previous,token in self._owners:
            if existing is owner:
                require(previous==kind,'An actual owner cannot be relabelled as another model skill')
                return token
        token='v4-actually-issued-owner-%06d'%len(self._owners)
        self._owners.append((owner,kind,token))  # Retain identity; no id reuse, target or private pose exposed.
        return token

    def _owner(self):
        h=self._host;ex=h.executor
        if h.loop is None:
            require(ex is None,'No native session can hide behind cold capture')
            return h.capture,'SupportedCapture',None
        require(type(ex)is self._native_api.NativeOptionExecutor and ex.runtime is h.r
                and ex.factory is h.factory and not ex.fatal and not ex.reported_end,
                'Actual installed original executor, not selected/prospective semantic intent')
        session=ex.session
        require(isinstance(session,self._native_api.NativeOptionSession)and session.runtime is h.r
                and session.entered and any(s is session for s in ex.sessions),
                'Actual retained/entered native motor session required')
        if session.exit is not None:
            # Do not infer EXIT_PUSH/RECOVER from a label without its own reviewed ABI.
            return session.exit,'NativeProtectedExitUnmodelled',None
        require(session.failure is None,'Failed owner cannot issue a modelled motor reference')
        skill=ex.option.skill;tasks=session.machine.tasks
        require(skill in ('NAV','PUSH','CLIMB')and len(tasks)==1
                and tasks[0].get('skill')==skill.lower(),
                'Installed native single-task owner must match its ACTUALLY issued option')
        return session,'NativeSession:'+skill,skill

    def append_command(self,**kwargs):
        try:
            result=self._raw.append_command(**kwargs)  # Preserve original raw evidence before WM validation/callback.
            require(not self._failed,'Failed WM stream bridge cannot resume')
            h=self._host;tick=kwargs['physical_tick'];now=kwargs['time_s'];issued=kwargs['issued']
            require(type(tick)is int and tick==self._last_tick+1 and h.r.step_count==tick
                    and type(now)in(int,float)and math.isfinite(now)
                    and abs(now-tick*.005)<1e-7 and abs(now-float(h.r.sim.data.time))<1e-7,
                    'Consecutive actually advanced200Hz command/current world clock, not proposed action')
            accepted=h.r.last.array()
            require(tuple(issued.shape)==(5,18)and tuple(accepted.shape)==(5,18)
                    and str(issued.dtype)==str(accepted.dtype)and issued.tobytes()==accepted.tobytes()
                    and all(math.isfinite(float(v))for v in issued[0]),
                    'Exact accepted global5x18 command; no delayed/local/action11 or padded motor reference')
            owner,kind,skill=self._owner();token=self._token(owner,kind)
            if skill is None:
                self._port.on_unmodelled_issued(tick,now,native_owner_id=token,owner_kind=kind)
                self._unmodelled+=1
            else:
                self._port.on_issued(issued[0].copy(),tick,now,actual_issued_skill=skill,native_owner_id=token)
            self._last_tick=tick;self._commands+=1
            return result
        except BaseException:
            self._failed=True
            raise  # Original loop still executes its after_step/safety handling and owner teardown.

    def append_visual(self,packet,*,control_tick,private_catalog):
        try:
            result=self._raw.append_visual(packet,control_tick=control_tick,private_catalog=private_catalog)
            require(not self._failed,'Failed WM stream bridge cannot resume')
            h=self._host;tick=control_tick*4
            require(type(control_tick)is int and control_tick>=0 and tick%20==0
                    and tick==h.r.step_count==self._last_tick
                    and (self._last_visual_tick is None and tick==0 or
                         self._last_visual_tick is not None and tick==self._last_visual_tick+20)
                    and abs(float(h.r.sim.data.time)-tick*.005)<1e-7,
                    'Only original consecutive10Hz recorded grid; never off-grid public-query frames')
            require(type(packet)is dict and set(packet)==PACKET_KEYS
                    and tuple(packet['timestamps_s'].shape)==(1,1)
                    and abs(float(packet['timestamps_s'][0,0])-tick*.005)<1e-7,
                    'Exact public sensor packet clock, never a private catalog or stale/backfilled frame')
            self._port.on_visual(packet)  # Original Reach resize_packet owns96x64/calibration conversion.
            self._last_visual_tick=tick;self._frames+=1
            return result
        except BaseException:
            self._failed=True
            raise

    def report(self):
        return dict(role='CURRENT_RECORDED_GRID_AND_ACCEPTED_REFERENCES_NOT_WM_OR_NATIVE_QUALIFICATION',
            software_fixture=self.software_fixture,failed=self._failed,
            actual_command_callbacks=self._commands,unmodelled_owner_callbacks=self._unmodelled,
            actual_grid_frame_callbacks=self._frames,last_accepted_tick=self._last_tick,
            context_status=self._port.context_status(),private_catalog_forwarded=False,
            observer_capture_or_model_forward_or_physics_calls=0,
            bootstrap_and_same96x64_semantic_association_not_supplied=True)


def attach_current_wm_stream(*,enabled=False,driver=None,port=None,reach_source_root=None,software_fixture=False):
    require(type(enabled)is bool and type(software_fixture)is bool,'Explicit opt-in/fixture identity')
    if not enabled:return None
    h=driver
    require(h.arm in ('A','B')and not hasattr(h,'_v4_wm_stream_bridge'),
            'Only one fresh A/B method stream, never add WM to C/D/E')
    require(h.r.step_count==0 and float(h.r.sim.data.time)==0. and not h.r.sim.queue
            and h.loop is None and h.executor is None and getattr(h.writer,'steps',None)==0,
            'Fresh own-zero driver/writer only, not active/closed runtime or a midstream hook')
    require(h.owner_guard()is not False,'Actual Data owner guard refused WM stream assembly')
    adapters,causal,raw,native=_checked_sources(h.source_root,reach_source_root)
    p=h.planner
    require(type(p)is adapters.VLMWMIntentPlanner and p.enabled is (h.arm=='B')
            and p.software_fixture is software_fixture and type(port)is causal.CausalWMQueryPort
            and type(p.wm)is raw.OriginalBehaviorWMAdapter and p.wm.provider is port,
            'Exact method -> already-created original WM adapter -> SAME causal port identity')
    require(p.calls==0 and p.pending is None and p.last_time is None and p.wm.forward_batches==0
            and port.completed_queries==0 and port._last_callback_tick is None
            and not port.buffer.frames and not port.buffer.commands,
            'No old query/history/forward/counters are reset or adopted')
    from factor_scope import FactorJournal,factors
    require(type(h.journal)is FactorJournal and h.journal.policy==factors(h.arm)
            and h.journal is p.journal and h.journal is h._v4_factor_journal,
            'One exact same-arm original common factor journal, not another arm/output')
    if software_fixture:
        require(port.role=='EXPLICIT_SOFTWARE_FIXTURE_NOT_MODEL_TASK_INPUT','Fixture provenance must remain explicit')
    else:
        require(port.role=='CURRENT_ORIGINAL_SENSOR_AND_ISSUED_HISTORY'
                and port.buffer._reach_query_software_fixture is False
                and port.buffer.model is p.wm.model,
                'Already bound original model/buffer only; no restore or fixture/live relabel')
    wrapper=CurrentWMStreamWriter(h,h.writer,port,native,software_fixture=software_fixture)
    ref=h.journal(dict(event='V4_current_WM_stream_attached_NOT_bootstrap_or_method_qualified',arm=h.arm,
        software_fixture=software_fixture,port_source_sha256=PORT_PINS,
        raw_writer_before_callbacks=True,supported_capture_not_labelled_HOLD_NAV_RECOVER=True,
        same96x64_semantic_association_not_supplied=True,model_input=False,
        actual_WM_forward_or_Actor_or_physics_calls=0,task_success_claimed=False))
    require(type(ref)is str and bool(ref),'Durable stream source evidence')
    require(h.owner_guard()is not False,'Actual Data owner guard refused WM stream attachment')
    h.writer=wrapper;h._v4_wm_stream_bridge=wrapper
    return wrapper
