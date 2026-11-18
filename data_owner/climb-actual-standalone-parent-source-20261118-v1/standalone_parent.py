"""Original standalone CLIMB parent SOURCE assembly, never a dispatch authority.

CPU prepare imports REAL SDK classes using the original Plugin isolation and
hashes the existing Actor; it does NOT construct a model/data/Actor/Stop/world.
The future native path additionally requires a complete new program's active
H/PID/AUTH/prepare receipt and its ORIGINAL own-process PerGpuLease. No lease is
acquired, borrowed, refreshed or released here. Registration safety/whole outer
runner, original watch/IO/finally are still the future complete parent's job.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import math
import os
import sys
import types

R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114')
SDK=Path('/mnt/yuanyue/ainav-execution-reference-20261112-v1/sdk-bundle')
OWNER='01a1e4e1-3037-7333-9019-a3f37effe5da'
PINS={'switch/plugins.py':'c9e87fbb774c1daa38f6329e95ded0ad5bdbad642283b79be7b707c9e30b5f2a',
 'climb/bridge.py':'055f5c791064b65fd9bc943365d3b6f41ae820a75ee2a928f78cc68b7686eed2',
 'climb/stop.py':'99bef7c9b22f55a8bff6d0c5975f8a887292497bcf01bff06416f800cb42ede7',
 'climb/play.py':'8fe257c698152785e07a4a0e61e77474cb76ba7382a6da028d008539fc46f0df',
 'climb/policy/contract.json':'1947b066cdc22e3583cc99dab7b0f20fa8378e6539e482daa35ff3821a6cbe35',
 'climb/policy/actor.pt':'8285bb4e40b7cddbac141786d10e9a7864057f63c0c77fce1ff2ab748ccddb8e'}
OWNER_SOURCE_SHA='1c0504aa26111c8a00eaa0defcf1270fb053f07efd8b46b1ec00dc7bb119bdd7'
INTERVAL_SOURCE_SHA='e9098862eae9f4e45b64b9c661cfe5eadaeffaddbac21cdd1f46c7a32db77c6a'
CASE=dict(seed=42001,randomization=False,height_m=.2,friction=.6,added_mass_kg=0.,delay_ms=20,
 finish_mode='stop',max_controls=1200,actor_logical_device='cuda:0',not_a_native_authorization=True)


def need(ok,message):
 if not ok:raise ValueError(message)
def checked(callback):
 answer=callback();need(answer is None or answer is True,'Original parent watch/authority refusal');return answer
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def pinned(p,digest):
 p=Path(p);need(not p.is_symlink()and sha(p)==digest,'Exact original/source bytes required: '+str(p));return p

def source_module(path,pin,name):
 path=pinned(path,pin);module=types.ModuleType(name);module.__file__=str(path)
 # The exact original Plugin imports need a genuine module entry for introspection.
 need(name not in sys.modules,'Fresh private source module; never replace an ambient alias')
 sys.modules[name]=module
 try:exec(compile(path.read_bytes(),str(path),'exec',dont_inherit=True),module.__dict__)
 except BaseException:
  sys.modules.pop(name,None);raise
 return module


class ClockedOriginalStep:
 """Actual external step-counter/issued-reader adapter, NOT resource/skill authority.

 A real factory binds the genuine SDK physics method. Pure software tests may
 bind a fake callback and are explicitly not native proof. Count real 5ms clock
 advance EVEN when the native callback raises afterwards; never edit sim.steps
 or elapsed (original status owns those control counters).
 """
 def __init__(self,sim,actual_physics,command_type,*,parent_check,active_context):
  need(all(callable(f)for f in(actual_physics,command_type,parent_check,active_context)),'Actual parent interfaces required')
  self.sim,self.actual_physics,self.Command,self.check,self.context=sim,actual_physics,command_type,parent_check,active_context
  self.world=(sim,sim.model,sim.data,sim.queue);self.tick=0;self.last=None;self.attempts=0;self.failed=False
  self.last_error_type=None;self.partial_clock=None
  need(float(sim.data.time)==0.,'Fresh real world only; no old task/zero resume')
 def issue(self,command):
  need(not self.failed,'Failed native step never retries/resumes')
  try:
   need(all(a is b for a,b in zip(self.world,(self.sim,self.sim.model,self.sim.data,self.sim.queue))),'Same actual standalone world/FIFO')
   need(self.context()is True,'Complete live native context still required')
   answer=self.check();need(answer is None or answer is True,'Original cached parent watch/authority refusal')
   need(abs(float(self.sim.model.opt.timestep)-.005)<1e-12,'Original 5ms model timestep before issue')
   before=float(self.sim.data.time);need(abs(before-self.tick*.005)<1e-7,'Independent parent tick/data.time')
   need(type(command)is self.Command,'Exact original CLIMB command class')
   array=command.array().copy();need(array.shape==(5,18),'Actual original command layout')
   captured=self.Command(*(row.copy()for row in array))
   self.attempts+=1;error=None
   try:self.actual_physics(command) # GENUINE original method; no rewritten PD/FIFO/mj_step.
   except BaseException as exc:error=exc
   try:after=float(self.sim.data.time)
   except BaseException:
    self.partial_clock=None
    if error is not None:raise error
    raise
   if not math.isfinite(after):
    self.partial_clock=None
    if error is not None:raise error
    raise ValueError('Actual physical clock unavailable after original issue')
   self.partial_clock=after
   if after>before:
    # Record this actual advance even if native code failed after integration.
    if abs(after-before-.005)<1e-7:self.tick+=1;self.last=captured
    elif error is None:raise ValueError('Original physical callback advanced other than one 5ms step')
   if error is not None:raise error
   need(abs(after-before-.005)<1e-7 and self.last is captured,'Exactly one original native physical issue; no fake ACK')
  except BaseException as error:
   self.failed=True;self.last_error_type=type(error).__name__;raise
 def snapshot(self):
  return dict(actual_clock_advances_observed=self.tick,actual_issue_attempts=self.attempts,failed=self.failed,
   observed_partial_clock_s=self.partial_clock,last_error_type=self.last_error_type,
   counter_is_not_original_control_steps=True,no_pose_velocity_FIFO_history_reset=True,
   not_a_resource_admission_or_registered_success=True)


def require_native_context(context,lease):
 """Cannot activate on today's closed scopes/source receipt. Reads only; no CAS/lease calls."""
 need(type(context)is dict and context.get('question')=='CLIMB_ORIGINAL_STANDARD_L0_FULL_STOP_FINITE',
      'Only a NEW exact CLIMB complete program, never PUSH/NAV or a source fixture')
 need(context.get('scope_id','').startswith('data-46308-CLIMB-original-L0-'),'Explicit new standalone CLIMB scope')
 H=R/'workspace/registry/handoff_current_status_20261115.json';h=json.loads(H.read_bytes());key=context['authority_key'];q=h[key]
 need(key.startswith('active_CLIMB_original_L0_')and h['executing_thread_id']==q['owner']==OWNER and q['active'], 'Actual active current maintenance/scope owner')
 need(not h['bulk24_collector_v1']['global_stop']and not q.get('stop_requested',False),'Original stop authority')
 need(all(not v.get('active',False)for k,v in h.items()if k.startswith('active_')and k!=key and isinstance(v,dict)),'No second active Data physical scope')
 phase=context['phase'];need(phase in('zero','main')and q.get(phase+'_PID')==os.getpid(),'Actual own native phase PID, not borrowed authority')
 need(q['scope_id']==context['scope_id']and q['question']==context['question'],'Exact new question/scope')
 freeze=Path(context['freeze_path']);pin=context['program_sha256'];need(sha(freeze)==pin==q['whole_program_freeze_sha256'],'Exact complete program freeze')
 f=json.loads(freeze.read_bytes());need(f['files'].get(str(Path(__file__)))==sha(__file__),'This actual adapter is fully frozen')
 auth=Path(context['authorization']);need(sha(auth)==q['authorization_sha256']and f['files'].get(str(auth))==sha(auth),'Actual frozen authorization')
 a=json.loads(auth.read_bytes());need(a['owner']==OWNER and a['scope_id']==q['scope_id']and a['question']==q['question'],'No old AUTH/zero reuse')
 prepared=json.loads(Path(context['complete_prepare_receipt']).read_bytes())
 need(prepared['stage']=='CLIMB_ORIGINAL_L0_COMPLETE_PROGRAM_ACTUAL_CPU_PREPARE_PASS'and prepared['program_sha256']==pin and prepared['CUDA_initialized']is False,
      'A source-only receipt NEVER qualifies a complete native parent')
 need(q['zero_dispatch_count']==1 and((phase=='zero'and q['main_dispatch_count']==0)or(phase=='main'and q['main_dispatch_count']==1 and q['zero_passed']and q['camera_sha256'])), 'Independent own-zero/camera before one main')
 module=sys.modules.get('per_gpu_lease');need(module is not None and type(lease)is module.PerGpuLease and sha(module.__file__)=='d44b3176255d177d432a4243da2b4a9a472881222fc1079224c82a9140dd9857','Original actual PerGpuLease object')
 need(f['files'].get(str(Path(module.__file__)))=='d44b3176255d177d432a4243da2b4a9a472881222fc1079224c82a9140dd9857','Actual original lease source is in this complete freeze')
 need(a['physical_GPU']==lease.index and a['GPU_UUID']==lease.profile['UUID'],'Only this exact authorization physical GPU/UUID, no idle-card switch')
 need(all(f['files'].get(str(SDK/name))==digest for name,digest in PINS.items()),'Actual source/contract/Actor inputs in complete freeze')
 need(lease.pid==os.getpid()and len(lease.fds)==len(lease.rows)==2,'Own-process completed canonical acquisition, no FD borrowing')
 for fd,row in zip(lease.fds,lease.rows):
  st=os.fstat(fd);need(row['holder_PID']==os.getpid()and(st.st_dev,st.st_ino)==(row['device'],row['inode']),'Actual retained own canonical FDs')
 need(os.environ.get('CUDA_VISIBLE_DEVICES')==lease.profile['UUID']and os.environ.get('MUJOCO_GL')=='egl'and os.environ.get('MUJOCO_EGL_DEVICE_ID')==str(lease.index),'Exact existing UUID/EGL mapping')
 return True


