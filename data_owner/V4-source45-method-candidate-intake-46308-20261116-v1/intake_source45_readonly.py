"""Consume exact candidate45 source bytes only. No import, fixtures, runtime or H change."""
from pathlib import Path
import json,hashlib,subprocess,shlex,base64,datetime,ast
M=Path(__file__).resolve().parent;B=M.parents[1];A=Path('/home/yuanyue/main/work/ainav/consumer-deliveries/AINAV-V4-FIVE-ARM-ASSET-E-RULE-AND-CLIMB-GAP-20261115-v1');sha=lambda raw:hashlib.sha256(raw).hexdigest();ptr=json.loads((A/'LATEST_SOURCE_RECORD.json').read_bytes());raw=(A/ptr['record']).read_bytes();assert sha(raw)==ptr['record_sha256'];x=json.loads(raw);assert x['cloud_commit']=='0270381f18b48951329c09f701cb7b755befdf52'and len(x['source_files_sha256'])==45
with(M/'source45-owner-record.original.json').open('xb')as f:f.write(raw)
old=json.loads((B/'manifests/V4-parallel-guard-bounded-native-46308-20261116-v1/PARALLEL_CURRENT_FULL_PATH_GUARD.original.json').read_bytes())
code=r'''
from pathlib import Path
import json,sys,hashlib,base64,datetime
x=json.load(sys.stdin);P=Path(x['remote_code_root'])/'development/complex_v4_four_arm_v1';H=Path('/mnt/yuanyue/data-team/deployments/46308-20261114/workspace/registry/handoff_current_status_20261115.json');before=H.read_bytes();h=json.loads(before);q=h['active_V4_parallel_guard_bounded_scope'];assert h['executing_thread_id']=='01a1d3aa-a0d5-7de0-b886-9d92ed5f1480'and q['active']and q['source_commit']=='2ab8b8aed166f74039db25e50fc7cabf1e0610cc';assert not h['active_V4_bounded_climb_nav_scope']['active']and not h['active_V4_bounded_climb_nav_v2_scope']['active'];files={}
for name,pin in x['source_files_sha256'].items():
 rel=Path(name);assert not rel.is_absolute()and'..'not in rel.parts;p=P/rel;assert not p.is_symlink();raw=p.read_bytes();assert len(raw)<128*1024 and hashlib.sha256(raw).hexdigest()==pin;files[name]=base64.b64encode(raw).decode()
assert H.read_bytes()==before
print(json.dumps(dict(at=datetime.datetime.now().astimezone().isoformat(),files=files,H_sha256=hashlib.sha256(before).hexdigest(),active_source41_program=q['whole_program_freeze_sha256'],active_source41_not_changed=True,no_H_or_source_mutation_or_import=True)))
'''
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],input=json.dumps(x),capture_output=True,text=True,timeout=60)
for suf,s in [('stderr',r.stderr),('exit',str(r.returncode))]:
 with(M/('intake.'+suf)).open('x')as f:f.write(s)
assert r.returncode==0,r.stderr;v=json.loads(r.stdout);rows=v.pop('files');P=M/'source-0270381f';P.mkdir();size=0
for name,b64 in rows.items():
 data=base64.b64decode(b64);assert sha(data)==x['source_files_sha256'][name];q=P/name;q.parent.mkdir(parents=True,exist_ok=True)
 with q.open('xb')as f:f.write(data)
 if q.suffix=='.py':ast.parse(data,filename=str(q))
 size+=len(data)
changed=[n for n,s in old['source_files_sha256'].items()if x['source_files_sha256'].get(n)!=s];added=sorted(set(x['source_files_sha256'])-set(old['source_files_sha256']));assert set(changed)=={'README_CN.md','factor_scope.py'}and added==['backbone_entry.py','method_entry.py','tests/test_backbone_entry.py','tests/test_method_entry.py'];assert all(x['source_files_sha256'][n]==old['source_files_sha256'][n]for n in ['parallel_alias_guard.py','live_driver.py','scene.json','execution_entry.py','task_terminal.py'])
v.update(role='EXACT45_CD_METHOD_COMPOSITION_SOURCE_INTAKE_ONLY_NOT_HOT_ADOPTION_OR_NATIVE_QUALIFICATION',at=datetime.datetime.now().astimezone().isoformat(),cloud_commit=x['cloud_commit'],owner_record_sha256=sha(raw),Data_verified45_local_and_remote_SHA=True,verified_members=45,local_copy_bytes=size,changed_from41=changed,added_from41=added,source_pins=x['source_files_sha256'],parent370_not_reaudited_or_qualified=True,source41_active_program_not_relabelled_as45=True,new_method_inputs_auth_API_WM_and_native_qualification_still_required=True,actual_backend_or_model_or_physics_imports_or_calls=0,source_owner_fixture_tests_not_repeated=True,new_registration_or_fit_or_J_purpose_grant=False)
assert sha((B/'registry/handoff_46308_current_status_20261115.json').read_bytes())==v['H_sha256']
with(M/'Data-source45-received-no-hot-adoption.json').open('x')as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps(dict(cloud_commit=x['cloud_commit'],verified_members=45,copy_bytes=size,changed=changed,added=added,no_native_or_hot_adoption=True),ensure_ascii=False,indent=2))
