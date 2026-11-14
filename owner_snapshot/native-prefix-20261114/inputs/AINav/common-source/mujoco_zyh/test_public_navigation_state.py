import unittest
import numpy as np
from mujoco_zyh.public_navigation_state import PublicNavigationState

class PublicOdometryTests(unittest.TestCase):
    def proprio(self,velocity=(0,0,0),yaw_rate=0.):
        p=np.zeros(45);p[38]=-1.;p[41]=yaw_rate;p[42:]=velocity;return p
    def test_constant_observed_velocity_and_declared_goal_body_reference(self):
        s=PublicNavigationState();p=self.proprio((1,0,0))
        s.update(0.,p)
        for i in range(1,11):state=s.update(i*.1,p)
        self.assertTrue(np.allclose(state,[.92,0,0]));self.assertTrue(np.allclose(s.goal_body_xy([1.92,1.]),[1.,1.]))
    def test_integrated_yaw_rotates_body_velocity_and_goal_without_true_pose(self):
        s=PublicNavigationState();p=self.proprio((0,0,0),1.)
        for i in range(11):s.update(i*.1,p)
        self.assertAlmostEqual(s.yaw,1.);self.assertTrue(np.allclose(s.goal_body_xy([.92,0]),[np.cos(1.),-np.sin(1.)]))
    def test_future_perturbations_never_change_past_estimates(self):
        def trajectory(change):
            s=PublicNavigationState();out=[]
            for i in range(11):out.append(s.update(i*.1,self.proprio((10 if change and i>=6 else 1,0,0))))
            return np.array(out)
        original=trajectory(False);changed=trajectory(True)
        self.assertTrue(np.array_equal(original[:6],changed[:6]));self.assertFalse(np.array_equal(original[-1],changed[-1]))
    def test_missing_duplicate_rebased_or_nonpublic_inputs_rejected(self):
        p=self.proprio();s=PublicNavigationState()
        with self.assertRaises(ValueError):s.update(.1,p)
        s.update(0.,p)
        with self.assertRaises(ValueError):s.update(0.,p)
        with self.assertRaises(ValueError):s.update(.2,p)
        with self.assertRaises(ValueError):s.update(.1,np.zeros(46))
        with self.assertRaises(ValueError):s.update(.1,np.zeros(45))