class OriginalStandaloneAssembly:
 def __init__(self,sdk,plugin,bridge,stop,torch,np,contract,owner_module,interval_path,receipt):
  self.sdk,self.plugin,self.bridge,self.stop_module,self.torch,self.np=sdk,plugin,bridge,stop,torch,np
  self.contract,self.cfg,self.owner_module,self.interval_path=contract,contract['configuration']['task'],owner_module,interval_path
  self.receipt=receipt;self.model=self.sim=self.actor=self.stop=None;self.construct_started=False;self.construct_completed=False;self.case_failed=False
  self.flags=dict(model_compile_started=False,model_compile_completed=False,bridge_init_started=False,bridge_init_completed=False,actor_load_started=False,actor_load_completed=False,stop_init_started=False,stop_init_completed=False)
 def expected_original_rng(self):
  cfg=self.cfg;np=self.np;rng=np.random.default_rng(42001)
  groups=rng.integers(0,cfg['actuator_delay_max']+1,7)
  xyz=[rng.uniform(*cfg['reset_x_range']),rng.uniform(*cfg['reset_y_range']),.33]
  yaw=rng.uniform(*cfg['reset_yaw_range']);reference=self.bridge.REFERENCE.copy();reference[12:]=cfg['arm_pose']
  joints=reference.copy();joints[:12]+=rng.uniform(-.03,.03,12)
  return dict(group_delays=groups,delays=np.r_[np.repeat(groups[0],12),groups[1:]],xyz=np.asarray(xyz),
   quaternion=np.asarray([np.cos(yaw/2),0.,0.,np.sin(yaw/2)]),joints=joints,rng_state=rng.bit_generator.state)
 def construct(self,*,context=None,lease=None,parent_check=None,enabled=False):
  need(type(enabled)is bool,'Explicit future native path')
  if not enabled:return None
  # NO native constructor before ALL complete-context/own-lease checks.
  require_native_context(context,lease);need(callable(parent_check),'Actual original cached parent watch')
  need(not self.construct_started and not self.case_failed,'Never reconstruct a partial/failed/closed world')
  self.construct_started=True
  try:
   expected=self.expected_original_rng();pinned(self.sdk/'climb/policy/actor.pt',PINS['climb/policy/actor.pt'])
   checked(parent_check);self.torch.set_num_threads(2);self.torch.backends.cuda.matmul.allow_tf32=False;self.torch.backends.cudnn.allow_tf32=False
   with self.plugin.active():
    self.flags['model_compile_started']=True
    self.model,self.spec=self.bridge.build_model(self.cfg,.2,friction=.6,added_mass=0.)
    self.flags['model_compile_completed']=True;checked(parent_check)
    self.sim=self.bridge.ClimbBridge.__new__(self.bridge.ClimbBridge);self.flags['bridge_init_started']=True
    self.bridge.ClimbBridge.__init__(self.sim,self.model,self.cfg,.2,42001,False)
    self.flags['bridge_init_completed']=True;np=self.np
    need(np.array_equal(self.sim.delays,expected['delays'])and np.array_equal(self.sim.data.qpos[:3],expected['xyz'])and
         np.array_equal(self.sim.data.qpos[3:7],expected['quaternion'])and np.array_equal(self.sim.data.qpos[self.sim.qids],expected['joints'])and
         self.sim.rng.bit_generator.state==expected['rng_state'],'Actual original seeded constructor/RNG draws; never patch pose to match')
    # Exactly original play's prospective override AFTER all original draws.
    self.sim.delays[:]=round(20/1000/self.cfg['physics_dt'])
    need(self.sim.rng.bit_generator.state==expected['rng_state'],'Delay override cannot skip/consume original RNG')
    checked(parent_check);self.flags['actor_load_started']=True
    self.actor=self.torch.jit.load(str(self.sdk/'climb/policy/actor.pt'),map_location='cuda:0').eval()
    self.flags['actor_load_completed']=True;checked(parent_check)
    self.stop=self.stop_module.StopController.__new__(self.stop_module.StopController);self.flags['stop_init_started']=True
    self.stop_module.StopController.__init__(self.stop,self.sim);self.flags['stop_init_completed']=True
   checked(parent_check);require_native_context(context,lease)
   self.construct_completed=True
   return OriginalLiveParent(self,context,lease,parent_check)
  except BaseException:self.case_failed=True;raise
 def partial_snapshot(self):
  clock=None
  try:clock=float(self.sim.data.time)
  except BaseException:pass
  return dict(construct_started=self.construct_started,construct_completed=self.construct_completed,failed=self.case_failed,
   stages=dict(self.flags),actual_clock_if_available=clock,missing_clock_is_not_zero=True,
   original_partial_objects_retained_for_future_parent_finally=True,not_a_resource_or_registered_qualification=True)


