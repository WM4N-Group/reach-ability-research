"""One explicitly authorized full-host validation: existing locks, one-shot ledger.
No simulator imports, no creation/replacement of canonical resource locks.
"""
from pathlib import Path
import contextlib,fcntl,hashlib,json,math,os,stat,subprocess,sys,tempfile,time
R=Path('/mnt/miaojigui/data-team');OWNER='01a1d3aa-a0d5-7de0-b886-9d92ed5f1480'
import prepare_prefix as plan_api
CANDIDATE=os.environ.get('DATA_PREFIX_CONDITION')
if CANDIDATE not in plan_api.IDS:raise ValueError('Explicit new native prefix condition required; never default to old scope')
SCOPE=plan_api.SCOPES[CANDIDATE];ROOT=R/'runtime/workers'/SCOPE
W=R/'workspace/workers/native-prefix-condition-pilot-20261114-v1'
M=R/'workspace/manifests/native-prefix-condition-pilot-20261114-v1'/CANDIDATE
H=R/'workspace/registry/handoff_current_status_20261031.json'
AUTH=R/'workspace/registry/NATIVE_PREFIX_CONDITION_PILOT_AUTHORITY_20261114_v1.json'
BIND=R/'resource-locks/new-host-canonical-binding-v1.json'
BIND_SHA='6b837e15dcabd9f0b1c632bf21e24672f5b739c21623df26ee0e10a95f8fee19'
UUID='GPU-8a965a92-64b6-8e9e-4fc7-b21129623022';GPU_CAP=3*1024**3;RSS_CAP=4*1024**3
CAPS={'sim_s':300.,'wall_s':5400.,'output_bytes':1610612736}
INHERITED={'sim_s':0.,'wall_s':0.,'output_bytes':0} # previous ledgers retained separately by pinned history, never erased
class Stop(RuntimeError):pass

def need(x,msg):
 if not x:raise Stop(msg)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write_new(p,value):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x') as f:json.dump(value,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
