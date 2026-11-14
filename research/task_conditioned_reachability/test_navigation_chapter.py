"""Selector/ablation unit fixtures, NOT navigation episodes or physical evidence."""
import copy
import sys
import unittest

from navigation_goal_bridge import select_shadow_goal, as_original_shadow_action
from analyze_state_height_ablations import ablations_for_state


def packet():
    def row(cid, cost, endpoint, path):
        return dict(candidate_id=cid, observed_state_id='synthetic_fixture_state', model_body_height_m=.28,
                    target_se2_world=[cost, 0, 0], route_status='reachable', navigation_cost=cost,
                    task_pose_status='found', endpoint_rho=endpoint, path_rho=path,
                    analytic_necessary_excluded=False)
    return dict(schema='reachability-navigation-shadow-query-v1',
                observed_state_id='synthetic_fixture_state', observed_body_height_m=.28,
                data_role='synthetic_unit_fixture_NOT_robot_episode',
                navigation_cost_source=dict(kind='original_planner_route_cost', sha256='a'*64),
                candidates=[row('near', .1, .5, -.2), row('offset', .3, .4, .4)])


class NavigationBridgeTests(unittest.TestCase):
    def test_ablations_same_input_and_original_NAV_action_type_only(self):
        p = packet()
        before = copy.deepcopy(p)
        self.assertEqual(select_shadow_goal(p, 'nav_only')['candidate_id'], 'near')
        self.assertEqual(select_shadow_goal(p, 'endpoint')['candidate_id'], 'near')
        shadow = select_shadow_goal(p, 'path')
        self.assertEqual(shadow['candidate_id'], 'offset')
        self.assertFalse(shadow['execution_authorized'])
        self.assertIsNone(shadow['actual_navigation_success'])
        action = as_original_shadow_action(shadow)
        self.assertIs(type(action), sys.modules['reconfigurable_navigation.representations'].SkillAction)
        self.assertNotIn('reconfigurable_navigation.locomotion_runtime', sys.modules)
        self.assertEqual(action.skill.name, 'NAV')
        self.assertEqual(action.target_pose.shape, (3,))
        self.assertEqual(p, before)

    def test_no_static_reference_cost_disguised_as_navigation_cost(self):
        p = packet()
        p['navigation_cost_source']['kind'] = 'static_alignment_and_direction_fraction'
        r = select_shadow_goal(p)
        self.assertEqual(r['status'], 'not_ready')
        self.assertIn('actual_original_planner_route_cost_and_source', r['missing'])

    def test_no_cross_height_choice_or_new_body_height_action(self):
        p = packet()
        p['candidates'][1]['model_body_height_m'] = .33
        with self.assertRaisesRegex(ValueError, 'height is not an action'):
            select_shadow_goal(p)
        p = packet()
        p['candidates'][0]['target_se2_world'] = [0, 0, 0, .28]
        with self.assertRaisesRegex(ValueError, 'SE2'):
            select_shadow_goal(p)

    def test_no_stale_state_mix(self):
        p = packet()
        p['candidates'][0]['observed_state_id'] = 'other_state'
        with self.assertRaisesRegex(ValueError, 'share observed state'):
            select_shadow_goal(p)

    def test_missing_route_cost_domain_is_unknown_not_silently_dropped(self):
        p = packet()
        p['candidates'][0]['route_status'] = 'unknown'
        r = select_shadow_goal(p)
        self.assertEqual(r['status'], 'unknown_navigation_cost_domain')
        self.assertIsNone(r['candidate_id'])
        self.assertEqual(r['missing_route_ids'], ['near'])

    def test_bounded_solver_miss_kept_unknown_NOT_physical_failure(self):
        p = packet()
        p['candidates'][0]['task_pose_status'] = 'bounded_solver_miss_UNKNOWN'
        r = select_shadow_goal(p)
        self.assertEqual(r['candidate_id'], 'offset')
        self.assertEqual(r['unknown_candidate_ids'], ['near'])
        self.assertIsNone(r['actual_navigation_success'])

    def test_analytic_contradiction_stops_instead_of_dropping_positive_witness(self):
        p = packet()
        p['candidates'][0]['analytic_necessary_excluded'] = True
        with self.assertRaisesRegex(ValueError, 'contradicts'):
            select_shadow_goal(p)

    def test_all_infeasible_or_unknown_does_not_make_success(self):
        p = packet()
        for r in p['candidates']:
            r['path_rho'] = None
        result = select_shadow_goal(p)
        self.assertEqual(result['status'], 'abstain_no_known_nominal_candidate')
        self.assertEqual(result['unknown_candidate_ids'], ['near', 'offset'])
        with self.assertRaises(ValueError):
            as_original_shadow_action(result)

    def test_duplicate_or_nonfinite_cost_rejected(self):
        p = packet()
        p['candidates'][1]['candidate_id'] = 'near'
        with self.assertRaisesRegex(ValueError, 'unique'):
            select_shadow_goal(p)
        p = packet()
        p['candidates'][0]['navigation_cost'] = float('nan')
        with self.assertRaisesRegex(ValueError, 'finite'):
            select_shadow_goal(p)

    def test_static_ablation_never_populates_actual_success_or_measured_speedup(self):
        row = dict(candidate_id='synthetic', body_position_world_m=[0, 0, .28], body_yaw_rad=0,
                   common_reference_cost=.5, wide_fraction13=0, task_IK_found=False,
                   height_necessary_bound=dict(exclusion_gap_m=.01), queries=[{}]*13)
        a = ablations_for_state([row], .28)
        self.assertEqual(a['arms'][0]['selected']['candidate_id'], 'synthetic')
        self.assertIsNone(a['arms'][0]['selected']['actual_navigation_success'])
        self.assertEqual(a['actual_queries_saved_in_recorded_run'], 0)
        self.assertEqual(a['counterfactual_shared_queries_on_excluded_candidates'], 13)
        self.assertEqual(a['arms'][-1]['selected']['status'], 'abstain')


if __name__ == '__main__':
    unittest.main()