class OriginalLiveParent:
 def __init__(self,assembly,context,lease,parent_check):
  self.a=assembly;self.context,self.lease,self.check=context,lease,parent_check;self.failed=False
  need(type(assembly.sim)is assembly.bridge.ClimbBridge and type(assembly.stop)is assembly.stop_module.StopController,'Genuine actual SDK class identity, not fixture substitutes')
  self.counter=ClockedOriginalStep(assembly.sim,assembly.sim.physics_step,assembly.bridge.MotorCommand,
   parent_check=parent_check,active_context=lambda:require_native_context(context,lease))
  with assembly.plugin.active():
   self.owner=assembly.owner_module.prepare(assembly.sim,assembly.actor,types.SimpleNamespace(device='cuda:0'),assembly.cfg,assembly.stop,
    counter_reader=lambda:self.counter.tick,issued_reader=lambda:self.counter.last,parent_check=parent_check,
    interval_source_path=assembly.interval_path,play_path=assembly.sdk/'climb/play.py',bridge_path=assembly.sdk/'climb/bridge.py',
    contract_path=assembly.sdk/'climb/policy/contract.json',torch_backend=assembly.torch,max_controls=1200,enabled=True)
 def step_one(self):
  need(not self.failed,'No live-parent restart after source/native failure')
  error=None
  try:
   checked(self.check)
   with self.a.plugin.active():
    command=self.owner.next_command()
    if command is None:return False
    try:self.counter.issue(command)
    except BaseException as exc:error=exc
    self.owner.after_actual_issue(native_error=error) # Immediate drain; original object re-raised on error.
   checked(self.check);return True
  except BaseException:self.failed=True;raise
 def snapshot(self):
  return dict(native_construction=self.a.partial_snapshot(),physical_issue=self.counter.snapshot(),source_owner=self.owner.snapshot(),
   registered_12N_safety_full_Stop_receipt_live_IO_outer_finally_complete=False,not_a_complete_runner_or_native_permission=True)


