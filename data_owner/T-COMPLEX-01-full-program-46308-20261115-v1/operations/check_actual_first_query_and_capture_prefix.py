"""Read immutable completed chunks of live B; no live state/model access or replay."""
from pathlib import Path
import subprocess,shlex,json
M=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import json,hashlib,io,datetime
import numpy as np
R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114');B=R/'workspace';M=B/'manifests/T-COMPLEX-01-full-program-46308-20261115-v1';P=json.loads((B/'workers/T-COMPLEX-01-full-program-46308-20261115-v1/protocol.json').read_bytes());roots={a:R/'runtime/workers'/row['scope_id']/'main'for a,row in P['arms'].items()};sha=lambda b:hashlib.sha256(b).hexdigest();records={};origpins={};packets={};events={}
for a,S in roots.items():
 obs=S/'intent-observation-0001.json';raw=obs.read_bytes();v=json.loads(raw);q=Path(v['rgb']['path']).parent;assert q.is_relative_to(S/'query-observations')
 for p in [obs,q/'rgb.png',q/'depth_m.npy',q/'calibration.json']:
  rawp=p.read_bytes();origpins[str(p)]=sha(rawp)
 assert origpins[str(q/'rgb.png')]==v['rgb']['sha256'];cal=json.loads((q/'calibration.json').read_bytes());depth=np.load(q/'depth_m.npy',allow_pickle=False);packets[a]=dict(observation=v,RGB_file_sha256=origpins[str(q/'rgb.png')],depth=depth,calibration=cal)
 arrays={};count=0
 # Only the first3 already-completed immutable chunks: need448 actual commands.
 for p in sorted((S/'episode/commands').glob('*.npz'))[:3]:
  rawp=p.read_bytes();assert p.read_bytes()==rawp;origpins[str(p)]=sha(rawp)
  with np.load(io.BytesIO(rawp),allow_pickle=False)as n:
   for key in n.files:arrays.setdefault(key,[]).append(n[key].copy())
  count+=len(arrays['physical_tick'][-1])
 assert count>=448;records[a]={key:np.concatenate(values,axis=0)[:448]for key,values in arrays.items()}
 rows=[]
 for line in(S/'events.jsonl').read_text().splitlines():
  try:rows.append(json.loads(line)['payload'])
  except json.JSONDecodeError:continue
 events[a]=rows
va=json.loads(json.dumps(packets['A']['observation']));vb=json.loads(json.dumps(packets['B']['observation']));va['rgb']['path']='STORAGE_PATH_EXCLUDED_FROM_EQUALITY_ONLY';vb['rgb']['path']='STORAGE_PATH_EXCLUDED_FROM_EQUALITY_ONLY'
checks=dict(exact_capture_prefix_448_channel_equality={k:np.array_equal(v,records['B'][k],equal_nan=True)for k,v in records['A'].items()},actual_first_public_observation_equal_except_RGB_storage_path=va==vb,actual_first_RGB_file_bytes_equal=packets['A']['RGB_file_sha256']==packets['B']['RGB_file_sha256'],actual_first_depth_values_equal=np.array_equal(packets['A']['depth'],packets['B']['depth'],equal_nan=True),actual_first_calibration_equal=packets['A']['calibration']==packets['B']['calibration'])
first={a:next(row for row in rows if row.get('event')=='skill_intent_selected')for a,rows in events.items()};installed=[e for e in events['B']if e.get('event')=='native_option_installed'];forwards=[e for e in events['B']if e.get('event')=='registered_NAV_actual_actor_forward'];captures={a:next(e for e in rows if e.get('event')=='complex_actual_cold_capture_completed')for a,rows in events.items()};assert all(sha(Path(p).read_bytes())==pin for p,pin in origpins.items())
report=dict(at=datetime.datetime.now().astimezone().isoformat(),role='ACTUAL_RECORDED_PREDECISION_EQUALITY_AND_B_NATIVE_PROGRESS_NOT_FINAL_RESULT',checks=checks,all_equal=all(checks['exact_capture_prefix_448_channel_equality'].values())and all(v for k,v in checks.items()if k!='exact_capture_prefix_448_channel_equality'),actual_capture_witnesses=captures,actual_first_intent={a:row['intent']for a,row in first.items()},B_original_native_option_installed=installed,B_original_NAV_actor_forward_events_seen=len(forwards),B_source_journal_still_live=True,B_task_success_not_inferred=True,source_files_sha256=origpins,storage_paths_not_rewritten_or_canonical_source_SHA_overridden=True,only_immutable_original_chunks_read=True,no_live_state_access_private_pose_GT_future_route_or_threshold_sweep=True,no_new_Runtime_Actor_Renderer_or_physics_calls=True)
with(M/'actual-first-query-and-capture-prefix-equality.json').open('x')as f:json.dump(report,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps(report,ensure_ascii=False))
'''
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],capture_output=True,text=True,timeout=75)
for suffix,text in [('stdout',r.stdout),('stderr',r.stderr),('exit',str(r.returncode)+'\n')]:
 with(M/('actual-first-query-prefix-equality.'+suffix)).open('x')as f:f.write(text)
assert r.returncode==0,r.stderr;v=json.loads(r.stdout);(M/'actual-first-query-and-capture-prefix-equality.json').write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:z for k,z in v.items()if k not in('source_files_sha256','actual_capture_witnesses')},ensure_ascii=False,indent=2))
