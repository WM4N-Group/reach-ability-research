"""One claimed, bounded MuJoCo collection episode using native zyh skills/switches.

No replan success is invented: native failure stops collection. New training and
WM inference/control are zero. Source calibration is a separate budgeted world.
"""
import argparse
import fcntl
import hashlib
import importlib.metadata
import json
import math
import os
import subprocess
import sys
from pathlib import Path
import time
import traceback
import numpy as np
import torch

from .source_bundle import verify_bundle, COMMIT
from .runtime_adapter import construct_runtime
from .streams import ChunkedEpisodeWriter, write_json
from .observer import OnboardObserver
from .scene import IDENTITY

SCENARIOS=('nav-nav','nav-climb','nav-push','nav-push-climb')


def validate_protocol(p):
    if p.get("schema")=="piper-causal-task-model-full1-transfer-v1":
        from .causal_model_protocol import validate
        return validate(p)
    if p.get('schema')=='piper-integrated-nav-parameter-training-v1':
        from .nav_parameter_training import validate
        return validate(p)
    if p.get('schema')=='piper-integrated-batch-case-v1':
        from .integrated_batch import validate_case
        return validate_case(p)
    if p.get('schema')=='piper-continuous-integrated-course-v1':
        from .integrated_course import validate_protocol as validate_integrated
        return validate_integrated(p)
    if p.get('schema')=='piper-mujoco-five-easy-scenes-case-v1':
        from .five_scene_suite import validate_protocol as validate_suite
        return validate_suite(p)
    if p.get('schema')=='piper-mujoco-composite-shadow-case-v1':
        from .composite_shadow_study import validate_case
        return validate_case(p)
    if p.get('schema')=='piper-mujoco-compact-supported-recovery-v25':
        from .supported_recovery_protocol import validate_protocol as validate_supported
        return validate_supported(p)
    if p.get('schema')=='piper-mujoco-prequeue-protected-recovery-pilot-v1':
        from .protected_recovery_pilot import validate_protocol as validate_protection
        return validate_protection(p)
    if p.get('schema')=='piper-mujoco-recovery-exit-capsule-protocol-v3':
        from .recovery_exit_diagnostic import validate_protocol as validate_diagnostic
        return validate_diagnostic(p)
    if p.get('schema')=='piper-mujoco-terminated-option-forecast-case-v2':
        from .option_probe import validate_case as validate_option
        return validate_option(p)
    if p.get('schema') in ('piper-mujoco-A-recovery-selected-B-protocol-v1',
                           'piper-mujoco-A-recovery-selected-B-recorded-protocol-v2'):
        from .reselect_B import validate_protocol as validate_reselect
        return validate_reselect(p)
    if p.get('schema')=='piper-mujoco-compact-resume-nav-protocol-v1':
        from .resume_nav import validate_protocol as validate_resume
        return validate_resume(p)
    if p.get('schema')=='piper-mujoco-soft-stall-stow-protocol-v1':
        from .stall_stow import validate_protocol as validate_stall
        return validate_stall(p)
    if p.get('schema')=='piper-narrow-push-displacement-case-v1':
        from .push_forecast_protocol import validate_case
        return validate_case(p)
    if p.get('schema')!='piper-zyh-mujoco-collection-protocol-v1' or p.get('source_commit')!=COMMIT:
        raise ValueError('Exact independent MuJoCo protocol/source pin required')
    if p['scenario'] not in SCENARIOS or p['automatic_retry'] is not False or p['reset_after_initial_allowed']!=0:
        raise ValueError('Supported native scenario, no automatic retry and no task reset required')
    if p['training_runs']!=0 or p['WM_forwards']!=0 or p['WM_control'] is not False or p['episodes']!=1:
        raise ValueError('Exactly one frozen-skill engineering episode, no WM training/forward/control')
    for name,maximum in [('max_sim_seconds',180),('max_wall_seconds',3600),('max_payload_bytes',512*1024*1024)]:
        value=p[name]
        if type(value) not in (int,float) or not math.isfinite(value) or not 0<value<=maximum:raise ValueError('Invalid budget: '+name)
    if p['grace_seconds']!=10 or p['delay_ms'] not in (0,5,10,15,20):raise ValueError('Native delay/registered grace required')
    if type(p['seed']) is not int or p['actor_device']!='cpu':raise ValueError('Explicit seed and frozen CPU skill inference required')
    from .scene import calibration
    calibration(p['width'],p['height'])
    for n in ('visual_stride_control_ticks','visual_chunk_frames','command_chunk_steps'):
        if type(p[n]) is not int or not 1<=p[n]<=1000:raise ValueError('Invalid stream configuration')
    if p['scene_recipe'] not in ('research_threebox','zyh_native_single_box'):raise ValueError('Explicit scene recipe required')
    if p['scene_recipe']=='research_threebox' and 'climb' in p['scenario']:
        raise ValueError('Frozen40cm research platform cannot be relabeled as native20cm CLIMB acceptance')
    target='light' if p['scene_recipe']=='research_threebox' else 'upstream_demo'
    if p['selected_object_id']!=target:raise ValueError('Selected B executor is not implemented: never relabel A commands as B')
    needs_aux=p['scenario'] in ('nav-push','nav-push-climb')
    if p['auxiliary_calibration_worlds_allowed']!=int(needs_aux) or p['auxiliary_calibration_max_sim_seconds']!=(10.5 if needs_aux else 0):
        raise ValueError('Exact native auxiliary calibration budget required')
    if p['role']!='development' or p['training_allowed'] is not False:raise ValueError('Initial migration is engineering development, not training/evaluation')
    if not 0<=p['box_height_m']<=.2 or p['push_distance_m']!=.6 or p['post_success_hold_s']!=5.:
        raise ValueError('Frozen native task domain required')
    if not all(isinstance(p[n],str) and p[n] for n in ('source_id','episode_id','source_group')):
        raise ValueError('Explicit new source/group identities required')
    if type(p.get('full_state_review',False)) is not bool:raise ValueError('Explicit full-state review flag required')
    if p.get('full_state_review',False):
        if p['scene_recipe']!='zyh_native_single_box' or p['scenario']!='nav-push-climb':
            raise ValueError('Initial full-scene review is the native1kg route, never failed-A/B recovery')
        if (type(p.get('max_review_state_bytes')) is not int or not 0<p['max_review_state_bytes']<=32*1024*1024
            or p.get('max_total_episode_bytes')!=192*1024*1024):
            raise ValueError('Explicit bounded private review-state/total quota required')
        if type(p.get('max_compiled_model_cache_bytes')) is not int or not 0<p['max_compiled_model_cache_bytes']<=512*1024*1024:
            raise ValueError('Shared immutable static-model quota must be separately registered')
    if p.get('nav_efficiency_mode') is not None:
        from .nav_efficiency import MODE
        if (p['nav_efficiency_mode']!=MODE or p['scenario']!='nav-push-climb' or
            p['scene_recipe']!='zyh_native_single_box' or not p.get('full_state_review') or
            p.get('source_control_algorithms_changed') is not True or p.get('NAV_arm_joint5_kd')!=2.5):
            raise ValueError('Explicit bounded native-actor NAV adaptation protocol required')
    return p


