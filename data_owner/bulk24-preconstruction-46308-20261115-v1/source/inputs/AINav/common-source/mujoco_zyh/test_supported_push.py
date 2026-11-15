"""Source/kinematic CPU checks, not real recovery success claims."""
import json,os,unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
import numpy as np
from mujoco_zyh.supported_push import zero_base_com_goal,fixed_base_com_goal,alignment_waypoints,hand_center_base_velocity,precontact_support_admission,supported_base_height_floor,rebalance_completion,lateral_reload_completion,lateral_reload_target_issued,protected_line_reference_step,projection_goal,SupportedPushRouter
from mujoco_zyh.supported_recovery_protocol import CASES,protocol
from mujoco_zyh.collect import validate_protocol
from mujoco_zyh.push_protection import protected_position_reference_step


class SourceContract(unittest.TestCase):
    def test_exact_source_pinned_compact_entry_adapter_reused(self):
        from mujoco_zyh.runtime_adapter import construct_runtime
        p=protocol();p.update(scenario='nav-nav',auxiliary_calibration_worlds_allowed=0,auxiliary_calibration_max_sim_seconds=0)
        r,m,receipt=construct_runtime(os.environ['ZYH_BUNDLE'],p)
        self.assertTrue(r.wm_compact_entry_provenance['inverse_restores_exact_original'])
        self.assertEqual(r.step_count,0);self.assertEqual(r.sim.data.time,0.)
        self.assertEqual(r.wm_compact_entry_provenance['compact_arm_target'],[0.,.3,-.3,0.,0.,0.])
    def test_original_initialization_not_failed_state_transplant(self):
        p=protocol();self.assertEqual(p['reset_after_initial_allowed'],0);self.assertFalse(p['automatic_retry'])
        self.assertFalse(p['original_motor_executor_unchanged']);self.assertEqual(p['training_runs'],0)
    def test_only_known_TRAIN_development_conditions_no_test_tuning(self):
        plan=json.loads(Path(__file__).with_name('option_forecast_study_v2_plan.json').read_text())
        for name in CASES:
            p=protocol(name);validate_protocol(p)
            old=next(x for x in plan['cases'] if x['case_id']==name.replace('train','train-'))
            self.assertEqual(old['role'],'train');self.assertEqual(p['role'],'development')
            self.assertEqual(p['seed'],old['seed']);self.assertEqual(p['probe_physics']['mass_kg'],old['mass_kg_executor_private'])
            self.assertEqual(p['probe_physics']['friction'],old['friction_executor_private'])
    def test_cannot_change_seed_budget_or_train_flag(self):
        for key,value in [('seed',33),('training_allowed',True),('max_sim_seconds',101),('WM_control',True),('reset_after_initial_allowed',1)]:
            p=protocol();p[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):validate_protocol(p)
    def test_all_old_hard_capture_stow_gates_retained(self):
        old=json.loads(Path(__file__).with_name('soft_stall_stow_protocol_v7.json').read_text())
        for name in CASES:self.assertEqual(protocol(name)['recovery_limits'],old['recovery_limits'])


