"""Publish already produced static model proof only; no render/model/physics call or retry."""
from pathlib import Path
import json,subprocess,shlex,hashlib,base64,datetime
M=Path(__file__).resolve().parent;B=M.parents[1];sha=lambda raw:hashlib.sha256(raw).hexdigest()
code=r'''
from pathlib import Path
import json,sys,hashlib,base64,datetime
B=Path('/mnt/yuanyue/data-team/deployments/46308-20261114/workspace');N='V4-common-palette-bounded-native-46308-20261116-v2';M=B/'manifests'/N;W=B/'workers'/N;H=B/'registry/handoff_current_status_20261115.json';before=H.read_bytes();h=json.loads(before);q=h['active_V4_palette_bounded_v2_scope'];assert q['active']and q['component_zero_dispatch_count']==1 and q['task_main_dispatch_count']==0 and not h['active_V4_palette_bounded_scope']['active'];S=B.parent/'runtime/workers'/q['scope_id'];assert not(S/'result.json').exists()
files={}
for p in [S/'new-common-appearance-static-delta-proof.json',S/'claim.json',S/'resource-lease.json',W/'protocol.json',W/'inputs/ainav/development/complex_v4_four_arm_v1/COMMON_APPEARANCE_REVISION.json',M/'program-freeze.json']:
 raw=p.read_bytes();assert len(raw)<256*1024;files[p.name]=raw
proof=json.loads(files['new-common-appearance-static-delta-proof.json']);revision=proof['common_appearance_revision'];delta=revision['compiled_render_only_delta_proof'];assert proof['actual_main_steps']==proof['Actor_forwards']==0 and delta['only_changed_array']=='geom_rgba'and len(delta['only_changed_rows'])==3 and delta['unchanged_nonRGBA_array_count']==398 and delta['engine_options_unchanged']and delta['topology_names_paths_unchanged'];assert H.read_bytes()==before
D=B/'consumer-deliveries/AINAV-DATA-PALETTE-V2-STATIC-DELTA-PASS-NATIVE-INFLIGHT-20261116-v1';D.mkdir()
for name,raw in files.items():
 with(D/name).open('xb')as f:f.write(raw)
release=dict(schema='Data-new-common-palette-static-model-proof-subset-inflight-not-task-v1',at=datetime.datetime.now().astimezone().isoformat(),scope_id=q['scope_id'],program_sha256=q['whole_program_freeze_sha256'],source_commit=q['source_commit'],static_asset_delta_passed=True,actual_new_MJB_sha256=proof['model_sha256'],appearance_revision_id=revision['revision_id'],appearance_contract_sha256=revision['contract_sha256'],original_static_reference_sha256=revision['reference_static_MJB_sha256'],all398_nonRGBA_arrays_engine_options_topology_names_paths_identical=True,only_three_geom_RGBA_rows_changed=delta['only_changed_rows'],new_environment_not_old_brown_same_arm_comparison=True,future_five_arms_must_use_same_new_asset_if_adopted=True,component_still_inflight_not_native_or_task_qualified=True,full_component_result_or_ledger_not_available=True,component_zero_dispatches=1,five_arm_main_calls=0,same_scope_subset_no_new_physical_sample_or_invocation=True,no_first_WM_forward_or_J_purpose_grant=True,whole_artifact_model_input_allowed=False,training_allowed=False,files={name:hashlib.sha256(raw).hexdigest()for name,raw in files.items()})
(D/'release.json').write_text(json.dumps(release,ensure_ascii=False,indent=2)+'\n');print(json.dumps(dict(release_path=str(D/'release.json'),release_sha256=hashlib.sha256((D/'release.json').read_bytes()).hexdigest(),new_MJB_sha256=proof['model_sha256'],static_nonRGBA398_proof=True,H_sha256=hashlib.sha256(before).hexdigest(),small_files={p.name:base64.b64encode(p.read_bytes()).decode()for p in D.iterdir()if p.is_file()})))
'''
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],capture_output=True,text=True,timeout=60)
for suf,data in [('stdout',r.stdout),('stderr',r.stderr),('exit',str(r.returncode))]:
 with(M/('static-subset.'+suf)).open('x')as f:f.write(data)
assert r.returncode==0,r.stderr;x=json.loads(r.stdout);D=B/'consumer-deliveries'/Path(x['release_path']).parent.name;D.mkdir()
for name,b64 in x.pop('small_files').items():
 assert Path(name).name==name
 with(D/name).open('xb')as f:f.write(base64.b64decode(b64))
assert sha((D/'release.json').read_bytes())==x['release_sha256'];release=json.loads((D/'release.json').read_bytes());assert all(sha((D/n).read_bytes())==p for n,p in release['files'].items());assert x['H_sha256']==sha((B/'registry/handoff_46308_current_status_20261115.json').read_bytes())
with(M/'static-asset-subset-publication-proof.json').open('x')as f:json.dump(dict(local_release_path=str(D/'release.json'),**x),f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps(x,ensure_ascii=False,indent=2))
