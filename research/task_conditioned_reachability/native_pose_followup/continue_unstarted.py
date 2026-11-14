"""Explicit continuation of ONLY the three unclaimed cells after a GPU-busy stop.

Never dispatch SDK, create another reservation, retry a claim, or modify frozen
source. The user's explicit continuation is bound to exact stopped-ledger/source
hashes. Technical/safety/crash stops are deliberately NOT resumable here.
"""
import argparse
import copy
import importlib.util
import json
import os
from pathlib import Path
import sys
import time
import traceback


def validate(root, expected_ledger, expected_source, authority, supervisor):
    a=authority
    if a.sha(root/'physical_ledger.json')!=expected_ledger:raise PermissionError('Stopped ledger changed')
    if a.sha(root/'source/manifest.json')!=expected_source:raise PermissionError('Source identity changed')
    auth,p=a.approval(root,'physical');a.verify_source(root);a.family_snapshot(p);a.sdk_gate(root)
    ledger=a.load(root/'physical_ledger.json');schedule=p['schedule']
    if (p['arms']!=['P2','P3'] or len(schedule)!=6 or ledger.get('max_starts')!=6
            or ledger.get('status')!='STOPPED_GPU_BUSY_UNSPENT_RESERVED' or ledger.get('active') is not None
            or ledger.get('starts')!=3 or len(ledger.get('entries',[]))!=3
            or ledger.get('not_run')!=schedule[3:]):
        raise PermissionError('Not the exact three-complete resource-only stop')
    phase=a.phase_directory(p);reservation=a.load(phase/'reservation.json')
    if (reservation['max_starts']!=6 or reservation['release_root']!=str(root)
            or reservation['source_manifest_sha256']!=expected_source
            or reservation['approval_sha256']!=a.sha(root/'approval.json')):
        raise PermissionError('Existing reservation mismatch')
    family=Path(p['original_family_root'])
    if 2+sum(a.load(f)['max_starts'] for f in (family/'pose_allocations').glob('*/reservation.json'))>16:
        raise PermissionError('Parent cap exceeded')
    claims=phase/'physical_claims'
    if {f.stem for f in claims.glob('*.json')}!={x['output_name'] for x in schedule[:3]}:
        raise PermissionError('Claims do not match completed prefix; never retry')
    for item,row in zip(schedule[:3],ledger['entries']):
        if any(row.get(k)!=v for k,v in item.items()):raise PermissionError('Completed schedule prefix mismatch')
        if row.get('returncode')!=0 or row.get('severe') is not False or row.get('terminal_missing') is not False:
            raise PermissionError('A completed cell has technical/safety uncertainty')
        claim=a.load(claims/(item['output_name']+'.json'))
        if claim.get('item')!=item or claim.get('source_manifest_sha256')!=expected_source:
            raise PermissionError('Completed claim identity mismatch')
        out=root/'runs'/item['output_name']
        for name,key in [('report.json','report_sha256'),('control.jsonl','control_sha256'),
                         ('actual-initial-state.json','initial_state_sha256'),('entry_geometry.jsonl','geometry_sha256')]:
            if row.get(key):
                if not (out/name).exists() or a.sha(out/name)!=row[key]:raise PermissionError('Completed evidence changed: '+name)
            elif name in ('report.json','control.jsonl','actual-initial-state.json'):
                raise PermissionError('Completed required evidence has no digest')
        checked=supervisor.summarize_case(root,item)
        if checked.get('severe') or checked.get('primary_success')!=row.get('primary_success'):
            raise PermissionError('Completed raw outcome disagrees with ledger')
    for item in schedule[3:]:
        for path in [root/'runs'/item['output_name'],root/(item['output_name']+'.log'),
                     root/(item['output_name']+'-launch.json'),root/'permits'/(item['output_name']+'.json'),
                     claims/(item['output_name']+'.json'),claims/'admissions'/(item['output_name']+'.json')]:
            if path.exists():raise PermissionError('Remaining cell already has evidence/claim: '+str(path))
    return p,ledger


