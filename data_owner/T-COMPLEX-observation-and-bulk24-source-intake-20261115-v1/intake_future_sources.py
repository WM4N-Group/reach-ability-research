"""Code-only future-source custody; no scope, native/NN test, model or dispatch."""
from pathlib import Path
import json,hashlib,base64,subprocess,shlex,datetime,collections
B=Path('/home/yuanyue/main/work/data-team');M=Path(__file__).resolve().parent;sha=lambda b:hashlib.sha256(b).hexdigest();H=B/'registry/handoff_46308_current_status_20261115.json';before=sha(H.read_bytes())
records={
'observation':Path('/home/yuanyue/main/work/ainav/manifests/T_COMPLEX_01_full_program_intake_20261115_v1/NEW_BOUNDED_OBSERVATION_QUALIFICATION_SOURCE_DEPLOYED_NOT_NATIVE_QUALIFIED.json'),
'bulk24':Path('/home/yuanyue/main/work/ainav/manifests/bulk_registered_geometry_source_20261115_v1/FINAL_TEN_GEOMETRY_SOURCE_AND_GOAL_FRAME_DEPLOYED_NOT_NATIVE_QUALIFIED.json')}
rows=[]
for kind,p in records.items():
 v=json.loads(p.read_bytes());d=M/kind;d.mkdir();(d/'SOURCE_OWNER_RECORD.json').write_bytes(p.read_bytes());root=v.get('remote_code_root');sub='development/complex_dual_route_v1'if kind=='observation'else'development/bulk_registered_conditions_v1';rows.append(dict(kind=kind,remote_root=root,sub=sub,expected=v['files_sha256'],source_commit=v.get('cloud_commit')))
code=r'''
from pathlib import Path
import json,sys,base64,hashlib
rows=json.load(sys.stdin);out={}
for row in rows:
 root=Path(row['remote_root'])/row['sub'];assert root.is_dir()
 for name,pin in row['expected'].items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==pin
 files={}
 for p in root.rglob('*'):
  if p.is_file()and p.suffix in('.py','.md','.json')and '__pycache__'not in p.parts:
   assert not p.is_symlink();raw=p.read_bytes();files[str(p.relative_to(root))]=dict(sha256=hashlib.sha256(raw).hexdigest(),data=base64.b64encode(raw).decode())
 out[row['kind']]=files
print(json.dumps(out))
'''
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],input=json.dumps(rows),capture_output=True,text=True,timeout=75);(M/'source-intake.stderr').write_text(r.stderr);assert r.returncode==0,r.stderr;out=json.loads(r.stdout);inventory={}
for kind,files in out.items():
 d=M/kind/'source';d.mkdir();pins={}
 for name,row in files.items():
  p=Path(name);assert not p.is_absolute()and '..'not in p.parts;p=d/p;p.parent.mkdir(parents=True,exist_ok=True);raw=base64.b64decode(row['data']);assert sha(raw)==row['sha256'];p.write_bytes(raw);pins[name]=row['sha256']
 (M/kind/'SOURCE_FILES_SHA256.json').write_text(json.dumps(pins,indent=2)+'\n');inventory[kind]=dict(source_commit=next(x['source_commit']for x in rows if x['kind']==kind),members=len(pins),source_owner_files_checked=True)
obs=json.loads((M/'observation/source/OBSERVABILITY_QUALIFICATION_SOURCE_REQUEST.json').read_bytes());assert obs['purpose']=='OBSERVABILITY_QUALIFICATION_ONLY'and obs['original_NAV_count']==2 and obs['PUSH_count']==0 and len(obs['fixed_boundaries'])==3 and obs['scope_id']is None and obs['program_sha256']is None and obs['current_B_not_modified_or_given_new_source']
p=Path('/home/yuanyue/reach-ability-research/protocols/2026-11-15/G2-bulk24-lane-width-new-purpose-v1/BULK24_COLLECTION_PROTOCOL.json');raw=p.read_bytes();assert sha(raw)=='0f9e0e03a4cdf8263b1c69f69db9697968040023f42d4c1f383a320631d9e57e';protocol=json.loads(raw);(M/'bulk24/BULK24_COLLECTION_PROTOCOL.json').write_bytes(raw);owner=json.loads((M/'bulk24/SOURCE_OWNER_RECORD.json').read_bytes());assert sha((M/'bulk24/SOURCE_OWNER_RECORD.json').read_bytes())==protocol['source_owner_record_sha256']and owner['cloud_commit']==protocol['source_owner_commit']and owner['files_sha256']==protocol['source_owner_files_sha256']
schedule=protocol['attempt_schedule'];assert len(schedule)==24 and len({r['attempt_key']for r in schedule})==24 and [r['ordinal']for r in schedule]==list(range(1,25));assert len({r['group_id']for r in schedule})==4 and len({r['condition_key']for r in schedule})==8 and len({r['scene_ancestry_key']for r in schedule})==1;assert all(r['scope_id']is None and r['physical_program_sha256']is None and r['own_zero_max']==r['main_max']==1 and r['split']=='TRAIN'for r in schedule);assert all(c==8 for c in collections.Counter(r['candidate_id']for r in schedule).values());assert protocol['dispatch']is False and protocol['physical_admission']is False and protocol['new_scopes_allocated']==0 and protocol['current_frozen_critic_refit_allowed']is False and protocol['old_TRAIN6_or_CAL_VAL_schedule_modified']is False
inventory['bulk24'].update(protocol_sha256=sha(raw),new_main_upper_bound=24,geometric_groups=4,contexts=8,existing_TRAIN_ancestries=1,current_model_refit_allowed=False)
assert sha(H.read_bytes())==before
proof=dict(at=datetime.datetime.now().astimezone().isoformat(),role='FUTURE_CODE_AND_PREREGISTRATION_INTAKE_NOT_NATIVE_OR_QUEUE',sources=inventory,original_B_program_unchanged=True,no_new_scope_or_program_freeze_or_lease=True,new_physical_zero_main_calls=0,old_counts_and_fit_and_H_unchanged=True,observation_study_must_not_use_existing_full_task_while_not_host_complete_loop=True,observation_source_cannot_replace_inflight_B=True,observation_visible_flag_not_PUSH_READY_or_task_success=True,bulk_remaining36_combinations_not_authorized_by_this24_protocol=True,capacity_not_reserved_for_future_full24=True,software_fixtures_not_rerun_or_counted_as_research=True)
(M/'FUTURE_SOURCES_RECEIVED_NOT_DISPATCHED.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n');print(json.dumps(proof,ensure_ascii=False,indent=2))
