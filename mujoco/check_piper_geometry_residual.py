"""Check common-anchor rigid geometry bounds independently of the controller."""

import unittest

import mujoco
import numpy as np

from reconfigurable_navigation.reachability.geometry_residual import (
    anchored_clearance_lower_bound, anchored_geometry_displacement_bounds,
    conditioned_geometry_poses,
)


class GeometryResidualChecks(unittest.TestCase):
    def setUp(self):
        self.model = mujoco.MjModel.from_xml_string('''<mujoco><worldbody>
          <body pos="0.1 0.2 0.3"><freejoint/><geom type="box" size="0.1 0.2 0.15"/></body>
          <body pos="0.8 -0.3 0.2"><freejoint/><geom type="box" size="0.2 0.1 0.1"/></body>
          <body pos="-0.7 0.3 0.2"><freejoint/><geom type="capsule" size="0.1 0.2"/></body>
        </worldbody></mujoco>''')
        self.reference = mujoco.MjData(self.model)
        mujoco.mj_forward(self.model, self.reference)

    def residual(self, data):
        return anchored_geometry_displacement_bounds(self.model, self.reference, data,
                                                     geometry_ids=(0, 1, 2), anchor_geometry=0)

    def test_common_full_se3_cancels_and_inputs_are_unchanged(self):
        observed = mujoco.MjData(self.model)
        quaternion = np.empty(4)
        mujoco.mju_axisAngle2Quat(quaternion, np.ones(3) / np.sqrt(3), 1.4)
        rotation = np.empty(9)
        mujoco.mju_quat2Mat(rotation, quaternion)
        for address in (0, 7, 14):
            observed.qpos[address:address + 3] = (rotation.reshape(3, 3)
                @ self.reference.qpos[address:address + 3] + [1.2, -0.6, 0.4])
            observed.qpos[address + 3:address + 7] = quaternion
        mujoco.mj_forward(self.model, observed)
        before = [data.qpos.copy() for data in (self.reference, observed)]
        residual = self.residual(observed)
        np.testing.assert_allclose(list(residual.values()), 0, atol=1e-14)
        for data, expected in zip((self.reference, observed), before):
            np.testing.assert_array_equal(data.qpos, expected)

    def test_residual_covers_surface_points_and_pair_distances(self):
        rng = np.random.default_rng(861)
        for _ in range(32):
            observed = mujoco.MjData(self.model)
            for address in (0, 7, 14):
                observed.qpos[address:address + 3] += rng.uniform(-0.02, 0.02, 3)
                axis = rng.normal(size=3)
                mujoco.mju_axisAngle2Quat(observed.qpos[address + 3:address + 7],
                                         axis / np.linalg.norm(axis), rng.uniform(-0.2, 0.2))
            mujoco.mj_forward(self.model, observed)
            residual = self.residual(observed)
            self.assertEqual(residual[0], 0)
            anchor_rotation = observed.geom_xmat[0].reshape(3, 3)
            translation = observed.geom_xpos[0] - anchor_rotation @ self.reference.geom_xpos[0]
            for geometry in (1, 2):
                # The bounding sphere includes every point of each rigid shape.
                points = rng.normal(size=(20, 3))
                points *= self.model.geom_rbound[geometry] / np.linalg.norm(points, axis=1)[:, None]
                expected = (points + self.reference.geom_xpos[geometry]) @ anchor_rotation.T + translation
                actual = points @ observed.geom_xmat[geometry].reshape(3, 3).T + observed.geom_xpos[geometry]
                self.assertLessEqual(np.max(np.linalg.norm(actual - expected, axis=1)), residual[geometry] + 1e-12)
            for pair in ((0, 1), (0, 2), (1, 2)):
                lower = anchored_clearance_lower_bound(self.model, self.reference, [pair], residual)
                actual_distance = mujoco.mj_geomDistance(self.model, observed, *pair, float("inf"), None)
                self.assertGreaterEqual(actual_distance, lower - 1e-12)

    def test_invalid_ids_radii_and_anchor_poses_rejected(self):
        for geometries, anchor in (((0, 0), 0), ((3,), 0), ((1,), -1), ((0.5,), 0)):
            with self.assertRaises(ValueError):
                anchored_geometry_displacement_bounds(self.model, self.reference, self.reference,
                    geometry_ids=geometries, anchor_geometry=anchor)
        for pairs, radii in (([], {}), ([(0, 1)], {0: 0}),
                              ([(0, 1)], {0: 0, 1: -1}), ([(0, 1)], {0: 0, 1: np.nan})):
            with self.assertRaises(ValueError):
                anchored_clearance_lower_bound(self.model, self.reference, pairs, radii)
        self.reference.geom_xpos[0, 0] = np.nan
        with self.assertRaises(ValueError):
            self.residual(self.reference)

    def test_initial_conditioned_motion_and_clearance_bound(self):
        reference_current = mujoco.MjData(self.model)
        reference_current.qpos[7:10] += [0.03, -0.04, 0.02]
        mujoco.mju_axisAngle2Quat(reference_current.qpos[10:14], [0, 0, 1], 0.3)
        mujoco.mj_forward(self.model, reference_current)
        observed_initial = mujoco.MjData(self.model)
        observed_initial.qpos[7:10] += [0.02, 0.01, -0.01]
        observed_initial.qpos[14:17] += [-0.03, 0.01, 0]
        mujoco.mj_forward(self.model, observed_initial)
        predicted, initial_residual = conditioned_geometry_poses(
            self.model, self.reference, self.reference, observed_initial, observed_initial,
            geometry_ids=(0, 1, 2), anchor_geometry=0)
        np.testing.assert_allclose(list(initial_residual.values()), 0, atol=1e-14)
        np.testing.assert_allclose(predicted[1][0], observed_initial.geom_xpos[1]
                                   - observed_initial.geom_xpos[0], atol=1e-14)

        observed_current = mujoco.MjData(self.model)
        observed_current.qpos[:] = observed_initial.qpos
        mujoco.mj_forward(self.model, observed_current)
        predicted, _ = conditioned_geometry_poses(
            self.model, self.reference, reference_current, observed_initial, observed_current,
            geometry_ids=(0, 1, 2), anchor_geometry=0)
        nominal = mujoco.MjData(self.model)
        mujoco.mj_forward(self.model, nominal)
        for geometry, (position, rotation) in predicted.items():
            nominal.geom_xpos[geometry] = position
            nominal.geom_xmat[geometry] = rotation.ravel()
            observed_current.geom_xpos[geometry] = position
            observed_current.geom_xmat[geometry] = rotation.ravel()
        observed_current.geom_xpos[1, 0] += 0.012
        _, residual = conditioned_geometry_poses(
            self.model, self.reference, reference_current, observed_initial, observed_current,
            geometry_ids=(0, 1, 2), anchor_geometry=0)
        self.assertAlmostEqual(residual[1], 0.012)
        lower = anchored_clearance_lower_bound(self.model, nominal, [(1, 2)], residual)
        actual = mujoco.mj_geomDistance(self.model, observed_current, 1, 2, float("inf"), None)
        self.assertGreaterEqual(actual, lower - 1e-12)


if __name__ == "__main__":
    unittest.main()
