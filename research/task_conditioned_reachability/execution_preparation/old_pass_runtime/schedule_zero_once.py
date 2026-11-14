"""Bounded resource wait, then at most ONE new own native-zero invocation.

No old queue/world. Resource polls do not consume native attempt. No API/main.
Never waits while holding partial shared locks; original probe still reacquires
and verifies its canonical locks. A race is retained as NOT_STARTED, not retried.
"""
import argparse,hashlib,json,os,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from runtime_entry import readiness


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--release',type=Path,required=True);ap.add_argument('--arm',choices=('A','B'),required=True);ap.add_argument('--wait-s',type=float,default=600.);a=ap.parse_args()
    if not 0<a.wait_s<=600:raise ValueError('One <=600s resource-wait budget')
    release=a.release.resolve();out=release/a.arm/'zero-schedule-v1';out.mkdir(exist_ok=False)
    context=json.loads((release/a.arm/'cpu-qualified-v6/CPU-qualified.json').read_text())
    if not context['passed']:raise ValueError('Own CPU qualification incomplete')
    resource=Path('/mnt/yuanyue/data/go2-piper-world-model')
    names=['integrated-world-model-training-gpu0.lock','native-observer-physics-gpu1.lock','native-observer-sdk-gpu1.lock']
    started=time.monotonic();polls=0
    while True:
        snap=readiness(resource,names);polls+=1
        if snap['available']:break
        if time.monotonic()-started>=a.wait_s:
            (out/'report.json').write_text(json.dumps(dict(status='RESOURCE_WAIT_EXPIRED_NO_NATIVE_ZERO_STARTED',polls=polls,held_no_partial_locks=True,main_dispatched=False),indent=2)+'\n');return
        time.sleep(min(20.,a.wait_s-(time.monotonic()-started)))
    cmd=[sys.executable,'-I','-B',str(release/'runtime_entry.py'),'--release',str(release),'--arm',a.arm,'--mode','zero']
    with (out/'native-zero-launcher.log').open('x') as log:
        completed=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,timeout=480)
    result=dict(status='ONE_NATIVE_ZERO_PROCESS_RETURNED',returncode=completed.returncode,
                resource_polls=polls,held_no_partial_locks_during_wait=True,main_dispatched=False,
                native_claim_created=(release/a.arm/'native-zero-v1/own-wrapper.claim').exists())
    (out/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2));sys.exit(completed.returncode)


if __name__=='__main__':main()
