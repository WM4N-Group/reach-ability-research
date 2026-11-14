"""New12-case terminated-PUSH pilot. No old role changes or automatic retries."""
import argparse,fcntl,hashlib,json,os,shutil,subprocess,time
from pathlib import Path
import numpy as np
from .option_probe import load_plan,case_protocol,PLAN
from .streams import sha,write_json
from .prepare import prepare as prepare_case
from .source_bundle import verify_bundle

PYTHON='/mnt/yuanyue/envs/piper-zyh-mujoco-340d7d8-v1/bin/python'


def admission(plan):
    p=Path(plan['required_actual_B_binding_audit']);d=json.loads(p.read_text())
    if not d['binding_and_actual_B_actuation_pass'] or d['errors'] or not d['A_failed_goal_history_preserved']:raise ValueError('Independent actual B binding/execution evidence required')
    return dict(path=str(p),sha256=sha(p),B_binding_actuation_pass=True,B_task_goal_success=d['B_native_goal_success'],B_original_hard_failure_retained=d['actual_native_terminal_error'])


def preflight(bundle,resource,output):
    plan=load_plan();evidence=admission(plan);output=Path(output);output.mkdir(exist_ok=False);probes=[]
    for case in plan['cases']:
        protocol=output/(case['case_id']+'-protocol.json');write_json(protocol,case_protocol(case))
        probe=output/(case['case_id']+'-preflight.json')
        env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',CUDA_VISIBLE_DEVICES='',OMP_NUM_THREADS='2',MUJOCO_GL='egl',MUJOCO_EGL_DEVICE_ID='1')
        with (output/(case['case_id']+'-preflight.log')).open('x') as log:
            result=subprocess.run([PYTHON,'-m','mujoco_zyh.preflight','--bundle',str(bundle),'--protocol',str(protocol),'--resource-dir',str(resource),'--output',str(probe)],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=120)
        if result.returncode:raise RuntimeError('Case zero-step preflight failed: '+case['case_id'])
        d=json.loads(probe.read_text());probes.append(dict(case=case['case_id'],path=str(probe),sha256=sha(probe),protocol_sha256=sha(protocol),passed=d['passed'],native_physics_steps=d['native_physics_steps']))
    write_json(output/'grid-preflight.json',dict(schema='terminated-option-grid-preflight-v2',plan_sha256=sha(Path(__file__).with_name(PLAN)),B_admission=evidence,cases=probes,physics_steps=0,training_runs=0))
    print(json.dumps(dict(cases=len(probes),all_zero_step=True,physics_starts=0)))


def prepare(root,bundle,tests,probes,commit):
    plan=load_plan();evidence=admission(plan);grid=json.loads((Path(probes)/'grid-preflight.json').read_text())
    if grid['plan_sha256']!=sha(Path(__file__).with_name(PLAN)) or len(grid['cases'])!=12:raise ValueError('Frozen full12case preflight required')
    root=Path(root);root.mkdir(exist_ok=False);(root/'episodes').mkdir();own=Path(__file__).parent
    shutil.copytree(own,root/'source/mujoco_zyh',ignore=shutil.ignore_patterns('__pycache__'))
    for name in ('visual_shadow_model.py','initial_contact_progress_monitor.py','recovery_reference_intersection.py','failure_exit_backoff_contract.py','contact_failure_exit_contract.py'):
        shutil.copyfile(own.parent/name,root/'source'/name)
    write_json(root/'plan.json',plan);shutil.copyfile(tests,root/'cpu-tests.log');shutil.copyfile(Path(probes)/'grid-preflight.json',root/'grid-preflight.json')
    for case,witness in zip(plan['cases'],grid['cases']):
        if witness['case']!=case['case_id'] or sha(witness['path'])!=witness['sha256']:raise ValueError('Case admission receipt mismatch')
        p=root/(case['case_id']+'-protocol.json');write_json(p,case_protocol(case))
        prepare_case(root/'episodes'/case['case_id'],bundle,p,tests,witness['path'])
        frozen=root/'episodes'/case['case_id']/'freeze.json';metadata=json.loads(frozen.read_text());metadata['collector_source_commit']=commit;metadata['new_study_role']=case['role'];frozen.write_text(json.dumps(metadata,indent=2)+'\n')
    inputs={str(p.relative_to(root)):sha(p) for p in (root/'source').rglob('*') if p.is_file()}
    inputs.update({n:sha(root/n) for n in ('plan.json','cpu-tests.log','grid-preflight.json')})
    write_json(root/'study-freeze.json',dict(schema='terminated-option-study-freeze-v2',inputs=inputs,children={c['case_id']:sha(root/'episodes'/c['case_id']/'freeze.json') for c in plan['cases']},collector_source_commit=commit,bundle=str(bundle),B_admission=evidence,main_episodes_allowed=12,auxiliary_calibration_worlds_allowed=12,training_runs_allowed=1,heldout_evaluations_allowed=1))
    launcher=root/'launch-study-once.sh';launcher.write_text('#!/bin/bash\nset -euo pipefail\ncd '+str(root/'source')+'\nexport PYTHONDONTWRITEBYTECODE=1 CUDA_VISIBLE_DEVICES="" OMP_NUM_THREADS=2 MUJOCO_GL=egl MUJOCO_EGL_DEVICE_ID=1\nexec timeout --signal=TERM --kill-after=10 1800 '+PYTHON+' -m mujoco_zyh.option_forecast_study collect --root '+str(root)+'\n');launcher.chmod(0o755)
    print(json.dumps(dict(prepared=str(root),main_episodes=12,physics_started=False,training_started=False)))


