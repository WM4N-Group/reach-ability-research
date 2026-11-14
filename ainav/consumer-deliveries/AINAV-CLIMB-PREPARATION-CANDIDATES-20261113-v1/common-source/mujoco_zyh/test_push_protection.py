"""Synthetic CPU decisions/authority only, not simulated safety/reliability."""
from collections import deque
from dataclasses import asdict,replace
from pathlib import Path
from types import SimpleNamespace as NS
import io,json,unittest
from unittest.mock import patch
import numpy as np

from mujoco_zyh.push_protection import CONFIG,screen,PrequeueProtectionRouter
from mujoco_zyh.protected_recovery_pilot import protocol
from mujoco_zyh.collect import validate_protocol


def inputs():
    u=np.zeros((5,18));u[2]=20.;u[3]=1.
    return dict(proposed=u,queue=[u.copy() for _ in range(5)],delay_steps=np.full(18,4),q=np.zeros(18),dq=np.zeros(18),
        effort=np.full(18,20.),base_velocity_world=np.array([.03,0.,0.]),measured_acceleration_world=np.zeros(3),
        foot_normal_N=np.full(4,20.),tilt_rad=.01,hard_flags=dict(box_contact=False,invalid_hand_contact=False,box_tipped=False))


class PrequeueScreens(unittest.TestCase):
    def test_good_real_inputs_return_UNCHANGED_not_certified_safety(self):
        d=screen(**inputs());self.assertEqual(d['action'],'PROPOSE_UNCHANGED');self.assertFalse(d['guaranteed_future_safety']);self.assertFalse(d['physical_command_authorized'])
    def test_early_speed_warns_before_original_point15_gate(self):
        p=inputs();p['base_velocity_world'][0]=.081;d=screen(**p)
        self.assertEqual(d['action'],'BRAKE_RETIRE_PUSH');self.assertIn('base_speed_reserve',d['reasons'])
    def test_already_outside_original_domain_is_failure_not_recovery(self):
        p=inputs();p['base_velocity_world'][0]=.151
        self.assertEqual(screen(**p)['action'],'STOP_AND_CENSOR')
    def test_orthogonal_speed_not_only_forward_x(self):
        p=inputs();p['base_velocity_world'][:]=[0.,.09,0.]
        self.assertIn('base_speed_reserve',screen(**p)['reasons'])
    def test_current_acceleration_warns_but_never_certifies_bound(self):
        p=inputs();p['measured_acceleration_world'][0]=4.;d=screen(**p)
        self.assertEqual(d['action'],'BRAKE_RETIRE_PUSH');self.assertTrue(d['measured_acceleration_is_NOT_future_bound'])
    def test_forecast_includes_per_axis_delay_next_step_measurement_reserve(self):
        d=screen(**inputs());self.assertAlmostEqual(d['warning_horizon_s'],.030)
    def test_zero_delay_does_not_erase_sampling_and_execution_latency(self):
        p=inputs();p['delay_steps'][:]=0;self.assertAlmostEqual(screen(**p)['warning_horizon_s'],.010)
    def test_support_warning_requires_measured_load_and_motion(self):
        p=inputs();p['foot_normal_N'][:]=[20.,20.,0.,0.];p['base_velocity_world'][0]=.05
        self.assertIn('measured_support_load_reserve',screen(**p)['reasons'])
    def test_stationary_foot_unload_not_fabricated_capture(self):
        p=inputs();p['foot_normal_N'][:]=0.;d=screen(**p)
        self.assertEqual(d['loaded_feet_count'],0);self.assertFalse(d['guaranteed_future_safety'])
    def test_tilt_reserve_is_stricter_not_relaxed_native_guard(self):
        p=inputs();p['tilt_rad']=.061;self.assertIn('tilt_reserve',screen(**p)['reasons'])
    def test_actual_complete_PD_FF_proposal_not_position_only(self):
        p=inputs();p['proposed'][4,13]=14.1
        self.assertIn('arm_PD_FF_reserve',screen(**p)['reasons'])
    def test_target_velocity_is_included_in_effort_screen(self):
        p=inputs();p['proposed'][1,13]=15.
        self.assertIn('arm_PD_FF_reserve',screen(**p)['reasons'])
    def test_predicted_actual_motion_effort_checked_at60ms(self):
        p=inputs();p['dq'][13]=12.
        self.assertIn('arm_PD_FF_reserve',screen(**p)['reasons'])
    def test_old_pending_high_torque_cannot_be_erased_by_good_new_proposal(self):
        p=inputs();p['queue'][-1][4,0]=19.
        self.assertIn('immutable_pending_torque_screen',screen(**p)['reasons'])
    def test_hard_contact_always_wins_over_early_soft_retirement(self):
        p=inputs();p['hard_flags']['invalid_hand_contact']=True;p['base_velocity_world'][0]=.09
        self.assertEqual(screen(**p)['action'],'STOP_AND_CENSOR')
    def test_each_original_contact_guard_remains_hard(self):
        for name in inputs()['hard_flags']:
            p=inputs();p['hard_flags'][name]=True
            with self.subTest(name=name):self.assertEqual(screen(**p)['action'],'STOP_AND_CENSOR')
    def test_invalid_measured_data_fails_closed(self):
        for key,value in [('base_velocity_world',[np.nan,0,0]),('delay_steps',np.full(18,.5)),('effort',np.zeros(18)),('q',np.zeros(17)),('tilt_rad',np.inf)]:
            p=inputs();p[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):screen(**p)
    def test_invalid_or_negative_gains_refused(self):
        p=inputs();p['proposed'][2,0]=-1.
        with self.assertRaises(ValueError):screen(**p)
    def test_future_margin_cannot_be_silently_tuned(self):
        with self.assertRaises(ValueError):screen(**inputs(),config=replace(CONFIG,warning_base_speed_m_s=.14))
    def test_unmodified_actual_state_and_proposal_and_immutable_queue(self):
        p=inputs();q=p['q'].copy();u=p['proposed'].copy();queue=[v.copy() for v in p['queue']]
        screen(**p);self.assertTrue(np.array_equal(q,p['q']));self.assertTrue(np.array_equal(u,p['proposed']))
        for before,after in zip(queue,p['queue']):self.assertTrue(np.array_equal(before,after))


