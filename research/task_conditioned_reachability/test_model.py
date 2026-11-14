"""Mathematical/implementation tests only. No robot/physics outcomes."""
from dataclasses import replace
from itertools import product
import math
import unittest

from model import (BasePose, Constraint, Ellipsoid, NominalPath, OmniNavParameters,
                   Sample, candidate_score, omninav_cost, path_score,
                   quasi_static_torque, select_exact_candidate)


def path(pid, rows, domain=True):
    return NominalPath(pid, tuple(Sample(float(i), row) for i, row in enumerate(rows)), domain)


def params():
    return OmniNavParameters(
        Ellipsoid((0, 0, 0), ((.25, 0, 0), (0, 1, 0), (0, 0, 1))),
        Ellipsoid((0, 0, 0), ((25, 0, 0), (0, 25, 0), (0, 0, 25))),
        1/6, 2/6, 3/6, .5, .3, .05)


class PaperFormTests(unittest.TestCase):
    def test_target_inside_shell_zero(self):
        cost = omninav_cost(BasePose.planar(0, 0, 0, 0), (1, 0, 0), [], params())
        self.assertEqual(cost['total'], 0)
        self.assertEqual(cost['target'], 0)

    def test_outer_target_penalty_matches_squared_quadratic_excess(self):
        cost = omninav_cost(BasePose.planar(0, 0, 0, 0), (3, 0, 0), [], params())
        self.assertEqual(cost['target'], (2.25 - 1) ** 2)
        self.assertEqual(cost['total'], (2/6) * (2.25 - 1) ** 2)

    def test_inner_target_penalty_and_alignment(self):
        c = omninav_cost(BasePose.planar(0, 0, 0, 0), (.1, 0, 0), [], params())
        self.assertAlmostEqual(c['target'], (1 - .25) ** 2)
        b = omninav_cost(BasePose.planar(0, 0, 0, 0), (-1, 0, 0), [], params())
        self.assertEqual(b['alignment'], 2)

    def test_cloud_shell_and_softplus_manual(self):
        c = omninav_cost(BasePose.planar(0, 0, 0, 0), (1, 0, 0), [(1, 0, 0)], params())
        expected_shell = .75 / (1 + math.exp(-24))
        expected_collision = math.log1p(math.exp(-.65))
        self.assertAlmostEqual(c['shell'], expected_shell)
        self.assertAlmostEqual(c['collision'], expected_collision)
        self.assertAlmostEqual(c['total'], (2/6) * .5 * expected_shell + (3/6) * expected_collision)

    def test_common_world_yaw_translation_invariance(self):
        pose = BasePose.planar(0, 0, 0, .3)
        original = omninav_cost(pose, (1, 0, .4), [(1, .2, .7)], params())
        yaw, dx, dy = .7, 3, -2
        def world(p):
            x, y, z = p
            return (math.cos(yaw) * x - math.sin(yaw) * y + dx,
                    math.sin(yaw) * x + math.cos(yaw) * y + dy, z)
        transformed = omninav_cost(BasePose.planar(dx, dy, yaw, .3), world((1, 0, .4)),
                                   [world((1, .2, .7))], params())
        for k in ['target', 'alignment', 'shell', 'collision', 'total']:
            self.assertAlmostEqual(original[k], transformed[k])

    def test_actual_body_pitch_is_not_flattened(self):
        c, s = math.cos(.3), math.sin(.3)
        pose = BasePose((0, 0, .4), ((c, 0, s), (0, 1, 0), (-s, 0, c)))
        self.assertAlmostEqual(pose.to_base((1, 0, .4))[2], s)
        self.assertNotEqual(pose.to_base((1, 0, .4)), BasePose.planar(0, 0, 0, .4).to_base((1, 0, .4)))

    def test_invalid_ellipsoid_and_pose_rejected(self):
        for metric in [((0, 0, 0), (0, 1, 0), (0, 0, 1)),
                       ((1, 2, 0), (0, 1, 0), (0, 0, 1)),
                       ((1, 2, 0), (2, 1, 0), (0, 0, 1))]:
            with self.assertRaises(ValueError):
                Ellipsoid((0, 0, 0), metric)
        with self.assertRaises(ValueError):
            BasePose((0, 0, 0), ((1, 0, 0), (0, 1, 0), (0, 0, -1)))
        with self.assertRaises(ValueError):
            omninav_cost(BasePose.planar(0, 0, 0, 0), (0, 0, 1), [], params())
        with self.assertRaises(ValueError):
            replace(params(), reach_weight=-1)
        with self.assertRaises(ValueError):
            replace(params(), reach_weight=2)


