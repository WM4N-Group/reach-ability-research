"""NEW PREPARED L0 live-bias-only FULL registered PUSH parent, default OFF; no old scope/AUTH/zero reuse.

Original resource/identity/IO/video/finally lifecycle; direct original camera-only
Runtime and registered safety chain. Complete new freeze/actual prepare/own zero
required. Source development alone grants no native/GPU/skill admission.
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

sys.path.insert(0,str(Path(__file__).resolve().parent))
if (Path(__file__).resolve().parent.parent/'push-standard-parent-20261118-v1/actor_trace.py').is_file():
    sys.path.insert(1,str(Path(__file__).resolve().parent.parent/'push-standard-parent-20261118-v1'))
for _name in ('push-original-L0-entry-20261118-v1','push-standard-parent-20261118-v1'):
    _support=Path(__file__).resolve().parent.parent/_name
    if _support.is_dir():sys.path.insert(1,str(_support))
from actor_trace import ActorTrace
from standard_runtime import ConstructionReceipt, assemble, bounded_exception
from push_l0_driver import driver_class, run_case, CaseLoopError
import registered_arm_ff  # Source-only dependency MUST exist before run helper gate.

OWNER='01a1e4e1-3037-7333-9019-a3f37effe5da'
EXPECTED_BASE_SOURCE='04a9c0fe82fdb7d619b7507d5b554c133572af40'
QUESTION='PUSH_PREPARED_L0_ONE_DEV_TERMINAL_ACTION_ORIGINAL_GUARDED_BRAKE'

def need(value,message):
    if not value:raise RuntimeError(message)

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def now():return datetime.datetime.now().astimezone().isoformat()

HELPER_NAMES = ('scoped_io', 'runner_outputs', 'fd_capture', 'resource_watch', 'fast_health', 'private_writer_binding', 'observation_io', 'boundary_install', 'indexed_guard', 'per_gpu_lease', 'private_catalog_boundary', 'library_maps', 'timed_probe', 'probe_history', 'standard_runtime', 'actor_trace', 'registered_trace', 'push_l0_driver', 'l0_startup', 'l0_witness', 'registered_arm_ff', 'lease_site_observer', 'connect_l0', 'public_geometry_provenance', 'metadata_prepare', 'public_descriptor_projection', 'query_bindings', 'query_prepare', 'zero_retirement', 'zero_retirement_fixture', 'selected_push_option', 'selected_option_prepare', 'direct_nvml', 'direct_held_check', 'direct_held_prepare', 'first_failure_chain', 'first_callback_prepare', 'clearance_prepare', 'terminal_action', 'native_connector', '_data_l0_original_standard_driver')


def _preload_and_verify_execution_helpers(freeze):
    # Same execution helper set as run, now also genuinely covered by CPU prepare.
    # Imports are source-only; no constructors, leases, world or Actor forward.
    import importlib
    for name in HELPER_NAMES:
        importlib.import_module(name)
    checked=[]
    for name in HELPER_NAMES:
        path=Path(sys.modules[name].__file__)
        need(not path.is_symlink() and str(path) in freeze['files'] and
             sha(path)==freeze['files'][str(path)],
             'CPU prepare execution-helper presence/source drift: '+name)
        checked.append((name,str(path)))
    return tuple(checked)


def prepare(config_path=None,pin=None,*,enabled=False):
    if enabled is not True:return None
    c=json.loads(Path(config_path).read_bytes())
    need(c['GPU_UUID']=='GPU-297c1146-bcec-a8ee-8437-d9603392a2e1','Authorized physical GPU0 only')
    need(c['question']==QUESTION and c['source_commit']==EXPECTED_BASE_SOURCE,'Original common control and explicit new original independent L0 question')
    need(c['scope_id']=='data-46308-PUSH-prepared-L0-terminal-connector-DEV-20261118-v10','New complete task, not a closed asset/D3 retry')
    need(c['GPU_transport']=='DIRECT_NVML_PRIVATE_ORIGINAL_HELD_CHECK_ONLY','Explicit direct GPU transport candidate')
    need(c['resource_probe_schedule']=='ACTUAL_START_NOMINAL_HALF_S' and c['resource_poll_s']==.5 and c['resource_oldest_max_age_s']==2.,'Explicit new cadence question, original oldest safety bound')
    need(sha(Path(c['program_cwd'])/'policy/resource_watch.py')==c['resource_watch_source_sha256'],'Exact previously CPU-reviewed future scheduler, no label-only policy')
    need(sha(c['prior_closed_result_path'])==c['prior_closed_result_sha256'],'Pinned earlier failure evidence, never reused as zero/authority/state')
    need(c['max_task_steps']==15000 and c['max_task_sim_s']==75. and c['max_driver_calls']==15200,'Full original task finite 75sim/15000steps/15200calls')
    need(c['boundary_only_no_task_skill'] is False and c['full_original_task_execution'] is True,'Explicit independent FULL registered PUSH question')
    need(c['public_task_geometry_provenance_required'] is True and c['metadata_constructor_CPU_prepare_required'] is True,'Actual new metadata constructor prepare and true public declaration provenance')
    need(c['public_query_and_watch_callsite_bindings_required'] is True and c['resource_oldest_max_age_s']==2.,'Explicit public query and .5s/2s watch caller binding required')
    need(c['original_lease_handoff_observation_SHA256']=='162178178e5078be271413026be3558c8326d49304c52309182352519271cb42' and c['new_original_lease_required_not_borrowed'] is True,'Actual prior resource ownership proof is not this program admission or zero')
    need(sha(c['peer_safe_phase_proof'])==c['peer_safe_phase_proof_SHA256'],'Frozen fresh peer terminal/release evidence')
    need(c['prepared_L0_only_difference']=='REGISTERED_SIX_ARM_LIVE_QFRC_BIAS_FF_ONLY' and c['unmodified_standalone_L0'] is False,'Only selected FF-only prepared-L0 difference; no pose/gain/target change')
    need(c['terminal_connector_DEV_action']=={'index':1,'lead_m':.08} and sha(c['terminal_pilot_spec_path'])==c['terminal_pilot_spec_sha256'],'One frozen DEV action, not a train sampler')
    need(c['seed']==3701 and c['delay_ms']==20,'Original fixed prospective initialization, no seed tuning')
    need(c['own_zero_max']==c['main_max']==1 and c['training_allowed']is False,'One new own-zero/main original independent L0 screen, no training')
    need(sha(c['freeze_path'])==pin,'Exact new complete program freeze')
    freeze=json.loads(Path(c['freeze_path']).read_bytes())
    need(freeze['question']==QUESTION and freeze['scope_id']==c['scope_id'],'Freeze question/identity')
    for name,digest in freeze['files'].items():
        p=Path(name);need(not p.is_symlink()and sha(p)==digest,'Frozen new-program file drift: '+name)
    need(sys.prefix=='/mnt/yuanyue/data-team/env-native-v1'and sys.version_info[:3]==(3,11,16),'Original private interpreter')
    need(os.environ.get('CUDA_VISIBLE_DEVICES')==c['GPU_UUID']and os.environ.get('MUJOCO_GL')=='egl'and os.environ.get('MUJOCO_EGL_DEVICE_ID')=='0','Original GPU UUID/EGL binding')
    need(os.environ.get('LD_PRELOAD')==c['LD_PRELOAD'],'Original private loader')
    need(c['output_cap_bytes']==4<<30 and c['reserve_bytes']==64<<20,'Aggregate scope budget includes both phases/output/FDs/reports/encoder')
    policy=c['gl_runtime_mapping_policy'];auth=json.loads(Path(c['authorization']).read_bytes())
    need(auth['owner']==OWNER and auth['scope_id']==c['scope_id'] and auth['gl_runtime_mapping_policy']==policy,
        'New real maintenance owner explicitly authorizes this exact runtime RX policy; not historical binding owner')
    need(auth['registered_case_reused'] is True and auth['new_diagnostic_question']==QUESTION,'Reuse original registered case under distinct finite question, no closed scope resume')
    need(auth['boundary_only_no_task_skill'] is False and auth['full_original_task_execution'] is True and auth['max_task_steps']==c['max_task_steps'] and auth['max_task_sim_s']==c['max_task_sim_s'] and auth['max_driver_calls']==c['max_driver_calls'] and auth['main_wall_cap_s']==c['main_wall_cap_s'],'Full task AUTH and exact finite caps')
    need(auth['GPU_transport']==c['GPU_transport'],'No inferred replacement authority')
    need(auth['resource_poll_s']==.5 and auth['resource_oldest_max_age_s']==2 and auth['resource_probe_schedule']=='ACTUAL_START_NOMINAL_HALF_S','New finite AUTH explicitly permits .5s actual START and unchanged two-second oldest')
    evidence=Path(c['gl_mapping_evidence_path'])
    need(freeze['files'].get(str(evidence))==policy['evidence_result_sha256'] and sha(evidence)==policy['evidence_result_sha256'],
        'Real closed GPU-library diagnostic evidence is pinned, not a policy label')
    evidence_rows=json.loads(evidence.read_bytes())['loaded_driver_file_identity']
    need(policy['driver_files_sha256']=={row['path']:row['sha256'] for row in evidence_rows} and len(evidence_rows)==9,
        'All nine actual observed driver file identities, not fixture pins')
    need(all(freeze['files'].get(p)==v for p,v in policy['driver_files_sha256'].items()),'All evidenced driver libraries pinned in new program')
    need(c['zero_wall_cap_s']==300 and c['main_wall_cap_s']==1800,'Selected new full standard case caps')
    sys.path[:0]=c['import_paths']
    from mujoco_zyh.source_bundle import verify_bundle
    sdk=verify_bundle(c['SDK'])
    need(sdk['verified_files']==148 and sdk['original_source_or_weights_modified']is False,'Exact ORIGINAL SDK, no D3 predicate fork')
    need(c['guard_source_SHA'] in freeze['files'].values(),'Explicit selected identity-guard source SHA, not commit-directory trust')
    # Paths are explicit frozen new-program copies / original read-only sources.
    sys.path[:0]=c['import_paths']
    need(Path.cwd()==Path(c['program_cwd']),'Explicit stable new program cwd, never synthetic files under /root')
    import private_catalog_boundary,per_gpu_lease,raw_third_view
    receipt=ConstructionReceipt()
    trace=ActorTrace(lambda:dict(root_skill='NOT_STARTED',native_phase='CPU_SOURCE_ONLY',task_step=0,task_sim_s=0.))
    build=assemble(source_root=c['common_source'],bundle=c['SDK'],trace=trace,receipt=receipt,enabled=True)
    cls=driver_class(source_root=c['common_source'],legacy_base_dir=c['legacy_base_dir'],legacy_guard_dir=c['legacy_guard_dir'],legacy_driver_source=c['legacy_driver_source'],enabled=True)
    need(build(enabled=False)is None and cls is not None and receipt.runtime is None,'CPU source assembly never constructs a world/Actor')
    # CPU-only import/path qualification catches the observed real package-root
    # omission before another native construction, without hashing full env.
    import torch,numpy,mujoco,PIL,importlib
    from PIL import Image
    need(c['PIL_preinit_required'] is True,'Exact prior main lazy-PNG failure corrected before seal')
    Image.preinit()  # Same original PNG encoder/plugin path, no output or native calls.
    for module_name in c['reviewed_preload_modules']:importlib.import_module(module_name)
    checked_helper_files=_preload_and_verify_execution_helpers(freeze)
    need(len(checked_helper_files)==len(HELPER_NAMES),'Every actual run helper must be CPU-qualified')
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
    need(assemble(enabled=False)is None and driver_class(enabled=False)is None,'Default-OFF actual new entry before own zero')
    return c,freeze

def run(config_path=None,pin=None,phase=None,*,enabled=False):
    if enabled is not True:return None
    need(phase in('zero','main'),'Explicit new own-zero or one original independent L0 main')
    start=time.monotonic();c,freeze=prepare(config_path,pin,enabled=True)
    H=Path(c['handoff']);AUTH=Path(c['authorization']);S=Path(c['runtime_root'])/c['scope_id'];ROOT=S/phase
    def authority():
        h=json.loads(H.read_bytes());q=h[c['authority_key']];auth_raw=AUTH.read_bytes();a=json.loads(auth_raw)
        need(h['executing_thread_id']==q['owner']==OWNER and q['active']and q['scope_id']==c['scope_id'],'Actual new original independent L0 owner/scope')
        need(not h['bulk24_collector_v1']['global_stop'],'Shared source/resource stop')
        need(not q.get('stop_requested',False),'Current original independent L0 scope was revoked; do not resume')
        need(q['authorization_sha256']==hashlib.sha256(auth_raw).hexdigest()and a['owner']==OWNER and a['scope_id']==c['scope_id'] and a['question']==QUESTION and a['own_zero_max']==a['main_max']==1,'Exact new original independent L0 authority')
        need(all(not v['active']for k,v in h.items()if k.startswith('active_')and k!=c['authority_key']and isinstance(v,dict)and'active'in v),'No second active Data physical scope')
        need(q['zero_dispatch_count']==1 and (phase=='zero'and q['main_dispatch_count']==0 or phase=='main'and q['main_dispatch_count']==1 and q['zero_passed']and q['camera_sha256']is not None),'Own actual zero before one new main')
        need(q['whole_program_freeze_sha256']==pin,'Exact dispatched whole-program pin')
        need(q.get(phase+'_PID')==os.getpid(),'Current authorized native phase PID, not historical binding/owner identity')
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
    from probe_history import ProbeHistory
    from standard_runtime import ConstructionReceipt
    from fast_health import make_original_fast_health
    from private_writer_binding import load_private_writer
    from observation_io import load_controlled_publisher,bind_fresh_observation_outputs
    from boundary_install import install,data_resource_watch_callbacks
    from indexed_guard import FrozenFiles,module_paths
    from library_maps import executable_file_maps
    from per_gpu_lease import PerGpuLease
    from private_catalog_boundary import PrivateCatalogBoundaryWriter
    for name in HELPER_NAMES:
        path=Path(sys.modules[name].__file__);need(str(path)in freeze['files']and sha(path)==freeze['files'][str(path)],'No ambient unpinned execution helper: '+name)
    need(sha(sys.modules['indexed_guard'].__file__)==c['guard_source_SHA'],'Exact selected guard implementation')
    partial=ConstructionReceipt();resource_probe=nvml_reader=direct_trace=None
    resource_cold_timeline={}
    probe_history=ProbeHistory(enabled=True,limit=128)
    state=StopState();budget=ScopeIO(S,cap_bytes=c['output_cap_bytes'],reserve_bytes=c['reserve_bytes'],state=state)
    # FDCapture filenames are relative to its budget. Keep phases disjoint by
    # explicit scoped paths, never use a second/forked counter over the same tree.
    capture=None;watch=None;lease=None;lease_entered=False;runtime=None;observer=None;writer=None;driver=None
    journal=None;video=None;progress=None;health=None;errors=[];loop_start=None;loop_receipt=None;trace=None
    cap=c['zero_wall_cap_s']if phase=='zero'else c['main_wall_cap_s']
    result=dict(question=QUESTION,scope_id=c['scope_id'],phase=phase,program_sha256=pin,
        started_at=now(),PID=os.getpid(),seed=c['seed'],old_seed_or_hidden_state_pair_not_claimed=True,passed=False,full_task_success=False,
        fresh_prepared_L0_original_case_geometry_with_live_arm_bias_only=True,training_allowed=False,
        VLM_calls=0,WM_calls=0,automatic_retry=False,source_commit=c['source_commit'])
    def guard():
        if watch is not None:return watch()
        authority();state.check()
        if health is not None:health()
    def report(name,value):write_json(budget,ROOT/name,value)
    def timeout(*_):raise RuntimeError('Original hard wall deadline; no retry')
    zero_timeline={}
    def zero_mark(name):
        if phase=='zero':zero_timeline[name]=time.monotonic()
    if phase=='zero':result['zero_lifecycle_monotonic_s']=zero_timeline
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
        lease=PerGpuLease(physical_index=0,authority_check=authority)
        from lease_site_observer import enter_once
        result['original_lease_site_observations']=[]
        enter_once(lease,result['original_lease_site_observations'])  # ONE exact original enter, no FD/lease borrowing.
        lease_entered=True
        report('resource-lease.json',dict(locks=lease.rows,GPU=lease.last_gpu))
        import shutil
        from direct_nvml import DirectNvml
        from direct_held_check import build_direct_held_check
        from types import SimpleNamespace
        resource_cold_timeline['direct_NVML_init_enter']=time.monotonic()
        nvml_reader=DirectNvml(enabled=True)
        resource_cold_timeline['direct_NVML_init_return']=time.monotonic()
        direct_check,direct_trace=build_direct_held_check(lease.check,nvml_reader.observe,enabled=True)
        resource_probe=make_timed_scope_probe(SimpleNamespace(check=direct_check),budget,min_free_bytes=c['disk_floor_bytes'],
            disk_free=lambda root:shutil.disk_usage(root).free,enabled=True)
        frozen_ELF=None
        def probe():
            def original_composite_and_ELF():
                resource_probe()  # ONE real original held/scope/disk composite with direct GPU transport
                if frozen_ELF is not None:
                    current=executable_file_maps(c['gl_runtime_mapping_policy'])
                    if current!=frozen_ELF:state.fail('Executable mapping changed after bootstrap; before='+json.dumps(frozen_ELF.record(),sort_keys=True)+'; after='+json.dumps(current.record(),sort_keys=True))
            return probe_history.call(original_composite_and_ELF)
        from query_bindings import construct_watch, check_phase_health
        def phase_health():
            option=None if driver is None or driver.executor is None else driver.executor.option
            return check_phase_health(health,state,c,phase,option)
        from zero_retirement import zero_watch_class
        watch_cls=zero_watch_class(ResourceWatch) if phase=='zero' else ResourceWatch
        watch,actual_watch=construct_watch(watch_cls,probe,state,phase_health,c)
        result['resource_watch_actual_configuration']=actual_watch
        watch.start()
        import importlib
        for module_name in c['reviewed_preload_modules']:importlib.import_module(module_name)
        from first_callback_prepare import verify_preloaded
        result['original_after_step_preload_source_sha256']=verify_preloaded(freeze)
        from clearance_prepare import verify_clearance_preload
        result['original_clearance_preload_source_sha256']=verify_clearance_preload(freeze)
        source=Path(c['common_source'])
        streams=load_private_writer(source/'mujoco_zyh/streams.py',c['streams_SHA'],budget,
            name='_data_perf_private_streams',package='mujoco_zyh',enabled=True)
        evidence=load_private_writer(source/'ainav/evidence.py',c['evidence_SHA'],budget,
            name='_data_perf_private_journal',package='ainav',enabled=True)
        raw=load_private_writer(c['raw_source'],c['raw_SHA'],budget,name='_data_perf_private_raw',enabled=True)
        publisher=load_controlled_publisher(source/'ainav/native/observation.py',c['publisher_SHA'],budget,
            name='_data_perf_private_publisher',enabled=True)
        journal=evidence.Journal(ROOT/'events.jsonl')
        trace=ActorTrace(lambda:driver.actor_context() if driver is not None else dict(
            root_skill='CONSTRUCTION',native_phase='CONSTRUCTION',task_step=partial.runtime.step_count,
            task_sim_s=float(partial.runtime.sim.data.time)))
        construct=assemble(source_root=source,bundle=c['SDK'],trace=trace,receipt=partial,enabled=True)
        resource_cold_timeline['original_runtime_construct_enter']=time.monotonic()
        components=construct(guard=guard,journal=journal,enabled=True)
        resource_cold_timeline['original_runtime_construct_return']=time.monotonic()
        runtime=components['runtime'];observer=components['observer']
        result['original_L0_construction']=components['construction']
        need(runtime is partial.runtime and observer is partial.observer,'Actual partial objects retained')
        need(runtime.step_count==0 and float(runtime.sim.data.time)==0. and not runtime.sim.queue,'Fresh original task0/FIFO')
        need(runtime.wm_auxiliary_calibration['worlds']==1 and runtime.wm_auxiliary_calibration['sim_seconds']<=10.5,'Original independent auxiliary calibration accounted separately')
        meta=dict(c['recorder_metadata'],source_id=c['scope_id'],episode_id=c['scope_id']+'-'+phase,
            source_group=c['scope_id'],role='PREPARED_L0_FULL_ORIGINAL_PUSH_PRIVATE_DEV_NOT_TRAINING',forecast_study_training_authorized=False,
            joint_names=runtime.push['model'].JOINTS,program_sha256=pin,whole_artifact_model_input_allowed=False)
        writer=PrivateCatalogBoundaryWriter(streams.ChunkedEpisodeWriter(ROOT/'episode',meta))
        cls=driver_class(source_root=source,legacy_base_dir=c['legacy_base_dir'],legacy_guard_dir=c['legacy_guard_dir'],legacy_driver_source=c['legacy_driver_source'],enabled=True)
        from terminal_action import BrakeAction
        components['terminal_connector_DEV_action']=BrakeAction(**c['terminal_connector_DEV_action'])
        result['terminal_connector_DEV_action']=c['terminal_connector_DEV_action']
        driver=cls(components,bundle=Path(c['SDK']),output_root=ROOT,writer=writer,journal=journal,guard=guard,trace=trace)
        bind_fresh_observation_outputs(driver,publisher,budget,enabled=True)
        chosen=c['camera_spec'];camera=raw.LiveMuJoCoCamera(runtime,chosen,snapshot=observer.snapshot,unchanged=observer.unchanged)
        if phase=='zero':
            try:
                tick,stamp,rgb=camera.frame();need(tick==0 and stamp==0,'Own-zero camera must not step task')
                write_png(budget,ROOT/'camera.png',Image.fromarray(rgb))
                result['own_zero_camera']=dict(image_path=str(ROOT/'camera.png'),image_sha256=sha(ROOT/'camera.png'),physical_tick=tick,actual_sim_time_s=stamp,spec=chosen,spec_sha256=hashlib.sha256(json.dumps(chosen,sort_keys=True).encode()).hexdigest())
                report('camera-choice.json',result['own_zero_camera'])
            finally:
                zero_mark('third_view_close_enter');camera.close();zero_mark('third_view_close_return')
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
        zero_mark('bootstrap_maps_enter')
        frozen_ELF=executable_file_maps(c['gl_runtime_mapping_policy'])
        zero_mark('bootstrap_maps_return')
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
        result['ELF_policy']='Named files SHA bootstrap + only evidenced EGL8192B memfd RX snapshot; RX identity/bytes changes fail at configured original real probe/oldest<=2s. Generated bytes are not file SHA or root/native-memory/supply-chain proof'
        seal_start=time.monotonic()
        result['identity_bootstrap']=install(driver,enabled=True,files=inventory,owner_fast=fast,owner_refresh=ack,tokens=tokens,boundary_only=False)
        result['bootstrap_seal_mainthread_wall_s']=time.monotonic()-seal_start
        report('identity-bootstrap.json',result['identity_bootstrap'])
        if phase=='zero':
            need(runtime.step_count==0 and not runtime.sim.queue,'Own-zero has no task commands')
            zero_mark('terminal_probe_ack_wait_enter')
            terminal_ack=watch.retire_for_zero()
            zero_mark('terminal_probe_ack_wait_return')
            budget.begin_finalization()
            zero_mark('acceptance_watch_close_enter')
            watch.close()  # the same existing .2s timeout, never converted to PASS
            zero_mark('acceptance_watch_close_return')
            need(not watch.thread.is_alive() and state.reason is None,'Zero requires joined watch and no latched failure')
            terminal_ack.update(sealed=True,watch_joined_before_observer_close=True)
            result['zero_lifecycle_retirement']=terminal_ack
            result.update(passed=True,status='OWN_ZERO_TASK0_IO_IDENTITY_READY_NOT_MAIN')
        else:
            loop_start=time.monotonic()
            try:
                loop_receipt=run_case(driver,watch=watch,budget=budget,video=video,scope_start_mono=start,enabled=True)
            except CaseLoopError as error:
                loop_receipt=error.receipt
                raise
            result.update(case_loop=loop_receipt,
                passed=bool(loop_receipt['full_case_success']),
                status=loop_receipt['stop_reason'],
                full_task_success=bool(loop_receipt['full_case_success']))
    except BaseException as e:
        # Actual references were handed off before later constructor/postcheck errors.
        # No reset/replay, source inference, old-zero substitution or resumed native.
        if runtime is None:runtime=partial.runtime
        if observer is None:observer=partial.observer
        result['partial_construction_receipt']=partial.usage_snapshot()
        primary=e.original_error if isinstance(e,CaseLoopError)else e
        from first_failure_chain import capture_failure
        engine=None if driver is None else type(driver)._native_guards.engine
        result['guard_failure_provenance']=capture_failure(primary,engine,bounded_exception)
        result.update(status='PREPARED_L0_FULL_ORIGINAL_STARTUP_ENTRY_NATIVE_OR_RESOURCE_STOP_NO_RETRY',error=bounded_exception(primary),native_skill_failure_not_inferred=True)
        if loop_receipt is not None:result['case_loop']=loop_receipt
    finally:
        if phase=='main'and loop_start is not None:
            result['scope_start_to_last_driver_boundary_wall_s']=time.monotonic()-start
            result['loop_to_last_driver_boundary_wall_s']=time.monotonic()-loop_start
        if not budget.finalizing:budget.begin_finalization()  # Same shared state; loop already seals on all exits.
        # Keep the hard wall timer active through cleanup; never silently unbound.
        if watch is not None and not result.get('zero_lifecycle_retirement',{}).get('watch_joined_before_observer_close',False):
            try:watch.close()
            except BaseException as e:errors.append(dict(stage='watch_close',error=bounded_exception(e)))
        if progress is not None:
            try:progress.close()
            except BaseException as e:errors.append(dict(stage='progress_close',error=bounded_exception(e)))
        if resource_probe is not None and resource_probe.last_attempt is not None:
            attempt=resource_probe.last_attempt
            result['resource_probe_attempt']=dict(started=attempt.started,completed=attempt.completed,
                stages=[dict(name=name,started=before,completed=after,wall_s=after-before)
                    for name,before,after in attempt.stages],error=attempt.error,
                diagnostic_only_not_owner_freshness=True,one_held_check_original_guards_with_direct_GPU_transport=True)
        result['resource_probe_history']=probe_history.snapshot()
        if watch is not None:
            result['resource_watch_metrics']=dict(check_calls=watch.check_calls,probe_calls=watch.probe_calls,probe_wall_s=watch.probe_wall_s,oldest_completed_pair=watch.last_observation_stamp,probe_wall_inclusive_background_not_exclusive=True)
        if driver is not None:
            result['identity_metrics']=dict(type(driver)._native_guards.engine.metrics)
            try:driver.close_metadata_workers()
            except BaseException as e:errors.append(dict(stage='identity_close',error=bounded_exception(e)))
        if writer is not None:
            try:result['episode_closure']=writer.close(outcome=result['status'],terminal_time_s=float(runtime.sim.data.time),censored=not result.get('full_task_success',False))
            except BaseException as e:errors.append(dict(stage='writer_close',error=bounded_exception(e)))
        if video is not None:
            try:result['direct_video_raw_closure']=video.close()
            except BaseException as e:errors.append(dict(stage='raw_close',error=bounded_exception(e)))
        if observer is not None:
            zero_mark('observer_close_enter')
            try:observer.close()
            except BaseException as e:errors.append(dict(stage='observer_close',error=bounded_exception(e)))
            else:zero_mark('observer_close_return')
        if journal is not None:
            try:journal.close()
            except BaseException as e:errors.append(dict(stage='journal_close',error=bounded_exception(e)))
        partial_usage=partial.usage_snapshot()
        result['partial_construction_receipt']=partial_usage
        result.update(actual_task_steps=partial_usage['task_steps'],
            actual_task_sim_s=partial_usage['task_sim_s'],
            actual_auxiliary_calibration=partial_usage['auxiliary'])
        if runtime is not None and not partial_usage['usage_known']:
            errors.append(dict(stage='partial_usage_unknown',error=partial_usage.get('accounting_error','Actual fields unavailable')))
        if lease is not None:
            result['lease_admission']=dict(entered=lease_entered,completed_canonical_rows=list(lease.rows),
                rows_are_historical_completions_not_current_holders=True,FDs_exported_or_borrowed=False)
        if direct_trace is not None:
            from dataclasses import asdict
            result['direct_GPU_transport']=dict(mode=c['GPU_transport'],GPU_read_calls=direct_trace.GPU_read_calls,
                tail=[asdict(row) for row in tuple(direct_trace.tail)],diagnostic_only_not_owner_stamp=True,
                original_enter_and_final_GPU_check_still_CLI=True)
        result['cold_native_timeline']=resource_cold_timeline
        still_probing=watch is not None and watch.thread is not None and watch.thread.is_alive()
        if still_probing:
            errors.append(dict(stage='live_probe_after_join_timeout',holding_resources_until_process_exit=True))
        else:
            if nvml_reader is not None:
                try:nvml_reader.close();result['direct_NVML_close_after_watch_join']=True
                except BaseException as e:errors.append(dict(stage='direct_NVML_close',error=bounded_exception(e)))
            if lease_entered:
                try:result['final_GPU']=lease.check(force=True)
                except BaseException as e:errors.append(dict(stage='final_GPU',error=bounded_exception(e)))
                lease.__exit__()
        if not still_probing and phase=='main'and video is not None and getattr(video,'closed',False)and video.closure.get('complete_for_capture_grid'):
            try:
                from controlled_encoder import encode_raw_master
                result['encoded_direct_video']=encode_raw_master(raw,ROOT/'direct-third-view',budget,
                    ffmpeg=c['ffmpeg_path'],ffmpeg_sha256=c['ffmpeg_sha256'],ffprobe=c['ffprobe_path'],
                    ffprobe_sha256=c['ffprobe_sha256'],timeout_s=min(180.,max(.1,cap-(time.monotonic()-start)-10.)),enabled=True)
                report('video-encoding-result.json',result['encoded_direct_video'])
            except BaseException as e:errors.append(dict(stage='controlled_encoder',error=bounded_exception(e)))
        if capture is not None:
            try:result['FD_capture']=capture.close()
            except BaseException as e:result['FD_capture']=getattr(e,'receipt',capture.snapshot());errors.append(dict(stage='FD_close',error=bounded_exception(e)))
        if health is not None:result['original_fast_health']=dict(health.metrics)
        if trace is not None:result['actual_Actor_call_metadata']=trace.snapshot()
        if driver is not None:
            result['prepared_L0_startup']=driver.startup.report()
            observed=driver.startup.arm_gate_audit
            result['diagnostic_question_answered']=bool(observed and observed.get('sample_complete') and
                observed.get('stage')=='ORIGINAL_GUARD_RETURNED' and
                observed.get('reason_class') in ('PASS','ARM_JOINT_LIMIT','ARM_GEOMETRY_PAIR'))
            result['diagnostic_answer_is_not_full_skill_success']=True
        zero_mark('final_state_sample_enter')
        result.update(close_errors=errors,wall_s=time.monotonic()-start,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            resource_failure=state.reason,output_budget_before_result=budget.snapshot(),usage_known=partial_usage['usage_known'],
            actual_task_success_claimed=bool(result.get('full_task_success')),system_5x_qualified=False,
            wall_sample_excludes_following_result_ledger_final_accounting_writes=True)
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
        if args.phase=='prepare':
            c,f=prepare(args.config,args.program_sha256,enabled=True)
            import torch
            from metadata_prepare import qualify
            metadata=qualify(c,f,enabled=True)
            from query_prepare import qualify_query_bindings
            query=qualify_query_bindings(c,f)
            from zero_retirement_fixture import qualify
            lifecycle=qualify()
            from selected_option_prepare import qualify_selected_option
            selected=qualify_selected_option(f)
            from direct_held_prepare import qualify_direct_held
            direct=qualify_direct_held(f)
            from first_callback_prepare import qualify_first_callback
            first_after=qualify_first_callback(f)
            from clearance_prepare import qualify_clearance
            clearance=qualify_clearance(c,f)
            from ainav.native.registered_skill_factory import RegisteredSkillSessionFactory
            from mujoco_zyh.native_behavior_executor import world_snapshot
            from native_connector import factory_class,FACTORY_SHA
            from terminal_action import BrakeAction
            typ=factory_class(RegisteredSkillSessionFactory,source_root=c['common_source'],factory_sha256=FACTORY_SHA,action=BrakeAction(**c['terminal_connector_DEV_action']),world_snapshot=world_snapshot,enabled=True)
            assert issubclass(typ,RegisteredSkillSessionFactory) and not torch.cuda.is_initialized()
            dev=dict(CPU_constructor_source_only=True,action=c['terminal_connector_DEV_action'],not_training_or_native=True)
            print(json.dumps(dict(terminal_connector_DEV_qualification=dev,clearance_einsum_qualification=clearance,first_original_after_step_qualification=first_after,direct_transport_qualification=direct,selected_option_qualification=selected,zero_lifecycle_qualification=lifecycle,query_binding_qualification=query,metadata_qualification=metadata,stage='PREPARED_L0_TERMINAL_DEV_ACTION_CPU_PREPARE_PASS',program_sha256=args.program_sha256,CUDA_initialized=torch.cuda.is_initialized(),Runtime_lease_Actor_GPU_API_calls=0,all_run_helper_file_gate_cpu_checked=True,helper_count=len(HELPER_NAMES)),sort_keys=True))
        else:sys.exit(0 if run(args.config,args.program_sha256,args.phase,enabled=True)['passed']else 1)
