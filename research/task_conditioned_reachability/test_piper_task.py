"""New task-frame/path checks; static only, never a contact/robot success test."""
import json
from pathlib import Path
import unittest

import mujoco
import numpy as np

from model import Constraint, PhaseSample, Sample, NominalPath, candidate_score
from piper_kinematics import PiperKinematics, REPO, load_existing, no_physics_steps
from piper_task_geometry import (bind_task_sources, task_world_pose, task_in_base,
    candidate_grid, common_orientation_pool, reference_bounds, quintic_path)
from run_piper_task_study import constructed_path, summarize

P = json.loads(Path(__file__).with_name('piper_task_protocol_v1.json').read_text())


class TaskGeometryTests(unittest.TestCase):
    def test_source_bound_task_pose_and_no_success_direction_selection(self):
        self.assertEqual(len(bind_task_sources(P)), 3)
        p, q = task_world_pose(P)
        np.testing.assert_allclose(p, [.47, 0, .10], atol=1e-14)
        np.testing.assert_allclose(q, [np.cos(.4), 0, np.sin(.4), 0])
        point, quat = task_in_base(np.array([0, 0, .33]), 0, p, q)
        np.testing.assert_allclose(point, [.47, 0, -.23], atol=1e-14)
        self.assertEqual(len(common_orientation_pool(quat)), 13)
        np.testing.assert_array_equal(common_orientation_pool(quat)[-1], quat)

    def test_candidate_count_and_pose_frame_roundtrip_all_candidates(self):
        p, q = task_world_pose(P)
        grid = candidate_grid(P)
        self.assertEqual(len(grid), 75)
        self.assertEqual(len({cid for cid, _, _ in grid}), 75)
        for _, b, yaw in grid:
            point, quat = task_in_base(b, yaw, p, q)
            qb = np.array([np.cos(yaw/2), 0, 0, np.sin(yaw/2)])
            rotation = np.empty(9)
            mujoco.mju_quat2Mat(rotation, qb)
            np.testing.assert_allclose(rotation.reshape(3, 3) @ point + b, p, atol=1e-14)
            result = np.empty(4)
            mujoco.mju_mulQuat(result, qb, quat)
            self.assertAlmostEqual(abs(np.dot(result, q)), 1.)

    def test_same90percent_reference_interval_and_convex_quintic_path(self):
        low, high = np.array([-2., 0]), np.array([2., 3.])
        softlow, softhigh = reference_bounds(low, high)
        np.testing.assert_allclose(softhigh - softlow, .9 * (high - low))
        phase, path = quintic_path(softlow, softhigh, 21)
        self.assertEqual((phase[0], phase[-1]), (0., 1.))
        self.assertTrue((np.diff(path, axis=0) >= 0).all())
        self.assertTrue((path >= softlow).all() and (path <= softhigh).all())

    def test_phase_sample_not_mislabeled_seconds(self):
        constraints = [Constraint('g', 'm', 1)]
        samples = (PhaseSample(0, {'g': 1}), PhaseSample(.5, {'g': -1}), PhaseSample(1, {'g': 1}))
        path = NominalPath('phase', samples, sample_axis='normalized_phase')
        self.assertEqual(candidate_score([path], constraints).status, 'infeasible')
        self.assertEqual(candidate_score([path], constraints, endpoint_only=True).status, 'feasible')
        with self.assertRaisesRegex(ValueError, 'axis'):
            candidate_score([NominalPath('wrong', samples)], constraints)
        with self.assertRaisesRegex(ValueError, r'\[0,1\]'):
            candidate_score([NominalPath('wrong', (PhaseSample(2, {'g': 1}),), sample_axis='normalized_phase')], constraints)
        # Legacy real-timestamp API remains supported, without changing seconds to phase.
        self.assertEqual(candidate_score([NominalPath('t', (Sample(2, {'g': 1}),))], constraints).status, 'feasible')

    def test_empty_constructed_set_abstains_but_preserves_solver_unknowns(self):
        row = dict(candidate_id='unknown', task_IK_found=False, wide_fraction13=0,
                   queries=[dict(attempts=[{}, {}]) for _ in range(13)])
        result = summarize([row], {}, {}, {}, P)
        self.assertEqual(result['task_solver_miss_UNKNOWN'], 1)
        self.assertEqual(result['selections']['sampled_path']['status'], 'abstain')
        self.assertEqual(result['selections']['excluded_unknown_ids'], ['unknown'])


class NativeCollisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with no_physics_steps():
            cls.plain = PiperKinematics()
            cls.native = PiperKinematics(native_collision_profile=True)

    def test_collision_profile_does_not_change_same_joint_fk(self):
        with no_physics_steps():
            q = self.native.midpoint_seed
            a, b = self.plain.fk(q), self.native.fk(q)
            np.testing.assert_allclose(a[0], b[0], atol=1e-12)
            self.assertAlmostEqual(abs(np.dot(a[1], b[1])), 1.)
            self.assertTrue(self.native.contract()['native_USD_collision_geometry_loaded'])

    def test_same_constructed_path_clearance_restores_private_state_and_has_no_seconds(self):
        m = self.native
        low, high = m.oracle.arm_low.copy(), m.oracle.arm_high.copy()
        original_seed = m.default_seed.copy()
        old_limits = m.oracle.arm_low, m.oracle.arm_high
        try:
            m.oracle.arm_low, m.oracle.arm_high = reference_bounds(low, high)
            m.default_seed = np.clip(original_seed, m.oracle.arm_low, m.oracle.arm_high)
            mod = load_existing('clearance', REPO / 'mujoco/reconfigurable_navigation/reachability')
            checker = mod.PiperArmClearanceChecker(m.oracle.runtime, protected_body_names=mod.PROTECTED_BODY_NAMES)
            before = m.snapshot()
            with no_physics_steps():
                detail, endpoint, path = constructed_path(m, checker, m.default_seed, P, low, high)
            self.assertTrue(m.restored(before))
            self.assertEqual(m.data.time, 0.)
            self.assertEqual(len(detail['samples']), 21)
            self.assertNotIn('time_s', detail['samples'][0])
            self.assertIn('phase', detail['samples'][0])
            self.assertEqual(endpoint.rho, path.rho)  # constant path uses identical constraints
            self.assertGreater(detail['samples'][0]['clearance']['checked_pairs'], 0)
        finally:
            m.oracle.arm_low, m.oracle.arm_high = old_limits
            m.default_seed = original_seed

    def test_integration_is_explicitly_guarded(self):
        with no_physics_steps():
            for name in ('mj_step', 'mj_step1', 'mj_step2'):
                with self.assertRaisesRegex(RuntimeError, 'forbidden'):
                    getattr(mujoco, name)(self.native.model, self.native.data)


if __name__ == '__main__':
    unittest.main()
