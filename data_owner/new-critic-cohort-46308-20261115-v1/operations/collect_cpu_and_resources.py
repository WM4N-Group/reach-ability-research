from pathlib import Path
import json,hashlib,datetime,subprocess,os,fcntl
R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114');B=R/'workspace';N='new-critic-cohort-46308-20261115-v1';W=B/'workers'/N;M=B/'manifests'/N;H=B/'registry/handoff_current_status_20261115.json';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
owner='01a1d3aa-a0d5-7de0-b886-9d92ed5f1480';h=json.loads(H.read_bytes());assert h['executing_thread_id']==owner
probes={c:json.loads((M/c/'cpu-source-and-binding-probe.json').read_bytes()) for c in ('new_critic_01_full4_left_original', 'new_critic_02_full4_right_original', 'new_critic_03_full4_left_lateral_plus_0p04', 'new_critic_04_full4_right_lateral_plus_0p04', 'new_critic_05_full4_left_lateral_minus_0p04', 'new_critic_06_full4_right_lateral_minus_0p04', 'new_critic_07_full1_left_original', 'new_critic_08_full1_left_lateral_plus_0p04', 'new_critic_09_full1_left_lateral_minus_0p04', 'new_critic_10_full2_left_original', 'new_critic_11_full2_left_lateral_plus_0p04', 'new_critic_12_full2_left_lateral_minus_0p04')}
assert len({p['initial_binding_sha256']for p in probes.values()})==3
for case in ('full-1','full-2','full-4'):assert len({p['initial_binding_sha256']for p in probes.values()if p['plan']['source_scene_case_id']==case})==1
assert all(p['new_physical_calls']==0 and not p['physical_admission'] and not p['native_module_attempts'] for p in probes.values())
locks=[]
for kind,inode in [('physics', 3428459217), ('sdk', 3428459218)]:
 path=R/f'resource-locks/native-observer-{kind}-gpu1.lock';fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW);s=os.fstat(fd);assert(s.st_dev,s.st_ino)==(51,inode)
 available=False
 try:
  try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB);available=True;fcntl.flock(fd,fcntl.LOCK_UN)
  except BlockingIOError:pass
 finally:os.close(fd)
 locks.append(dict(path=str(path),device=s.st_dev,inode=s.st_ino,available_at_observation=available,not_run_lease=True))
processes=[]
for p in Path('/proc').iterdir():
 if not p.name.isdigit() or int(p.name)==os.getpid():continue
 try:args=[a.decode(errors='replace') for a in(p/'cmdline').read_bytes().split(b'\0')if a]
 except(FileNotFoundError,PermissionError,ProcessLookupError):continue
 if any(a.startswith((str(R/'runtime')+'/',str(B/'workers')+'/'))for a in args):processes.append(int(p.name))
gpu=subprocess.check_output(['nvidia-smi','--id=GPU-6d66aa68-9a3f-fdcf-89b7-f98d4106fa39','--query-gpu=index,uuid,memory.free','--format=csv,noheader,nounits'],text=True,timeout=20).strip().split(',');assert gpu[0].strip()=='1'
owned=int(subprocess.check_output(['du','-sx','-B1','/mnt/yuanyue/data-team'],text=True,timeout=90).split()[0])
files={str(p.relative_to(B)):sha(p)for p in sorted(W.rglob('*'))if p.is_file() and '__pycache__'not in p.parts and p.suffix!='.pyc'}
out=dict(at=datetime.datetime.now().astimezone().isoformat(),owner=owner,H_sha256=sha(H),GPU_UUID=gpu[1].strip(),GPU_index=1,GPU_free_MiB=int(gpu[2].strip()),GPU_startup_minimum_MiB=4096,locks=locks,owned_worker_processes=processes,owned_allocated_bytes=owned,owned_cap_bytes=40*1024**3,new_twelve_condition_reserve_bytes=19327352832,provider_quota_known=False,files_sha256=files,software_native_tests_count=8,software_native_tests_stderr=(M/'native-exact3-tests.stderr').read_text(),probes=probes,phase_dispatches=0,runtime_roots_created=0,no_physical_permission_from_CPU=True)
assert owned+19327352832<40*1024**3 and not processes
out['ready_for_freeze_and_phase_resource_check']=int(gpu[2].strip())>=4096 and all(v['available_at_observation']for v in locks)
p=M/'CPU_READY_RESOURCE_OBSERVATION.json';assert not p.exists();p.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(json.dumps(out,ensure_ascii=False,indent=2))
