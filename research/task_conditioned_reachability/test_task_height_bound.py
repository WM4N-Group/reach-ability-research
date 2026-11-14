"""Algebra/source checks for the posthoc necessary bound. No IK or simulation."""
import json
import math
from pathlib import Path
import unittest

import numpy as np

from task_height_bound import min_sinusoid, quat_matrix, validate_structure, height_bound

STUDY = Path(__file__).resolve().parents[2] / 'evidence/2026-10-20/piper-source-task-static-v1'
C = json.loads((STUDY / 'robot_contract.json').read_text())
ROWS = json.loads((STUDY / 'candidate_queries_and_paths.json').read_text())


class HeightBoundTests(unittest.TestCase):
    def test_exact_sinusoid_minimum_includes_critical_point(self):
        self.assertAlmostEqual(min_sinusoid(3, 4, -10, 10)['value'], -5.)
        self.assertAlmostEqual(min_sinusoid(1, 0, 0, .3)['value'], math.cos(.3))
        self.assertAlmostEqual(min_sinusoid(1, 0, 2, 4)['at_joint2_rad'], math.pi)
        with self.assertRaises(ValueError):
            min_sinusoid(1, 1, 2, 1)

    def test_source_bound_lower_arm_height_is_conservative(self):
        chain = validate_structure(C)
        r2 = quat_matrix(chain['link2']['local_quaternion_wxyz'])
        length = chain['link3']['local_position_m'][0]
        a, b = length*r2[2, 0], length*r2[2, 1]
        lo, hi = C['study_reference_low_rad'][1], C['study_reference_high_rad'][1]
        bound = min_sinusoid(a, b, lo, hi)['value']
        for q in np.linspace(lo, hi, 101):
            self.assertGreaterEqual(a*math.cos(q)+b*math.sin(q)+1e-14, bound)

    def test_wrist_offset_identity_does_not_drop_small_native_offset(self):
        chain = validate_structure(C)
        rfix6 = quat_matrix(chain['link6']['local_quaternion_wxyz'])
        rtool = quat_matrix(chain['end_effector']['local_quaternion_wxyz'])
        t6, ttool = (np.array(chain[b]['local_position_m']) for b in ('link6', 'end_effector'))
        ell = t6 @ rfix6[:, 2]
        residual = t6 - ell*rfix6[:, 2]
        self.assertGreater(np.linalg.norm(residual), 0)  # do not silently idealize native 88um offset
        for a in [-1., 0., .7]:
            r5 = quat_matrix([math.cos(a/2), math.sin(a/2), 0, 0])
            for q6 in [-1., 0., 1.]:
                rz6 = quat_matrix([math.cos(q6/2), 0, 0, math.sin(q6/2)])
                r6 = r5 @ rfix6 @ rz6
                ree = r6 @ rtool
                exact_offset = r5 @ t6 + r6 @ ttool
                derived = (ell+ttool[2])*ree @ rtool.T[:, 2] + r5 @ residual
                np.testing.assert_allclose(exact_offset, derived, atol=1e-14)

    def test_orientation_allowance_covers_unit_vector_displacement(self):
        theta = C['orientation_tolerance_rad']
        r = quat_matrix([math.cos(theta/2), 0, math.sin(theta/2), 0])
        for v in np.eye(3):
            self.assertLessEqual(np.linalg.norm(r @ v - v), 2*math.sin(theta/2)+1e-15)

    def test_reference_exclusion_never_becomes_native_hard_feasibility_claim(self):
        for row in ROWS:
            ref = height_bound(C, row['target_base_m'], row['task_quaternion_base_wxyz'])
            hard = height_bound(C, row['target_base_m'], row['task_quaternion_base_wxyz'], use_hard_limits=True)
            self.assertGreaterEqual(ref['exclusion_gap_m'], hard['exclusion_gap_m'])
            self.assertIn(hard['status'], ('EXCLUDED_by_analytic_necessary_condition', 'INCONCLUSIVE_NOT_feasible'))
            self.assertEqual(ref['arithmetic_guard_m'], 1e-8)

    def test_unsupported_chain_fails_closed(self):
        c = json.loads(json.dumps(C))
        c['chain_from_tip_to_base'][0]['local_position_m'][0] = .01
        with self.assertRaisesRegex(ValueError, 'offset'):
            height_bound(c, ROWS[0]['target_base_m'], ROWS[0]['task_quaternion_base_wxyz'])


if __name__ == '__main__':
    unittest.main()
