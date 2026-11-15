"""Minimal future-batch per-GPU adaptation of Data's existing exclusive Lease.
One owner, one worker/GPU initially; no scope scheduler, model or physics import.
Does NOT change/bypass the frozen TRAIN6's globally serialized lifecycle.
"""
from pathlib import Path
import os,sys,time,json,hashlib,fcntl,subprocess
from gpu_observation import own_memory_bytes
ROOT=Path('/mnt/yuanyue/data-team/deployments/46308-20261114')
OWNER='01a1d3aa-a0d5-7de0-b886-9d92ed5f1480'
PROFILES={
 0:dict(UUID='GPU-297c1146-bcec-a8ee-8437-d9603392a2e1',binding=ROOT/'resource-locks/46308-gpu0-bulk-canonical-binding-20261115-v1.json',sha256='50d6365e40fa07402d6765809b841cd29cc7b0c2a93d00542aecc92879df1bcd',locks=((51,3428729629),(51,3428729630))),
 1:dict(UUID='GPU-6d66aa68-9a3f-fdcf-89b7-f98d4106fa39',binding=ROOT/'resource-locks/46308-canonical-binding-20261115-v1.json',sha256='ada256e7a3b3f4d2fdb5b4e210963d6522f8d00485ccbedb707039eedaefc11b',locks=((51,3428459217),(51,3428459218)))
}
class ResourceStop(RuntimeError):pass
def need(ok,message):
 if not ok:raise ResourceStop(message)
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def check_binding(index,payload):
 need(type(index)is int and index in PROFILES,'Only the two explicit new-host authorized GPUs')
 p=PROFILES[index];need(payload['owner']==OWNER and payload['GPU_UUID']==p['UUID']and payload['GPU_physical_index']==index and payload['Actor_logical_device']=='cuda:0'and payload['MUJOCO_EGL_DEVICE_ID']==str(index),'Exact GPU/actor/EGL binding, no borrowed UUID')
 need(len(payload['locks'])==2,'Exactly physical and SDK locks per GPU')
 for kind,row,identity in zip(('physics','sdk'),payload['locks'],p['locks']):
  need(Path(row['path'])==ROOT/f'resource-locks/native-observer-{kind}-gpu{index}.lock'and(row['device'],row['inode'])==identity,'Existing canonical lock path/device/inode; never create/copy/replace')
 return p

def parse_gpu(text,*,index):
 p=PROFILES[index];rows=[[s.strip()for s in line.split(',')]for line in text.splitlines()if line.strip()];matches=[r for r in rows if len(r)==4 and r[1]==p['UUID']]
 need(len(matches)==1 and matches[0][0]==str(index),'Exact unique physical GPU index/UUID')
 row=matches[0];need(row[2].isdigit()and row[3].isdigit(),'GPU counters unknown is not zero')
 return dict(UUID=p['UUID'],index=index,free_MiB=int(row[2]),utilization_percent=int(row[3]))

class PerGpuLease:
 def __init__(self,*,physical_index,authority_check):
  need(type(physical_index)is int and physical_index in PROFILES,'Explicit authorized per-GPU allocation required')
  need(callable(authority_check),'Future frozen caller must verify its own live scope/phase authority')
  self.index=physical_index;self.profile=PROFILES[physical_index];self.authority=authority_check;self.fds=[];self.rows=[];self.pid=os.getpid();self.last_gpu=None;self.last_at=0.;self.peak_own_compute_bytes=None
 def __enter__(self):
  try:
   self.authority();path=self.profile['binding'];need(not path.is_symlink()and sha(path)==self.profile['sha256'],'Immutable per-GPU canonical binding SHA')
   binding=json.loads(path.read_bytes());check_binding(self.index,binding)
   for row in binding['locks']:
    p=Path(row['path']);fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC);self.fds.append(fd);st=os.fstat(fd);need((st.st_dev,st.st_ino)==(row['device'],row['inode'])and(p.stat().st_dev,p.stat().st_ino)==(st.st_dev,st.st_ino),'Canonical inode identity before lock');fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB);self.rows.append(dict(row,holder_PID=self.pid))
   self.check(force=True);need(self.last_gpu['free_MiB']>=4096,'Initial own3GiB + shared1GiB headroom, not future promise');return self
  except BaseException:
   self.__exit__();raise
 def check(self,force=False):
  need(os.getpid()==self.pid and len(self.fds)==2,'Lease belongs to this process, no cross-worker inheritance')
  for fd,row in zip(self.fds,self.rows):
   st=os.fstat(fd);p=Path(row['path']);need((st.st_dev,st.st_ino)==(row['device'],row['inode'])and(p.stat().st_dev,p.stat().st_ino)==(st.st_dev,st.st_ino),'Held inode changed')
  now=time.monotonic()
  if force or now-self.last_at>=1:
   self.authority();need(sha(self.profile['binding'])==self.profile['sha256'],'Held binding SHA drift')
   args=['nvidia-smi','--id='+self.profile['UUID']];gpu=subprocess.check_output(args+['--query-gpu=index,uuid,memory.free,utilization.gpu','--format=csv,noheader,nounits'],text=True,timeout=10);v=parse_gpu(gpu,index=self.index);need(v['free_MiB']>=1024,'Shared free safety1GiB exhausted; stop new dispatch, do not evict')
   apps=subprocess.check_output(args+['--query-compute-apps=pid,used_gpu_memory,gpu_uuid','--format=csv,noheader,nounits'],text=True,timeout=10);torch=sys.modules.get('torch');initialized=torch is not None and torch.cuda.is_initialized();used=own_memory_bytes(apps,pid=self.pid,uuid=self.profile['UUID'],initialized=initialized);need(used is None or used<=3*1024**3,'Own GPU3GiB cap exceeded')
   if used is not None:self.peak_own_compute_bytes=max(self.peak_own_compute_bytes or 0,used)
   v.update(PID=self.pid,own_compute_bytes=used,own_observation_state='MEASURED'if used is not None else'CUDA_UNINITIALIZED_NO_PID_ROW',peak_own_compute_bytes=self.peak_own_compute_bytes);self.last_gpu=v;self.last_at=now
  return self.last_gpu
 def __exit__(self,*args):
  for fd in reversed(self.fds):os.close(fd)
  self.fds=[]
