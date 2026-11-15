#!/usr/bin/env python3
"""46308: one original checkpoint restore, no inference/physical task or training."""
import argparse,datetime,json,os,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from research.task_conditioned_reachability.execution_preparation.v4_original_wm_loader import restore_original_cpu

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('checkpoint','source-root','output'):p.add_argument('--'+n,required=True)
    a=p.parse_args();need_output=Path(a.output);assert not need_output.exists(),'New exclusive report only'
    assert os.environ.get('CUDA_VISIBLE_DEVICES')=='','No GPU use or Data GPU lease borrowed'
    blocked=[]
    def fence(event,args):
        if event=='import'and str(args[0]).split('.')[0]in('mujoco','onnxruntime','gym','isaaclab'):
            blocked.append(str(args[0]));raise RuntimeError('No native/Actor/world imports')
        if event in('socket.connect','socket.bind','socket.getaddrinfo','subprocess.Popen'):
            blocked.append(event);raise RuntimeError('No network/API/child process')
    sys.addaudithook(fence)
    start=time.monotonic();model,normalization,report=restore_original_cpu(a.checkpoint,source_root=a.source_root)
    report.update(at=datetime.datetime.now().astimezone().isoformat(),wall_s=time.monotonic()-start,
        role='ACTUAL_ORIGINAL_WM_CPU_RESTORE_NOT_FORWARD_OR_NATIVE_QUALIFICATION',forbidden_attempts=blocked)
    assert not blocked
    with need_output.open('x')as f:json.dump(report,f,ensure_ascii=False,indent=2);f.write('\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
