"""New v6 configuration/freeze builder ONLY; never starts physics or edits old files."""
from pathlib import Path
import json,hashlib,os,shutil,datetime,subprocess
R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114');B=R/'workspace';G=R/'code/reach-ability-research';SRC=G/'data_owner/PERF-01-NAV2000-20261117-v6';G1=G/'data_owner/PERF-01-NAV2000-20261116-v1'
WORKER_SOURCE=SRC/'worker'
N='perf-NAV2000-indexed-46308-20261117-v6';W=B/'workers'/N;M=B/'manifests'/N;W1=B/'workers/perf-NAV2000-indexed-46308-20261116-v1';M1=B/'manifests/perf-NAV2000-indexed-46308-20261116-v1'
SCOPE='data-46308-perf-NAV2000-indexed-20261117-v6';A=B/'registry/PERF01_NAV2000_INDEXED_AUTHORITY_20261117_v6.json';OWNER='01a1e4e1-3037-7333-9019-a3f37effe5da';PLAN='1664ef3ad2f1df6b6cca9ea71fa18ac874dc4a1142e9a5f1d6106657d6afd1de';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();now=datetime.datetime.now().astimezone().isoformat()
assert not W.exists()and not M.exists()and not A.exists();assert sha(M1/'program-freeze.json')=='cbc751e43b257e291ddc8fa46073d567e7c53bb704b951fece30c83df786fc04'
h=json.loads((B/'registry/handoff_current_status_20261115.json').read_bytes());assert h['executing_thread_id']==OWNER and not any(v.get('active')for v in h.values()if isinstance(v,dict))
assert not subprocess.check_output(['git','-C',str(G),'status','--porcelain','-uall'],text=True)
W.mkdir();M.mkdir();shutil.copytree(G1/'policy',W/'policy');shutil.copytree(WORKER_SOURCE,W/'worker');shutil.copyfile(W1/'worker/private_catalog_boundary.py',W/'worker/private_catalog_boundary.py');shutil.copytree(W1/'guard',W/'guard');shutil.copytree(SRC/'operations',M/'operations')
for p in (SRC/'worker').iterdir():
 if p.is_file():shutil.copyfile(p,W/'worker'/p.name)
c=json.loads((W1/'protocol.json').read_bytes());c.update(scope_id=SCOPE,authority_key='active_PERF01_NAV2000_indexed_v6_scope',authorization=str(A),freeze_path=str(M/'program-freeze.json'),Data_code_commit=subprocess.check_output(['git','-C',str(G),'rev-parse','HEAD'],text=True).strip(),plan_sha256=PLAN)
c['import_paths']=[s.replace(str(W1),str(W))for s in c['import_paths']]
c['program_cwd']=str(W)
c['partial_constructor_overlay']=True
c['partial_base_source']=str(Path(c['scene_path']).parent.parent/'complex_dual_route_v1/native_construction.py')
c['partial_base_sha256']='6c3ee245cd54bfeeec0c64a53627ec2efbebba34775afcac7aab794a286b18cf'
assert sha(c['partial_base_source'])==c['partial_base_sha256']
c['probe_timing_is_diagnostic_not_owner_stamp']=True
c['ResourceWatch_oldest_max_age_s_unchanged']=2.0
c['PIL_preinit_required']=True
PIL_PROOF=json.loads((WORKER_SOURCE/'PIL-preinit-CPU-proof.json').read_bytes());assert PIL_PROOF['strict_code_events_after_preinit']==[]
c['PIL_preinit_sources_sha256']=PIL_PROOF['files_sha256'];assert all(sha(p)==v for p,v in c['PIL_preinit_sources_sha256'].items())
c['inventory_roots'].append('/mnt/yuanyue/envs/piper-zyh-mujoco-340d7d8-v1/lib/python3.11/site-packages')
c['explicit_missing_module_paths']=[str(W/'_ops.py'),str(W/'_classes.py')]
PATH_PINS={'/mnt/yuanyue/data-team/env-native-v1/lib/python3.11/site-packages/frozen-native-dependencies.pth':'1559afc8495d2d97eaac4c732beba5161cd77517d684429a5caa77cb27d227e9','/mnt/yuanyue/envs/go2-isaac/lib/python3.11/site-packages/torch/_ops.py':'7e88a7ec282d5d445969d0d00afc7b3ce23ceacc88935a96d52e952f3719e8a4','/mnt/yuanyue/envs/go2-isaac/lib/python3.11/site-packages/torch/_classes.py':'2a3dd93d72e9f19450670b89f3a57b5b5adf245709f6a49a551bbfad33c434bf'}
assert all(sha(p)==pin for p,pin in PATH_PINS.items())
c['inventory_root_provenance']=dict(actual_original_package_path_pins=PATH_PINS,synthetic_slots=c['explicit_missing_module_paths'],never_create_synthetic_files=True,new_policy_does_not_disable_SHA_or_guard=True)
NAV_PROOF=json.loads((SRC/'worker/NAV-helper-CPU-intake.json').read_bytes());assert NAV_PROOF['CPU_import_succeeded']and NAV_PROOF['CUDA_initialized']is False and not NAV_PROOF['watched_native_constructor_loader_forward_step_calls']
c['reviewed_preload_modules']=list(dict.fromkeys(c['reviewed_preload_modules']+NAV_PROOF['preload_modules']))
c['NAV_helper_preload_revision']=dict(modules=NAV_PROOF['preload_modules'],source_files_sha256=NAV_PROOF['source_files_sha256'],CPU_evidence_sha256=sha(SRC/'worker/NAV-helper-CPU-intake.json'),unchanged_v4_worker_source_reused=False,only_existing_configuration_preload_list_changed=False,original_physical_loop_and_guard_source_preserved=True)
assert all(sha(p)==v for p,v in NAV_PROOF['source_files_sha256'].items())


