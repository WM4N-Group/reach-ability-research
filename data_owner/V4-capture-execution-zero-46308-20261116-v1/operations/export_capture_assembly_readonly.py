"""Cold-check actual capture motor/onboard streams; publish small originals only. No native/model imports."""
from pathlib import Path
import os,json,hashlib,datetime,base64
import numpy as np
assert os.environ.get('CUDA_VISIBLE_DEVICES')==''
R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114');B=R/'workspace';N='V4-capture-execution-zero-46308-20261116-v1';M=B/'manifests'/N;C=json.loads((B/'workers'/N/'protocol.json').read_bytes());S=R/'runtime/workers'/C['scope_id'];sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();read=lambda p:json.loads(Path(p).read_bytes());canonical=lambda x:json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()
h=read(B/'registry/handoff_current_status_20261115.json');q=h['active_V4_capture_execution_scope'];assert not q['active'] and q['component_zero_dispatch_count']==1 and q['task_main_dispatch_count']==0
v=read(S/'result.json');l=read(S/'ledger.json');f=read(M/'program-freeze.json');assert l['closed']and l['result_sha256']==q['actual_result_sha256']==sha(S/'result.json')and v['program_sha256']==sha(M/'program-freeze.json')
for name,pin in f['files'].items():assert sha(name)==pin
before={str(p):sha(p)for p in S.rglob('*')if p.is_file()};events=[];last='0'*64
for line in(S/'events.jsonl').read_text().splitlines():
 rec=json.loads(line);pin=rec.pop('sha256')
 assert rec['sequence']==len(events)and rec['previous_sha256']==last and hashlib.sha256(canonical(rec)).hexdigest()==pin
 last=pin;events.append(rec['payload'])
