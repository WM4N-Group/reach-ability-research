import copy
import unittest
from mujoco_zyh.five_scene_suite import plan,case_protocol,validate_protocol

class SuiteContracts(unittest.TestCase):
    def test_five_distinct_geometries_and_real_gap_not_initially_bridged(self):
        cases=plan()['cases'];self.assertEqual(len(cases),5)
        self.assertEqual(len({c['case_id'] for c in cases}),5)
        self.assertEqual({c['family'] for c in cases},{'side_platform','stairs','bridge'})
        for c in cases:
            if c['family']=='bridge':
                initial_end=.5+c['box_length_m']
                self.assertLess(initial_end,c['gap_near_x_m'])
                self.assertGreater(initial_end+c['push_distance_m'],c['gap_near_x_m']+c['gap_width_m']+.1)
                self.assertGreater(c['finish_x_m']-.25,c['gap_near_x_m']+c['gap_width_m'])
    def test_exact_protocols_reject_geometry_or_budget_change(self):
        from mujoco_zyh.collect import validate_protocol as dispatch
        for c in plan()['cases']:
            p=case_protocol(c);self.assertEqual(dispatch(p),p)
            p=copy.deepcopy(p);p['suite_case']['box_mass_kg']=2.
            with self.assertRaises(ValueError):validate_protocol(p)
    def test_low_platform_revision_has_real_side_clearance(self):
        c=next(c for c in plan(2)['cases'] if c['case_id']=='platform12-shortlane')
        self.assertGreater(abs(c['push_lane_y_m'])-.6-c['platform_width_m']/2,.05)
        p=case_protocol(c,2);self.assertEqual(validate_protocol(p)['suite_revision'],2)

    def test_easy_ramp_cannot_bypass_gap_and_remains_an_actual_push_task(self):
        cases=plan(5)['cases']
        self.assertEqual(sum(c['family']=='side_platform' for c in cases),3)
        for c in cases:
            validate_protocol(case_protocol(c,5))
            if c['family']=='bridge':
                self.assertLess(c['ramp_landing_end_x_m'],c['gap_near_x_m']-.1)
                self.assertLess(.5+c['box_length_m'],c['gap_near_x_m'])

    def test_construction_goal_is_declared_before_physics_and_does_not_claim_crossing(self):
        for c in plan(6)['cases']:
            validate_protocol(case_protocol(c,6))
            if c['family']=='bridge':
                self.assertEqual(c['bridge_goal'],'construction_and_stow')
                self.assertFalse(c['ramp_entry'])

    def test_fresh_bootstrap_roles_are_training_only_and_readiness_bound(self):
        for c in plan(7)['cases']:
            p=case_protocol(c,7);validate_protocol(p)
            self.assertEqual(p['role'],'train');self.assertTrue(p['training_allowed'])
            self.assertNotIn('five-easy-',p['source_id'])
            self.assertEqual(len(p['readiness']['sha256']),64)
            p['readiness']=dict(p['readiness'],sha256='0'*64)
            with self.assertRaises(ValueError):validate_protocol(p)

    def test_platform20_supplement_restores_native_entry_and_is_one_case_only(self):
        from mujoco_zyh.five_scene_suite import machine_type
        class Native:pass
        c=plan(8)['cases'][0];p=case_protocol(c,8);validate_protocol(p)
        self.assertIs(machine_type(Native,p),Native)
        with self.assertRaises(ValueError):validate_protocol(case_protocol(plan(8)['cases'][1],8))

    def test_complete_route_recording_and_no_training_before_feasibility(self):
        for c in plan()['cases']:
            p=case_protocol(c);self.assertTrue(p['full_state_review'])
            self.assertEqual(p['training_runs'],0);self.assertFalse(p['WM_control'])
            self.assertEqual(p['reset_after_initial_allowed'],0);self.assertFalse(p['automatic_retry'])

if __name__=='__main__':unittest.main()
