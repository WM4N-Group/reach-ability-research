"""CPU contract tests; not live NAV acceptance."""
import importlib.util,json,os,sys,unittest
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from mujoco_zyh.resume_nav import compact_contract,make_compact_nav,validate_protocol,NAV_ARM
from mujoco_zyh.stall_stow import STOW_ARM

class CompactContracts(unittest.TestCase):
    def p(self):return json.loads(Path(__file__).with_name('resume_nav_protocol_v5.json').read_text())
    def test_exact_new_scope_only(self):self.assertIs(validate_protocol(self.p())['training_allowed'],False)
    def test_cannot_call_original_READY_passed(self):
        p=self.p();p['navigation']['original_zero_arm_READY']=True
        with self.assertRaises(ValueError):validate_protocol(p)
    def test_budget_change_requires_new_protocol(self):
        p=self.p();p['max_sim_seconds']+=1
        with self.assertRaises(ValueError):validate_protocol(p)
    def runtime(self):
        limits=np.array([[-2.618,2.618],[0.,3.14],[-2.967,0.],[-1.745,1.745],[-1.22,1.22],[-2.0944,2.0944]])
        soft=limits.mean(1)[:,None]+.90*(limits-limits.mean(1)[:,None])
        tensor=SimpleNamespace(numpy=lambda:soft[None])
        robot=SimpleNamespace(data=SimpleNamespace(soft_joint_pos_limits=tensor),joint_names=['joint'+str(i) for i in range(1,7)])
        sim=SimpleNamespace(robot=robot,model=SimpleNamespace(jnt_range=limits),jids=np.r_[np.zeros(12,dtype=int),np.arange(6)])
        return SimpleNamespace(sim=sim)
    def test_original_zero_contract_is_incompatible_with_frozen_inner_domain(self):
        contract=compact_contract(self.runtime())
        self.assertTrue(contract['original_zero_arm_contract_incompatible'])
        self.assertFalse(contract['original_zero_arm_READY_passed'])
        self.assertGreater(contract['protected_soft_limits'][1][0]+.01,.12)
    def test_arm_motor_interface_change_is_explicit_not_claimed_original_NAV(self):
        contract=compact_contract(self.runtime())
        self.assertFalse(contract['native_NAV_arm_motor_interface_unchanged'])
        self.assertEqual(contract['native_NAV_arm_kp'],[40.,40.,40.,20.,20.,20.])
        self.assertEqual(contract['protected_arm_kp'],[50.,50.,80.,30.,30.,20.])
        self.assertTrue(contract['native_NAV_leg_gains_unchanged'])
    def test_no_guard_threshold_relaxation(self):
        contract=compact_contract(self.runtime());self.assertFalse(contract['threshold_relaxation'])
        self.assertEqual(contract['compact_entry_error_limit'],.04)

class TargetRelativeGates(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root=Path(os.environ['ZYH_BUNDLE'])/'nav';sys.path.insert(0,str(root))
        spec=importlib.util.spec_from_file_location('_resume_native_navigation',root/'navigation.py');module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module);cls.module=module
    def nav(self):return make_compact_nav(SimpleNamespace(nav={'navigation':self.module}),[0.,-.35])
    def state(self,**kw):
        args=dict(time=1.,xy=np.array([0.,-.35]),yaw=0.,velocity=np.zeros(3),arm_q=NAV_ARM.copy(),arm_qd=np.zeros(6),tilt=0.);args.update(kw);return self.module.NavState(**args)
    def test_change_target_not_arm_tolerance(self):
        nav=self.nav();self.assertEqual(nav.config.arm_joint_tolerance,.1)
        state=self.state();nav.native.phase='settle'
        self.assertTrue(nav.native.stability_checks(state)['arm_joints'])
        native=self.module.NavSkill([0.,-.35],0.,nav.config,arm_zero=True);native.phase='settle'
        self.assertFalse(native.stability_checks(state)['arm_joints'])
    def test_other_native_gates_identical_and_fail_closed(self):
        nav=self.nav();native=self.module.NavSkill([0.,-.35],0.,nav.config,arm_zero=True)
        nav.native.phase=native.phase='settle';state=self.state(velocity=np.array([.2,0.,0.]))
        new=nav.native.stability_checks(state);old=native.stability_checks(state)
        for k in old:
            if k!='arm_joints':self.assertEqual(new[k],old[k])
        self.assertFalse(new['planar_speed'])
    def test_arm_target_error_refused(self):
        nav=self.nav();nav.native.phase='settle'
        self.assertFalse(nav.native.stability_checks(self.state(arm_q=NAV_ARM+.2))['arm_joints'])
    def test_actual_observation_state_not_subtracted_or_faked(self):
        nav=self.nav();state=self.state();before=state.arm_q.copy();nav.native.stability_checks(state)
        self.assertTrue(np.array_equal(state.arm_q,before))
    def test_lateral_motion_does_not_command_turning_to_face_route(self):
        nav=self.nav();command=nav.update(self.state(xy=np.zeros(2)))
        self.assertLess(command[1],0.);self.assertEqual(command[0],0.);self.assertEqual(command[2],0.)
    def test_continuous_native_one_second_arrival_hold_still_required(self):
        nav=self.nav()
        for t in np.arange(1.,2.,.02):nav.update(self.state(time=t))
        self.assertFalse(nav.arrived)
        nav.update(self.state(time=2.));self.assertTrue(nav.arrived)

if __name__=='__main__':unittest.main()

class DynamicMarginRegression(unittest.TestCase):
    def run_case(self,target):
        from mujoco_zyh.stall_stow import select_reference
        limits=np.array([[-2.3562,2.3562],[.157,2.983],[-2.81865,-.14835],[-1.5705,1.5705],[-1.098,1.098],[-1.88496,1.88496]])
        q=target.copy();q[1]-=.00235;dq=np.zeros(6);dq[1]=-.39666
        return select_reference(target,target,np.zeros(6),q,dq,np.array([50.,50.,80.,30.,30.,20.]),np.array([3.,2.,3.,3.,2.5,1.]),np.zeros(6),np.array([20.,20.,15.,7.,5.,5.]),limits,dt=.005)
    def test_v1_measured_gait_transient_remains_refused_at_old_shallow_target(self):
        with self.assertRaises(RuntimeError):self.run_case(STOW_ARM)
    def test_deeper_target_has_forecast_margin_without_relaxing_screen(self):
        ref,rate,_=self.run_case(NAV_ARM)
        self.assertTrue(np.allclose(ref,NAV_ARM));self.assertTrue((abs(rate)<=.45).all())
