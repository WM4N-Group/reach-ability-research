"""Bounded, no-App resource queue for an already approved immutable release.

This orchestrates existing frozen supervisors ONLY. It never edits source,
creates SDK/physical claims itself, retries a claimed App, replaces a case, or
kills another job. Resource waiting is bounded separately from App timeouts.
"""
import argparse,json,os,subprocess,sys,time
from pathlib import Path


def sequence(wait,launch,gate,evaluate,record):
    if not wait('sdk'):return 'WAIT_TIMEOUT_NO_SDK_CLAIM'
    if launch('sdk')!=0:return 'STOPPED_SDK_SUPERVISOR_FAILURE_NO_RETRY'
    gate();record('SDK_COMPLETE_PASS')
    if not wait('physical'):return 'WAIT_TIMEOUT_AFTER_SDK_UNSPENT_PHYSICAL'
    rc=launch('physical');evaluate()
    return 'COMPLETED_APPROVED_SEQUENCE' if rc==0 else 'PHYSICAL_STOPPED_PRESERVE_UNSPENT'


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',required=True,type=Path);p.add_argument('--resource-wait-s',type=float,default=1800);a=p.parse_args()
    if not 0<a.resource_wait_s<=1800:raise ValueError('Resource wait cap must not be expanded')
    root=a.root.resolve();sys.path.insert(0,str(root/'source'))
    from release_authority import approval,exclusive,family_snapshot,load,locked,phase_directory,save,sdk_gate,sha
    auth,protocol=approval(root,'physical');family_snapshot(protocol)
    phase=phase_directory(protocol)
    if (phase/'sdk.claim.json').exists() or (root/'physical_ledger.json').exists():raise PermissionError('Existing SDK/physical attempt; this queue never retries/resumes it')
    with locked(root/'approved_queue.lock'):
        owner=dict(pid=os.getpid(),started_unix=time.time(),source_manifest_sha256=sha(root/'source/manifest.json'),
            approval_sha256=sha(root/'approval.json'),script_sha256=sha(Path(__file__)),resource_wait_cap_s=a.resource_wait_s,App_or_physical_claim=False)
        exclusive(root/'approved_queue_owner.json',owner)
        state=dict(owner,status='RESOURCE_QUEUE_ONLY',active_supervisor=None)
        def record(status,**extra):
            state.update(status=status,updated_unix=time.time(),**extra);save(root/'approved_queue_state.json',state)
            print(json.dumps(state),flush=True)
        def wait(mode):
            began=time.time();record('WAITING_GPU_BEFORE_'+mode.upper())
            while True:
                busy=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,process_name','--format=csv,noheader'],text=True).strip()
                if not busy:record('GPU_IDLE_FOR_'+mode.upper(),gpu_snapshot='');return True
                record('WAITING_GPU_BEFORE_'+mode.upper(),gpu_snapshot=busy,resource_wait_elapsed_s=time.time()-began)
                if time.time()-began>=a.resource_wait_s:return False
                time.sleep(min(15.,a.resource_wait_s-(time.time()-began)))
        def launch(mode):
            command=['python3','-u',str(root/'source/run_supervisor.py'),'--mode',mode]
            with (root/(mode+'_supervisor.log')).open('x') as log:
                proc=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
                info=dict(mode=mode,supervisor_pid=proc.pid,command=command,log=str(root/(mode+'_supervisor.log')),
                    started_unix=time.time(),source_manifest_sha256=sha(root/'source/manifest.json'))
                exclusive(root/(mode+'_supervisor_queue_launch.json'),info);record(mode.upper()+'_SUPERVISOR_RUNNING',active_supervisor=info)
                rc=proc.wait();record(mode.upper()+'_SUPERVISOR_ENDED',returncode=rc,active_supervisor=None);return rc
        def evaluate():
            command=['python3',str(root/'source/evaluate_pose_pilot.py'),'--root',str(root),'--output',str(root/'evaluation-terminal.json')]
            r=subprocess.run(command,capture_output=True,text=True)
            exclusive(root/'evaluation-launch.json',dict(command=command,returncode=r.returncode,stdout=r.stdout,stderr=r.stderr))
            if r.returncode:raise RuntimeError('Evaluation failed; preserve raw outcomes')
        try:
            final=sequence(wait,launch,lambda:sdk_gate(root),evaluate,record);record(final,ended_unix=time.time())
        except Exception as error:
            record('QUEUE_STOPPED_PRESERVE_NO_RETRY',error_type=type(error).__name__,error=str(error),ended_unix=time.time());raise

if __name__=='__main__':main()
