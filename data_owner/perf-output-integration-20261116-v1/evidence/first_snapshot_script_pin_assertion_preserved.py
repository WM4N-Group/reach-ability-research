from pathlib import Path
import json,hashlib,os,subprocess,datetime,fcntl
R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114');H=R/'workspace/registry/handoff_current_status_20261115.json'
raw=H.read_bytes();h=json.loads(raw);binding=R/'resource-locks/46308-gpu0-bulk-canonical-binding-20261115-v1.json'
locks=[]
for name,ino in [('native-observer-physics-gpu0.lock',3428729629),('native-observer-sdk-gpu0.lock',3428729630)]:
 p=R/'resource-locks'/name;s=p.stat();assert (s.st_dev,s.st_ino)==(51,ino)
 # Read-only observation /proc/locks, never take/replace/delete a lock.
 holders=[]
 for line in Path('/proc/locks').read_text().splitlines():
  if str(ino)==line.split()[5].split(':')[-1]:holders.append(line)
 locks.append(dict(path=str(p),device=s.st_dev,inode=s.st_ino,proc_locks=holders))
used=int(subprocess.check_output(['du','-s','-B1','/mnt/yuanyue/data-team'],text=True).split()[0])
active={k:v.get('scope_id')for k,v in h.items()if isinstance(v,dict)and v.get('active')is True}
assert not active and h['executing_thread_id']=='01a1d3aa-a0d5-7de0-b886-9d92ed5f1480'
api=Path('/mnt/yuanyue/ainav-compute/code/a35428d9982c5621ae363c00e8918516e5f52510/ainav/development/indexed_identity_guard_v1')
pins={n:hashlib.sha256((api/n).read_bytes()).hexdigest()for n in ['indexed_guard.py','install_fresh_driver.py','tests/test_install_fresh_driver.py']}
assert pins['indexed_guard.py']=='5aa94c79e37315f9d62839b31ce7d421299b0971ec3f47c7fe4329f05bebf4a5'
assert pins['install_fresh_driver.py']=='4c8e9a64a06ed2b4900aca75b866e079645d81a54670a197c6490493292723d5'
print(json.dumps(dict(at=datetime.datetime.now().astimezone().isoformat(),authority_sha256=hashlib.sha256(raw).hexdigest(),owner=h['executing_thread_id'],active_scopes=active,E20_main_PID248453_exists=Path('/proc/248453').exists(),E20_closed=h['active_E20_prearrival40_v3_scope'],gpu0_canonical_locks=locks,owned_allocated_bytes=used,owned_self_limit_bytes=40*1024**3,provider_quota_unknown=True,disk_free_bytes=os.statvfs(R).f_bavail*os.statvfs(R).f_frsize,gpu_inventory=subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,memory.used','--format=csv,noheader'],text=True),AINav_source_pins=pins,no_claim_CAS_dispatch_lock_or_source_mutation=True),ensure_ascii=False))