class BottleneckTests(unittest.TestCase):
    def setUp(self):
        self.c = (Constraint('gap', 'm', .01), Constraint('torque', 'Nm', 1.))

    def test_endpoint_misses_interior_violation(self):
        p = path('p', [dict(gap=.02, torque=1), dict(gap=-.001, torque=1), dict(gap=.01, torque=1)])
        self.assertEqual(path_score(p, self.c, endpoint_only=True).status, 'feasible')
        result = path_score(p, self.c)
        self.assertEqual(result.status, 'infeasible')
        self.assertEqual(result.witness, (1, 'gap'))
        self.assertAlmostEqual(result.rho, -.1)

    def test_large_positive_terms_do_not_cancel_negative(self):
        result = path_score(path('p', [dict(gap=-.01, torque=1000)]), self.c)
        self.assertEqual(result.rho, -1)
        self.assertEqual(result.status, 'infeasible')

    def test_max_over_complete_paths_not_per_constraint_cherrypicking(self):
        a = path('a', [dict(gap=.02, torque=-1)])
        b = path('b', [dict(gap=-.01, torque=2)])
        result = candidate_score([a, b], self.c)
        self.assertEqual(result.rho, -1)
        self.assertEqual(result.status, 'infeasible')

    def test_correct_max_path_and_argmax(self):
        result = candidate_score([path('low', [dict(gap=.01, torque=.4)]),
                                  path('high', [dict(gap=.02, torque=.8)])], self.c)
        self.assertEqual(result.rho, .8)
        self.assertEqual(result.best_known_path_id, 'high')

    def test_missing_not_zero_or_passed(self):
        result = candidate_score([path('a', [dict(gap=.01)])], self.c)
        self.assertEqual(result.status, 'unknown')
        self.assertIsNone(result.rho)
        self.assertEqual(result.upper, 1.)

    def test_known_negative_can_reject_despite_missing_other_gate(self):
        result = candidate_score([path('a', [dict(gap=-.01)])], self.c)
        self.assertEqual(result.status, 'infeasible')
        self.assertIsNone(result.rho)
        self.assertLess(result.upper, 0)

    def test_incomplete_dominated_alternative_does_not_obscure_exact_max(self):
        result = candidate_score([path('good', [dict(gap=.01, torque=.5)]),
                                  path('cannot_beat', [dict(gap=-.01)])], self.c)
        self.assertEqual(result.rho, .5)
        self.assertEqual(result.best_known_path_id, 'good')

    def test_unknown_alternative_can_obscure_exact_max_but_not_existential_feasibility(self):
        result = candidate_score([path('good', [dict(gap=.01, torque=.5)]),
                                  path('possibly_better', [dict(gap=.02)])], self.c)
        self.assertEqual(result.status, 'feasible')
        self.assertIsNone(result.rho)
        self.assertEqual((result.lower, result.upper), (.5, 2.))

    def test_unsupported_domain_not_proven_robot_infeasible(self):
        for domain in [False, None]:
            result = candidate_score([path('a', [dict(gap=1, torque=2)], domain)], self.c)
            self.assertEqual(result.status, 'unknown')
            self.assertIsNone(result.rho)

    def test_empty_not_physical_failure(self):
        self.assertEqual(candidate_score([], self.c).status, 'unknown')

    def test_zero_boundary_is_feasible_for_declared_non_strict_formula_only(self):
        self.assertEqual(path_score(path('a', [dict(gap=0, torque=0)]), self.c).status, 'feasible')

    def test_positive_rescaling_cannot_change_feasibility(self):
        p = path('a', [dict(gap=-.01, torque=100)])
        other = (Constraint('gap', 'm', 10), Constraint('torque', 'Nm', .01))
        self.assertEqual(path_score(p, self.c).status, path_score(p, other).status)
        self.assertNotEqual(path_score(p, self.c).rho, path_score(p, other).rho)

    def test_unit_change_with_matching_scale_preserves_score(self):
        m = path_score(path('a', [dict(gap=.01, torque=.5)]), self.c)
        mm = path_score(path('a', [dict(gap=10, torque=.5)]),
                        (Constraint('gap', 'mm', 10), self.c[1]))
        self.assertEqual(m.rho, mm.rho)

    def test_appending_checks_never_improves_path_bottleneck(self):
        p = path('a', [dict(gap=.02, torque=1)])
        q = path('a', [dict(gap=.02, torque=1), dict(gap=.001, torque=.2)])
        self.assertLessEqual(path_score(q, self.c).rho, path_score(p, self.c).rho)

    def test_finite_equivalence_exhaustive_small_arrays(self):
        # 3^8 = 6561 candidate tensors; not robot trials or statistical samples.
        for v in product([-1., 0., 1.], repeat=8):
            p = [path(str(i), [dict(gap=v[4*i] * .01, torque=v[4*i+1]),
                               dict(gap=v[4*i+2] * .01, torque=v[4*i+3])]) for i in range(2)]
            expected = any(all(x >= 0 for x in v[i:i+4]) for i in (0, 4))
            self.assertEqual(candidate_score(p, self.c).rho >= 0, expected)

    def test_bad_scales_values_keys_ids_times(self):
        for x in [0, -1, math.nan, math.inf, True]:
            with self.assertRaises(ValueError):
                Constraint('gap', 'm', x)
        for x in [math.nan, math.inf, True]:
            with self.assertRaises(ValueError):
                path_score(path('p', [dict(gap=x, torque=1)]), self.c)
        with self.assertRaises(ValueError):
            path_score(path('p', [dict(gapp=1)]), self.c)
        with self.assertRaises(ValueError):
            candidate_score([path('p', [dict(gap=1)]), path('p', [dict(gap=2)])], self.c)
        with self.assertRaises(ValueError):
            path_score(NominalPath('p', (Sample(1, {}), Sample(1, {}))), self.c)

    def test_nominal_selection_and_deterministic_tie(self):
        scores = {cid: candidate_score([path('p', [dict(gap=.01, torque=.5)])], self.c)
                  for cid in ['b', 'a']}
        self.assertEqual(select_exact_candidate({'b': 1, 'a': 1}, scores, 1)['candidate_id'], 'a')
        with self.assertRaises(ValueError):
            select_exact_candidate({'b': 1, 'a': 1}, scores, -1)

    def test_unknown_contender_not_silently_discarded(self):
        scores = {'a': candidate_score([path('a', [dict(gap=.01, torque=1)])], self.c),
                  'b': candidate_score([path('b', [dict(gap=.02)])], self.c)}
        self.assertEqual(select_exact_candidate({'a': 0, 'b': 0}, scores, 1)['status'], 'unknown')

    def test_all_infeasible_abstains(self):
        scores = {'a': candidate_score([path('a', [dict(gap=-.01, torque=1)])], self.c)}
        self.assertEqual(select_exact_candidate({'a': 0}, scores, 1)['status'], 'abstain')

    def test_static_wrench_sign_and_coupling(self):
        j = [[1, 2], [0, 0], [0, 0], [0, 0], [0, 0], [0, 0]]
        self.assertEqual(quasi_static_torque([1, 2], j, [3, 0, 0, 0, 0, 0]), (-2., -4.))
        self.assertEqual(quasi_static_torque([1, 2], j, [-3, 0, 0, 0, 0, 0]), (4., 8.))
        with self.assertRaises(ValueError):
            quasi_static_torque([1], j, [3, 0, 0, 0, 0, 0])


if __name__ == '__main__':
    unittest.main()
