#!/usr/bin/env python3
"""One bounded native cold-start development probe. NO VLM, NAV or full-task claim.

Fresh world/root/source/asset hashes + canonical GPU lease + original motor FIFO.
--zero-step exercises construction/first command screens but issues NO command.
"""
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import resource
import sys
import time


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):
    def cast(v):
        if hasattr(v,'tolist'):return v.tolist()
        raise TypeError(type(v).__name__)
    Path(p).write_text(json.dumps(x,indent=2,ensure_ascii=False,default=cast,allow_nan=False)+'\n')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ('source','bundle','case-root','root','gpu-lock'):ap.add_argument('--'+name,required=True)
    ap.add_argument('--case-format',choices=('legacy-full4','transfer'),required=True)
    ap.add_argument('--native-executor',action='store_true',help='Engineering exact-query factory/executor validation, not VLM')
    ap.add_argument('--zero-step',action='store_true');ap.add_argument('--preflight-report')
    ap.add_argument('--nav-probe-segments',type=int,choices=(1,2),default=1,help='Explicit distinct engineering targets; no failure retry')
    ap.add_argument('--nav-probe-delta',nargs=2,type=float,help='Explicit engineering NAV delta, never a model action')
    ap.add_argument('--support-ref');ap.add_argument('--initial-xy',nargs=2,type=float)
    args=ap.parse_args()
    if args.native_executor and args.nav_probe_delta is None:ap.error('Native executor probe requires an explicit NAV delta')
    if args.nav_probe_segments>1 and args.nav_probe_delta is None:ap.error('Multiple engineering NAV segments require an explicit delta')
    source=Path(args.source).resolve();case=Path(args.case_root).resolve();root=Path(args.root).resolve()
    if root.exists():raise FileExistsError('Fresh standalone experiment root required')
    if not args.zero_step:
        if not args.preflight_report:raise ValueError('Actual matching zero-step preflight required')
        z=json.loads(Path(args.preflight_report).read_text())
        if z.get('outcome')!='zero_step_capture_command_screened' or z['source_manifest_sha256']!=sha(source/'ainav-source.json'):
            raise ValueError('Preflight missing or source differs')
        if z['case_root']!=str(case) or z['case_format']!=args.case_format or z['requested_support']!=args.support_ref or z['requested_initial_xy']!=args.initial_xy or z.get('requested_nav_probe_delta')!=args.nav_probe_delta or z.get('requested_nav_probe_segments',1)!=args.nav_probe_segments or z.get('native_executor_probe',False)!=args.native_executor:
            raise ValueError('Preflight must use exact registered initial configuration')
    resource.setrlimit(resource.RLIMIT_CORE,(0,0));os.environ.update(MUJOCO_GL='egl',MUJOCO_EGL_DEVICE_ID='1',PYTHONDONTWRITEBYTECODE='1')
    root.mkdir(parents=True,exist_ok=False);sys.path.insert(0,str(source))
    from ainav.evidence import Journal
    from ainav.native.resources import ResourceLease
    journal=Journal(root/'events.jsonl');started=time.monotonic();runtime=owner=writer=observer=review=nav=option_probe=None;tick=0
    report=dict(schema='ainav-supported-capture-probe-v1',started_at=datetime.now().astimezone().isoformat(),
        case_root=str(case),case_format=args.case_format,requested_support=args.support_ref,requested_initial_xy=args.initial_xy,requested_nav_probe_delta=args.nav_probe_delta,requested_nav_probe_segments=args.nav_probe_segments,NAV_stages=[],
        native_executor_probe=args.native_executor,source_manifest_sha256=sha(source/'ainav-source.json'),task_success=False,model_API_calls=0,model_decisions=0,
        native_capture_verified=False,native_NAV_verified=False,zero_step=args.zero_step,max_sim_seconds=75. if args.nav_probe_delta else 15.,max_wall_seconds=300.,max_launches=1,
        automatic_retry=False,physical_reset_after_initial=False,scope='engineering_cold_start_only_not_navigation_trial')
    try:
        with ResourceLease([args.gpu_lock]) as lease:
            save(root/'resource-admission.json',lease.evidence);save(root/'attempt.claim',dict(pid=os.getpid(),max_launches=1))
            import numpy as np
            import torch
            import mujoco
            torch.set_num_threads(2)
            from ainav.native.scene_registry import SceneRegistry
            from ainav.native.registered_runtime import construct_cold_runtime
            from ainav.native.supported_capture import SupportedCapture,ActualCaptureWitness
            from ainav.native.registered_observer import RegisteredObserver
            from mujoco_zyh import integrated_course
            from mujoco_zyh.stall_stow import STOW_ARM
            from mujoco_zyh.review_capture import WorldStateRecorder,load_display_model
            from mujoco_zyh.streams import ChunkedEpisodeWriter
            from mujoco_zyh.source_bundle import verify_bundle
            from mujoco_zyh.failure_capsules import install,emit
            verify_bundle(args.bundle)
            native=integrated_course.protocol(next(c for c in integrated_course.plan()['cases'] if c['case_id']=='full-4'))
            if args.case_format=='transfer':
                scene=json.loads((case/'scene.json').read_text());bindings=json.loads((case/'private-object-bindings.json').read_text())
                registry=SceneRegistry.from_transfer(scene,bindings);model_path=case/'scene.mjb';model_sha=json.loads((case/'report.json').read_text())['scene_model_sha256']
                initial=dict(scene['initial_robot'])
            else:
                protocol=json.loads((case/'original-native-protocol.json').read_text());integrated_course.validate_protocol(protocol)
                registry=SceneRegistry.from_legacy_full4(protocol,integrated_course.layout(protocol['integrated_case']))
                model=load_display_model(case/'review-state');model_path=root/'static-original-model.mjb';mujoco.mj_saveModel(model,str(model_path));model_sha=sha(model_path)
                initial=dict(xy_m=[-.08,0.],yaw_rad=0.,support='ground')
            if bool(args.support_ref)!=bool(args.initial_xy):raise ValueError('Probe support and XY override must be supplied together')
            if args.support_ref:initial.update(support=args.support_ref,xy_m=args.initial_xy)
            support=registry.surfaces[initial['support']];x,y=initial['xy_m'];x0,x1,y0,y1=support.bounds_xy_m
            if not x0+.5<x<x1-.5 or not y0+.4<y<y1-.4:raise ValueError('Initial robot must be safely interior to declared support')
            report.update(initial_configuration=initial,registered_initial_arm_reference=STOW_ARM.tolist(),static_model_sha256=model_sha,source_asset_verification=verify_bundle(args.bundle))
            runtime,construction=construct_cold_runtime(args.bundle,model_path,model_sha256=model_sha,initial_robot=initial,initial_surface_height_m=support.top_z_m,initial_arm_reference=STOW_ARM)
            save(root/'construction.json',construction);report['auxiliary_calibration']=runtime.wm_auxiliary_calibration
            report['delay_steps']=runtime.sim.delays.tolist();report['effort_limits_nm']=runtime.push['model'].EFFORT.tolist()
            registry.verify_compiled(runtime.sim.model);install(runtime,root,native['private_failure_capsules'])
            owner=SupportedCapture(runtime,registry,support_ref=initial['support'],journal=journal)
            if args.zero_step:
                before=runtime.sim.data.qpos.copy();command=owner.command()
                if runtime.sim.data.time or runtime.step_count or len(runtime.sim.queue) or not np.array_equal(before,runtime.sim.data.qpos):raise ValueError('Zero-step command changed world')
                report.update(outcome='zero_step_capture_command_screened',first_command_shape=list(command.array().shape),main_motor_steps=0,first_command_issued=False)
            else:
                metadata=dict(native,schema='ainav-cold-start-development-v1',source_id=root.name,episode_id=root.name+'-episode0',source_group='cold-start-engineering-only',
                    role='seen-development-only',scene_recipe='registered',suite_case={'family':'cold-start'},
                    review_scope='Cold-start compact support only | NO VLM/task progress',joint_names=runtime.push['model'].JOINTS,
                    actor_sha256=json.loads((Path(args.bundle)/'MANIFEST.json').read_text())['actor_sha256'])
                metadata.pop('integrated_case',None);save(root/'probe-protocol.json',metadata)
                writer=ChunkedEpisodeWriter(root/'episode',metadata)
                observer=RegisteredObserver(runtime,dict(width=192,height=128,scene_recipe='registered'),registry)
                review=WorldStateRecorder(root/'review-state',runtime,metadata,model_cache_dir=root.parent/'compiled-review-models')
                while True:
                    if time.monotonic()-started>300 or runtime.sim.data.time>=report['max_sim_seconds']:raise TimeoutError('Explicit capture probe budget reached')
                    if tick%20==0:
                        packet,private=observer.capture(tick//4,runtime.last.position)
                        writer.append_visual(packet,control_tick=tick//4,private_catalog=dict(private,model_input_allowed=False));review.capture(tick//4)
                        writer.boundary(dict(control_tick=tick//4,physical_tick=tick,skill='nav' if nav is not None else 'cold_capture',phase=nav.phase if nav is not None else owner.phase))
                    p=runtime.sim;q=p.data.qpos[p.qids].copy();dq=p.data.qvel[p.dids].copy();before=float(p.data.time)
                    if nav is not None and (tick-nav.started_tick)%4==0:
                        if option_probe is not None:option_probe.update()
                        else:nav.update()
                    command=(option_probe.command() if option_probe is not None else nav.command() if nav is not None else owner.command());issued=command.array().copy()
                    try:runtime.step(command)
                    finally:
                        if float(p.data.time)>before:
                            if abs(float(p.data.time)-before-.005)>1e-7:raise RuntimeError('Original 5ms clock violated')
                            tick+=1
                            delayed=np.stack([p.queue[-1-int(lag)][:,i] for i,lag in enumerate(p.delays)],axis=1)
                            writer.append_command(issued=issued,delayed=delayed,torque=p.torque,raw_torque=p.raw_torque,q_before=q,dq_before=dq,physical_tick=tick,time_s=float(p.data.time))
                    if nav is not None:
                        if option_probe is not None:option_probe.after_actual_issue(issued,tick,float(p.data.time))
                        else:nav.after_step()
                        if nav.complete:
                            report['NAV_stages'].append(nav.report())
                            if len(report['NAV_stages'])>=args.nav_probe_segments:
                                report.update(outcome='actual_cold_capture_and_registered_NAV_observed',native_NAV_verified=True);break
                            from ainav.native.registered_compact_nav import ActualArrivalSupportWitness,RegisteredCompactNav
                            if option_probe is not None:
                                nav=option_probe.start_segment();continue
                            arrival_witness=ActualArrivalSupportWitness(nav)
                            goal=(runtime.sim.data.qpos[:2]+np.asarray(args.nav_probe_delta)).tolist()
                            nav=RegisteredCompactNav(runtime,registry,capture_witness=arrival_witness,goal_xy=goal,journal=journal)
                    else:
                        owner.after_step()
                        if owner.complete:
                            witness=ActualCaptureWitness(owner);report.update(outcome='actual_supported_cold_capture_observed',native_capture_verified=True,witness=witness.report(),capture_at_handoff=owner.report())
                            if args.nav_probe_delta is None:break
                            from ainav.native.registered_compact_nav import RegisteredCompactNav
                            goal=(runtime.sim.data.qpos[:2]+np.asarray(args.nav_probe_delta)).tolist()
                            report['engineering_NAV_goal_xy']=goal
                            if args.native_executor:
                                from nav_executor_probe import NativeNavOptionProbe
                                option_probe=NativeNavOptionProbe(runtime,registry,capture_witness=witness,observer=observer,root=root,journal=journal,delta=args.nav_probe_delta)
                                nav=option_probe.start_segment()
                            else:nav=RegisteredCompactNav(runtime,registry,capture_witness=witness,goal_xy=goal,journal=journal)
                report['asset_verification_after']=verify_bundle(args.bundle)
    except Exception as error:
        report.update(outcome='failed_no_retry',error=type(error).__name__+': '+str(error))
        if runtime is not None:
            try:
                from mujoco_zyh.failure_capsules import emit
                emit(runtime,'cold_capture_failure',extra=dict(error=str(error),phase=getattr(nav if nav is not None else owner,'phase',None),reference_inputs=getattr(error,'wm_reference_inputs',None)),preserve_primary_failure=True)
            except Exception as diagnostic:report['failure_capsule_error']=type(diagnostic).__name__
    finally:
        cleanup=[]
        for name,action in (
            ('review',lambda:review.close() if review else None),
            ('episode',lambda:writer.close(outcome=report.get('outcome','failed'),terminal_time_s=float(runtime.sim.data.time),censored=not (report['native_capture_verified'] and (args.nav_probe_delta is None or report['native_NAV_verified']))) if writer else None),
            ('capsules',lambda:runtime.wm_private_capsules.close() if runtime is not None and getattr(runtime,'wm_private_capsules',None) is not None else None),
            ('observer',lambda:observer.close() if observer else None)):
            try:
                value=action()
                if value is not None:report[name+'_closure']=value
            except Exception as error:cleanup.append(name+':'+str(error))
        if option_probe is not None:report['native_option_probe']=option_probe.report()
        if nav is not None:
            try:report['registered_NAV']=nav.report()
            except Exception as error:cleanup.append('NAV report:'+str(error))
        if owner is not None:
            try:report['capture']=report['capture_at_handoff'] if nav is not None and 'capture_at_handoff' in report else owner.report()
            except Exception as error:cleanup.append('capture report:'+str(error))
        if cleanup:report.update(cleanup_errors=cleanup,native_capture_verified=False,native_NAV_verified=False)
        report['caller_outcome']=report.get('outcome')
        report.update(main_motor_steps=tick,main_sim_seconds=float(runtime.sim.data.time) if runtime else 0.,wall_seconds=time.monotonic()-started)
        journal.close();save(root/'report.json',report)
    print(json.dumps(report,ensure_ascii=False));return 0 if report.get('outcome')=='zero_step_capture_command_screened' or (report['native_capture_verified'] and (args.nav_probe_delta is None or report['native_NAV_verified'])) else 2

if __name__=='__main__':raise SystemExit(main())
