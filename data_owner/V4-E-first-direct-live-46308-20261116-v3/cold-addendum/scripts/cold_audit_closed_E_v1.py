"""Read only closed E bytes/NPZ. No Runtime/Actor/MuJoCo/render/world creation or imports."""
from pathlib import Path
import os,json,hashlib,datetime,collections,time
import numpy as np
assert os.environ.get('CUDA_VISIBLE_DEVICES')==''
start=time.monotonic();R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114');B=R/'workspace';N='V4-E-first-direct-live-46308-20261116-v3';M=B/'manifests'/N;S=R/'runtime/workers/data-46308-V4-E-first-direct-live-20261116-v3';T=S/'main';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();read=lambda p:json.loads(Path(p).read_bytes());canon=lambda x:json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()
hraw=(B/'registry/handoff_current_status_20261115.json').read_bytes();h=json.loads(hraw);q=h['active_V4_E_first_main_v3_scope'];assert not q['active']and q['phase']=='CLOSED_E_MAIN'and q['zero_dispatch_count']==q['main_dispatch_count']==1
v=read(T/'result.json');l=read(T/'ledger.json');freeze=read(M/'program-freeze.json');assert l['closed']and l['result_sha256']==q['result_sha256']==sha(T/'result.json')and v['program_sha256']==q['whole_program_freeze_sha256']==sha(M/'program-freeze.json');assert not v['passed']and not v['resource_censored']
for p,pin in freeze['files'].items():assert sha(p)==pin,('frozen member mismatch',p)
before={str(p):sha(p)for p in S.rglob('*')if p.is_file()};last='0'*64;events=[];transitions=[];was_pass=None;phase=None;counts=collections.Counter();first_placement_pass=None;first_loss_after_pass=None;markers=[]
with(T/'events.jsonl').open()as f:
 for line in f:
  rec=json.loads(line);pin=rec.pop('sha256');assert rec['sequence']==len(events)and rec['previous_sha256']==last and hashlib.sha256(canon(rec)).hexdigest()==pin;last=pin;p=rec['payload'];events.append(p);e=p.get('event','');counts[e]+=1
  if e=='placement_actual_20ms_measurement':
   ok=p['placement_geometry_verified'];ph=p['phase'];row=dict(sequence=rec['sequence'],time_s=p['time_s'],phase=ph,placement_geometry_verified=ok,task_geometry_pass=p['task_geometry_pass'],public_XY_error_m=p['public_XY_error_m'],actual_signed_dock_gap_m=p['actual_signed_dock_gap_m'],native_result=p['native_clock']['native_result'])
   if ph!=phase or ok!=was_pass:transitions.append(row)
   if ok and first_placement_pass is None:first_placement_pass=row
   if first_placement_pass is not None and not ok and first_loss_after_pass is None:first_loss_after_pass=row
   was_pass=ok;phase=ph
  if e in ['placement_arrival_original_brake_started','placement_original_native_clock_confirmed','placement_original_NN_confirmed_landing_promoted_without_reset','original_leg_release_reverse_confirmed','V4_legacy_common_H_kernel_attempt','V4_legacy_common_H_kernel_returned','ainav_chain_hard_stop']:
   markers.append(dict(sequence=rec['sequence'],event=e,original_payload=p))
ep=T/'episode';cl=read(ep/'closure.json');ix=read(ep/'index.json');assert cl['episode_sha256']==sha(ep/'episode.json')and cl['index_sha256']==sha(ep/'index.json')and cl['private_catalog_sha256']==sha(ep/'private-catalog.jsonl')and cl['control_boundaries_sha256']==sha(ep/'control-boundaries.jsonl')
arr={k:[]for k in ['issued','delayed','q_before','dq_before','raw_torque','torque','time_s','physical_tick']}
for row in ix['commands']:
 p=ep/row['path'];assert not p.is_symlink()and p.resolve().is_relative_to(ep)and sha(p)==row['sha256']
 with np.load(p,allow_pickle=False)as d:
  for k in arr:assert np.isfinite(d[k]).all();arr[k].append(d[k])
