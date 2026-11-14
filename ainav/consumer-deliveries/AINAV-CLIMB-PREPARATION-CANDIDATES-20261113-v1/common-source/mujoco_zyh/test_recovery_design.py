"""Synthetic CPU-only design tests. No actual recovery, physics or actor forward."""
import ast
from copy import deepcopy
import inspect
import json
import os
from pathlib import Path
import unittest
from initial_contact_progress_monitor import ContactProgressSample,ContactProgressConfig
from recovery_reference_intersection import axis_interval
from mujoco_zyh import recovery_design as d
from mujoco_zyh.preflight_recovery_design import inspect as inspect_sources


def design():return json.loads(Path(__file__).with_name('no_reset_recovery_protocol_v1.json').read_text())


def sample(tick,**changes):
    fields=dict(control_tick=tick,time_s=tick*.02,push_active=True,motion_ready=True,legal_hand_contact=True,
        measurement_valid=True,box_course_x_m=0.,near_original_goal=False,native_settled=False,native_hard_stop=False)
    fields.update(changes);return ContactProgressSample(**fields)


def axis(**changes):
    values=dict(reference=0.,reference_velocity=0.,measured_q=0.,measured_dq=0.,kp=10.,kd=1.,effort_limit=10.,soft_lower=-1.,soft_upper=1.,dt=.02)
    values.update(changes);return values


def queue():return [[[0.]*18,[0.]*18,[10.]*18,[1.]*18,[0.]*18] for _ in range(5)]


class Protocol(unittest.TestCase):
    def test_consistent_but_never_dispatchable_or_actuation_authorized(self):
        r=d.validate_design(design());self.assertTrue(r['design_consistent']);self.assertFalse(r['dispatchable']);self.assertFalse(r['actuator_command_authorized'])
    def test_no_execution_flag_flip(self):
        for k in ('dispatchable','controller_implemented','physical_dispatch_started','training_authorized'):
            p=design();p[k]=True
            with self.subTest(k=k),self.assertRaises(ValueError):d.validate_design(p)
    def test_no_margin_relaxation(self):
        for k,v in [('unloaded_force_N',4.),('support_capture_min_foot_N',4.),('body_clearance_m',.03),('effort_prediction_reserve',.98),('inner_joint_reference_margin_rad',0.)]:
            p=design();p['boundaries'][k]=v
            with self.subTest(k=k),self.assertRaises(ValueError):d.validate_design(p)
    def test_no_stow_or_ready_shortcut(self):
        for start,end in [('SOFT_ABORT_LATCH','PROTECTED_STOW'),('SHORT_RETREAT','PROTECTED_STOW'),('NATIVE_NAV_MOVE','RECOVERED_NAV_READY')]:
            p=design();p['state_edges'][start].append(end)
            with self.subTest(start=start),self.assertRaises(ValueError):d.validate_design(p)
    def test_no_invariant_removal_or_truthy_string(self):
        p=design();p['invariants'].pop('no_actuator_queue_clear_or_delay_rewrite')
        with self.assertRaises(ValueError):d.validate_design(p)
        p=design();p['invariants']['no_actuator_queue_clear_or_delay_rewrite']='yes'
        with self.assertRaises(ValueError):d.validate_design(p)
    def test_no_global_immovability_or_completed_physics_claim(self):
        p=design();p['global_immovability_claim']=True
        with self.assertRaises(ValueError):d.validate_design(p)
        p=design();p['new_physics_starts']=1
        with self.assertRaises(ValueError):d.validate_design(p)
    def test_private_high_rate_recovery_evidence_is_separate_from10Hz_visual(self):
        p=design();m=p['measurement_semantics']
        self.assertEqual(m['contact_monitor_rate_hz'],50);self.assertEqual(m['RGBD_rate_hz'],10)
        self.assertEqual(m['recovery_executor_private_sample_hz'],50);self.assertTrue(m['private_logs_never_model_input'])
        self.assertEqual(p['proposed_budget_NOT_DISPATCHED']['max_total_episode_bytes'],192*1024*1024)
    def test_no_live_or_strict_admission_claim(self):
        p=design();p['completion_status']['strict_limit_admission']=True
        with self.assertRaises(ValueError):d.validate_design(p)
    def test_not_accepted_by_original_collection_dispatcher(self):
        file=Path(__file__).with_name('collect.py');tree=ast.parse(file.read_text())
        fn,=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='validate_protocol']
        ns={};exec(compile(ast.Module(body=[fn],type_ignores=[]),str(file)+'[schema-only]','exec'),ns)
        with self.assertRaises(ValueError):ns['validate_protocol'](design())
    def test_same_goal_episode_and_attempt_immutable(self):
        self.assertTrue(d.unchanged_attempt([1.7,0.,.1],[1.7,0.,.1],'episode','episode','A0','A0'))
        for goal,episode,attempt in [([1.1,0.,.1],'episode','A0'),([1.7,0.,.1],'new','A0'),([1.7,0.,.1],'episode','new')]:
            with self.assertRaises(ValueError):d.unchanged_attempt([1.7,0.,.1],goal,'episode',episode,'A0',attempt)
    def test_no_physics_actor_or_actuator_API_in_design_module(self):
        for node in ast.walk(ast.parse(inspect.getsource(d))):
            if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute):
                self.assertNotIn(node.func.attr,('mj_step','step','reset','clear','copy_','set_action','set_joint_position_target','write_root_pose_to_sim','forward'))