def collect(root):
    root=Path(root);f=json.loads((root/'study-freeze.json').read_text());plan=load_plan()
    if any(sha(root/n)!=h for n,h in f['inputs'].items()) or any(sha(root/'episodes'/n/'freeze.json')!=h for n,h in f['children'].items()):raise ValueError('Frozen study source changed')
    verify_bundle(f['bundle']);admission(plan);began=time.monotonic();records=[]
    with (root/'study-dispatch.lock').open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        with (root/'collection.claim').open('x') as h:json.dump(dict(pid=os.getpid(),automatic_retry=False),h)
        for case in plan['cases']:
            if time.monotonic()-began>plan['max_collection_wall_s']-90:break
            ep=root/'episodes'/case['case_id']
            with (ep/'collector.log').open('x') as log:result=subprocess.run([str(ep/'launch_once.sh')],stdout=log,stderr=subprocess.STDOUT)
            d=json.loads((ep/'report.json').read_text())
            from .audit import audit
            receipt=audit(ep/'episode');write_json(ep/'data-audit.json',receipt)
            if receipt['errors']:raise ValueError('Actual stream integrity failed: '+case['case_id'])
            record=dict(case=case['case_id'],role=case['role'],returncode=result.returncode,sim_seconds=d['sim_seconds'],first_exit=d['stall_stow_recovery']['option_first_exit'] if d['stall_stow_recovery'] else None,error=d['error'],audit_errors=[])
            records.append(record);print(json.dumps({k:record[k] for k in ('case','role','returncode','sim_seconds')}),flush=True)
            dynamic=sum(p.stat().st_size for folder in (root/'episodes').iterdir() if folder.is_dir() and folder.name!='compiled-review-models' for p in folder.rglob('*') if p.is_file() and 'source' not in p.relative_to(folder).parts)
            static=sum(p.stat().st_size for p in (root/'episodes/compiled-review-models').glob('*.mjb.gz'))
            if dynamic>plan['budgets']['total_dynamic_payload_cap_bytes'] or static>plan['budgets']['total_static_review_model_cap_bytes']:raise RuntimeError('Study quota exhausted; never drop evidence/auto-retry')
    write_json(root/'collection.json',dict(schema='terminated-option-collection-v2',records=records,complete=len(records)==12,wall_seconds=time.monotonic()-began,physics_episodes=len(records),automatic_retry=False,training_runs=0,WM_control=False))


