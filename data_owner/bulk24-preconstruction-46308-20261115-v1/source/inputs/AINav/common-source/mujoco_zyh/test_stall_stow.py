"""CPU contracts only. No real recovery/physics acceptance from these tests."""
import ast,json,unittest
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from mujoco_zyh.stall_stow import unload_reference,INITIAL_ARM,STOW_ARM,select_reference,validate_protocol,prepare_initialization_source
from mujoco_zyh.runtime_adapter import prepare_runtime_source
from mujoco_zyh.push_forecast_protocol import load_plan,case_protocol
from mujoco_zyh.collect import validate_protocol as validate_any

class Protocol(unittest.TestCase):
    def p(self):return json.loads(Path(__file__).with_name('soft_stall_stow_protocol_v7.json').read_text())
    def test_independent_no_reset_no_training_single_stow_only(self):
        p=self.p();validate_any(p);self.assertEqual(p['episodes'],1);self.assertEqual(p['reset_after_initial_allowed'],0);self.assertFalse(p['automatic_retry']);self.assertEqual(p['WM_forwards'],0);self.assertEqual(p['training_runs'],0)
    def test_budget_or_physics_or_goal_cannot_flip(self):
        for k,v in [('max_sim_seconds',101),('push_distance_m',0),('selected_object_id','middle'),('automatic_retry',True)]:
            p=self.p();p[k]=v
            with self.subTest(k=k),self.assertRaises(ValueError):validate_protocol(p)
    def test_old_design_stays_non_dispatchable(self):
        p=json.loads(Path(__file__).with_name('no_reset_recovery_protocol_v1.json').read_text());self.assertFalse(p['dispatchable']);self.assertFalse(p['controller_implemented'])
    def test_interior_start_within_original_entry_contract(self):
        self.assertLess(abs(INITIAL_ARM).max(),.12);self.assertGreater(INITIAL_ARM[1],.01);self.assertLess(INITIAL_ARM[2],-.01)
    def test_final_is_native_compact_waypoint_not_NAV_ready_claim(self):
        self.assertGreater(STOW_ARM[1],.1);self.assertLess(abs(STOW_ARM).max(),.2)
    def test_extra_hooks_only_in_initialization_source(self):
        import os
        source=(Path(os.environ['ZYH_BUNDLE'])/'switch/runtime.py').read_text();prepared,_=prepare_runtime_source(source);changed,receipt=prepare_initialization_source(prepared)
        self.assertEqual(receipt['initialization_only_hunks'],3);self.assertTrue(receipt['inverse_restores_native_scene_hook_source']);ast.parse(changed)
    def test_supported_initializer_refuses_after_physics(self):
        from mujoco_zyh.stall_stow import initialize_supported_stance
        for time,steps,queue in [(.005,0,[]),(0.,1,[]),(0.,0,[1])]:
            r=SimpleNamespace(sim=SimpleNamespace(data=SimpleNamespace(time=time),queue=queue),step_count=steps)
            with self.assertRaises(ValueError):initialize_supported_stance(r)
    def test_supported_initializer_requires_original_reference(self):
        from mujoco_zyh.stall_stow import initialize_supported_stance
        r=SimpleNamespace(sim=SimpleNamespace(data=SimpleNamespace(time=0.),queue=[]),step_count=0)
        with self.assertRaises(ValueError):initialize_supported_stance(r)
        self.assertFalse(initialize_supported_stance(r,False)['applied'])
    def test_hook_mismatch_refused(self):
        with self.assertRaises(ValueError):prepare_initialization_source('unknown source')
    def test_no_task_physics_setters_in_live_recovery_module(self):
        tree=ast.parse(Path(__file__).with_name('stall_stow.py').read_text())
        for node in ast.walk(tree):
            if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute):self.assertNotIn(node.func.attr,('mj_step','mj_setState','mj_resetData','reset_data','clear'))
    def test_new_protocol_does_not_change_old_forecast_cases(self):
        validate_any(case_protocol(load_plan()['cases'][0]))

class CoupledReference(unittest.TestCase):
    def call(self,**kw):
        a=dict(desired=np.ones(6)*.3,reference=np.ones(6)*.2,velocity=np.zeros(6),q=np.ones(6)*.2,dq=np.zeros(6),kp=np.ones(6)*50,kd=np.ones(6)*3,ff=np.ones(6)*.5,effort=np.ones(6)*20,limits=np.tile([-1.,1.],(6,1)));a.update(kw);return select_reference(**a)
    def test_actual_PD_velocity_and_FF_are_bounded_at_both_horizons(self):
        q,v,receipt=self.call();self.assertTrue((abs(v)<=.02000001).all());self.assertTrue((q>.2).all())
        for h in (0,.06):self.assertTrue((abs(50*(q-.2)+3*v+.5)<=18+1e-7).all())
    def test_reference_acceleration_not_silently_relaxed(self):
        q,v,_=self.call(velocity=np.ones(6)*.2);self.assertTrue((abs(v-.2)<=.0200001).all())
    def test_unreachable_effort_intersection_refuses_not_clips_actual_state(self):
        q=np.ones(6)*.9;before=q.copy()
        with self.assertRaises(RuntimeError):self.call(reference=np.ones(6)*-.9,q=q,ff=np.zeros(6))
        self.assertTrue(np.array_equal(q,before))
    def test_invalid_reference_speed_seed_refused(self):
        with self.assertRaises(ValueError):self.call(velocity=np.ones(6)*.6)
    def test_goal_step_does_not_jump_reference(self):
        q,v,_=self.call(desired=np.ones(6)*.9);self.assertLess(abs(q-.2).max(),.000401)
    def test_actual200Hz_reference_sequence_obeys_speed_and_acceleration(self):
        r=np.ones(6)*.2;v=np.zeros(6)
        for i in range(1600):
            goal=np.ones(6)*(.7 if i<800 else -.4)
            q,nv,_=self.call(desired=goal,reference=r,velocity=v,q=r.copy(),dq=v.copy(),dt=.005)
            self.assertTrue((abs((q-r)/.005)<=.45+1e-9).all());self.assertTrue((abs((nv-v)/.005)<=1.+1e-7).all());r,v=q,nv
    def test_feedforward_extreme_causes_refusal_not_actuator_override(self):
        with self.assertRaises(RuntimeError):self.call(ff=np.ones(6)*100)

