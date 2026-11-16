"""New v2 configuration/freeze builder ONLY; never starts physics or edits old files."""
from pathlib import Path
import json,hashlib,os,shutil,datetime,subprocess
R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114');B=R/'workspace';G=R/'code/reach-ability-research';SRC=G/'data_owner/PERF-01-NAV2000-20261116-v2';G1=G/'data_owner/PERF-01-NAV2000-20261116-v1'
N='perf-NAV2000-indexed-46308-20261116-v2';W=B/'workers'/N;M=B/'manifests'/N;W1=B/'workers/perf-NAV2000-indexed-46308-20261116-v1';M1=B/'manifests/perf-NAV2000-indexed-46308-20261116-v1'
SCOPE='data-46308-perf-NAV2000-indexed-20261116-v2';A=B/'registry/PERF01_NAV2000_INDEXED_AUTHORITY_20261116_v2.json';OWNER='01a1e4e1-3037-7333-9019-a3f37effe5da';PLAN='c7cd77abebfcc33808389ec211284b46802a23de02ddb4ee6e6158cf805ea2e7';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();now=datetime.datetime.now().astimezone().isoformat()
assert not W.exists()and not M.exists()and not A.exists();assert sha(M1/'program-freeze.json')=='cbc751e43b257e291ddc8fa46073d567e7c53bb704b951fece30c83df786fc04'
h=json.loads((B/'registry/handoff_current_status_20261115.json').read_bytes());assert h['executing_thread_id']==OWNER and not any(v.get('active')for v in h.values()if isinstance(v,dict))
assert not subprocess.check_output(['git','-C',str(G),'status','--porcelain','-uall'],text=True)
W.mkdir();M.mkdir();shutil.copytree(G1/'policy',W/'policy');shutil.copytree(SRC/'worker',W/'worker');shutil.copyfile(W1/'worker/private_catalog_boundary.py',W/'worker/private_catalog_boundary.py');shutil.copytree(W1/'guard',W/'guard');shutil.copytree(SRC/'operations',M/'operations')
c=json.loads((W1/'protocol.json').read_bytes());c.update(scope_id=SCOPE,authority_key='active_PERF01_NAV2000_indexed_v2_scope',authorization=str(A),freeze_path=str(M/'program-freeze.json'),Data_code_commit=subprocess.check_output(['git','-C',str(G),'rev-parse','HEAD'],text=True).strip(),plan_sha256=PLAN)
c['import_paths']=[s.replace(str(W1),str(W))for s in c['import_paths']]
c['camera_spec']=h['active_E20_prearrival40_v3_scope']['camera_spec'];assert c['camera_spec']['lookat']==[7.5,0.,.4]and c['camera_spec']['distance']==20.
assert hashlib.sha256(json.dumps(c['camera_spec'],sort_keys=True,separators=(',',':')).encode()).hexdigest()==h['active_E20_prearrival40_v3_scope']['camera_sha256']
D=R/'runtime/diagnostics/data-46308-PERF01-deleted-map-GPU-library-diagnostic-20261116-v1/result.json';assert sha(D)=='4196731445a874df09644bb0da117eb32eb70d85eaba2bd8e4c7bee30cdb2a09'
d=json.loads(D.read_bytes());assert d['passed']and d['Runtime_Actor_model_restore_forward_Renderer_MjModel_MjData_physics_calls']==0
c['gl_mapping_evidence_path']=str(D);c['gl_runtime_mapping_policy']=dict(kind='OBSERVED_EGL_MEMFD_RX_8192_PINNED_DRIVER_BOOTSTRAP_V1',name='/memfd:/.glXXXXXX (deleted)',evidence_result_sha256=sha(D),driver_files_sha256={row['path']:row['sha256']for row in d['loaded_driver_file_identity']})
c['resource_binding_historical_owner_not_current_authority']='01a1d3aa-a0d5-7de0-b886-9d92ed5f1480';c['actual_scope_owner']=OWNER
# Reuse unchanged exact closure pins; actual prepare hashes every listed file.
# No full environment sweep, asset download, old native run, or binding mutation.
files={p:pin for p,pin in json.loads((M1/'program-freeze.json').read_bytes())['files'].items()if not p.startswith(str(W1)+'/')and p!=str(B/'registry/PERF01_NAV2000_INDEXED_AUTHORITY_20261116_v1.json')}
files[str(D)]=sha(D);files.update(c['gl_runtime_mapping_policy']['driver_files_sha256'])
for p in [*W.rglob('*'),*(M/'operations').rglob('*')]:
 if p.is_file():files[str(p)]=sha(p)
c['frozen_inventory_paths']=list(files);(W/'protocol.json').write_text(json.dumps(c,ensure_ascii=False,indent=2)+'\n');files[str(W/'protocol.json')]=sha(W/'protocol.json')
a=dict(at=now,owner=OWNER,scope_id=SCOPE,question=c['question'],plan_sha256=PLAN,own_zero_max=1,main_max=1,automatic_retry=False,old_closed_scopes_not_reopened=True,NAV_only_preissue_rejects_PUSH_CLIMB=True,main_task_command_cap=2000,main_task_sim_cap_s=10.,zero_wall_cap_s=300.,main_wall_cap_s=1200.,output_cap_bytes=1<<30,owned_limit_bytes=40*1024**3,reference_seed_unknown_not_fabricated=True,extra_reference_baseline_not_authorized_implicitly=True,training_allowed=False,physical_GPU=0,GPU_UUID=c['GPU_UUID'],gl_runtime_mapping_policy=c['gl_runtime_mapping_policy'],runtime_generated_RX_bootstrap_trust_not_named_file_signature=True,no_root_or_arbitrary_native_memory_protection_claim=True,specific_revision='evidenced strict EGL8KiB exception + original RGBD task0 no-step warm + actual original final camera + new real owner authority; not changed ID only')
A.write_text(json.dumps(a,ensure_ascii=False,indent=2)+'\n');files[str(A)]=sha(A)
freeze=dict(schema='PERF01-independent-new-program-freeze-v2',at=now,scope_id=SCOPE,question=c['question'],authorization_sha256=sha(A),files=files)
(M/'program-freeze.json').write_text(json.dumps(freeze,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(at=now,scope_id=SCOPE,worker_root=str(W),manifest_root=str(M),authorization=str(A),authorization_sha256=sha(A),program_sha256=sha(M/'program-freeze.json'),files=len(files),new_runtime_not_created=not(R/'runtime/workers'/SCOPE).exists(),native_calls=0,Data_code_commit=c['Data_code_commit'])))