def build(root,output):
    from .push_forecast_data import read_episode,public_features
    from .option_exit_forecast import label_until_exit
    root=Path(root);output=Path(output);output.mkdir(exist_ok=False);plan=load_plan();collection=json.loads((root/'collection.json').read_text())
    if not collection['complete']:raise ValueError('Incomplete finite study, no fill/retry')
    rows=[]
    for case in plan['cases']:
        ep=root/'episodes'/case['case_id'];meta,report,v,c,cat=read_episode(ep);rec=report.get('stall_stow_recovery') or {};event=rec.get('option_first_exit')
        entries=[e['time'] for e in report['native_events'] if e['event']=='enter' and e.get('skill')=='push'];start=entries[0] if entries else None
        truth=np.array([item['objects'][0]['position_world_m'][:2] for item in cat]);times=v['timestamps_s'];features=[];kin=[];ys=[];cvs=[];clocks=[];queries=[];censors={}
        def censor(reason):censors[reason]=censors.get(reason,0)+1
        limits=np.array(report['joint_position_limits_rad']);speed=np.array([30.1,30.1,15.7]*4+[3.]*6)
        for i,t in enumerate(times):
            t=float(t)
            if start is None or t<start or (event and t>=event['time_s']-1e-9) or i<7:continue
            end=t+.8 if event is None else min(t+.8,event['time_s']);first=round((t-.7)/.005);last=round(end/.005)
            segment=c['q_before'][first:min(last+1,len(c['q_before']))];vel=c['dq_before'][first:min(last+1,len(c['dq_before']))]
            if not len(segment) or np.any(segment<limits[:,0]) or np.any(segment>limits[:,1]) or np.any(abs(vel)>speed):censor('strict_actual_history_future_invalid');continue
            if event and end>=event['time_s']-1e-9:
                eq=np.array(event['actual_joint_q']);ev=np.array(event['actual_joint_dq'])
                if np.any(eq<limits[:,0]) or np.any(eq>limits[:,1]) or np.any(abs(ev)>speed):censor('strict_actual_exit_state_invalid');continue
            labels=[];valid=True
            for horizon in (.4,.8):
                future=None;idx=np.flatnonzero(abs(times-(t+horizon))<1e-6)
                if len(idx):future=truth[idx[0]].tolist()
                e={k:event[k] for k in ('time_s','box_xy','kind','actual_measured','first_exit')} if event else None
                label=label_until_exit(query_time=t,horizon=horizon,query_xy=truth[i].tolist(),measured_horizon_xy=future,exit_event=e,horizon_PUSH_active=bool(future is not None and (event is None or event['time_s']>t+horizon)))
                if not label['valid']:valid=False;censor(label['censor_reason']);break
                labels.append(label)
            if not valid:continue
            qtick=round(t/.005);past=np.stack((c['issued'][qtick-140:qtick],c['delayed'][qtick-140:qtick]),axis=1)
            f,k,cv,visible=public_features(v['rgb'][i-7:i+1],v['depth_m'][i-7:i+1,...,0],v['proprio'][i-7:i+1],v['actions_previous'][i-7:i+1],times[i-7:i+1],v['camera_K'],v['T_base_optical'],past,t-start)
            y=[*labels[0]['dxdy_m'],*labels[1]['dxdy_m'],float(labels[0]['failure_within_horizon']),float(labels[1]['failure_within_horizon'])]
            features.append(f);kin.append(k);ys.append(y);cvs.append(cv);clocks.append(t-start);queries.append(t)
        target=None
        if ys:
            target=case['case_id']+'.npz';np.savez_compressed(output/target,full=np.array(features),kin=np.array(kin),y=np.array(ys),cv=np.array(cvs),clock=np.array(clocks),query_time_s=np.array(queries))
        rows.append(dict(id=case['case_id'],split=case['role'],path=target,sha256=sha(output/target) if target else None,queries=len(ys),censor=censors,moving=bool(ys and np.any(np.linalg.norm(np.array(ys)[:,2:4],axis=1)>.01)),failure=bool(event and event['kind']!='native_goal_reached'),first_exit=event,whole_episode_success=report['task_success']))
    tr=[r for r in rows if r['split']=='train'];moving=sum(r['moving'] for r in tr);failures=sum(r['failure'] and r['queries']>0 for r in tr)
    write_json(output/'manifest.json',dict(schema='terminated-option-forecast-dataset-v2',rows=rows,coverage_pass=moving>=3 and failures>=3,train_independent_moving_episodes=moving,train_independent_failure_episodes=failures,labels='deltaXY at min(t+h,FIRST observed PUSH exit), plus failure within h',no_post_exit_continued_PUSH_labels=True,private_truth_only_for_labels=True,old_data_role_changes=False))
    print(json.dumps(dict(rows=len(rows),queries=sum(r['queries'] for r in rows),moving_train=moving,failure_train=failures,coverage_pass=moving>=3 and failures>=3)))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=('preflight','prepare','collect','build'));p.add_argument('--root',type=Path);p.add_argument('--bundle',type=Path);p.add_argument('--resource',type=Path);p.add_argument('--output',type=Path);p.add_argument('--tests',type=Path);p.add_argument('--probes',type=Path);p.add_argument('--commit');a=p.parse_args()
    if a.mode=='preflight':preflight(a.bundle,a.resource,a.output)
    elif a.mode=='prepare':prepare(a.root,a.bundle,a.tests,a.probes,a.commit)
    elif a.mode=='collect':collect(a.root)
    else:build(a.root,a.output)

if __name__=='__main__':main()