class Authority(unittest.TestCase):
    def router(self,speed=.03):
        import torch
        p=inputs();s=NS(queue=deque(p['queue'],maxlen=5),delays=p['delay_steps'],data=NS(
            qpos=p['q'].copy(),qvel=np.r_[speed,np.zeros(17)],qacc=np.zeros(18),xmat=np.eye(3).reshape(1,9),time=1.),
            qids=np.arange(18),dids=np.arange(18),base_id=0,feet_ids=np.arange(4),forces=np.c_[np.zeros((4,2)),p['foot_normal_N']],
            controller=NS(motion_ready=[True]),hand_cfg=NS(),box_push_target=torch.ones((1,3)))
        proposal=NS(array=lambda:p['proposed'].copy());old=NS(array=lambda:np.ones((5,18))*.001)
        box=NS(forbidden_box_contact=lambda s:[False],invalid_hand_contact=lambda s,cfg:[False],box_tipped=lambda s:[False],hand_contact=lambda s,cfg:[True])
        r=NS(sim=s,last=old,push={'model':NS(EFFORT=p['effort']),'bridge':NS(box_push=box)})
        router=PrequeueProtectionRouter.__new__(PrequeueProtectionRouter);router.r=r;router.recovery=None
        router.native=NS(phase='run',kind='push',finish=None,next_command=lambda:proposal)
        router.protection_log=io.StringIO();router.prequeue_checks=0;router.protective_retirement=None
        router.last_two=deque([np.zeros(18),np.zeros(18)],maxlen=2)
        return router,proposal
    def test_good_original_NN_proposal_is_identical_object(self):
        router,proposal=self.router();self.assertIs(router.next_command(),proposal);self.assertIsNone(router.recovery)
    def test_bad_proposal_not_sent_to_motor_and_irreversible_QP_takeover(self):
        router,proposal=self.router(.09);replacement=object();stow=NS(events=[],command=lambda:replacement)
        before=[v.copy() for v in router.r.sim.queue]
        with patch('mujoco_zyh.push_protection.emit'),patch('mujoco_zyh.push_protection.ProtectedStow',return_value=stow):
            out=router.next_command()
            self.assertIs(out,replacement);self.assertIsNot(out,proposal);self.assertIs(router.next_command(),replacement)
        self.assertFalse(router.protective_retirement['original_60ms_progress_failure_observed'])
        for a,b in zip(before,router.r.sim.queue):self.assertTrue(np.array_equal(a,b))
    def test_hard_failure_never_constructs_stow(self):
        router,_=self.router(.16)
        with patch('mujoco_zyh.push_protection.emit'),patch('mujoco_zyh.push_protection.ProtectedStow') as stow:
            with self.assertRaisesRegex(RuntimeError,'prequeue_native_hard'):router.next_command()
            stow.assert_not_called()
    def test_does_not_modify_or_intercept_native_prepare(self):
        router,proposal=self.router(.16);router.native.phase='prepare';self.assertIs(router.next_command(),proposal)
        self.assertEqual(router.prequeue_checks,0)
    def test_protective_abort_before_hand_contact_is_explicit_not_hidden(self):
        router,_=self.router(.09);router.r.push['bridge'].box_push.hand_contact=lambda *a:[False]
        with patch('mujoco_zyh.push_protection.emit'),patch('mujoco_zyh.push_protection.ProtectedStow',return_value=NS(events=[],command=lambda:None)):
            router.next_command()
        self.assertFalse(router.protective_retirement['actual_legal_hand_contact']);self.assertFalse(router.protective_retirement['native_goal_success'])


