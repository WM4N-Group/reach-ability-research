"""Pure CPU NAV adaptation checks with byte-pinned original arrival predicates."""
from dataclasses import replace
import importlib.util
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
import numpy as np
from mujoco_zyh.nav_efficiency import EfficientNav,install,MODE,SPEED_LIMITS,MIN_SPEEDS
from mujoco_zyh.collect import validate_protocol

BUNDLE=Path(os.environ['ZYH_BUNDLE'])
sys.path.insert(0,str(BUNDLE/'nav'))
spec=importlib.util.spec_from_file_location('_wm_native_navigation',BUNDLE/'nav/navigation.py')
module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)


def state(t,xy=(0.,0.),yaw=0.,velocity=(0.,0.,0.),arm_speed=0.):
    return module.NavState(t,np.array(xy),yaw,np.array(velocity),np.zeros(6),np.full(6,arm_speed),0.)


def controller(goal=(1.,0.)):
    cfg=replace(module.profile_nav_config('skills'),warmup_seconds=.24)
    return EfficientNav(module.NavSkill(goal,0.,cfg,arm_zero=True))


class NavCPU(unittest.TestCase):
    def test_original_arrival_parameters_not_relaxed(self):
        nav=controller();self.assertEqual(nav.config.hold_seconds,1.)
        self.assertEqual(nav.config.arm_stopped_speed,.2);self.assertEqual(nav.config.position_tolerance,.13)
        self.assertEqual(nav.config.yaw_tolerance,.25)
    def test_backward_target_uses_backward_without_turn(self):
        nav=controller((-1.,0.));v=nav.update(state(.24));self.assertLess(v[0],0.);self.assertEqual(v[2],0.)
    def test_sideways_target_no_bearing_turn(self):
        nav=controller((0.,2.));v=nav.update(state(.24));self.assertGreater(v[1],0.);self.assertEqual(v[2],0.)
    def test_velocity_envelope_and_source_nonzero_minimums(self):
        nav=controller((10.,10.));prev=np.zeros(3)
        for i in range(200):
            v=nav.update(state(.24+i*.02,yaw=-1.))
            self.assertTrue((abs(v)<=SPEED_LIMITS+1e-10).all());self.assertTrue(((abs(v)<1e-12)|(abs(v)>=MIN_SPEEDS-1e-10)).all());prev=v
    def test_actual_stable_one_second_required(self):
        nav=controller((0.,0.));nav.update(state(0.))
        for i in range(1,200):nav.observe(state(i*.005))
        self.assertFalse(nav.arrived);nav.observe(state(1.));self.assertTrue(nav.arrived)
    def test_actual_arm_velocity_violation_restarts_original_hold(self):
        nav=controller((0.,0.));nav.update(state(0.))
        nav.observe(state(.9,arm_speed=.21));self.assertFalse(nav.arrived)
        nav.observe(state(.905));nav.observe(state(1.9));self.assertFalse(nav.arrived)
        nav.observe(state(1.905));self.assertTrue(nav.arrived)
    def test_warmup_zero_not_faked_forward(self):
        self.assertTrue((controller().update(state(0.))==0).all())
    def test_clock_gap_rejected(self):
        nav=controller();nav.update(state(0.))
        with self.assertRaisesRegex(ValueError,'clock gap'):nav.update(state(.1))
    def test_invalid_actual_state_rejected(self):
        with self.assertRaises(ValueError):controller().update(state(.24,yaw=float('nan')))
    def test_15s_censor_instead_of_32s_wait(self):
        with self.assertRaisesRegex(RuntimeError,'15s'):controller().update(state(15.01))
    def test_repeated_goal_chasing_censors(self):
        nav=controller((0.,0.))
        for i in range(6):
            if i==5:
                with self.assertRaisesRegex(RuntimeError,'reacquisition'):nav.update(state(.24+i*.02,xy=(.2,0.)))
            else:nav.update(state(.24+i*.02,xy=(0.,0.) if i%2==0 else (.2,0.)))
    def test_original_protocol_default_unchanged(self):
        old=json.loads(Path(__file__).with_name('composite_review_protocol_v1.json').read_text())
        self.assertNotIn('nav_efficiency_mode',validate_protocol(old))
    def test_new_protocol_explicit_about_own_method_and_gain(self):
        p=json.loads(Path(__file__).with_name('nav_efficiency_protocol_v2.json').read_text());validate_protocol(p)
        for k,v in [('source_control_algorithms_changed',False),('NAV_arm_joint5_kd',1.),('nav_efficiency_mode','unknown')]:
            bad=dict(p,**{k:v})
            with self.assertRaises(ValueError):validate_protocol(bad)
    def test_install_only_copies_gain_command_not_mutates_native_command(self):
        class Command:
            def __init__(self,*a):self.position,self.velocity,self.kp,self.kd,self.feedforward=a
        original=Command(np.zeros(18),np.zeros(18),np.ones(18),np.ones(18),np.zeros(18))
        r=SimpleNamespace(make_nav=lambda item:module.NavSkill(item['goal'],item['yaw'],arm_zero=True),nav_command=lambda:original,Command=Command)
        tasks=[dict(skill='nav',goal=g,yaw=3.14) for g in [[-.02,-2.],[-.4,-2.],[-.4,0.],[-.08,0.]]]
        p=json.loads(Path(__file__).with_name('nav_efficiency_protocol_v2.json').read_text());new=install(r,tasks,p);self.assertNotIsInstance(r.make_nav(new[0]),EfficientNav);self.assertEqual(r.nav_command().kd[16],1.);r.make_nav(new[1]);cmd=r.nav_command()
        self.assertEqual(original.kd[16],1.);self.assertEqual(cmd.kd[16],2.5)
        self.assertTrue(np.array_equal(np.delete(cmd.kd,16),np.delete(original.kd,16)))
        self.assertTrue(all(t['yaw']==0. for t in new));self.assertTrue(all(t['yaw']==3.14 for t in tasks))
        self.assertIsInstance(r.make_nav(new[1]),EfficientNav)
    def test_install_noop_without_opt_in(self):
        tasks=[];self.assertIs(install(None,tasks,{}),tasks)


if __name__=='__main__':unittest.main()
