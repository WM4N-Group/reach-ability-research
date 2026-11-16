"""One bounded historical command-window extraction; no physics or model import."""
from pathlib import Path
import json,hashlib,os,datetime
import numpy as np
assert os.environ.get('CUDA_VISIBLE_DEVICES')==''
R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114');B=R/'workspace';S=R/'runtime/workers/data-46308-V4-E-first-direct-live-20261116-v3';T=S/'main';ep=T/'episode';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();read=lambda p:json.loads(Path(p).read_bytes())
hraw=(B/'registry/handoff_current_status_20261115.json').read_bytes();q=json.loads(hraw)['active_V4_E_first_main_v3_scope'];assert not q['active']and q['zero_dispatch_count']==q['main_dispatch_count']==1 and q['result_sha256']==sha(T/'result.json')=='f74842a970f20126a0adba1f1b64a8d8d954bfd391aee72bc1617e41cf658f4a';cl=read(ep/'closure.json');assert cl['index_sha256']==sha(ep/'index.json');ix=read(ep/'index.json');rows={};parents=[];landmarks={5314,5315,5319,5322,5326};start,stop=5308,5332
for item in ix['commands']:
 p=ep/item['path']
 with np.load(p,allow_pickle=False)as d:
  ticks=d['physical_tick'];sel=np.flatnonzero((ticks>=start)&(ticks<=stop))
  if not len(sel):continue
  assert not p.is_symlink()and p.resolve().is_relative_to(ep)and sha(p)==item['sha256'];parents.append(dict(path=str(p),sha256=item['sha256'],original_index_entry=item))
  for i in sel:
   tick=int(ticks[i]);arrays={k:np.ascontiguousarray(d[k][i])for k in ['issued','delayed','q_before','dq_before','raw_torque','torque']};rows[tick]=dict(physical_tick=tick,actual_time_s=float(d['time_s'][i]),source_path=str(p),source_row_index=int(i),arrays=arrays)
assert sorted(rows)==list(range(start,stop+1))
for tick in range(start+4,stop+1):assert np.array_equal(rows[tick]['arrays']['delayed'],rows[tick-4]['arrays']['issued'])
base=rows[5314]['arrays'];outrows=[]
for tick,row in sorted(rows.items()):
 a=row['arrays'];out=dict(physical_tick=tick,actual_time_s=row['actual_time_s'],original_NPZ=row['source_path'],original_row_index=row['source_row_index'],FIFO_source_issued_tick=tick-4,field_byte_pins={k:dict(dtype=str(v.dtype),shape=list(v.shape),sha256=hashlib.sha256(v.tobytes()).hexdigest())for k,v in a.items()},issued_max_abs_delta_vs_tick5314_by_command_field=np.max(abs(a['issued']-base['issued']),axis=1).tolist(),delayed_max_abs_delta_vs_tick5314_by_command_field=np.max(abs(a['delayed']-base['delayed']),axis=1).tolist())
 if tick in landmarks:out['exact_original_fields']={k:v.tolist()for k,v in a.items()}
 outrows.append(out)
markers=[];last='0'*64;seq=0
with(T/'events.jsonl').open()as f:
 for line in f:
  rec=json.loads(line);p=rec['payload'];stamp=p.get('time_s');e=p.get('event','')
  if e in ['placement_arrival_original_brake_started','placement_original_native_clock_confirmed','placement_original_NN_confirmed_landing_promoted_without_reset']or (e=='placement_actual_20ms_measurement'and stamp is not None and 26.54<=stamp<=26.67):
   markers.append(dict(sequence=rec['sequence'],journal_record_sha256=rec['sha256'],event=e,original_scalar_fields={k:p[k]for k in ['time_s','phase','placement_geometry_verified','task_geometry_pass','public_XY_error_m','actual_signed_dock_gap_m','genuine_native_confirmation']if k in p}))
assert hraw==(B/'registry/handoff_current_status_20261115.json').read_bytes()
for p in parents:assert sha(p['path'])==p['sha256']
print(json.dumps(dict(schema='Data-E59-bounded-original-arrival-NNSTOP-command-window-v1',at=datetime.datetime.now().astimezone().isoformat(),scope_id=q['scope_id'],program_sha256=q['whole_program_freeze_sha256'],result_sha256=q['result_sha256'],original_journal_path=str(T/'events.jsonl'),original_journal_sha256=sha(T/'events.jsonl'),original_index_sha256=cl['index_sha256'],physical_tick_window_inclusive=[start,stop],window_command_rows=len(rows),exact_original_landmark_ticks=sorted(landmarks),command_field_order=['q_reference','dq_reference','Kp','Kd','feedforward_torque'],full_vector_byte_pins_are_dtype_shape_plus_C_order_not_JSON_hash=True,original_parent_NPZ=parents,original_command_rows=outrows,journal_markers=markers,FIFO_within_window_exact=True,interpretation=dict(first_pass_measurement_tick=5314,first_post_measurement_issued_tick=5315,that_issued_command_FIFO_applies_at_tick=5319,first_loss_measurement_tick=5326,delayed_at_first_loss_is_issued_tick=5322,actual_command_changes_not_unique_physical_cause=True,controller_mode_origin_not_inferred_from_array_difference=True),closed_H_and_parent_NPZ_unchanged=True,no_new_task_world_replay_or_training=True,model_input_allowed=False,training_allowed=False,role='PRIVATE_COMMAND_EVIDENCE_NOT_PLANNER_INPUT'),ensure_ascii=False))