class ProspectiveProtocol(unittest.TestCase):
    def test_exact_one_new_development_pilot_registered(self):
        p=protocol();validate_protocol(p);self.assertEqual(p['episodes'],1);self.assertFalse(p['training_allowed']);self.assertEqual(p['seed'],5405)
    def test_no_reset_training_role_budget_or_margin_changes(self):
        for key,value in [('seed',11),('automatic_retry',True),('max_sim_seconds',81),('training_allowed',True),('reset_after_initial_allowed',1)]:
            p=protocol();p[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):validate_protocol(p)
    def test_original_hard_and_full_stow_gates_retained(self):
        old=json.loads(Path(__file__).with_name('soft_stall_stow_protocol_v7.json').read_text());p=protocol()
        self.assertEqual(p['recovery_limits'],old['recovery_limits']);self.assertEqual(p['protection_config'],asdict(CONFIG))
        self.assertNotIn('option_forecast_case',p);self.assertFalse(p['WM_control'])
    def test_new_pilot_does_not_relabel_ABCor_heldout(self):
        p=protocol();self.assertEqual(p['role'],'development');self.assertEqual(p['selected_object_id'],'probe_object')
        self.assertIn('TRAIN5',p['known_condition_NOT_new_independent_sample']);self.assertNotIn('reselect_B_mode',p)


