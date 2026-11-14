"""New state-protocol/cache/conditional-domain tests, no FK/IK/physics."""
import copy
import unittest

import numpy as np

from piper_task_geometry import task_world_pose, task_in_base
from run_piper_state_height_study import (load_frozen_inputs, height_candidates,
                                         row_scores, per_state_summary)
from task_height_bound import height_bound


class StateHeightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.protocol, cls.parent, cls.cached, cls.contract = load_frozen_inputs()

    def test_closed_control_is_bound_and_never_rerun(self):
        self.assertEqual(len(self.cached), 75)
        self.assertFalse(self.protocol['reused_control']['rerun_control'])
        with self.assertRaisesRegex(ValueError, 'reused'):
            height_candidates(self.parent, .33)

    def test_exact_new_budget_and_shared_se2_candidate_identity(self):
        low = height_candidates(self.parent, .28)
        high = height_candidates(self.parent, .38)
        self.assertEqual(len(low)+len(high), 150)
        self.assertEqual((len(low)+len(high))*13, self.protocol['resources']['max_new_pose_queries'])
        for a, b in zip(low, high):
            self.assertEqual(a[0], b[0])
            np.testing.assert_array_equal(a[1][:2], b[1][:2])
            self.assertEqual(a[2], b[2])
            self.assertAlmostEqual(b[1][2]-a[1][2], .1)

    def test_height_condition_changes_relative_target_only_not_task_orientation(self):
        target, quat = task_world_pose(self.parent)
        low = height_candidates(self.parent, .28)[0]
        high = height_candidates(self.parent, .38)[0]
        a, qa = task_in_base(low[1], low[2], target, quat)
        b, qb = task_in_base(high[1], high[2], target, quat)
        np.testing.assert_allclose(a-b, [0, 0, .1], atol=1e-14)
        np.testing.assert_array_equal(qa, qb)

    def test_necessary_gap_height_derivative_one_without_experiment(self):
        target, quat = task_world_pose(self.parent)
        gaps = []
        for h in [.28, .33, .38]:
            p, q = task_in_base(np.array([0, 0, h]), 0, target, quat)
            gaps.append(height_bound(self.contract, p, q)['exclusion_gap_m'])
        np.testing.assert_allclose(np.diff(gaps), [.05, .05], atol=1e-14)
        self.assertLess(gaps[0], 0)  # no exclusion is NOT a prediction of solver/task success
        self.assertGreater(gaps[1], 0)

    def test_reused_unknown_control_stays_unknown_no_invented_paths(self):
        rows = copy.deepcopy(self.cached)
        for r in rows:
            r['height_necessary_bound'] = height_bound(self.contract, r['target_base_m'], r['task_quaternion_base_wxyz'])
        endpoint, path, costs = row_scores(rows, self.parent)
        self.assertEqual((endpoint, path, costs), ({}, {}, {}))
        summary = per_state_summary(rows, self.parent)
        self.assertEqual(summary['analytic_reference_excluded'], 75)
        self.assertEqual(summary['analytic_exclusion_and_task_IK_found'], 0)
        self.assertEqual(summary['task_solver_miss_UNKNOWN'], 75)
        self.assertEqual(summary['selections']['sampled_path']['status'], 'abstain')
        self.assertTrue(summary['height_is_condition_NOT_NAV_action'])


if __name__ == '__main__':
    unittest.main()