class NativeCOMTask(unittest.TestCase):
    def test_lateral_reload_requires_real_shift_brake_and_load(self):
        start=np.array([-.0675,-.0456,.1851]);target=start+np.array([0.,.07,0.])
        observed=lateral_reload_completion(start,target,target,np.eye(3),
            np.zeros(3),[85.,55.,50.,24.],.002)
        self.assertTrue(observed['allow_arm_recenter'])
        self.assertAlmostEqual(observed['measured_lateral_reload_m'],.07)
        for actual,velocity,loads,foot_speed in (
                (start+.055*np.array([0.,1.,0.]),np.zeros(3),[85.,55.,50.,24.],.002),
                (target,np.array([0.,.016,0.]),[85.,55.,50.,24.],.002),
                (target,np.zeros(3),[85.,55.,50.,17.9],.002),
                (target,np.zeros(3),[85.,55.,50.,24.],.031)):
            self.assertFalse(lateral_reload_completion(start,actual,target,np.eye(3),
                velocity,loads,foot_speed)['allow_arm_recenter'])
    def test_lateral_issued_target_ignores_independent_height_floor(self):
        target=np.array([-.06831191865692941,.043323066401300916,.1854804881688646])
        issued=np.array([-.0683119186569293,.04332306640130086,.1871231758407704])
        self.assertTrue(lateral_reload_target_issued(issued,target))
        self.assertFalse(lateral_reload_target_issued(issued+np.array([0.,.0011,0.]),target))
        self.assertFalse(lateral_reload_completion(
            np.array([-.06411443820336829,-.02655097139416339,.1854804881688646]),
            issued+np.array([0.,0.,.02]),target,np.eye(3),np.zeros(3),
            [70.,66.,39.,36.],.001)['allow_arm_recenter'])
    def test_v20_measured_rebalance_releases_after_real_retreat_and_braking(self):
        start=np.array([-.01599188456,-.00777925785,.18547310606])
        actual=np.array([-.06856522823,-.02755704407,.18588775135])
        target=np.array([-.06580209151,-.01077146177,.18599929796])
        R=np.array([[.9982,-.0600,0.],[.0600,.9982,0.],[0.,0.,1.]])
        loads=np.array([87.925,49.497,57.159,18.934])
        observed=rebalance_completion(start,actual,R,target,target,
            np.array([-1.11e-5,-1.18e-5,6.45e-7]),loads)
        self.assertTrue(observed['allow_arm_contact'])
        self.assertGreater(observed['measured_retreat_m'],.05)
        self.assertLess(observed['lateral_drift_m'],.025)
        self.assertFalse(rebalance_completion(start,actual+np.array([0.,-.012,0.]),R,
            target,target,np.zeros(3),loads)['allow_arm_contact'])
        self.assertFalse(rebalance_completion(start,actual,R,target,target,
            np.zeros(3),[87.,49.,57.,11.])['allow_arm_contact'])
        self.assertFalse(rebalance_completion(start,actual,R,start,target,
            np.zeros(3),loads)['allow_arm_contact'])
    def test_fixed_base_position_feedback_cancels_com_shape_velocity(self):
        com=np.array([.1,.2,.4]);base=np.array([.02,-.03,.3]);velocity=np.array([.01,-.02,.005])
        cv=velocity+np.array([.04,.05,-.01]);target=base+np.array([-.08,-.09,-.04])
        result=fixed_base_com_goal(com,cv,base,velocity,target,20.,8.)
        self.assertTrue(np.allclose(20.*(result-com)-8.*cv,20.*(target-base)-8.*velocity))
        self.assertTrue(np.array_equal(base,np.array([.02,-.03,.3])))
    def test_source_diagnosed_retreat_then_align_is_bounded(self):
        path=alignment_waypoints(np.array([.05,.0,.31]),np.eye(3),np.array([-.61173,.08633,.01772]))
        self.assertTrue(np.allclose(path[1]-path[0],[-.08827,0.,0.]))
        self.assertTrue(np.allclose(path[2]-path[1],[0.,-.08633,-.04772]))
        self.assertLess(np.linalg.norm(path[2]-path[0]),.18)
    def test_already_behind_face_never_moves_forward_while_offcenter(self):
        path=alignment_waypoints(np.array([-.08,.06,.25]),np.eye(3),np.array([-.754,.10,.037]))
        self.assertTrue(np.array_equal(path[0],path[1]))
        self.assertAlmostEqual(path[2,0],path[0,0])
        self.assertLess(path[2,1],path[0,1]);self.assertLess(path[2,2],path[0,2])
    def test_hand_center_feedback_corrects_lateral_and_height_without_forward_motion(self):
        for y,z in ((-.052,-.029),(.086,.018)):
            v=hand_center_base_velocity(np.array([-.75,y,z]),np.eye(3))
            self.assertEqual(v[0],0.)
            self.assertLessEqual(np.linalg.norm(v),.020000001)
            self.assertLess(y*v[1],0.)
            self.assertLess((z+.03)*v[2],0.)
        biased=hand_center_base_velocity(np.array([-.71,0.,-.02]),np.eye(3),.03)
        self.assertGreater(biased[1],0.)
        self.assertLessEqual(np.linalg.norm(biased),.020000001)
        with self.assertRaises(ValueError):hand_center_base_velocity(np.array([-.71,0.,-.02]),np.eye(3),.04)
    def test_partial_support_permits_only_correction_never_forward(self):
        self.assertEqual(precontact_support_admission([98.,30.,76.,7.3],.001),
                         dict(corrective_centering=True,forward_approach=False))
        self.assertEqual(precontact_support_admission([98.,30.,76.,3.9],.001),
                         dict(corrective_centering=False,forward_approach=False))
        self.assertEqual(precontact_support_admission([98.,30.,76.,12.2],.001),
                         dict(corrective_centering=True,forward_approach=True))
    def test_original_low_posture_threshold_keeps_target_margin(self):
        heights=[.01771799,.02124402,.01897879,.02242054]
        floor=supported_base_height_floor(heights,[96.,32.,74.,8.3])
        self.assertAlmostEqual(floor,.18521799)
        self.assertGreater(floor-min(np.array(heights)-.0225),.18)
    def test_alignment_rejects_start_behind_front_or_excess_translation(self):
        with self.assertRaises(ValueError):alignment_waypoints(np.zeros(3),np.eye(3),[-.5,0.,-.03])
        with self.assertRaises(ValueError):alignment_waypoints(np.zeros(3),np.eye(3),[-.61,.2,.2])
    def test_native_task_zeroes_ACTUAL_baseXY_not_just_arm_velocity(self):
        for internal in (-.2,0.,.3):
            for base in (-.05,.01,.05):
                com=np.array([.2,.1,.3]);bv=np.array([base,-base,0.]);cv=bv+[internal,-internal,.02]
                target=zero_base_com_goal(com,cv,bv,20.,8.)
                accel=20.*(target-com)-8.*cv
                self.assertTrue(np.allclose(accel[:2],-8.*bv[:2]));self.assertEqual(target[2],com[2])
    def test_invalid_kinematics_or_gains_refused(self):
        with self.assertRaises(ValueError):zero_base_com_goal([0.,0.,np.nan],np.zeros(3),np.zeros(3),20.,8.)
        with self.assertRaises(ValueError):zero_base_com_goal(np.zeros(3),np.zeros(3),np.zeros(3),0.,8.)
    def test_reference_only_does_not_mutate_measuredCOM(self):
        com=np.array([0.,0.,.3]);before=com.copy();zero_base_com_goal(com,np.ones(3),np.zeros(3),20.,8.)
        self.assertTrue(np.array_equal(com,before))


