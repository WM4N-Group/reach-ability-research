"""Synthetic checks for base-collider height and fixed-point rate projection."""

import math
import unittest

import numpy as np

from analyze_piper_base_geometry_projection import projected_state


class BaseGeometryProjectionTests(unittest.TestCase):
    def test_lowest_vertex_and_fixed_point_rate_are_distinct(self):
        state = {
            "base_pos": [0.0, 0.0, 0.3],
            "base_quat": [1.0, 0.0, 0.0, 0.0],
            "base_vel_w": [0.0, 0.0, -0.2],
            "base_omega_w": [0.0, -0.5, 0.0],
        }
        result = projected_state(state, np.array([[1.0, 0.0, 0.0],
                                                   [0.0, 0.0, -0.1]]), 0)
        self.assertEqual(result["active_vertex"], 1)
        self.assertAlmostEqual(result["minimum_height_m"], 0.2)
        self.assertAlmostEqual(result["fixed_height_m"], 0.3)
        self.assertAlmostEqual(result["fixed_height_rate_m_s"], 0.3)

    def test_attitude_rotates_body_vertex_into_world_height(self):
        state = {
            "base_pos": [0.0, 0.0, 1.2],
            "base_quat": [math.sqrt(0.5), 0.0, math.sqrt(0.5), 0.0],
            "base_vel_w": [0.0, 0.0, 0.0],
            "base_omega_w": [0.0, 0.0, 0.0],
        }
        result = projected_state(state, np.array([[1.0, 0.0, 0.0],
                                                   [0.0, 0.0, 0.0]]), 0)
        self.assertEqual(result["active_vertex"], 0)
        self.assertAlmostEqual(result["minimum_height_m"], 0.2)
        self.assertAlmostEqual(result["fixed_height_rate_m_s"], 0.0)


if __name__ == "__main__":
    unittest.main()
