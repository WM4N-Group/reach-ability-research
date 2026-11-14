"""Freeze, collect20 distinct one-shot conditions, release strict-valid windows.
No auto retry, old roots changed, skill training, WM control, or test tuning.
"""
import argparse,fcntl,importlib.metadata,json,os,shutil,subprocess,time
from pathlib import Path
import numpy as np
from .push_forecast_protocol import load_plan,plan_sha,case_protocol,configure_probe
from .streams import sha,write_json
from .source_bundle import verify_bundle
from .prepare import prepare as prepare_case

PYTHON='/mnt/yuanyue/envs/piper-zyh-mujoco-340d7d8-v1/bin/python'

def preflight(bundle,resource,output):
    from .preflight import run
    from .runtime_adapter import construct_runtime
    plan=load_plan();first=case_protocol(plan['cases'][0]);probe=run(bundle,first,resource)
    cfg=dict(first,scenario='nav-nav',auxiliary_calibration_worlds_allowed=0,auxiliary_calibration_max_sim_seconds=0,full_state_review=False)
    r,_,_=construct_runtime(bundle,cfg);grid=[]
    for c in plan['cases']:
        n=configure_probe(r.sim.spec,dict(mass_kg=c['mass_kg'],friction=c['friction']));m=r.sim.spec.compile();gid=m.geom('push_box_geom').id;pairs=(m.pair_geom1==gid)|(m.pair_geom2==gid)
        mass=float(m.body('push_box').mass[0])
        if abs(mass-c['mass_kg'])>1e-6 or not np.allclose(m.pair_friction[pairs,:2],c['friction']):raise ValueError('Grid physical binding failed')
        grid.append(dict(id=c['id'],actual_mass_kg=mass,actual_contact_pairs=n,actual_pair_friction=c['friction'],nq=m.nq,nv=m.nv))
    probe['compiled_grid_zero_step']=grid;probe['forecast_plan_sha256']=plan_sha();probe['skill_or_WM_training_started']=False
    write_json(output,probe);print(json.dumps(probe))


def prepare(root,bundle,tests,probe_path,commit):
    plan=load_plan();root=Path(root).resolve();probe=json.loads(Path(probe_path).read_text())
    if probe.get('forecast_plan_sha256')!=plan_sha() or len(probe['compiled_grid_zero_step'])!=20:raise ValueError('Whole physics grid preflight required')
    root.mkdir(exist_ok=False);(root/'episodes').mkdir();(root/'source').mkdir()
    own=Path(__file__).parent
    for p in own.glob('*.py'):
        if sha(p)!=probe['implementation_sha256'][p.name]:raise ValueError('Own implementation changed since preflight')
    shutil.copytree(own,root/'source/mujoco_zyh',ignore=shutil.ignore_patterns('__pycache__'))
    shutil.copyfile(own.parent/'visual_shadow_model.py',root/'source/visual_shadow_model.py')
    shutil.copyfile(probe_path,root/'zero-step-preflight.json');shutil.copyfile(tests,root/'cpu-tests.log')
    write_json(root/'plan.json',plan)
    for c in plan['cases']:
        protocol=root/(c['id']+'-protocol.json');write_json(protocol,case_protocol(c))
        prepare_case(root/'episodes'/c['id'],bundle,protocol,tests,probe_path)
    inputs={str(p.relative_to(root)):sha(p) for p in sorted((root/'source').rglob('*')) if p.is_file()}
    inputs.update({'plan.json':sha(root/'plan.json'),'zero-step-preflight.json':sha(root/'zero-step-preflight.json'),'cpu-tests.log':sha(root/'cpu-tests.log')})
    children={c['id']:sha(root/'episodes'/c['id']/'freeze.json') for c in plan['cases']}
    write_json(root/'study-freeze.json',dict(schema='narrow-push-study-freeze-v1',inputs=inputs,child_freezes=children,source_commit=commit,bundle=str(Path(bundle).resolve()),plan_sha256=plan_sha(),physics_episodes_allowed=20,training_runs_allowed=1,test_evaluations_allowed=1))
    (root/'launch-study-once.sh').write_text('#!/bin/bash\nset -euo pipefail\ncd '+str(root/'source')+'\nexport PYTHONDONTWRITEBYTECODE=1 CUDA_VISIBLE_DEVICES="" OMP_NUM_THREADS=2 MUJOCO_GL=egl MUJOCO_EGL_DEVICE_ID=1\nexec timeout --signal=TERM --kill-after=10 1800 '+PYTHON+' -m mujoco_zyh.push_forecast_study collect --root '+str(root)+'\n');(root/'launch-study-once.sh').chmod(0o755)
    print(json.dumps(dict(prepared=str(root),episodes=20,physics_started=False,training_started=False)))