class ArmProtectedFromFirstCommand(unittest.TestCase):
    def test_v23_arm_line_uses_stricter_speed_without_relaxing_effort(self):
        start=np.zeros(6);goal=np.array([.2,-.1,.2,0.,0.,0.])
        inner=np.tile([-.5,.5],(6,1));reference=start.copy();velocity=np.zeros(6);progress=0.
        for _ in range(300):
            result=protected_line_reference_step(start=start,goal=goal,progress=progress,
                reference=reference,reference_velocity=velocity,q=reference,dq=np.zeros(6),
                kp=np.ones(6)*50,kd=np.ones(6)*3,feedforward=np.zeros(6),
                effort=np.ones(6)*20,inner_limits=inner,speed_cap=.25)
            self.assertLessEqual(np.max(np.abs(result['reference_velocity'])),.25+1e-8)
            self.assertLessEqual(np.max(np.abs((result['reference_velocity']-velocity)/.005)),1.+1e-8)
            self.assertTrue(np.allclose(result['reference'],start+result['path_progress']*(goal-start)))
            reference=result['reference'];velocity=result['reference_velocity'];progress=result['path_progress']
        self.assertGreater(progress,.99)
    def test_coupled_reference_stays_on_admitted_line_through_full_move(self):
        start=np.array([.314,2.565,-1.270,1.434,-.411,-1.150])
        goal=np.array([.022,2.889,-2.052,.164,.244,-.185])
        inner=np.column_stack((np.minimum(start,goal)-.2,np.maximum(start,goal)+.2))
        reference=start.copy();velocity=np.zeros(6);progress=0.
        reached=None
        for step in range(1400):
            result=protected_line_reference_step(start=start,goal=goal,progress=progress,
                reference=reference,reference_velocity=velocity,q=reference,dq=np.zeros(6),
                kp=np.array([50.,50.,80.,30.,30.,20.]),kd=np.array([3.,2.,3.,3.,2.5,1.]),
                feedforward=np.zeros(6),effort=np.array([20.,20.,15.,7.,5.,5.]),
                inner_limits=inner)
            self.assertLessEqual(np.max(np.abs(result['reference_velocity'])),.45+1e-8)
            self.assertLessEqual(np.max(np.abs((result['reference_velocity']-velocity)/.005)),1.+1e-8)
            self.assertTrue(np.allclose(result['reference'],
                start+result['path_progress']*(goal-start),atol=1e-10))
            reference=result['reference'];velocity=result['reference_velocity'];progress=result['path_progress']
            if progress>=1.-1e-9 and reached is None:reached=step
            if reached is not None and step-reached>=50:break
        self.assertGreater(progress,.999)
        self.assertIsNotNone(reached)
    def test_first_native_waypoint_still_reachable_with_original_tolerance(self):
        inner=np.array([[-2.,2.],[.167,2.973],[-2.808,-.15835],[-1.56,1.56],[-1.08,1.08],[-1.87,1.87]])
        native=np.array([0.,.15699999,-.14834999,0.,0.,0.]);goal=projection_goal(native,inner)
        self.assertTrue((abs(goal-native)<.04).all())
        self.assertTrue((goal>inner[:,0]).all());self.assertTrue((goal<inner[:,1]).all())
    def test_compact_entry_original_PDFF_rate_projection_feasible(self):
        r=np.array([0.,.3,-.3,0.,0.,0.]);inner=np.tile([-1.,1.],(6,1));inner[1]=[.167,2.973];inner[2]=[-2.808,-.15835]
        x=protected_position_reference_step(desired=projection_goal(np.zeros(6),inner),reference=r,reference_velocity=np.zeros(6),q=r,dq=np.zeros(6),kp=np.array([50.,50.,80.,30.,30.,20.]),kd=np.array([3.,2.,3.,3.,2.5,1.]),feedforward=np.array([0.,-.5,-5.,0.,-1.,0.]),effort=np.array([20.,20.,15.,7.,5.,5.]),inner_limits=inner)
        self.assertLessEqual(abs(x['reference_velocity']).max(),.45)
    def test_actual_previous_action_uses_actual_lastissued_NOT_rejected_proposal(self):
        import torch
        r=NS(last=NS(position=np.ones(18)*.25),push={'model':NS(REFERENCE=np.zeros(18))},sim=NS(applied_commands=np.zeros(18)))
        router=SupportedPushRouter.__new__(SupportedPushRouter);router.r=r;router.recovery=None;router.native=NS(kind='push',phase='run')
        with patch('mujoco_zyh.stall_stow.StallStowRouter.update'):router.update()
        self.assertTrue(np.array_equal(r.sim.applied_commands,np.ones(18)))
    def test_after_retirement_no_actor_history_rewrite(self):
        r=NS(sim=NS(applied_commands=np.zeros(18)))
        router=SupportedPushRouter.__new__(SupportedPushRouter);router.r=r;router.recovery=NS()
        with patch('mujoco_zyh.stall_stow.StallStowRouter.update'):router.update()
        self.assertTrue((r.sim.applied_commands==0).all())


