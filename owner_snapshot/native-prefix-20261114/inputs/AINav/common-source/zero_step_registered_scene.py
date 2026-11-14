#!/usr/bin/env python3
"""A800 zero-step integration of common registry, real native target views and RGBD.

Runs old/new cases through the same adapters. No planner/API calls, action
admission or task motor steps. Separate original stance calibration is counted.
"""
import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path
import resource
import sys
import time


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):
    def convert(v):
        if hasattr(v,'tolist'):return v.tolist()
        raise TypeError(type(v).__name__)
    Path(p).write_text(json.dumps(x,indent=2,ensure_ascii=False,allow_nan=False,default=convert)+'\n')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for k in ('source','bundle','case-root','root','gpu-lock'):ap.add_argument('--'+k,required=True)
    ap.add_argument('--case-format',choices=('legacy-full4','transfer'),required=True)
    a=ap.parse_args();root=Path(a.root).resolve();source=Path(a.source).resolve();case=Path(a.case_root).resolve()
    if root.exists():raise FileExistsError('Fresh independent preflight root required')
    root.mkdir(parents=True,exist_ok=False);resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    os.environ.update(MUJOCO_GL='egl',MUJOCO_EGL_DEVICE_ID='1',PYTHONDONTWRITEBYTECODE='1')
    sys.path.insert(0,str(source))
    from ainav.native.resources import ResourceLease
    report=dict(schema='ainav-registered-scene-native-preflight-v1',case_format=a.case_format,source_manifest_sha256=sha(source/'ainav-source.json'),
        main_motor_steps=0,main_actor_forwards=0,API_calls=0,task_success=False,navigation_trial_started=False,
        current_native_admission_claimed=False,automatic_retry=False)
    observer=None;runtime=None;start=time.monotonic()
    try:
        with ResourceLease([a.gpu_lock]) as lease:
            save(root/'resource-admission.json',lease.evidence);save(root/'attempt.claim',dict(pid=os.getpid(),max_launches=1,main_steps_budget=0))
            import numpy as np
            import torch
            import mujoco
            from PIL import Image
            torch.set_num_threads(2)
            from ainav.native.scene_registry import SceneRegistry,RegisteredTerrain
            from ainav.native.registered_runtime import construct_cold_runtime
            from ainav.native.registered_observer import RegisteredObserver
            from ainav.native import registered_target_context as contexts
            from ainav.native.registered_bindings import RegisteredBindingResolver,_SOURCES
            from mujoco_zyh import native_behavior_executor as api,stall_stow,integrated_course
            from mujoco_zyh.source_bundle import verify_bundle
            from ainav.contracts import canonical
            report['asset_verification_before']=verify_bundle(a.bundle)
            if a.case_format=='transfer':
                scene=json.loads((case/'scene.json').read_text());bindings=json.loads((case/'private-object-bindings.json').read_text())
                registry=SceneRegistry.from_transfer(scene,bindings);model_path=case/'scene.mjb'
                old_report=json.loads((case/'report.json').read_text());model_sha=old_report['scene_model_sha256']
                if sha(model_path)!=model_sha:raise ValueError('Verified static scene changed')
                initial=scene['initial_robot'];initial_z=registry.surfaces[initial['support']].top_z_m
                report['scene_sha256']=sha(case/'scene.json')
            else:
                from mujoco_zyh.review_capture import load_display_model
                protocol=json.loads((case/'original-native-protocol.json').read_text());integrated_course.validate_protocol(protocol)
                registry=SceneRegistry.from_legacy_full4(protocol,integrated_course.layout(protocol['integrated_case']))
                model=load_display_model(case/'review-state');model_path=root/'static-original-model.mjb';mujoco.mj_saveModel(model,str(model_path));model_sha=sha(model_path)
                initial=dict(xy_m=[-.08,0.],yaw_rad=0.,support='ground');initial_z=0.;report['scene_sha256']=sha(case/'original-native-protocol.json')
            runtime,construction=construct_cold_runtime(a.bundle,model_path,model_sha256=model_sha,initial_robot=initial,initial_surface_height_m=initial_z)
            p=runtime.sim;report['construction']=construction;report['compiled_registry']=registry.verify_compiled(p.model)
            save(root/'registry-public-geometry.json',registry.public_geometry())
            before=api.world_snapshot(runtime);history_before=stall_stow.history_sha(p)
            global_aliases=(id(p.scene['box']),id(p.controller),id(p.box_push_target));sensors={k:id(v) for k,v in p.scene.sensors.items()}
            receipt=contexts.register_candidate_channels(runtime,registry);runtime.wm_candidate_contacts=receipt
            save(root/'private-contact-registry.json',receipt)
            results=[];views=[]
            for ref,o in registry.objects.items():
                view,proof=contexts.make_target_context(runtime,receipt,ref,cfg_overrides={'box_size':o.size_m},
                    declared_push={'distance_m':.2,'declaration_id':'zero-software-binding-'+ref})
                views.append(view)
                with runtime.push.active():
                    observation=view.observation();flags=view.termination()
                    hand=runtime.push['bridge'].box_push.hand_contact(view,view.hand_cfg)
                target=view.box_push_target.detach().cpu().numpy()[0];expected=p.data.xpos[p.model.body(o.body_name).id].copy();expected[0]+=.2
                if not np.allclose(target,expected,rtol=0,atol=1e-6):raise ValueError('Prospective target not the actual selected body')
                if view.controller is p.controller or view.queue is not p.queue or view.data is not p.data:raise ValueError('Context alias/history ownership invalid')
                if not np.isfinite(observation).all():raise ValueError('Nonfinite actual native observation')
                try:view.physics_step()
                except RuntimeError:pass
                else:raise ValueError('Selected view illegally acquired motor authority')
                if api.world_snapshot(runtime)!=before or stall_stow.history_sha(p)!=history_before:raise ValueError('Binding/readers changed original world/history/FIFO')
                results.append(dict(ref=ref,body=o.body_name,actual_observation_shape=list(observation.shape),
                    actual_native_flags={k:bool(v) for k,v in flags.items()},hand_contact=bool(hand[0]),
                    prospective_goal=target.tolist(),selected_goal_sha256=api.array_sha(view.box_push_target.numpy()),
                    shared_world_and_fifo=True,independent_controller=True,can_step_world=False,
                    actual_entry_admitted=False,physics_steps=0,native_completion_clock=view.settled.report()))
            if len({id(v.controller) for v in views})!=len(views):raise ValueError('Target controllers share hidden mutable state')
            if global_aliases!=(id(p.scene['box']),id(p.controller),id(p.box_push_target)) or any(id(p.scene.sensors[k])!=v for k,v in sensors.items()):
                raise ValueError('Original aliases or sensors replaced')
            observer=RegisteredObserver(runtime,dict(width=192,height=128,scene_recipe='registered'),registry)
            packet,private=observer.capture(0,runtime.last.position)
            Image.fromarray(packet['rgb'].numpy()[0,0]).save(root/'actual-onboard-rgb.png');np.save(root/'actual-depth.npy',packet['depth_m'].numpy(),allow_pickle=False)
            save(root/'private-observer-catalog.json',private)
            proposals=importlib.import_module('visual_box_proposals');geometry=importlib.import_module('native_visual_target_binding')
            modules={n:importlib.import_module(n) for n in _SOURCES};modules['mujoco_selected_target_context']=contexts
            sources={n:sha(m.__file__) for n,m in modules.items()}
            resolver=RegisteredBindingResolver(runtime,proposals=proposals,geometry=geometry,contexts=contexts,
                native_api=api,native_history_sha=stall_stow.history_sha,source_sha256=sources,registry=registry)
            descriptors=resolver.observe(packet,control_tick=0,physical_tick=0)
            save(root/'private-visual-associations.json',dict(descriptors=descriptors,source_sha256=sources,model_input=False))
            terrain=RegisteredTerrain(registry);geometries=[]
            for ref in registry.objects:
                o=registry.objects[ref];height=registry.surfaces[o.initial_support].top_z_m
                g=terrain.climb_geometry(p,ref,source_surface_height_m=height)
                geometries.append(dict(ref=ref,geometry=g,admission_claimed=False))
            # Query all fixed supports too, with explicit 20cm lower source.
            for ref,s in registry.surfaces.items():
                if s.top_z_m>0:geometries.append(dict(ref=ref,geometry=terrain.climb_geometry(p,ref,source_surface_height_m=s.top_z_m-.2),admission_claimed=False))
            from ainav.native.registered_guards import check_object_contacts,goal_region_gate
            from ainav.native.course_tools import movement_entry,nav_backend
            contact_check=check_object_contacts(runtime,registry)
            foot_ids=[p.model.body(n+'_foot').id for n in ('FR','FL','RR','RL')]
            goal_check=goal_region_gate(registry,feet_world_m=p.data.xpos[foot_ids].tolist(),
                foot_vertical_load_N=p.forces[foot_ids,2].tolist(),base_linear_speed_m_s=float(np.linalg.norm(p.data.qvel[:3])),
                base_angular_speed_rad_s=float(np.linalg.norm(p.data.qvel[3:6])),tilt_rad=float(runtime.n.state()[3]),require_stop=True)
            if goal_check['passed']:raise ValueError('Initial state must not be reported as terminal goal')
            try:movement_entry(runtime);movement=dict(admitted=True)
            except ValueError as error:movement=dict(admitted=False,reason=str(error))
            nav_contracts=[]
            for height in sorted({s.top_z_m for s in registry.surfaces.values()}):
                try:nav_contracts.append(dict(height_m=height,backend=nav_backend(runtime,height),current_support_not_claimed=True))
                except ValueError as error:nav_contracts.append(dict(height_m=height,backend=None,reason=str(error),current_support_not_claimed=True))
            report.update(registered_object_contact_check=contact_check,initial_goal_check=goal_check,
                original_movement_READY=movement,arm_state_NAV_contract_queries=nav_contracts,
                live_contact_forces_after_motor_steps_not_yet_verified=True,
                remaining_execution_gates=['Cold-start supported owner without mandatory failed-A prefix',
                    'Protected NAV handoff on arbitrary declared support including .2m',
                    'Generic currently-admitted action catalogue and exact factory binding',
                    'CLIMB and final-stop session handoff through registry geometry',
                    'PUSH settled versus 10mm dock completion remains unresolved'])
            if api.world_snapshot(runtime)!=before or stall_stow.history_sha(p)!=history_before or runtime.step_count or p.data.time:
                raise ValueError('Zero-step integration changed world/history')
            report.update(outcome='registered_native_context_and_RGBD_zero_step_passed',
                targets=results,actual_visual_associations=len(descriptors),all_objects_registered=len(results),
                native_climb_geometry_queries=geometries,actual_RGBD_nonempty=bool(packet['rgb'].numpy().std()>1),
                original_goal_history_aliases_and_FIFO_preserved=True,shared_adapter_no_fixed_object_successors=True,
                source_bundle_verification_after=verify_bundle(a.bundle),auxiliary_calibration=runtime.wm_auxiliary_calibration)
    except Exception as error:
        report.update(outcome='failed_zero_step_no_retry',error=type(error).__name__+': '+str(error))
        if runtime is not None:report.update(auxiliary_calibration=runtime.wm_auxiliary_calibration,actual_main_time_s=float(runtime.sim.data.time),actual_main_steps=runtime.step_count)
    finally:
        if observer is not None:observer.close()
        report['wall_seconds']=time.monotonic()-start;save(root/'report.json',report)
    print(json.dumps(report,ensure_ascii=False));return 0 if report['outcome']=='registered_native_context_and_RGBD_zero_step_passed' else 2

if __name__=='__main__':raise SystemExit(main())
