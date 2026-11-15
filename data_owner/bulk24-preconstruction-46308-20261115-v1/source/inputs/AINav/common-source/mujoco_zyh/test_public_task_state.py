import unittest
import numpy as np
from unittest.mock import patch
from mujoco_zyh.public_task_state import assemble_public_task_state,MACROS

class PublicTaskStateTests(unittest.TestCase):
    def sample(self,macro='WAIT',time=1.,declared=.4):
        rgb=np.zeros((32,48,3),np.uint8);depth=np.ones((32,48),np.float32);K=np.array([[24.,0,24],[0,24,16],[0,0,1.]])
        p=np.arange(45,dtype=np.float32)/10
        return assemble_public_task_state(rgb,depth,K,np.eye(4),p,time_s=time,declared_macro=macro,macro_declared_at_s=declared)
    def test_shared_current_state_retains_actual_proprio_mode_and_observed_age(self):
        r=self.sample();s=r['state'];self.assertEqual(s.shape,(69,));self.assertTrue(np.array_equal(s[:45],np.arange(45,dtype=np.float32)/10))
        self.assertEqual(s[45+MACROS.index('WAIT')],1.);self.assertAlmostEqual(float(s[60]),.6,places=6)
        self.assertFalse(r['geometry_valid']);self.assertTrue(np.array_equal(s[61:],np.zeros(8)))
        self.assertFalse(r['physical_action_admitted'])
    def test_missing_geometry_is_explicit_not_a_zero_distance_success(self):
        r=self.sample('NAV_STEP');self.assertFalse(r['geometry_valid']);self.assertEqual(r['state'][68],0.)
        self.assertIsNotNone(r['geometry_missing_reason'])
    def test_geometry_is_copied_only_from_current_public_descriptor(self):
        proposal=dict(candidates=[dict(appearance_family='green',frame_local_ref='visible0')],RGB_sha256='pixels')
        proof=dict(plane=dict(normal_body_xyz=[1.,0,0],plane_offset_body_m=.6,p90_inlier_residual_m=.001,inlier_fraction=.4))
        with patch('mujoco_zyh.public_task_state.propose_visual_candidates',return_value=proposal),patch('mujoco_zyh.public_task_state.describe_visible_goal',return_value=proof):r=self.sample('NAV_STEP')
        self.assertTrue(r['geometry_valid']);self.assertAlmostEqual(float(r['state'][65]),.6,places=6);self.assertEqual(r['state'][68],1.)
    def test_future_declared_control_time_or_unknown_macro_rejected(self):
        with self.assertRaises(ValueError):self.sample(declared=1.1)
        with self.assertRaises(ValueError):self.sample(macro='PRIVATE_BOX_MASS')