def prepare(sdk=None,*,owner_source=None,interval_source=None,enabled=False):
 need(type(enabled)is bool,'Explicit source CPU assembly')
 if not enabled:return None
 sdk=Path(sdk).resolve(strict=True);need(sdk==SDK and sys.dont_write_bytecode,'Exact current SDK, never writes __pycache__ into original source')
 need(sys.prefix=='/mnt/yuanyue/data-team/env-native-v1'and sys.version_info[:3]==(3,11,16),'Existing private interpreter, no environment installation')
 sums=(sdk/'SHA256SUMS').read_bytes();entries={line.split(maxsplit=1)[1].lstrip('*').removeprefix('./'):line.split(maxsplit=1)[0]for line in sums.decode().splitlines()if line.strip()}
 for name,pin in PINS.items():pinned(sdk/name,pin);need(entries[name]==pin,'Original SDK checksum entry')
 owner_path=pinned(owner_source,OWNER_SOURCE_SHA);interval_path=pinned(interval_source,INTERVAL_SOURCE_SHA)
 import numpy as np
 import torch
 import mujoco
 need(not torch.cuda.is_initialized(),'Source prepare never starts CUDA')
 plugins=source_module(sdk/'switch/plugins.py',PINS['switch/plugins.py'],'_data_original_climb_plugins_parent_source')
 need(plugins.ROOT.resolve()==sdk,'Original Plugin ROOT, no changed module/asset routing')
 before_bridge=sys.modules.get('bridge');before_stop=sys.modules.get('stop')
 plugin=plugins.Plugin('climb',['bridge','stop']);bridge,stop=plugin['bridge'],plugin['stop']
 need(sys.modules.get('bridge')is before_bridge and sys.modules.get('stop')is before_stop,'Original Plugin isolation restored ambient module table')
 need(Path(bridge.__file__).resolve()==sdk/'climb/bridge.py'and Path(stop.__file__).resolve()==sdk/'climb/stop.py','Actual original module classes, no mocked real prepare')
 with plugin.active():contract=bridge.load_contract() # Original static contract/Actor SHA check; NOT Actor load.
 need(contract['version']=='V1'and contract['iteration']==900 and contract['actor_sha256']==PINS['climb/policy/actor.pt'],'Original 923D/18D export contract')
 owner_module=source_module(owner_path,OWNER_SOURCE_SHA,'_data_climb_original_ACK_owner_parent_source')
 need(owner_module.prepare(enabled=False)is None and not torch.cuda.is_initialized(),'Source closure remains default OFF/CPU only')
 receipt=dict(stage='CLIMB_REAL_SDK_PARENT_SOURCE_ASSEMBLY_CPU_IMPORT_ONLY_NOT_COMPLETE_PROGRAM_PREPARE',
  original_selected_files_SHA256=dict(PINS),SDK_SHA256SUMS_SHA256=hashlib.sha256(sums).hexdigest(),
  genuine_Plugin_bridge_Stop_class_imports=True,original_Plugin_restores_ambient_module_table=True,
  Actor_SHA_verified_only_not_jit_loaded=True,CUDA_initialized=False,native_construct_called=False,
  complete_program_freeze_AUTH_H_scope_own_zero_main=False,
  real_registered_safety_IO_budget_watch_finally_and_outer_full_Stop_still_missing=True)
 return OriginalStandaloneAssembly(sdk,plugin,bridge,stop,torch,np,contract,owner_module,interval_path,receipt)
