"""One-shot budgeted remote supervisor. No retry/replacement/new seed dispatch.

Own kernel lock and all claims/logs persist. SDK must pass exact manifest before
any new physical start. Only original timeouts may stop the running new source;
ordinary contact failure remains a failed case, technical/severe failures stop
future scheduling. Never touches old ledgers, actors, or owner source.
"""
import argparse,fcntl,hashlib,json,os,subprocess,sys,time,traceback
from pathlib import Path

SOURCE=Path(__file__).resolve().parent;ROOT=SOURCE.parent
PROTOCOL=json.loads((SOURCE/'protocol.json').read_text())
MANIFEST=json.loads((SOURCE/'manifest.json').read_text())
REF=PROTOCOL['source_refs']


def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()


def save(path,value):
    tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(value,indent=2)+'\n');tmp.replace(path)


def claim(path,data):
    with path.open('x') as f:json.dump(data,f,indent=2);f.write('\n')


def verify():
    for n,h in MANIFEST['files'].items():
        if sha(SOURCE/n)!=h:raise ValueError('Package source changed '+n)
    p=Path(REF['source_plan']);parent=json.loads(p.read_text())
    if sha(p)!=json.loads((SOURCE/'parent_plan.original.json').read_text())['source_plan_sha256']:
        raise ValueError('Frozen train plan changed')
    for rel,h in parent['source_hashes'].items():
        if sha(Path(REF['train'])/rel)!=h:raise ValueError('Frozen input changed '+rel)
    for k,h in PROTOCOL['weight_sha256'].items():
        if sha(REF[k])!=h:raise ValueError('Frozen weight changed '+k)


def apps():
    return subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,process_name','--format=csv,noheader'],text=True).strip()


def environment():
    e=os.environ.copy();e.update(CUDA_VISIBLE_DEVICES='0',
        PYTHONPATH=str(Path(REF['train'])/'source/LeggedManip_Lab')+':'+REF['geometry'],
        PIPER_SOURCE_ROOT=REF['train'],PYTHONUNBUFFERED='1')
    return e


def command(script,out,seed=120401,arm='E2'):
    return ['/mnt/yuanyue/bin/isaac-python',str(SOURCE/script),'--source',REF['train'],
        '--nav-actor',REF['nav'],'--output',str(out),'--seed',str(seed),'--seconds','96',
        '--entry-geometry-arm',arm,'--headless','--device','cuda:0']


