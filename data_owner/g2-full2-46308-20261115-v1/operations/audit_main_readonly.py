"""Audit closed native streams and journal, no physics/model/Actor imports."""
from pathlib import Path
import os,json,hashlib,importlib.util,time
import numpy as np
R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114');B=R/'workspace';C=os.environ['DATA_PREFIX_CONDITION'];W=B/'workers/g2-full2-46308-20261115-v1'
import sys
sys.path.insert(0,str(W));from prepare_prefix import SCOPES
ROOT=R/'runtime/workers'/SCOPES[C];S=ROOT/'main';M=B/'manifests/g2-full2-46308-20261115-v1'/C;start=time.monotonic()
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
# Explicit additive release, independent of the already frozen physical program.
bp=M/'adopted_optional_journal_bridge.py';assert sha(bp)=='4013453725cc923dd012cf34a06e69540d2b5bd4fd11ab5831fbd0bdfbbe4252'
assert sha(M/'JOURNAL_RECORD_BRIDGE_RELEASE_v1.json')=='060b87e6812746f74ce76ecf85425a959b5598ebfde319daf5eb11995b723845'
spec=importlib.util.spec_from_file_location('_AINav_optional_offline_bridge',bp);bridge=importlib.util.module_from_spec(spec);spec.loader.exec_module(bridge)
index=bridge.index_original_journal(S/'events.jsonl',data_reader_ref={'path':str(R/'workspace/workers/ainav-record-adapter-20261113-v1/ainav_records.py'),'sha256':'dec9d769ccd4c4d4a80c2cfe707227236ba2905bb0c50bbb9fb0cded7700ec2a'})
with (M/'actual-main-journal-Data-index.json').open('x') as f:json.dump(index,f,ensure_ascii=False,indent=2);f.write('\n')
placement=[];native_confirmation=[];receipts=[]
with (S/'events.jsonl').open() as f:
 for line in f:
  e=json.loads(line)['payload'];event=e['event']
  if event=='completed_placement_boundary_latched':placement.append(e)
  if event=='placement_original_native_clock_confirmed':native_confirmation.append(e)
for d in index['data_index']['decisions']:
 for execution in d['native_executions']:
  for receipt in execution['receipts']:
   t=round(receipt['time_s']/.005)
   if t>0 and t<=n:
    a=issued[t-1];h=hashlib.sha256(str((a.shape,str(a.dtype))).encode()+a.tobytes()).hexdigest()
    receipts.append({'status':receipt['status'],'time_s':receipt['time_s'],'native_option_sha256':receipt['option_sha256'],'recorded_command_hash_matches_receipt':h==receipt['issued_command_sha256']})
checks={'episode_storage_complete':cl['storage_complete'],'continuous_200Hz_commands':n==cl['physical_command_steps']==v['actual_recorded_commands']==round(v['actual_main_world_sim_s']/.005),'same_program_actual_zero_and_main_model':v['program_sha256']==z['program_sha256'] and v['actual_model_numeric_sha256']==z['actual_model_numeric_sha256'],'original_delay_FIFO_exact':delay_equal,'PD_raw_torque_reproduced':raw_error<1e-10,'hard_clip_reproduced':clip_error<1e-10,'visual_actions_previous_matches_actual_issue':bool(actions_equal),'visual_and_review_grid_complete':visual_frames==review_frames==cl['observations'],'no_teardown_errors':not v['close_errors']}
unchanged=all(sha(p)==digest for p,digest in source_before.items());assert unchanged
result={'schema':'Data-closed-AINav-main-stream-and-literal-event-audit-v1','source_result_passed':v['passed'],'source_literal_status':v['status'],'checks':checks,'all_stream_checks_passed':all(checks.values()),'actual_command_steps':n,'visual_frames':visual_frames,'review_frames':review_frames,'max_raw_torque_reproduction_error':raw_error,'max_hard_clip_error':clip_error,'literal_receipt_command_hash_checks':receipts,'actual_journal_rows':index['original_journal']['rows'],'selected_engineering_intents':index['data_index']['selected_intents'],'bound_native_options':index['data_index']['bound_native_options'],'literal_receipts':index['data_index']['literal_receipts'],'actual_completed_placement_boundaries':placement,'actual_original_NN_confirmations':native_confirmation,'main_raw_sources_unchanged':unchanged,'raw_source_SHA':source_before,'no_actual_Runtime_Actor_Renderer_model_world_physics_or_API_calls':True,'next_skill_ready_or_whole_task_success_inferred':False,'training_admission':False,'audit_wall_s':time.monotonic()-start}
with (M/'actual-main-cold-audit.json').open('x') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps({k:v for k,v in result.items() if k not in ('literal_receipt_command_hash_checks','actual_completed_placement_boundaries','actual_original_NN_confirmations','raw_source_SHA')},ensure_ascii=False))
