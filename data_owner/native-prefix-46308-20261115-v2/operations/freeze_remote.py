"""Exact new-program freeze + maintenance/phase authority; NO phase dispatch."""
from pathlib import Path
import os,sys,json,hashlib,base64,fcntl,stat,tempfile,datetime,subprocess
R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114');B=R/'workspace';N='native-prefix-46308-20261115-v2';W=B/'workers'/N;M=B/'manifests'/N;E=M/'evaluation-inputs';H=B/'registry/handoff_current_status_20261115.json'
x=json.load(sys.stdin);sha=lambda b:hashlib.sha256(b).hexdigest();now=lambda:datetime.datetime.now().astimezone().isoformat()
def write_new(p,raw):
 p.parent.mkdir(parents=True,exist_ok=True)
 if p.exists():assert not p.is_symlink() and p.read_bytes()==raw,('EXISTING_DIFF',str(p))
 else:
  with p.open('xb')as f:f.write(raw);f.flush();os.fsync(f.fileno())
assert sha(H.read_bytes())==x['expected_H_sha256'] and json.loads(H.read_bytes())['executing_thread_id']==x['owner']
# Exact pre-CPU staged source/worker, not a different program or re-opened old root.
v=json.loads((M/'CPU_READY_RESOURCE_OBSERVATION.json').read_bytes())
for rel,pin in v['files_sha256'].items():assert sha((B/rel).read_bytes())==pin
for row in x['files']:
 rel=Path(row['path']);assert not rel.is_absolute() and '..'not in rel.parts and rel.is_relative_to(Path('manifests')/N)
 raw=base64.b64decode(row['bytes']);assert sha(raw)==row['sha256'];write_new(B/rel,raw)
def fence(event,args):
 if event=='import' and str(args[0]).split('.')[0]in('torch','mujoco','onnxruntime'):raise RuntimeError('No native/model construction in source freeze')
sys.addaudithook(fence);sys.path.insert(0,str(W));import prepare_prefix as p
plans={c:p.build_plan(c)for c in p.IDS};assert len({p.digest(v['runtime_config'])for v in plans.values()})==1
assert sha((E/'main-plan.md').read_bytes())=='53233939a5df85d33aa3f31cb4a01f140f28d28e1f31b2d161bc45cadd0dad40'
assert sha((W/'inputs/prefix-question/EXPERIMENT_CN.md').read_bytes())=='a3c7a1e6a443196334144b15d5172747f4c15578e4113c8a20917323e0ee8123'
for c in p.IDS:assert not(R/'runtime/workers'/p.SCOPES[c]).exists()
locks=[]
for kind,inode in [('physics', 3428459217), ('sdk', 3428459218)]:
 path=R/f'resource-locks/native-observer-{kind}-gpu1.lock';s=path.stat();assert(s.st_dev,s.st_ino)==(51,inode);fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
 try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(fd,fcntl.LOCK_UN)
 finally:os.close(fd)
 locks.append(dict(path=str(path),device=s.st_dev,inode=s.st_ino,available_at_observation=True,not_run_lease=True))
active=[]
for q in Path('/proc').iterdir():
 if not q.name.isdigit():continue
 try:args=[a.decode(errors='replace')for a in(q/'cmdline').read_bytes().split(b'\0')if a]
 except(FileNotFoundError,PermissionError,ProcessLookupError):continue
 if any(a.startswith((str(R/'runtime')+'/',str(B/'workers')+'/'))for a in args):active.append(int(q.name))
