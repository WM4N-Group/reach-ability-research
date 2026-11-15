"""No-step native model/camera preflight under the same renderer resource locks."""
import argparse
import fcntl
import importlib.metadata
import hashlib
import json
import tempfile
from pathlib import Path
import numpy as np
from .collect import validate_protocol
from .runtime_adapter import construct_runtime
from .observer import OnboardObserver
from .streams import write_json


def run(bundle,protocol,resource_dir):
    original=validate_protocol(protocol)
    if (original.get('recovery_exit_diagnostic_case') or original.get('push_protection_mode') or original.get('supported_push_mode')) and Path(resource_dir).resolve()!=Path(original['resource_lock_dir']).resolve():
        raise ValueError('Diagnostic zero-step preflight requires canonical shared locks')
    p=dict(original,scenario='nav-nav',auxiliary_calibration_worlds_allowed=0,auxiliary_calibration_max_sim_seconds=0)
    p.pop('nav_efficiency_mode',None)
    handles=[];observer=None
    try:
        for name in ('native-observer-physics-gpu1.lock','native-observer-sdk-gpu1.lock'):
            f=(Path(resource_dir)/name).open('a+');handles.append(f);fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
        r,m,construction=construct_runtime(bundle,p)
        nav_adaptation_probe=None
        if original.get('nav_efficiency_mode'):
            from .nav_efficiency import install
            from plans import plan
            tasks=install(r,plan(original['scenario']),original)
            nav=r.make_nav(tasks[2]);velocity=nav.update(r.nav_state(0.))
            command=r.nav_command()
            if not np.all(velocity==0.) or command.kd[16]!=2.5 or float(r.sim.data.time)!=0.:
                raise ValueError('Candidate NAV zero-step interface/initial warmup differs')
            nav_adaptation_probe=dict(passed=True,receipt=r.wm_nav_efficiency,native_physics_steps=0)
        observer=OnboardObserver(r,p)
        before=observer.snapshot();packet,catalog=observer.capture(0,np.zeros(18));after=observer.snapshot()
        if not observer.unchanged(before,after) or float(r.sim.data.time)!=0. or r.step_count!=0:
            raise ValueError('Read-only preflight changed/stepped native physics')
        if original.get('schema')=='piper-mujoco-composite-shadow-case-v1':
            if (catalog.get('model_input_allowed') is not False or
                    len(catalog.get('root_position_world_m',[]))!=3 or
                    np.asarray(catalog.get('R_world_from_body',[])).shape!=(3,3) or
                    len(catalog.get('objects',[]))!=1 or
                    catalog['objects'][0]['opaque_object_id']!='upstream_demo'):
                raise ValueError('Fresh composite label catalog source incomplete or misbound')
        review_probe=None
        if original.get('full_state_review',False):
            from .review_capture import WorldStateRecorder,state_records,load_display_model
            import mujoco
            with tempfile.TemporaryDirectory(prefix='mujoco-review-zero-step-') as temp:
                recorder=WorldStateRecorder(Path(temp)/'state',r,p)
                actual_before=recorder.actual_state().copy();recorder.capture(0);closure=recorder.close()
                records=list(state_records(Path(temp)/'state'))
                model=load_display_model(Path(temp)/'state');display=mujoco.MjData(model)
                mujoco.mj_setState(model,display,records[0][2],mujoco.mjtState.mjSTATE_INTEGRATION)
                mujoco.mj_forward(model,display)
                if not np.array_equal(actual_before,recorder.actual_state()) or display.time!=0.:
                    raise ValueError('Private-state preflight mutated main world or time')
                review_probe=dict(passed=True,actual_state_recorded=True,roundtrip_geometry_pass=True,
                    dynamic_state_bytes=closure['bytes'],shared_static_model_gzip_bytes=closure['shared_static_model_bytes'],state_size=recorder.size,native_physics_steps=0,
                    live_world_unchanged=True,recording_added_not_recovery_or_research_scene=True)
        stall_probe=None
        if original.get('stall_stow_mode'):
            from .stall_stow import INITIAL_ARM,NATIVE_COMPACT_ARM,STOW_ARM,dependency_hashes
            finish=r.push['finish'];guard=finish.CollisionGuard(r.sim,finish.FinishConfig())
            reasons={name:guard.check(q,record=True) for name,q in [('entry',INITIAL_ARM),('initial',NATIVE_COMPACT_ARM),('stowed_inner',STOW_ARM)]}
            if any(reasons.values()):raise ValueError('Initial/stowed actual-model FK refused: '+str(reasons))
            native_soft=r.sim.robot.data.soft_joint_pos_limits.numpy()[0][
                [r.sim.robot.joint_names.index('joint'+str(i)) for i in range(1,7)]]
            physical=r.sim.model.jnt_range[r.sim.jids[12:]]
            inner=np.column_stack((np.maximum(native_soft[:,0],physical[:,0])+.01,np.minimum(native_soft[:,1],physical[:,1])-.01))
            if not np.all((STOW_ARM>inner[:,0]) & (STOW_ARM<inner[:,1])):
                raise ValueError('Final stow reference is unreachable inside frozen soft-limit+margin domain')
            stall_probe=dict(passed=True,final_reference_strictly_inside_frozen_inner_domain=True,inner_reference_limits=inner.tolist(),zero_physics_steps=True,geometry=reasons,dependencies_sha256=dependency_hashes(),
                initial_arm=NATIVE_COMPACT_ARM.tolist(),entry_arm=INITIAL_ARM.tolist(),actual_initial_base=r.sim.data.qpos[:3].tolist(),stow_arm=STOW_ARM.tolist(),minimum_body_clearance_m=guard.minimum_surface,minimum_other_clearance_m=guard.minimum)
        resume_probe=None
        if original.get('resume_nav_mode'):
            from .resume_nav import compact_contract,nominal_compact_ee,make_compact_nav,NAV_ARM
            contract=compact_contract(r);ee=nominal_compact_ee(r);nav=make_compact_nav(r,[0.,-.35])
            transfer=guard.segment(STOW_ARM,NAV_ARM)
            if transfer:raise ValueError('Compact NAV transfer FK path refused: '+transfer)
            resume_probe=dict(passed=True,contract=contract,nominal_compact_ee=ee.tolist(),original_native_thresholds=vars(nav.config),native_physics_steps=0)
        target_probe=None
        if original.get('reselect_B_mode'):
            from mujoco_selected_target_context import make_target_context,contact_routing_fixture
            from .reselect_B import compile_entry_and_machine,dependency_hashes
            Machine,hook=compile_entry_and_machine(bundle)
            targets=[]
            for candidate in ('middle','heavy'):
                size=None
                if original.get('integrated_course_mode'):
                    c=original['integrated_case'];size=(c['step_length_m'],c['step_width_m'],.2) if candidate=='middle' else (c['bridge_length_m'],c['bridge_width_m'],.2)
                view,binding=make_target_context(r,r.wm_candidate_contacts,candidate,cfg_overrides=dict(box_size=size) if size else None)
                with r.push.active():
                    observation=view.observation();flags=view.termination()
                if observation.shape!=(226,):raise ValueError('Selected target observation schema differs')
                binding['contact_routing_fixture']=contact_routing_fixture(r,view)
                targets.append(binding)
            if len(catalog['objects'])!=3 or {x['opaque_object_id'] for x in catalog['objects']}!={'light','middle','heavy'}:raise ValueError('Fresh research RGBD/catalog identity mismatch')
            target_probe=dict(passed=True,targets=targets,caller_source_hook=hook,dependencies_sha256=dependency_hashes(),native_physics_steps=0,live_B_dispatch_or_three_real_ticks_validated=False)
        suite_probe=None
        if original.get('schema')=='piper-mujoco-five-easy-scenes-case-v1':
            case=original['suite_case']
            suite_probe=dict(case_id=case['case_id'],family=case['family'],native_physics_steps=0,
                             geometry=dict(r.wm_suite_construction),real_gap_checked=False)
            if case['family']=='side_platform' and original.get('suite_revision',1)>=2:
                if abs(case['push_lane_y_m'])-.6<=case['platform_width_m']/2+.05:
                    raise ValueError('Side box overlaps or nearly touches the climb platform')
            if case['family']=='bridge':
                near=case['gap_near_x_m'];far=near+case['gap_width_m']
                h=r.staircase.height_at(r.sim,np.array([(near+far)/2,far+.1]),np.array([0.,0.]))
                if not np.allclose(h,[-.6,0.],atol=1e-8):raise ValueError('Real bridge opening absent at initial state')
                initial_end=float(r.sim.data.xpos[r.sim.box_id,0])+case['box_length_m']/2
                if initial_end>=near:raise ValueError('Initial box already bridges the opening')
                suite_probe.update(real_gap_checked=True,gap_floor_and_far_bank_height_m=h.tolist(),
                                   initial_box_end_m=initial_end)
        integrated_probe=None
        if original.get('integrated_course_mode'):
            from .integrated_course import layout,frame_classes
            from .scene import IDENTITY
            case=original['integrated_case'];g=layout(case);lane=case['lane_y_m']
            x=np.array([g['near_edge']-.03,(g['near_edge']+g['far_front'])/2,g['far_front']+.05,g['far_deck_front']+.1])
            heights=r.staircase.height_at(r.sim,x,np.full(4,lane))
            if not np.allclose(heights,[.4,0.,.4,.6],atol=1e-7):raise ValueError('Integrated gap/high-bank geometry is not real')
            Frame,Stop,receipt=frame_classes(r,lane)
            model=r.sim.model
            foot_ids={model.body(n+'_foot').id for n in ('FR','FL','RR','RL')}
            foot_geoms={i for i in range(model.ngeom) if int(model.geom_bodyid[i]) in foot_ids}
            foot_materials={}
            for candidate in ('middle','heavy'):
                gid=model.geom(IDENTITY[candidate]['body']+'_geom').id
                values=[float(model.pair_friction[i,0]) for i,(a,b) in enumerate(zip(model.pair_geom1,model.pair_geom2)) if (int(a)==gid and int(b) in foot_geoms) or (int(b)==gid and int(a) in foot_geoms)]
                if len(values)<4 or not np.allclose(values,.8):raise ValueError('Registered box-top foot friction not applied to compiled pairs')
                foot_materials[candidate]=values
            integrated_probe=dict(passed=True,case_id=case['case_id'],task_lane_y_m=lane,frame_hooks=receipt,
                real_gap_profile_m=heights.tolist(),actual_foot_pair_friction=foot_materials,physics_steps=0,full_continuous_task_pass_claimed=False)
        from visual_shadow_model import validate_visual_input
        validate_visual_input(packet)
        capsule_probe=None
        if (original.get('recovery_exit_diagnostic_case') or original.get('push_protection_mode') or original.get('supported_push_mode') or original.get('schema')=='piper-mujoco-A-recovery-selected-B-recorded-protocol-v2' or original.get('integrated_course_mode')):
            from .failure_capsules import install
            # Initialize REAL native heterogeneous histories BEFORE testing the
            # reader. No actor/physics; the reader itself never calls observation.
            native_obs=r.sim.observation()
            if native_obs.shape!=(226,):raise ValueError('Actual native cached-history schema mismatch')
            with tempfile.TemporaryDirectory(prefix='exit-capsule-zero-step-') as temp:
                recorder=install(r,temp,original['private_failure_capsules'])
                recorder.capture('diagnostic_zero_step_preflight',extra=dict(actual_failure_claimed=False))
                if original.get('schema')=='piper-mujoco-A-recovery-selected-B-recorded-protocol-v2' or original.get('integrated_course_mode'):
                    from mujoco_selected_target_context import make_target_context
                    size=None
                    if original.get('integrated_course_mode'):
                        c=original['integrated_case'];size=(c['step_length_m'],c['step_width_m'],.2)
                    selected_B,_=make_target_context(r,r.wm_candidate_contacts,'middle',cfg_overrides=dict(box_size=size) if size else None)
                    selected_B.refresh()
                    row=recorder.capture('diagnostic_zero_step_selected_b',view=selected_B,
                                         extra=dict(actual_failure_claimed=False))
                    if row['selected_box_body_id']!=selected_B.box_id:
                        raise ValueError('B zero-step capsule selected wrong body')
                capsule_probe=recorder.close()
                capsule_probe['actual_nonempty_native_history_shapes']=[list(v.shape) for v in r.sim.history]
                if not capsule_probe['all_required_captures_complete']:raise ValueError('Diagnostic reader preflight incomplete')
        supported_probe=None
        if original.get('supported_push_mode'):
            native_cfg=r.sim.controller.env.cfg
            if (r.sim.controller.env.cfg is not r.sim.cfg or
                    native_cfg.push_approach_distance!=original['original_native_push_approach_distance_m'] or
                    native_cfg.push_hand_height_offset!=original['original_hand_height_offset_m']):
                raise ValueError('Preflight must begin from actual unchanged native PUSH binding/config')
            if (original['protected_push_approach_distance_m']>=original['original_native_push_approach_distance_m'] or
                    original['protected_hand_height_offset_m']>=original['original_hand_height_offset_m']):
                raise ValueError('Prospective protected config must be separately registered before controller install')
            from .resume_nav import NAV_ARM
            reason=guard.segment(r.sim.data.qpos[r.sim.qids[12:]],NAV_ARM)
            if reason:raise ValueError('Source-matched real-entry compact path geometry:'+reason)
            supported_probe=dict(preflight_actual_outer_push_approach_distance_m=r.sim.cfg.push_approach_distance,
                preflight_actual_native_push_approach_distance_m=native_cfg.push_approach_distance,preflight_actual_native_push_hand_height_offset_m=native_cfg.push_hand_height_offset,
                controller_env_config_is_native_bound_push_config=True,prospective_protected_push_approach_distance_m=original['protected_push_approach_distance_m'],
                prospective_protected_hand_height_offset_m=original['protected_hand_height_offset_m'],configuration_applied_later_by_frozen_collector_router_before_task_first_step=True,compact_entry_provenance=r.wm_compact_entry_provenance,
                actual_initial_to_compact_geometry_pass=True,compact_target=NAV_ARM.tolist(),
                actual_q_not_changed_by_geometry_check=True,actor_forwards=0,physics_steps=0,
                original_leg_motor_executor_unchanged=False,protected_NN_proposals_require_QP_support=True)
        valid=np.isfinite(packet['depth_m'].numpy())
        if not valid.any():raise ValueError('No real calibrated metric depth in actual renderer')
        return dict(schema='zyh-mujoco-zero-step-render-preflight-v1',passed=True,
            native_physics_steps=0,actual_world_time_s=float(r.sim.data.time),source=construction,
            implementation_sha256={path.name:hashlib.sha256(path.read_bytes()).hexdigest()
                for path in Path(__file__).parent.iterdir() if path.suffix in ('.py','.json')},
            visual_validator_sha256=hashlib.sha256(Path(__file__).parents[1].joinpath('visual_shadow_model.py').read_bytes()).hexdigest(),
            validated_protocol=original,integrated_probe=integrated_probe,engineering_suite_probe=suite_probe,supported_push_probe=supported_probe,private_failure_capsule_probe=capsule_probe,selected_B_probe=target_probe,resume_NAV_probe=resume_probe,stall_stow_probe=stall_probe,nav_adaptation_probe=nav_adaptation_probe,full_scene_state_probe=review_probe,actual_RGB_shape=list(packet['rgb'].shape),actual_metric_depth_valid_fraction=float(valid.mean()),
            render_does_not_change_state_or_motor_queue=True,synthetic_RGBD=False,
            environment_versions={n:importlib.metadata.version(n) for n in ('mujoco','numpy','scipy','osqp','torch')},
            live_episode_or_skill_success_certified=False,auxiliary_calibration_worlds=0)
    finally:
        if observer is not None:observer.close()
        for f in reversed(handles):f.close()


def main():
    a=argparse.ArgumentParser(description=__doc__)
    for name in ('bundle','protocol','resource-dir','output'):a.add_argument('--'+name,type=Path,required=True)
    p=a.parse_args();r=run(p.bundle,json.loads(p.protocol.read_text()),p.resource_dir);write_json(p.output,r);print(json.dumps(r))


if __name__=='__main__':main()
