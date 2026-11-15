"""Publish source-revision component qualification + original CAL07, no physics."""
from pathlib import Path
import json,hashlib,shutil,base64,subprocess,shlex,sys,os,datetime
B=Path('/home/yuanyue/main/work/data-team');M=Path(__file__).resolve().parent;O=B/'manifests/new-critic-cohort-46308-20261115-v1';sys.path.insert(0,str(O));from mirror_H import mirror
sha=lambda b:hashlib.sha256(b).hexdigest();now=datetime.datetime.now().astimezone().isoformat();before=(B/'registry/handoff_46308_current_status_20261115.json').read_bytes();h=json.loads(before);q=h['active_T_COMPLEX_v2_camera_component_scope'];assert not q['active']and q['component_zero_dispatch_count']==1 and q['task_main_dispatch_count']==0;assert not h['active_new_critic_cohort_scope']['active'];V=json.loads((M/'close-control-receipt.json').read_bytes());r=V['result'];assert r['passed']and r['actual_task_steps']==0 and r['comparison_main_calls']==0 and r['actual_HD_frame']['frames']==1;D=B/'consumer-deliveries/AINAV-DATA-T-COMPLEX-01-V2-COMPONENT-PASS-20261115-v1';D.mkdir();members={}
for p in sorted((M/'actual-small').glob('*.json')):shutil.copy2(p,D/p.name);members[p.name]=sha(p.read_bytes())
for name in ['single-live-HD-world0-preview-proof.json','released-source-intake.json']:
 shutil.copy2(M/name,D/name);members[name]=sha((M/name).read_bytes())
