"""Keep source/geometry splits and exact one-shot collection contracts frozen."""
import copy,unittest
from mujoco_zyh.integrated_batch import plan,case_protocol,validate_case,check_split_plan,geometry_key
from mujoco_zyh.collect import validate_protocol

class BatchContracts(unittest.TestCase):
    def test_whole_geometry_groups_are_disjoint(self):
        self.assertEqual(check_split_plan(),dict(train=4,validation=2,test=2))
        keys=[geometry_key(r['geometry']) for r in plan()['cases']]
        self.assertEqual(len(keys),len(set(keys)))
    def test_split_seed_or_physics_changes_require_new_registered_plan(self):
        p=case_protocol(plan()['cases'][0]);validate_protocol(p)
        for key,value in [('role','test'),('seed',1),('automatic_retry',True),('reset_after_initial_allowed',1)]:
            q=copy.deepcopy(p);q[key]=value
            with self.assertRaises(ValueError):validate_case(q)
    def test_collectors_cannot_train_or_control_world_model(self):
        for row in plan()['cases']:
            p=case_protocol(row);validate_case(p)
            self.assertEqual(p['training_runs'],0);self.assertEqual(p['WM_forwards'],0)
            self.assertFalse(p['WM_control']);self.assertFalse(p['automatic_retry'])
            self.assertEqual(p['max_sim_seconds'],420)
            self.assertEqual(p['forecast_study_training_authorized'],row['role']=='train')
    def test_fixed_training_budget_never_selects_on_test(self):
        t=plan()['training'];self.assertEqual(t['updates'],1000)
        self.assertFalse(t['test_used_for_selection']);self.assertTrue(t['evaluate_test_once_after_checkpoint_frozen'])
        self.assertEqual(t['action_substeps_per_frame']*t['issued_action_channels'],1800)
