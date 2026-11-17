"""SOURCE-ONLY original CLIMB command/ACK protocol, default OFF.

No physics, Model, Actor load, lease, H, registration or dispatch here. A future
frozen parent must authenticate original constructor/RNG/model/Actor/Stop and
supply real independent physical-counter/issued-command readers, genuine
owner/resource checks, registration safety, whole Stop/finally and output.
"""
from pathlib import Path
import hashlib
import json
import math
import types

INTERVAL_SHA256='e9098862eae9f4e45b64b9c661cfe5eadaeffaddbac21cdd1f46c7a32db77c6a'
BRIDGE_SHA256='055f5c791064b65fd9bc943365d3b6f41ae820a75ee2a928f78cc68b7686eed2'
CONTRACT_SHA256='1947b066cdc22e3583cc99dab7b0f20fa8378e6539e482daa35ff3821a6cbe35'


def need(ok,message):
    if not ok:raise ValueError(message)


def _pinned(path,pin):
    path=Path(path);raw=path.read_bytes()
    need(not path.is_symlink()and hashlib.sha256(raw).hexdigest()==pin,'Exact regular original/source bytes required')
    return raw


def _cfg_sha(cfg):
    return hashlib.sha256(json.dumps(cfg,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


class _SourceStepOwner:
    def __init__(self,sim,actor,args,cfg,stop,*,counter_reader,issued_reader,parent_check,
                 interval,np,max_controls,source_proof):
        need(callable(actor)and callable(counter_reader)and callable(issued_reader)and callable(parent_check),
             'Future actual parent supplies real independent clock/command readers and original cached watch/authority check')
        need(stop is not None and all(callable(getattr(stop,n,None))for n in ('command','after_step','status')),
             'This owner candidate supports original FULL STOP only; not ascent/default None')
        need(type(max_controls)is int and 0<max_controls<=round(cfg['episode_seconds']/(cfg['physics_dt']*cfg['decimation'])),
             'Explicit finite source interval cap, not native authorization')
        need(cfg['physics_dt']==.005 and type(cfg['decimation'])is int and cfg['decimation']==4,
             'Original 200Hz physics/50Hz control profile')
        need(sim.cfg is cfg and type(sim.steps)is int and sim.steps==0 and float(sim.elapsed)==0. and
             float(sim.data.time)==0. and counter_reader()==0 and not sim.queue and sim.history is None,
             'Fresh task only; no predecessor/old zero/reset or borrowed history')
        need(abs(float(sim.model.opt.timestep)-.005)<1e-12 and 0.<=float(sim.height)<=.2,
             'Original standalone dt and declared deployment height domain')
        self.sim,self.actor,self.args,self.cfg,self.stop=sim,actor,args,cfg,stop
        self.counter_reader,self.issued_reader,self.parent_check=counter_reader,issued_reader,parent_check
        self.interval,self.np,self.max_controls=interval,np,max_controls
        self.interfaces=(actor,args,stop,counter_reader,issued_reader,parent_check,interval,np)
        self.fixed_limit=max_controls
        self.world=(sim,sim.model,sim.data,sim.queue,cfg)
        self.cfg_sha=_cfg_sha(cfg);self.device=getattr(args,'device');self.height=float(sim.height)
        self.failed=False;self.pending=False;self.done=False;self.censored=False
        self.issued=0;self.controls=0;self.actor_attempts=0;self.actor_returned=0
        self.commands_produced=0;self.initial_observations=0
        self.gen=None;self.buffer=None;self.buffer_seal=None;self.pending_seal=None;self.before=None
        self.control_yields=0;self.source_state='running';self.source_reason=''
        self.error_type=None;self.source_proof=source_proof
        self.observed_after_error=None
        try:
            self._check()
            before=self._physical_fingerprint()
            self.obs=sim.observation() # EXACT original initial call; history may update, never reset.
            self.initial_observations=1
            need(self._physical_fingerprint()==before,'Initial observation cannot step/write physical state/FIFO')
            self._observation(self.obs);self._integrity()
        except BaseException as error:self._fail(error);raise

    def _clock(self):
        tick=self.counter_reader();stamp=float(self.sim.data.time)
        need(type(tick)is int and tick>=0 and math.isfinite(stamp)and stamp>=0.,'Actual independent physical tick/time')
        return tick,stamp

    def _integrity(self):
        p=self.sim
        need(not self.failed,'Failed source owner cannot resume')
        need(all(a is b for a,b in zip(self.world,(p,p.model,p.data,p.queue,p.cfg))), 'Same actual world/FIFO/cfg aliases')
        need(all(a is b for a,b in zip(self.interfaces,(self.actor,self.args,self.stop,self.counter_reader,self.issued_reader,self.parent_check,self.interval,self.np))) and
             self.max_controls==self.fixed_limit,'Same original interface/reader identities and finite limit')
        need(_cfg_sha(self.cfg)==self.cfg_sha and self.args.device==self.device and float(p.height)==self.height,
             'Immutable original configuration/device/target geometry; no reset/retune')
        # IMPORTANT: original ClimbBridge.steps/elapsed advance in STATUS once
        # per control interval, NEVER once per physical step.
        need(type(p.steps)is int and p.steps==self.controls and
             abs(float(p.elapsed)-self.controls*.02)<1e-7,'Original stateful control status was not externally polled')
        tick,stamp=self._clock()
        need(abs(stamp-tick*.005)<1e-7,'Actual physical clock/counter coupling')
        return tick,stamp

    def _check(self):
        self._integrity()
        before=self._physical_fingerprint()
        answer=self.parent_check() # Parent's genuine cached watch/authority, NOT new composite GPU probes/stamps.
        need(answer is None or answer is True,'Original parent guard refusal')
        need(self._physical_fingerprint()==before,'Parent guard must not step/write state or FIFO')
        return self._integrity()

    def _physical_fingerprint(self):
        p=self.sim
        return (self._clock(),p.data.qpos.tobytes(),p.data.qvel.tobytes(),
                tuple((a.shape,str(a.dtype),a.tobytes())for a in p.queue))

    def _seal(self,command):
        need(command is not None and callable(getattr(command,'array',None)), 'Original full-stop MotorCommand, never fabricated zero/None')
        a=command.array()
        need(a.shape==(5,18)and self.np.isfinite(a).all(),'Exact finite original issued command layout')
        return (a.shape,str(a.dtype),a.tobytes())

    def _observation(self,obs):
        need(obs.shape==(923,)and self.np.isfinite(obs).all(),'Original finite V1/900 observation')

    def _source_actor(self,inputs):
        self.actor_attempts+=1
        result=self.actor(inputs)
        self.actor_returned+=1
        return result

    def _resume_interval(self):
        before=self._physical_fingerprint();control_before=self.controls
        try:
            command=next(self.gen)
        except StopIteration as end:
            need(self.control_yields==4,'One exact original four-step control interval, no missing ACK')
            state,reason,obs=end.value
            need(type(state)is str and state in ('running','failed','success','timeout','incomplete') and
                 type(reason)is str and len(reason)<=4096,'Bounded original source terminal state/reason')
            need(self._physical_fingerprint()==before,'Draining control interval cannot add physics/write physical state/FIFO')
            need(type(self.sim.steps)is int and self.sim.steps==control_before+1 and
                 abs(float(self.sim.elapsed)-(control_before+1)*.02)<1e-7,
                 'Exactly one original status/elapsed update at the 20ms boundary')
            self.controls+=1;self.source_state,self.source_reason=state,reason
            self._observation(obs);self.obs=obs;self.gen=None;self.buffer=None;self.buffer_seal=None
            self.done=(state!='running' or self.controls>=self.max_controls)
            self.censored=(state=='running'and self.controls>=self.max_controls)
            self._integrity();return
        need(self._physical_fingerprint()==before,'Source/Actor/Stop cannot hide physical steps/state writes or clear FIFO')
        need(self.sim.steps==control_before and abs(float(self.sim.elapsed)-control_before*.02)<1e-7,
             'No source stateful status poll inside the four-step interval')
        self.control_yields+=1;need(self.control_yields<=4,'No fifth command in one original interval')
        self.buffer=command;self.buffer_seal=self._seal(command);self.commands_produced+=1
        self._integrity()

    def next_command(self):
        try:
            need(not self.pending,'Cannot skip/duplicate an unacknowledged request')
            tick,stamp=self._check()
            need(tick==self.issued,'Actual parent count cannot move without an ACK')
            if self.done:return None
            if self.gen is None:
                need(self.buffer is None,'No lost previous interval command')
                self.control_yields=0
                self.gen=self.interval(self.sim,self._source_actor,self.args,self.cfg,self.stop,self.obs)
                self._resume_interval() # Original Actor call at control0 even if ready/gain is zero.
            need(self.buffer is not None and self._seal(self.buffer)==self.buffer_seal,'Prepared original command drift')
            command=self.buffer;self.pending_seal=self.buffer_seal;self.before=(tick,stamp)
            self.buffer=None;self.buffer_seal=None;self.pending=True
            return command
        except BaseException as error:self._fail(error);raise

    def after_actual_issue(self,*,native_error=None):
        try:
            if native_error is not None:raise native_error # Preserve actual error object before any metadata/guard error.
            need(self.pending,'No invented or duplicate actual issue acknowledgement')
            tick,stamp=self._check()
            need(tick==self.before[0]+1 and abs(stamp-self.before[1]-.005)<1e-7,'Exactly one real external 5ms issue before ACK')
            actual=self.issued_reader()
            need(self._seal(actual)==self.pending_seal,'Actual parent issued command must match PRE-issue seal, not delayed FIFO output')
            self.issued+=1;self.pending=False;self.pending_seal=None
            self._resume_interval() # Process original after_step and, at step4, status/obs NOW; never start another Actor.
        except BaseException as error:self._fail(error);raise

    def _fail(self,error):
        self.failed=True;self.error_type=type(error).__name__
        try:
            tick=self.counter_reader();stamp=float(self.sim.data.time);elapsed=float(self.sim.elapsed)
            self.observed_after_error=dict(physical_tick=tick if type(tick)is int else None,
                time_s=stamp if math.isfinite(stamp) else None,
                source_control_steps=self.sim.steps if type(self.sim.steps)is int else None,
                source_elapsed_s=elapsed if math.isfinite(elapsed) else None)
        except BaseException:self.observed_after_error=None

    def snapshot(self):
        return dict(kind='CLIMB_ORIGINAL_EXTERNAL_STEP_ACK_SOURCE_OWNER_NOT_REGISTERED_AUTHORITY',
            verified_physical_ACKs=self.issued,completed_control_intervals=self.controls,
            source_actor_call_attempts=self.actor_attempts,source_actor_calls_returned=self.actor_returned,
            source_inference_calls_not_registered_admission_or_body_Actor_SR=True,
            source_commands_constructed_not_necessarily_issued=self.commands_produced,
            initial_original_observations=self.initial_observations,pending=self.pending,buffered=self.buffer is not None,
            failed=self.failed,error_type=self.error_type,observed_after_error=self.observed_after_error,
            source_state=self.source_state,source_reason=self.source_reason,source_terminal=(self.source_state!='running'),
            finite_censored_not_success=self.censored,source_interval_done=self.done,
            original_control_steps_not_physical_counter=True,source_profile=self.source_proof,
            partial_finally_actual_parent_cost_must_not_be_replaced_by_verified_ACK_count=True,
            no_added_reset_FIFO_history_clear_extra_status_or_settle=True,
            constructor_RNG_Model_Actor_Stop_authentication=False,registered_12N_safety_finally_full_Stop_receipt=False,
            physical_or_skill_qualification=False,execution_permission=False)


def prepare(sim=None,actor=None,args=None,cfg=None,stop=None,*,counter_reader=None,issued_reader=None,parent_check=None,
            interval_source_path=None,play_path=None,bridge_path=None,contract_path=None,torch_backend=None,max_controls=None,enabled=False):
    need(type(enabled)is bool,'Explicit source-only opt-in')
    if not enabled:return None
    interval_raw=_pinned(interval_source_path,INTERVAL_SHA256)
    _pinned(bridge_path,BRIDGE_SHA256);contract=json.loads(_pinned(contract_path,CONTRACT_SHA256))
    need(_cfg_sha(cfg)==_cfg_sha(contract['configuration']['task']),'Exact original V1/900 task configuration; no safety retune')
    module=types.ModuleType('_data_pinned_original_CLIMB_interval_source')
    exec(compile(interval_raw,str(interval_source_path),'exec',dont_inherit=True),module.__dict__)
    text,proof=module.derive(play_path,enabled=True)
    import numpy as np
    need(callable(getattr(torch_backend,'inference_mode',None))and callable(getattr(torch_backend,'from_numpy',None)),
         'Future parent supplies actual frozen Torch API; software fixtures are not native authenticity')
    namespace=dict(np=np,torch=torch_backend)
    exec(compile(text,str(play_path)+'[external-ACK-source-owner-interval]','exec',dont_inherit=True),namespace)
    return _SourceStepOwner(sim,actor,args,cfg,stop,counter_reader=counter_reader,issued_reader=issued_reader,
        parent_check=parent_check,interval=namespace['original_control_interval_requests'],np=np,max_controls=max_controls,source_proof=proof)