release=dict(schema='Data-native-component-qualification-not-task-AB-v2',at=now,scope_id=r['scope_id'],source_owner_commit=r['source_owner_commit'],program_sha256=r['program_sha256'],authorization_sha256=r['authorization_sha256'],passed=True,component_zero_invocations=1,task_main_invocations=0,actual_task_steps=0,actual_task_sim_s=0.,actual_aux_sim_s=r['actual_auxiliary_calibration']['sim_seconds'],actual_wall_s=r['wall_s'],actual_worker_peak_RSS_bytes=r['peak_RSS_bytes'],peak_observed_own_GPU_bytes=r['peak_observed_own_GPU_bytes'],scope_output_bytes=V['ledger']['output_bytes'],usage_known=True,actual_model_sha256=r['actual_model_sha256'],actual_live_HD_frames=1,full_task_or_dynamic_plan_qualified=False,original_SupportedCapture_witness_complete=False,AB_mains=0,task_videos=0,old_failed_scope_or_result_modified=False,large_assets_and_raw_stay_remote=True,members_sha256=members)
(D/'release.json').write_text(json.dumps(release,ensure_ascii=False,indent=2)+'\n');pin=sha((D/'release.json').read_bytes());C=B/'consumer-deliveries/AINAV-DATA-NEW-CRITIC-46308-ORDINAL-07-ACTUAL-20261115-v1';cpin=sha((C/'release.json').read_bytes());assert cpin=='9249faef92810270bf192d7958b7254aabf76bff37639348931d7c2beb0884f5';cv=json.loads((C/'release.json').read_bytes());summary=cv['actual_summary'];assert summary['split']=='CALIBRATION'and summary['source_result_passed']and all(summary['nine_stream_checks'].values())
x=dict(owner=os.environ['CODEX_THREAD_ID'],expected=sha(before),release_sha256=pin,files={p.name:base64.b64encode(p.read_bytes()).decode()for p in D.glob('*.json')},CAL07_release_sha256=cpin,CAL07_condition=summary['condition_id'])
code=r'''
from pathlib import Path
import os,sys,json,base64,hashlib,fcntl,stat,tempfile,datetime
x=json.load(sys.stdin);R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114');B=R/'workspace';H=B/'registry/handoff_current_status_20261115.json';D=B/'consumer-deliveries/AINAV-DATA-T-COMPLEX-01-V2-COMPONENT-PASS-20261115-v1';C=B/'consumer-deliveries/AINAV-DATA-NEW-CRITIC-46308-ORDINAL-07-ACTUAL-20261115-v1';sha=lambda b:hashlib.sha256(b).hexdigest();now=lambda:datetime.datetime.now().astimezone().isoformat();assert sha((C/'release.json').read_bytes())==x['CAL07_release_sha256'];cv=json.loads((C/'release.json').read_bytes());assert cv['split']=='CALIBRATION'and cv['ordinal']==7
for name,pin in cv['files'].items():assert sha((C/name).read_bytes())==pin
D.mkdir()
for name,data in x['files'].items():
 assert Path(name).name==name
 with(D/name).open('xb')as f:f.write(base64.b64decode(data))
assert sha((D/'release.json').read_bytes())==x['release_sha256'];v=json.loads((D/'release.json').read_bytes())
for name,pin in v['members_sha256'].items():assert sha((D/name).read_bytes())==pin
active=[]
for p in Path('/proc').glob('[0-9]*'):
 try:args=[v.decode(errors='replace')for v in(p/'cmdline').read_bytes().split(b'\0')if v]
 except OSError:continue
 if any(v.startswith((str(R/'runtime')+'/',str(B/'workers')+'/'))for v in args):active.append(int(p.name))
assert not active
for gpu,inos in[(0,(3428729629,3428729630)),(1,(3428459217,3428459218))]:
 for kind,ino in zip(('physics','sdk'),inos):
  p=R/f'resource-locks/native-observer-{kind}-gpu{gpu}.lock';fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW)
  try:
   st=os.fstat(fd);assert(st.st_dev,st.st_ino)==(51,ino)and(p.stat().st_dev,p.stat().st_ino)==(51,ino);fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(fd,fcntl.LOCK_UN)
  finally:os.close(fd)
d=os.open(H.parent,os.O_RDONLY|os.O_DIRECTORY)
try:
 fcntl.flock(d,fcntl.LOCK_EX)
 with H.open('rb')as f:
  fcntl.flock(f,fcntl.LOCK_EX);before=f.read();st=os.fstat(f.fileno());assert sha(before)==x['expected']and(H.stat().st_dev,H.stat().st_ino)==(st.st_dev,st.st_ino);h=json.loads(before);saved=json.loads(before);assert h['executing_thread_id']==x['owner'];q=h['active_T_COMPLEX_v2_camera_component_scope'];co=h['new_critic_cohort_v1'];assert not q['active']and q['component_zero_dispatch_count']==1 and q['task_main_dispatch_count']==0 and q['actual_result_sha256']==sha((D/'result.json').read_bytes());assert not h['active_new_critic_cohort_scope']['active'];br=co['branches'][x['CAL07_condition']];assert br['status']=='CLOSED_ACTUAL_MAIN_PASS'and br['zero_dispatch_count']==br['main_dispatch_count']==1
  br['actual_public_delivery']=dict(release=str(C/'release.json'),release_sha256=x['CAL07_release_sha256'],data_role='CALIBRATION_ONLY_EVALUATE_SAME_FROZEN_MODEL_NO_REFIT',source_clocks_and_bytes_preserved=True);co['status']='CAL07_CLOSED_ORIGINALS_PUBLISHED_08_09_NOT_DISPATCHED_VAL_BLOCKED'
  h['T_COMPLEX_v2_component_zero_release']=dict(release=str(D/'release.json'),release_sha256=x['release_sha256'],component_passed=True,task_or_AB_qualified=False,own_zero_not_reusable_for_different_task_program=True,old_failed_component_scope_preserved=True)
  assert all(h[k]==val for k,val in saved.items()if k not in('new_critic_cohort_v1','updated_at'));h['updated_at']=now();after=(json.dumps(h,ensure_ascii=False,indent=2)+'\n').encode();fd,t=tempfile.mkstemp(prefix='.H-component-CAL07-publication-',dir=H.parent)
  try:
   with os.fdopen(fd,'wb')as out:out.write(after);out.flush();os.fchmod(out.fileno(),stat.S_IMODE(st.st_mode));os.fsync(out.fileno())
   assert H.read_bytes()==before;os.replace(t,H);os.fsync(d)
  finally:
   if os.path.exists(t):os.unlink(t)
finally:os.close(d)
proof=dict(at=now(),before_H_sha256=sha(before),after_H_sha256=sha(after),component_release_sha256=x['release_sha256'],CAL07_release_sha256=x['CAL07_release_sha256'],no_owned_native_processes=True,both_GPU_canonical_locks_free=True,all_phase_counts_old_closed_and_fit_pins_unchanged=True,publication_not_physical_dispatch=True)
with(B/'manifests/T-COMPLEX-01-v2-camera-components-46308-20261115-v1/component-and-CAL07-publication-CAS.json').open('x')as f:json.dump(proof,f,indent=2);f.write('\n')
print(json.dumps(dict(proof=proof,after_base64=base64.b64encode(after).decode())))
'''
rp=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],input=json.dumps(x),capture_output=True,text=True,timeout=120)
for suffix,text in [('stdout',rp.stdout),('stderr',rp.stderr),('exit',str(rp.returncode)+'\n')]:
 with(M/('combined-publication.'+suffix)).open('x')as f:f.write(text)
assert rp.returncode==0,rp.stderr;v=json.loads(rp.stdout);raw=base64.b64decode(v['after_base64']);assert sha(raw)==v['proof']['after_H_sha256'];mirror(raw,sha(before));(M/'component-and-CAL07-publication-CAS.json').write_text(json.dumps(v['proof'],indent=2)+'\n');print(json.dumps(v['proof'],indent=2))
