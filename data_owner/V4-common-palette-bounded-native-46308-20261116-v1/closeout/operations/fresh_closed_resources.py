"""Final fixed24 authority/capacity/canonical-lock read; never dispatch, unlock another owner or mutate H."""
from pathlib import Path
import json,subprocess,shlex,hashlib,datetime
B=Path('/home/yuanyue/main/work/data-team');M=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import os,json,hashlib,fcntl,subprocess,datetime
R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114');B=R/'workspace';H=B/'registry/handoff_current_status_20261115.json';raw=H.read_bytes();h=json.loads(raw);co=h['bulk24_collector_v1'];rows=list(co['branches'].values());assert len(rows)==24 and all(x['status']in('CLOSED_ACTUAL_MAIN_PASS','CLOSED_ACTUAL_MAIN_FAILED_NO_RETRY')and x['zero_dispatch_count']==x['main_dispatch_count']==1 for x in rows);assert h['executing_thread_id']=='01a1d3aa-a0d5-7de0-b886-9d92ed5f1480'and not co['global_stop']and not h['active_bulk24_collector_scope']['active'];assert all(not h[k]['active']for k in['active_V4_palette_bounded_scope','active_V4_parallel_guard_bounded_scope','active_V4_bounded_climb_nav_scope','active_V4_bounded_climb_nav_v2_scope','active_V4_native_component_scope','active_V4_capture_execution_scope','active_T_COMPLEX_observation_study_scope','active_T_COMPLEX_full_program_scope'])
active=[]
for p in Path('/proc').glob('[0-9]*'):
 try:args=[x.decode(errors='replace')for x in(p/'cmdline').read_bytes().split(b'\0')if x]
 except OSError:continue
 if any(x.startswith((str(R/'runtime')+'/',str(B/'workers')+'/'))for x in args):active.append(int(p.name))
assert not active,active
locks=[]
for index,inodes in[(0,[3428729629,3428729630]),(1,[3428459217,3428459218])]:
 for kind,ino in zip(['physics','sdk'],inodes):
  p=R/f'resource-locks/native-observer-{kind}-gpu{index}.lock';fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW)
  try:
   st=os.fstat(fd);assert(st.st_dev,st.st_ino)==(51,ino)==(p.stat().st_dev,p.stat().st_ino);fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(fd,fcntl.LOCK_UN);locks.append(dict(path=str(p),device=51,inode=ino,free_snapshot_not_new_lease=True))
  finally:os.close(fd)
owned=int(subprocess.check_output(['du','-sx','-B1','/mnt/yuanyue/data-team'],text=True,timeout=90).split()[0]);assert owned<40*1024**3;disk=os.statvfs(R);available=next(int(x.split()[1])*1024 for x in Path('/proc/meminfo').read_text().splitlines()if x.startswith('MemAvailable:'))
print(json.dumps(dict(at=datetime.datetime.now().astimezone().isoformat(),H_sha256=hashlib.sha256(raw).hexdigest(),all24_H_closed_zero24_main24=True,global_stop=False,Data_runtime_worker_PIDs=active,canonical_GPU0_GPU1_locks=locks,owned_bytes=owned,owned_limit_bytes=40*1024**3,provider_quota_unknown=True,MemAvailable_bytes=available,shared_disk_available_bytes=disk.f_bavail*disk.f_frsize,GPU_inventory=subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,memory.free','--format=csv,noheader,nounits'],text=True,timeout=15),GPU_compute_app_rows=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,used_gpu_memory,gpu_uuid','--format=csv,noheader,nounits'],text=True,timeout=15),J_remote_root_exists=Path('/mnt/yuanyue/v-jepa').exists(),old_asset_and_capture_components_still_closed_no_repeat=True,no_H_native_lock_inode_process_or_scope_mutation=True),ensure_ascii=False))
'''
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],text=True,capture_output=True,timeout=150)
for suf,data in [('stdout',r.stdout),('stderr',r.stderr),('exit',str(r.returncode))]:
 with(M/('palette50-final-resource-readonly.'+suf)).open('x')as f:f.write(data)
assert r.returncode==0,r.stderr;v=json.loads(r.stdout);v['local_H_mirror_matches_remote']=hashlib.sha256((B/'registry/handoff_46308_current_status_20261115.json').read_bytes()).hexdigest()==v['H_sha256'];assert v['local_H_mirror_matches_remote'];(M/'palette50-final-authority-resource-proof.json').write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v[k]for k in['at','all24_H_closed_zero24_main24','Data_runtime_worker_PIDs','owned_bytes','GPU_inventory','J_remote_root_exists','local_H_mirror_matches_remote']},ensure_ascii=False,indent=2))
