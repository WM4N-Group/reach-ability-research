"""Verify delivered real r3 SDK artifacts only. Never executes SDK or inheritance."""
import datetime,hashlib,json
from pathlib import Path
OUT=Path(__file__).resolve().parent
RUNTIME=Path('/home/yuanyue/main/work/agent_team_runtime')
D=RUNTIME/'stage2_joint_gate_20261018/control_dev/s2_dev019_v001r3_sdk0env_delivery.json'
SRC=Path('/home/yuanyue/re-nav -piper-deploy/artifacts/go2-piper/sim2sim-current-20261008-a/wm07-old714-firststep-baseline-v001r3')
SHA='1fa50a30f008c00e7dde7199a86e283bf854f49e9bfe534fde6fde8295413a8a';ESHA='6eb394d66fc9c12510cc848b4de6653ea513774dd2a258bf82adab4cf6e79a44'
h=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();read=lambda p:json.loads(Path(p).read_text())
d=read(D);e=read(d['SDK_envelope']);directory=Path(d['SDK_envelope']).parent
assert d['actual_executed_source']=='v001r3' and d['source_manifest_sha256']==SHA
assert h(d['SDK_envelope'])==d['SDK_envelope_sha256']==ESHA
m=read(SRC/'package-manifest.json');assert h(SRC/'package-manifest.json')==SHA and all(h(SRC/n)==s for n,s in m['files_sha256'].items())
for name,key in [('SDK_original_result','result'),('SDK_original_log','log')]:assert d[name]==e[key]['path'] and h(d[name])==d[name+'_sha256']==e[key]['sha256']
r=read(e['result']['path']);log=Path(e['log']['path']).read_text();zero={'environments_created':0,'physics_steps':0,'actor_forwards':0,'actor_loads':0}
for value in (e,r):
 assert value['source_manifest_sha256']==SHA and value['success'] is True and value['actual_SDK_AppLauncher'] is True and value['AppLauncher_constructor_calls']==1 and value['counts']==zero and value['forbidden_attempts']==[]
assert e['process_returncode']==e['remote_exit_code']==int((directory/'SDK0env.exit-code.original.txt').read_text())==0 and e['error'] is None
embedded,_=json.JSONDecoder().raw_decode(log[log.index('{\n  "success": true,'):]);assert embedded==r
assert 'SDK0ENV=app_ready' in log and 'SDK0ENV=exact_config_prefix_PASS' in log
assert r['configuration_prefix_last_line']==313 and r['stopped_before_output_mkdir_line']==315 and r['original_main_not_executed'] is True
assert r['asset_count']==len(r['scene_assets'])==13
assert r['check_source_sha256']==m['files_sha256']['check_sdk0env.py'] and r['caller_sha256']==m['files_sha256']['source/run_piper_integrated_course_v2.py']
assert r['binding']['original_cfg_push_distance_m']==.60 and r['binding']['push_event_dx_m']==.50
command=(directory/'SDK0env.command.original.sh').read_text();assert 'wm07-old714-firststep-baseline-v001r3/check_sdk0env.py' in command
marker=read(directory/'SDK0env.started.json');assert marker['source_manifest_sha256']==SHA and marker['maximum_AppLauncher_constructors']==1 and marker['physical_source_start'] is False
em=read(d['evidence_manifest']);assert h(d['evidence_manifest'])==d['evidence_manifest_sha256']
assert all(h(directory/n)==v['sha256'] and (directory/n).stat().st_size==v['bytes'] for n,v in em['files'].items())
p=read(SRC/'protocol.json');root=Path(read(SRC/'paths.json')['remote_iy_train'])/'source/LeggedManip_Lab'
assert all(Path(origin).is_relative_to(root) for origin in r['module_origins'].values())
comp=read(directory/'completion.json');absence=read(directory/'formal-absence.final.json')
assert d['formal_source_deployed'] is False and d['formal_physical_starts']==0 and d['RUN_authorized'] is False
assert not Path(p['local_run_preparation']).exists() and not Path(p['main_authority']).exists()
ledger_rows=[]
for path in p['local_ledgers']:
 if Path(path).exists():ledger_rows += [json.loads(s) for s in Path(path).read_text().splitlines() if s.strip() and json.loads(s).get('source_id')==p['source_id']]
assert not ledger_rows
result={'schema':'rev018-dev019-real-r3-sdk-original-review-v1','at':datetime.datetime.now().astimezone().isoformat(),'source_manifest_sha256':SHA,'sdk_envelope_path':d['SDK_envelope'],'sdk_envelope_sha256':ESHA,'SDK_binding_accepted':True,'actual_executed_source':'v001r3','inheritance_used':False,'machine_gate_relaxed':False,'actual_AppLauncher_calls_this_permission':1,'counts':zero,'forbidden_attempts':[],'local_process_returncode':0,'remote_exit_code':0,'success_original_result':True,'original_result_sha256':e['result']['sha256'],'original_log_sha256':e['log']['sha256'],'log_embedded_JSON_equals_original_result':True,'configuration_prefix_last_line':313,'stop_before_output_mkdir_line':315,'original_main_not_executed':True,'scene_objects':13,'original_iy_module_origins':True,'old_cfg_point60_and_push_event_point50_retained':True,'evidence_manifest_members_verified':len(em['files']),'source_unchanged':True,'frozen_pending_metadata_not_rewritten_or_used_as_blocker':True,'source_ledger_events':0,'local_run_preparation_exists':False,'final_main_authority_exists':False,'source_acceptance_requires_separate_final_review':True,'reviewer_SDK_starts':0,'reviewer_physics_starts':0,'input_sha256':{str(p):h(p) for p in [D,Path(d['evidence_manifest']),*[directory/n for n in em['files']]]}}
(OUT/'new_sdk_originals_result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='input_sha256'},indent=2))