class FromStartReferenceDomain(unittest.TestCase):
    def test_fast_real_seed_is_rejected_not_zeroed_or_clipped(self):
        from mujoco_zyh.push_protection import arm_takeover_admission,arm_reference_rate_step
        refs=np.zeros((2,18));refs[1,13]=.01
        a=arm_takeover_admission(last_two_issued_positions=refs,actual_arm_q=np.zeros(6),inner_reference_limits=np.tile([-1.,1.],(6,1)))
        self.assertFalse(a['direct_existing_stow_handoff_admitted']);self.assertEqual(a['reference_speed_violations_zero_based'],[1])
        with self.assertRaises(ValueError):arm_reference_rate_step(np.ones(6),refs[1,12:],np.array(a['actual_reference_velocity_rad_s']))
    def test_stationary_approach_outside_fold_domain_needs_real_bridge(self):
        from mujoco_zyh.push_protection import arm_takeover_admission
        refs=np.zeros((2,18));refs[:,13]=.05;limits=np.tile([-1.,1.],(6,1));limits[1]=[.167,3.]
        a=arm_takeover_admission(last_two_issued_positions=refs,actual_arm_q=refs[-1,12:],inner_reference_limits=limits)
        self.assertFalse(a['direct_existing_stow_handoff_admitted']);self.assertEqual(a['actual_q_outside_inner_domain_zero_based'],[1])
    def test_rate_and_acceleration_obey_original_bounds_for_reversals(self):
        from mujoco_zyh.push_protection import arm_reference_rate_step
        r=np.zeros(6);v=np.zeros(6)
        for i in range(1400):
            nr,nv=arm_reference_rate_step(np.full(6,1. if i<700 else -1.),r,v)
            self.assertLessEqual(abs(nv).max(),.45);self.assertLessEqual(abs((nv-v)/.005).max(),1.+1e-8)
            self.assertTrue(np.allclose((nr-r)/.005,nv));r,v=nr,nv
    def test_software_step_never_mutates_actual_seed_or_goal(self):
        from mujoco_zyh.push_protection import arm_reference_rate_step
        r=np.zeros(6);v=np.zeros(6);goal=np.ones(6);arm_reference_rate_step(goal,r,v)
        self.assertTrue((r==0).all());self.assertTrue((v==0).all());self.assertTrue((goal==1).all())
    def test_measured_inside_domain_is_not_certified_queue_or_dynamics(self):
        from mujoco_zyh.push_protection import arm_takeover_admission
        a=arm_takeover_admission(last_two_issued_positions=np.zeros((2,18)),actual_arm_q=np.zeros(6),inner_reference_limits=np.tile([-1.,1.],(6,1)))
        self.assertTrue(a['direct_existing_stow_handoff_admitted']);self.assertFalse(a['physical_control_authorized']);self.assertFalse(a['actual_future_brake_safety_certified'])


