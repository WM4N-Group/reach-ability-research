"""Synthetic reporting fixtures, never physical episode evidence."""
import unittest
from evaluate_pilot import classify,summarize

class EvaluationTests(unittest.TestCase):
    def report(self):
        return dict(seed=120401,study_arm='E0',study_global_goal_se2=[-.25,0.,0.],physical_resets_after_initial=0,
            physics_samples=1,outcome='nav_push_stow_nav_target_stable',
            prospective_support_plan={'box_approach_preview':{'study_arm':'E0','query_id':'fixture'}},
            control_events=[dict(event='return_nav_requested_after_stowed_ready',goal=[-.25,0.,.28])],
            return_nav_final_state=dict(root_position=[-.25,0,.28],root_quaternion=[1,0,0,0],
                return_nav_stable_seconds=.5,retracted_ready=True,exit_stable_gates={'fixture':True}))
    def test_actual_registered_goal_and_execution_are_required(self):
        r=self.report();self.assertTrue(classify(r,{'seed':120401,'arm':'E0'})['primary_success'])
        r['control_events'][0]['goal']=[.26,0,.28]
        v=classify(r,{'seed':120401,'arm':'E0'})
        self.assertIsNone(v['primary_success']);self.assertEqual(v['native_outcome'],'nav_push_stow_nav_target_stable')
    def test_missing_report_is_unknown_not_filled_failure_or_success(self):
        self.assertIsNone(classify(None,{'seed':120401,'arm':'E0'})['primary_success'])
    def test_SDK_fixture_does_not_become_episode(self):
        r=self.report();r['physics_samples']=0
        self.assertIsNone(classify(r,{'seed':120401,'arm':'E0'})['primary_success'])
    def test_native_failure_remains_failure(self):
        r=self.report();r['outcome']='native_termination_during_push'
        self.assertFalse(classify(r,{'seed':120401,'arm':'E0'})['primary_success'])
    def test_all_registered_cases_retained_without_point_effect_on_incomplete(self):
        p=dict(seeds=[1,2,3,4],schedule=[dict(seed=s,arm=a) for s in [1,2,3,4] for a in ['E0','E1','E2','E3']])
        v=summarize(p,None,{})
        self.assertEqual(len(v['rows']),16);self.assertEqual(v['starts'],0)
        self.assertTrue(all(e is None for e in v['paired_effects'].values()))
        self.assertEqual(v['arms']['E0']['registered_success_bounds'],[0.,1.])

if __name__=='__main__':unittest.main()
