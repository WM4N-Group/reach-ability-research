#!/usr/bin/env python3
"""One same-world current-query PUSH→NAV engineering handoff, NOT a VLM route.

Source scene, actor, motor, public XY and dock thresholds identical across the
uncompensated/reference-offset arms. Each has a fresh root/world; never resume a
failed attempt, shift an active goal or conceal the separate drive reference.
"""
import argparse
from datetime import datetime
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
    def cast(v):
        if hasattr(v,'tolist'):return v.tolist()
        raise TypeError(type(v).__name__)
    Path(p).write_text(json.dumps(x,indent=2,ensure_ascii=False,default=cast,allow_nan=False)+'\n')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for k in ('source','bundle','case-root','root','gpu-lock','target-ref','target-surface','support-ref'):ap.add_argument('--'+k,required=True)
    ap.add_argument('--initial-xy',nargs=2,type=float,required=True);ap.add_argument('--lane-y',type=float,required=True)
    ap.add_argument('--mode',choices=('uncompensated','declared_native_stop_offset'),required=True)
    ap.add_argument('--handoff-policy',choices=('after_native_confirmation','arrival_brake_with_native_confirmation'),default='after_native_confirmation')
    ap.add_argument('--body-braking-reference',choices=('native_drive','public_placement'),default='native_drive')
    ap.add_argument('--brake-arm-policy',choices=('issued_hold','original_unload','reconciled_unload'),default='issued_hold')
    ap.add_argument('--stop-leg-policy',choices=('held_native_scale','reverse_after_native_confirmation'),default='held_native_scale')
    ap.add_argument('--next-nav-delta',nargs=2,type=float,required=True)
    ap.add_argument('--next-nav-index',type=int,choices=(0,1),default=0)
    ap.add_argument('--zero-step',action='store_true');ap.add_argument('--preflight-report')
    a=ap.parse_args();source,bundle,case,root=[Path(x).resolve() for x in (a.source,a.bundle,a.case_root,a.root)]
    configuration=dict(case_root=str(case),target_ref=a.target_ref,target_surface=a.target_surface,support_ref=a.support_ref,initial_xy=a.initial_xy,lane_y=a.lane_y,mode=a.mode,handoff_policy=a.handoff_policy,body_braking_reference=a.body_braking_reference,brake_arm_policy=a.brake_arm_policy,stop_leg_policy=a.stop_leg_policy,next_nav_delta=a.next_nav_delta,next_nav_index=a.next_nav_index)
    if (a.mode,a.handoff_policy,a.body_braking_reference,a.brake_arm_policy,a.stop_leg_policy)!=('declared_native_stop_offset','arrival_brake_with_native_confirmation','public_placement','reconciled_unload','reverse_after_native_confirmation'):
        raise ValueError('Common host probe requires the already-proven explicit stop configuration')
    import math
    if not all(math.isfinite(v) for v in a.next_nav_delta) or not .05<=math.hypot(*a.next_nav_delta)<=.5:raise ValueError('Bounded explicit engineering NAV delta required')
    if root.exists():raise FileExistsError('Fresh independent root required; no retries')
    if not a.zero_step:
        if not a.preflight_report:raise ValueError('Matching zero-step placement preflight required')
        z=json.loads(Path(a.preflight_report).read_text())
        if z.get('outcome')!='zero_step_placement_binding_verified' or z['configuration']!=configuration or z['source_manifest_sha256']!=sha(source/'ainav-source.json'):
            raise ValueError('Actual preflight/config/source mismatch')
        if a.handoff_policy=='arrival_brake_with_native_confirmation':
            if not z.get('common_host_zero_entry_denied') or not z.get('common_host_zero_opaque_body_contract_link_verified'):raise ValueError('Zero-step live-owner denial not verified')
            proof=z.get('two_phase_preflight',{})
            if (not all(proof.get(k) is True for k in ('exact_native_session_class','unissued_stop_seed_denied',
                    'native_finish_not_fabricated','brake_owner_not_created_without_actual_issue','task_success_not_claimed'))
                    or proof.get('main_steps')!=0 or proof.get('clock',{}).get('native_advances')!=0):
                raise ValueError('Actual two-phase zero-step contract has not passed')
            if proof.get('declared_leg_policy')!=a.stop_leg_policy:raise ValueError('Actual declared stop-leg preflight mismatch')
            if proof.get('declared_arm_policy')!=a.brake_arm_policy:raise ValueError('Actual declared brake-arm preflight mismatch')
            if a.body_braking_reference=='public_placement':
                body=proof.get('body_braking_reference')
                if (not body or not proof.get('actual_native_observation_finite')
                        or proof.get('actual_native_observation_shape')!=[226]
                        or body['declaration_sha256']!=z['body_braking_declaration']['declaration_sha256']):
                    raise ValueError('Actual declared body-reference/226D zero-step preflight missing')
    resource.setrlimit(resource.RLIMIT_CORE,(0,0));os.environ.update(MUJOCO_GL='egl',MUJOCO_EGL_DEVICE_ID='1',PYTHONDONTWRITEBYTECODE='1')
    root.mkdir(parents=True,exist_ok=False);sys.path.insert(0,str(source))
    from ainav.evidence import Journal
    from ainav.native.resources import ResourceLease
    journal=Journal(root/'events.jsonl');started=time.monotonic();runtime=capture=observer=writer=review=executor=session=None;tick=0;binding_record=None;stop_trace=None;host=None;chain_started=False;nav_session=None;push_terminal_tick=None
    report=dict(schema='ainav-placement-reference-engineering-probe-v1',started_at=datetime.now().astimezone().isoformat(),configuration=configuration,
        source_manifest_sha256=sha(source/'ainav-source.json'),zero_step=a.zero_step,main_motor_steps=0,model_API_calls=0,model_decisions=0,
        task_success=False,placement_and_stow_verified=False,chain_verified=False,cold_capture_verified=False,max_launches=1,automatic_retry=False,
        max_sim_seconds=120.,max_wall_seconds=600.,physical_reset_after_initial=False,
        scope='same_world_common_host_PUSH_then_NAV_engineering_fixture_NOT_model_route_or_full_task')
    try:
        with ResourceLease([a.gpu_lock]) as lease:
            save(root/'resource-admission.json',lease.evidence);save(root/'attempt.claim',dict(pid=os.getpid(),max_launches=1))
            import numpy as np
            import torch
            import mujoco
            torch.set_num_threads(2)
            from ainav.native.scene_registry import SceneRegistry
            from ainav.native.registered_runtime import construct_cold_runtime
            from ainav.native.supported_capture import SupportedCapture,ActualCaptureWitness
            from ainav.native.registered_observer import RegisteredObserver
            from ainav.native import registered_target_context as contexts
            from ainav.native.registered_bindings import RegisteredBindingResolver,_SOURCES
            from ainav.native.registered_guards import check_object_contacts
            from ainav.native.placement_contract import PlacementContract,PlacementTerrain,wrap_placement_session
            from ainav.native.session_factory import BehaviorSessionFactory
            from ainav.native.registered_skill_factory import RegisteredSkillSessionFactory
            from ainav.native.observation import AcquisitionPublisher
            from ainav.native.behavior_authority import BehaviorOption
            from ainav.contracts import DecisionBatch,canonical
            from mujoco_zyh import integrated_course,stall_stow,native_behavior_executor as api
            from mujoco_zyh.source_bundle import verify_bundle
            from mujoco_zyh.review_capture import load_display_model,WorldStateRecorder
            from mujoco_zyh.streams import ChunkedEpisodeWriter
            from mujoco_zyh.failure_capsules import install,emit
            report['asset_verification_before']=verify_bundle(bundle)
            native=json.loads((case/'original-native-protocol.json').read_text());integrated_course.validate_protocol(native)
            registry=SceneRegistry.from_legacy_full4(native,integrated_course.layout(native['integrated_case']))
            obj=registry.objects[a.target_ref];support=registry.surfaces[a.support_ref];target=registry.surfaces[a.target_surface]
            if obj.initial_support!=a.support_ref or abs(target.top_z_m-support.top_z_m-obj.size_m[2])>1e-8:raise ValueError('Declared docking level/box geometry mismatch')
            model=load_display_model(case/'review-state');model_path=root/'static-scene.mjb';mujoco.mj_saveModel(model,str(model_path));model_sha=sha(model_path)
            initial=dict(xy_m=a.initial_xy,yaw_rad=0.,support=a.support_ref)
            runtime,construction=construct_cold_runtime(bundle,model_path,model_sha256=model_sha,initial_robot=initial,
                initial_surface_height_m=support.top_z_m,initial_arm_reference=stall_stow.STOW_ARM)
            registry.verify_compiled(runtime.sim.model);save(root/'construction.json',construction)
            p=runtime.sim;report.update(auxiliary_calibration=runtime.wm_auxiliary_calibration,delay_steps=p.delays.tolist(),effort_limits_nm=runtime.push['model'].EFFORT.tolist())
            contract=PlacementContract(a.target_ref,(target.bounds_xy_m[0]-obj.size_m[0]/2,a.lane_y),target.bounds_xy_m[0],obj.size_m,
                support.top_z_m,float(p.cfg.push_stop_distance),a.mode)
            nominal_center=float(p.model.body(obj.body_name).pos[0]);drive_distance=contract.drive_goal_xy_m[0]-nominal_center
            if not 0<drive_distance<=.8:raise ValueError('Prospective native drive goal outside original forward workspace')
            report.update(placement_contract=contract.public(),placement_contract_sha256=contract.sha256,declared_native_drive_distance_m=drive_distance,
                box_parameters=dict(size_m=obj.size_m,mass_kg=float(p.model.body(obj.body_name).mass[0])))
            save(root/'declared-placement-and-drive.json',contract.public())
            runtime.staircase=PlacementTerrain(contract)
            if a.handoff_policy=='arrival_brake_with_native_confirmation':
                from ainav.native.stop_actor_trace import StopActorTrace
                stop_trace=StopActorTrace(root,max_proposals=1000,max_bytes=8*1024*1024)
            runtime.wm_completion_clock_journal=journal
            runtime.wm_candidate_contacts=contexts.register_candidate_channels(runtime,registry)
            install(runtime,root,native['private_failure_capsules'])
            capture=SupportedCapture(runtime,registry,support_ref=a.support_ref,journal=journal)
            observer=RegisteredObserver(runtime,dict(width=192,height=128,scene_recipe='registered'),registry)
            publisher=AcquisitionPublisher(root/'query-observations')
            modules={n:importlib.import_module(n) for n in _SOURCES};modules['mujoco_selected_target_context']=contexts
            source_shas={n:sha(m.__file__) for n,m in modules.items()}
            resolver=RegisteredBindingResolver(runtime,proposals=modules['visual_box_proposals'],geometry=modules['native_visual_target_binding'],contexts=contexts,
                native_api=api,native_history_sha=stall_stow.history_sha,source_sha256=source_shas,registry=registry)
            original_global_goal_sha=api.array_sha(p.box_push_target.numpy());original_global_history=stall_stow.history_sha(p)
            def prepare_selected():
                nonlocal binding_record
                before=api.world_snapshot(runtime)
                packet,_=observer.capture(tick//4,runtime.last.position)
                descriptors=resolver.observe(packet,control_tick=tick//4,physical_tick=tick)
                refs=[ref for ref,(body,_) in resolver._observed.items() if body==obj.body_name]
                if len(refs)!=1:raise ValueError('Selected declared object lacks current unambiguous RGBD association')
                ref=refs[0];attempt=root.name+'-push-once'
                goal_sha=resolver.prepare_push(ref,distance_m=drive_distance,attempt_id=attempt,
                    approach_xy=tuple(a.initial_xy),surface_height_m=support.top_z_m,goal_xy_m=contract.drive_goal_xy_m,
                    body_braking_goal_xy_m=contract.public_goal_xy_m if a.body_braking_reference=='public_placement' else None)
                body_proof=None
                if a.body_braking_reference=='public_placement':
                    prebound=resolver._pushes[attempt].view
                    body_proof=prebound.body_braking_reference.receipt()
                    report['body_braking_declaration']=body_proof
                public=[]
                for d in descriptors:
                    g=d['descriptor'];public.append(dict(target_ref=d['target_ref'],label='observed cuboid region',bbox_xyxy=g['pixel_bbox_xyxy'],evidence_ref='current-rgbd-association'))
                obs=publisher.publish(packet,now=float(p.data.time),descriptors=public,
                    declared_map=dict(source_ref='frozen placement and drive reference contract',anchors=[
                        dict(target_ref='public_placement',description='Immutable task placement, not native drive reference',position_xyz_m=[*contract.public_goal_xy_m,support.top_z_m],uncertainty_xyz_m=[0.,0.,0.]),
                        dict(target_ref='native_drive_reference',description='Immutable original arm/NN drive reference, not task success goal',position_xyz_m=[*contract.drive_goal_xy_m,support.top_z_m],uncertainty_xyz_m=[0.,0.,0.])] +
                        ([dict(target_ref='body_braking_reference',description='Immutable public placement reference used only for requested body velocity',position_xyz_m=[*contract.public_goal_xy_m,support.top_z_m],uncertainty_xyz_m=[0.,0.,0.])] if body_proof is not None else [])),
                    goal='Brake arm policy: '+a.brake_arm_policy+'. Body braking reference: '+a.body_braking_reference+'. Isolated engineering docking test. Original public XY and 10mm dock plus actual native stop/stow are required.',events=[])
                if body_proof is not None:
                    journal(dict(event='body_braking_reference_prebound_before_query',receipt=body_proof,time_s=float(p.data.time),model_input=False))
                proof=journal(dict(event='engineering_placement_candidate_prepared',time_s=float(p.data.time),contract_sha256=contract.sha256,
                    public_goal_xy=list(contract.public_goal_xy_m),native_drive_goal_xy=list(contract.drive_goal_xy_m),model_input=False))
                option=BehaviorOption('placement-probe','PUSH',ref,tuple(sorted(dict(push_distance_m=drive_distance,surface_height_m=support.top_z_m).items())),60.,proof,
                    attempt_id=attempt,original_push_goal_sha256=goal_sha)
                batch=DecisionBatch(root.name,obs,(option,),canonical(dict(source_ref='common NAV/PUSH host engineering query, no VLM selection',skills=['NAV','PUSH'],
                    constraints=['No VLM policy in this experiment','Placement point and native drive reference are declared separately','Native and physical goal checks remain mandatory'])))
                def extra_guards():
                    if api.array_sha(p.box_push_target.numpy())!=original_global_goal_sha or stall_stow.history_sha(p)!=original_global_history:
                        raise RuntimeError('Selected PUSH altered original global goal/history')
                    check_object_contacts(runtime,registry,selected_push_ref=a.target_ref)
                factory=BehaviorSessionFactory(runtime,bundle,resolver,extra_guards,native_api=api)
                if api.world_snapshot(runtime)!=before:raise RuntimeError('Prospective placement binding changed physical state/FIFO')
                binding_record=dict(query_sha256=batch.sha256,option_sha256=option.sha256,original_drive_goal_sha256=goal_sha,
                    public_placement_contract_sha256=contract.sha256,observation_sha256=obs.sha256,actual_visual_associations=len(descriptors))
                journal(dict(event='engineering_current_public_placement_query',**batch.public(),model_decision=False))
                return option,batch,factory
            def new_host(backend,witness):
                common=RegisteredSkillSessionFactory(runtime,registry,initial_witness=witness,journal=journal,
                    push_backend=backend,placement_contracts={contract.target_ref:contract},native_api=api)
                common.stop_trace=stop_trace
                current=api.NativeOptionExecutor(runtime,common,journal);common.attach_executor(current)
                return common,current
            if a.zero_step:
                option,batch,backend=prepare_selected();host,executor=new_host(backend,None)
                try:host.bind_batch(batch)
                except ValueError as denied:
                    if 'Actual live' not in str(denied):raise
                    report['common_host_zero_entry_denied']=True
                else:raise RuntimeError('Common host admitted a fabricated zero-step capture')
                # Check the original prospective native construction separately,
                # NEVER installing it in the common executor without a live owner.
                backend.bind_query(batch.sha256,(option,))
                linked,linked_support=host.prospective_push_contract(option,batch.sha256)
                if linked is not contract or linked_support!=a.support_ref:raise RuntimeError('Opaque-ref contract binding mismatch')
                report['common_host_zero_opaque_body_contract_link_verified']=True
                from ainav.native.placement_handoff import wrap_two_phase_placement
                session=wrap_two_phase_placement(backend(option),contract,journal,arm_policy=a.brake_arm_policy,
                    leg_policy=a.stop_leg_policy,stop_trace=stop_trace)
                report['common_host_zero_native_session_installed']=executor.session is not None
                from ainav.native.push_stow_witness import ActualPushStowSupportWitness
                try:ActualPushStowSupportWitness(runtime,session,executor,registry,support_ref=a.support_ref)
                except ValueError as denied:
                    if 'succeeded boundary' not in str(denied):raise
                    report['common_host_unissued_live_stow_owner_denied']=True
                else:raise RuntimeError('Unissued prospective session fabricated a live stow owner')
                if p.data.time or runtime.step_count or len(p.queue):raise RuntimeError('Zero-step binding issued motor steps')
                if a.handoff_policy=='arrival_brake_with_native_confirmation':
                    machine=session.machine
                    with runtime.push.active():actual_policy_observation=machine.native.r.sim.observation()
                    if actual_policy_observation.shape!=(226,) or not np.isfinite(actual_policy_observation).all():
                        raise RuntimeError('Actual original 226D body-reference observation invalid')
                    try:machine.services.issued.seed()
                    except RuntimeError as denied:
                        if 'actually issued native observation' not in str(denied):raise
                        no_seed=True
                    else:raise RuntimeError('Unissued stop seed was fabricated at zero-step preflight')
                    report['two_phase_preflight']=dict(
                        exact_native_session_class=isinstance(session,api.NativeOptionSession),
                        machine_class=type(machine).__name__,clock=machine.services.clock_report(),
                        declared_arm_policy=machine.services.arm_policy,declared_leg_policy=machine.services.leg_policy,
                        original_leg_release_ramp_s=float(machine.services.p.cfg.push_leg_release_ramp_s),
                        unissued_stop_seed_denied=no_seed,
                        native_finish_not_fabricated=machine.native.finish is None,
                        brake_owner_not_created_without_actual_issue=machine.brake is None,
                        task_success_not_claimed=True,main_steps=runtime.step_count,
                        actual_native_observation_shape=list(actual_policy_observation.shape),
                        actual_native_observation_finite=bool(np.isfinite(actual_policy_observation).all()),
                        body_braking_reference=machine.services.body_binding.receipt() if machine.services.body_binding is not None else None)
                    machine.services.assert_immutable()
                report.update(outcome='zero_step_placement_binding_verified',binding=binding_record,selected_controller_constructed=True,physical_entry_admitted=False)
            else:
                metadata=dict(native,schema='ainav-placement-reference-probe-v1',source_id=root.name,episode_id=root.name+'-episode0',source_group='placement-engineering-only',
                    role='seen-development-only',scene_recipe='registered',suite_case={'family':'placement'},review_scope='Isolated placement/drive reference probe | NO VLM or full-task success',
                    joint_names=runtime.push['model'].JOINTS,actor_sha256=json.loads((bundle/'MANIFEST.json').read_text())['actor_sha256'])
                metadata.pop('integrated_case',None);save(root/'probe-protocol.json',metadata)
                writer=ChunkedEpisodeWriter(root/'episode',metadata);review=WorldStateRecorder(root/'review-state',runtime,metadata,model_cache_dir=root.parent/'compiled-review-models')
                push_started_tick=None
                def start_explicit_nav_query():
                    nonlocal chain_started,nav_session,push_terminal_tick
                    import numpy as np
                    now=float(p.data.time);before=api.world_snapshot(runtime)
                    witness=host._current_completed_witness();witness.validate(runtime)
                    report['live_push_witness']=witness.report()
                    report['live_owner_provenance']=dict(original_class=type(witness.owner).__name__,
                        selected_runtime_distinct_from_global=witness.owner.r is not runtime,
                        selected_stow_same_data=witness.owner.recovery.s.data is p.data,
                        selected_stow_same_FIFO=witness.owner.recovery.s.queue is p.queue,
                        actual_last_two_equal_latest=bool(np.array_equal(witness.owner.last_two[-1],runtime.last.position)))
                    if api.world_snapshot(runtime)!=before:raise RuntimeError('Live completed-owner construction changed world/FIFO')
                    packet,_=observer.capture(tick//4,runtime.last.position);xy=p.data.qpos[:2].copy();dx,dy=a.next_nav_delta
                    if not np.isfinite([dx,dy]).all() or np.hypot(dx,dy)>.5 or np.hypot(dx,dy)<.05:raise ValueError('Bounded explicit engineering NAV delta required')
                    points=(xy+np.asarray([dx,dy]),xy+np.asarray([-dy,dx]))
                    anchors=[dict(target_ref='handoff_NAV_'+str(i),description='Explicit engineering next-goal, NOT model selection',position_xyz_m=[float(g[0]),float(g[1]),support.top_z_m],uncertainty_xyz_m=[0.,0.,0.]) for i,g in enumerate(points)]
                    obs=publisher.publish(packet,now=now,descriptors=[],declared_map=dict(source_ref='same-world engineering successor goal declarations',anchors=anchors),
                        goal='Verify live original PUSH handback and current-query common-host NAV only; no model route or full task claim.',events=[])
                    proof=journal(dict(event='actual_live_PUSH_owner_for_current_query',time_s=now,witness=witness.report(),model_input=False))
                    options=tuple(BehaviorOption('handoff-NAV-'+str(i),'NAV',entry['target_ref'],tuple(sorted(dict(goal_world_x_m=entry['position_xyz_m'][0],goal_world_y_m=entry['position_xyz_m'][1],surface_height_m=support.top_z_m).items())),60.,proof) for i,entry in enumerate(anchors))
                    batch=DecisionBatch(root.name+'-nav-current-query',obs,options,canonical(dict(source_ref='common NAV/PUSH host engineering fixture',skills=['NAV','PUSH'],constraints=['Explicit selection is not VLM output','Original loaded support and native guards retained'])))
                    host.bind_batch(batch);chosen=options[a.next_nav_index]
                    journal(dict(event='engineering_explicit_successor_selection',query_sha256=batch.sha256,selected_option_sha256=chosen.sha256,candidate_count=len(options),option=chosen.__dict__,model_decision=False))
                    push_terminal_tick=tick
                    rec=executor.start(chosen,batch.decision_id,now);nav_session=executor.session;chain_started=True
                    journal(dict(event='engineering_common_host_NAV_receipt',receipt=rec.__dict__,model_decision=False))
                    if api.world_snapshot(runtime)!=before:raise RuntimeError('Common executor handoff changed actual world/FIFO')
                    report['common_host_handoff']=dict(time_s=now,physical_tick=tick,query_sha256=batch.sha256,selected_option_sha256=chosen.sha256,
                        candidate_count=len(options),same_executor=True,same_native_session_class=True,no_physics_at_admission=True,model_decision=False)
                def verified_terminal():
                    if executor is None or not executor.reported_end:return False
                    if executor.last_outcome!='succeeded':raise RuntimeError('Actual common native option failed:'+str(executor.last_outcome))
                    if chain_started:
                        nav=nav_session.machine.native_nav
                        if not nav.complete or nav.arrival is None or not nav.arrival.complete or not all(nav.report()['native_goal_checks'].values()):raise RuntimeError('Original NAV and guarded arrival not complete')
                        session.refresh()  # refresh original selected cached sensors only, no clock/history reset
                        placement=session.machine.placement_receipt()
                        if not placement['placement_geometry_verified']:raise RuntimeError('Completed box placement lost during NAV')
                        emit(runtime,'push_nav_chain_success_terminal_observed',view=session.machine.native.r.sim,extra=dict(placement=placement,nav=nav.report()),preserve_primary_failure=False)
                        report.update(outcome='actual_PUSH_to_NAV_shared_host_verified',chain_verified=True,final_placement=placement,
                            guarded_NAV=nav.report(),common_host_sessions=len(executor.sessions),PUSH_terminal_tick=push_terminal_tick,
                            actual_NAV_motor_steps=tick-push_terminal_tick,selector='explicit_engineering_current_query_NOT_VLM',automatic_task_route_not_claimed=True)
                        return True
                    result=session.machine.placement_receipt()
                    if not result['placement_geometry_verified']:raise RuntimeError('Declared physical placement lost at completion')
                    emit(runtime,'placement_success_terminal_observed',view=session.machine.native.r.sim,extra=dict(placement=result),preserve_primary_failure=False)
                    report.update(placement_and_stow_verified=True,PUSH_completion_time_s=float(p.data.time),PUSH_final_placement=result,
                        native_results=session.machine.results,selected_native_completion_clock=session.machine.services.clock_report(),
                        actual_two_phase_brake=session.machine.brake.report())
                    save(root/'PUSH-completion.json',dict(source_manifest_sha256=report['source_manifest_sha256'],physical_tick=tick,
                        time_s=float(p.data.time),placement=result,native_results=report['native_results'],
                        original_native_clock=report['selected_native_completion_clock'],original_guarded_stop=report['actual_two_phase_brake']))
                    start_explicit_nav_query()
                    return False
                while True:
                    if time.monotonic()-started>600 or float(p.data.time)>=120:raise TimeoutError('Original bounded engineering probe budget reached')
                    if tick%20==0:
                        packet,private=observer.capture(tick//4,runtime.last.position);writer.append_visual(packet,control_tick=tick//4,private_catalog=dict(private,model_input_allowed=False));review.capture(tick//4)
                        writer.boundary(dict(control_tick=tick//4,physical_tick=tick,skill=('nav' if chain_started else 'push') if executor else 'cold_capture',phase=executor.session.machine.phase if executor else capture.phase))
                    if executor is not None and (tick-push_started_tick)%4==0:
                        executor.update()
                        for rec in executor.receipts():
                            journal(dict(event='engineering_placement_native_receipt',receipt=rec.__dict__,model_decision=False))
                            if rec.status not in ('started','succeeded'):raise RuntimeError('Native placement boundary failed:'+rec.status)
                        if verified_terminal():break
                    command=executor.next_command() if executor is not None else capture.command();issued=command.array().copy()
                    q=p.data.qpos[p.qids].copy();dq=p.data.qvel[p.dids].copy();before=float(p.data.time)
                    try:runtime.step(command)
                    finally:
                        if float(p.data.time)>before:
                            if abs(float(p.data.time)-before-.005)>1e-7:raise RuntimeError('Original 5ms clock violated')
                            tick+=1;delayed=np.stack([p.queue[-1-int(lag)][:,i] for i,lag in enumerate(p.delays)],axis=1)
                            writer.append_command(issued=issued,delayed=delayed,torque=p.torque,raw_torque=p.raw_torque,q_before=q,dq_before=dq,physical_tick=tick,time_s=float(p.data.time))
                    if executor is None:
                        capture.after_step()
                        if capture.complete:
                            witness=ActualCaptureWitness(capture);witness.validate(runtime);report.update(cold_capture_verified=True,capture_at_handoff=capture.report())
                            option,batch,backend=prepare_selected();host,executor=new_host(backend,witness);host.bind_batch(batch)
                            rec=executor.start(option,batch.decision_id,float(p.data.time));session=executor.session;push_started_tick=tick
                            report['binding']=binding_record;journal(dict(event='engineering_placement_native_receipt',receipt=rec.__dict__,model_decision=False))
                    else:
                        executor.record_issued(issued,tick,float(p.data.time),'actual-commands:physical_tick='+str(tick))
                        for rec in executor.receipts():journal(dict(event='engineering_placement_native_receipt',receipt=rec.__dict__,model_decision=False))
                        if verified_terminal():break
                report['asset_verification_after']=verify_bundle(bundle)
    except Exception as error:
        report.update(outcome='failed_no_retry',chain_verified=False,error=type(error).__name__+': '+str(error))
        if executor is not None:
            for rec in executor.receipts():journal(dict(event='engineering_placement_native_receipt',receipt=rec.__dict__,model_decision=False))
        if chain_started and nav_session is not None:
            report['guarded_NAV_failure_snapshot']=nav_session.machine.native_nav.report()
        if session is not None and hasattr(session.machine,'placement_receipt'):
            try:report['final_placement']=session.machine.placement_receipt()
            except Exception as diagnostic:report['placement_diagnostic_error']=str(diagnostic)
        if runtime is not None:
            try:
                from mujoco_zyh.failure_capsules import emit
                view=session.machine.native.r.sim if session is not None and hasattr(session.machine,'native') else None
                emit(runtime,'placement_probe_failure',view=view,
                    extra=dict(error=str(error),placement=report.get('final_placement')),preserve_primary_failure=True)
            except Exception as diagnostic:report['capsule_error']=type(diagnostic).__name__
    finally:
        cleanup=[]
        for name,action in (('review',lambda:review.close() if review else None),
            ('episode',lambda:writer.close(outcome=report.get('outcome','failed'),terminal_time_s=float(runtime.sim.data.time),censored=not report['placement_and_stow_verified']) if writer else None),
            ('capsules',lambda:runtime.wm_private_capsules.close() if runtime is not None and getattr(runtime,'wm_private_capsules',None) is not None else None),
            ('observer',lambda:observer.close() if observer else None)):
            try:
                value=action()
                if value is not None:report[name+'_closure']=value
            except Exception as error:cleanup.append(name+':'+str(error))
        if session is not None and not chain_started:
            try:
                report['native_results']=session.machine.results
                if hasattr(session.machine,'native'):
                    settled=session.machine.native.r.sim.settled
                    if hasattr(settled,'report'):report['selected_native_completion_clock']=settled.report()
                    if getattr(session.machine,'brake',None) is not None:report['actual_two_phase_brake']=session.machine.brake.report()
            except Exception as error:cleanup.append('native results:'+str(error))
        if session is not None and getattr(getattr(session.machine,'services',None),'unload_binding',None) is not None:
            try:report['private_reconciled_unload_trace']=session.machine.services.unload_binding.close(root)
            except Exception as error:cleanup.append('reference FF trace:'+str(error))
        if session is not None and getattr(getattr(session.machine,'services',None),'leg_release',None) is not None:
            try:report['native_reverse_leg_release']=session.machine.services.leg_release.receipt()
            except Exception as error:cleanup.append('leg release receipt:'+str(error))
        if stop_trace is not None:
            try:report['private_stop_actor_trace']=stop_trace.close()
            except Exception as error:cleanup.append('stop trace:'+str(error))
        if cleanup:report.update(cleanup_errors=cleanup,placement_and_stow_verified=False)
        report.update(main_motor_steps=tick,main_sim_seconds=float(runtime.sim.data.time) if runtime else 0.,caller_outcome=report.get('outcome'),wall_seconds=time.monotonic()-started)
        journal.close();save(root/'report.json',report)
    print(json.dumps(report,ensure_ascii=False));return 0 if report.get('outcome')=='zero_step_placement_binding_verified' or report['chain_verified'] else 2

if __name__=='__main__':raise SystemExit(main())
