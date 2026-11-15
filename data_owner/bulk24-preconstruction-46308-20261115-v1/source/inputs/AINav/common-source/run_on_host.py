#!/usr/bin/env python3
"""Run an unchanged frozen task runner on an explicitly registered host.

Usage: run_on_host.py --source SOURCE --profile yuanyue-5090
       --runner run_full_course.py -- [original runner arguments]
The runner must still receive fresh root, resource lock and finite budgets.
"""
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import sys


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source',required=True);ap.add_argument('--profile',required=True);ap.add_argument('--runner',required=True)
    ap.add_argument('arguments',nargs=argparse.REMAINDER);a=ap.parse_args()
    source=Path(a.source).resolve();sys.path.insert(0,str(source))
    from ainav.deployment import profile
    from ainav.host_runner import compile_runner
    host=profile(a.profile);args=a.arguments[1:] if a.arguments[:1]==['--'] else a.arguments
    if '--root' not in args or '--gpu-lock' not in args or '--source' not in args:raise ValueError('Explicit original root/lock/source required')
    get=lambda key:args[args.index(key)+1]
    root=Path(get('--root')).resolve()
    if root.exists() or not root.is_relative_to(Path(host.root)/'experiments'):raise ValueError('Fresh experiment under this host root required')
    if Path(get('--gpu-lock')).resolve()!=Path(host.lock_path).resolve() or not Path(host.lock_path).is_file():raise ValueError('Existing registered AINav host lock required')
    if Path(get('--source')).resolve()!=source:raise ValueError('Launcher and native-runner frozen source must match')
    manifest=json.loads((source/'ainav-source.json').read_text())
    for name,digest in manifest['files'].items():
        if hashlib.sha256((source/name).read_bytes()).hexdigest()!=digest:raise ValueError('Frozen source modified:'+name)
    script=source/a.runner;raw=script.read_text();code,receipt=compile_runner(raw,filename=str(script),host=host)
    receipt.update(schema='ainav-explicit-host-launch-v1',recorded_at=datetime.now().astimezone().isoformat(),host=host.report(),
        frozen_source_manifest_sha256=hashlib.sha256((source/'ainav-source.json').read_bytes()).hexdigest(),new_experiment_root=str(root),
        old_A800_world_or_state_restored=False,exclusive_GPU_ownership_claimed=False)
    dest=Path(host.root)/'deployment'/(root.name+'-host-launch.json')
    with dest.open('x') as f:json.dump(receipt,f,indent=2);f.write('\n')
    # Never implicitly pick a device, another host, script, or task after failure.
    sys.argv=[str(script),*args]
    namespace=dict(__name__='__main__',__file__=str(script),__package__=None,_AINAV_HOST=host)
    exec(code,namespace)


if __name__=='__main__':main()
