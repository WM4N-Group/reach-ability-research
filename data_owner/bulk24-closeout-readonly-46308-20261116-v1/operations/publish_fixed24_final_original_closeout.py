"""Publish fixed24 final original index and bounded cost ledger; no fitting/relabel/dispatch/H writes."""
from pathlib import Path
import json,hashlib,datetime,subprocess,shlex,base64
B=Path('/home/yuanyue/main/work/data-team');M=Path(__file__).resolve().parent;K=B/'manifests/bulk24-collector-46308-20261115-v1';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();pointer=json.loads((M/'latest-snapshot-pointer.json').read_bytes());source=M/pointer['file'];assert sha(source)==pointer['sha256'];v=json.loads(source.read_bytes());assert v['closed']==24 and v['zero_dispatches']==v['main_dispatches']==24 and v['batch_physically_and_metadata_closed']and v['all_fixed24_formal_originals_released']and v['formal_original_public_queries']==84 and v['closed_ledger_usage_all_known']and not v['inflight_or_future_costs_unknown_not_zero']and v['closed_resource_censored']==0
resource=json.loads((M/'fixed24-final-authority-resource-proof.json').read_bytes());assert resource['all24_H_closed_zero24_main24']and not resource['Data_runtime_worker_PIDs']and resource['local_H_mirror_matches_remote']
D=B/'consumer-deliveries/AINAV-DATA-BULK24-FIXED-COLLECTION-CLOSEOUT-NO-REFIT-20261116-v1';D.mkdir();rows=[]
for row in v['rows']:
 p=B/'consumer-deliveries'/('AINAV-DATA-BULK24-ORDINAL-%02d-ORIGINAL-ACTUAL-20261115-v1'%row['ordinal'])/'release.json';raw=p.read_bytes();r=json.loads(raw);assert sha(p)==row['formal_release_sha256'];assert r['actual_summary']['source_result_sha256']==row['actual_result_sha256']
 for name,pin in r['files'].items():
  q=Path(name);assert not q.is_absolute()and'..'not in q.parts and sha(p.parent/q)==pin
 rows.append(dict(ordinal=row['ordinal'],candidate_id=row['candidate_id'],scope_id=row['scope_id'],local_original_release=str(p),remote_original_release='/mnt/yuanyue/data-team/deployments/46308-20261114/workspace/consumer-deliveries/'+p.parent.name+'/release.json',release_sha256=sha(p),program_sha256=row['program_sha256'],actual_result_sha256=row['actual_result_sha256'],actual_chain_passed=row['source_result_passed'],source_error=row['source_error'],failure_class=row['failure_class'],public_query_count=row['formal_public_query_count'],first_CLIMB_PREPARE_query_present=row['first_CLIMB_PREPARE_present'],CLIMB_native_admitted=row['CLIMB_interaction_native_admitted'],literal_CLIMB_terminal_receipts=row['literal_CLIMB_terminal_receipts']))
files={}
for name,raw in [('fixed24-final-scalar-snapshot.json',source.read_bytes()),('fixed24-final-authority-resource-proof.json',(M/'fixed24-final-authority-resource-proof.json').read_bytes()),('original24-release-index.json',(json.dumps(dict(rows=rows),ensure_ascii=False,indent=2)+'\n').encode())]:
 p=D/name;p.write_bytes(raw);files[name]=sha(p)
