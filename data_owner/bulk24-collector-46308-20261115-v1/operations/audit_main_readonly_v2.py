"""Closed B only: audit original recordings, no physics/model/Actor imports.
Independent from A audit: HD frame count derives from actual final physics tick;
installed/admitted/terminal outcome namespaces remain distinct.
"""
from pathlib import Path
import os,json,hashlib,importlib.util,time
import numpy as np
R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114');B=R/'workspace';C=os.environ['DATA_PREFIX_CONDITION'];W=B/'workers/bulk24-collector-46308-20261115-v1'
import sys
protocol=json.loads((W/'protocol.json').read_bytes());SCOPES=protocol['scopes']
ROOT=R/'runtime/workers'/SCOPES[C];S=ROOT/'main';M=B/'manifests/bulk24-collector-46308-20261115-v1'/C;start=time.monotonic()
assert os.environ.get('CUDA_VISIBLE_DEVICES')==''
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def check_file(base,row):
 p=base/row['path'];assert not p.is_symlink() and p.resolve().is_relative_to(base.resolve()) and sha(p)==row['sha256'];return p
v=read(S/'result.json');z=read(ROOT/'zero/result.json');ledger=read(ROOT/'accounting/ledger.json');assert len(ledger['rows'])==2 and all(r['closed'] for r in ledger['rows']);assert ledger['rows'][1]['report_sha256']==sha(S/'result.json')
episode=S/'episode';cl=read(episode/'closure.json');ix=read(episode/'index.json');assert cl['episode_sha256']==sha(episode/'episode.json') and cl['index_sha256']==sha(episode/'index.json')
source_before={str(p):sha(p) for p in [S/'result.json',S/'events.jsonl',ROOT/'zero/result.json',ROOT/'accounting/ledger.json',episode/'closure.json',episode/'index.json']}
issued=[];delayed=[];q=[];dq=[];raw=[];torque=[];times=[];ticks=[]
for row in ix['commands']:
 with np.load(check_file(episode,row),allow_pickle=False) as d:
  assert all(np.isfinite(d[k]).all() for k in d.files)
  issued.append(d['issued']);delayed.append(d['delayed']);q.append(d['q_before']);dq.append(d['dq_before']);raw.append(d['raw_torque']);torque.append(d['torque']);times.append(d['time_s']);ticks.append(d['physical_tick'])
if issued:
 issued,delayed,q,dq,raw,torque,times,ticks=[np.concatenate(x,axis=0) for x in [issued,delayed,q,dq,raw,torque,times,ticks]];n=len(ticks)
 assert np.array_equal(ticks,np.arange(1,n+1)) and np.allclose(times,ticks*.005,atol=1e-7,rtol=0) and issued.shape==(n,5,18)
 # Original source delay is4 native steps. Queue initialization repeats first
 # actually issued command5 times, not a fabricated zero history.
 expected=np.stack([issued[np.maximum(np.arange(n)-4,0),:,j] for j in range(18)],axis=2)
 delay_equal=np.array_equal(expected,delayed)
 calculated=delayed[:,2]*(delayed[:,0]-q)+delayed[:,3]*(delayed[:,1]-dq)+delayed[:,4]
 raw_error=float(np.max(abs(calculated-raw)))
 E=np.array([23.7,23.7,45.43]*4+[20.,20.,15.,7.,5.,5.]);clip_error=float(np.max(abs(np.clip(raw,-E,E)-torque)))
else:n=0;delay_equal=True;raw_error=clip_error=0.
visual_frames=0;actions_equal=True
for row in ix['visual']:
 with np.load(check_file(episode,row),allow_pickle=False) as d:
  ct=d['control_ticks'];assert np.array_equal(ct,np.arange(visual_frames,visual_frames+len(ct))*5)
  assert d['rgb'].dtype==np.uint8 and d['rgb'].shape[2:]==(128,192,3) and d['depth_m'].shape[2:]==(128,192,1)
  assert np.allclose(d['timestamps_s'][0],ct*.02,atol=1e-7,rtol=0)
  for j,t in enumerate(ct):
   assert bool(d['action_valid'][0,j])==(t>0)
   actions_equal &= np.array_equal(d['actions_previous'][0,j],issued[int(t)*4-1,0].astype(d['actions_previous'].dtype,copy=False) if t else np.zeros(18,dtype=d['actions_previous'].dtype))
  visual_frames+=len(ct)
review=S/'review-state';rc=read(review/'closure.json');assert rc['metadata_sha256']==sha(review/'metadata.json') and rc['model_sha256']==sha(rc['model_path']);review_frames=0
for row in rc['chunks']:
 with np.load(check_file(review,row),allow_pickle=False) as d:
  assert np.array_equal(d['control_ticks'],np.arange(review_frames,review_frames+len(d['control_ticks']))*5)
  assert np.isfinite(d['full_state']).all() and np.allclose(d['time_s'],d['control_ticks']*.02,atol=1e-7,rtol=0);review_frames+=len(d['time_s'])

