"""One explicit fixed bulk24 phase onGPU1; no old source/OBS mutation or retry."""
from pathlib import Path
import sys,os,json,hashlib,base64,subprocess,shlex
B=Path('/home/yuanyue/main/work/data-team');M=Path(__file__).resolve().parent;O=B/'manifests/new-critic-cohort-46308-20261115-v1';sys.path.insert(0,str(O));from mirror_H import mirror
arm,action=sys.argv[1:];assert arm in json.loads((B/'workers'/M.name/'protocol.json').read_bytes())['order']and action in('prepare','zero-dispatch','zero-run','zero-cold','main-dispatch','main-run','fetch-zero','fetch-main','close-zero','close-main');sha=lambda b:hashlib.sha256(b).hexdigest();before=(B/'registry/handoff_46308_current_status_20261115.json').read_bytes();rec=json.loads((M/'freeze-CAS-receipt.json').read_bytes());x=dict(owner=os.environ['CODEX_THREAD_ID'],arm=arm,action=action,program=rec['programs'][arm],expected=sha(before));assert x['owner']==os.environ['CODEX_SESSION_ID']=='01a1d3aa-a0d5-7de0-b886-9d92ed5f1480'
PRELUDE=r'''
from pathlib import Path
import sys,os,json,hashlib,base64,subprocess,fcntl,stat,tempfile,datetime
x=json.load(sys.stdin);R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114');B=R/'workspace';N='bulk24-collector-46308-20261115-v1';W=B/'workers'/N;M=B/'manifests'/N;H=B/'registry/handoff_current_status_20261115.json';a=x['arm'];D=M/a;C=json.loads((W/'protocol.json').read_bytes());scope=C['arms'][a]['scope_id'];ROOT=R/'runtime/workers'/scope;pin=x['program'];sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();digest=lambda b:hashlib.sha256(b).hexdigest();now=lambda:datetime.datetime.now().astimezone().isoformat();assert sha(D/'program-freeze.json')==pin;h=json.loads(H.read_bytes());q=h['active_bulk24_collector_scope'];co=h['bulk24_collector_v1'];assert h['executing_thread_id']==x['owner'];assert co['branches'][a]['whole_program_freeze_sha256']==pin
E=dict(os.environ,LD_PRELOAD=str(R/'dependencies/native-expat-overlay-20261115-v1/lib/libexpat.so.1'),DATA_PREFIX_CONDITION=a,OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2',MKL_NUM_THREADS='2',PYTHONDONTWRITEBYTECODE='1');PY='/mnt/yuanyue/data-team/env-native-v1/bin/python'
def record(p,v):
 with p.open('x')as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
sys.path.insert(0,str(W));from resource_snapshot import fresh
def cas(change):
 d=os.open(H.parent,os.O_RDONLY|os.O_DIRECTORY)
 try:
  fcntl.flock(d,fcntl.LOCK_EX)
  with H.open('rb')as f:
   fcntl.flock(f,fcntl.LOCK_EX);before=f.read();st=os.fstat(f.fileno());assert digest(before)==x['expected']and(H.stat().st_dev,H.stat().st_ino)==(st.st_dev,st.st_ino);v=json.loads(before);saved=json.loads(before);change(v);assert all(v[k]==old for k,old in saved.items()if k not in('bulk24_collector_v1','active_bulk24_collector_scope','updated_at'));v['updated_at']=now();after=(json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode();fd,t=tempfile.mkstemp(prefix='.H-complex-full-phase-',dir=H.parent)
   try:
    with os.fdopen(fd,'wb')as out:out.write(after);out.flush();os.fchmod(out.fileno(),stat.S_IMODE(st.st_mode));os.fsync(out.fileno())
    assert H.read_bytes()==before;os.replace(t,H);os.fsync(d)
   finally:
    if os.path.exists(t):os.unlink(t)
 finally:os.close(d)
 return dict(before_H_sha256=digest(before),after_H_sha256=digest(after),after_base64=base64.b64encode(after).decode())
'''
ACTIONS={
'prepare':r'''
assert not h['active_T_COMPLEX_full_program_scope']['active']and not h['active_new_critic_cohort_scope']['active'];assert q['active']and q['arm']==a and q['zero_dispatch_count']==q['main_dispatch_count']==0 and not ROOT.exists();E.update(CUDA_VISIBLE_DEVICES='',MUJOCO_GL='disable')
with(D/'prepare.stdout').open('xb')as out,(D/'prepare.stderr').open('xb')as err:r=subprocess.run(['taskset','-c','38,39',PY,'-I','-B',str(W/'full_host_worker.py'),'--phase','prepare','--program-sha256',pin],env=E,stdout=out,stderr=err,timeout=90)
record(D/'prepare.exit.json',dict(exit_code=r.returncode));assert r.returncode==0,(D/'prepare.stderr').read_text();assert not ROOT.exists();print(json.dumps(dict(prepared=True,arm=a,stdout=(D/'prepare.stdout').read_text())))
''',
'dispatch':r'''
phase=x['action'].split('-')[0];resources=fresh();assert json.loads((D/'prepare.exit.json').read_bytes())['exit_code']==0;prep=json.loads((D/('fenced-prepare-'+pin+'.json')).read_bytes());assert prep['prepared']and prep['program_sha256']==pin
if phase=='zero':assert not ROOT.exists()
else:
 z=json.loads((ROOT/'zero/result.json').read_bytes());cold=json.loads((D/'zero-cold.json').read_bytes());l=json.loads((ROOT/'accounting/ledger.json').read_bytes());assert z['passed']and z['program_sha256']==pin and cold['passed']and cold['program_sha256']==pin and not l['stopped']and len(l['rows'])==1 and l['rows'][0]['closed'];assert not(ROOT/'main').exists()
def change(v):
 q=v['active_bulk24_collector_scope'];co=v['bulk24_collector_v1'];br=co['branches'][a];assert not co['global_stop']and q['active']and q['arm']==a and q['scope_id']==scope and q['whole_program_freeze_sha256']==pin and q[phase+'_dispatch_count']==br[phase+'_dispatch_count']==0
 q.update(phase='CAS_DISPATCHED_'+phase.upper(),**{phase+'_dispatch_count':1,phase+'_dispatch_program_sha256':pin});br.update(status='DISPATCHED_'+phase.upper(),**{phase+'_dispatch_count':1});co['status']='FULL_NATIVE_DEV_'+a+'_'+phase.upper()+'_IN_PROGRESS';q['last_phase_resource_snapshot']=resources
v=cas(change);record(D/('CAS-'+phase+'.json'),{k:z for k,z in v.items()if k!='after_base64'});print(json.dumps(v))
''',
'run':r'''
phase=x['action'].split('-')[0];assert not h['active_T_COMPLEX_full_program_scope']['active']and not h['active_new_critic_cohort_scope']['active'];assert q['active']and q['arm']==a and q[phase+'_dispatch_count']==1 and q[phase+'_dispatch_program_sha256']==pin;assert not(ROOT/phase).exists();resources=fresh();record(D/(phase+'-launch-once.json'),dict(at=now(),program_sha256=pin,resources=resources,automatic_retry=False));E.update(CUDA_VISIBLE_DEVICES=C['GPU_UUID'],MUJOCO_GL='egl',MUJOCO_EGL_DEVICE_ID='1');cpus=C['CPU_affinity'];assert cpus==[38,39]
with(D/(phase+'-launch.stdout')).open('xb')as out,(D/(phase+'-launch.stderr')).open('xb')as err:
 p=subprocess.Popen(['taskset','-c',','.join(map(str,cpus)),PY,'-I','-B',str(W/'full_host_worker.py'),'--phase',phase,'--program-sha256',pin],env=E,stdout=out,stderr=err);record(D/(phase+'-child.json'),dict(PID=p.pid,at=now(),CPUs=cpus))
 try:rc=p.wait(timeout=(220 if phase=='zero'else C['scope_caps']['wall_s']+60))
 except subprocess.TimeoutExpired:
  p.terminate()
  try:rc=p.wait(timeout=20)
  except subprocess.TimeoutExpired:p.kill();rc=p.wait(timeout=10)
record(D/(phase+'-exit.json'),dict(at=now(),exit_code=rc));print(json.dumps(dict(exit_code=rc,result_available=(ROOT/phase/'result.json').exists(),stderr=(D/(phase+'-launch.stderr')).read_text()[-5000:])))
''',
'zero-cold':r'''
import numpy as np
z=ROOT/'zero';v=json.loads((z/'result.json').read_bytes());l=json.loads((ROOT/'accounting/ledger.json').read_bytes());assert v['passed']and v['status']=='OWN_ZERO_PASS'and v['program_sha256']==pin and v['task_physics_steps']==v['actual_main_world_sim_s']==0 and v['actual_recorded_commands']==0 and v['actual_recorded_visual_frames']==1 ;assert not v['close_errors']and not Path('/proc/'+str(v['PID'])).exists();assert len(l['rows'])==1 and l['rows'][0]['closed']and l['rows'][0]['report_sha256']==sha(z/'result.json')and not l['stopped'];assert v['raw_third_view_closure']['captured_frames']==1 and v['raw_third_view_closure']['complete_for_capture_grid']and v['review_closure']['frames']==1
idx=json.loads((z/'episode/index.json').read_bytes());assert idx['commands']==[]and len(idx['visual'])==1;row=idx['visual'][0];p=z/'episode'/row['path'];assert sha(p)==row['sha256']
with np.load(p,allow_pickle=False)as n:
 assert n['rgb'].shape==(1,1,128,192,3)and n['rgb'].dtype==np.uint8 and n['depth_m'].shape==(1,1,128,192,1)and n['proprio'].shape==(1,1,45)and n['timestamps_s'].tolist()==[[0.]]and not n['action_valid'].any()
rawdir=z/'raw-third-view';rawmeta=json.loads((rawdir/'metadata.json').read_bytes());camera=json.loads((W/'third-view-camera.json').read_bytes());assert rawmeta['camera_spec']==camera and(camera['width'],camera['height'])==(192,128)
rawcl=json.loads((rawdir/'closure.json').read_bytes());assert rawcl['archived_frames']==1 and len(rawcl['chunks'])==1;rr=rawcl['chunks'][0];assert sha(rawdir/rr['path'])==rr['sha256']
with np.load(rawdir/rr['path'],allow_pickle=False)as n:assert n['rgb'].shape==(1,128,192,3)and n['rgb'].dtype==np.uint8 and n['physics_tick'].tolist()==[0]
report=dict(passed=True,program_sha256=pin,original_zero_result_sha256=sha(z/'result.json'),actual_model_numeric_sha256=v['actual_model_numeric_sha256'],full_host_real_INPUT8_raw_frame_and_review=True,direct_raw_resolution_px=[192,128],HD_not_claimed=True,original_INPUT8_no_synthetic_alias=True,no_simulator_or_Actor_calls=True,not_task_or_witness_or_dynamic_plan=True)
record(D/'zero-cold.json',report);print(json.dumps(report))
''',
'fetch':r'''
files={}
for phase in(x['action'].split('-')[1],):
 for name in('result.json','actual-config.json','actual-model-identity.json','native-asset-construction.json','resource-lease.json'):
  p=ROOT/phase/name
  if p.exists():files[phase+'-'+name]=base64.b64encode(p.read_bytes()).decode()
p=ROOT/'accounting/ledger.json'
if p.exists():files['ledger.json']=base64.b64encode(p.read_bytes()).decode()
p=D/'zero-cold.json'
if p.exists():files['zero-cold.json']=base64.b64encode(p.read_bytes()).decode()
print(json.dumps(dict(small_files=files)))
''',
'close':r'''
phase=x['action'].split('-')[1];assert q[phase+'_dispatch_count']==1;v=json.loads((ROOT/phase/'result.json').read_bytes());l=json.loads((ROOT/'accounting/ledger.json').read_bytes());assert not Path('/proc/'+str(v['PID'])).exists()and all(r['closed']for r in l['rows'])and l['rows'][-1]['report_sha256']==sha(ROOT/phase/'result.json');resources=fresh(require_dispatch_reserve=False)
def change(h):
 q=h['active_bulk24_collector_scope'];co=h['bulk24_collector_v1'];br=co['branches'][a];assert not h['active_T_COMPLEX_full_program_scope']['active']and not h['active_new_critic_cohort_scope']['active'];assert q['active']and q['arm']==a and q['whole_program_freeze_sha256']==pin
 if phase=='zero'and v['passed']:
  assert json.loads((D/'zero-cold.json').read_bytes())['passed'];q.update(phase='OWN_FULL_ZERO_COLD_PASS_AWAIT_MAIN',zero_dispatch_program_sha256=None);br.update(status='OWN_FULL_ZERO_COLD_PASS_AWAIT_MAIN',zero_result_sha256=sha(ROOT/'zero/result.json'))
 else:
  q.update(active=False,phase='CLOSED_ACTUAL_'+phase.upper()+('_PASS'if v['passed']else'_FAILED_NO_RETRY'),zero_dispatch_program_sha256=None,main_dispatch_program_sha256=None,closed_at=now(),actual_result_sha256=sha(ROOT/phase/'result.json'));br.update(status=q['phase'],actual_result_sha256=q['actual_result_sha256'],actual_task_success=v.get('whole_task_success_claimed',False),actual_requested_chain_passed=v['passed'],actual_main_world_sim_s=v['actual_main_world_sim_s'])
  if phase=='zero'or not v.get('usage_known',False)or v.get('resource_censored')or any(t in str(v.get('error','')).lower()for t in('immutable','identity','source mismatch','binding mismatch','frozen','canonical')):co['global_stop']=True
 co['status']=q['phase'];q['closure_resource_snapshot']=resources
out=cas(change);record(D/('CAS-close-'+phase+'.json'),{k:z for k,z in out.items()if k!='after_base64'});print(json.dumps(out))
'''}
key='dispatch'if action.endswith('-dispatch')else'run'if action.endswith('-run')else'fetch'if action.startswith('fetch-')else'close'if action.startswith('close-')else action
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(PRELUDE+ACTIONS[key])],input=json.dumps(x),capture_output=True,text=True,timeout=(2700 if action=='main-run'else 450));D=M/arm;D.mkdir(exist_ok=True)
for suffix,text in [('stdout',r.stdout),('stderr',r.stderr),('exit',str(r.returncode)+'\n')]:
 with(D/(action+'-control.'+suffix)).open('x')as f:f.write(text)
assert r.returncode==0,r.stderr;v=json.loads(r.stdout)
if 'after_base64'in v:
 raw=base64.b64decode(v.pop('after_base64'));assert sha(raw)==v['after_H_sha256'];mirror(raw,sha(before))
if 'small_files'in v:
 for name,data in v.pop('small_files').items():assert Path(name).name==name;(D/name).write_bytes(base64.b64decode(data))
with(D/(action+'-control-receipt.json')).open('x')as f:json.dump(v,f,indent=2);f.write('\n')
print(json.dumps(v,indent=2))
