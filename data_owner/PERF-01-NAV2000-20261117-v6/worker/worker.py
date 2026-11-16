"""NEW 2000-command NAV-prefix performance worker; NOT an E20 retry/launcher.

Off by default; prepare/zero/main require a separately registered exact program.
No old run state/root is loaded. Source/Actor/dt/goals/native safety stay original.
The window stops BEFORE the old first PUSH (~15.095s), not at the failed brake.
This file being implemented does not assert native qualification or dispatch.
"""
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import os
import resource
import signal
import sys
import time
import traceback

OWNER='01a1e4e1-3037-7333-9019-a3f37effe5da'
EXPECTED_BASE_SOURCE='04a9c0fe82fdb7d619b7507d5b554c133572af40'
QUESTION='SAME_SCENE_FIRST_2000_NAV_COMMANDS_NEW_AUDIT_POLICY_PERFORMANCE_NOT_E_RETRY'

def need(value,message):
    if not value:raise RuntimeError(message)

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def now():return datetime.datetime.now().astimezone().isoformat()

def prepare(config_path=None,pin=None,*,enabled=False):
    if enabled is not True:return None
    c=json.loads(Path(config_path).read_bytes())
    need(c['GPU_UUID']=='GPU-297c1146-bcec-a8ee-8437-d9603392a2e1','Authorized physical GPU0 only')
    need(c['model_sha256']=='ed6267bbaa7fa0e0dda0906f5e55f4abbf2c129d1b9ee5ffa0f17e54490934b1'and c['scene_sha256']=='08a260a4bda6de75e1f0012e12a4a3a04a5c682b0534f785a7b504af4a666381','Same original E20 static scene/asset, not restored state')
    need(c['question']==QUESTION and c['source_commit']==EXPECTED_BASE_SOURCE,'Explicit unchanged same-source NAV-prefix question')
    need(c['measure_task_steps']==2000 and c['measure_task_sim_s']==10.,'Not full E/another brake attempt or post-outcome step sweep')
    need(c['scope_id'].startswith('data-46308-perf-NAV2000-') and 'E20-prearrival40'not in c['scope_id'],'Distinct performance scope, never reopen old family')
    need(c['seed']is None or type(c['seed'])is int and 0<=c['seed']<2**32,'Explicit seed or truthful source-default unrecorded reference')
    need(c['own_zero_max']==c['main_max']==1 and c['training_allowed']is False,'Finite technical zero/performance window, not training')
    need(sha(c['freeze_path'])==pin,'Exact new complete program freeze')
    freeze=json.loads(Path(c['freeze_path']).read_bytes())
    need(freeze['question']==QUESTION and freeze['scope_id']==c['scope_id'],'Freeze question/identity')
    for name,digest in freeze['files'].items():
        p=Path(name);need(not p.is_symlink()and sha(p)==digest,'Frozen new-program file drift: '+name)
    need(sys.prefix=='/mnt/yuanyue/data-team/env-native-v1'and sys.version_info[:3]==(3,11,16),'Original private interpreter')
    need(os.environ.get('CUDA_VISIBLE_DEVICES')==c['GPU_UUID']and os.environ.get('MUJOCO_GL')=='egl'and os.environ.get('MUJOCO_EGL_DEVICE_ID')=='0','Original GPU UUID/EGL binding')
    need(os.environ.get('LD_PRELOAD')==c['LD_PRELOAD'],'Original private loader')
    need(c['output_cap_bytes']==1<<30 and c['reserve_bytes']==64<<20,'Aggregate scope budget includes both phases/output/FDs/reports/encoder')
    policy=c['gl_runtime_mapping_policy'];auth=json.loads(Path(c['authorization']).read_bytes())
    need(auth['owner']==OWNER and auth['scope_id']==c['scope_id'] and auth['gl_runtime_mapping_policy']==policy,
        'New real maintenance owner explicitly authorizes this exact runtime RX policy; not historical binding owner')
    evidence=Path(c['gl_mapping_evidence_path'])
    need(freeze['files'].get(str(evidence))==policy['evidence_result_sha256'] and sha(evidence)==policy['evidence_result_sha256'],
        'Real closed GPU-library diagnostic evidence is pinned, not a policy label')
    evidence_rows=json.loads(evidence.read_bytes())['loaded_driver_file_identity']
    need(policy['driver_files_sha256']=={row['path']:row['sha256'] for row in evidence_rows} and len(evidence_rows)==9,
        'All nine actual observed driver file identities, not fixture pins')
    need(all(freeze['files'].get(p)==v for p,v in policy['driver_files_sha256'].items()),'All evidenced driver libraries pinned in new program')
    need(c['guard_source_SHA'] in freeze['files'].values(),'Explicit selected identity-guard source SHA, not commit-directory trust')
    # Paths are explicit frozen new-program copies / original read-only sources.
    sys.path[:0]=c['import_paths']
    need(Path.cwd()==Path(c['program_cwd']),'Explicit stable new program cwd, never synthetic files under /root')
    import e_entry,native_entry,private_catalog_boundary,per_gpu_lease,raw_third_view
    from partial_constructor import PartialObjects,build_receipted_constructor,build_receipted_entry
    need(c['partial_constructor_overlay'] is True,'Explicit changed lifecycle bytecode new-program policy')
    receipt=PartialObjects()
    inner=build_receipted_constructor(native_entry._bound_original('construct_cold_components'),
        receipt,source_path=c['partial_base_source'],enabled=True)
    outer=build_receipted_entry(native_entry,receipt,source_path=c['partial_base_source'],
        entry_sha256=freeze['files'][str(Path(native_entry.__file__))],enabled=True)
    need(inner(enabled=False)is None and outer(enabled=False)is None and receipt.runtime is None
        and receipt.observer is None,'Actual constructor overlays default-off CPU qualification; no world')
    # CPU-only import/path qualification catches the observed real package-root
    # omission before another native construction, without hashing full env.
    import torch,numpy,mujoco,PIL,importlib
    from PIL import Image
    need(c['PIL_preinit_required'] is True,'Exact prior main lazy-PNG failure corrected before seal')
    Image.preinit()  # Same original PNG encoder/plugin path, no output or native calls.
    for module_name in c['reviewed_preload_modules']:importlib.import_module(module_name)
    from indexed_guard import module_paths
    roots=tuple(Path(r).resolve(strict=True)for r in c['inventory_roots'])
    missing=set(c['explicit_missing_module_paths'])
    for module_name,raw in [('torch.ops','_ops.py'),('torch.classes','_classes.py')]:
        need(getattr(sys.modules[module_name],'__file__',None)==raw and not Path(raw).exists()
            and str(Path(raw).absolute())in missing,'Exact observed torch synthetic file slot, never arbitrary missing source')
    for raw in module_paths():
        absolute=str(Path(raw).absolute());canonical=Path(raw).resolve()
        need(any(canonical.is_relative_to(root)for root in roots),'CPU-loaded module outside exact actual roots: '+raw)
        need(canonical.is_file()or absolute in missing,'CPU-loaded file absent without explicit synthetic slot: '+raw)
    need(not torch.cuda.is_initialized(),'Prepare must not initialize CUDA, Actor, renderer or physics')
    need(e_entry.build_E_driver(enabled=False)is None and native_entry.construct_cold_components(enabled=False)is None,'Actual source default-off import preflight before own-zero')
    return c,freeze