# The optional older three-request bridge is intentionally NOT applied to this new source host.
journal_rows=[];last='0'*64
for line in(S/'events.jsonl').read_text().splitlines():
 row=json.loads(line);pin=row.pop('sha256');assert row['sequence']==len(journal_rows)and row['previous_sha256']==last and hashlib.sha256(json.dumps(row,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()).hexdigest()==pin;last=pin;journal_rows.append(row)
journal=dict(rows=len(journal_rows),last_sha256=last,valid=True);events=[r['payload']for r in journal_rows]
checks={'episode_storage_complete':cl['storage_complete'],'continuous_200Hz_commands':n==cl['physical_command_steps']==v['actual_recorded_commands']==round(v['actual_main_world_sim_s']/.005),'same_program_actual_zero_and_main_model':v['program_sha256']==z['program_sha256']and v['actual_model_numeric_sha256']==z['actual_model_numeric_sha256'],'original_delay_FIFO_exact':delay_equal,'PD_raw_torque_reproduced':raw_error<1e-10,'hard_clip_reproduced':clip_error<1e-10,'visual_actions_previous_matches_actual_issue':bool(actions_equal),'visual_and_review_grid_complete':visual_frames==review_frames==cl['observations'],'no_teardown_errors':not v['close_errors']}
rawbase=S/'raw-third-view';rawclose=read(rawbase/'closure.json');camera=read(W/'third-view-camera.json');metadata=read(rawbase/'metadata.json');assert metadata['camera_spec']==camera;count=0
for row in rawclose['chunks']:
 with np.load(check_file(rawbase,row),allow_pickle=False)as d:
  assert d['rgb'].dtype==np.uint8 and d['rgb'].shape[1:]==(camera['height'],camera['width'],3)and np.array_equal(d['physics_tick'],np.arange(count,count+len(d['rgb']))*20)and np.allclose(d['actual_sim_time_s'],d['physics_tick']*.005,atol=1e-7,rtol=0);assert hashlib.sha256(d['rgb'].tobytes()).hexdigest()==row['raw_RGB_bytes_sha256'];count+=len(d['rgb'])
assert count==rawclose['archived_frames']==n//20+1 and rawclose['complete_for_capture_grid']and rawclose['origin']=='DIRECT_CURRENT_LIVE_MUJOCO_RGB'
unchanged=all(sha(p)==pin for p,pin in source_before.items());assert unchanged and all(checks.values())
report=dict(schema='Data-bulk24-closed-original-chain-stream-audit-camera-metadata-bound-v2',passed=True,source_result_passed=v['passed'],source_result_sha256=sha(S/'result.json'),checks=checks,actual_commands=n,visual_frames=visual_frames,review_frames=review_frames,direct_raw_frames=count,direct_raw_resolution_px=[camera["width"],camera["height"]],HD_not_claimed=True,raw_video_grid_complete=True,journal_chain=journal,actual_capture_events=[e for e in events if e.get('event')=='complex_actual_cold_capture_completed'],actual_semantic_intent_selections=[e for e in events if e.get('event')=='skill_intent_selected'],literal_native_option_installed_event_count=sum(e.get('event')=='native_option_installed'for e in events),actual_native_admissions=[e for e in events if e.get('event')=='ainav_native_admitted'],actual_native_terminal_receipts=[e for e in events if e.get('event')=='ainav_native_receipt' and e['receipt']['status'] in ('succeeded','failed','hard_stop','budget_expired')],actual_intent_native_outcomes=[e for e in events if e.get('event')=='intent_actual_native_outcome'],literal_NAV_actor_forward_event_count=sum(e.get('event')=='registered_NAV_actual_actor_forward'for e in events),actual_public_bundles=sum(e.get('event')=='reach_complex_public_decision'for e in events),source_resource_censored=v.get('resource_censored',False),source_error=v.get('error'),resource_censor_not_method_failure=True,recorder_censored_not_resource_class=True,actual_task_placement_completions=sum(e.get('event')=='completed_placement_boundary_latched'for e in events),max_raw_torque_reproduction_error=raw_error,max_hard_clip_reproduction_error=clip_error,source_sha_before_after_identical=unchanged,no_new_model_Runtime_Actor_Renderer_or_physics_calls=True,task_success_inferred=False,new_preregistered_collection_evidence=True,not_current_critic_refit_permission=True)
# Recheck literal semantic request/outcome/result correlation from ORIGINAL events.
requests=[(i,e)for i,e in enumerate(events)if e.get('event')=='explicit_engineering_intent_requested'];outcomes=[(i,e)for i,e in enumerate(events)if e.get('event')=='intent_actual_native_outcome'and e.get('execution_role')=='interaction'];results=[(i,e)for i,e in enumerate(events)if e.get('event')=='engineering_intent_actual_result']
if v['passed']:
 assert len(requests)==len(outcomes)==len(results)==3 and len(v['selected_requests'])==3 and [r['skill']for r in v['selected_requests']]==['NAV','PUSH','CLIMB']
 last=-1
 for k,((ri,req),(oi,out),(ei,res),expected)in enumerate(zip(requests,outcomes,results,v['selected_requests'])):
  assert last<ri<oi<ei and req['request_index']==k and req['request']==expected
  receipt=out['receipt'];assert req['intent_sha256']==out['intent_sha256']==res['intent_sha256']and res['native_option_sha256']==out['native_option_sha256']==receipt['option_sha256']
  assert receipt['status']==res['actual_status']=='succeeded'and out['intent_succeeded']and receipt['evidence_ref']==res['receipt_ref']and res['binding_ref'];last=ei
 report['exact3_original_semantic_receipt_correlations_rechecked']=True
 report['exact3_is_NAV_PUSH_CLIMB_not3_planning_decisions_or_full_mission']=True
with(M/'actual-main-cold-audit-v2.json').open('x')as f:json.dump(report,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps(report,ensure_ascii=False))
