import math
import unittest
from .selected_ainav_baseline import (box_center_preimage, contains,
                                    interval_stroke_relation, direct_entry_pullback)


class SelectedV6DemandTests(unittest.TestCase):
    def test_selected_goal_preimages(self):
        for goal, lo, hi in ((2.3, 1.61, 2.41), (9.2, 8.51, 9.31)):
            r = box_center_preimage(goal)
            self.assertAlmostEqual(r['lower_m'], lo); self.assertAlmostEqual(r['upper_m'], hi)
            self.assertTrue(contains(r, r['lower_m'])); self.assertFalse(contains(r, r['upper_m']))

    def test_no_bound_means_unknown_even_with_nominal_numbers(self):
        r = interval_stroke_relation(2.3, [1.7, 1.8])
        self.assertEqual(r['relation'], 'UNKNOWN'); self.assertFalse(r['dispatch'])
        self.assertIsNone(r['actual_native_ready'])

    def test_interval_all_partial_and_none(self):
        f = lambda values: interval_stroke_relation(2.3, values, independent_bound_available=True)['relation']
        self.assertEqual(f([1.7, 1.8]), 'ALL_NUMERIC_STROKES_WITHIN_DOMAIN_IN_SUPPLIED_BOUND')
        self.assertEqual(f([1.5, 1.8]), 'PARTIAL_NUMERIC_STROKE_MATCH_IN_SUPPLIED_BOUND')
        self.assertEqual(f([2.5, 2.6]), 'NO_NUMERIC_STROKE_MATCH_IN_SUPPLIED_BOUND')

    def test_joint_pose_and_drive_sets_can_each_exist_but_not_intersect(self):
        r = direct_entry_pullback(2.3, box_length=2.4, lane_y=-2., base_xy=[-1., -2.])
        self.assertIsNotNone(r['direct_pose_box_center_interval'])
        self.assertIsNotNone(r['numeric_drive_box_center_interval'])
        self.assertIsNone(r['joint_direct_box_center_interval'])
        self.assertTrue(r['original_NAV_preparation_not_ruled_out'])
        self.assertIsNone(r['whole_task_infeasible'])

    def test_joint_intersection_at_ready_approach(self):
        r = direct_entry_pullback(2.3, box_length=2.4, lane_y=-2., base_xy=[-.08, -2.])
        self.assertTrue(contains(r['joint_direct_box_center_interval'], 1.7))
        self.assertFalse(r['physical_dispatch'])

    def test_lateral_boundary_and_outside(self):
        # Exactly representable geometry for boundary inclusion.
        r = direct_entry_pullback(2., box_length=1., lane_y=0., base_xy=[1., .125], radius=.125)
        pose = r['direct_pose_box_center_interval']
        self.assertEqual(pose['lower_m'], pose['upper_m'])
        r = direct_entry_pullback(2., box_length=1., lane_y=0., base_xy=[1., .126], radius=.125)
        self.assertIsNone(r['direct_pose_box_center_interval'])

    def test_invalid_numbers_or_bound_shape_rejected(self):
        for bad in (True, float('inf'), float('nan')):
            with self.assertRaises(ValueError): box_center_preimage(bad)
        with self.assertRaises(ValueError): interval_stroke_relation(2.3, [2., 1.], independent_bound_available=True)
        with self.assertRaises(ValueError): direct_entry_pullback(2.3, box_length=0., lane_y=0., base_xy=[0., 0.])


if __name__ == '__main__': unittest.main()
