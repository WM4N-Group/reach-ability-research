"""Bind previously unused authorized GPU0 locks. No Runtime/Actor/world or H write.
Existing GPU1 binding/lock inode/held lease are NEVER changed or bypassed.
"""
from pathlib import Path
import json,sys,hashlib,os,fcntl,subprocess,datetime,stat
R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114');L=R/'resource-locks';x=json.load(sys.stdin);OWNER='01a1d3aa-a0d5-7de0-b886-9d92ed5f1480';PIN='b158483b71151ce54d854c28c13ee9fa0980800785c0741b1ae3c4da05f082c7';assert x['main_plan_sha256']==PIN;H=R/'workspace/registry/handoff_current_status_20261115.json';h=json.loads(H.read_bytes());assert h['executing_thread_id']==OWNER;sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();old=L/'46308-canonical-binding-20261115-v1.json';oldraw=old.read_bytes();assert sha(old)=='ada256e7a3b3f4d2fdb5b4e210963d6522f8d00485ccbedb707039eedaefc11b';oldident=[(Path(r['path']).stat().st_dev,Path(r['path']).stat().st_ino)for r in json.loads(oldraw)['locks']];assert oldident==[(51,3428459217),(51,3428459218)]
info=subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,name,memory.total,memory.free','--format=csv,noheader,nounits'],text=True,timeout=20);rows=[[s.strip()for s in line.split(',')]for line in info.splitlines()];gpu=next(r for r in rows if r[0]=='0');assert gpu[1]=='GPU-297c1146-bcec-a8ee-8437-d9603392a2e1'and '4090'in gpu[2];assert int(gpu[4])>=4096
binding=L/'46308-gpu0-bulk-canonical-binding-20261115-v1.json';assert not binding.exists();d=os.open(L,os.O_RDONLY|os.O_DIRECTORY);locks=[]
try:
 fcntl.flock(d,fcntl.LOCK_EX|fcntl.LOCK_NB)
 for kind in('physics','sdk'):
  p=L/f'native-observer-{kind}-gpu0.lock';assert not p.exists();fd=os.open(p,os.O_CREAT|os.O_EXCL|os.O_RDWR|os.O_NOFOLLOW|os.O_CLOEXEC,0o644)
  try:
   st=os.fstat(fd);fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB);other=os.open(p,os.O_RDONLY|os.O_NOFOLLOW)
   try:
    try:fcntl.flock(other,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:blocked=True
    else:raise AssertionError('Independent open must be blocked by canonical lock')
   finally:os.close(other)
   locks.append(dict(path=str(p),device=st.st_dev,inode=st.st_ino,independent_contention_blocked=blocked))
  finally:os.close(fd)
 v=dict(schema='Data-new-host-canonical-binding-v1',at=datetime.datetime.now().astimezone().isoformat(),owner=OWNER,host='180.97.68.228:46308',hostname=subprocess.check_output(['hostname'],text=True).strip(),GPU_UUID=gpu[1],GPU_physical_index=0,Actor_logical_device='cuda:0',MUJOCO_EGL_DEVICE_ID='0',locks=locks,source_authorization_main_plan_sha256=PIN,old_GPU1_binding_sha256=sha(old),old_GPU1_device_inode_preserved=oldident,current_frozen_TRAIN6_not_changed=True,resource_lease_not_held_after_this_probe=True,new_world_or_zero_or_main_started=False,new_bulk_program_or_scope_allocated=False,not_native_or_GL_qualification=True,initial_next_batch_worker_limit_one_per_gpu=True)
 with binding.open('x')as f:json.dump(v,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 os.fsync(d)
finally:os.close(d)
assert old.read_bytes()==oldraw and oldident==[(Path(r['path']).stat().st_dev,Path(r['path']).stat().st_ino)for r in json.loads(oldraw)['locks']]
proof=dict(binding=str(binding),binding_sha256=sha(binding),binding_payload=v,all_existing_GPU1_bytes_inodes_unchanged=True,H_not_written=True,no_Runtime_Actor_GL_world_or_physics=True,unused_GPU0_resource_binding_only=True,current_global_TRAIN_lifecycle_blocks_concurrent_other_Data_workers_until_closed=True)
print(json.dumps(proof,indent=2))
