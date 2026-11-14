"""Preparation CPU tests, not collected-data/model effectiveness evidence."""
import ast,inspect,unittest
from pathlib import Path
import numpy as np
from mujoco_zyh.option_probe import load_plan,case_protocol,validate_case
from mujoco_zyh.option_forecast_fit import clock_fit,clock_predict,score

class RegisteredFreshStudy(unittest.TestCase):
    def test_split_is_independent_cases_not_windows(self):
        cases=load_plan()['cases'];self.assertEqual(len(cases),12);self.assertEqual(len({c['case_id'] for c in cases}),12)
        self.assertEqual([sum(c['role']==r for c in cases) for r in ('train','validation','test')],[6,3,3])
    def test_only_new_train_cases_authorized(self):
        for c in load_plan()['cases']:
            p=case_protocol(c);self.assertEqual(p['training_allowed'],c['role']=='train');self.assertEqual(p['forecast_study_training_authorized'],c['role']=='train');validate_case(p)
    def test_changed_case_or_geometry_refused(self):
        p=case_protocol(load_plan()['cases'][0]);p['initial_probe_geometry']['initial_box_dx_m']+=.001
        with self.assertRaises(ValueError):validate_case(p)
    def test_no_mass_or_color_features(self):
        from mujoco_zyh.push_forecast_data import public_features
        names=set(inspect.signature(public_features).parameters)
        self.assertFalse(names & {'mass','friction','private_pose','object_id','future_action'})
        self.assertTrue(all(c['box_appearance']=='identical_no_mass_color_encoding' for c in load_plan()['cases']))
    def test_only_two_static_model_review_sentinels(self):
        self.assertEqual(sum(case_protocol(c)['full_state_review'] for c in load_plan()['cases']),2)
        self.assertLessEqual(load_plan()['budgets']['total_dynamic_payload_cap_bytes'],512*1024**2)
    def test_train_function_never_loads_test(self):
        from mujoco_zyh.option_forecast_fit import train
        tree=ast.parse(inspect.getsource(train))
        for node in ast.walk(tree):
            if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=='read':self.assertNotEqual(node.args[1].value,'test')
    def test_clock_control_fit_uses_only_supplied_training_rows(self):
        data=dict(clock=np.array([.01,.11]),y=np.array([[0,0,0,0,0,0],[1,0,2,0,1,1]],dtype=float))
        model=clock_fit(data,np.ones(2));pred=clock_predict(model,np.array([.1]))
        self.assertTrue(np.array_equal(pred,data['y'][1:2]))
    def test_joint_displacement_risk_score_shapes(self):
        y=np.zeros((3,6));pred=np.zeros((3,6));s=score(y,pred,np.array(['a','b','c']))
        self.assertEqual(s['episode_equal_RMSE_m'],0.);self.assertEqual(s['episode_equal_Brier'],0.)

if __name__=='__main__':unittest.main()
