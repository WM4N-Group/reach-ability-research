"""One bounded new-source SDK then ONE live-video demo after the user stop."""
import argparse
import datetime
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True);args=parser.parse_args();r=args.root.resolve()
    sys.path.insert(0,str(r/'source'));import video_authority as a
    p=a.verify(r);family=Path(p['original_family_root'])
    with a.lock(r/'video-dispatch.lock'):
        a.exclusive(r/'video-supervisor.json',dict(pid=os.getpid(),started_at=datetime.datetime.now().astimezone().isoformat(),source_manifest_sha256=a.sha(r/'source/manifest.json')))
        for mode in ('sdk','physical'):
            began=time.time()
            while True:
                a.verify(r)
                busy=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,process_name','--format=csv,noheader'],text=True).strip()
                if not busy:break
                if time.time()-began>1800:raise RuntimeError('Resources busy; do not claim/retry')
                time.sleep(10)
            with a.lock(family/'pose_app.lock'):
                if subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,process_name','--format=csv,noheader'],text=True).strip():raise RuntimeError('Resource race; no new claim')
                out=r/'sdk-app' if mode=='sdk' else r/'run'
                argv=['--source',p['source_refs']['train'],'--nav-actor',p['source_refs']['nav'],'--output',str(out),
                      '--seed','120601','--seconds','96','--entry-geometry-arm','P3','--headless','--device','cuda:0','--enable_cameras']
                ticket,nonce=a.issue(r,mode,argv)
                script=r/'source'/('sdk_check.py' if mode=='sdk' else 'probe.py')
                env=dict(os.environ,CUDA_VISIBLE_DEVICES='0',PYTHONDONTWRITEBYTECODE='1',PYTHONUNBUFFERED='1',
                    REACH_VIDEO_PERMIT=str(ticket),REACH_VIDEO_NONCE=nonce,
                    PYTHONPATH=str(Path(p['source_refs']['train'])/'source/LeggedManip_Lab')+':'+p['source_refs']['geometry'],PIPER_SOURCE_ROOT=p['source_refs']['train'])
                command=['/mnt/yuanyue/bin/isaac-python',str(script),*argv];start=time.time()
                with (r/(mode+'.log')).open('x') as log:
                    proc=subprocess.Popen(['timeout','--kill-after=5','175' if mode=='sdk' else '1795',*command],stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,env=env,cwd=p['source_refs']['train'],start_new_session=True)
                    a.exclusive(r/(mode+'-launch.json'),dict(mode=mode,supervisor_pid=os.getpid(),timeout_pid=proc.pid,command=command,started_unix=start,log=str(r/(mode+'.log')),source_manifest_sha256=a.sha(r/'source/manifest.json')))
                    rc=proc.wait()
                a.exclusive(r/(mode+'_terminal.json'),dict(returncode=rc,wall_s=time.time()-start,source_manifest_sha256=a.sha(r/'source/manifest.json')))
                a.verify(r)
                if rc:raise RuntimeError(mode+' failed; no retry')
                if mode=='sdk':a.sdk_gate(r)
                else:
                    report=a.read(out/'report.json');video=a.read(out/'native-video.json')
                    spec=importlib.util.spec_from_file_location('native_demo_classifier',r/'source/evaluate_pose_pilot.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
                    verdict=m.classify(report,p['schedule'][0])
                    a.exclusive(r/'demo-result.json',dict(role=p['role'],task=verdict,native_video=video,new_research_success_claim=False,source_manifest_sha256=a.sha(r/'source/manifest.json')))
                    print(json.dumps(a.read(r/'demo-result.json'),indent=2),flush=True)

if __name__=='__main__':main()