assert not active
owned=int(subprocess.check_output(['du','-sx','-B1',str(R)],text=True,timeout=90).split()[0]);assert owned+3*1024**3<40*1024**3
GPU=subprocess.check_output(['nvidia-smi','--id=GPU-6d66aa68-9a3f-fdcf-89b7-f98d4106fa39','--query-gpu=index,uuid,memory.free','--format=csv,noheader,nounits'],text=True,timeout=20).strip();g=[s.strip()for s in GPU.split(',')];assert g[0]=='1' and g[1]=='GPU-6d66aa68-9a3f-fdcf-89b7-f98d4106fa39' and int(g[2])>=4096
AUTH=B/'registry/NATIVE_PREFIX_46308_CORRECTED_EXPAT_V2_AUTHORITY_20261115.json';assert not AUTH.exists()
a=dict(schema='Data-two-native-prefix-qualification-one-shot-authority-v1',at=now(),owner=x['owner'],stage='TWO_NATIVE_PREFIX_CONDITION_QUALIFICATION',authorization_basis='Standing autonomous existing-skill simulation + current experiment-first main plan and fixed2 question. Not new economic approval or any old scope retry.',main_plan_sha256=sha((E/'main-plan.md').read_bytes()),standing_user_autonomous_record_sha256=sha((E/'USER_AUTONOMOUS_NO_COST_BUDGET_LIMIT_20261113_v1.json').read_bytes()),AINav_question_sha256=sha((W/'inputs/prefix-question/EXPERIMENT_CN.md').read_bytes()),Reach_preoutcome_analysis_sha256=sha((E/'REACH_PREOUTCOME_ANALYSIS_CN.md').read_bytes()),candidate_order=list(p.IDS),branches={c:dict(scope_id=p.SCOPES[c],allowed_own_zero_invocations=1,allowed_main_invocations=1)for c in p.IDS},GPU_UUID=g[1],technical_caps_per_branch=dict(sim_s=300.,wall_s=5400.,output_bytes=1610612736),own_GPU_cap_bytes=3*1024**3,own_RSS_cap_bytes=4*1024**3,CPU_threads=2,owned_cap_bytes=40*1024**3,all_two_new_roots_reserved_bytes=3*1024**3,provider_quota_known=False,seed=4301,source_owner_release_sha256=p.SOURCE_RELEASE,current_source_fork_sha256=p.SOURCE_FORK,initial_input_binding_sha256=v['probes'][p.IDS[0]]['initial_binding_sha256'],new_cohort_authorized_main_plan_sha256='53233939a5df85d33aa3f31cb4a01f140f28d28e1f31b2d161bc45cadd0dad40',old_46174_admin_UNKNOWN_stop_preserved=True,old_46174_attempt_not_resumed=True,corrected_library_protocol_sha256=sha((E/'CORRECTED_LIBRARY_VERSION_PROTOCOL.json').read_bytes()),v1_closed_zero_failure_costs_preserved=True,total_G1_new_host_main_limit_including_v1=2,all_old_scopes_remain_closed=True,automatic_retry=False,training_allowed=False,data_role='NEW_DEV_AUDIT_ONLY',qualified_entry_condition_family=False,critic_24_main_not_queued=True,WM_API_or_real_robot_allowed=False,physical_safe_success_gates_unchanged=True,optional_direct_live_video_not_native_success_gate=True,old_state_replay_backfill_forbidden=True,terminal_semantic_successes_required=3,first_condition='left',second_condition='right')
write_new(AUTH,(json.dumps(a,ensure_ascii=False,indent=2)+'\n').encode());auth_sha=sha(AUTH.read_bytes())
SDK=p.SDK_ROOT;files={}
for line in(SDK/'SHA256SUMS').read_text().splitlines():
 pin,rel=line.split(None,1);rel=rel.strip().removeprefix('*');path=SDK/rel;assert not Path(rel).is_absolute() and '..'not in Path(rel).parts and not path.is_symlink()and sha(path.read_bytes())==pin;files[str(path)]=pin
for name in('SHA256SUMS','MANIFEST.json'):files[str(SDK/name)]=sha((SDK/name).read_bytes())
assert len(files)>=148
for q in list(W.rglob('*'))+list(E.rglob('*')):
 if q.is_file() and '__pycache__'not in q.parts and q.suffix!='.pyc':files[str(q)]=sha(q.read_bytes())
for name in x['operation_names']:files[str(M/name)]=sha((M/name).read_bytes())
for q in(AUTH,R/'resource-locks/46308-canonical-binding-20261115-v1.json',p.EXPAT_LIBRARY):files[str(q)]=sha(q.read_bytes())
freezes={}
for c,plan in plans.items():
 write_new(M/c/'preconstruction-plan.json',(json.dumps(plan,ensure_ascii=False,indent=2)+'\n').encode())
 sf=dict(schema='Data-native-prefix-complete-new-program-freeze-v1',at=now(),scope_id=p.SCOPES[c],candidate_id=c,authorization_sha256=auth_sha,files=dict(files,**{str(M/c/'preconstruction-plan.json'):sha((M/c/'preconstruction-plan.json').read_bytes())}),physical_safety_or_actor_weights_modified=False,same_program_for_zero_and_main=True,source_profile='EXPLICIT_FOUR_DELTA_NATIVE_PREFIX_ORIGINAL_PREPARATION',initial_input_binding_sha256=a['initial_input_binding_sha256'],request_sequence=plan['requested_intents'],seed=4301,recording_overlay=json.loads((W/'third-view-camera.json').read_bytes()),optional_video_failure_not_native_success_gate=True,phase_limits=dict(zero=1,main=1),technical_caps=a['technical_caps_per_branch'],complete_native_qualification=False)
 raw=(json.dumps(sf,ensure_ascii=False,indent=2)+'\n').encode();write_new(M/c/'program-freeze.json',raw);freezes[c]=sha(raw)