c['camera_spec']=h['active_E20_prearrival40_v3_scope']['camera_spec'];assert c['camera_spec']['lookat']==[7.5,0.,.4]and c['camera_spec']['distance']==20.
assert hashlib.sha256(json.dumps(c['camera_spec'],sort_keys=True,separators=(',',':')).encode()).hexdigest()==h['active_E20_prearrival40_v3_scope']['camera_sha256']
D=R/'runtime/diagnostics/data-46308-PERF01-deleted-map-GPU-library-diagnostic-20261116-v1/result.json';assert sha(D)=='4196731445a874df09644bb0da117eb32eb70d85eaba2bd8e4c7bee30cdb2a09'
d=json.loads(D.read_bytes());assert d['passed']and d['Runtime_Actor_model_restore_forward_Renderer_MjModel_MjData_physics_calls']==0
c['gl_mapping_evidence_path']=str(D);c['gl_runtime_mapping_policy']=dict(kind='OBSERVED_EGL_MEMFD_RX_8192_PINNED_DRIVER_BOOTSTRAP_V1',name='/memfd:/.glXXXXXX (deleted)',evidence_result_sha256=sha(D),driver_files_sha256={row['path']:row['sha256']for row in d['loaded_driver_file_identity']})
c['resource_binding_historical_owner_not_current_authority']='01a1d3aa-a0d5-7de0-b886-9d92ed5f1480';c['actual_scope_owner']=OWNER
# Reuse unchanged exact closure pins; actual prepare hashes every listed file.
# No full environment sweep, asset download, old native run, or binding mutation.
files={p:pin for p,pin in json.loads((M1/'program-freeze.json').read_bytes())['files'].items()if not p.startswith(str(W1)+'/')and p!=str(B/'registry/PERF01_NAV2000_INDEXED_AUTHORITY_20261116_v1.json')}
assert files.get(c['partial_base_source'])==c['partial_base_sha256']
files.update(NAV_PROOF['source_files_sha256']);files.update(c['PIL_preinit_sources_sha256']);files.update(PATH_PINS);files[str(D)]=sha(D);files.update(c['gl_runtime_mapping_policy']['driver_files_sha256'])
for p in [*W.rglob('*'),*(M/'operations').rglob('*')]:
 if p.is_file():files[str(p)]=sha(p)
c['frozen_inventory_paths']=list(files);(W/'protocol.json').write_text(json.dumps(c,ensure_ascii=False,indent=2)+'\n');files[str(W/'protocol.json')]=sha(W/'protocol.json')
a=dict(at=now,owner=OWNER,scope_id=SCOPE,question=c['question'],plan_sha256=PLAN,own_zero_max=1,main_max=1,automatic_retry=False,old_closed_scopes_not_reopened=True,NAV_only_preissue_rejects_PUSH_CLIMB=True,main_task_command_cap=2000,main_task_sim_cap_s=10.,zero_wall_cap_s=300.,main_wall_cap_s=1200.,output_cap_bytes=1<<30,owned_limit_bytes=40*1024**3,reference_seed_unknown_not_fabricated=True,extra_reference_baseline_not_authorized_implicitly=True,training_allowed=False,physical_GPU=0,GPU_UUID=c['GPU_UUID'],gl_runtime_mapping_policy=c['gl_runtime_mapping_policy'],runtime_generated_RX_bootstrap_trust_not_named_file_signature=True,no_root_or_arbitrary_native_memory_protection_claim=True,NAV_helper_preload_revision=c['NAV_helper_preload_revision'],bounded_probe_attribution_and_partial_constructor_qualification=True,partial_constructor_overlay=True,exact_two_private_AST_receipt_sites_changed=True,old_v5_UNKNOWN_not_backfilled=True,resource_oldest_pair_1s_2s_unchanged=True,PIL_preinit_before_seal_both_phases=True,PIL_preinit_sources_sha256=c['PIL_preinit_sources_sha256'],no_further_automatic_native_retry=True,inventory_root_provenance=c['inventory_root_provenance'],specific_revision='one original lease composite with per-stage immutable timing plus two explicit partial Runtime/Observer handoff callbacks in a private constructor; original outer postchecks/control/guard/freshness preserved; v5 closed untouched')
A.write_text(json.dumps(a,ensure_ascii=False,indent=2)+'\n');files[str(A)]=sha(A)
freeze=dict(schema='PERF01-independent-new-program-freeze-v6',at=now,scope_id=SCOPE,question=c['question'],authorization_sha256=sha(A),files=files)
(M/'program-freeze.json').write_text(json.dumps(freeze,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(at=now,scope_id=SCOPE,worker_root=str(W),manifest_root=str(M),authorization=str(A),authorization_sha256=sha(A),program_sha256=sha(M/'program-freeze.json'),files=len(files),new_runtime_not_created=not(R/'runtime/workers'/SCOPE).exists(),native_calls=0,Data_code_commit=c['Data_code_commit'])))
