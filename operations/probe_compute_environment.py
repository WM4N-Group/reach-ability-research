#!/usr/bin/env python3
"""Read-only deployment probe. No model, MjModel/MjData, renderer or task run.

Writes a small exclusive JSON report; never confers runtime freeze/lease or
permission to train. Existing environments are inspected, not modified.
"""
import argparse
import datetime as dt
import importlib.metadata
import json
import platform
from pathlib import Path
import subprocess
import sys

PACKAGES=('numpy','torch','mujoco','scipy','osqp','imageio','pillow')

def command(args):
    result=subprocess.run(args,text=True,capture_output=True,timeout=20,check=False)
    return dict(exit_code=result.returncode,stdout=result.stdout.strip(),stderr=result.stderr.strip())

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--code-root',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();root=a.code_root.resolve()
    versions={}
    for name in PACKAGES:
        try:versions[name]=importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:versions[name]=None
    report=dict(at=dt.datetime.now(dt.timezone.utc).isoformat(),hostname=platform.node(),
        python=sys.version,python_executable=sys.executable,python_prefix=sys.prefix,
        code_root=str(root),packages=versions,
        code_commit=command(['git','-C',str(root),'rev-parse','HEAD']),
        code_dirty=command(['git','-C',str(root),'status','--porcelain']),
        GPUs=command(['nvidia-smi','--query-gpu=index,name,uuid,memory.total,memory.free','--format=csv,noheader']),
        CUDA_probe=None,mujoco_import=None,
        runtime_constructed=False,model_loaded_or_fit=False,physics_steps=0,
        execution_authority_or_lease_granted=False)
    try:
        import torch
        report['CUDA_probe']=dict(torch_version=torch.__version__,built_cuda_version=torch.version.cuda,
                                  available=torch.cuda.is_available(),visible_device_count=torch.cuda.device_count(),
                                  tensors_or_Actor_created=False)
    except Exception as error:
        report['CUDA_probe']=dict(error_type=type(error).__name__,error=str(error))
    try:
        import mujoco
        report['mujoco_import']=dict(version=mujoco.__version__,model_or_data_created=False)
    except Exception as error:
        report['mujoco_import']=dict(error_type=type(error).__name__,error=str(error))
    with a.output.open('x') as f:json.dump(report,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
    print(json.dumps({k:report[k] for k in ('hostname','python_executable','CUDA_probe','mujoco_import')},ensure_ascii=False))
if __name__=='__main__':main()