pre=dict(at=now(),GPU_readonly=GPU,canonical_locks=locks,owned_worker_processes=active,owned_allocated_bytes=owned,owned_cap_bytes=40*1024**3,new_two_condition_reserve_bytes=3*1024**3,provider_quota_known=False,all_old_physical_roots_remain_closed=True,phase_dispatches=0)
write_new(M/'freeze-preflight.json',(json.dumps(pre,indent=2)+'\n').encode())
d=os.open(H.parent,os.O_RDONLY|os.O_DIRECTORY)
try:
 fcntl.flock(d,fcntl.LOCK_EX|fcntl.LOCK_NB)
 with H.open('rb')as f:
  fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);before=f.read();s=os.fstat(f.fileno());assert sha(before)==x['expected_H_sha256']and(H.stat().st_dev,H.stat().st_ino)==(s.st_dev,s.st_ino);h=json.loads(before);assert h['executing_thread_id']==x['owner']
  assert 'active_native_prefix_condition_v2_scope'not in h and 'native_prefix_condition_v2_cohort'not in h
  parent=h['native_prefix_condition_cohort'];assert parent['status']=='CLOSED_NEW_HOST_STARTUP_FAILURE_MAIN0_NO_RETRY' and all(b['main_dispatch_count']==0 for b in parent['branches'].values())
  assert parent['branches']['native_NAV_prefix_left']['zero_dispatch_count']==1 and parent['branches']['native_NAV_prefix_right']['zero_dispatch_count']==0
  for k in('active_full_host_execution_scope','active_full_host_continuation_scope','active_stow_choice_execution_scope','active_stow_choice_v2_execution_scope','active_climb_preparation_stageB_scope','active_native_prefix_condition_scope'):
   q=h[k];assert q['active']is False and q['zero_dispatch_program_sha256']is None and q['main_dispatch_program_sha256']is None
  h['native_prefix_condition_v2_cohort']=dict(at=now(),owner=x['owner'],authorization_sha256=auth_sha,authorization=str(AUTH),order=list(p.IDS),status='FROZEN_CPU_PREPARE_NO_PHYSICAL_DISPATCH',branches={c:dict(scope_id=p.SCOPES[c],whole_program_freeze_sha256=freezes[c],zero_dispatch_count=0,main_dispatch_count=0,status='FROZEN_PENDING_CPU_PREPARE')for c in p.IDS},technical_storage_reserve_bytes=3*1024**3)
  c=p.IDS[0];h['active_native_prefix_condition_v2_scope']=dict(active=True,owner=x['owner'],scope_id=p.SCOPES[c],candidate_id=c,phase='FROZEN_CPU_PREPARE_NO_PHYSICAL_PHASE_DISPATCH',authorization_sha256=auth_sha,whole_program_freeze_sha256=freezes[c],zero_dispatch_count=0,main_dispatch_count=0,zero_dispatch_program_sha256=None,main_dispatch_program_sha256=None,physical_retry_allowed=False)
  h['updated_at']=now();after=(json.dumps(h,ensure_ascii=False,indent=2)+'\n').encode();write_new(M/'H-before-cohort-freeze.json',before);write_new(M/'H-after-cohort-freeze.json',after)
  fd,t=tempfile.mkstemp(prefix='.H-prefix-freeze-',dir=H.parent)
  try:
   with os.fdopen(fd,'wb')as out:out.write(after);out.flush();os.fchmod(out.fileno(),stat.S_IMODE(s.st_mode));os.fsync(out.fileno())
   assert H.read_bytes()==before;os.replace(t,H);os.fsync(d)
  finally:
   if os.path.exists(t):os.unlink(t)
finally:os.close(d)
receipt=dict(at=now(),owner=x['owner'],before_H_sha256=sha(before),after_H_sha256=sha(after),programs=freezes,authorization_sha256=auth_sha,frozen_member_count=len(files),physical_phase_dispatches=0,runtime_roots_created=0,all_prior_H_fields_except_updated_at_preserved=True,preflight=pre)
write_new(M/'freeze-CAS-receipt.json',(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n').encode());print(json.dumps(dict(receipt=receipt,after_base64=base64.b64encode(after).decode())))
