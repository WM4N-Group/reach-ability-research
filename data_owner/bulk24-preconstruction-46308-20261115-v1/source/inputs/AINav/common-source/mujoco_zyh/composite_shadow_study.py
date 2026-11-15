"""Fresh, bounded composite-scene collection; training is a separate step."""
import argparse
import fcntl
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

from .prepare import prepare as prepare_case
from .source_bundle import verify_bundle
from .streams import sha, write_json

PYTHON='/mnt/yuanyue/envs/piper-zyh-mujoco-340d7d8-v1/bin/python'
RESOURCE=Path('/mnt/yuanyue/data/go2-piper-world-model')
PLAN='composite_shadow_plan_v1.json'


def plan():
    return json.loads(Path(__file__).with_name(PLAN).read_text())


def case_protocol(case):
    p=json.loads(Path(__file__).with_name('nav_efficiency_protocol_v2.json').read_text())
    p.update(schema='piper-mujoco-composite-shadow-case-v1',
        purpose='Fresh full native route data for causal shadow model training; preserve all actual failures and strict-safety censoring',
        source_id='composite-shadow-20261025-v1-'+case['case_id'],
        episode_id='composite-shadow-20261025-v1-'+case['case_id']+'-episode0',
        source_group='composite-shadow-v1-'+case['case_id'],
        role=case['role'],training_allowed=case['role']=='train',
        forecast_study_training_authorized=case['role']=='train',
        seed=case['seed'],delay_ms=case['delay_ms'],
        resource_lock_dir=str(RESOURCE),full_state_review=False,
        max_sim_seconds=90,max_wall_seconds=900,max_payload_bytes=134217728,
        independent_sample=True,training_runs=0,WM_forwards=0,WM_control=False)
    return p


def validate_case(p):
    candidate=next((c for c in plan()['cases'] if c['case_id']==p.get('source_id','').removeprefix('composite-shadow-20261025-v1-')),None)
    if candidate is None or p!=case_protocol(candidate):
        raise ValueError('Exact preregistered composite-shadow case required')
    if p['scene_recipe']!='zyh_native_single_box' or p['scenario']!='nav-push-climb' or p['automatic_retry'] is not False or p['reset_after_initial_allowed']!=0:
        raise ValueError('Native full route/no retry/no reset required')
    return p


def preflight(bundle,resource,output):
    if Path(resource).resolve()!=RESOURCE.resolve():raise ValueError('Canonical GPU resource directory required')
    output=Path(output);output.mkdir(exist_ok=False);rows=[]
    for case in plan()['cases']:
        protocol=output/(case['case_id']+'-protocol.json');write_json(protocol,case_protocol(case))
        probe=output/(case['case_id']+'-preflight.json')
        env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',CUDA_VISIBLE_DEVICES='',OMP_NUM_THREADS='2',MUJOCO_GL='egl',MUJOCO_EGL_DEVICE_ID='1')
        with (output/(case['case_id']+'-preflight.log')).open('x') as log:
            result=subprocess.run([PYTHON,'-m','mujoco_zyh.preflight','--bundle',str(bundle),'--protocol',str(protocol),'--resource-dir',str(resource),'--output',str(probe)],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=180)
        if result.returncode:raise RuntimeError('Zero-step case preflight failed: '+case['case_id'])
        d=json.loads(probe.read_text())
        if not d['passed'] or d['native_physics_steps']!=0 or d['actual_metric_depth_valid_fraction']<=0:
            raise ValueError('Real nonempty RGBD zero-step preflight required')
        rows.append(dict(case_id=case['case_id'],sha256=sha(probe),path=str(probe),source_sha256=d['source']['source']['sha256sums_sha256'],actual_RGB_shape=d['actual_RGB_shape'],valid_depth_fraction=d['actual_metric_depth_valid_fraction']))
    write_json(output/'grid.json',dict(schema='composite-shadow-zero-step-grid-v1',plan_sha256=sha(Path(__file__).with_name(PLAN)),rows=rows,physical_steps=0))


