import json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from mujoco_zyh.push_forecast_protocol import load_plan,case_protocol,validate_case,configure_probe
from mujoco_zyh.push_forecast_data import public_features,appearance
from mujoco_zyh.push_forecast_fit import fit,predict,metric

class PlanTests(unittest.TestCase):
    def test_exact20_unique_conditions_and_disjoint_roles(self):
        cases=load_plan()['cases'];self.assertEqual(len(cases),20)
        self.assertEqual(len({(c['mass_kg'],c['friction']) for c in cases}),20)
        self.assertEqual({s:sum(c['split']==s for c in cases) for s in ['train','validation','test']},{'train':10,'validation':4,'test':6})
    def test_new_case_exact_frozen_protocol(self):
        for c in load_plan()['cases']:validate_case(case_protocol(c))
    def test_role_mass_or_budget_cannot_change(self):
        p=case_protocol(load_plan()['cases'][0])
        for k,v in [('role','test'),('seed',1),('training_runs',1),('max_sim_seconds',999),('reset_after_initial_allowed',1)]:
            with self.subTest(k=k),self.assertRaises(ValueError):validate_case(dict(p,**{k:v}))
    def test_training_release_only_train_split(self):
        for c in load_plan()['cases']:
            p=case_protocol(c);self.assertEqual(p['training_allowed'],c['split']=='train');self.assertTrue(p['forecast_study_training_authorized'])
    def test_no_research_ID_or_alias_change(self):
        for c in load_plan()['cases']:
            p=case_protocol(c);self.assertEqual(p['selected_object_id'],'probe_object');self.assertEqual(p['scene_recipe'],'zyh_native_single_box')
    def test_nested_case_uses_canonical_resource_locks(self):
        self.assertEqual(case_protocol(load_plan()['cases'][0])['resource_lock_dir'],'/mnt/yuanyue/data/go2-piper-world-model')
    def test_pair_friction_not_only_geom(self):
        geom=SimpleNamespace(mass=1,friction=None);pair=SimpleNamespace(geomname1='push_box_geom',geomname2='ground',friction=None)
        spec=SimpleNamespace(geom=lambda n:geom,pairs=[pair]);configure_probe(spec,dict(mass_kg=3.,friction=.4))
        self.assertEqual(geom.mass,3.);self.assertEqual(pair.friction,[.4,.4,0,0,0])
    def test_missing_contact_pairs_rejected(self):
        with self.assertRaises(ValueError):configure_probe(SimpleNamespace(geom=lambda n:SimpleNamespace(),pairs=[]),dict(mass_kg=1.,friction=.2))

class CausalFeatures(unittest.TestCase):
    def data(self):
        return dict(rgb=np.full((8,128,192,3),80,dtype=np.uint8),depth=np.ones((8,128,192),np.float32),proprio=np.zeros((8,45)),actions=np.zeros((8,18)),times=np.arange(8)*.1,K=np.array([[48,0,96],[0,48,64],[0,0,1]]),mount=np.eye(4),past_commands=np.zeros((140,2,5,18)),elapsed_push_s=1.)
    def test_public_feature_finite_deterministic(self):
        a=self.data();x=public_features(**a);y=public_features(**a)
        self.assertTrue(np.array_equal(x[0],y[0]));self.assertTrue(np.isfinite(x[0]).all())
    def test_first_and_last_past_commands_affect_encoding(self):
        a=self.data();x=public_features(**a)[0]
        for i in (0,139):
            b=self.data();b['past_commands'][i,0,0,0]=.1
            self.assertFalse(np.array_equal(x,public_features(**b)[0]))
    def test_order_of_full_past_commands_matters(self):
        a=self.data();a['past_commands'][0,0,0,0]=1.;x=public_features(**a)[0]
        a['past_commands']=a['past_commands'][::-1].copy();self.assertFalse(np.array_equal(x,public_features(**a)[0]))
    def test_future_command_or_private_truth_not_accepted(self):
        a=self.data()
        with self.assertRaises(TypeError):public_features(**a,mass_kg=20)
        with self.assertRaises(TypeError):public_features(**a,future_RGB=np.zeros(1))
    def test_missing_or_extra_motor_steps_rejected(self):
        for n in (139,141):
            a=self.data();a['past_commands']=np.zeros((n,2,5,18))
            with self.assertRaises(ValueError):public_features(**a)
    def test_sparse_clock_gap_not_tiled_history(self):
        a=self.data();a['times'][3]=a['times'][2]
        with self.assertRaises(ValueError):public_features(**a)
    def test_image_changes_encoding(self):
        a=self.data();x=public_features(**a)[0];a['rgb'][:]=0;self.assertFalse(np.array_equal(x,public_features(**a)[0]))
    def test_missing_visual_proxy_explicit_zero_and_mask(self):
        a=self.data();x=public_features(**a);self.assertFalse(x[3]);self.assertTrue((x[2]==0).all())

class Fits(unittest.TestCase):
    def test_fit_scaling_train_only_predict_no_refit(self):
        x=np.array([[0.,0.],[1.,0.],[2.,0.]]);y=np.tile(x[:,:1],(1,4));m=fit(x,y,.001);before={k:v.copy() for k,v in m.items()};predict(m,np.array([[100.,100.]]))
        self.assertTrue(all(np.array_equal(m[k],v) for k,v in before.items()));self.assertTrue(np.isfinite(m['scale']).all())
    def test_regression_learns_nonconstant_consequence(self):
        x=np.arange(20).reshape(-1,1)/20;y=np.tile(x,(1,4));m=fit(x,y,.0001)
        self.assertLess(metric(y,predict(m,x))['vector_RMSE_m'],.01)
    def test_baseline_metric_horizon_shape(self):
        m=metric(np.zeros((2,4)),np.ones((2,4))*.1);self.assertEqual(len(m['per_horizon_vector_RMSE_m']),2)

if __name__=='__main__':unittest.main()