policy=dict(purpose='FIXED_PREREGISTERED_HIGH_LEVEL_SUCCESSOR_CRITIC_TRAIN_COLLECTION_ORIGINALS',fit_allowed_by_closeout=False,current_critic_refit_allowed=False,whole_package_model_input_allowed=False,features_only_original_qualified_first_CLIMB_PREPARE_48slots=True,private_state_ID_future_or_unreached_outcome_not_features=True,raw_onboard_not_third_view_HD=True,raw_third_view_resolution_px=[192,128],four_geometries_eight_contexts_same_one_TRAIN_ancestor=True,independent_TEST_groups=0,V4_five_arm_or_whole_mission_success_not_claimed=True,no_VJEPA_WM_or_audit_repurpose=True,old_TRAIN6_frozen_model_CAL_VAL_not_changed=True,no_new_labels_or_features_derived_by_this_closeout=True,no_automatic_retry_or_new_batch_registration=True,old_driver_metadata_CAS_race_and_all_prior_failures_preserved=True,native_scope_ledgers_not_end_to_end_or_monetary_total=True,scope_highwater_sum_not_current_disk_usage=True)
p=D/'purpose-and-no-refit-boundary.json';p.write_text(json.dumps(policy,ensure_ascii=False,indent=2)+'\n');files[p.name]=sha(p)
summary={k:v[k]for k in ['fixed_registered_attempts','zero_dispatches','main_dispatches','closed','conditional_original_chain_PASS','closed_nonPASS','failure_class_counts','closed_resource_censored','formal_original_releases_count','formal_original_public_queries','CLIMB_first_PREPARE_query_present','CLIMB_native_admitted','closed_actual_main_commands','closed_actual_onboard_frames','closed_actual_review_frames','closed_actual_raw_third_view_frames','closed_ledger_usage_all_known','closed_only_scope_sim_s','closed_only_scope_wall_s','closed_scope_highwater_sum_not_current_disk_usage']}
release=dict(schema='Data-fixed24-original-collection-final-closeout-no-refit-v1',at=datetime.datetime.now().astimezone().isoformat(),source_H_sha256=v['source_H_sha256'],physical_and_H_all24_closed=True,formal_originals_all24_released=True,not_new_physical_scope_or_dispatch=True,summary=summary,fit_allowed=False,current_critic_refit_allowed=False,VJEPA_WM_purpose_granted=False,no_method_gain_or_independent_TEST_claim=True,files=files)
p=D/'release.json';p.write_text(json.dumps(release,ensure_ascii=False,indent=2)+'\n');payload={q.name:dict(sha256=sha(q),source=base64.b64encode(q.read_bytes()).decode())for q in D.iterdir()if q.is_file()}
code=r'''
from pathlib import Path
import json,sys,base64,hashlib
x=json.load(sys.stdin);B=Path('/mnt/yuanyue/data-team/deployments/46308-20261114/workspace');D=B/'consumer-deliveries'/x['name'];D.mkdir();h=json.loads((B/'registry/handoff_current_status_20261115.json').read_bytes());assert not h['active_bulk24_collector_scope']['active'];assert all(r['status']in('CLOSED_ACTUAL_MAIN_PASS','CLOSED_ACTUAL_MAIN_FAILED_NO_RETRY')for r in h['bulk24_collector_v1']['branches'].values())
for name,row in x['files'].items():
 assert Path(name).name==name;raw=base64.b64decode(row['source']);assert hashlib.sha256(raw).hexdigest()==row['sha256']
 with(D/name).open('xb')as f:f.write(raw)
index=json.loads((D/'original24-release-index.json').read_bytes())
for row in index['rows']:assert hashlib.sha256(Path(row['remote_original_release']).read_bytes()).hexdigest()==row['release_sha256']
print(json.dumps(dict(release_path=str(D/'release.json'),release_sha256=hashlib.sha256((D/'release.json').read_bytes()).hexdigest(),all24_original_release_SHA_verified=True,no_H_or_raw_source_or_physical_mutations=True)))
'''
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],input=json.dumps(dict(name=D.name,files=payload)),text=True,capture_output=True,timeout=90)
for suf,data in [('stdout',r.stdout),('stderr',r.stderr),('exit',str(r.returncode))]:
 with(M/('fixed24-final-release-transport.'+suf)).open('x')as f:f.write(data)
assert r.returncode==0,r.stderr;out=json.loads(r.stdout);assert out['release_sha256']==sha(D/'release.json')
with(M/'fixed24-final-original-release-proof.json').open('x')as f:json.dump(dict(local_release_path=str(D/'release.json'),**out),f,indent=2);f.write('\n')
print(json.dumps(dict(release_sha256=out['release_sha256'],summary=summary),ensure_ascii=False,indent=2))