def verify_freeze(root,bundle):
    freeze=json.loads((root/'freeze.json').read_text())
    for name,expected in freeze['inputs'].items():
        path=root/name
        if not path.resolve().is_relative_to(root) or hashlib.sha256(path.read_bytes()).hexdigest()!=expected:
            raise ValueError('Own collector/protocol/tests changed since freeze: '+name)
    source=verify_bundle(bundle)
    if source['sha256sums_sha256']!=freeze['upstream_manifest_sha256']:raise ValueError('Upstream freeze mismatch')
    return freeze,source


def guard_other_candidates(runtime,config):
    if config['scene_recipe']!='research_threebox':return
    import mujoco
    p=runtime.sim
    active=getattr(runtime,'wm_active_candidate','light')
    forbidden={p.model.body(IDENTITY[c]['body']).id for c in IDENTITY if c!=active}
    robot=set()
    for b in range(1,p.model.nbody):
        current=b
        while current:
            if current==p.base_id:robot.add(b);break
            current=int(p.model.body_parentid[current])
    for index,contact in enumerate(p.data.contact):
        a,b=map(int,p.model.geom_bodyid[[contact.geom1,contact.geom2]])
        if (a in robot and b in forbidden) or (b in robot and a in forbidden):
            force=np.zeros(6);mujoco.mj_contactForce(p.model,p.data,index,force)
            if np.linalg.norm(force[:3])>1.:raise RuntimeError('Unselected B/C physical contact safety veto')


