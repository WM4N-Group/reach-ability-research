"""Independent measurement ledger; old pair caps/counts/stop never modified."""
from pathlib import Path
import contextlib,fcntl,hashlib,json,math,os,stat,subprocess,sys,tempfile,time
from observation_config import *
OWNER='01a1d3aa-a0d5-7de0-b886-9d92ed5f1480'
SCOPE=SCOPES[ARM];ROOT=R/'runtime/workers'/SCOPE
H=B/'registry/handoff_current_status_20261115.json';AUTH=B/'registry/T_COMPLEX_OBSERVATION_STUDY_AUTHORITY_20261115_v1.json'
CAPS=PROTOCOL['scope_caps'];INHERITED={'sim_s':0.,'wall_s':0.,'output_bytes':0}
class Stop(RuntimeError):pass
def need(ok,msg):
 if not ok:raise Stop(msg)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write_new(p,v):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x')as f:json.dump(v,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
def atomic(p,v):
 fd,t=tempfile.mkstemp(prefix='.'+p.name+'.',dir=p.parent)
 try:
  with os.fdopen(fd,'w')as f:json.dump(v,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
  os.replace(t,p)
 finally:
  if os.path.exists(t):os.unlink(t)
def authority(phase=None,program_sha=None):
 h=json.loads(H.read_bytes());q=h['active_T_COMPLEX_observation_study_scope'];a=json.loads(AUTH.read_bytes());need(h['executing_thread_id']==q['owner']==a['owner']==OWNER and q['active']and not h['T_COMPLEX_observation_study_v1']['global_stop']and q['arm']==ARM and q['scope_id']==SCOPE,'Exact current full-task owner/arm/scope');need(q['authorization_sha256']==sha(AUTH)and a['training_allowed']is False and a['automatic_retry']is False and a['arms'][ARM]['zero_limit']==a['arms'][ARM]['main_limit']==1,'One own-zero/main each, no fit/retry');need(not h['active_T_COMPLEX_full_program_scope']['active']and not h['active_new_critic_cohort_scope']['active']and not h['active_T_COMPLEX_v2_camera_component_scope']['active']and not h['active_T_COMPLEX_component_zero_scope']['active'],'No old cohort/component running or reopened')
 if phase is not None:need(phase in('zero','main')and q[phase+'_dispatch_count']==1 and q[phase+'_dispatch_program_sha256']==program_sha,'Explicit exact program phase dispatch')
 return h,q,a
def verify_program(pin):
 p=M/ARM/'program-freeze.json';need(sha(p)==pin,'Exact complete program freeze');v=json.loads(p.read_bytes());need(v['arm']==ARM and v['scope_id']==SCOPE and v['authorization_sha256']==sha(AUTH),'Exact frozen full-task arm/auth')
 for name,digest in v['files'].items():
  p=Path(name);need(not p.is_symlink()and(p.resolve().is_relative_to(R)or p.resolve().is_relative_to(SDK_ROOT))and sha(p)==digest,'Frozen full source/dependency drift: '+name)
 return v
def dirbytes(root):
 return sum(p.stat().st_size for p in Path(root).rglob('*')if p.is_file())if Path(root).exists()else 0
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
   if status not in ('OWN_ZERO_PASS','OBSERVATION_STUDY_COMPLETE_NOT_TASK_SUCCESS') or not usage_known:v['stopped']=True
   atomic(self.path,v)