class ActualFFBumplessHandoff(unittest.TestCase):
    def test_actual_existing_gravityFF_is_not_dropped_to_zero(self):
        from mujoco_zyh.stall_stow import unload_reference
        q=np.ones(6)*.3;g=np.ones(6)*-5.;args=dict(goal=q.copy(),start=q.copy(),reference=q.copy(),velocity=np.zeros(6),q=q.copy(),dq=np.zeros(6),
            kp=np.ones(6)*50,kd=np.ones(6)*3,gravity=g.copy(),effort=np.ones(6)*20,limits=np.tile([-.9,.9],(6,1)),age=0.,start_ff=g.copy())
        r,v,ff,_=unload_reference(**args);self.assertTrue(np.array_equal(ff,g));self.assertTrue(np.array_equal(r,q))
    def test_initialFF_tracks_small_gravity_change_without_jump(self):
        from mujoco_zyh.stall_stow import unload_reference
        q=np.ones(6)*.3;old=np.ones(6)*-5.
        r,v,ff,_=unload_reference(q,q,q,np.zeros(6),q,np.zeros(6),np.ones(6)*50,np.ones(6)*3,old-.1,np.ones(6)*20,np.tile([-.9,.9],(6,1)),.005,start_ff=old)
        self.assertLess(abs(ff-old).max(),.001)
    def test_default_legacy_FF_path_unchanged(self):
        from mujoco_zyh.stall_stow import unload_reference
        q=np.ones(6)*.3;g=np.ones(6)*-5.
        _,_,legacy,_=unload_reference(q,q,q,np.zeros(6),q,np.zeros(6),np.ones(6)*50,np.ones(6)*3,g,np.ones(6)*20,np.tile([-.9,.9],(6,1)),0.)
        self.assertTrue((legacy==0.).all())
    def test_new_path_retains_original_rate_effort_bounds(self):
        from mujoco_zyh.stall_stow import unload_reference
        q=np.ones(6)*.3;r=q.copy();v=np.zeros(6);g=np.ones(6)*-5.
        for i in range(200):
            nr,nv,ff,_=unload_reference(q+.02,q,r,v,q,np.zeros(6),np.ones(6)*50,np.ones(6)*3,g,np.ones(6)*20,np.tile([-.9,.9],(6,1)),i*.005,start_ff=g)
            self.assertLessEqual(abs(nv).max(),.45);self.assertLessEqual(abs((nv-v)/.005).max(),1.+1e-8)
            self.assertTrue((abs(50*(nr-q)+ff)<=18+1e-9).all());r,v=nr,nv