def prepare(root,bundle,tests,probes,source_commit):
    root=Path(root);probes=Path(probes);grid=json.loads((probes/'grid.json').read_text())
    if grid['plan_sha256']!=sha(Path(__file__).with_name(PLAN)) or len(grid['rows'])!=len(plan()['cases']):raise ValueError('Exact full grid required')
    if not Path(tests).read_text().rstrip().endswith('OK'):raise ValueError('Final CPU regression must pass')
    root.mkdir(exist_ok=False);(root/'episodes').mkdir();own=Path(__file__).parent
    shutil.copytree(own,root/'source/mujoco_zyh',ignore=shutil.ignore_patterns('__pycache__'))
    for name in ('visual_shadow_model.py','initial_contact_progress_monitor.py','recovery_reference_intersection.py','failure_exit_backoff_contract.py','contact_failure_exit_contract.py'):
        shutil.copyfile(own.parent/name,root/'source'/name)
    write_json(root/'plan.json',plan());shutil.copyfile(tests,root/'cpu-tests.log');shutil.copyfile(probes/'grid.json',root/'grid-preflight.json')
    for case,row in zip(plan()['cases'],grid['rows']):
        if case['case_id']!=row['case_id'] or sha(row['path'])!=row['sha256']:raise ValueError('Grid witness changed')
        p=root/(case['case_id']+'-protocol.json');write_json(p,case_protocol(case))
        prepare_case(root/'episodes'/case['case_id'],bundle,p,tests,row['path'])
    inputs={str(p.relative_to(root)):sha(p) for p in (root/'source').rglob('*') if p.is_file()}
    inputs.update({n:sha(root/n) for n in ('plan.json','cpu-tests.log','grid-preflight.json')})
    write_json(root/'study-freeze.json',dict(schema='composite-shadow-study-freeze-v1',inputs=inputs,
        children={c['case_id']:sha(root/'episodes'/c['case_id']/'freeze.json') for c in plan()['cases']},
        source_commit=source_commit,bundle=str(bundle),physical_starts_allowed=len(plan()['cases']),training_runs_allowed=1,automatic_retry=False))
    launcher=root/'launch-collection-once.sh'
    launcher.write_text('#!/bin/bash\nset -euo pipefail\ncd '+str(root/'source')+'\nexport PYTHONDONTWRITEBYTECODE=1 CUDA_VISIBLE_DEVICES="" OMP_NUM_THREADS=2 MUJOCO_GL=egl MUJOCO_EGL_DEVICE_ID=1\nexec timeout --signal=TERM --kill-after=10 2400 '+PYTHON+' -m mujoco_zyh.composite_shadow_study collect --root '+str(root)+'\n')
    launcher.chmod(0o755)


def collect(root):
    root=Path(root);freeze=json.loads((root/'study-freeze.json').read_text());cases=plan()['cases']
    if any(sha(root/n)!=h for n,h in freeze['inputs'].items()) or any(sha(root/'episodes'/n/'freeze.json')!=h for n,h in freeze['children'].items()):
        raise ValueError('Study frozen inputs changed')
    verify_bundle(freeze['bundle']);started=time.monotonic();rows=[]
    with (root/'study-dispatch.lock').open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        with (root/'collection.claim').open('x') as claim:json.dump(dict(pid=os.getpid(),automatic_retry=False),claim)
        for case in cases:
            if time.monotonic()-started>plan()['limits']['total_wall_s']-900:break
            ep=root/'episodes'/case['case_id']
            with (ep/'collector.log').open('x') as log:
                result=subprocess.run([str(ep/'launch_once.sh')],stdout=log,stderr=subprocess.STDOUT)
            report=json.loads((ep/'report.json').read_text())
            from .audit import audit
            checked=audit(ep/'episode');write_json(ep/'data-audit.json',checked)
            if checked['errors']:raise ValueError('Actual RGBD/motor stream integrity failed: '+case['case_id'])
            row=dict(case_id=case['case_id'],role=case['role'],returncode=result.returncode,
                outcome=report['caller_outcome'],task_success=report['task_success'],error=report['error'],
                sim_seconds=report['sim_seconds'],visual_frames=report['frames'],physical_steps=report['physical_steps'],
                speed_exceeded_steps=sum(report.get('speed_exceeded_physics_steps',[])),
                angle_violation_max_rad=max(report.get('angle_violation_rad',[0.])))
            rows.append(row);print(json.dumps(row),flush=True)
    write_json(root/'collection.json',dict(schema='composite-shadow-collection-v1',rows=rows,complete=len(rows)==len(cases),
        wall_seconds=time.monotonic()-started,physical_starts=len(rows),automatic_retry=False,WM_control=False,training_runs=0))


def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=('preflight','prepare','collect'));p.add_argument('--root',type=Path)
    p.add_argument('--bundle',type=Path);p.add_argument('--resource',type=Path);p.add_argument('--output',type=Path)
    p.add_argument('--tests',type=Path);p.add_argument('--probes',type=Path);p.add_argument('--commit');a=p.parse_args()
    if a.mode=='preflight':preflight(a.bundle,a.resource,a.output)
    elif a.mode=='prepare':prepare(a.root,a.bundle,a.tests,a.probes,a.commit)
    else:collect(a.root)


if __name__=='__main__':main()
