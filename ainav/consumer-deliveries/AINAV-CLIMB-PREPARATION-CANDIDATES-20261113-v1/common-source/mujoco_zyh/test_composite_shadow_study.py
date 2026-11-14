"""CPU contracts for fresh composite collection and causal training labels."""
import unittest

import numpy as np

from mujoco_zyh.collect import validate_protocol
from mujoco_zyh.composite_shadow_study import case_protocol,plan
from mujoco_zyh.composite_shadow_fit import body_xy_delta,clock_fit,clock_predict,same_option,score


class CompositeShadowContracts(unittest.TestCase):
    def test_exact_five_fresh_roles_and_training_release(self):
        cases=plan()['cases']
        self.assertEqual([sum(c['role']==r for c in cases) for r in ('train','validation','test')],[3,1,1])
        self.assertEqual(len({c['seed'] for c in cases}),5)
        for case in cases:
            p=case_protocol(case)
            self.assertEqual(validate_protocol(p),p)
            self.assertEqual(p['training_allowed'],case['role']=='train')
            self.assertEqual(p['forecast_study_training_authorized'],case['role']=='train')
            self.assertEqual(p['resource_lock_dir'],'/mnt/yuanyue/data/go2-piper-world-model')
            self.assertFalse(p['automatic_retry'])
            self.assertEqual(p['reset_after_initial_allowed'],0)

    def test_case_mutation_rejected(self):
        p=case_protocol(plan()['cases'][0])
        for key,value in [('seed',1),('role','test'),('scene_recipe','research_threebox'),('resource_lock_dir','/tmp'),('training_allowed',False)]:
            with self.subTest(key=key),self.assertRaises(ValueError):validate_protocol(dict(p,**{key:value}))

    def test_skill_boundary_censors_future(self):
        b=[dict(skill='nav',task_index=0)]*3+[dict(skill='push',task_index=1)]*3
        self.assertTrue(same_option(b,0,2))
        self.assertFalse(same_option(b,1,3))

    def test_body_frame_uses_measured_rotation_and_height(self):
        rotation=np.array([[0.,-1.,0.],[1.,0.,0.],[0.,0.,1.]])
        self.assertEqual(body_xy_delta([0,0,0],[1,0,1],rotation),[0.,-1.])

    def test_train_only_skill_clock_and_episode_score(self):
        data=dict(skill=np.array([0,0,1]),clock=np.array([0.,1.,0.]),y=np.array([[0.]*8,[1.]*8,[2.]*8]))
        model=clock_fit(data,np.ones(3))
        q=dict(skill=np.array([0,1]),clock=np.array([.8,.1]))
        self.assertTrue(np.array_equal(clock_predict(model,q),data['y'][[1,2]]))
        self.assertEqual(score(data['y'],data['y'],np.array(['a','a','b']))['episode_equal_vector_RMSE_m'],0.)


if __name__=='__main__':unittest.main()