class GravitySupportWarning(unittest.TestCase):
    def inputs(self):
        from mujoco_zyh.test_push_protection import inputs
        a=inputs();a['proposed'][4,13]=15.
        return a
    def test_default_old_warning_not_changed(self):
        from mujoco_zyh.push_protection import screen
        self.assertEqual(screen(**self.inputs())['action'],'BRAKE_RETIRE_PUSH')
    def test_explicit_new_warning_allows_normal_gravity_below_original90reserve(self):
        from mujoco_zyh.push_protection import screen
        x=screen(**self.inputs(),arm_warning_fraction=.85)
        self.assertEqual(x['action'],'PROPOSE_UNCHANGED');self.assertEqual(x['original_arm_prediction_effort_reserve_fraction'],.90)
    def test85still_retires_before_original90and98gates(self):
        from mujoco_zyh.push_protection import screen
        a=self.inputs();a['proposed'][4,13]=17.1
        self.assertEqual(screen(**a,arm_warning_fraction=.85)['action'],'BRAKE_RETIRE_PUSH')
    def test_cannot_tune_above_original_reserve(self):
        from mujoco_zyh.push_protection import screen
        for margin in (.90,.98,1.):
            with self.subTest(margin=margin),self.assertRaises(ValueError):screen(**self.inputs(),arm_warning_fraction=margin)


class NativeGravityPositionContract(unittest.TestCase):
    def test_source_native_IK_position_offset_and_newFF_not_double_applied(self):
        from mujoco_zyh.supported_push import uncompensated_native_arm_goal
        q=np.ones(6)*.3;g=np.array([.1,-14.,-6.,.3,-1.,0.]);K=np.array([50.,50.,80.,30.,30.,20.])
        original=q+g/K;goal=uncompensated_native_arm_goal(original,g,K)
        self.assertTrue(np.allclose(goal,q));self.assertTrue(np.allclose(K*(goal-q)+g,g))
        self.assertFalse(np.allclose(K*(original-q)+g,g))
    def test_actual_frozen_source_witness_contains_gravity_position_compensation(self):
        text=(Path(os.environ['ZYH_BUNDLE'])/'push/controller/box_push_ik.py').read_text()
        self.assertIn('compensated = self.reference + gravity[:, columns] / self.stiffness',text)
    def test_extraction_never_mutates_NN_proposal_or_gravity(self):
        from mujoco_zyh.supported_push import uncompensated_native_arm_goal
        q=np.ones(6);g=np.ones(6)*-1.;K=np.ones(6)*50;uncompensated_native_arm_goal(q,g,K)
        self.assertTrue((q==1).all());self.assertTrue((g==-1).all())
    def test_invalid_Kp_or_nonfinite_fields_rejected(self):
        from mujoco_zyh.supported_push import uncompensated_native_arm_goal
        with self.assertRaises(ValueError):uncompensated_native_arm_goal(np.zeros(6),np.zeros(6),np.zeros(6))


