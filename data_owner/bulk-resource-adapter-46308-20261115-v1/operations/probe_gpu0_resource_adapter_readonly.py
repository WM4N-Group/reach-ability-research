"""Real GPU0 lock/counter probe only; no Runtime/Actor/GL and no scope claim."""
from pathlib import Path
import sys,json,hashlib,datetime,os,fcntl
R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114');B=R/'workspace';D=B/'development/bulk-resource-adapter-46308-20261115-v1';sys.path.insert(0,str(D));from per_gpu_lease import PerGpuLease,OWNER,PROFILES
H=B/'registry/handoff_current_status_20261115.json';old=R/'resource-locks/46308-canonical-binding-20261115-v1.json';before=hashlib.sha256(old.read_bytes()).hexdigest();hraw=H.read_bytes()
def read_only_owner_check():assert json.loads(H.read_bytes())['executing_thread_id']==OWNER
with PerGpuLease(physical_index=0,authority_check=read_only_owner_check)as lease:
 lease.check(force=True);snapshot=lease.last_gpu;rows=lease.rows
 for row in rows:
  fd=os.open(row['path'],os.O_RDONLY|os.O_NOFOLLOW)
  try:
   try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
   except BlockingIOError:pass
   else:raise AssertionError('Independent GPU0 lock claim not blocked')
  finally:os.close(fd)
assert before==hashlib.sha256(old.read_bytes()).hexdigest();assert not any(n=='torch'or n=='mujoco'or n=='onnxruntime'for n in sys.modules)
print(json.dumps(dict(at=datetime.datetime.now().astimezone().isoformat(),kind='READONLY_GPU0_RESOURCE_LOCK_AND_COUNTER_PROBE_NOT_NATIVE_QUALIFICATION',GPU_snapshot=snapshot,canonical_locks=rows,lease_released=True,legacy_GPU1_binding_SHA_unchanged=before,H_not_written=True,old_TRAIN_scope_not_changed=True,actual_Runtime_Actor_GL_world_or_physics=False,new_bulk_scope_or_authority_allocated=False,one_worker_per_GPU_next_batch_limit=True,source_files_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in D.glob('*.py')}),indent=2))