def continue_three(root, expected_ledger, expected_source, authorization, a, s,
                   *, runner=None, gpu_busy=None, external=None):
    root=Path(root).resolve();runner=runner or s.run_one;gpu_busy=gpu_busy or s.apps;external=external or a.verify_external
    if not authorization.strip():raise PermissionError('Explicit user continuation reason required')
    with a.locked(root/'dispatch.lock'):
        p,state=validate(root,expected_ledger,expected_source,a,s);external(root)
        family=Path(p['original_family_root']);phase=a.phase_directory(p)
        # Busy resources do not mutate ledger or create continuation ownership.
        with a.locked(family/'pose_app.lock'):
            if gpu_busy():raise RuntimeError('GPU busy; no continuation or case claim consumed')
        record_dir=root/'continuations'/'explicit-unstarted-v1';record_dir.mkdir(parents=True,exist_ok=False)
        before=(root/'physical_ledger.json').read_bytes()
        with (record_dir/'stopped-ledger.original.json').open('xb') as stream:
            stream.write(before);stream.flush();os.fsync(stream.fileno())
        if a.sha(record_dir/'stopped-ledger.original.json')!=expected_ledger:raise PermissionError('Stop snapshot changed')
        prefix=copy.deepcopy(state['entries'])
        info=dict(schema='explicit-three-unstarted-continuation-v1',supervisor_pid=os.getpid(),
                  source_manifest_sha256=expected_source,stopped_ledger_sha256=expected_ledger,
                  approval_sha256=a.sha(root/'approval.json'),launcher_sha256=a.sha(Path(__file__)),
                  authorization=authorization,remaining_schedule=state['not_run'],
                  SDK_repeated=False,new_reservation_created=False,max_new_starts=3,started_unix=time.time())
        a.exclusive(record_dir/'authorization-and-owner.json',info)
        def journal(status):
            a.save(record_dir/'state.json',dict(info,status=status,updated_unix=time.time(),
                   starts=state['starts'],closed=len(state['entries']),active=state['active']))
        state.update(status='RUNNING_EXPLICIT_UNSTARTED_CONTINUATION',supervisor_pid=os.getpid(),
                     continuation_record=str(record_dir/'authorization-and-owner.json'))
        state.pop('ended_unix',None);a.save(root/'physical_ledger.json',state);journal(state['status'])
        try:
            while state['not_run']:
                a.verify_source(root);external(root);a.family_snapshot(p);a.sdk_gate(root)
                with a.locked(family/'pose_app.lock'):
                    if gpu_busy():state['status']='STOPPED_GPU_BUSY_UNSPENT_RESERVED';break
                    item=state['not_run'][0]
                    if (root/'runs'/item['output_name']).exists():raise PermissionError('No repeat output allowed')
                    argv=s.argv_for(p,root,'physical',item)
                    ticket,nonce=a.make_permit(root,'physical',argv,item)
                    state['not_run'].pop(0);state['starts']+=1;state['active']=item
                    a.save(root/'physical_ledger.json',state);journal('PHYSICAL_RUNNING')
                    terminal=runner(root,'physical',item,ticket,nonce,argv)
                    row=dict(item,**terminal,**s.summarize_case(root,item));state['entries'].append(row);state['active']=None
                a.verify_source(root);external(root);a.family_snapshot(p)
                if row['returncode']!=0 or row['severe'] or row['terminal_missing']:
                    state['status']='STOPPED_TECHNICAL_OR_SEVERE_NO_RETRY';break
                a.save(root/'physical_ledger.json',state);journal('CELL_CLOSED')
            else:state['status']='COMPLETED_REGISTERED_SIX'
        except Exception as error:
            state.update(status='STOPPED_CONTINUATION_ERROR_NO_RETRY',error=str(error),traceback=traceback.format_exc())
            if state['active'] is not None:
                state['entries'].append(dict(state['active'],outcome='continuation_launcher_error',severe=True,primary_success=None,error=str(error)))
                state['active']=None
        finally:
            if state['entries'][:3]!=prefix:raise RuntimeError('Completed prefix altered; do not overwrite ledger')
            state.update(charged_global_claims=len(list((phase/'physical_claims').glob('*.json'))),ended_unix=time.time())
            a.save(root/'physical_ledger.json',state);journal(state['status'])
        return state


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--expected-ledger-sha',required=True);parser.add_argument('--expected-source-sha',required=True)
    parser.add_argument('--authorization',required=True);args=parser.parse_args()
    root=args.root.resolve();sys.path.insert(0,str(root/'source'))
    import release_authority as a
    spec=importlib.util.spec_from_file_location('frozen_native_six_supervisor',root/'source/run_supervisor.py')
    s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
    result=continue_three(root,args.expected_ledger_sha,args.expected_source_sha,args.authorization,a,s)
    print(json.dumps(result,indent=2),flush=True)
    return 0 if result['status']=='COMPLETED_REGISTERED_SIX' else 1


if __name__=='__main__':raise SystemExit(main())
