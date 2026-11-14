"""One own frozen old-pass arm: real native zero or admitted original collector.

Zero needs no API credentials and NEVER dispatches main. Main requires explicit
new own admission, freeze, own successful zero, original locks and API mechanism.
"""
import argparse,fcntl,hashlib,importlib,json,os,resource,signal,sys,time,traceback
from pathlib import Path


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def save(p,v):Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')


def readiness(resource_dir,names):
    handles=[];evidence=[]
    try:
        for name in names:
            p=resource_dir/name;f=p.open('r+');handles.append(f)
            try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:return dict(available=False,held_by_other=name,partial_handles_released=True)
            evidence.append(dict(path=str(p),inode=p.stat().st_ino))
        return dict(available=True,locks=evidence,snapshot_only=True)
    finally:
        for f in reversed(handles):f.close()


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--release',type=Path,required=True);ap.add_argument('--arm',choices=('A','B'),required=True)
    ap.add_argument('--mode',choices=('zero','main'),required=True);a=ap.parse_args();release=a.release.resolve(strict=True);armdir=release/a.arm
    if a.mode=='zero':source=armdir/'source';root=armdir/'native-zero-v1'
    else:
        admission=json.loads((armdir/'main-admission.json').read_text())
        if not admission.get('admitted') or not admission.get('own_zero_passed'):raise ValueError('Main is NOT admitted')
        if not os.environ.get('DEEPSEEK_API_KEY'):raise ValueError('Original task API credential not supplied; no claim/key search/probe')
        root=Path(admission['new_physical_root']).resolve();source=root/'source'
        if not (root/'freeze.json').is_file() or (root/'attempt.claim').exists():raise ValueError('Fresh original collector freeze/claim required')
    runtime_pins=json.loads((release/'runtime-source-freeze.json').read_text())
    for name,h in runtime_pins['files'].items():
        if sha(release/name)!=h:raise ValueError('Own runtime wrapper changed after qualification')
    pins=json.loads((armdir/'source-freeze.json').read_text())
    if a.mode=='zero':
        for name,h in pins['files'].items():
            if sha(source/name)!=h:raise ValueError('Source changed since own freeze: '+name)
    else:
        if sha(root/'freeze.json')!=admission['physical_freeze_sha256']:raise ValueError('Own prepared main freeze changed')
        for name,h in json.loads((root/'freeze.json').read_text())['inputs'].items():
            if sha(root/name)!=h:raise ValueError('Own actual deployment input changed: '+name)
    sys.path.insert(0,str(source));sys.path.insert(0,str(release))
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    signal.signal(signal.SIGTERM,lambda s,f:(_ for _ in ()).throw(TimeoutError('Outer bounded supervisor terminated run')))
    def audit(event,values):
        if event=='open' and values and isinstance(values[0],str):
            path=values[0]
            if path.startswith('/mnt/yuanyue/data/') and any(x in path for x in ('5311','5312')):
                raise PermissionError('Reserved outcomes cannot be runtime adapter inputs')
        if a.mode=='zero' and event=='socket.connect':raise PermissionError('Zero cannot issue network/API calls')
    sys.addaudithook(audit)
    from mujoco_zyh.deepseek_mission_task_NAV_request_physical_protocol import protocol,validate,LOCK_NAMES,cpu_admission
    qualified_log=armdir/'cpu-qualified-v6/CPU-qualified.log'
    if a.mode=='zero':
        cpu=cpu_admission(qualified_log)
    else:
        cpu=json.loads(qualified_log.with_suffix('.json').read_text())
        if not cpu.get('passed') or sha(qualified_log.with_suffix('.json'))!=admission['own_CPU_qualification_sha256']:
            raise ValueError('Prepared deployment is not bound to its own complete CPU qualification')
    p=protocol();validate(p)
    scope=json.loads((armdir/'source-scope-qualification.json').read_text())
    if not scope.get('passed') or not scope.get('source_compatibility_not_physical_or_model_efficacy_certificate'):
        raise ValueError('Own declared delta/public component source qualification required')
    ready=readiness(Path(p['resource_lock_dir']),LOCK_NAMES)
    if not ready['available']:
        save(armdir/(a.mode+'-resource-busy.json'),dict(status='RESOURCE_BUSY_NO_NATIVE_INVOCATION',snapshot=ready,native_zero_or_main_started=False))
        print(json.dumps(ready));return
    if a.mode=='zero':root.mkdir(exist_ok=False)
    else:
        if sha(armdir/'native-zero-v1/report.json')!=admission['own_zero_report_sha256']:raise ValueError('Own zero report changed')
    with (root/'own-wrapper.claim').open('x') as stream:stream.write('One actual '+a.mode+' invocation; no retries\n')
    started=time.monotonic();recorder=None;hookevents=None;out=None
    try:
        if a.arm=='B':
            from mujoco_zyh import stall_stow
            from mujoco_zyh.reach_phe_hook import bind_owned_fork
            hookevents=(root/'PHE-actual-decisions.jsonl').open('x')
            def emit(row):hookevents.write(json.dumps(row,separators=(',',':'))+'\n');hookevents.flush()
            binding=bind_owned_fork(stall_stow,owned_source_root=source,enabled=True,emit=emit)
        else:binding=dict(enabled=False,baseline_original_stall_module=True)
        from mujoco_zyh.observer import OnboardObserver
        from native_video import NativeCameraVideo
        recorder=NativeCameraVideo(root,p['width'],p['height'],10.)
        original=OnboardObserver.capture
        def native_capture(self,*args,**kwargs):
            packet,catalog=original(self,*args,**kwargs)
            rgb=packet['rgb'].detach().cpu().numpy()[0,0]
            t=float(packet['timestamps_s'][0,0])
            recorder.write(rgb,t)
            return packet,catalog
        OnboardObserver.capture=native_capture
        if a.mode=='zero':
            from mujoco_zyh.preflight import run
            probe=run(Path('/mnt/yuanyue/data/go2-piper-world-model/zyh-mujoco-source-340d7d8-v1'),p,Path(p['resource_lock_dir']))
            if (probe.get('passed') is not True or probe.get('native_physics_steps')!=0
                    or probe.get('actual_world_time_s')!=0. or probe.get('auxiliary_calibration_worlds')!=0
                    or probe.get('validated_protocol')!=p):
                raise ValueError('Own zero is incomplete or advanced actual physics')
            save(root/'native-probe.json',probe)
            out=dict(status='OWN_ACTUAL_NATIVE_ZERO_PASS',passed=probe['passed'],actual_native_step_count=probe.get('native_physics_steps'),
                     source_id=p['source_id'],hook=binding,API_calls=0,main_dispatched=False,
                     source_freeze_sha256=sha(armdir/'source-freeze.json'),validated_protocol=p,
                     actual_probe_sha256=sha(root/'native-probe.json'),
                     own_CPU_qualification_sha256=sha(qualified_log.with_suffix('.json')),
                     CPU_qualification_type=cpu.get('qualification_method','original_single_run'),
                     own_runtime_freeze_sha256=sha(release/'runtime-source-freeze.json'))
        else:
            # Secure credentials must already be supplied by the established
            # mechanism; never scan/copy another chat's key or print its value.
            if not os.environ.get('DEEPSEEK_API_KEY'):raise ValueError('Original task API key not supplied to this process; no key search or probe')
            from mujoco_zyh.collect import run
            run(root,Path('/mnt/yuanyue/data/go2-piper-world-model/zyh-mujoco-source-340d7d8-v1'))
            out=dict(status='ORIGINAL_COLLECTOR_RETURNED',original_report_sha256=sha(root/'report.json'),source_id=p['source_id'],hook=binding)
    except Exception as exc:
        out=dict(status='FAILED_NO_RETRY',error=repr(exc),traceback=traceback.format_exc(),mode=a.mode,main_success_NOT_claimed=True)
        raise
    finally:
        if recorder is not None:
            try:recorder.close()
            except Exception as exc:
                if out is None:out={}
                out['native_video_error']=repr(exc);out['status']='FAILED_NATIVE_RECORDING'
        if hookevents is not None:hookevents.close()
        if out is not None:
            out['wrapper_wall_s']=time.monotonic()-started;save(root/'wrapper-report.json',out)
        if a.mode=='zero' and out and out.get('status')=='OWN_ACTUAL_NATIVE_ZERO_PASS':save(root/'report.json',out)
    print(json.dumps({k:v for k,v in out.items() if k not in ('validated_protocol','traceback')},indent=2))
    if out.get('status','').startswith('FAILED'):raise RuntimeError('Own invocation failed; preserve exact root')


if __name__=='__main__':main()
