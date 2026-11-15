"""Register a NEW frozen, one-shot collection root. Does not launch physics."""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import shutil
from .collect import validate_protocol
from .source_bundle import verify_bundle
from .streams import write_json,sha

RUNTIME='/mnt/yuanyue/envs/piper-zyh-mujoco-340d7d8-v1/bin/python'


def prepare(root,bundle,protocol,tests,preflight):
    p=validate_protocol(json.loads(Path(protocol).read_text()))
    source=verify_bundle(bundle)
    probe=json.loads(Path(preflight).read_text());log=Path(tests).read_text()
    if not probe.get('passed') or probe['native_physics_steps']!=0 or not log.rstrip().endswith('OK') or 'FAILED (' in log:
        raise ValueError('Passed final CPU + native zero-step real-render preflight required')
    if probe['source']['source']['sha256sums_sha256']!=source['sha256sums_sha256']:
        raise ValueError('Preflight upstream source differs')
    if p.get('recovery_exit_diagnostic_case') or p.get('push_protection_mode') or p.get('supported_push_mode') or p.get('schema')=='piper-mujoco-A-recovery-selected-B-recorded-protocol-v2' or p.get('integrated_course_mode'):
        if probe.get('validated_protocol')!=p or not (probe.get('private_failure_capsule_probe') or {}).get('all_required_captures_complete'):
            raise ValueError('Exact case-matched prospective zero-step capsule preflight required')
    if p.get('schema')=='piper-mujoco-five-easy-scenes-case-v1':
        if probe.get('validated_protocol')!=p or not probe.get('engineering_suite_probe'):
            raise ValueError('Case-matched geometry preflight required')
    root=Path(root).resolve()
    own=Path(__file__).parent
    for name,expected in probe['implementation_sha256'].items():
        if sha(own/name)!=expected:raise ValueError('Collector changed since native preflight: '+name)
    if sha(own.parent/'visual_shadow_model.py')!=probe['visual_validator_sha256']:
        raise ValueError('Visual input schema changed since preflight')
    root.mkdir(parents=True,exist_ok=False)
    dest=root/'source/mujoco_zyh';dest.mkdir(parents=True)
    for path in own.glob('*.py'):shutil.copyfile(path,dest/path.name)
    for path in own.glob('*.json'):
        shutil.copyfile(path,dest/path.name)
    shutil.copyfile(own.parent/'visual_shadow_model.py',root/'source/visual_shadow_model.py')
    if p.get('stall_stow_mode'):
        from .stall_stow import DEPENDENCIES
        for name in DEPENDENCIES:
            if sha(own.parent/name)!=probe['stall_stow_probe']['dependencies_sha256'][name]:raise ValueError('Stow helper changed: '+name)
            shutil.copyfile(own.parent/name,root/'source'/name)
    if p.get('reselect_B_mode'):
        from .reselect_B import DEPENDENCIES as selected_dependencies
        for name in selected_dependencies:
            if sha(own.parent/name)!=probe['selected_B_probe']['dependencies_sha256'][name]:raise ValueError('Selected-target helper changed: '+name)
            shutil.copyfile(own.parent/name,root/'source'/name)
    write_json(root/'protocol.json',p)
    shutil.copyfile(tests,root/'cpu-tests.log');shutil.copyfile(preflight,root/'zero-step-preflight.json')
    if p.get('causal_model_policy'):
        for name,expected in p['causal_model_policy']['source_dependencies_sha256'].items():
            if sha(own.parent/name)!=expected:raise ValueError('Causal public input dependency changed: '+name)
            shutil.copyfile(own.parent/name,root/'source'/name)
    command=[RUNTIME,'-m','mujoco_zyh.collect','--root',str(root),'--bundle',str(Path(bundle).resolve())]
    launcher='''#!/bin/bash
set -euo pipefail
cd '''+shlex.quote(str(root/'source'))+'''
export PYTHONDONTWRITEBYTECODE=1 CUDA_VISIBLE_DEVICES="" OMP_NUM_THREADS=2 MUJOCO_GL=egl MUJOCO_EGL_DEVICE_ID=1
exec timeout --signal=TERM --kill-after='''+str(p['grace_seconds'])+' '+str(p['max_wall_seconds'])+' '+shlex.join(command)+'\n'
    (root/'launch_once.sh').write_text(launcher);(root/'launch_once.sh').chmod(0o755)
    inputs={str(path.relative_to(root)):sha(path) for path in sorted(root.rglob('*')) if path.is_file()}
    freeze=dict(schema='piper-zyh-mujoco-collection-freeze-v1',inputs=inputs,
        upstream_manifest_sha256=source['sha256sums_sha256'],upstream_source=source,
        environment_versions=probe['environment_versions'],command=command,
        physics_episodes_allowed=1,auxiliary_calibration_worlds_allowed=p['auxiliary_calibration_worlds_allowed'],
        old_Isaac_root_claim_budget_or_dispatch_flags_changed=False,training_authorized=bool(p.get('forecast_study_training_authorized')))
    write_json(root/'freeze.json',freeze)
    print(json.dumps(dict(prepared_root=str(root),launch_command=str(root/'launch_once.sh'),physics_started=False,automatic_retry=False)))


def main():
    a=argparse.ArgumentParser(description=__doc__)
    for name in ('root','bundle','protocol','tests','preflight'):a.add_argument('--'+name,type=Path,required=True)
    p=a.parse_args();prepare(p.root,p.bundle,p.protocol,p.tests,p.preflight)


if __name__=='__main__':main()