CANONICAL_RESOURCE_DIR=Path('/mnt/yuanyue/data/go2-piper-world-model')


def resolve_resource_dir(root,protocol):
    """Fail closed: nested episodes must NEVER silently get private GPU locks."""
    root=Path(root).resolve();canonical=CANONICAL_RESOURCE_DIR.resolve()
    if not root.is_relative_to(canonical):raise ValueError('Formal collection root outside registered data directory')
    explicit=protocol.get('resource_lock_dir')
    if root.parent!=canonical and explicit is None:raise ValueError('Nested episode requires explicit canonical resource_lock_dir')
    path=Path(explicit) if explicit is not None else canonical
    if not path.is_absolute() or path.resolve()!=canonical:raise ValueError('Only shared canonical GPU resource locks are admitted')
    return canonical



def held_lock_evidence(handles,paths):
    """Owned flock + inode equality + fresh-process contention for EVERY file.

    Some mounted paths expose no fdinfo lock line even when flock excludes an
    independent opener. Missing telemetry is never converted into a held-lock
    assertion: actual fresh-open nonblocking contention is mandatory instead.
    """
    rows=[]
    child_code="""import errno,fcntl,json,os,sys
with open(sys.argv[1],'a+') as f:
 try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
 except BlockingIOError as e:
  print(json.dumps(dict(PID=os.getpid(),blocked=True,errno=e.errno)));sys.exit(0)
 print(json.dumps(dict(PID=os.getpid(),blocked=False)));sys.exit(3)
"""
    for handle,path in zip(handles,paths):
        path=Path(path).resolve();fd=os.fstat(handle.fileno());current=path.stat()
        kernel=[line for line in Path('/proc/self/fdinfo/'+str(handle.fileno())).read_text().splitlines() if line.startswith('lock:')]
        if (fd.st_dev,fd.st_ino)!=(current.st_dev,current.st_ino):raise ValueError('Lock fd/path inode mismatch: '+str(path))
        if kernel and not any('FLOCK' in line and 'WRITE' in line and str(os.getpid()) in line.split() for line in kernel):
            raise ValueError('Available kernel lock record contradicts ownership: '+str(path))
        probe=subprocess.run([sys.executable,'-c',child_code,str(path)],capture_output=True,text=True,timeout=5)
        if probe.returncode!=0:raise ValueError('Independent fresh-open contender was NOT excluded: '+str(path))
        result=json.loads(probe.stdout)
        if not result['blocked'] or result['PID']==os.getpid() or result['errno'] not in (11,13):
            raise ValueError('Invalid independent contention evidence')
        rows.append(dict(path=str(path),device=fd.st_dev,inode=fd.st_ino,PID=os.getpid(),kernel_FLOCK_records=kernel,
            kernel_fdinfo_lock_line_available=bool(kernel),independent_contender_blocked=True,
            independent_contender=result,independent_contender_returncode=probe.returncode))
    if len(rows)!=len(paths):raise ValueError('Incomplete actual lock evidence')
    return rows


