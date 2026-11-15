#!/usr/bin/env python3
"""One-shot real original-scene DeepSeek/tree full-task controller.

Original physical endpoint and required loaded-surface history own success. Mandatory native A failure/stow
is explicitly excluded from model contribution. New root, frozen source/assets,
canonical GPU lease, no reset, no automatic retry, original native guards.
"""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import resource
import sys
import time


def save(path,value):
    def array_only(x):
        if hasattr(x,'tolist'):return x.tolist()
        raise TypeError('Unsupported evidence type: '+type(x).__name__)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False,default=array_only)+'\n')


def main(*,engineering_planner_factory=None,engineering_requests_sha256=None):
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('source','bundle','root','gpu-lock'):parser.add_argument('--'+name,required=True)
    parser.add_argument('--host-adapter',choices=('original','verified-placement','execution-judged'),default='original')
    parser.add_argument('--max-wall-seconds',type=float,default=2340.)
    parser.add_argument('--max-sim-seconds',type=float,default=420.)
    args=parser.parse_args()
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    source,bundle,root=[Path(p).resolve() for p in (args.source,args.bundle,args.root)]
    if root.exists() or not 0<args.max_wall_seconds<=2400 or not 0<args.max_sim_seconds<=420:
        raise ValueError('Fresh root and budgets within original native protocol required')
    root.mkdir(parents=True,exist_ok=False)
    os.environ.update(MUJOCO_GL='egl',MUJOCO_EGL_DEVICE_ID='1',PYTHONDONTWRITEBYTECODE='1')
    os.environ.pop('CUDA_VISIBLE_DEVICES',None)
    sys.path.insert(0,str(source))
    from ainav.contracts import file_sha
    from ainav.evidence import Journal
    from ainav.native.resources import ResourceLease
    journal=Journal(root/'events.jsonl')
    started=time.monotonic();runtime=observer=writer=review=host=backend=None
    report=dict(schema='ainav-deepseek-full-course-v1',role='seen-development-only',
        started_at=datetime.now().astimezone().isoformat(),source_manifest_sha256=file_sha(source/'ainav-source.json'),
        original_scene_case='full-4',world_model_used=False,actor_retrained=False,
        full_course_passed=False,task_success=False,error=None,all_behavior_skills_connected=False,progress_skills_registered=['NAV','PUSH','CLIMB','HOLD'],NAV_control_chain_verified=False,
        automatic_retry=False,max_launches=1,reset_allowed=False,credentials_persisted=False,
        max_wall_seconds=args.max_wall_seconds,max_sim_seconds=args.max_sim_seconds,
        engineering_only=engineering_planner_factory is not None,engineering_entry_probe_passed=False,
        engineering_requests_sha256=engineering_requests_sha256,api_calls=0,api_total_tokens=0)
    try:
        with ResourceLease([args.gpu_lock]) as lease:
            save(root/'resource-admission.json',lease.evidence)
            (root/'attempt.claim').write_text(json.dumps(dict(pid=os.getpid(),max_launches=1,automatic_retry=False))+'\n')
            import importlib.metadata
            versions={k:importlib.metadata.version(k) for k in ('torch','numpy','scipy','osqp','mujoco')}
            if versions!={'torch':'2.7.0+cu128','numpy':'1.26.4','scipy':'1.13.1','osqp':'1.1.3','mujoco':'3.3.2'}:
                raise ValueError('Actual validated A800 native dependency versions required')
            import numpy as np
            import torch
            torch.set_num_threads(2)
            from mujoco_zyh import integrated_course as integrated,stall_stow as stall,native_behavior_executor as api
            from mujoco_zyh.runtime_adapter import construct_runtime
            from mujoco_zyh.observer import OnboardObserver
            from mujoco_zyh.streams import ChunkedEpisodeWriter
            from mujoco_zyh.review_capture import WorldStateRecorder
            from mujoco_zyh.failure_capsules import install as install_capsules
            from mujoco_zyh.source_bundle import verify_bundle
            from ainav.backend import create_vision_backend
            from ainav.vlm import RoleRunner
            from ainav.planner import AinavPlanner
            from ainav.native.full_course import FullCourse
            report['versions']=versions
            save(root/'asset-verification-before.json',verify_bundle(bundle))
            native=integrated.protocol(next(c for c in integrated.plan()['cases'] if c['case_id']=='full-4'))
            integrated.validate_protocol(native);save(root/'original-native-protocol.json',native)
            runtime,machine,construction=construct_runtime(bundle,dict(native,bundle=str(bundle)))
            report['auxiliary_calibration']=getattr(runtime,'wm_auxiliary_calibration',None)
            save(root/'construction.json',construction)
            report['delay_steps']=runtime.sim.delays.tolist()
            report['effort_limits_nm']=runtime.push['model'].EFFORT.tolist()
            install_capsules(runtime,root,native['private_failure_capsules'])
            observer=OnboardObserver(runtime,native)
            manifest=json.loads((bundle/'MANIFEST.json').read_text())
            writer=ChunkedEpisodeWriter(root/'episode',dict(native,joint_names=runtime.push['model'].JOINTS,
                actor_sha256=manifest['actor_sha256'],physics_dt_s=.005,control_dt_s=.02,
                VLM_control=engineering_planner_factory is None,ainav_pilot_only=False,original_scene_source_id=native['source_id']))
            review=WorldStateRecorder(root/'review-state',runtime,native,model_cache_dir=root.parent/'compiled-review-models')
            if engineering_planner_factory is None:
                backend=create_vision_backend(max_calls=100,max_tokens=8192,max_total_tokens=900000)
                report['VLM_backend_identity']=backend.identity
                roles=RoleRunner(backend,journal,timeout_s=90.)
                planner=AinavPlanner(roles,journal,plan_count=5,terminal_bonus=10.)
            else:
                if args.host_adapter!='execution-judged':raise ValueError('Engineering entry probe requires the independent execution judge')
                planner=engineering_planner_factory(journal)
                report['planner_source']='explicit_engineering_requests_NOT_VLM'
                report['VLM_backend_identity']=None
            Host=FullCourse
            if args.host_adapter=='verified-placement':
                from ainav.native.full_verified_placement import VerifiedPlacementFullCourse
                Host=VerifiedPlacementFullCourse
            if args.host_adapter=='execution-judged':
                from ainav.native.execution_judged_course import ExecutionJudgedFullCourse
                Host=ExecutionJudgedFullCourse
            report['host_adapter']=args.host_adapter
            host=Host(runtime=runtime,native_a=machine,observer=observer,writer=writer,root=root,
                config=dict(native,bundle=str(bundle)),api=api,integrated=integrated,stall=stall,
                planner=planner,journal=journal)
            last_review=None
            endpoint=None
            while True:
                if time.monotonic()-started>=args.max_wall_seconds:raise TimeoutError('Bounded pilot wall budget reached')
                if float(runtime.sim.data.time)>=args.max_sim_seconds:raise TimeoutError('Bounded pilot sim budget reached')
                if host.tick%20==0 and last_review!=host.tick:
                    review.capture(host.tick//4);last_review=host.tick
                host.step_one()
                if host.loop is not None:
                    host.record_footprints()
                    if engineering_planner_factory is not None and planner.complete:
                        endpoint=dict(passed=False,engineering_requested_intents_completed=True)
                        break
                    if (host.executor.option is not None and host.executor.option.skill=='HOLD'
                            and host.executor.last_outcome=='succeeded'):
                        endpoint=host.original_goal()
                        if endpoint['passed']:break
            host.monitor.check_a()
            report.update(outcome='engineering_entry_prerequisites_observed' if engineering_planner_factory is not None else 'original_full_physical_goal_observed',
                NAV_control_chain_verified=True,full_course_passed=engineering_planner_factory is None,task_success=engineering_planner_factory is None,
                engineering_entry_probe_passed=engineering_planner_factory is not None,
                original_physical_endpoint=endpoint,private_surface_history=host.surface_visits.report(),
                actual_completed_skills=host.completed,actual_dispatches=host.dispatched,
                api_calls=backend.calls if backend is not None else 0,api_total_tokens=backend.total_tokens if backend is not None else 0,
                original_prefix_counted_as_model_contribution=False,
                original_A_goal_and_retired_history_preserved=True,
                public_static_viewpoints_not_BC_role_map=True)
            save(root/'asset-verification-after.json',verify_bundle(bundle))
    except BaseException as error:
        detail=type(error).__name__+': '+str(error)
        for name in ('AINAV_VLM_API_KEY','DEEPSEEK_API_KEY'):
            key=os.environ.get(name,'')
            if key:detail=detail.replace(key,'[REDACTED]')
        report.update(outcome='failed_no_retry',error=detail,NAV_control_chain_verified=False,full_course_passed=False,task_success=False,engineering_entry_probe_passed=False)
        if runtime is None:runtime=getattr(error,'wm_partial_runtime',None)
        if host is not None:
            try:
                from ainav.native.failure_diagnostics import terminal_snapshot
                diagnostic=terminal_snapshot(host,error)
                journal(dict(diagnostic,time_s=float(runtime.sim.data.time),error=detail))
                from mujoco_zyh.failure_capsules import emit
                emit(runtime,'ainav_terminal_failure',extra=diagnostic,preserve_primary_failure=True)
            except Exception as diagnostic_error:
                report['terminal_diagnostic_error_type']=type(diagnostic_error).__name__
    finally:
        cleanup_errors=[]
        for name,action in (
            ('review',lambda:review.close() if review is not None else None),
            ('episode',lambda:writer.close(outcome=report.get('outcome','failed'),terminal_time_s=float(runtime.sim.data.time) if runtime else 0.,censored=not report['full_course_passed']) if writer is not None else None),
            ('capsules',lambda:runtime.wm_private_capsules.close() if runtime is not None and getattr(runtime,'wm_private_capsules',None) is not None else None),
            ('observer',lambda:observer.close() if observer is not None else None)):
            try:
                result=action()
                if result is not None:report[name+'_closure']=result
            except Exception as error:cleanup_errors.append(name+': '+str(error))
        if host is not None:
            report['actual_native_results']=[result for session in host.executor.sessions for result in getattr(session.machine,'results',[])]
            for handle in (host.prefix.log,host.prefix.recovery_log):
                try:handle.close()
                except Exception as error:cleanup_errors.append('prefix close: '+str(error))
            report.update(actual_dispatches=host.dispatched,actual_completed_skills=host.completed,
                          actual_physical_ticks=host.tick)
        if host is not None:
            try:host.private_samples.close()
            except Exception as error:cleanup_errors.append(str(error))
            report['private_surface_history']=host.surface_visits.report()
        if cleanup_errors:report.update(cleanup_errors=cleanup_errors,NAV_control_chain_verified=False,full_course_passed=False,task_success=False,engineering_entry_probe_passed=False)
        if backend is not None:report.update(api_calls=backend.calls,api_total_tokens=backend.total_tokens)
        report['main_world_sim_seconds']=float(runtime.sim.data.time) if runtime is not None else 0.
        report['wall_seconds']=time.monotonic()-started
        report['sim_seconds']=report['main_world_sim_seconds']
        report['caller_outcome']=report.get('outcome')
        journal.close();save(root/'report.json',report)
    print(json.dumps(report,ensure_ascii=False),flush=True)
    return 0 if report['full_course_passed'] or report['engineering_entry_probe_passed'] else 2


if __name__=='__main__':raise SystemExit(main())