class ClippedNativeActionProvenance(unittest.TestCase):
    def test_gravity_inverse_after_native_action_clip_is_not_valid_rawtarget(self):
        from mujoco_zyh.supported_push import uncompensated_native_arm_goal
        reference=np.ones(6)*2.9;gravity=np.ones(6)*-10.;K=np.ones(6)*50.
        clipped=np.clip(reference+gravity/K,-2.5,2.5)
        self.assertFalse(np.allclose(uncompensated_native_arm_goal(clipped,gravity,K),reference))
    def test_supported_executor_reads_original_controller_reference_NOT_compensated_clip(self):
        import inspect
        text=inspect.getsource(SupportedPushRouter.next_command)
        self.assertIn('projection_goal(s.controller.reference.detach().cpu().numpy()[0],self.inner)',text)
        self.assertIn('self.arm_hold',text)
        self.assertNotIn('desired=projection_goal(uncompensated_native_arm_goal',text)


class BoundedQPApproach(unittest.TestCase):
    def test_measured_gap_velocity_cap_and_signed_braking(self):
        from mujoco_zyh.supported_push import approach_com_goal
        for gap in (.43,.485,.55):
            c,v=approach_com_goal(np.array([0.,0.,.3]),np.zeros(3),np.zeros(3),gap,20.,8.)
            self.assertLessEqual(abs(v).max(),.02);self.assertAlmostEqual(v[0],np.clip(2.*(gap-.485),-.02,.02))
    def test_actualbase_feedback_removes_FULL_shapevelocity(self):
        from mujoco_zyh.supported_push import approach_com_goal
        for internal in (-.2,0.,.2):
            com=np.array([0.,0.,.3]);bv=np.array([.015,-.01,0.]);cv=bv+[internal,internal,0.]
            target,v=approach_com_goal(com,cv,bv,.55,20.,8.)
            self.assertTrue(np.allclose((20*(target-com)-8*cv)[:2],8*(v-bv[:2])))
    def test_targetretreat_budget_is_not_claimed_actual_guarantee(self):
        self.assertLess(.645-.485,.18);self.assertEqual(protocol()['recovery_limits']['max_actual_retreat_m'],.18)


class RegisteredContactPreload(unittest.TestCase):
    def test_approach_reference_advances25mm_but_legal_force_threshold_stays_oneN(self):
        p=protocol();self.assertEqual(p['original_native_push_approach_distance_m'],.03)
        self.assertEqual(p['protected_push_approach_distance_m'],.005)
        self.assertAlmostEqual(p['original_native_push_approach_distance_m']-p['protected_push_approach_distance_m'],.025)
        self.assertEqual(p['original_native_contact_force_gate_N'],1.)
    def test_approach_and_hand_height_are_set_on_the_actual_bound_native_env(self):
        import inspect
        from mujoco_zyh.preflight import run
        router=inspect.getsource(SupportedPushRouter.__init__)
        self.assertIn('self.active_push_cfg=r.sim.controller.env.cfg',router)
        preflight=inspect.getsource(run)
        self.assertIn('r.sim.controller.env.cfg is not r.sim.cfg',preflight)
        self.assertIn('preflight_actual_native_push_hand_height_offset_m=native_cfg.push_hand_height_offset',preflight)
    def test_router_changes_software_approach_field_before_any_physics_without_goal_alias(self):
        import inspect
        text=inspect.getsource(SupportedPushRouter.__init__)
        self.assertIn('self.active_push_cfg=r.sim.controller.env.cfg',text)
        self.assertIn('self.active_push_cfg.push_approach_distance=.005',text)
        self.assertIn('self.active_push_cfg.push_hand_height_offset=-.03',text)
        self.assertIn('original_push_approach_distance',text)
    def test_registered_height_preload_centers_native_point_without_gate_change(self):
        p=protocol();self.assertEqual(p['original_hand_height_offset_m'],0.)
        self.assertEqual(p['protected_hand_height_offset_m'],-.03)
        self.assertEqual(p['original_native_contact_force_gate_N'],1.)
        with self.assertRaises(ValueError):
            q=protocol();q['protected_hand_height_offset_m']=-.08;validate_protocol(q)
    def test_protocol_rejects_contact_threshold_or_preload_tuning(self):
        for key,value in [('protected_push_approach_distance_m',.03),('original_native_contact_force_gate_N',.5)]:
            p=protocol();p[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):validate_protocol(p)