a={k:np.concatenate(xs,axis=0)for k,xs in arr.items()};n=len(a['physical_tick']);assert n==9719
continuous=np.array_equal(a['physical_tick'],np.arange(1,n+1))and np.allclose(a['time_s'],a['physical_tick']*.005,rtol=0,atol=1e-7)
expected=a['issued'][np.maximum(np.arange(n)-4,0)];fifo=np.array_equal(expected,a['delayed']);calc=a['delayed'][:,2]*(a['delayed'][:,0]-a['q_before'])+a['delayed'][:,3]*(a['delayed'][:,1]-a['dq_before'])+a['delayed'][:,4];raw_err=float(np.max(abs(calc-a['raw_torque'])));effort=np.array([23.7,23.7,45.43]*4+[20.,20.,15.,7.,5.,5.]);clip_err=float(np.max(abs(np.clip(a['raw_torque'],-effort,effort)-a['torque'])))
frames=0;actions_equal=True
for row in ix['visual']:
 p=ep/row['path'];assert not p.is_symlink()and p.resolve().is_relative_to(ep)and sha(p)==row['sha256']
 with np.load(p,allow_pickle=False)as d:
  ct=d['control_ticks'];assert np.array_equal(ct,np.arange(frames,frames+len(ct))*5);assert d['rgb'].dtype==np.uint8 and d['rgb'].shape[2:]==(128,192,3);assert np.allclose(d['timestamps_s'][0],ct*.02,rtol=0,atol=1e-7)
  for j,t in enumerate(ct):
   assert bool(d['action_valid'][0,j])==(t>0);actions_equal &= np.array_equal(d['actions_previous'][0,j],a['issued'][int(t)*4-1,0].astype(d['actions_previous'].dtype,copy=False)if t else np.zeros(18,dtype=d['actions_previous'].dtype))
  frames+=len(ct)
rawroot=T/'direct-third-view';rc=read(rawroot/'closure.json');meta=read(rawroot/'metadata.json');assert rc['metadata_sha256']==sha(rawroot/'metadata.json')and rc['camera_spec_sha256']==meta['camera_spec_sha256']==q['camera_sha256'];rawframes=0
for row in rc['chunks']:
 p=rawroot/row['path'];assert p.resolve().is_relative_to(rawroot)and not p.is_symlink()and sha(p)==row['sha256']
 with np.load(p,allow_pickle=False)as d:
  rgb=d['rgb'];ticks=d['physics_tick'];stamps=d['actual_sim_time_s'];nf=row['frames'];assert rgb.dtype==np.uint8 and rgb.shape==(nf,720,1280,3)and hashlib.sha256(rgb.tobytes()).hexdigest()==row['raw_RGB_bytes_sha256'];assert np.array_equal(ticks,np.arange(rawframes,rawframes+nf)*20)and np.allclose(stamps,ticks*.005,atol=1e-7,rtol=0);rawframes+=nf
checks=dict(all_frozen_members_SHA=True,journal_chain_verified=True,episode_storage_complete=cl['storage_complete'],continuous200Hz=bool(continuous),FIFO4step_exact=bool(fifo),raw_PD_reproduction=raw_err<1e-10,hard_effort_clip=clip_err<1e-10,previous_actions_onboard_exact=bool(actions_equal),onboard10Hz_grid_complete=frames==cl['observations']==(n+19)//20,raw_RGB_grid_complete=rawframes==rc['captured_frames']==rc['archived_frames']==486 and rc['complete_for_capture_grid'],actual_task_count_and_time=n==cl['physical_command_steps']==v['actual_task_steps']==round(v['actual_task_sim_s']/.005),close_errors0=not v['close_errors'])
assert all(checks.values()),checks
assert before=={str(p):sha(p)for p in S.rglob('*')if p.is_file()},'Closed original bytes changed during read-only audit';assert hraw==(B/'registry/handoff_current_status_20261115.json').read_bytes(),'H changed during audit; snapshot not reusable'
out=dict(schema='Data-closed-E-original-stream-cold-and-placement-gate-timeline-v1',at=datetime.datetime.now().astimezone().isoformat(),scope_id=v['scope_id'],source_commit=v['source_commit'],program_sha256=v['program_sha256'],original_result_sha256=sha(T/'result.json'),original_task_passed=False,original_task_error=v['error'],native_PUSH_terminal_label=None,resource_censored=v['resource_censored'],recorder_censored_original=cl['censored'],cold_checks=checks,all_frozen_members=len(freeze['files']),journal_rows=len(events),command_rows=n,onboard_frames=frames,raw_frames=rawframes,raw_chunks=len(rc['chunks']),max_raw_PD_error=raw_err,max_clip_error=clip_err,first_placement_pass=first_placement_pass,first_loss_after_pass=first_loss_after_pass,observed_placement_phase_or_gate_transitions=transitions,original_milestone_events=markers,event_counts=counts,immutable_originals_sha256=before,closed_scope_and_H_unchanged=True,CPU_readonly_audit_wall_s=time.monotonic()-start,task_success_not_inferred_from_cold_checks=True,reason_for_drift_not_determined_by_this_readonly_timeline=True,original_FIFO_PD_and_placement_thresholds_not_changed=True,no_native_Actor_Runtime_renderer_WM_or_physics_imports=True,no_simulation_or_replay_or_recovery=True,model_input_allowed=False,training_allowed=False)
print(json.dumps(out,ensure_ascii=False))