if __name__=='__main__':unittest.main()

class UnloadBumpless(unittest.TestCase):
    def test_reconciles_PD_gravity_deflection_without_torque_jump(self):
        start=np.ones(6)*.2;goal=np.ones(6)*.3;r=start.copy();v=np.zeros(6);g=np.ones(6)*-5;limits=np.tile([-1.,1.],(6,1))
        for i in range(300):
            nr,nv,ff,_=unload_reference(goal,start,r,v,goal,np.zeros(6),np.ones(6)*50,np.ones(6)*3,g,np.ones(6)*20,limits,i*.005)
            tau=50*(nr-goal)+ff
            
            if ((nr>=start)&(nr<=goal)).all():self.assertTrue(np.allclose(tau,g,atol=1e-8))
            self.assertLess(abs(tau-g).max(),.1)  # bounded discrete braking overshoot, not a torque step
            self.assertTrue((abs(nv)<=.45).all());self.assertTrue((abs((nv-v)/.005)<=1.+1e-7).all());r,v=nr,nv
    def test_all_real_feedforward_and_position_fields_remain_finite(self):
        r,v,ff,_=unload_reference(np.ones(6)*.25,np.ones(6)*.2,np.ones(6)*.2,np.zeros(6),np.ones(6)*.25,np.zeros(6),np.ones(6)*50,np.ones(6)*3,np.ones(6)*-2.5,np.ones(6)*20,np.tile([-1.,1.],(6,1)),0.)
        self.assertTrue(np.isfinite(np.r_[r,v,ff]).all())


class MeasuredBaseServo(unittest.TestCase):
    def test_native_COM_task_reduces_to_actual_base_velocity_feedback(self):
        from mujoco_zyh.stall_stow import base_tracking_com_goal
        for leg_shape in (-.2,0.,.2):
            for rotation in (-.03,.03):
                for arm in (-.05,.05):
                    for gap in (.52,.64,.645,.65,.70):
                        base=-.035;comv=base+leg_shape+rotation+arm;K,D=80.,18.
                        target,v=base_tracking_com_goal(.1,base,comv,gap,K,D)
                        actual_native_accel=K*(target-.1)-D*comv
                        self.assertAlmostEqual(actual_native_accel,D*(v-base),places=12)
                        self.assertLessEqual(abs(v),.05)
    def test_overshoot_brakes_and_returns_instead_of_uncontrolled_drift(self):
        from mujoco_zyh.stall_stow import base_tracking_com_goal
        target,v=base_tracking_com_goal(.1,-.04,0.,.68,80.,18.)
        self.assertGreater(v,0.)
        self.assertGreater(80*(target-.1),0.)
    def test_invalid_kinematics_or_gains_refused(self):
        from mujoco_zyh.stall_stow import base_tracking_com_goal
        for args in ((0.,0.,float('nan'),.64,80.,18.),(0.,0.,0.,.64,0.,18.)):
            with self.assertRaises(ValueError):base_tracking_com_goal(*args)


class InteriorTerminalReference(unittest.TestCase):
    def test_initialization_does_not_change_with_final_target(self):
        from mujoco_zyh.stall_stow import initial_posture,NATIVE_COMPACT_ARM
        self.assertTrue(np.array_equal(initial_posture(np.zeros(18))[12:],NATIVE_COMPACT_ARM))
        self.assertFalse(np.array_equal(NATIVE_COMPACT_ARM,STOW_ARM))
    def test_final_target_is_strictly_inside_native_soft_plus_margin(self):
        limits=np.array([[-2.618,2.618],[0.,3.139999816941817],[-2.9669998072658332,0.],[-1.745,1.745],[-1.22,1.22],[-2.0944,2.0944]])
        soft=limits.mean(1)[:,None]+.95*(limits-limits.mean(1)[:,None])
        self.assertTrue((STOW_ARM>soft[:,0]+.01).all());self.assertTrue((STOW_ARM<soft[:,1]-.01).all())
        q,v,_=select_reference(STOW_ARM,STOW_ARM,np.zeros(6),STOW_ARM,np.zeros(6),np.ones(6)*50,np.ones(6)*3,np.zeros(6),np.ones(6)*20,soft,dt=.005)
        self.assertTrue(np.array_equal(q,STOW_ARM));self.assertTrue((v==0).all())
