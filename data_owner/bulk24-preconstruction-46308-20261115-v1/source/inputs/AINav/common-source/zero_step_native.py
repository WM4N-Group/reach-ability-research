#!/usr/bin/env python3
"""One-shot A800 original-scene RGBD/DeepSeek vision preflight, NOT control pass.

No main-world motor steps. Original separate stance calibration is explicitly
accounted, not disguised as zero physics. Credentials arrive only in memory.
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
import traceback


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True)
    parser.add_argument('--bundle', required=True)
    parser.add_argument('--root', required=True)
    parser.add_argument('--gpu-lock', required=True)
    parser.add_argument('--api-vision', action='store_true')
    parser.add_argument('--compose-nav-pilot', action='store_true')
    parser.add_argument('--compose-full-course', action='store_true')
    args = parser.parse_args()
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    source, bundle, root = [Path(p).resolve() for p in (args.source,args.bundle,args.root)]
    if root.exists() or not source.is_dir() or not bundle.is_dir():
        raise ValueError('Fresh independent root and existing frozen source/assets required')
    root.mkdir(parents=True, exist_ok=False)
    os.environ.update(MUJOCO_GL='egl', MUJOCO_EGL_DEVICE_ID='1', PYTHONDONTWRITEBYTECODE='1')
    os.environ.pop('CUDA_VISIBLE_DEVICES', None)  # Preserve original EGL device numbering.
    sys.path.insert(0, str(source))
    from ainav.contracts import file_sha
    from ainav.evidence import Journal
    from ainav.native.resources import ResourceLease
    from ainav.native.observation import AcquisitionPublisher
    journal = Journal(root/'events.jsonl')
    report = dict(schema='ainav-original-scene-zero-step-v1', started_at=datetime.now().astimezone().isoformat(),
        a800_host=os.uname().nodename, role='seen-development-only', main_world_physical_steps=0,
        model_control_decisions=0, robot_control_chain_verified=False, full_course_passed=False,
        world_model_used=False, source=str(source), bundle=str(bundle),
        source_manifest_sha256=file_sha(source/'ainav-source.json'), automatic_retry=False,
        actor_retrained=False, credentials_persisted=False, api_vision_verified=False)
    runtime = observer = None
    started = time.monotonic()
    try:
        with ResourceLease([args.gpu_lock]) as lease:
            save(root/'resource-admission.json', lease.evidence)
            with (root/'attempt.claim').open('x') as claim:
                claim.write(json.dumps(dict(pid=os.getpid(), max_launches=1, automatic_retry=False))+'\n')
            import importlib.metadata
            versions = {k:importlib.metadata.version(k) for k in ('torch','numpy','scipy','osqp','mujoco')}
            if versions['mujoco']!='3.3.2' or versions['osqp']!='1.1.3':
                raise ValueError('Exact original supported native solver/simulator versions required')
            report['versions'] = versions
            import numpy as np
            import torch
            torch.set_num_threads(2)
            from mujoco_zyh import integrated_course as integrated
            from mujoco_zyh.runtime_adapter import construct_runtime
            from mujoco_zyh.observer import OnboardObserver
            from mujoco_zyh.source_bundle import verify_bundle
            from mujoco_zyh.native_behavior_executor import world_snapshot
            from visual_box_proposals import propose_visual_candidates
            asset_receipt = verify_bundle(bundle)
            save(root/'asset-verification.json', asset_receipt)
            cases=[x for x in integrated.plan()['cases'] if x['case_id']=='full-4']
            if len(cases)!=1:raise ValueError('Exact original full-4 case required')
            native=integrated.protocol(cases[0]);integrated.validate_protocol(native)
            save(root/'original-native-protocol.json', native)
            # Bundle location is wrapper provenance, not a changed physical field.
            runtime,machine,construction=construct_runtime(bundle,dict(native,bundle=str(bundle)))
            report['original_auxiliary_calibration']=getattr(runtime,'wm_auxiliary_calibration',None)
            save(root/'construction.json',construction)
            before=world_snapshot(runtime)
            if float(runtime.sim.data.time)!=0.:raise ValueError('No main-world step allowed in this preflight')
            observer=OnboardObserver(runtime,native)
            packet,private_catalog=observer.capture(0,runtime.last.position)
            save(root/'private-catalog-not-model-input.json',private_catalog)
            def array(v):return v.detach().cpu().numpy() if hasattr(v,'detach') else np.asarray(v)
            proposals=propose_visual_candidates(array(packet['rgb'])[0,0],array(packet['depth_m'])[0,0],
                array(packet['camera_K'])[0],array(packet['T_base_optical'])[0])
            save(root/'pixel-proposals.json',proposals)
            descriptors=[]
            for index,desc in enumerate(proposals['candidates']):
                descriptors.append(dict(target_ref='frame0-region-%d'%index,
                    label='observed '+desc['appearance_family']+' appearance region; object type unknown',
                    bbox_xyxy=list(desc['pixel_bbox_xyxy']),evidence_ref='pixel-proposals.json#'+str(index)))
            observation=AcquisitionPublisher(root/'public-observations').publish(packet,now=0.,
                descriptors=descriptors,declared_map=dict(source_ref='no-static-map-in-zero-step',anchors=[]),
                goal='Observe the current scene before planning the original navigation task.',events=[])
            save(root/'public-observation.json',observation.value)
            if world_snapshot(runtime)!=before:raise RuntimeError('Capture/publication changed main world/FIFO')
            report.update(real_RGBD_verified=True,actual_frame_sha256=observation.value['rgb']['sha256'],
                          actual_pixel_proposals=len(descriptors),main_world_time_s=float(runtime.sim.data.time))
            if args.api_vision:
                from ainav.backend import create_vision_backend
                from ainav.vlm import RoleRunner
                backend=create_vision_backend(max_calls=1,max_tokens=2048,max_total_tokens=10000)
                roles=RoleRunner(backend,journal,timeout_s=90.)
                result=roles.run('scene_observer',dict(observation=observation.value,
                    task='Describe only currently visible regions/obstacles and uncertainty. Do not plan motor actions.'),observation)
                if (not isinstance(result,dict) or set(result)!={'scene_summary','visible_objects','uncertainties'}
                        or not isinstance(result['scene_summary'],str) or not isinstance(result['visible_objects'],list)
                        or not isinstance(result['uncertainties'],list)):
                    raise ValueError('Typed real-scene vision response required')
                save(root/'deepseek-vision.json',dict(result=result,provider_metadata=backend.last_response_metadata,
                     backend_identity=backend.identity,geometry_accuracy_validated=False,robot_command_issued=False))
                report['api_vision_verified']=True
            if world_snapshot(runtime)!=before:raise RuntimeError('API inference changed main world/FIFO')
            verify_bundle(bundle)
            if args.compose_nav_pilot or args.compose_full_course:
                from ainav.backend import create_vision_backend
                from ainav.vlm import RoleRunner
                from ainav.planner import AinavPlanner
                from ainav.native.nav_pilot import NavPilot
                from mujoco_zyh import stall_stow as stall, native_behavior_executor as api
                from mujoco_zyh.streams import ChunkedEpisodeWriter
                manifest=json.loads((bundle/'MANIFEST.json').read_text())
                writer=ChunkedEpisodeWriter(root/'composed-episode',dict(native,
                    joint_names=runtime.push['model'].JOINTS,actor_sha256=manifest['actor_sha256'],physics_dt_s=.005,control_dt_s=.02))
                composed=None
                try:
                    actual_backend=create_vision_backend(max_calls=1,max_tokens=2048,max_total_tokens=10000)
                    Host=NavPilot
                    if args.compose_full_course:
                        from ainav.native.full_course import FullCourse
                        Host=FullCourse
                    composed=Host(runtime=runtime,native_a=machine,observer=observer,writer=writer,root=root,
                        config=dict(native,bundle=str(bundle)),api=api,integrated=integrated,stall=stall,
                        planner=AinavPlanner(RoleRunner(actual_backend,journal),journal),journal=journal)
                    composed.capture_grid()
                    if args.compose_full_course:
                        real_obs=composed.observe_public(0.)
                        prepared=0
                        for target,body in composed.entity_by_ref.items():
                            e=composed.entities[body]
                            g=runtime.staircase.climb_geometry(runtime.sim,e['surface'])
                            composed.resolver.prepare_push(target,distance_m=.6,attempt_id='zero-software-'+str(prepared),
                                approach_xy=(float(g['front'])-.58,native['integrated_case']['lane_y_m']),surface_height_m=e['initial_bottom'])
                            prepared+=1
                        # Private software-only goal-mode test on the actual
                        # compiled body, not an image-binding/admission claim.
                        e=composed.entities['wm_object_middle']
                        delta=.6
                        view,receipt=composed.resolver.contexts.make_target_context(runtime,runtime.wm_candidate_contacts,'middle',
                            declared_push=dict(distance_m=delta,declaration_id='zero-absolute-goal-mode',goal_xy_m=(2.3,native['integrated_case']['lane_y_m'])),
                            cfg_overrides={'box_size':tuple(e['size'])})
                        if not np.allclose(view.box_push_target.detach().cpu().numpy()[0,:2],[2.3,native['integrated_case']['lane_y_m']],atol=1e-6):
                            raise ValueError('Absolute native goal mode was not actually bound')
                        report['absolute_goal_mode_software_verified']=True
                        report['absolute_goal_mode_visual_admission_claimed']=False
                        report['actual_full_visual_associations']=len(composed.last_descriptors)
                        report['actual_dynamic_push_software_bindings']=prepared
                        report['current_public_observation_sha256']=real_obs.sha256
                    if world_snapshot(runtime)!=before or float(runtime.sim.data.time)!=0.:
                        raise RuntimeError('Pilot composition stepped or changed the actual world/FIFO')
                    report['nav_pilot_composed_real_world']=True
                    report['full_course_composed_real_world']=bool(args.compose_full_course)
                    report['nav_pilot_live_commands_issued']=0
                finally:
                    if composed is not None:
                        composed.prefix.log.close();composed.prefix.recovery_log.close()
                        if hasattr(composed,'private_samples'):composed.private_samples.close()
                    writer.close(outcome='zero_step_composition',terminal_time_s=float(runtime.sim.data.time),censored=True)
            report['outcome']='real_RGBD_and_API_vision' if args.api_vision else 'real_RGBD_only'
    except BaseException as error:
        # Do not dump arbitrary process env/credentials or raw Authorization.
        key=os.environ.get('DEEPSEEK_API_KEY','')
        detail=type(error).__name__+': '+str(error)
        if key:detail=detail.replace(key,'[REDACTED]')
        report.update(outcome='failed_no_retry',error=detail)
        if runtime is None:runtime=getattr(error,'wm_partial_runtime',None)
        if runtime is not None:
            report['original_auxiliary_calibration']=getattr(runtime,'wm_auxiliary_calibration',None)
            report['main_world_time_s']=float(runtime.sim.data.time)
        print(json.dumps({'outcome':report['outcome'],'error':detail}),flush=True)
    finally:
        if observer is not None:observer.close()
        journal.close()
        report['wall_seconds']=time.monotonic()-started
        save(root/'report.json',report)
    print(json.dumps(report,ensure_ascii=False),flush=True)
    return 0 if report['outcome'].startswith('real_RGBD') else 2


if __name__=='__main__':
    raise SystemExit(main())
