"""New numeric map/fitter and static asset-adapter tests, no integration steps."""
import json
from pathlib import Path
import unittest

import mujoco
import numpy as np

from piper_kinematics import PiperKinematics, no_physics_steps
from workspace_fit import position_grids, orientation_matrices, fit_dual_ellipsoid, shell_membership, approximation_metrics

PROTOCOL = json.loads(Path(__file__).with_name('piper_map_protocol_v1.json').read_text())


def fixture():
    points = np.array([[x, y, z] for x in [-1., 1.] for y in [-1., 1.] for z in [-1., 1.]]
                      + [[.5, 0, 0], [-.5, 0, 0], [0, .5, 0], [0, -.5, 0], [0, 0, .5], [0, 0, -.5]])
    return points, np.ones(len(points))


class MapAndFitTests(unittest.TestCase):
    def test_predeclared_query_counts_and_disjoint_positions(self):
        train, val = position_grids(PROTOCOL)
        self.assertEqual((len(train), len(val)), (125, 64))
        self.assertEqual(len(train) * 12 + len(val) * 12, 2268)
        self.assertFalse(set(map(tuple, train)) & set(map(tuple, val)))

    def test_12_rotations_are_unique_proper_matrices(self):
        matrices = orientation_matrices()
        self.assertEqual(len(matrices), 12)
        for r in matrices:
            np.testing.assert_allclose(r.T @ r, np.eye(3), atol=1e-14)
            self.assertAlmostEqual(np.linalg.det(r), 1.)
        for i, r in enumerate(matrices):
            self.assertTrue(all(not np.allclose(r, x) for x in matrices[i+1:]))

    def test_ellipsoids_cover_training_positive_and_are_nested(self):
        p, rate = fixture()
        fit = fit_dual_ellipsoid(p, rate, PROTOCOL['fit'])
        self.assertTrue(shell_membership(p, fit).all())
        self.assertTrue((np.array(fit['inner_semiaxes_m']) <= np.array(fit['outer_semiaxes_m'])).all())
        self.assertTrue(np.linalg.eigvalsh(fit['outer_metric_m_minus2']).min() > 0)

    def test_fit_does_not_consume_negative_positions(self):
        p, rate = fixture()
        a = fit_dual_ellipsoid(p, rate, PROTOCOL['fit'])
        b = fit_dual_ellipsoid(np.vstack([p, [100, 0, 0]]), np.r_[rate, 0], PROTOCOL['fit'])
        self.assertEqual(a['outer_metric_m_minus2'], b['outer_metric_m_minus2'])
        self.assertEqual(a['inner_metric_m_minus2'], b['inner_metric_m_minus2'])

    def test_rigid_transform_covariance_of_fitted_membership(self):
        p, rate = fixture()
        r = orientation_matrices()[5]
        shift = np.array([1, -2, .5])
        a = fit_dual_ellipsoid(p, rate, PROTOCOL['fit'])
        b = fit_dual_ellipsoid(p @ r.T + shift, rate, PROTOCOL['fit'])
        q = np.array([[0, 0, 0], [2, 0, 0], [.6, .1, 0]])
        np.testing.assert_array_equal(shell_membership(q, a), shell_membership(q @ r.T + shift, b))

    def test_report_empty_and_false_accepts_without_task_labels(self):
        p, rate = fixture()
        fit = fit_dual_ellipsoid(p, rate, PROTOCOL['fit'])
        m = approximation_metrics(np.array([[.6, 0, 0], [3, 0, 0]]), [0, 1], fit)
        self.assertEqual(m['false_accept_vs_sampled_rate'], 1)
        self.assertEqual(m['false_reject_vs_sampled_rate'], 1)
        self.assertNotIn('task_success_rate', m)

    def test_degenerate_or_missing_inputs_refuse_not_invent_fit(self):
        with self.assertRaisesRegex(ValueError, 'full-dimensional'):
            fit_dual_ellipsoid([[0, 0, 0], [1, 0, 0], [0, 1, 0], [1, 1, 0]], [1] * 4, PROTOCOL['fit'])
        with self.assertRaisesRegex(ValueError, 'Insufficient'):
            fit_dual_ellipsoid([[0, 0, 0]], [0], PROTOCOL['fit'])
        with self.assertRaises(ValueError):
            fit_dual_ellipsoid([[float('nan'), 0, 0]], [1], PROTOCOL['fit'])


class StaticAssetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with no_physics_steps():
            cls.model = PiperKinematics()

    def test_repository_mount_and_original_joint_order(self):
        contract = self.model.contract()
        np.testing.assert_allclose(contract['mount_position_in_base_m'], [0, 0, .07], atol=1e-8)
        self.assertEqual(contract['arm_joint_order'], [f'joint{i}' for i in range(1, 7)])
        self.assertFalse(contract['actor_loaded'])
        self.assertFalse(contract['collision_checked'])
        self.assertEqual(len(contract['hard_joint_low_rad']), 6)

    def test_actual_known_pose_solves_and_restores_private_state(self):
        with no_physics_steps():
            before = self.model.snapshot()
            target_world, q = self.model.fk(self.model.default_seed)
            target_base = self.model.base_rotation.T @ (target_world - self.model.base_position)
            found = self.model.solve(target_base, q)
            self.assertTrue(found['found'])
            self.assertLessEqual(found['verified_position_error_m'], .002)
            self.assertTrue(self.model.restored(before))
            self.assertEqual(self.model.data.time, 0.)

    def test_distant_pose_is_solver_miss_not_infeasibility_certificate(self):
        with no_physics_steps():
            before = self.model.snapshot()
            result = self.model.solve([10, 0, 10], [1, 0, 0, 0])
            self.assertFalse(result['found'])
            self.assertEqual(result['classification'], 'bounded_solver_not_found_NOT_unreachable_proof')
            self.assertEqual(len(result['attempts']), 2)
            self.assertTrue(self.model.restored(before))

    def test_physics_guard_refuses_actual_integration(self):
        before = self.model.snapshot()
        with no_physics_steps():
            with self.assertRaisesRegex(RuntimeError, 'forbidden'):
                mujoco.mj_step(self.model.model, self.model.data)
        self.assertTrue(self.model.restored(before))
        self.assertEqual(self.model.data.time, 0.)


if __name__ == '__main__':
    unittest.main()
