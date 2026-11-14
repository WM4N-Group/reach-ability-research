"""Let the active physical child finish, then close its user-paused scheduler.

No signals are sent to the physical timeout process or Isaac child. Only the
SIGSTOP-paused scheduler is terminated, and ONLY after its timeout child is a
zombie (its real exit status remains available in /proc). No further case claim.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import signal
import sys
import time


def process_stat(pid):
    values=Path('/proc',str(pid),'stat').read_text().rsplit(')',1)[1].split()
    return dict(state=values[0],start_ticks=values[19],exit_status=int(values[49]))


def completed_returncode(info):
    if info['state']!='Z':raise ValueError('Physical process has not exited; never signal it')
    return os.waitstatus_to_exitcode(info['exit_status'])


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True);a0=p.parse_args()
    r=a0.root.resolve();sys.path.insert(0,str(r/'source'));import release_authority as a
    request=a.load(r/'user-stop-after-active.json');pid=request['scheduler_pid'];child=request['active_timeout_pid']
    a.verify_source(r);a.family_snapshot(a.context(r)[2])
    if a.sha(r/'physical_ledger.json')!=request['stopped_ledger_sha256']:raise PermissionError('Running ledger changed')
    if process_stat(pid)['start_ticks']!=request['scheduler_start_ticks']:raise PermissionError('Scheduler PID reused')
    while True:
        info=process_stat(child)
        if info['start_ticks']!=request['active_timeout_start_ticks']:raise PermissionError('Physical PID reused')
        if info['state']=='Z':break
        if time.time()-request['active_launch']['started_unix']>1840:raise TimeoutError('Timeout supervisor did not exit; preserve state for inspection')
        time.sleep(1.)
    rc=completed_returncode(info);observed=time.time()
    # Still-paused scheduler cannot launch the sixth cell. Terminate only it,
    # after the physical process has really exited; retain its original ledger.
    if process_stat(pid)['state'] not in ('T','t'):raise PermissionError('Scheduler no longer paused')
    a.exclusive(r/'user-stop-physical-exit.json',dict(timeout_pid=child,returncode=rc,raw_wait_status=info['exit_status'],exit_observed_unix=observed,physical_process_not_signalled=True))
    os.kill(pid,signal.SIGTERM);os.kill(pid,signal.SIGCONT)
    for _ in range(100):
        try:
            if process_stat(pid)['state']=='Z':break
        except FileNotFoundError:break
        time.sleep(.05)
    else:raise RuntimeError('Scheduler did not exit; do not take ledger ownership')
    spec=importlib.util.spec_from_file_location('original_case_summary',r/'source/run_supervisor.py');s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
    with a.locked(r/'dispatch.lock'):
        state=a.load(r/'physical_ledger.json');assert state['active']==request['active_case']
        before=(r/'physical_ledger.json').read_bytes()
        with (r/'user-stop-ledger-before-harvest.json').open('xb') as f:f.write(before)
        row=dict(request['active_case'],returncode=rc,started_unix=request['active_launch']['started_unix'],
                 ended_unix=observed,wall_s=observed-request['active_launch']['started_unix'],
                 wall_time_scope='exit observed by read-only one-second poll, not original paused wait',**s.summarize_case(r,request['active_case']))
        state['entries'].append(row);state['active']=None
        state.update(status='STOPPED_USER_AFTER_ACTIVE',ended_unix=observed,
                     user_stop_record=str(r/'user-stop-after-active.json'),
                     charged_global_claims=5,supervisor_pid=None)
        a.save(r/'physical_ledger.json',state)
        record=a.load(r/'continuations/explicit-unstarted-v1/state.json');record.update(status='STOPPED_USER_AFTER_ACTIVE',starts=5,closed=5,active=None,updated_unix=observed)
        a.save(r/'continuations/explicit-unstarted-v1/state.json',record)
        a.exclusive(r/'user-stop-terminal.json',dict(status=state['status'],active_case_result=row,not_run=state['not_run'],physical_starts=5,source_manifest_sha256=a.sha(r/'source/manifest.json'),physical_process_not_signalled=True))
        print(json.dumps(a.load(r/'user-stop-terminal.json'),indent=2),flush=True)


if __name__=='__main__':main()
