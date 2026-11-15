import unittest
import numpy as np
from unittest.mock import patch
from mujoco_zyh.task_boundary_request import FirstNAVBoundaryRequest

class BoundaryRequestTests(unittest.TestCase):
    def packet(self,tick):
        return dict(rgb=np.zeros((1,1,32,48,3),np.uint8),depth_m=np.ones((1,1,32,48,1),np.float32),camera_K=np.array([[[24.,0,24],[0,24,16],[0,0,1.]]]),T_base_optical=np.eye(4)[None],proprio=np.zeros((1,1,45),np.float32),actions_previous=np.zeros((1,1,18),np.float32),action_valid=np.array([[tick>0]]),timestamps_s=np.array([[tick*.02]]))
    def request(self):
        def state(raw,m,s,**kw):
            out=np.zeros(124,np.float32);out[:69]=raw;out[69:114]=kw.get('fresh_body',raw[:45]);out[115]=kw.get('rgb_age',0.);return out
        def action(macro,dx=0.,dt=.1):
            a=np.zeros(20,np.float32);a[4 if macro=='PUSH_B' else 5]=1;a[15]=dx/.1;a[19]=dt;return a
        r=FirstNAVBoundaryRequest(dict(mean=[0.]*45,scale=[1.]*45),state,action)
        for tick in [0,5,10]:r.append_acquired(self.packet(tick),declared_macro='PUSH_B',macro_declared_at_s=0.)
        return r
    def build(self,r,**kw):
        defaults=dict(decision_time_s=.22,actual_public_body=np.ones(45,np.float32),body_observed_at_s=.22,known_B_completion=dict(time=.22,event='B_native_goal_and_original_finish_complete',stage='A_FAIL_RECOVER_RESELECT_B'));defaults.update(kw)
        proposals=dict(candidates=[dict(appearance_family='green',frame_local_ref='green0')],RGB_sha256='rgb')
        proof=dict(RGB_sha256='rgb',plane=dict(normal_body_xyz=[1.,0,0],plane_offset_body_m=.6,p90_inlier_residual_m=.001,inlier_fraction=.4))
        with patch('mujoco_zyh.task_boundary_request.propose_visual_candidates',return_value=proposals),patch('mujoco_zyh.task_boundary_request.describe_visible_goal',return_value=proof):return r.build(**defaults)
    def test_mixed_rate_context_and_first08s_do_not_relabel_observed_phase(self):
        r=self.request();out=self.build(r);arrays=out['context_arrays']
        self.assertEqual(set(arrays),{'rgb_context','state_context','past_declared_actions'})
        self.assertTrue(np.all(arrays['state_context'][:,49]==1.));self.assertTrue(np.all(arrays['state_context'][:,50]==0.))
        self.assertAlmostEqual(out['provenance']['first_prediction_interval_s'],.08)
        self.assertTrue(np.allclose(out['candidate_declared_actions'][:,0,19],.08));self.assertTrue(np.allclose(out['candidate_declared_actions'][:,1:,19],.1))
        self.assertFalse(out['provenance']['physical_action_dispatched'])
    def test_future_or_stale_body_and_nonregistered_candidates_rejected(self):
        r=self.request()
        for kw in [dict(body_observed_at_s=.24),dict(body_observed_at_s=.18),dict(candidate_dx_m=(0.,)),dict(known_B_completion=dict(time=.3,event='B_native_goal_and_original_finish_complete',stage='A_FAIL_RECOVER_RESELECT_B'))]:
            with self.assertRaises(ValueError):self.build(r,**kw)
    def test_no_mid_episode_reset_missing_frames_or_private_packet_keys(self):
        r=self.request()
        with self.assertRaises(ValueError):r.append_acquired(self.packet(25),declared_macro='PUSH_B',macro_declared_at_s=0.)
        p=self.packet(15);p['true_base_pose']=np.zeros(7)
        with self.assertRaises(ValueError):r.append_acquired(p,declared_macro='PUSH_B',macro_declared_at_s=0.)