def verify(root):
    f=json.loads((root/'study-freeze.json').read_text())
    if any(sha(root/n)!=h for n,h in f['inputs'].items()):raise ValueError('Study source/plan changed')
    if any(sha(root/'episodes'/n/'freeze.json')!=h for n,h in f['child_freezes'].items()):raise ValueError('Case freeze changed')
    verify_bundle(f['bundle']);return f


def collect(root):
    root=Path(root).resolve();freeze=verify(root);plan=load_plan();began=time.monotonic();records=[]
    with (root/'study-dispatch.lock').open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        with (root/'collection.claim').open('x') as h:json.dump(dict(pid=os.getpid(),automatic_retry=False),h)
        cache=root/'episodes/compiled-review-models';before=set(cache.glob('*.mjb.gz')) if cache.exists() else set()
        for case in plan['cases']:
            if time.monotonic()-began>plan['max_collection_wall_seconds']-75:break
            ep=root/'episodes'/case['id'];start=time.time()
            with (ep/'collector.log').open('x') as log:
                result=subprocess.run([str(ep/'launch_once.sh')],stdout=log,stderr=subprocess.STDOUT,check=False)
            rc=result.returncode;report=json.loads((ep/'report.json').read_text()) if (ep/'report.json').exists() else None
            record=dict(id=case['id'],split=case['split'],exit_code=rc,wall_seconds=time.time()-start,report_written=report is not None,
                sim_seconds=report['sim_seconds'] if report else None,outcome=report['caller_outcome'] if report else 'missing_report')
            records.append(record);print(json.dumps(record),flush=True)
            # Failed/native-guarded cases are retained and never retried. Continue
            # only to the next PREDECLARED different physical condition.
            if report is None:break
            total=sum(p.stat().st_size for c in plan['cases'] for name in ('episode','review-state') for p in (root/'episodes'/c['id']/name).rglob('*') if p.is_file())
            static=sum(p.stat().st_size for p in cache.glob('*.mjb.gz') if p not in before)
            if total>plan['max_dataset_dynamic_bytes'] or static>plan['max_new_static_model_cache_bytes']:break
        write_json(root/'collection-summary.json',dict(records=records,all_planned_cases_closed=len(records)==20,automatic_retry=False,wall_seconds=time.monotonic()-began,training_started=False,WM_control=0))
    return len(records)==20


def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['preflight','prepare','collect','dataset']);p.add_argument('--root',type=Path);p.add_argument('--bundle',type=Path);p.add_argument('--resource-dir',type=Path);p.add_argument('--output',type=Path);p.add_argument('--tests',type=Path);p.add_argument('--probe',type=Path);p.add_argument('--commit');a=p.parse_args()
    if a.mode=='preflight':preflight(a.bundle,a.resource_dir,a.output)
    elif a.mode=='prepare':prepare(a.root,a.bundle,a.tests,a.probe,a.commit)
    elif a.mode=='collect':raise SystemExit(0 if collect(a.root) else 2)
    else:
        from .push_forecast_data import build_dataset
        build_dataset(a.root,a.output)
if __name__=='__main__':main()
