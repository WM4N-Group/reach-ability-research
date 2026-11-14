"""New target-domain mathematics, not a replica of owner's test suite."""
import unittest
from .ainav_target_domain import (goal_interval, in_interval, aligned_final_interval,
                                  support_projection, fixed_edge_baselines, receiver_stage)


class TargetDomainTests(unittest.TestCase):
    def test_native_interval_is_not_old_three_point_menu(self):
        r = goal_interval(5.48, offset=.11, drive_max=.8)
        self.assertAlmostEqual(r['upper_m'], 6.17)
        self.assertTrue(in_interval(6.15, r))
        self.assertAlmostEqual(6.15-5.48+.11, .78)
        self.assertNotIn(.78, (.2, .4, .6))

    def test_open_lower_closed_upper(self):
        r = goal_interval(1., offset=.125, drive_max=.875)
        self.assertFalse(in_interval(r['lower_m'], r))
        self.assertTrue(in_interval(r['upper_m'], r))
        self.assertFalse(in_interval(r['upper_m']+.01, r))

    def test_reject_invalid_numbers_and_geometry(self):
        for bad in (True, float('nan'), float('inf')):
            with self.assertRaises(ValueError): goal_interval(bad, offset=.11, drive_max=.8)
        with self.assertRaises(ValueError): goal_interval(0., offset=.9, drive_max=.8)
        with self.assertRaises(ValueError): support_projection([0., 0.], [1., 1., .2], [1., 0., -1., 1.], [0., 2., -1., 1.])

    def test_realized_error_slice_not_control_goal_domain(self):
        r = aligned_final_interval(6.15, offset=.11, public_tol=.02, dock_tol=.01, native_tol=.12)
        self.assertAlmostEqual(r['lower_error_m'], -.01)
        self.assertAlmostEqual(r['upper_error_m'], .01)
        self.assertFalse(r['lower_closed']); self.assertTrue(r['upper_closed'])
        self.assertIsNone(r['actual_native_ready'])

    def test_projection_does_not_reject_valid_gap_span_for_not_contained_box(self):
        r = support_projection([6.15, -1.15], [3.2, 1.6, .2], [-1.6, 7.4, -5.1, 2.9], [7.75, 13.55, -5.1, 2.9])
        self.assertGreater(r['source_contact_projection_area_m2'], 0.)
        self.assertAlmostEqual(r['source_to_receiver_span_margin_m'], 2.85)
        self.assertAlmostEqual(r['nominal_box_forward_face_x_m'], 7.75)
        self.assertIsNone(r['loaded_support_verified'])
        self.assertIsNone(r['collision_free_path_verified'])

    def test_no_contact_projection_is_not_a_load_certificate(self):
        r = support_projection([10., 0.], [1., 1., .2], [0., 2., -1., 1.], [10.5, 12., -1., 1.])
        self.assertFalse(r['source_contact_projection_nonempty'])
        self.assertLess(r['source_to_receiver_span_margin_m'], 0.)
        self.assertIsNone(r['loaded_support_verified'])

    def test_same_problem_singleton_baselines_agree(self):
        row = dict(public_goal_xy_m=[6.15, -1.15], receiver_front_x_m=7.75,
                   object_size_m=[3.2, 1.6, .2], declared_public_translation_m=.67,
                   initial_stroke_necessary_in_blueprint=True)
        r = fixed_edge_baselines(row)
        self.assertTrue(r['goals_agree']); self.assertEqual(r['genuine_continuous_goal_degrees_of_freedom'], 0)
        self.assertAlmostEqual(r['full_catalogue_enumeration_goal'], 6.15)
        self.assertFalse(r['dispatch']); self.assertIsNone(r['total_navigation_cost_s'])

    def test_blueprint_stroke_rejection_does_not_fill_task_cost(self):
        row = dict(public_goal_xy_m=[6.15, -1.15], receiver_front_x_m=7.75,
                   object_size_m=[3.2, 1.6, .2], declared_public_translation_m=1.17,
                   initial_stroke_necessary_in_blueprint=False)
        r = fixed_edge_baselines(row)
        self.assertTrue(r['goals_agree']); self.assertIsNone(r['nominal_joint_affine_elimination_goal'])
        self.assertIsNone(r['total_navigation_cost_s'])

    def test_later_nav_vs_climb_is_not_immediate_push_handover(self):
        ground = receiver_stage(0., .2, .2)
        raised = receiver_stage(.2, .2, .6)
        self.assertEqual(ground['nominal_skill_height_relation'], 'NAV_SAME_LAYER_HEIGHT_ONLY')
        self.assertEqual(raised['nominal_skill_height_relation'], 'CLIMB_UP_020_HEIGHT_ONLY')
        self.assertTrue(raised['immediate_after_PUSH_successor_is_separate'])
        self.assertIsNone(raised['native_ready'])

    def test_no_direct_040_climb_is_not_global_task_infeasibility(self):
        r = receiver_stage(0., .2, .6)
        self.assertEqual(r['nominal_skill_height_relation'], 'NO_DIRECT_CATALOGUE_NAV_OR_UP020_CLIMB_HEIGHT_MATCH')
        self.assertIsNone(r['support_connection_verified'])
        self.assertNotIn('global_task_infeasible', r)

    def test_cannot_silently_replace_catalogue_goal_by_interval_point(self):
        row = dict(public_goal_xy_m=[6.16, -1.15], receiver_front_x_m=7.75,
                   object_size_m=[3.2, 1.6, .2], declared_public_translation_m=.68,
                   initial_stroke_necessary_in_blueprint=True)
        with self.assertRaises(ValueError): fixed_edge_baselines(row)


if __name__ == '__main__': unittest.main()