class ContactDetector(unittest.TestCase):
    def test_reuses60ms_without_changing_inherited80ms_default(self):
        self.assertEqual(ContactProgressConfig().window_s,.08)
        m=d.new_initial_contact_monitor()
        for tick in range(3):self.assertFalse(m.observe(sample(tick)).new_soft_abort_request)
        out=m.observe(sample(3));self.assertTrue(out.new_soft_abort_request);self.assertTrue(out.attempt_failed)
        self.assertFalse(out.retraction_authorized);self.assertFalse(out.nav_takeover_authorized)
    def test_real_progress_not_mass_or_colour_decides(self):
        m=d.new_initial_contact_monitor()
        for i in range(4):out=m.observe(sample(i,box_course_x_m=i*.001))
        self.assertTrue(out.initial_progress_established);self.assertFalse(out.soft_abort_requested)
    def test_native_hard_stop_wins_even_at_failure_window(self):
        m=d.new_initial_contact_monitor()
        for i in range(3):m.observe(sample(i))
        out=m.observe(sample(3,native_hard_stop=True,native_settled=True))
        self.assertTrue(out.native_hard_stop_latched);self.assertFalse(out.new_soft_abort_request)
    def test_no_near_goal_false_failure(self):
        m=d.new_initial_contact_monitor()
        for i in range(6):out=m.observe(sample(i,near_original_goal=True))
        self.assertFalse(out.attempt_failed)
    def test_10Hz_RGBD_cannot_fake_a_continuous50Hz_contact_window(self):
        m=d.new_initial_contact_monitor()
        for i in (0,5,10,15):out=m.observe(sample(i))
        self.assertFalse(out.attempt_failed)
    def test_failed_attempt_not_relabelled_on_later_settling(self):
        m=d.new_initial_contact_monitor()
        for i in range(4):m.observe(sample(i))
        out=m.observe(sample(4,native_settled=True,box_course_x_m=.6))
        self.assertTrue(out.attempt_failed);self.assertFalse(out.object_globally_unmovable)


class Admission(unittest.TestCase):
    def entry(self,**changes):
        fields=dict(hard_flags=[],strict_limits_ok=True,strict_speed_ok=True,substep_guard_coverage=True,
            measured_reference_epoch=True,committed_queue_screen_pass=True,foot_normal_N=[11.62,40.,50.,60.])
        fields.update(changes);return d.entry_screen(**fields)
    def test_positive_bridge_is_not12N_capture(self):
        r=self.entry();self.assertTrue(r['screen_pass']);self.assertFalse(r['actual_supported_capture_pass']);self.assertFalse(r['actuator_command_authorized'])
    def test_airborne_foot_hard_flag_or_unsafe_range_refuses(self):
        for changes in [dict(foot_normal_N=[0.,40.,50.,60.]),dict(hard_flags=['arm_effort_safety']),dict(strict_limits_ok=False),dict(strict_speed_ok=False),dict(substep_guard_coverage=False),dict(committed_queue_screen_pass=False)]:
            with self.subTest(changes=changes):self.assertFalse(self.entry(**changes)['screen_pass'])
    def capture(self,**changes):
        fields=dict(legal_hand_contact=False,selected_hand_force_N=0.,all_candidate_hand_force_N=0.,box_linear_speed=0.,box_angular_speed=0.,base_linear_speed=0.,base_angular_speed=0.,tilt_rad=0.,foot_normal_N=[20.]*4,contact_point_slip_m_s=[0.]*4,strict_limits_ok=True,strict_speed_ok=True,native_all_candidate_contact_ok=True)
        fields.update(changes);return d.supported_unloaded_screen(**fields)
    def test_loaded_hand_cannot_start_stow_even_with_stopped_base(self):
        self.assertTrue(self.capture())
        for changes in [dict(selected_hand_force_N=3.),dict(all_candidate_hand_force_N=4.),dict(legal_hand_contact=True),dict(native_all_candidate_contact_ok=False)]:
            self.assertFalse(self.capture(**changes))
    def test_four_real_loads_and_contact_point_slip_required(self):
        self.assertFalse(self.capture(foot_normal_N=[11.99,20.,20.,20.]))
        self.assertFalse(self.capture(contact_point_slip_m_s=[0.,.04,0.,0.]))
        self.assertFalse(self.capture(base_linear_speed=.03))
    def test_nonfinite_and_implicit_boolean_refused(self):
        with self.assertRaises(ValueError):self.entry(strict_limits_ok=1)
        with self.assertRaises(ValueError):self.capture(selected_hand_force_N=float('nan'))
    def test_old_measured_backoff_envelope_reused_not_a_motion_policy(self):
        m=d.new_backoff_measurement_monitor()
        self.assertEqual(m.cfg.maximum_distance_m,.18);self.assertEqual(m.cfg.maximum_seconds,8.)
        m.begin(1.,[0.,0.,.3],.60,original_stable=True)
        r=m.observe(1.5,[-.03,0.,.3],.63,.01)
        self.assertEqual(r['phase'],'BRAKE_AFTER_BACKOFF')