def run_one(cmd,log,timeout_s,launch_path,info):
    began=time.time()
    with log.open('x') as f:
        proc=subprocess.Popen(['timeout','--kill-after=5',str(timeout_s),*cmd],cwd=REF['train'],env=environment(),stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
        info=dict(info,timeout_pid=proc.pid,process_group=proc.pid,command=cmd,started_unix=began,log=str(log),source_manifest_sha256=sha(SOURCE/'manifest.json'))
        time.sleep(.15)
        children=Path(f'/proc/{proc.pid}/task/{proc.pid}/children')
        info['observed_child_pids']=children.read_text().split() if children.exists() else []
        save(launch_path,info)
        rc=proc.wait()
    return dict(returncode=rc,started_unix=began,ended_unix=time.time(),wall_s=time.time()-began)


def summarize_case(out):
    f=out/'report.json'
    if not f.exists():return dict(outcome='missing_report',terminal_missing=True,success=None,severe=True)
    r=json.loads(f.read_text());last=None;length=0.;prev=None;rows=0
    control=out/'control.jsonl'
    if control.exists():
        with control.open() as stream:
            for line in stream:
                row=json.loads(line);rows+=1;last=row
                p=row['root_position'][:2]
                if prev is not None:length+=sum((a-b)**2 for a,b in zip(p,prev))**.5
                prev=p
    terminal=r.get('terminal',{})
    severe=bool(r.get('error')) or r.get('outcome') in ('runtime_error','incomplete') or any(terminal.get(k,False) for k in ['base_contact','bad_orientation','low_posture','arm_effort_safety'])
    query=out/'entry_geometry.jsonl';qcount=0
    if query.exists():
        with query.open() as f:
            for line in f:
                v=json.loads(line)
                if v.get('event')=='finite_tip_query':qcount+=1
    return dict(outcome=r['outcome'],terminal=terminal,terminal_missing=False,
        success=r['outcome']=='nav_push_stow_nav_target_stable',end_sim_s=None if last is None else last['time_s'],
        travel_length_xy_m=length,control_rows=rows,geometry_queries=qcount,
        report_sha256=sha(out/'report.json'),control_sha256=sha(control) if control.exists() else None,
        geometry_sha256=sha(query) if query.exists() else None,
        physical_resets_after_initial=r.get('physical_resets_after_initial'),
        source_arm=r.get('study_arm'),common_goal=r.get('study_global_goal_se2'),
        error=r.get('error'),severe=severe)


def main():
    p=argparse.ArgumentParser();p.add_argument('--mode',choices=['sdk','physical'],required=True);a=p.parse_args()
    lock=(ROOT/'dispatch.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    auth_path=ROOT/'approval.json'
    if not auth_path.is_file():raise PermissionError('No explicit approval for this revision; no App/start claim consumed')
    auth=json.loads(auth_path.read_text())
    if auth.get('source_manifest_sha256')!=sha(SOURCE/'manifest.json'):
        raise PermissionError('This source revision is not covered by recorded approval; no automatic SDK retry')
    verify()
    if a.mode=='sdk':
        if apps():raise RuntimeError('GPU busy; no SDK claim consumed')
        claim(ROOT/'sdk.claim.json',dict(approval=PROTOCOL['approval'],budget_app=1,created_unix=time.time(),supervisor_pid=os.getpid()))
        result=run_one(command('sdk_check.py',ROOT/'sdk-app'),ROOT/'sdk.log',175,ROOT/'sdk_launch.json',dict(mode='SDK0env',App_budget=1,physical_starts=0))
        f=ROOT/'sdk_result.json';result['gate_passed']=result['returncode']==0 and f.exists() and json.loads(f.read_text()).get('passed') is True
        result['manifest_sha256']=sha(SOURCE/'manifest.json');save(ROOT/'sdk_terminal.json',result)
        return 0 if result['gate_passed'] else 1
    gate=json.loads((ROOT/'sdk_terminal.json').read_text())
    if not gate['gate_passed'] or gate['manifest_sha256']!=sha(SOURCE/'manifest.json'):
        raise ValueError('One permitted SDK gate not passed for this exact source')
    case_root=Path(PROTOCOL['physical_budget_family_root'])
    family_auth=json.loads((case_root/'approval.json').read_text())
    if family_auth['budgets']['max_new_Isaac_starts']!=16:
        raise PermissionError('No original shared-family16-start allocation')
    if (case_root/'physical_ledger.json').exists():raise ValueError('Supervisor was already started; inspect ledger/PIDs, never duplicate')
    (case_root/'runs').mkdir();(case_root/'claims').mkdir()
    state=dict(schema='native-entry-independent-physical-budget-ledger-v1',approval=PROTOCOL['approval'],
        max_starts=16,starts=0,status='RUNNING',supervisor_pid=os.getpid(),entries=[],active=None,
        source_manifest_sha256=sha(SOURCE/'manifest.json'),not_run=PROTOCOL['schedule'].copy(),new_physical_budget_NOT_old_shared=True)
    save(case_root/'physical_ledger.json',state)
    try:
        while state['not_run']:
            verify()
            if apps():
                state['status']='WAITING_GPU_NO_NEW_START';save(case_root/'physical_ledger.json',state)
                wait=time.time()
                while apps():
                    if time.time()-wait>1800:raise RuntimeError('Resource wait cap; unspent cases remain, no duplicate dispatch')
                    time.sleep(30)
                state['status']='RUNNING'
            item=state['not_run'].pop(0);out=case_root/'runs'/item['output_name']
            if out.exists():raise ValueError('Never repeat or overwrite an existing source')
            claim(case_root/'claims'/(item['output_name']+'.json'),dict(item,started_unix=time.time(),charged_start=state['starts']+1))
            state['starts']+=1;state['active']=item;save(case_root/'physical_ledger.json',state)
            if state['starts']>16:raise RuntimeError('Hard physical budget violation')
            term=run_one(command('probe.py',out,item['seed'],item['arm']),case_root/(item['output_name']+'.log'),1795,
                case_root/(item['output_name']+'-launch.json'),dict(item,mode='new_Isaac_physical_start',charged_start=state['starts']))
            row=dict(item,**term,**summarize_case(out));state['entries'].append(row);state['active']=None
            verify()
            if row['returncode']!=0 or row.get('severe') or row.get('terminal_missing'):
                state['status']='STOPPED_ON_TECHNICAL_OR_SEVERE_FAILURE_UNSPENT_REMAIN';save(case_root/'physical_ledger.json',state);break
            save(case_root/'physical_ledger.json',state)
        else:state['status']='COMPLETED_ALL_REGISTERED_STARTS'
    except Exception as exc:
        state.update(status='STOPPED_PRESERVE_NO_RETRY',error=str(exc),traceback=traceback.format_exc())
    finally:
        state['ended_unix']=time.time();save(case_root/'physical_ledger.json',state)
    return 0 if state['status']=='COMPLETED_ALL_REGISTERED_STARTS' else 2


if __name__=='__main__':raise SystemExit(main())