def run(root,bundle):
    began=time.monotonic();root=Path(root).resolve();bundle=Path(bundle).resolve()
    protocol=validate_protocol(json.loads((root/'protocol.json').read_text()))
    freeze,source=verify_freeze(root,bundle)
    versions={n:importlib.metadata.version(n) for n in ('mujoco','numpy','scipy','osqp','torch')}
    expected=freeze['environment_versions']
    if versions!=expected:raise ValueError('Runtime environment changed after CPU preflight')
    if versions['mujoco']!='3.3.2' or versions['osqp']!='1.1.3':raise ValueError('Published MuJoCo/OSQP API versions required in isolated runtime')
    handles=[]
    try:
        resource=resolve_resource_dir(root,protocol)
        lock_paths=[root/'dispatch.lock',resource/'native-observer-physics-gpu1.lock',resource/'native-observer-sdk-gpu1.lock']
        for path in lock_paths:
            f=path.open('a+');handles.append(f);fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
        actual_locks=held_lock_evidence(handles,lock_paths)
        claim=root/'attempt.claim'
        with claim.open('x') as f:json.dump(dict(pid=os.getpid(),source_commit=COMMIT,automatic_retry=False),f)
        write_json(root/'preflight.json',dict(pass_=True,source=source,environment=versions,protocol_frozen=True,locks=3,claim_consumed=True,actual_resource_lock_evidence=actual_locks))
        return execute(root,bundle,protocol,began,versions)
    finally:
        for f in reversed(handles):f.close()


