#!/usr/bin/env python3
"""Code-only deployment check. Never constructs Runtime/Actor/renderer or fits data."""
from pathlib import Path
import argparse, hashlib, importlib.util, json, sys
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True);args=p.parse_args()
root=args.root.resolve();blocked=[]
def fence(event,items):
    if event=='import' and str(items[0]).split('.')[0] in ('numpy','torch','mujoco','onnxruntime'):
        blocked.append(str(items[0]));raise RuntimeError('Code-only check forbids native/model imports')
    if event in ('socket.connect','socket.bind','socket.getaddrinfo','subprocess.Popen'):
        blocked.append(event);raise RuntimeError('No network/child in code-only check')
sys.addaudithook(fence)
paths=sorted(root.rglob('*.py'))
for path in paths:compile(path.read_bytes(),str(path),'exec')
base=root/'consumer-deliveries/AINAV-CLIMB-PREPARATION-CANDIDATES-20261113-v1'
release=json.loads((base/'CANDIDATE_RELEASE_v1.json').read_bytes())
for rel,h in release['files_sha256'].items():
    path=base/rel
    assert not path.is_symlink() and path.resolve().is_relative_to(base)
    assert hashlib.sha256(path.read_bytes()).hexdigest()==h,rel
sys.path.insert(0,str(base/'common-source'))
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module;spec.loader.exec_module(module);return module
original=load('deployment_original_bounded_planner',base/'common-source/probe_execution_judge.py')
prefix=root/'consumer-deliveries/AINAV-NATIVE-PREFIX-CONDITION-PILOT-20261114-v1'
updated=load('deployment_explicit_three_planner',prefix/'source-delta/probe_execution_judge.py')
conditions=json.loads((prefix/'FIXED_TWO_CONDITIONS.json').read_bytes())['conditions']
for condition in conditions:
    requests=condition['requested_intents']
    for cls in (original.RequestedIntentPlanner,updated.RequestedIntentPlanner):
        try:cls(requests,lambda row:None)
        except ValueError:pass
        else:raise AssertionError('Default two-request cap must remain closed')
    planner=updated.RequestedIntentPlanner(requests,lambda row:None,max_requests=3)
    assert planner.index==0 and planner.pending is None and not planner.complete and len(planner.requests)==3
assert not blocked
print(json.dumps({'status':'CODE_ONLY_DEPLOYMENT_PASS','python':sys.version.split()[0],
    'python_sources_compiled':len(paths),'original_release_members_verified':len(release['files_sha256']),
    'two_condition_optin3_construction':'PASS','default_two_request_cap':'PRESERVED',
    'heavy_import_or_network_attempts':blocked,'native_worlds_or_receipts_or_training':0},sort_keys=True))