class BeforeContactStageCPU(unittest.TestCase):
    def test_measured_center_and_original_loaded_foot_speed_capture_base_reference(self):
        s=NS(data=NS(qpos=np.r_[[-.08,.06,.25],np.zeros(20)],qvel=np.zeros(30)),
             dids=np.arange(18),feet_ids=np.arange(4),forces=np.tile([0.,0.,20.],(4,1)),
             controller=NS(safe_approach_complete=[True]))
        router=SupportedPushRouter.__new__(SupportedPushRouter)
        router.r=NS(sim=s);router.support=NS();router.alignment_stage='align'
        router.base_target=np.array([-.08,-.04,.18]);router.arm_hold=np.zeros(6)
        with patch('mujoco_zyh.supported_push.maximum_measured_foot_speed',return_value=.002):
            router.advance_alignment(np.array([-.75,-.025,-.024]),np.eye(3),np.zeros(6))
        self.assertEqual(router.alignment_stage,'approach')
        self.assertTrue(np.array_equal(router.base_target,s.data.qpos[:3]))

    def check(self,local,**kw):
        from mujoco_zyh.supported_push import contact_entry_admission
        a=dict(hand_local_box=local,arm_velocity=np.zeros(6),reference_velocity=np.zeros(6));a.update(kw);return contact_entry_admission(**a)
    def test_measured_upper_edge_case_not_admitted_for_approach(self):
        self.assertFalse(self.check([-.59,.104,.11])['reference_stage_admitted'])
    def test_measured_offaxis_prior_case_must_recenter_first(self):
        self.assertFalse(self.check([-.62,.086,.028])['reference_stage_admitted'])
    def test_slow_center_height_outside_face_pass_NOT_safetyguarantee(self):
        a=self.check([-.64,.01,-.03]);self.assertTrue(a['reference_stage_admitted']);self.assertFalse(a['physical_command_authorized'])
    def test_actual_arm_or_issuedreference_still_moving_blocks_contact_stage(self):
        self.assertFalse(self.check([-.64,0.,-.03],arm_velocity=np.ones(6)*.2)['reference_stage_admitted'])
        self.assertFalse(self.check([-.64,0.,-.03],reference_velocity=np.ones(6)*.2)['reference_stage_admitted'])
    def test_center_band_matches_registered_actual_cartesian_target(self):
        self.assertTrue(self.check([-.64,0.,protocol()['protected_hand_height_offset_m']])['reference_stage_admitted'])
        self.assertFalse(self.check([-.64,0.,.10])['reference_stage_admitted'])
    def test_native_joint_waypoints_not_contact_drive_flag_gate_approach(self):
        from mujoco_zyh.supported_push import body_approach_stage_admission
        entry=self.check([-.64,0.,-.03])
        for drive in (False,True):
            a=body_approach_stage_admission(entry,native_safe_approach_complete=True,native_motion_ready=drive)
            self.assertTrue(a['allow_body_approach']);self.assertFalse(a['native_flags_modified'])
            a=body_approach_stage_admission(entry,native_safe_approach_complete=False,native_motion_ready=drive)
            self.assertFalse(a['allow_body_approach'])
    def test_unsafe_geometry_never_approaches_even_when_native_flags_true(self):
        from mujoco_zyh.supported_push import body_approach_stage_admission
        a=body_approach_stage_admission(self.check([-.64,.1,.1]),native_safe_approach_complete=True,native_motion_ready=True)
        self.assertFalse(a['allow_body_approach'])
    def test_pinned_native_contact_drive_flag_is_downstream_of_face_approach(self):
        text=(Path(os.environ['ZYH_BUNDLE'])/'push/controller/box_push_ik.py').read_text()
        self.assertIn('ready = self.precontact_ready & contact if self.precontact_heights.numel() else self.env.box_push_approached',text)
        self.assertIn('self.motion_ready |= ready',text)
        self.assertIn('self.safe_approach_complete[:] = ~active',text)
    def test_protocol_stage_is_not_circular_contact_requirement(self):
        p=protocol();g=p['registered_contact_center_gate']
        self.assertTrue(g['native_safe_approach_complete_required'])
        self.assertFalse(g['native_motion_ready_required_for_precontact_body_approach'])
        self.assertEqual(g['hand_local_z_center_m'],p['protected_hand_height_offset_m'])
    def test_nan_or_changed_native_tip_contract_refused(self):
        with self.assertRaises(ValueError):self.check([-.64,0.,np.nan])
        with self.assertRaises(ValueError):self.check([-.64,0.,-.03],tip_radius=.1)


if __name__=='__main__':unittest.main()