def execute(root,bundle,p,began,versions):
    runtime=machine=observer=writer=review=None;review_closure=None;outcome='constructor_error';error=None;physical_steps=0
    task_success=False;complete_time=None;receipt=None;closure=None;capsule_closure=None
    torch.set_num_threads(2);torch.backends.cuda.matmul.allow_tf32=False
    try:
        runtime,machine,receipt=construct_runtime(bundle,p)
        if p.get('recovery_exit_diagnostic_case') or p.get('push_protection_mode') or p.get('supported_push_mode') or p.get('schema')=='piper-mujoco-A-recovery-selected-B-recorded-protocol-v2' or p.get('integrated_course_mode'):
            from .failure_capsules import install
            install(runtime,root,p['private_failure_capsules'])
        write_json(root/'construction.json',dict(**receipt,auxiliary_calibration=getattr(runtime,'wm_auxiliary_calibration',dict(worlds=0,sim_seconds=0.))))
        observer=OnboardObserver(runtime,p)
        writer=ChunkedEpisodeWriter(root/'episode',dict(p,joint_names=runtime.push['model'].JOINTS,
            actor_sha256=json.loads((Path(bundle)/'MANIFEST.json').read_text())['actor_sha256'],
            physics_dt_s=.005,control_dt_s=.02,physical_state_reset_at_switch=False,
            native_per_skill_software_history_reinitialization=True,provenance_not_model_input=True))
        if p.get('full_state_review',False):
            from .review_capture import WorldStateRecorder
            review=WorldStateRecorder(root/'review-state',runtime,p,model_cache_dir=root.parent/'compiled-review-models')
        r,s=runtime,runtime.sim
        last_issued_position=np.zeros(18)
        if p.get('stall_stow_mode'):
            from .stall_stow import StallStowRouter
            if p.get('integrated_course_mode'):
                from .integrated_course import IntegratedRouter
                machine=IntegratedRouter(runtime,machine,root,p,bundle)
                if p.get("causal_model_policy"):
                    from .causal_task_client import attach
                    attach(machine,observer,p,root)
                if p.get('nav_parameter_training_case'):
                    from .nav_parameter_training import install as install_parameter_training
                    install_parameter_training(machine,p)
            elif p.get('supported_push_mode'):
                from .supported_push import SupportedPushRouter
                machine=SupportedPushRouter(runtime,machine,root)
            elif p.get('push_protection_mode'):
                from .push_protection import PrequeueProtectionRouter
                machine=PrequeueProtectionRouter(runtime,machine,root)
            elif p.get('option_forecast_case') or p.get('recovery_exit_diagnostic_case'):
                from .option_probe import OptionProbeRouter
                machine=OptionProbeRouter(runtime,machine,root)
            elif p.get('reselect_B_mode'):
                from .reselect_B import ReselectBRouter
                machine=ReselectBRouter(runtime,machine,root,p,bundle)
            elif p.get('resume_nav_mode'):
                from .resume_nav import ResumeNavRouter
                machine=ResumeNavRouter(runtime,machine,root)
            else:machine=StallStowRouter(runtime,machine,root)
        while True:
            if time.monotonic()-began>=p['max_wall_seconds']:
                outcome='registered_wall_budget_censor';break
            if float(s.data.time)>=p['max_sim_seconds']-1e-9:
                outcome='registered_sim_budget_censor';break
            machine.update()  # native Machine; opt-in engineering NAV controller explicitly recorded
            if p.get('probe_physics') and not p.get('stall_stow_mode') and getattr(machine,'kind',None)=='push' and machine.phase!='prepare':
                if machine.finish is not None:
                    outcome='probe_stop_at_native_push_success_boundary';break
                if machine.age>=p['push_probe_max_active_s']:
                    outcome='probe_registered_PUSH_duration_censor';break
            if machine.complete and complete_time is None:complete_time=float(s.data.time)
            if complete_time is not None and float(s.data.time)-complete_time>=p['post_success_hold_s']-1e-9:
                if p.get('integrated_course_mode'):
                    from .integrated_course import endpoint as full_endpoint
                    if not full_endpoint(runtime,p)['passed']:raise RuntimeError('integrated_far_bank_endpoint_not_verified')
                if p.get('schema')=='piper-mujoco-five-easy-scenes-case-v1':
                    from .five_scene_suite import endpoint
                    if not endpoint(runtime,p)['passed']:raise RuntimeError('engineering_suite_measured_endpoint_not_passed')
                protected_abort=bool(p.get('supported_push_mode') and machine.retirement is not None)
                task_success=not protected_abort
                outcome=('full_integrated_A_B_high_bridge_robot_cross_verified' if p.get('integrated_course_mode') else 'supported_PUSH_protective_abort_stow_only_NOT_soft_failure_recovery' if protected_abort else 'supported_PUSH_failed_real_retreat_stow_verified' if p.get('supported_push_mode') else 'protected_PUSH_real_retreat_stow_verified_engineering_only' if p.get('push_protection_mode') else 'A_failed_B_attempt_safe_terminal_result' if p.get('reselect_B_mode') else 'failed_PUSH_compact_resume_NAV_arrival_verified' if p.get('resume_nav_mode') else 'failed_PUSH_protected_stow_verified_NO_NAV' if p.get('stall_stow_mode') else 'frozen_skill_sequence_complete_engineering_NAV' if p.get('nav_efficiency_mode') else 'native_sequence_complete_and_hold');break
            tick=physical_steps//4
            if getattr(machine,"causal_policy",None) is not None:machine.causal_policy.control(float(s.data.time),getattr(machine,"kind","startup"),machine.phase)
            writer.boundary(dict(control_tick=tick,time_s=float(s.data.time),task_index=machine.index,
                skill=getattr(machine,'kind','startup'),phase=machine.phase,
                **(dict(public_body_proprio=observer.public_body_proprio().tolist()) if p.get('public_control_proprio_hz')==50 else {}),
                q=s.data.qpos[s.qids].tolist(),dq=s.data.qvel[s.dids].tolist(),native_sequence_complete=machine.native.complete if p.get('stall_stow_mode') else machine.complete,
                protocol_sequence_complete=machine.complete,
                recovery_diagnostics=machine.diagnostics() if p.get('stall_stow_mode') else None,
                nav_diagnostics=machine.nav.diagnostics() if p.get('nav_efficiency_mode') and
                    getattr(machine,'kind',None)=='nav' and hasattr(getattr(machine,'nav',None),'diagnostics') else None))
            if tick%p['visual_stride_control_ticks']==0:
                packet,catalog=observer.capture(tick,last_issued_position)
                if getattr(machine,"causal_policy",None) is not None:machine.causal_policy.capture(packet)
                writer.append_visual(packet,control_tick=tick,private_catalog=catalog)
                if review is not None:review.capture(tick)
            for substep in range(4):
                command=machine.next_command()
                issued=command.array().copy();q=s.data.qpos[s.qids].copy();dq=s.data.qvel[s.dids].copy()
                before=float(s.data.time)
                try:r.step(command)
                finally:
                    if float(s.data.time)>before:
                        physical_steps+=1
                        last_issued_position=issued[0].copy()
                        delayed=np.stack([s.queue[-1-int(lag)][:,j] for j,lag in enumerate(s.delays)],axis=1)
                        writer.append_command(issued=issued,delayed=delayed,torque=s.torque,raw_torque=s.raw_torque,
                            q_before=q,dq_before=dq,physical_tick=physical_steps,time_s=float(s.data.time))
                machine.after_step()  # original dynamic collision/exit guards, never bypassed
                guard_other_candidates(runtime,p)
                if p.get('schema')=='piper-mujoco-five-easy-scenes-case-v1':
                    from .five_scene_suite import after_step as suite_after_step
                    suite_after_step(runtime)
            if tick%250==0:print(f'physical={s.data.time:.2f}s skill={getattr(machine,"kind","startup")} phase={machine.phase} frames={observer.frames}',flush=True)
    except Exception as exc:
        partial=getattr(exc,'wm_partial_runtime',None)
        if runtime is None and partial is not None and hasattr(partial,'sim'):runtime=partial
        option_boundary=False
        if p.get('option_forecast_case') or p.get('recovery_exit_diagnostic_case'):
            from .option_probe import NativeGoalBoundary
            option_boundary=isinstance(exc,NativeGoalBoundary)
        if option_boundary:
            error=None;outcome='observed_native_PUSH_goal_option_boundary';task_success=True
        else:
            error=repr(exc);outcome='native_or_collection_failure';traceback.print_exc()
            if runtime is not None and getattr(runtime,'wm_private_capsules',None) is not None:
                from .failure_capsules import emit
                selected=getattr(machine,'view',None)
                emit(runtime,'terminal_exception',view=selected,extra=dict(error=repr(exc),reference_inputs=getattr(exc,'wm_reference_inputs',None)),preserve_primary_failure=True)
    finally:
        terminal_time=float(runtime.sim.data.time) if runtime is not None else 0.
        if p.get('stall_stow_mode') and machine is not None and hasattr(machine,'close'):machine.close()
        if observer is not None:
            try:observer.close()
            except Exception as exc:error=(error or '')+' observer_close: '+repr(exc);task_success=False
        if review is not None:
            try:review_closure=review.close()
            except Exception as exc:error=(error or '')+' review_close: '+repr(exc);task_success=False
        recorder=getattr(runtime,'wm_private_capsules',None) if runtime is not None else None
        if recorder is not None:
            try:
                capsule_closure=recorder.close()
                if not capsule_closure['all_required_captures_complete']:
                    error=(error or '')+' private_failure_capsule_incomplete';task_success=False
            except Exception as exc:
                error=(error or '')+' private_failure_capsule_close: '+repr(exc);task_success=False
        if writer is not None:closure=writer.close(outcome=outcome,terminal_time_s=terminal_time,censored=not task_success)
        report=dict(schema='piper-zyh-mujoco-collection-report-v1',source_commit=COMMIT,backend='mujoco',
            caller_outcome=outcome,task_success=task_success,error=error,sim_seconds=terminal_time,
            wall_seconds=time.monotonic()-began,physical_steps=physical_steps,reset_after_initial=0,
            native_events=machine.events if machine is not None else [],native_results=machine.results if machine is not None else [],
            source_switch_metrics=machine.switch_metrics if machine is not None else [],
            auxiliary_calibration=getattr(runtime,'wm_auxiliary_calibration',dict(worlds=0,sim_seconds=0.)),
            nav_efficiency_adaptation=getattr(runtime,'wm_nav_efficiency',None),
            stall_stow_recovery=machine.report() if p.get('stall_stow_mode') and machine is not None and hasattr(machine,'report') else None,
            frames=observer.frames if observer is not None else 0,data_closure=closure,private_review_state=review_closure,
            source_postflight=verify_bundle(bundle),environment=versions,private_failure_capsules=capsule_closure,
            skill_actor_inference='original frozen actors executed by native Machine',WM_forwards=(machine.causal_policy.forwards if getattr(machine,"causal_policy",None) is not None else 0),WM_control=int(getattr(machine,"causal_policy",None) is not None),training_runs=0,
            A_failure_recovery_B_reselection_or_full_platform_validated=False,
            role=p['role'],probe_physics_private=p.get('probe_physics'),
            strict_safety_certified=False,model_training_authorized=p.get('forecast_study_training_authorized',False))
        if p.get('integrated_course_mode') and machine is not None:
            report['integrated_course']=machine.report()
            if getattr(machine,'causal_policy',None) is not None:report['causal_model_policy']=machine.causal_policy.summary()
            report['A_failure_recovery_B_reselection_or_full_platform_validated']=bool(task_success)
        if runtime is not None:
            s=runtime.sim
            if p.get('schema')=='piper-mujoco-five-easy-scenes-case-v1':
                from .five_scene_suite import endpoint
                report['engineering_scene_endpoint']=endpoint(runtime,p)
                report['actual_failure_contact']=getattr(runtime,'failure_contact',None)
            report.update(delay_steps=s.delays.tolist(),effort_limits_nm=runtime.push['model'].EFFORT.tolist(),
                actual_model_mass_kg=float(s.model.body_subtreemass[s.base_id]),
                joint_position_limits_rad=s.model.jnt_range[s.jids].tolist(),
                peak_joint_speed_rad_s=s.peak_speed.tolist(),torque_saturation_physics_steps=s.saturation.tolist(),
                speed_exceeded_physics_steps=s.speed_exceeded.tolist(),angle_violation_rad=runtime.angle_violation.tolist())
        if p.get('full_state_review',False) or p.get('recovery_exit_diagnostic_case') or p.get('push_protection_mode') or p.get('supported_push_mode'):
            actual=sum(path.stat().st_size for folder in (root/'episode',root/'review-state',root/'private-failure-capsules') for path in folder.rglob('*') if path.is_file())
            if p.get('stall_stow_mode'):
                private=sum((root/n).stat().st_size for n in ('stall-monitor-50hz.jsonl','stow-actual-200hz.jsonl','resume-nav-policy-50hz.jsonl','resume-nav-200hz.jsonl','selected-B-50hz.jsonl','selected-B-200hz.jsonl','push-protection-prequeue-200hz.jsonl','supported-push-200hz.jsonl','integrated-stage-events.jsonl') if (root/n).exists())
                actual+=private;report['recovery_private_log_bytes']=private
            report['total_episode_and_review_bytes']=actual
            if actual>p['max_total_episode_bytes']:
                report['error']=(report['error'] or '')+' registered total episode quota exceeded';error=report['error']
        write_json(root/'report.json',report)
    return 0 if error is None and closure is not None and closure['storage_complete'] else 2


def main():
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--root',type=Path,required=True);a.add_argument('--bundle',type=Path,required=True)
    args=a.parse_args();raise SystemExit(run(args.root,args.bundle))


if __name__=='__main__':main()
