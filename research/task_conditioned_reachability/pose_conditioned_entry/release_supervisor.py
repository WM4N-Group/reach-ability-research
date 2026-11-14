"""One source-bound SDK and eight NEW registered attempts, never old-batch resume.

SDK0env <=180 wall; each physical attempt <=1800 wall/96 sim. Every launch
is exclusive/charged before App; technical/severe errors stop future starts.
Only the registered exact preview refusal may end a cell and continue others.
"""
import argparse,json,os,subprocess,time,traceback
from pathlib import Path
from release_authority import (approval,context,exclusive,family_snapshot,load,locked,make_permit,
    phase_directory,reserve_physical,save,sdk_gate,sha,verify_external,verify_source)
from evaluate_pose_pilot import classify,refusal_verified


def apps():return subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,process_name','--format=csv,noheader'],text=True).strip()

def argv_for(p,root,mode,item=None):
    item=item or p['schedule'][0]
    out=root/'sdk-app' if mode=='sdk' else root/'runs'/item['output_name']
    return ['--source',p['source_refs']['train'],'--nav-actor',p['source_refs']['nav'],'--output',str(out),
            '--seed',str(item['seed']),'--seconds','96','--entry-geometry-arm',item['arm'],'--headless','--device','cuda:0']

def run_one(root,mode,item,ticket,nonce,argv):
    root,source,p=context(root);ref=p['source_refs'];key='sdk' if mode=='sdk' else item['output_name']
    command=['/mnt/yuanyue/bin/isaac-python',str(source/('sdk_check.py' if mode=='sdk' else 'probe.py')),*argv]
    env=os.environ.copy();env.update(CUDA_VISIBLE_DEVICES='0',REACH_POSE_PERMIT=str(ticket),REACH_POSE_NONCE=nonce,
        PYTHONPATH=str(Path(ref['train'])/'source/LeggedManip_Lab')+':'+ref['geometry'],PIPER_SOURCE_ROOT=ref['train'],PYTHONUNBUFFERED='1')
    began=time.time();timeout=175 if mode=='sdk' else 1795
    with (root/(key+'.log')).open('x') as log:
        proc=subprocess.Popen(['timeout','--kill-after=5',str(timeout),*command],cwd=ref['train'],env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        time.sleep(.15);children=Path(f'/proc/{proc.pid}/task/{proc.pid}/children')
        launch=dict(mode=mode,item=item,command=command,supervisor_pid=os.getpid(),timeout_pid=proc.pid,process_group=proc.pid,
            observed_child_pids=children.read_text().split() if children.exists() else [],log=str(root/(key+'.log')),
            started_unix=began,source_manifest_sha256=sha(source/'manifest.json'),permit=str(ticket))
        save(root/(key+'-launch.json'),launch);rc=proc.wait()
    return dict(returncode=rc,started_unix=began,ended_unix=time.time(),wall_s=time.time()-began)


def summarize_case(root,item):
    out=Path(root)/'runs'/item['output_name'];file=out/'report.json'
    if not file.exists():return dict(outcome='missing_report',severe=True,terminal_missing=True,primary_success=None)
    try:
        r=load(file);checked=classify(r,item);terminal=r.get('terminal',{})
        severe=bool(r.get('error')) or r.get('outcome') in ('runtime_error','incomplete') or any(terminal.get(k,False) for k in ['base_contact','bad_orientation','low_posture','arm_effort_safety'])
        if checked.get('protocol_valid') is not True or checked.get('primary_success') is None:severe=True
        if r.get('outcome')=='entry_final_preview_refused' and not refusal_verified(r):severe=True
        if r.get('outcome') not in {'entry_final_preview_refused','nav_push_stow_nav_target_stable','entry_timeout','native_termination','native_termination_during_exit','push_exit_stabilization_timeout','push_timeout','return_nav_timeout','total_timeout'}:severe=True
        count=0;last=None;travel=0.;previous=None
        control=out/'control.jsonl'
        if control.exists():
            with control.open() as f:
                for line in f:
                    last=json.loads(line);count+=1;point=last['root_position'][:2]
                    if previous is not None:travel+=sum((a-b)**2 for a,b in zip(point,previous))**.5
                    previous=point
        raw_final_verified=False
        preview=r.get('measured_final_support_verification',{}).get('box_approach_preview',{})
        if r.get('outcome') in ('entry_final_preview_refused','nav_push_stow_nav_target_stable'):
            geometry=out/'entry_geometry.jsonl';clouds=[];guards=[]
            if geometry.exists():
                with geometry.open() as stream:
                    for line in stream:
                        q=json.loads(line)
                        if q.get('query_id')!=preview.get('query_id'):continue
                        if q.get('event')=='finite_tip_query':clouds.append(q)
                        if q.get('event')=='source_hand_FK_guard':guards.append(q)
            raw_final_verified=(len(clouds)==1 and len(guards)==1 and clouds[0].get('evaluation_role')=='final_actual'
                and clouds[0].get('criterion')=='COMMON_original_full_cloud_fixed_yz'
                and len(clouds[0].get('tip_cloud_box_m',[]))==2624 and clouds[0].get('nominal_translation_w') is None
                and clouds[0].get('forecast_margin_m')==0 and guards[0].get('passed') is True
                and guards[0].get('evaluation_role')=='final_actual' and guards[0].get('step')==clouds[0].get('step'))
            if not raw_final_verified:severe=True
        if r.get('outcome')=='entry_final_preview_refused':
            refusal=r['entry_final_preview_refusal']
            if last is None or last.get('step')!=refusal.get('step') or last.get('time_s')!=refusal.get('time_s'):severe=True
        return dict(outcome=r.get('outcome'),severe=severe,terminal_missing=False,terminal=terminal,error=r.get('error'),
            primary_success=checked['primary_success'],protocol_valid=checked['protocol_valid'],ordinary_refusal=refusal_verified(r),raw_common_final_query_and_guard_verified=raw_final_verified,
            control_rows=count,end_sim_s=None if last is None else last['time_s'],travel_xy_m=travel,
            report_sha256=sha(file),control_sha256=sha(control) if control.exists() else None)
    except Exception as e:return dict(outcome='unreadable_report',severe=True,terminal_missing=True,primary_success=None,error=str(e))


def dispatch(root,mode,*,gpu_busy=apps,runner=run_one,external=verify_external):
    root=Path(root).resolve();a,p=approval(root,mode);family,_=family_snapshot(p)
    with locked(root/'dispatch.lock'):
        external(root)
        if mode=='sdk':
            with locked(family/'pose_app.lock'):
                if gpu_busy():raise RuntimeError('GPU busy; no new SDK claim consumed')
                argv=argv_for(p,root,mode);ticket,nonce=make_permit(root,mode,argv)
                try:terminal=runner(root,mode,None,ticket,nonce,argv)
                except Exception as e:terminal=dict(returncode=None,error=str(e),traceback=traceback.format_exc())
                verification_error=None
                try:external(root);verify_source(root)
                except Exception as error:verification_error=str(error)
                f=root/'sdk_result.json';result=load(f) if f.exists() else {}
                terminal.update(gate_passed=verification_error is None and terminal['returncode']==0 and result.get('passed') is True and result.get('manifest_sha256')==sha(root/'source/manifest.json'),
                    manifest_sha256=sha(root/'source/manifest.json'),post_run_verification_error=verification_error)
                save(root/'sdk_terminal.json',terminal)
                if terminal['gate_passed']:
                    try:sdk_gate(root)
                    except Exception as error:
                        terminal.update(gate_passed=False,completion_evidence_error=str(error));save(root/'sdk_terminal.json',terminal)
                return terminal
        sdk_gate(root)
        # Do not reserve8 while resources are already occupied at initial admission.
        if gpu_busy():raise RuntimeError('GPU busy; no physical reservation or start consumed')
        reserve_physical(root);(root/'runs').mkdir()
        state=dict(schema='new-pose-factorial-eight-start-ledger-v1',status='RUNNING',starts=0,max_starts=8,entries=[],active=None,
            not_run=p['schedule'].copy(),supervisor_pid=os.getpid(),source_manifest_sha256=sha(root/'source/manifest.json'),
            old16_ledger_replaced=False,old_consumed=2,parent_max_starts=16)
        exclusive(root/'physical_ledger.json',state)
        try:
            while state['not_run']:
                verify_source(root);external(root);family_snapshot(p)
                with locked(family/'pose_app.lock'):
                    if gpu_busy():
                        # Preserve unspent reservation. Do not silently poll/relaunch.
                        state['status']='STOPPED_GPU_BUSY_UNSPENT_RESERVED';break
                    item=state['not_run'][0];out=root/'runs'/item['output_name']
                    if out.exists():raise PermissionError('Existing output: no repeat or overwrite')
                    argv=argv_for(p,root,mode,item);ticket,nonce=make_permit(root,mode,argv,item)
                    state['not_run'].pop(0);state['starts']+=1;state['active']=item;save(root/'physical_ledger.json',state)
                    terminal=runner(root,mode,item,ticket,nonce,argv)
                    row=dict(item,**terminal,**summarize_case(root,item));state['entries'].append(row);state['active']=None
                verify_source(root);external(root);family_snapshot(p)
                if row['returncode']!=0 or row['severe'] or row['terminal_missing']:
                    state['status']='STOPPED_TECHNICAL_OR_SEVERE_NO_RETRY';break
                save(root/'physical_ledger.json',state)
            else:state['status']='COMPLETED_REGISTERED_EIGHT'
        except Exception as e:
            state.update(status='STOPPED_ERROR_NO_RETRY',error=str(e),traceback=traceback.format_exc())
            if state['active'] is not None:
                state['entries'].append(dict(state['active'],outcome='launcher_or_terminal_exception',severe=True,primary_success=None,error=str(e)))
                state['active']=None
        finally:
            state['charged_global_claims']=len(list((phase_directory(p)/'physical_claims').glob('*.json')))
            state['ended_unix']=time.time();save(root/'physical_ledger.json',state)
        return state


def main():
    p=argparse.ArgumentParser();p.add_argument('--mode',choices=['sdk','physical'],required=True);a=p.parse_args()
    result=dispatch(Path(__file__).resolve().parent.parent,a.mode)
    print(json.dumps(result,indent=2))
    return 0 if result.get('gate_passed') or result.get('status')=='COMPLETED_REGISTERED_EIGHT' else 1

if __name__=='__main__':raise SystemExit(main())