def run(config_path=None,pin=None,phase=None,*,enabled=False):
    if enabled is not True:return None
    need(phase in('zero','main'),'Explicit own-zero or NAV performance main')
    start=time.monotonic();c,freeze=prepare(config_path,pin,enabled=True)
    H=Path(c['handoff']);AUTH=Path(c['authorization']);S=Path(c['runtime_root'])/c['scope_id'];ROOT=S/phase
    def authority():
        h=json.loads(H.read_bytes());q=h[c['authority_key']];a=json.loads(AUTH.read_bytes())
        need(h['executing_thread_id']==q['owner']==OWNER and q['active']and q['scope_id']==c['scope_id'],'Actual new performance owner/scope')
        need(not h['bulk24_collector_v1']['global_stop'],'Shared source/resource stop')
        need(q['authorization_sha256']==sha(AUTH)and a['owner']==OWNER and a['scope_id']==c['scope_id'] and a['question']==QUESTION and a['own_zero_max']==a['main_max']==1,'Exact new performance authority')
        need(all(not v['active']for k,v in h.items()if k.startswith('active_')and k!=c['authority_key']and isinstance(v,dict)and'active'in v),'No second active Data physical scope')
        need(q['zero_dispatch_count']==1 and (phase=='zero'and q['main_dispatch_count']==0 or phase=='main'and q['main_dispatch_count']==1 and q['zero_passed']and q['camera_sha256']is not None),'Own actual zero before one new main')
        need(q['whole_program_freeze_sha256']==pin,'Exact dispatched whole-program pin')
        return q
    q=authority();need(not ROOT.exists(),'Never reopen phase/root')
    if phase=='main':
        need(S.is_dir()and sha(S/'zero/result.json')==q['zero_result_sha256'],'Actual own-zero files still present and exact')
        zero=json.loads((S/'zero/result.json').read_bytes());need(zero['passed']and zero['program_sha256']==pin,'Same-program actual own-zero required')
        need(sha(S/'zero/camera.png')==zero['own_zero_camera']['image_sha256'],'Actual own-zero image still exact, never substitute old-scope PNG')
    # One aggregate in-process counter covers scope/zero + scope/main + captures.
    # Existing zero files are bootstrap-measured, immutable during main.
    S.mkdir(parents=True,exist_ok=phase=='main');ROOT.mkdir()
    from scoped_io import ScopeIO,StopState
    from runner_outputs import write_json,write_png,finish_accounting
    from fd_capture import FDCapture
    from resource_watch import ResourceWatch
    from timed_probe import make_timed_scope_probe
    from partial_constructor import PartialObjects,build_receipted_entry
    from fast_health import make_original_fast_health
    from private_writer_binding import load_private_writer
    from observation_io import load_controlled_publisher,bind_fresh_observation_outputs
    from install_fresh_driver import install,data_resource_watch_callbacks
    from indexed_guard import FrozenFiles,module_paths
    from library_maps import executable_file_maps
    from per_gpu_lease import PerGpuLease
    from private_catalog_boundary import PrivateCatalogBoundaryWriter
    for name in ('scoped_io','runner_outputs','fd_capture','resource_watch','fast_health','private_writer_binding','observation_io','install_fresh_driver','indexed_guard','per_gpu_lease','private_catalog_boundary','library_maps','timed_probe','partial_constructor'):
        path=Path(sys.modules[name].__file__);need(str(path)in freeze['files']and sha(path)==freeze['files'][str(path)],'No ambient unpinned execution helper: '+name)
    need(sha(sys.modules['indexed_guard'].__file__)==c['guard_source_SHA'],'Exact selected guard implementation')
    partial=PartialObjects();resource_probe=None
    state=StopState();budget=ScopeIO(S,cap_bytes=c['output_cap_bytes'],reserve_bytes=c['reserve_bytes'],state=state)
    # FDCapture filenames are relative to its budget. Keep phases disjoint by
    # explicit scoped paths, never use a second/forked counter over the same tree.
    capture=None;watch=None;lease=None;runtime=None;observer=None;writer=None;driver=None
    journal=None;video=None;progress=None;health=None;errors=[];step_walls=[];call_walls=[];loop_start=None
    cap=c['zero_wall_cap_s']if phase=='zero'else c['main_wall_cap_s']
    result=dict(question=QUESTION,scope_id=c['scope_id'],phase=phase,program_sha256=pin,
        started_at=now(),PID=os.getpid(),seed=c['seed'],old_seed_not_recorded_comparability_unknown=True,passed=False,full_task_success=False,
        not_E_task_retry_or_new_skill_fix_evidence=True,training_allowed=False,
        VLM_calls=0,WM_calls=0,automatic_retry=False,source_commit=c['source_commit'])
    def guard():
        if watch is not None:return watch()
        authority();state.check()
        if health is not None:health()
    def report(name,value):write_json(budget,ROOT/name,value)
    def timeout(*_):raise RuntimeError('Original hard wall deadline; no retry')
    signal.signal(signal.SIGALRM,timeout);signal.setitimer(signal.ITIMER_REAL,cap-10)
    resource.setrlimit(resource.RLIMIT_CORE,(0,0));os.nice(15)
    try:
        capture=FDCapture(budget,stdout_path=ROOT/'stdout.bin',stderr_path=ROOT/'stderr.bin',enabled=True)
        report('claim.json',dict(at=now(),PID=os.getpid(),scope_id=c['scope_id'],phase=phase,program_sha256=pin))
        import torch
        import numpy as np
        from PIL import Image
        import random
        if c['seed']is not None:random.seed(c['seed']);np.random.seed(c['seed']);torch.manual_seed(c['seed'])
        torch.set_num_threads(2)
        health=make_original_fast_health(torch,state=state,start_mono=start,wall_cap_s=cap,
            rss_cap_bytes=c['own_RSS_cap_bytes'],gpu_cap_bytes=c['own_GPU_cap_bytes'])
        lease=PerGpuLease(physical_index=0,authority_check=authority).__enter__()
        report('resource-lease.json',dict(locks=lease.rows,GPU=lease.last_gpu))
        import shutil
        resource_probe=make_timed_scope_probe(lease,budget,min_free_bytes=c['disk_floor_bytes'],
            disk_free=lambda root:shutil.disk_usage(root).free,enabled=True)
        frozen_ELF=None
        def probe():
            resource_probe()  # exactly ONE original lease/authority/GPU/disk/reconcile composite
            if frozen_ELF is not None:
                current=executable_file_maps(c['gl_runtime_mapping_policy'])
                if current!=frozen_ELF:state.fail('Executable mapping changed after bootstrap; before='+json.dumps(frozen_ELF.record(),sort_keys=True)+'; after='+json.dumps(current.record(),sort_keys=True))
        def phase_health():
            health()
            option=None if driver is None or driver.executor is None else driver.executor.option
            if option is not None and option.skill!='NAV':
                state.fail('NAV-only performance scope forbids PUSH/CLIMB physical execution')
            return True
        watch=ResourceWatch(probe,state=state,token=object(),fast_health=phase_health).start()
        import importlib
        for module_name in c['reviewed_preload_modules']:importlib.import_module(module_name)
        source=Path(c['common_source'])
        streams=load_private_writer(source/'mujoco_zyh/streams.py',c['streams_SHA'],budget,
            name='_data_perf_private_streams',package='mujoco_zyh',enabled=True)
        evidence=load_private_writer(source/'ainav/evidence.py',c['evidence_SHA'],budget,
            name='_data_perf_private_journal',package='ainav',enabled=True)
        raw=load_private_writer(c['raw_source'],c['raw_SHA'],budget,name='_data_perf_private_raw',enabled=True)
        publisher=load_controlled_publisher(source/'ainav/native/observation.py',c['publisher_SHA'],budget,
            name='_data_perf_private_publisher',enabled=True)
        journal=evidence.Journal(ROOT/'events.jsonl')
        import native_entry,e_entry
        for module in(native_entry,e_entry):
            path=Path(module.__file__);need(str(path)in freeze['files']and sha(path)==freeze['files'][str(path)],'No ambient native/E source entry')
        construct=build_receipted_entry(native_entry,partial,source_path=c['partial_base_source'],
            entry_sha256=freeze['files'][str(Path(native_entry.__file__))],enabled=True)
        components=construct(source_root=source,bundle=Path(c['SDK']),
            model_path=Path(c['model_path']),model_sha256=c['model_sha256'],scene_path=Path(c['scene_path']),
            expected_scene_sha256=c['scene_sha256'],guard=guard,journal=journal,actor_device='cuda:0',enabled=True)
        runtime=components['runtime'];observer=components['observer']
        need(runtime is partial.runtime and observer is partial.observer,'Actual partial receipt and returned components must be same objects')
        need(runtime.step_count==0 and float(runtime.sim.data.time)==0 and not runtime.sim.queue,'Fresh task0/FIFO, never restored world')
        need(runtime.wm_auxiliary_calibration['worlds']==1 and runtime.wm_auxiliary_calibration['sim_seconds']<=10.5,'Original separately accounted auxiliary stance')
        meta=dict(c['recorder_metadata'],source_id=c['scope_id'],episode_id=c['scope_id']+'-'+phase,
            source_group=c['scope_id'],role='PERFORMANCE_WINDOW_NOT_TRAINING',forecast_study_training_authorized=False,
            joint_names=runtime.push['model'].JOINTS,program_sha256=pin,whole_artifact_model_input_allowed=False)
        writer=PrivateCatalogBoundaryWriter(streams.ChunkedEpisodeWriter(ROOT/'episode',meta))
        driver=e_entry.build_E_driver(components,source_root=source,bundle=Path(c['SDK']),output_root=ROOT,
            writer=writer,journal=journal,guard=guard,enabled=True)
        need(driver.planner.__class__.__name__=='RuleBaseline'and driver.planner.method=='E_public_geometry_engineering_rule_v1','Exact original rule, not a new planner')
        bind_fresh_observation_outputs(driver,publisher,budget,enabled=True)
        chosen=c['camera_spec'];camera=raw.LiveMuJoCoCamera(runtime,chosen,snapshot=observer.snapshot,unchanged=observer.unchanged)
        if phase=='zero':
            try:
                tick,stamp,rgb=camera.frame();need(tick==0 and stamp==0,'Own-zero camera must not step task')
                write_png(budget,ROOT/'camera.png',Image.fromarray(rgb))
                result['own_zero_camera']=dict(image_path=str(ROOT/'camera.png'),image_sha256=sha(ROOT/'camera.png'),physical_tick=tick,actual_sim_time_s=stamp,spec=chosen,spec_sha256=hashlib.sha256(json.dumps(chosen,sort_keys=True).encode()).hexdigest())
                report('camera-choice.json',result['own_zero_camera'])
            finally:camera.close()
        else:
            need(hashlib.sha256(json.dumps(chosen,sort_keys=True).encode()).hexdigest()==q['camera_sha256'],'Own-zero frozen same camera')
            video=raw.OptionalRawThirdView(ROOT/'direct-third-view',enabled=True,source_factory=lambda:camera,
                scope_id=c['scope_id'],episode_id=c['scope_id']+'-main',program_sha256=pin)
            need(video.status=='CAPTURING','Qualified original direct live recorder')
            video.capture_if_due()
        # Perform the ORIGINAL first task0 RGBD review at its original tick/time.
        # The original idempotent last_capture_tick prevents duplication at step0.
        # This warms the real depth/RGB GL path before hashing generated dispatch.
        driver.capture_grid()
        need(runtime.step_count==0 and float(runtime.sim.data.time)==0. and not runtime.sim.queue,'Task0 actual RGBD review cannot advance physics')
        # ALL private IO bindings/camera/native dependencies are now loaded.
        # Complete ELF/dlopen closure and exact source pins must be supplied by
        # the new freeze; this adapter never pretends module.__file__ is closure.
        frozen_ELF=executable_file_maps(c['gl_runtime_mapping_policy'])
        result['ELF_mapping_snapshot']=frozen_ELF.record()  # Preserve identity even if following inventory fails.
        inventory_start=time.monotonic()
        inventory=FrozenFiles.measure([*module_paths(),*c['frozen_inventory_paths'],*frozen_ELF],roots=c['inventory_roots'],
            expected_hashes=freeze['files'],allow_missing=c['explicit_missing_module_paths'])
        result['bootstrap_inventory_mainthread_wall_s']=time.monotonic()-inventory_start
        fast,ack=data_resource_watch_callbacks(watch,epoch=c['scope_id']+':'+pin)
        def tokens(host):
            session=None if host.executor is None else host.executor.session
            option=None if host.executor is None else host.executor.option
            target=None if option is None else option.target_ref
            original_goal=None if session is None else session.original_goal
            return dict(session=session,target=target,goal=original_goal,option=option,
                original_goal_sha=None if session is None else session.goal_sha,task_instruction=host.scene['task']['instruction'],
                config_epoch=pin,queue=host.r.sim.queue,writer=host.writer,
                publisher=host.publisher,publish=host.publisher.publish,output_root=host.root,
                owner_guard=host.owner_guard)
        result['ELF_mapping_snapshot']=frozen_ELF.record()
        result['ELF_file_inventory_paths']=sorted(frozen_ELF)
        result['ELF_policy']='Named files SHA bootstrap + only evidenced EGL8192B memfd RX snapshot; RX identity/bytes changes fail at1s probe/oldest<=2s. Generated bytes are not file SHA or root/native-memory/supply-chain proof'
        seal_start=time.monotonic()
        result['identity_bootstrap']=install(driver,enabled=True,files=inventory,owner_fast=fast,owner_refresh=ack,tokens=tokens)
        result['bootstrap_seal_mainthread_wall_s']=time.monotonic()-seal_start
        report('identity-bootstrap.json',result['identity_bootstrap'])
        if phase=='zero':
            need(runtime.step_count==0 and not runtime.sim.queue,'Own-zero has no task commands')
            result.update(passed=True,status='OWN_ZERO_TASK0_IO_IDENTITY_READY_NOT_MAIN')
        else:
            progress=budget.open(ROOT/'progress.jsonl','x',encoding='utf-8')
            loop_start=time.monotonic()
            while runtime.step_count<c['measure_task_steps']:
                guard();before=runtime.step_count;t=time.perf_counter()
                try:driver.step_one()
                finally:
                    if runtime.step_count>before:video.capture_if_due()
                    elapsed=time.perf_counter()-t;call_walls.append(elapsed)
                    if runtime.step_count>before:step_walls.append(elapsed)
                if runtime.step_count>before and runtime.step_count%400==0:
                    progress.write(json.dumps(dict(at=now(),task_steps=runtime.step_count,time_s=float(runtime.sim.data.time),wall_s=time.monotonic()-loop_start))+'\n');progress.flush()
                need(not driver.complete,'Performance prefix unexpectedly completed full E')
            need(runtime.step_count==2000 and abs(float(runtime.sim.data.time)-10.)<1e-7,'Exact frozen NAV2000 performance window')
            window_end=time.monotonic()
            result.update(passed=True,status='PERFORMANCE_WINDOW_COMPLETE_TASK_INTENTIONALLY_NOT_COMPLETE',
                window_wall_s=window_end-loop_start,scope_start_to_window_end_wall_s=window_end-start,initialization_wall_s=loop_start-start,step_wall_quantiles_s={str(p):float(np.quantile(step_walls,p))for p in(.5,.95,.99,1.)},
                driver_call_count=len(call_walls),actual_command_count=len(step_walls),driver_call_quantiles_s={str(p):float(np.quantile(call_walls,p))for p in(.5,.95,.99,1.)},task_intentionally_censored_at_preregistered_window=True)
    except BaseException as e:
        # Actual references were handed off before later constructor/postcheck errors.
        # No reset/replay, source inference, old-zero substitution or resumed native.
        if runtime is None:runtime=partial.runtime
        if observer is None:observer=partial.observer
        result['partial_construction_receipt']=partial.usage_snapshot()
        result.update(status='PERFORMANCE_SETUP_OR_WINDOW_FAILED_NO_RETRY',error=repr(e),traceback=traceback.format_exc(),native_skill_failure_not_inferred=True)
    finally:
        if phase=='main'and loop_start is not None:
            result['scope_start_to_last_driver_boundary_wall_s']=time.monotonic()-start
            result['loop_to_last_driver_boundary_wall_s']=time.monotonic()-loop_start
        budget.begin_finalization()  # Same shared state: NO new native steps.
        # Keep the hard wall timer active through cleanup; never silently unbound.
        if watch is not None:
            try:watch.close()
            except BaseException as e:errors.append(dict(stage='watch_close',error=repr(e)))
        if progress is not None:
            try:progress.close()
            except BaseException as e:errors.append(dict(stage='progress_close',error=repr(e)))
        if resource_probe is not None and resource_probe.last_attempt is not None:
            attempt=resource_probe.last_attempt
            result['resource_probe_attempt']=dict(started=attempt.started,completed=attempt.completed,
                stages=[dict(name=name,started=before,completed=after,wall_s=after-before)
                    for name,before,after in attempt.stages],error=attempt.error,
                diagnostic_only_not_owner_freshness=True,real_original_lease_composite_called_once=True)
        if watch is not None:
            result['resource_watch_metrics']=dict(check_calls=watch.check_calls,probe_calls=watch.probe_calls,probe_wall_s=watch.probe_wall_s,oldest_completed_pair=watch.last_observation_stamp,probe_wall_inclusive_background_not_exclusive=True)
        if driver is not None:
            result['identity_metrics']=dict(type(driver)._native_guards.engine.metrics)
            try:driver.close_metadata_workers()
            except BaseException as e:errors.append(dict(stage='identity_close',error=repr(e)))
        if writer is not None:
            try:result['episode_closure']=writer.close(outcome=result['status'],terminal_time_s=float(runtime.sim.data.time),censored=phase=='main'or not result['passed'])
            except BaseException as e:errors.append(dict(stage='writer_close',error=repr(e)))
        if video is not None:
            try:result['direct_video_raw_closure']=video.close()
            except BaseException as e:errors.append(dict(stage='raw_close',error=repr(e)))
        if observer is not None:
            try:observer.close()
            except BaseException as e:errors.append(dict(stage='observer_close',error=repr(e)))
        if journal is not None:
            try:journal.close()
            except BaseException as e:errors.append(dict(stage='journal_close',error=repr(e)))
        partial_usage=partial.usage_snapshot()
        result['partial_construction_receipt']=partial_usage
        result.update(actual_task_steps=partial_usage['actual_task_steps'],
            actual_task_sim_s=partial_usage['actual_task_sim_s'],
            actual_auxiliary_calibration=partial_usage['actual_auxiliary_calibration'])
        if runtime is not None and not partial_usage['usage_known']:
            errors.append(dict(stage='partial_usage_unknown',error=partial_usage.get('accounting_error','Actual fields unavailable')))
        if lease is not None:
            try:result['final_GPU']=lease.check(force=True)
            except BaseException as e:errors.append(dict(stage='final_GPU',error=repr(e)))
            lease.__exit__()
        if phase=='main'and video is not None and getattr(video,'closed',False)and video.closure.get('complete_for_capture_grid'):
            try:
                from controlled_encoder import encode_raw_master
                result['encoded_direct_video']=encode_raw_master(raw,ROOT/'direct-third-view',budget,
                    ffmpeg=c['ffmpeg_path'],ffmpeg_sha256=c['ffmpeg_sha256'],ffprobe=c['ffprobe_path'],
                    ffprobe_sha256=c['ffprobe_sha256'],timeout_s=min(180.,max(.1,cap-(time.monotonic()-start)-10.)),enabled=True)
                report('video-encoding-result.json',result['encoded_direct_video'])
            except BaseException as e:errors.append(dict(stage='controlled_encoder',error=repr(e)))
        if capture is not None:
            try:result['FD_capture']=capture.close()
            except BaseException as e:result['FD_capture']=getattr(e,'receipt',capture.snapshot());errors.append(dict(stage='FD_close',error=repr(e)))
        if health is not None:result['original_fast_health']=dict(health.metrics)
        result.update(close_errors=errors,wall_s=time.monotonic()-start,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            resource_failure=state.reason,output_budget_before_result=budget.snapshot(),usage_known=partial_usage['usage_known'],
            actual_task_success_claimed=False,system_5x_qualified=False)
        if errors or state.reason:result['passed']=False
        report('result.json',result)
        report('ledger.json',dict(scope_id=c['scope_id'],phase=phase,closed=True,result_sha256=sha(ROOT/'result.json'),
            output_controlled_logical_bytes_before_ledger=budget.used,wall_s=result['wall_s'],usage_known=result['usage_known'],main_calls=int(phase=='main'),automatic_retry=False))
        result['final_accounting']=finish_accounting(budget,ROOT/'final-output-accounting.json')
        signal.setitimer(signal.ITIMER_REAL,0)
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--enabled',action='store_true');p.add_argument('--config');p.add_argument('--program-sha256');p.add_argument('--phase',choices=('prepare','zero','main'));args=p.parse_args()
    if args.enabled:
        if args.phase=='prepare':prepare(args.config,args.program_sha256,enabled=True)
        else:sys.exit(0 if run(args.config,args.program_sha256,args.phase,enabled=True)['passed']else 1)
