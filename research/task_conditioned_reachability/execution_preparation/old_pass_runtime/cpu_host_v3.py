"""Use the original complete host CPU harness and exact old CPU-only support.

No test filtering/deletion. New per-arm receipt/log. Deployment still uses only
original7a6. Additional branch modules are original pinned TEST dependencies,
not newly admitted model loaders/weights or a new training study.
"""
import argparse,sys,os,json,hashlib,time
from pathlib import Path


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--release',type=Path,required=True);ap.add_argument('--arm',choices=('A','B'),required=True);a=ap.parse_args()
    release=a.release.resolve(strict=True);arm=release/a.arm;source=arm/'source';out=arm/'cpu-v3';out.mkdir(exist_ok=False)
    os.environ['ZYH_BUNDLE']='/mnt/yuanyue/data/go2-piper-world-model/zyh-mujoco-source-340d7d8-v1'
    pins=json.loads((arm/'source-freeze.json').read_text())
    for name,h in pins['files'].items():
        if sha(source/name)!=h:raise ValueError('Own source drift '+name)
    support_pins=json.loads((release/'cpu-context-pins.json').read_text())['support_pins']
    for name,h in support_pins.items():
        if sha(release/'cpu-support'/name)!=h:raise ValueError('CPU support drift '+name)
    sys.path[:0]=[str(source),str(release/'cpu-support')]
    def audit(event,values):
        if event=='socket.connect':
            addr=values[1]
            if not (isinstance(addr,tuple) and addr[0] in ('127.0.0.1','localhost','::1')):raise PermissionError('No actual API in CPU tests')
        if event=='open' and values and isinstance(values[0],str):
            if values[0].startswith('/mnt/yuanyue/data/') and any(x in values[0] for x in ('5311','5312')):raise PermissionError('Reserved outcomes are not CPU qualification inputs')
    sys.addaudithook(audit)
    import mujoco
    def fail(*args,**kwargs):raise AssertionError('No actual step/Renderer in CPU qualification')
    mujoco.mj_step=fail;mujoco.mj_step1=fail;mujoco.mj_step2=fail;mujoco.Renderer=fail
    if a.arm=='B':
        from mujoco_zyh import stall_stow
        from mujoco_zyh.reach_phe_hook import bind_owned_fork
        bind_owned_fork(stall_stow,owned_source_root=source,enabled=False,emit=lambda r:None)
    from mujoco_zyh.deepseek_mission_task_NAV_request_physical_protocol import protocol,validate
    p=protocol();validate(p);(out/'validated-protocol.json').write_text(json.dumps(p,indent=2)+'\n')
    from mujoco_zyh.run_behavior_cpu import run
    start=time.monotonic();rc=run(out/'CPU-full.log')
    # The original CPU-admission checks require their adjacent exact dependency
    # copy. Copying code here does not admit it to the physical model loader.
    import shutil
    shutil.copytree(release/'cpu-support',out/'cpu-support',ignore=shutil.ignore_patterns('__pycache__'))
    good=all(sha(out/'cpu-support'/n)==h for n,h in support_pins.items())
    (out/'CPU-support-audit.json').write_text(json.dumps(dict(passed=good,source_unchanged=good,source_sha256=support_pins,
        producer_environment_modified=False,physics_steps=0,context_source='same pinned old passed host CPU dependencies, no test/model-weight changes'),indent=2)+'\n')
    receipt=json.loads((out/'CPU-full.json').read_text())
    if rc==0:
        from mujoco_zyh.deepseek_mission_task_NAV_request_physical_protocol import cpu_admission
        cpu_admission(out/'CPU-full.log')
    summary=dict(arm=a.arm,original_full_CPU_receipt=receipt,original_cpu_admission_pass=rc==0,
                 source_unchanged=all(sha(source/n)==h for n,h in pins['files'].items()),
                 wall_s=time.monotonic()-start,training_pipeline_started=False,actual_task_model_forwards=0,
                 synthetic_NN_or_gradient_ops_in_unit_tests_possible=True,physical_or_API_started=False)
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(dict(arm=a.arm,tests=receipt['tests_run'],failures=receipt['failures'],errors=receipt['errors'],skips=receipt['skipped'],passed=rc==0,wall_s=summary['wall_s']),indent=2))
    sys.exit(rc)


if __name__=='__main__':main()