ep=S/'episode';audit=dict(original_result_passed=v['passed'],source_result_sha256=sha(S/'result.json'),all_frozen_source_members=len(f['files']),frozen_source_bytes_verified=True,journal_chain_verified_rows=len(events),original_error=v.get('error'),original_failure_stage=v.get('failure_stage'),no_Runtime_Actor_Renderer_WM_or_physics_imports=True,task_success_not_inferred=True,model_input_allowed=False,training_allowed=False)
if(ep/'closure.json').exists():
 cl=read(ep/'closure.json');ix=read(ep/'index.json');assert cl['episode_sha256']==sha(ep/'episode.json')and cl['index_sha256']==sha(ep/'index.json');arr={k:[]for k in['issued','delayed','q_before','dq_before','raw_torque','torque','time_s','physical_tick']}
 for row in ix['commands']:
  p=ep/row['path'];assert not p.is_symlink()and p.resolve().is_relative_to(ep)and sha(p)==row['sha256']
  with np.load(p,allow_pickle=False)as d:
   for k in arr:assert np.isfinite(d[k]).all();arr[k].append(d[k])
 n=sum(len(x)for x in arr['physical_tick']);delay_equal=actions_equal=True;raw_error=clip_error=0.
 if n:
  a={k:np.concatenate(xs,axis=0)for k,xs in arr.items()};assert np.array_equal(a['physical_tick'],np.arange(1,n+1))and np.allclose(a['time_s'],a['physical_tick']*.005,rtol=0,atol=1e-7)
  expected=np.stack([a['issued'][np.maximum(np.arange(n)-4,0),:,j]for j in range(18)],axis=2);delay_equal=bool(np.array_equal(expected,a['delayed']));calculated=a['delayed'][:,2]*(a['delayed'][:,0]-a['q_before'])+a['delayed'][:,3]*(a['delayed'][:,1]-a['dq_before'])+a['delayed'][:,4];raw_error=float(np.max(abs(calculated-a['raw_torque'])));effort=np.array([23.7,23.7,45.43]*4+[20.,20.,15.,7.,5.,5.]);clip_error=float(np.max(abs(np.clip(a['raw_torque'],-effort,effort)-a['torque'])))
 frames=0
 for row in ix['visual']:
  p=ep/row['path'];assert not p.is_symlink()and p.resolve().is_relative_to(ep)and sha(p)==row['sha256']
  with np.load(p,allow_pickle=False)as d:
   ct=d['control_ticks'];assert np.array_equal(ct,np.arange(frames,frames+len(ct))*5);assert d['rgb'].dtype==np.uint8 and d['rgb'].shape[2:]==(128,192,3);assert np.allclose(d['timestamps_s'][0],ct*.02,atol=1e-7,rtol=0)
   for j,t in enumerate(ct):
    assert bool(d['action_valid'][0,j])==(t>0);actions_equal &= np.array_equal(d['actions_previous'][0,j],a['issued'][int(t)*4-1,0].astype(d['actions_previous'].dtype,copy=False)if t else np.zeros(18,dtype=d['actions_previous'].dtype))
   frames+=len(ct)
 checks=dict(episode_storage_complete=cl['storage_complete'],continuous_200Hz_commands=n==cl['physical_command_steps']==v['actual_task_steps']==round(v['actual_task_time_s']/.005),original4step_delay_FIFO_exact=delay_equal,raw_PD_reproduction=raw_error<1e-10,original_hard_clip=clip_error<1e-10,onboard_visual_previous_action=bool(actions_equal),original10Hz_grid_complete=frames==cl['observations']==(n+19)//20,no_teardown_errors=not v['close_errors']);assert all(checks.values()),checks
 audit.update(checks=checks,actual_commands=n,original_onboard_frames=frames,max_raw_PD_error=raw_error,max_hard_clip_error=clip_error,original_capture_sample_events=sum(e.get('event')=='cold_capture_actual_sample'for e in events),actual_assembly_events=[e for e in events if e.get('event')=='V4_actual_capture_to_original_execution_assembled'])
 if v['passed']:assert v['capture_witness_complete']and v['actual_execution_assembly_verified']and len(audit['actual_assembly_events'])==1 and audit['original_capture_sample_events']==n
assert all(sha(p)==pin for p,pin in before.items())
D=B/'consumer-deliveries/AINAV-DATA-V4-GENUINE-CAPTURE-ORIGINAL-EXECUTION-ASSEMBLY-NOT-TASK-20261116-v1';D.mkdir();files={}
for p in[S/'result.json',S/'ledger.json',S/'claim.json',S/'resource-lease.json',S/'native-asset-construction.json',S/'native-model-camera-ABI.json',S/'V4-elevated-registry.json',S/'actual-supported-capture.json',S/'actual-execution-assembly.json',ep/'episode.json',ep/'index.json',ep/'closure.json',B/'workers'/N/'protocol.json',M/'program-freeze.json']:
 if p.exists():
  name=('episode/'if p.parent==ep else'')+p.name;out=D/name;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(p.read_bytes());files[name]=sha(out)
extra={'original-stream-cold-audit.json':audit,'remote-only-original-reference.json':dict(root=str(S),original_files_sha256=before,arrays_MJB_private_journal_kept_remote=True,whole_artifact_model_input_allowed=False,training_allowed=False,no_VJEPA_purpose_grant=True,no_full_task_or_skill_success_claim=True)}
for name,value in extra.items():(D/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n');files[name]=sha(D/name)
release=dict(schema='Data-V4-genuine-capture-and-original-execution-assembly-original-release-v1',at=datetime.datetime.now().astimezone().isoformat(),scope_id=C['scope_id'],source_commit=C['new_source_owner_commit'],program_sha256=v['program_sha256'],result_sha256=sha(S/'result.json'),passed=v['passed'],component_zero_calls=1,five_arm_task_main_calls=0,selected_skill_controllers_constructed=0,actual_task_commands=v['actual_task_steps'],original_audit=audit,whole_artifact_model_input_allowed=False,training_allowed=False,files=files)
(D/'release.json').write_text(json.dumps(release,ensure_ascii=False,indent=2)+'\n');print(json.dumps(dict(release_path=str(D/'release.json'),release_sha256=sha(D/'release.json'),audit=audit,small_files={str(p.relative_to(D)):base64.b64encode(p.read_bytes()).decode()for p in D.rglob('*')if p.is_file()})))
