"""Abstract algorithm tests only; NOT a T-COMPLEX scene/existence proof/demo."""
import unittest
from .finite_multistep_planner import Arc, propose, nominal_connection


class FiniteMultistepTests(unittest.TestCase):
    def run_policy(self, graph, method, **kw):
        return propose('root', arcs=lambda s:graph.get(s,()), is_goal=lambda s:s=='goal',
            state_key=lambda s:s, method=method, cost_unit='ABSTRACT_SOFTWARE_UNITS', **kw)

    def test_common_costs_and_three_transition_nominal_goal_not_native_success(self):
        graph={'root':(Arc('a','closed',1.,'POSSIBLE'),Arc('b','n1',2.,'POSSIBLE')),
               'n1':(Arc('c','n2',1.,'POSSIBLE'),), 'n2':(Arc('d','goal',1.,'POSSIBLE'),)}
        a=self.run_policy(graph,'greedy');b=self.run_policy(graph,'multistep')
        self.assertEqual(a['action'],'a');self.assertEqual(b['action'],'b')
        self.assertEqual(b['nominal_plan'],('b','c','d'));self.assertEqual(b['nominal_plan_cost'],4.)
        self.assertEqual(b['dynamic_success'],'UNKNOWN');self.assertFalse(b['execution_authorized'])
        self.assertFalse(b['actual_task_success_claimed'])

    def test_unknown_not_free_pass_and_incomplete_root_domain_abstains(self):
        graph={'root':(Arc('unknown','goal'),Arc('known','n1',2.,'POSSIBLE'))}
        out=self.run_policy(graph,'multistep');self.assertEqual(out['action'],'known')
        self.assertTrue(out['fallback_to_shared_greedy']);self.assertEqual(out['unknown_static_arcs'],1)
        self.assertIsNone(self.run_policy(graph,'multistep',max_transitions=1)['action'])
        direct=self.run_policy({'root':(Arc('direct','goal',1.,'POSSIBLE'),)},'multistep',max_transitions=1)
        self.assertEqual(direct['status'],'NOMINAL_GOAL_PLAN_NATIVE_GATES_REQUIRED')
        with self.assertRaises(ValueError):Arc('missing','goal',None,'POSSIBLE')

    def test_same_source_order_ties_cycle_bound_and_no_hindsight_route(self):
        graph={'root':(Arc('z','n1',1.,'POSSIBLE'),Arc('a','n2',1.,'POSSIBLE')),
               'n1':(Arc('loop','root',0.,'POSSIBLE'),)}
        a=self.run_policy(graph,'greedy');b=self.run_policy(graph,'multistep',max_depth=3)
        self.assertEqual(a['action'],'z');self.assertEqual(b['action'],'z')
        self.assertTrue(b['fallback_to_shared_greedy']);self.assertLessEqual(b['examined_transitions'],256)


    def test_shared_nominal_geometry_touch_block_and_unknown_envelope_not_native_pass(self):
        obstacles=((1.,0.,2.,1.),)
        unknown=nominal_connection((0.,0.),(3.,0.),obstacle_boxes_xyxy=obstacles)
        self.assertEqual(unknown['static_status'],'UNKNOWN')
        blocked=nominal_connection((0.,-.1),(3.,-.1),obstacle_boxes_xyxy=obstacles,footprint_radius_m=.1)
        self.assertEqual(blocked['static_status'],'REFUTED')
        clear=nominal_connection((0.,-1.),(3.,-1.),obstacle_boxes_xyxy=obstacles,footprint_radius_m=.1)
        self.assertEqual(clear['static_status'],'POSSIBLE');self.assertEqual(clear['dynamic_success'],'UNKNOWN')
        self.assertEqual(clear['nominal_robot_path_m'],3.)


if __name__=='__main__':unittest.main()
