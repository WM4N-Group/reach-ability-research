from pathlib import Path
import os,sys,json,base64,hashlib,subprocess,shlex
B=Path('/home/yuanyue/main/work/data-team');M=Path(__file__).resolve().parent;O=B/'manifests/new-critic-cohort-46308-20261115-v1';sys.path.insert(0,str(O));from mirror_H import mirror
sha=lambda b:hashlib.sha256(b).hexdigest();before=(B/'registry/handoff_46308_current_status_20261115.json').read_bytes();owner=os.environ['CODEX_THREAD_ID'];assert owner==os.environ['CODEX_SESSION_ID']=='01a1d3aa-a0d5-7de0-b886-9d92ed5f1480'
# Frozen old native/old controller bytes preserved; only additive distinct phase controller.
files=[dict(name=p.name,data=base64.b64encode(p.read_bytes()).decode(),sha256=sha(p.read_bytes()))for p in M.glob('*.py')];x=dict(owner=owner,expected=sha(before),files=files)
code=r'''
from pathlib import Path
import sys,os,json,hashlib,base64,datetime,fcntl,stat,tempfile,subprocess
x=json.load(sys.stdin);R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114');B=R/'workspace';CM=B/'manifests/cal-after-frozen-fit-46308-20261115-v1';O=B/'manifests/new-critic-cohort-46308-20261115-v1';W=B/'workers/new-critic-cohort-46308-20261115-v1';H=B/'registry/handoff_current_status_20261115.json';digest=lambda b:hashlib.sha256(b).hexdigest();sha=lambda p:digest(Path(p).read_bytes());now=lambda:datetime.datetime.now().astimezone().isoformat();CM.mkdir(exist_ok=True)
for row in x['files']:
 p=CM/row['name'];assert p.name==row['name']and not p.exists();raw=base64.b64decode(row['data']);assert digest(raw)==row['sha256']
 with p.open('xb')as f:f.write(raw)
sys.path[:0]=[str(CM),str(W)];from research_gate import verify,FIT_ROOT,PINS,RELEASE_SHA;from prepare_prefix import IDS,SCOPES
binding=verify();h=json.loads(H.read_bytes());co=h['new_critic_cohort_v1'];assert not co['global_stop']and not co['TRAIN_gate_passed']and co['training_fit_manifest_sha256']is None and co['protocol_sha256']==binding['collection_protocol_sha256'];assert not h['active_new_critic_cohort_scope']['active']and not h['active_T_COMPLEX_component_zero_scope']['active']
for c in IDS[:6]:
 br=co['branches'][c];assert br['status'].startswith('CLOSED_')and br['zero_dispatch_count']==br['main_dispatch_count']==1
for c in IDS[6:]:
 br=co['branches'][c];assert br['zero_dispatch_count']==br['main_dispatch_count']==0 and not(R/'runtime/workers'/SCOPES[c]).exists()
# Both GPUs unoccupied by Data and canonical inode checks, no future lease claim.
active=[]
for p in Path('/proc').glob('[0-9]*'):
 try:args=[v.decode(errors='replace')for v in(p/'cmdline').read_bytes().split(b'\0')if v]
 except OSError:continue
 if any(v.startswith((str(R/'runtime')+'/',str(B/'workers')+'/'))for v in args):active.append(int(p.name))
assert not active
for gpu,inodes in [(0,(3428729629,3428729630)),(1,(3428459217,3428459218))]:
 for kind,ino in zip(('physics','sdk'),inodes):
  p=R/f'resource-locks/native-observer-{kind}-gpu{gpu}.lock';fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW)
  try:
   st=os.fstat(fd);assert(st.st_dev,st.st_ino)==(51,ino)and(p.stat().st_dev,p.stat().st_ino)==(51,ino);fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(fd,fcntl.LOCK_UN)
  finally:os.close(fd)
owned=int(subprocess.check_output(['du','-sx','-B1','/mnt/yuanyue/data-team'],text=True,timeout=90).split()[0]);assert owned+6*1610612736<40*1024**3
files={str(CM/r['name']):r['sha256']for r in x['files']};programs={}
for c in IDS[6:9]:
 p=O/c/'program-freeze.json';programs[c]=sha(p);assert programs[c]==co['branches'][c]['whole_program_freeze_sha256'];files[str(p)]=sha(p);frozen=json.loads(p.read_bytes())
 for name,pin in frozen['files'].items():assert sha(Path(name))==pin
for name,pin in PINS.items():files[str(FIT_ROOT/name)]=pin
files[str(FIT_ROOT/'TRAIN_GATE_AND_FIT_RELEASE.json')]=RELEASE_SHA
F=CM/'phase-admission-freeze.json';v=dict(schema='Data-separate-CAL-only-phase-admission-freeze-v1',at=now(),owner=x['owner'],candidate_order=list(IDS[6:9]),research_gate=binding,original_native_programs=programs,files=files,original_TRAIN_controller_and_native_program_bytes_unchanged=True,original_total12_and_CAL3_not_expanded=True,VAL_not_released=True,refit_or_model_deployment_not_allowed=True,each_own_zero1_main1_no_retry=True,scope_or_physical_owner_not_added=True)
with F.open('x')as f:json.dump(v,f,indent=2);f.write('\n')
phase_pin=sha(F);d=os.open(H.parent,os.O_RDONLY|os.O_DIRECTORY)
try:
 fcntl.flock(d,fcntl.LOCK_EX)
 with H.open('rb')as f:
  fcntl.flock(f,fcntl.LOCK_EX);before=f.read();st=os.fstat(f.fileno());assert digest(before)==x['expected']and(H.stat().st_dev,H.stat().st_ino)==(st.st_dev,st.st_ino);h=json.loads(before);saved=json.loads(before);assert h['executing_thread_id']==x['owner'];co=h['new_critic_cohort_v1'];assert not co['TRAIN_gate_passed']and co['training_fit_manifest_sha256']is None
  co.update(TRAIN_gate_passed=True,training_fit_manifest_sha256=binding['fit_file_sha256'],CAL_research_gate_binding=binding,CAL_phase_admission_freeze_sha256=phase_pin,CAL_phase_admission_freeze_path=str(F),status='TRAIN_GATE_AND_SINGLE_FROZEN_FIT_VERIFIED_CAL7_9_ELIGIBLE_NOT_DISPATCHED',gate_and_fit_intake_at=now())
  assert co['branches']==saved['new_critic_cohort_v1']['branches'];assert all(h[k]==val for k,val in saved.items()if k not in('new_critic_cohort_v1','updated_at'));h['updated_at']=now();after=(json.dumps(h,ensure_ascii=False,indent=2)+'\n').encode();fd,t=tempfile.mkstemp(prefix='.H-actual-TRAIN-gate-fit-',dir=H.parent)
  try:
   with os.fdopen(fd,'wb')as out:out.write(after);out.flush();os.fchmod(out.fileno(),stat.S_IMODE(st.st_mode));os.fsync(out.fileno())
   assert H.read_bytes()==before;os.replace(t,H);os.fsync(d)
  finally:
   if os.path.exists(t):os.unlink(t)
finally:os.close(d)
proof=dict(at=now(),before_H_sha256=digest(before),after_H_sha256=digest(after),phase_freeze_sha256=phase_pin,research_gate=binding,all_branch_counts_preserved=True,all_closed_scopes_unchanged=True,no_physical_dispatch_by_gate_intake=True,owned_bytes=owned,retained_CAL_VAL_reserve_bytes=6*1610612736,provider_quota_unknown=True)
with(CM/'CAL-gate-admission-CAS.json').open('x')as f:json.dump(proof,f,indent=2);f.write('\n')
print(json.dumps(dict(proof=proof,after_base64=base64.b64encode(after).decode())))
'''
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],input=json.dumps(x),capture_output=True,text=True,timeout=240)
for suffix,text in [('stdout',r.stdout),('stderr',r.stderr),('exit',str(r.returncode)+'\n')]:
 with(M/('gate-intake.'+suffix)).open('x')as f:f.write(text)
assert r.returncode==0,r.stderr;v=json.loads(r.stdout);raw=base64.b64decode(v['after_base64']);assert sha(raw)==v['proof']['after_H_sha256'];mirror(raw,sha(before));(M/'CAL-gate-admission-CAS.json').write_text(json.dumps(v['proof'],indent=2)+'\n');print(json.dumps(v['proof'],indent=2))