class PositionPDFeasibleDomain(unittest.TestCase):
    def inputs(self):
        return dict(desired=np.ones(6)*.5,reference=np.ones(6)*.3,reference_velocity=np.zeros(6),q=np.ones(6)*.3,dq=np.zeros(6),
                    kp=np.array([50.,50.,80.,30.,30.,20.]),kd=np.array([3.,2.,3.,3.,2.5,1.]),feedforward=np.ones(6)*-.5,
                    effort=np.array([20.,20.,15.,7.,5.,5.]),inner_limits=np.tile([.1,.9],(6,1)))
    def call(self,**kw):
        from mujoco_zyh.push_protection import protected_position_reference_step
        a=self.inputs();a.update(kw);return a,protected_position_reference_step(**a)
    def test_outgoing_PD_velocity_is_zero_not_reference_derivative(self):
        a,b=self.call();self.assertTrue((b['PD_velocity']==0.).all());self.assertGreater(b['reference_velocity'].max(),0.)
    def test_exact_Kp_Kd_FF_effort_at_both_original_horizons(self):
        a,b=self.call(dq=np.ones(6)*.03)
        for h in (0.,.06):
            raw=a['kp']*(b['reference']-a['q']-h*a['dq'])-a['kd']*a['dq']+a['feedforward']
            self.assertTrue((abs(raw)<=.9*a['effort']+1e-10).all())
    def test_position_rate_and_acceleration_never_jump_to_goal(self):
        a,b=self.call();self.assertLessEqual(abs(b['reference']-a['reference']).max(),.45*.005)
        self.assertLessEqual(abs((b['reference_velocity']-a['reference_velocity'])/.005).max(),1.+1e-8)
    def test_real_fast_seed_cannot_be_clipped_into_admission(self):
        with self.assertRaises(ValueError):self.call(reference_velocity=np.ones(6)*1.145)
    def test_actual_approach_q_cannot_be_clipped_to_fold_inner_domain(self):
        with self.assertRaisesRegex(ValueError,'REAL compact-entry'):self.call(q=np.ones(6)*.05)
    def test_actual_reference_outside_domain_also_refused(self):
        with self.assertRaisesRegex(ValueError,'REAL compact-entry'):self.call(reference=np.ones(6)*.05)
    def test_predicted_q_outside_inner_domain_is_refusal_not_threshold_relaxation(self):
        with self.assertRaisesRegex(ValueError,'forecast'):self.call(q=np.ones(6)*.899,dq=np.ones(6)*.1)
    def test_infeasible_force_reference_intersection_stops(self):
        with self.assertRaisesRegex(RuntimeError,'intersection_empty'):self.call(feedforward=np.ones(6)*100.)
    def test_no_actor_or_motor_authority_from_pure_math_pass(self):
        _,b=self.call();self.assertFalse(b['actuator_command_authorized']);self.assertFalse(b['geometry_or_contact_or_base_dynamics_certified'])
    def test_invalid_joint_limits_gains_or_nonfinite_input_refused(self):
        for kw in (dict(kp=np.zeros(6)),dict(kd=-np.ones(6)),dict(q=np.ones(6)*np.nan),dict(inner_limits=np.zeros((6,2)))):
            with self.subTest(kw=kw),self.assertRaises(ValueError):self.call(**kw)
    def test_original_observed_inputs_are_not_written(self):
        a=self.inputs();copies={k:v.copy() for k,v in a.items()}
        from mujoco_zyh.push_protection import protected_position_reference_step
        protected_position_reference_step(**a)
        for k in a:self.assertTrue(np.array_equal(a[k],copies[k]))


class NativeSourceInnerDomain(unittest.TestCase):
    def runtime(self):
        names=['joint'+str(i) for i in range(1,7)]+['leg'+str(i) for i in range(12)]
        soft=np.tile([-2.,2.],(1,18,1));soft[0,1]=[.157,2.983];soft[0,2]=[-2.819,-.14835]
        physical=np.tile([-3.,3.],(18,1));physical[13]=[0.,3.14];physical[14]=[-2.967,0.]
        return NS(sim=NS(robot=NS(joint_names=names,data=NS(soft_joint_pos_limits=soft)),model=NS(jnt_range=physical),jids=np.arange(18)))
    def test_named_source_order_not_physical_range_guess(self):
        from mujoco_zyh.push_protection import native_arm_inner_limits
        bounds=native_arm_inner_limits(self.runtime());self.assertAlmostEqual(bounds[1,0],.167)
        self.assertAlmostEqual(bounds[2,1],-.15835);self.assertNotAlmostEqual(bounds[1,0],.025*3.14+.01)
    def test_original_physical_intersection_is_retained(self):
        from mujoco_zyh.push_protection import native_arm_inner_limits
        r=self.runtime();r.sim.model.jnt_range[13,0]=.2
        self.assertAlmostEqual(native_arm_inner_limits(r)[1,0],.21)
    def test_empty_native_domain_refused(self):
        from mujoco_zyh.push_protection import native_arm_inner_limits
        r=self.runtime();r.sim.robot.data.soft_joint_pos_limits[0,1]=[2.,1.]
        with self.assertRaises(ValueError):native_arm_inner_limits(r)
    def test_no_limit_mutation_during_readonly_admission(self):
        from mujoco_zyh.push_protection import native_arm_inner_limits
        r=self.runtime();before=r.sim.model.jnt_range.copy();old=r.sim.robot.data.soft_joint_pos_limits.copy()
        native_arm_inner_limits(r);self.assertTrue(np.array_equal(before,r.sim.model.jnt_range));self.assertTrue(np.array_equal(old,r.sim.robot.data.soft_joint_pos_limits))


if __name__=='__main__':unittest.main()
