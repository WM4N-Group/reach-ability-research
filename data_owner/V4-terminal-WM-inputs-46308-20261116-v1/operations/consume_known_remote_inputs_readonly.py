"""Targeted source/restore references only. No model restore/forward or native."""
from pathlib import Path
import json,hashlib,base64,subprocess,shlex,datetime
M=Path(__file__).resolve().parent;sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();rpath=Path('/home/yuanyue/reach-ability-research/operations/V4_ORIGINAL_WM_CPU_RESTORE_20261115.json');expected=sha(rpath);assert expected=='39c9a2f95f6325c5c1fa78b23a5093f38aa2671e4e74adeff92dcd8e9a41e246';report=json.loads(rpath.read_bytes());assert report['real_checkpoint_restores']==1 and report['actual_WM_prediction_forwards']==0
code=r'''
from pathlib import Path
import json,sys,hashlib,base64
x=json.load(sys.stdin);sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();commit='82a513b748b9c8eaec6d330e1dafb1aa57795f31';R=Path('/mnt/yuanyue/ainav-compute/code')/commit/'ainav/development/complex_v4_four_arm_v1';card=R/'SOURCE_PACKAGE_SHA256.json';pkg=json.loads(card.read_bytes());assert not pkg['source_native_qualified'] and pkg['physical_dispatches']==0
assert pkg['files_sha256']['elevated_terminal.py']=='aac30006cb0edbd0e63ae3b4f72948de90f0ae61dd6a75f6ea2f21dce5554242';files={}
for name,pin in pkg['files_sha256'].items():
 p=R/name;assert not p.is_symlink()and sha(p)==pin;files[name]=base64.b64encode(p.read_bytes()).decode()
q=Path('/mnt/yuanyue/reach-runs/V4-original7a6-CPU-restore-20261115-v1/ACTUAL_CPU_RESTORE.json');assert sha(q)==x['restore_report_sha256'];wm=json.loads(q.read_bytes());p=Path(wm['checkpoint_path']);assert not p.is_symlink()and p.stat().st_size==wm['checkpoint_bytes']==11314598 and sha(p)==wm['checkpoint_sha256']=='7a6ba61e89d824cd3e0a78f469a0925f91c784ab1f77ed4273365d6c313f569c'
assert wm['real_checkpoint_restores']==1 and wm['actual_WM_prediction_forwards']==0 and wm['actual_native_worlds_or_Actor_forwards']==0
print(json.dumps(dict(AINav_commit=commit,source_members=len(files),source_package_sha256=sha(card),all_source_SHA_verified=True,source_package=base64.b64encode(card.read_bytes()).decode(),source_files=files,WM_report=base64.b64encode(q.read_bytes()).decode(),WM_checkpoint_path=str(p),WM_checkpoint_sha256=sha(p),WM_checkpoint_bytes=p.stat().st_size,model_not_deserialized_or_restored_or_forwarded_by_Data=True,no_directory_search_or_environment_or_credentials_read=True,no_original_files_modified=True)))
'''
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],input=json.dumps(dict(restore_report_sha256=expected)),capture_output=True,text=True,timeout=60)
for suffix,text in [('stdout',r.stdout),('stderr',r.stderr),('exit',str(r.returncode)+'\n')]:
 with(M/('readonly-input-consumption.'+suffix)).open('x')as f:f.write(text)
assert r.returncode==0,r.stderr;v=json.loads(r.stdout);D=M/'AINav-immutable-82a513b7';D.mkdir()
for name,raw in v.pop('source_files').items():
 p=Path(name);assert not p.is_absolute()and'..'not in p.parts;p=D/p;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(base64.b64decode(raw))
(D/'SOURCE_PACKAGE_SHA256.json').write_bytes(base64.b64decode(v.pop('source_package')));(M/'Reach-ACTUAL_CPU_RESTORE.json').write_bytes(base64.b64decode(v.pop('WM_report')));assert sha(M/'Reach-ACTUAL_CPU_RESTORE.json')==expected;pkg=json.loads((D/'SOURCE_PACKAGE_SHA256.json').read_bytes());assert all(sha(D/name)==pin for name,pin in pkg['files_sha256'].items())
v.update(at=datetime.datetime.now().astimezone().isoformat(),role='DATA_INCREMENTAL_CODE_AND_EXISTING_WM_REFERENCE_INTAKE_NOT_NATIVE_ADMISSION',Reach_actual_restore_report_sha256=expected,Reach_restore1_not_Data_repeat_restore=True,Data_WM_forwards_API_world_compile_zero_main=0,WM_weight_not_downloaded=True,no_repeat_terminal_or_WM_software_tests=True,H_not_written=True,current_40cm_static_support_owner_caller_gap_not_solved_by_this_metadata=True)
with(M/'Data-consumed-inputs-proof.json').open('x')as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps(v,ensure_ascii=False,indent=2))