def atomic(p,value):
 fd,name=tempfile.mkstemp(prefix='.'+p.name+'.',dir=p.parent)
 try:
  with os.fdopen(fd,'w') as f:json.dump(value,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
  os.replace(name,p)
 finally:
  if os.path.exists(name):os.unlink(name)
def authority(phase=None,program_sha=None):
 h=json.loads(H.read_text());q=h['active_native_prefix_condition_scope'];a=json.loads(AUTH.read_text())
 need(h['executing_thread_id']==OWNER and q['active'] is True and q['owner']==OWNER and q['scope_id']==SCOPE and q['candidate_id']==CANDIDATE,'Live exact new branch maintenance owner and scope required')
 need(sha(AUTH)==q['authorization_sha256'] and a['owner']==OWNER and a['stage']=='TWO_NATIVE_PREFIX_CONDITION_QUALIFICATION' and a['candidate_order']==list(plan_api.IDS),'Pinned full cohort authorization, not a template or old scope')
 arm=a['branches'][CANDIDATE]
 need(arm['scope_id']==SCOPE and arm['allowed_own_zero_invocations']==1 and arm['allowed_main_invocations']==1 and a['GPU_UUID']==UUID and a['automatic_retry'] is False,'Exact branch one-shot limits and authorized UUID')
 need(a['all_old_scopes_remain_closed'] is True and a['training_allowed'] is False,'No old retry or training authority')
 for key in ('active_full_host_execution_scope','active_full_host_continuation_scope','active_stow_choice_execution_scope','active_stow_choice_v2_execution_scope','active_climb_preparation_stageB_scope'):
  old=h[key];need(old['active'] is False and old['zero_dispatch_program_sha256'] is None and old['main_dispatch_program_sha256'] is None,'All old scopes must remain closed')
 if phase is not None:need(phase in ('zero','main') and q[phase+'_dispatch_program_sha256']==program_sha,'THIS exact branch/program explicit phase CAS')
 return a,h

def verify_program(expected):
 p=M/'program-freeze.json';need(sha(p)==expected,'Whole-program freeze drift');v=json.loads(p.read_text())
 need(v['scope_id']==SCOPE and v['candidate_id']==CANDIDATE and v['authorization_sha256']==sha(AUTH) and v['physical_safety_or_actor_weights_modified'] is False,'Frozen scope/auth identity')
 for path,digest in v['files'].items():
  p=Path(path);need(p.is_absolute() and not p.is_symlink() and p.resolve().is_relative_to(R) and sha(p)==digest,'Program/dependency drift: '+path)
 return v

def dirbytes(root):
 total=0
 if not Path(root).exists():return total
 for base,dirs,files in os.walk(root):
  for name in dirs:need(not (Path(base)/name).is_symlink(),'No scope directory aliases')
  for name in files:
   p=Path(base)/name;need(not p.is_symlink(),'No scope file aliases');total+=p.stat().st_size
 return total

class Lease:
 def __init__(self):self.fds=[];self.pid=os.getpid();self.rows=[];self.last_gpu=None;self.last_at=0
 def __enter__(self):
  authority();need(sha(BIND)==BIND_SHA,'Canonical device binding drift');b=json.loads(BIND.read_text())
  expected=[(51,3426427599),(51,3426427600)]
  try:
   for row,identity in zip(b['locks'],expected):
    p=Path(row['path']);need(p.parent==R/'resource-locks' and (row['device'],row['inode'])==identity,'Canonical lock metadata')
    fd=os.open(p,os.O_RDWR|os.O_CLOEXEC|os.O_NOFOLLOW);self.fds.append(fd);s=os.fstat(fd);need((s.st_dev,s.st_ino)==identity,'Canonical inode replaced');fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
    code="import os,fcntl,sys;f=os.open(sys.argv[1],os.O_RDWR|os.O_NOFOLLOW);\ntry: fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)\nexcept BlockingIOError: sys.exit(0)\nsys.exit(3)"
    probe=subprocess.run([sys.executable,'-I','-B','-c',code,str(p)],capture_output=True,text=True,timeout=10)
    need(probe.returncode==0,'Independent fresh opener not excluded');self.rows.append(dict(row,holder_PID=self.pid,independent_contention_blocked=True))
   need(len(self.rows)==2,'Both canonical Data locks required');self.check(force=True);return self
  except BaseException:self.__exit__(None,None,None);raise
 def check(self,force=False):
  need(self.pid==os.getpid() and len(self.fds)==2,'Live same-process lease only')
  for fd,row in zip(self.fds,self.rows):
   s=os.fstat(fd);p=os.stat(row['path']);need((s.st_dev,s.st_ino)==(p.st_dev,p.st_ino)==(row['device'],row['inode']),'Lock path/FD identity changed')
  now=time.monotonic()
  if force or now-self.last_at>=1:
   authority();need(sha(BIND)==BIND_SHA,'Canonical binding changed while held')
   p=subprocess.run(['nvidia-smi','--id='+UUID,'--query-gpu=index,uuid,memory.free,utilization.gpu','--format=csv,noheader,nounits'],text=True,capture_output=True,timeout=10,check=True)
   rows=[[s.strip() for s in line.split(',')] for line in p.stdout.splitlines()];matches=[r for r in rows if r[1]==UUID];need(len(matches)==1 and matches[0][0]=='0','Exact authorized physical GPU0/UUID')
   need(int(matches[0][2])*1024**2>=1024**3,'Shared GPU free safety headroom exhausted')
   apps=subprocess.run(['nvidia-smi','--id='+UUID,'--query-compute-apps=pid,used_gpu_memory,gpu_uuid','--format=csv,noheader,nounits'],text=True,capture_output=True,timeout=10,check=True)
   from gpu_observation import own_memory_bytes
   torch_module=sys.modules.get('torch');initialized=torch_module is not None and torch_module.cuda.is_initialized()
   used=own_memory_bytes(apps.stdout,pid=self.pid,uuid=UUID,initialized=initialized)
   need(used is None or used<=GPU_CAP,'Own GPU memory cap exceeded; never evict another process')
   self.last_gpu={'UUID':UUID,'index':0,'free_MiB':int(matches[0][2]),'utilization_percent':int(matches[0][3]),'own_compute_bytes':used,'own_observation_state':'MEASURED' if used is not None else 'CUDA_UNINITIALIZED_NO_PID_ROW','PID':self.pid};self.last_at=now
  return self.last_gpu
 def __exit__(self,*args):
  for fd in reversed(self.fds):os.close(fd)
  self.fds=[]

class Ledger:
 def __init__(self,root,*,program_sha,auth_sha,provenance='ACTUAL'):
  self.root=Path(root);self.program_sha=program_sha;self.auth_sha=auth_sha;self.provenance=provenance
  need(provenance in ('ACTUAL','EXPLICIT_SOFTWARE_TEST'),'Explicit provenance')
  if provenance=='ACTUAL':need(self.root==ROOT and self.root.resolve()==self.root,'Exact new full-host root, never old B or alias')
  else:need(not str(self.root).startswith(str(R/'runtime')),'Software tests can never use a physical root')
  self.account=self.root/'accounting';self.account.mkdir(parents=True,exist_ok=True);self.path=self.account/'ledger.json';self.lock=self.account/'ledger.lock'
  with self.locked():
   if not self.path.exists():atomic(self.path,{'schema':'Data-one-full-host-zero-main-ledger-v1','scope_id':SCOPE,'provenance':provenance,'program_sha256':program_sha,'authorization_sha256':auth_sha,'stopped':False,'rows':[]})
   self.read()
 @contextlib.contextmanager
 def locked(self):
  fd=os.open(self.lock,os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW|os.O_CLOEXEC,0o664)
  try:fcntl.flock(fd,fcntl.LOCK_EX);yield
  finally:os.close(fd)
 def read(self):
  v=json.loads(self.path.read_text());need(v['program_sha256']==self.program_sha and v['authorization_sha256']==self.auth_sha and v['provenance']==self.provenance,'Ledger cannot change program/grant or upgrade a software test');return v
 def claim(self,phase,started):
  need(phase in ('zero','main'),'One zero/main only')
  with self.locked():
   v=self.read();need(not v['stopped'] and all(r['closed'] for r in v['rows']),'No failure/crash resume or simultaneous phases');need(not any(r['phase']==phase for r in v['rows']),'A claimed phase cannot be retried')
   if phase=='main':need(len(v['rows'])==1 and v['rows'][0]['phase']=='zero' and v['rows'][0]['status']=='OWN_ZERO_PASS','Own zero of THIS program must pass before main')
   v['rows'].append({'phase':phase,'PID':os.getpid(),'started_monotonic':started,'closed':False,'status':'CLAIMED_NOT_RESULT','sim_s':0.,'wall_s':0.,'output_highwater_bytes':0});atomic(self.path,v)
 def observe(self,phase,*,sim_s,wall_s,cleanup=False):
  need(all(type(x) in (int,float) and math.isfinite(x) and x>=0 for x in (sim_s,wall_s)),'Measured finite counters')
  with self.locked():
   v=self.read();rows=[r for r in v['rows'] if r['phase']==phase];need(len(rows)==1,'Current phase claim');r=rows[0];need(not r['closed'] and r['PID']==os.getpid(),'No foreign/resumed phase')
   need(sim_s+1e-8>=r['sim_s'] and wall_s>=r['wall_s'],'No sim/wall reset');r['sim_s']=sim_s;r['wall_s']=wall_s;r['output_highwater_bytes']=max(r['output_highwater_bytes'],dirbytes(self.root));atomic(self.path,v)
   totals={'sim_s':INHERITED['sim_s']+sum(x['sim_s'] for x in v['rows']),'wall_s':INHERITED['wall_s']+sum(x['wall_s'] for x in v['rows']),'output_bytes':INHERITED['output_bytes']+max([x['output_highwater_bytes'] for x in v['rows']]+[0])}
   margin={'sim_s':0. if cleanup else .005,'wall_s':0. if cleanup else 15.,'output_bytes':0 if cleanup else 64*1024**2}
   over=[k for k in CAPS if totals[k]>=CAPS[k]-margin[k]]
   if over:v['stopped']=True;r['budget_stop_channels']=over;atomic(self.path,v);raise Stop('Cumulative budget stop: '+str(over))
   return totals
 def close(self,phase,status,*,sim_s,wall_s,report_sha,usage_known=True):
  with self.locked():
   v=self.read();r=next(x for x in v['rows'] if x['phase']==phase);need(not r['closed'] and r['PID']==os.getpid(),'Close claimed owned phase once');r.update(closed=True,status=status,sim_s=sim_s,wall_s=wall_s,report_sha256=report_sha,usage_known=usage_known,output_highwater_bytes=max(r['output_highwater_bytes'],dirbytes(self.root)))
   if status not in ('OWN_ZERO_PASS','REQUESTED_API0_PASS') or not usage_known:v['stopped']=True
   atomic(self.path,v)