class MotorSemantics(unittest.TestCase):
    def test_zero_FF_matches_inherited_rate_effort_intersection(self):
        values=axis();result=d.motor_aware_axis_interval(feedforward=0.,target_velocity=0.,delay_s=0.,**values)
        old=axis_interval(**dict(values,soft_lower=-.99,soft_upper=.99))
        self.assertEqual(result['lower'],old['lower']);self.assertEqual(result['upper'],old['upper'])
        self.assertFalse(result['actuator_command_authorized'])
    def test_nonzero_FF_is_not_ignored_or_removed_from_measured_q(self):
        values=axis(reference=-.5,effort_limit=1.);saved=deepcopy(values)
        result=d.motor_aware_axis_interval(feedforward=5.,target_velocity=0.,delay_s=0.,**values)
        self.assertTrue(result['feasible']);self.assertEqual(values,saved)
        self.assertFalse(axis_interval(**dict(values,soft_lower=-.99,soft_upper=.99))['feasible'])
    def test_velocity_target_term_accounted_separately_from_measured_dq(self):
        a=d.motor_aware_axis_interval(feedforward=0.,target_velocity=0.,delay_s=0.,**axis())
        b=d.motor_aware_axis_interval(feedforward=0.,target_velocity=1.,delay_s=0.,**axis())
        self.assertAlmostEqual(b['effort_interval'][0]-a['effort_interval'][0],-.1)
    def test_delay_extends_forecast_instead_of_clearing_queue(self):
        a=d.motor_aware_axis_interval(feedforward=0.,target_velocity=0.,delay_s=0.,**axis(measured_dq=.2))
        b=d.motor_aware_axis_interval(feedforward=0.,target_velocity=0.,delay_s=.02,**axis(measured_dq=.2))
        self.assertGreaterEqual(b['effort_interval'][0],a['effort_interval'][0])
    def test_invalid_nonzero_issued_derivative_is_not_zeroed(self):
        with self.assertRaises(ValueError):d.motor_aware_axis_interval(feedforward=0.,target_velocity=0.,delay_s=0.,**axis(reference_velocity=.6))
    def test_actual_angle_violation_or_empty_force_intersection_refuses(self):
        self.assertFalse(d.motor_aware_axis_interval(feedforward=0.,target_velocity=0.,delay_s=0.,**axis(measured_q=1.01))['feasible'])
        self.assertFalse(d.motor_aware_axis_interval(feedforward=100.,target_velocity=0.,delay_s=0.,**axis())['feasible'])
    def test_zero_reference_on_arm_joint_boundary_is_not_admitted(self):
        r=d.motor_aware_axis_interval(feedforward=0.,target_velocity=0.,delay_s=0.,**axis(soft_lower=0.))
        self.assertFalse(r['feasible'])
    def check_queue(self,qbuf,delays=None,**kwargs):
        return d.committed_queue_screen(queue=qbuf,delay_steps=delays or [4]*18,q=[0.]*18,dq=[0.]*18,effort=[10.]*18,**kwargs)
    def test_real_full_queue_prefix_admitted_readonly(self):
        q=queue();before=deepcopy(q);r=self.check_queue(q)
        self.assertTrue(r['screen_pass']);self.assertEqual(r['immutable_prefix_axis_samples'],72);self.assertEqual(q,before)
    def test_already_committed_bad_command_cannot_be_unsent_by_new_zero(self):
        q=queue();q[-4][4][0]=9.1;q[-1][4][0]=0.
        result=self.check_queue(q);self.assertFalse(result['screen_pass']);self.assertFalse(result['queue_or_delay_modified'])
    def test_zero_delay_is_a_distinct_actual_configuration_not_assumed(self):
        r=self.check_queue(queue(),[0]*18);self.assertTrue(r['screen_pass']);self.assertEqual(r['immutable_prefix_axis_samples'],0)
    def test_missing_queue_or_unknown_delay_rejected(self):
        with self.assertRaises(ValueError):self.check_queue(queue()[:4])
        with self.assertRaises(ValueError):self.check_queue(queue(),[5]*18)


class SourceOnly(unittest.TestCase):
    def test_native_consumer_inventory_and_zero_boundary_not_a_controller(self):
        bundle=os.environ['ZYH_BUNDLE'];r=inspect_sources(bundle,design())
        self.assertEqual(len(r['native_consumer_inventory']),14);self.assertFalse(r['dispatchable'])
        self.assertEqual(r['native_zero_arm_reference_compatibility']['proposed_inward_reference_rad'],[0.,.01,-.01,0.,0.,0.])
        self.assertFalse(r['native_zero_arm_reference_compatibility']['FK_collision_NAV_policy_or_dynamics_validated'])
        self.assertEqual(r['new_physics_starts'],0)


if __name__=='__main__':unittest.main()
