"""Admission read-only snapshot, GPU1 lock probe is NOT a lease or GPU0 claim."""
from pathlib import Path
import os,json,hashlib,fcntl,subprocess,datetime
R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114');B=R/'workspace';H=B/'registry/handoff_current_status_20261115.json';OWNER='01a1d3aa-a0d5-7de0-b886-9d92ed5f1480'
def fresh(*,require_dispatch_reserve=True):
 h=json.loads(H.read_bytes());assert h['executing_thread_id']==OWNER;C=json.loads((B/'workers/bulk24-collector-46308-20261115-v1/protocol.json').read_bytes());assert not h['active_new_critic_cohort_scope']['active']and not h['active_T_COMPLEX_full_program_scope']['active'];allow=set();obs=h.get('active_T_COMPLEX_observation_study_scope',{})
 if obs.get('active'):
  assert obs['owner']==OWNER and obs['scope_id']=='data-46308-T-COMPLEX-observability-only-20261115-v1'and obs['whole_program_freeze_sha256']=='9fdd2076cda187b0749f7f294ef362acb954cac4d7fa95a2feec7e1b3529b7ad';root=R/'runtime/workers'/obs['scope_id'];l=json.loads((root/'accounting/ledger.json').read_bytes());row=l['rows'][-1];assert not row['closed']and Path('/proc/'+str(row['PID'])).exists()and not(root/row['phase']/'result.json').exists();allow.add(row['PID'])
 active=[]
 for p in Path('/proc').glob('[0-9]*'):
  try:args=[v.decode(errors='replace')for v in(p/'cmdline').read_bytes().split(b'\0')if v]
  except OSError:continue
  if any(v.startswith((str(R/'runtime')+'/',str(B/'workers')+'/'))for v in args):active.append(int(p.name))
 assert set(active)==allow,dict(owned_native=active,only_allowed_current_GPU0_OBS=list(allow))
 for kind,ino in [('physics',3428459217),('sdk',3428459218)]:
  p=R/f'resource-locks/native-observer-{kind}-gpu1.lock';fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
  try:
   st=os.fstat(fd);assert(st.st_dev,st.st_ino)==(51,ino)and(p.stat().st_dev,p.stat().st_ino)==(51,ino);fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(fd,fcntl.LOCK_UN)
  finally:os.close(fd)
 binding=R/'resource-locks/46308-canonical-binding-20261115-v1.json';assert hashlib.sha256(binding.read_bytes()).hexdigest()=='ada256e7a3b3f4d2fdb5b4e210963d6522f8d00485ccbedb707039eedaefc11b'
 owned=int(subprocess.check_output(['du','-sx','-B1','/mnt/yuanyue/data-team'],text=True,timeout=90).split()[0]);reserve=C['remaining_CAL_VAL_reserve_bytes']+C['concurrent_observation_scope_reserve_bytes']+C['rolling_one_active_root_reserve_bytes'];assert not require_dispatch_reserve or owned+reserve<40*1024**3
 gpu=subprocess.check_output(['nvidia-smi','--id='+C['GPU_UUID'],'--query-gpu=index,uuid,memory.free','--format=csv,noheader,nounits'],text=True,timeout=15).strip().split(',');assert gpu[0].strip()=='1'and gpu[1].strip()==C['GPU_UUID']and(not require_dispatch_reserve or int(gpu[2])>=4096)
 assert set(C['CPU_affinity'])=={38,39}and set(C['CPU_affinity']).issubset(os.sched_getaffinity(0));mem={l.split(':')[0]:int(l.split()[1])*1024 for l in Path('/proc/meminfo').read_text().splitlines()if l.startswith('MemAvailable:')};assert not require_dispatch_reserve or mem['MemAvailable']>=8*1024**3
 return dict(at=datetime.datetime.now().astimezone().isoformat(),GPU1_free_MiB=int(gpu[2]),owned_bytes=owned,rolling_reserve_bytes=reserve,MemAvailable_bytes=mem['MemAvailable'],only_allowed_GPU0_OBS_PIDs=sorted(allow),no_active_GPU1_Data_worker=True,canonical_GPU1_probe_free_not_lease=True,CPU38_39_disjoint_from_current_OBS36_37=True,provider_quota_unknown=True)
