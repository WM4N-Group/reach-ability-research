"""Completed fixed three-view observation study: numpy/JSON-only original audit."""
from pathlib import Path
import os,json,hashlib,importlib.util,time
import numpy as np
R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114');B=R/'workspace';C='OBS';W=B/'workers/T-COMPLEX-observability-study-46308-20261115-v1'
import sys
protocol=json.loads((W/'protocol.json').read_bytes());SCOPES={a:r['scope_id']for a,r in protocol['arms'].items()}
ROOT=R/'runtime/workers'/SCOPES[C];S=ROOT/'main';M=B/'manifests/T-COMPLEX-observability-study-46308-20261115-v1'/C;start=time.monotonic()
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
rawbase=S/'raw-third-view';rawclose=read(rawbase/'closure.json');camera=read(S/'actual-config.json')['camera'];selection=read(W/'inputs/scene/SOURCE_SELECTION_V2.json');scene_path=W/'inputs/scene'/selection['scene_file'];assert sha(scene_path)==selection['scene_sha256']==protocol['scene_sha256'];scene=read(scene_path)['third_view'];assert camera==dict(kind='fixed_free',width=scene['width'],height=scene['height'],stride_physics_ticks=20,chunk_frames=10,max_bytes=1024**3,lookat=scene['lookat'],distance=scene['distance'],azimuth=scene['azimuth'],elevation=scene['elevation']);metadata=read(rawbase/'metadata.json');assert metadata['camera_spec']==camera;count=0
for row in rawclose['chunks']:
 with np.load(check_file(rawbase,row),allow_pickle=False)as d:
  assert d['rgb'].dtype==np.uint8 and d['rgb'].shape[1:]==(camera['height'],camera['width'],3)and np.array_equal(d['physics_tick'],np.arange(count,count+len(d['rgb']))*20)and np.allclose(d['actual_sim_time_s'],d['physics_tick']*.005,atol=1e-7,rtol=0);assert hashlib.sha256(d['rgb'].tobytes()).hexdigest()==row['raw_RGB_bytes_sha256'];count+=len(d['rgb'])
assert count==rawclose['archived_frames']==n//20+1 and rawclose['complete_for_capture_grid']and rawclose['origin']=='DIRECT_CURRENT_LIVE_MUJOCO_RGB'
unchanged=all(sha(p)==pin for p,pin in source_before.items());assert unchanged and all(checks.values())
report=dict(schema='Data-bulk24-closed-original-chain-stream-audit-camera-metadata-bound-v2',passed=True,source_result_passed=v['passed'],source_result_sha256=sha(S/'result.json'),checks=checks,actual_commands=n,visual_frames=visual_frames,review_frames=review_frames,direct_raw_frames=count,direct_raw_resolution_px=[camera["width"],camera["height"]],HD_not_claimed=True,raw_video_grid_complete=True,journal_chain=journal,actual_capture_events=[e for e in events if e.get('event')=='complex_actual_cold_capture_completed'],actual_semantic_intent_selections=[e for e in events if e.get('event')=='skill_intent_selected'],literal_native_option_installed_event_count=sum(e.get('event')=='native_option_installed'for e in events),actual_native_admissions=[e for e in events if e.get('event')=='ainav_native_admitted'],actual_native_terminal_receipts=[e for e in events if e.get('event')=='ainav_native_receipt' and e['receipt']['status'] in ('succeeded','failed','hard_stop','budget_expired')],actual_intent_native_outcomes=[e for e in events if e.get('event')=='intent_actual_native_outcome'],literal_NAV_actor_forward_event_count=sum(e.get('event')=='registered_NAV_actual_actor_forward'for e in events),actual_public_bundles=sum(e.get('event')=='reach_complex_public_decision'for e in events),source_resource_censored=v.get('resource_censored',False),source_error=v.get('error'),resource_censor_not_method_failure=True,recorder_censored_not_resource_class=True,actual_task_placement_completions=sum(e.get('event')=='completed_placement_boundary_latched'for e in events),max_raw_torque_reproduction_error=raw_error,max_hard_clip_reproduction_error=clip_error,source_sha_before_after_identical=unchanged,no_new_model_Runtime_Actor_Renderer_or_physics_calls=True,task_success_inferred=False,new_preregistered_collection_evidence=True,not_current_critic_refit_permission=True)
# Exactly three fixed ORIGINAL public boundaries, not three planning choices.
obs=[e for e in events if e.get('event')=='observability_qualification_actual_public_observation']
selections=[e for e in events if e.get('event')=='observability_qualification_fixed_NAV_selected']
receipts=report['actual_native_terminal_receipts']
assert v['passed'] and v['observation_qualification_complete'] and not v['task_success'] and not v['AB_comparison']
assert len(obs)==3 and [e['boundary']for e in obs]==['initial_after_actual_supported_capture','after_original_left_NAV','after_original_right_NAV']
assert [e['accepted_current_public_aliases']for e in obs]==[[],['cuboid_a'],[]]
assert len(selections)==len(receipts)==2 and [e['stage']for e in selections]==[0,1]
for i,(selection,receipt)in enumerate(zip(selections,receipts)):
 assert selection['parameters']==dict(goal_world_x_m=-.08,goal_world_y_m=[.15,-.15][i],surface_height_m=0.)
 assert selection['counts_as_A_B_decision']is False and receipt['receipt']['status']=='succeeded'
 assert receipt['receipt']['time_s']==obs[i+1]['time_s']
 assert receipt['receipt']['evidence_ref']=='commands:physical_tick='+str(round(obs[i+1]['time_s']/.005))
for observation in obs:
 assert not observation['private_GT_or_pose_read'] and not observation['meaningful_A_B_decision'] and not observation['original_task_success']
 assert observation['target_visible_under_original_binding']==bool(observation['accepted_current_public_aliases'])
 assert sum(hashlib.sha256(json.dumps(read(p),sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()).hexdigest()==observation['observation_sha256']for p in S.glob('intent-observation-*.json'))==1
assert not any(e.get('event')=='completed_placement_boundary_latched'for e in events)
assert len([e for e in events if e.get('event')=='observability_qualification_complete_not_task'])==1
report.update(schema='Data-fixed-three-view-observability-original-stream-audit-v1',actual_observations=obs,exact_two_fixed_NAV_original_receipts_checked=True,exact_three_boundaries_complete=True,no_PUSH_or_task_success_claimed=True,AB_comparison=False,whole_artifact_not_model_input=True)
report.pop('HD_not_claimed');report['direct_HD_frames']=report['direct_raw_frames'];report['HD_camera_metadata_verified']=camera['width']==960 and camera['height']==540
assert report['HD_camera_metadata_verified']
with(M/'actual-main-cold-audit-v2.json').open('x')as f:json.dump(report,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps(report,ensure_ascii=False))
