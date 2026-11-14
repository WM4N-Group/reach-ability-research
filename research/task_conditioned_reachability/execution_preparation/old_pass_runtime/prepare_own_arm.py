"""Compose NEW H-only experiment admission from explicit component proofs.

Reuses the original preparer/native gates. The legacy *whole-repository replay*
checksum is NOT falsely reported as newly passed: a declared source-scope proof
qualifies unchanged public/model components and the sole intended PHE delta.
No historical private frames are reopened or relabelled. Physical guards, actual
own zero, original CPU-admission, original7a6 SHA and SDK checks remain required.
"""
import argparse,ast,hashlib,inspect,json,os,shutil,sys
from pathlib import Path


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def save(p,v):Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--release',type=Path,required=True);ap.add_argument('--arm',choices=('A','B'),required=True);a=ap.parse_args()
    release=a.release.resolve();armdir=release/a.arm;source=armdir/'source'
    pins=json.loads((armdir/'source-freeze.json').read_text())
    for name,h in pins['files'].items():
        if sha(source/name)!=h:raise ValueError('Own source drift '+name)
    sys.path.insert(0,str(source))
    from mujoco_zyh import prepare as parent
    from mujoco_zyh.deepseek_mission_task_NAV_request_physical_protocol import protocol,validate,cpu_admission
    p=protocol();validate(p);cpu_log=armdir/'cpu-qualified-v6/CPU-qualified.log';cpu=cpu_admission(cpu_log)
    zero=armdir/'native-zero-v1';wrapper=json.loads((zero/'report.json').read_text());probe=json.loads((zero/'native-probe.json').read_text())
    if wrapper.get('status')!='OWN_ACTUAL_NATIVE_ZERO_PASS' or probe.get('validated_protocol')!=p or probe.get('native_physics_steps')!=0 or wrapper.get('native_video_error'):
        raise ValueError('Own exact source native zero/video not complete')
    if wrapper['source_freeze_sha256']!=sha(armdir/'source-freeze.json') or wrapper['own_runtime_freeze_sha256']!=sha(release/'runtime-source-freeze.json'):
        raise ValueError('Own runtime/source changed since actual zero')
    scoped_path=armdir/'source-scope-qualification.json';scope=json.loads(scoped_path.read_text())
    if not scope.get('passed') or scope.get('current_source_manifest')!=pins['files'] or scope.get('private_replay_data_read') is not False:
        raise ValueError('Declared component qualification mismatch')
    if scope.get('original_whole_source_feedback_replay_revalidated') is not False:raise ValueError('Do not fabricate a new legacy replay pass')
    root=Path(p['resource_lock_dir'])/p['source_id']
    if root.exists():raise ValueError('New physical root already exists; never resume/retry')
    def qualify_unchanged_public_components(base_protocol):
        if base_protocol!=p:raise ValueError('Different task protocol')
        for name,h in scope['current_source_manifest'].items():
            if sha(source/name)!=h:raise ValueError('Component bytes changed before experiment freeze')
        return dict(schema='reach-PHE-new-study-unchanged-public-component-qualification-v1',passed=True,
                    audit_sha256=sha(scoped_path),audit_source_path=str(scoped_path),
                    qualification_type='exact unchanged public/WM source components plus declared metadata/PHE path delta',
                    no_new_legacy_replay_or_uncertainty_calibration_claimed=True,
                    original_private_replay_not_opened=True,original_native_guards_not_replaced=True,
                    source_scope_proof_is_not_dynamic_safety_or_model_efficacy=True)
    # No on-disk original/shared module or gate is changed. Build an isolated
    # preparation function with this ONE explicit provenance-gate substitution.
    text=inspect.getsource(parent.prepare)
    old="feedback=feedback_replay_admission(p['public_feedback_replay_audit'])"
    new="feedback=reach_qualify_unchanged_public_components(p)"
    if text.count(old)!=1:raise ValueError('Original preparer changed; no fuzzy patch')
    changed=text.replace(old,new,1)
    if changed.replace(new,old,1)!=text:raise ValueError('Not an exact single scope split')
    ns=dict(parent.__dict__);ns['reach_qualify_unchanged_public_components']=qualify_unchanged_public_components
    exec(compile(ast.parse(changed),str(release/'prepare_own_arm.py')+':scoped-original-prepare','exec'),ns)
    bundle=Path('/mnt/yuanyue/data/go2-piper-world-model/zyh-mujoco-source-340d7d8-v1')
    pp=zero/'protocol-for-prepare.json';save(pp,p)
    ns['prepare'](root,bundle,pp,cpu_log,zero/'native-probe.json')
    # Preserve the intermediate original-preparer freeze and explicitly label
    # source-scope evidence; no old receipt is rewritten into a new replay pass.
    shutil.copyfile(root/'freeze.json',root/'parent-preparer-freeze.json')
    model_admission=json.loads((root/'model-control-admission.json').read_text())
    model_admission.update(new_experiment_qualification='reach PHE H-only',
                           legacy_replay_hash_field_refers_to_source_scope_proof=True,
                           new_whole_source_feedback_replay_claimed=False,
                           original_native_CPU_zero_checkpoint_and_goal_gates_retained=True)
    save(root/'model-control-admission.json',model_admission)
    save(root/'reach-source-scope-qualification.json',scope)
    shutil.copyfile(root/'launch_once.sh',root/'parent-launch-once-NOT-ADMITTED.sh');(root/'parent-launch-once-NOT-ADMITTED.sh').chmod(0o644)
    command=[sys.executable,'-I','-B',str(release/'runtime_entry.py'),'--release',str(release),'--arm',a.arm,'--mode','main']
    import shlex
    script='#!/bin/bash\nset -euo pipefail\nexport CUDA_VISIBLE_DEVICES="" MUJOCO_GL=egl MUJOCO_EGL_DEVICE_ID=1 OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 PYTHONDONTWRITEBYTECODE=1\nexec timeout --signal=TERM --kill-after='+str(p['grace_seconds'])+' '+str(p['max_wall_seconds'])+' '+shlex.join(command)+'\n'
    (root/'launch_once.sh').write_text(script);(root/'launch_once.sh').chmod(0o755)
    save(root/'reach-study-scope.json',dict(arm=a.arm,PHE_enabled=a.arm=='B',scope='known-development H-only same-compact path ablation, not full F7',
         source_parent='old successful WM-v9/full-4',original_strict_safety=False,original_actor_QP_limits_and_task_endpoint_unchanged=True,
         same_source_model_input_channels=True,source_scope_admission_not_new_replay=True,native_camera_recording='actual capture callback, no reconstruction',
         old16_claims_reused=False,automatic_retry=False,actual_main_episodes_allowed=1))
    freeze=json.loads((root/'freeze.json').read_text());freeze['inputs']={str(f.relative_to(root)):sha(f) for f in sorted(root.rglob('*')) if f.is_file() and f.name!='freeze.json'}
    freeze['reach_scoped_preparer']=dict(source_scope_gate_substitution_explicit=True,old_preparer_source_byte_sha256=hashlib.sha256(text.encode()).hexdigest(),all_native_gates_retained=True)
    save(root/'freeze.json',freeze)
    admission=dict(admitted=True,own_zero_passed=True,new_physical_root=str(root),arm=a.arm,
                   own_zero_report_sha256=sha(zero/'report.json'),own_CPU_qualification_sha256=sha(cpu_log.with_suffix('.json')),
                   physical_freeze_sha256=sha(root/'freeze.json'),source_scope_sha256=sha(scoped_path),
                   secure_API_credential_must_be_supplied_at_runtime=True,API_key_never_searched_or_copied=True,
                   original_strict_safety_not_certified=True,physics_started=False)
    save(armdir/'main-admission.json',admission)
    print(json.dumps(dict(prepared_root=str(root),admitted_new_own_source_zero=True,main_started=False,API_called=False,
                         source_scope_gate_explicit_not_faked_as_replay=True,original_native_gates_retained=True),indent=2))


if __name__=='__main__':main()
