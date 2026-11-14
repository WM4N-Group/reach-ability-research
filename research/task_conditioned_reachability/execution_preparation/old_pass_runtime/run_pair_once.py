"""ONE admitted A then B full-task pair; no cached VLM route or auto retry.

Authentication is ONLY inherited env/API key file through original loader.
Missing credentials/resources exit before paired/native claims. Each actual arm
uses its prepared bounded original collector. Severe A error stops remaining B.
"""
import argparse,hashlib,json,os,resource,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from runtime_entry import readiness


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--release',type=Path,required=True);a=ap.parse_args();r=a.release.resolve()
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    if not (os.environ.get('DEEPSEEK_API_KEY') or os.environ.get('DEEPSEEK_KEY_FILE')):
        raise ValueError('Provide existing secure API env/key-file entry; no key search, API probe, claim or world started')
    audit=json.loads((r/'prepared-pair-invariance.json').read_text())
    if not audit.get('passed') or not audit.get('protocols_equal_except_run_identifiers') or not audit.get('deployed_model_exactly_same'):
        raise ValueError('Own zero/source/model pair qualification required')
    for arm in ('A','B'):
        admission=json.loads((r/arm/'main-admission.json').read_text());root=Path(admission['new_physical_root'])
        if not admission.get('admitted') or sha(root/'freeze.json')!=admission['physical_freeze_sha256']:raise ValueError('Actual arm admission/freeze incomplete')
        if (root/'attempt.claim').exists() or (root/'own-wrapper.claim').exists():raise ValueError('No old arm/world restart')
    snap=readiness(Path('/mnt/yuanyue/data/go2-piper-world-model'),['integrated-world-model-training-gpu0.lock','native-observer-physics-gpu1.lock','native-observer-sdk-gpu1.lock'])
    if not snap['available']:
        print(json.dumps(dict(status='RESOURCE_BUSY_NO_PAIR_OR_WORLD_STARTED',details=snap)));return
    with (r/'physical-pair.claim').open('x') as stream:stream.write('one A then B pair; no retries; caller supplies private credential mechanism\n')
    started=time.monotonic();rows=[]
    for arm in ('A','B'):
        root=Path(json.loads((r/arm/'main-admission.json').read_text())['new_physical_root'])
        cmd=[sys.executable,'-I','-B',str(r/'credential_entry.py'),'--release',str(r),'--arm',arm]
        arm_started=time.monotonic()
        with (r/arm/'actual-main-launcher.log').open('x') as log:
            process=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
        raw=json.loads((root/'report.json').read_text()) if (root/'report.json').exists() else None
        wrap=json.loads((root/'wrapper-report.json').read_text()) if (root/'wrapper-report.json').exists() else None
        row=dict(arm=arm,launcher_returncode=process.returncode,
                 full_arm_launcher_wall_s=time.monotonic()-arm_started,
                 whole_arm_time_includes_auth_source_optimization_recording_and_cleanup=True,
                 original_report_present=raw is not None,original_report_sha256=sha(root/'report.json') if raw is not None else None,
                 task_success=raw.get('task_success') if raw else None,
                 full_integrated_task_success=raw.get('full_integrated_task_success') if raw else None,
                 error=raw.get('error') if raw else None,
                 wrapper_status=wrap.get('status') if wrap else None,
                 native_video_error=wrap.get('native_video_error') if wrap else None)
        rows.append(row)
        severe=(process.returncode!=0 or raw is None or row['error'] is not None or row['native_video_error'] is not None
                or (wrap and str(wrap.get('status','')).startswith('FAILED')))
        if severe:break
    report=dict(status='PAIR_FINISHED' if len(rows)==2 else 'STOPPED_NO_RETRY',rows=rows,wall_s=time.monotonic()-started,
                statistical_success_rate_effect_NOT_established=True,scope='one seen-development H-only matched task pair',
                old_baseline_strict_safety_false_preserved=True,automatic_retry=False)
    (r/'actual-pair-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
