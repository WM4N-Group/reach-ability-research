"""New bounded software checks, not the old 180-case/owner/physics suite."""
import math
import random
import unittest
from .stow_path_choice import (all_subsequences, native_seconds, optimize,
                               reference_edge_interval)


def q(x):
    return (x, 0., 0., 0., 0., 0.)


class StowPathChoiceTests(unittest.TestCase):
    def test_native_timing_formula(self):
        for d in (0., .001, .2, .8, 2.):
            self.assertEqual(native_seconds(d), max(.6, 1.875*d/.4, math.sqrt(5.78*d/.8)))

    def test_origin_interval_covers_native_transition_tolerance(self):
        rng = random.Random(1311)
        for _ in range(100):
            a = tuple(rng.uniform(-1., 1.) for _ in range(6))
            b = tuple(rng.uniform(-1., 1.) for _ in range(6))
            shifted = tuple(x+rng.uniform(-.002, .002) for x in a)
            r = reference_edge_interval(a, b, uncertain_origin=True)
            t = native_seconds(max(abs(x-y) for x, y in zip(shifted, b)))
            self.assertLessEqual(r['lower_s'], t)
            self.assertGreaterEqual(r['upper_s'], t)
            self.assertIsNone(r['actual_completion_time_upper_s'])

    def test_first_reference_origin_is_exact(self):
        r = reference_edge_interval(q(0.), q(.4))
        self.assertEqual(r['upper_s'], r['lower_s'])
        self.assertEqual(r['source_reference_origin_tolerance_rad'], 0.)

    def test_all_subsequences_are_complete_ordered_terminal_preserving(self):
        for n in range(1, 8):
            paths = list(all_subsequences(n))
            self.assertEqual(len(set(paths)), 2**(n-1))
            for p in paths:
                self.assertEqual(p[0], 0); self.assertEqual(p[-1], n)
                self.assertEqual(p, tuple(sorted(set(p))))

    def test_direct_is_explicit_strong_baseline_not_new_algorithm(self):
        r = optimize(q(0.), q(0.), [q(1.), q(.5), q(.1)], guard_segment=lambda a,b: '', compare_exhaustive=True)
        self.assertEqual(r['chosen_path_indices'], [0, 3])
        self.assertTrue(r['changed']); self.assertTrue(r['equivalent_to_direct_baseline'])
        self.assertFalse(r['distinct_from_original_and_direct'])
        self.assertIsNone(r['actual_total_completion_cost_s'])
        self.assertIsNone(r['actual_successor_repair_cost_s'])
        self.assertFalse(r['execution_authorized'])
        self.assertEqual(r['unchanged_original_final_verify_min_s'], 4.)
        self.assertEqual(r['chosen_waypoints'][-1], list(q(.1)))

    def test_intermediate_path_can_differ_from_both_baselines(self):
        def guard(a, b):
            return 'blocked' if (a, b) == (q(0.), q(.3)) else ''
        r = optimize(q(0.), q(0.), [q(1.), q(.5), q(.3)], guard_segment=guard, compare_exhaustive=True)
        self.assertEqual(r['chosen_path_indices'], [0, 2, 3])
        self.assertTrue(r['distinct_from_original_and_direct'])
        self.assertIsNone(r['baselines']['direct_same_endpoint'])

    def test_actual_first_edge_must_pass_separately(self):
        calls = []
        def guard(a, b):
            calls.append((a, b))
            return 'actual-blocked' if a == q(-.1) and b == q(.3) else ''
        r = optimize(q(0.), q(-.1), [q(.5), q(.3)], guard_segment=guard)
        self.assertIn((q(-.1), q(.3)), calls)
        self.assertEqual(r['chosen_path_indices'], [0, 1, 2])
        self.assertFalse(r['changed'])

    def test_reference_first_edge_must_also_pass(self):
        def guard(a, b):
            return 'reference-blocked' if (a,b) == (q(0.), q(.3)) else ''
        r = optimize(q(0.), q(-.1), [q(.5), q(.3)], guard_segment=guard)
        self.assertFalse(r['changed'])

    def test_no_route_keeps_original_for_native_recheck_not_task_cut(self):
        r = optimize(q(0.), q(0.), [q(.5), q(.3)], guard_segment=lambda a,b: 'blocked', compare_exhaustive=True)
        self.assertFalse(r['guarded_candidate_found']); self.assertFalse(r['changed'])
        self.assertEqual(r['chosen_path_indices'], [0, 1, 2])
        self.assertIsNone(r['chosen_reference_duration_interval_s'])
        self.assertTrue(r['original_runtime_full_path_recheck_required'])

    def test_unsafe_original_does_not_prevent_valid_direct_choice(self):
        r = optimize(q(0.), q(0.), [q(.5), q(.3)],
                     guard_segment=lambda a,b: 'blocked' if b == q(.5) else '', compare_exhaustive=True)
        self.assertTrue(r['changed']); self.assertIsNone(r['baselines']['original_guarded_path'])
        self.assertIsNone(r['assigned_reference_upper_bound_reduction_s'])

    def test_single_waypoint_is_unchanged(self):
        r = optimize(q(0.), q(0.), [q(.3)], guard_segment=lambda a,b: '', compare_exhaustive=True)
        self.assertFalse(r['changed']); self.assertEqual(r['chosen_path_indices'], [0, 1])

    def test_tie_preserves_original(self):
        # All displacements tiny: two segments cannot tie one (.6 minimum).
        # Block every skip so the only equal best path is exactly the original.
        points = [q(0.), q(.1), q(.2), q(.3)]
        r = optimize(points[0], points[0], points[1:],
                     guard_segment=lambda a,b: '' if points.index(b)-points.index(a)==1 else 'blocked',
                     compare_exhaustive=True)
        self.assertFalse(r['changed'])

    def test_unknown_or_boolean_guard_is_never_pass(self):
        for unknown in (None, False, True, 0, [], {}):
            with self.subTest(unknown=unknown), self.assertRaises(ValueError):
                optimize(q(0.), q(0.), [q(.3)], guard_segment=lambda a,b: unknown)

    def test_guard_exception_is_not_success(self):
        def guard(a,b): raise RuntimeError('native refusal')
        with self.assertRaisesRegex(RuntimeError, 'native refusal'):
            optimize(q(0.), q(0.), [q(.3)], guard_segment=guard)

    def test_same_problem_DP_exhaustive_random_graphs(self):
        rng = random.Random(1313)
        for n in range(1, 8):
            for _ in range(12):
                points = [tuple(rng.uniform(-1,1) for _ in range(6)) for _ in range(n+1)]
                allowed = {(points[i],points[j]):rng.random()>.4 for i in range(n) for j in range(i+1,n+1)}
                r = optimize(points[0], points[0], points[1:],
                    guard_segment=lambda a,b: '' if allowed[a,b] else 'blocked', compare_exhaustive=True)
                enumeration = r['baselines']['exhaustive_subsequence_optimum']
                if enumeration is None:self.assertFalse(r['guarded_candidate_found'])
                else:
                    self.assertTrue(r['guarded_candidate_found'])
                    self.assertAlmostEqual(r['chosen_reference_duration_interval_s']['upper_s'], enumeration['upper_s'])

    def test_queries_cached_without_claiming_safety(self):
        calls=[]
        r = optimize(q(0.),q(0.),[q(.2),q(.4)],guard_segment=lambda a,b: calls.append((a,b)) or '')
        self.assertEqual(len(calls),len(set(calls)))
        self.assertEqual(r['native_guard_queries'],len(calls))
        self.assertFalse(r['later_segment_origin_guard_neighborhood_certified'])

    def test_bad_inputs_rejected(self):
        for bad in ([0.]*5, [0.]*5+[math.nan], [0.]*5+[True]):
            with self.assertRaises(ValueError): optimize(bad,q(0.),[q(.3)],guard_segment=lambda a,b:'')
        for ws in ([],[q(.3)]*17):
            with self.assertRaises(ValueError): optimize(q(0.),q(0.),ws,guard_segment=lambda a,b:'')
        for d in (-1.,math.inf,True):
            with self.assertRaises(ValueError): native_seconds(d)
        for n in (0,17,True):
            with self.assertRaises(ValueError): list(all_subsequences(n))

    def test_no_input_mutation(self):
        a=list(q(0.));b=list(q(-.1));ws=[list(q(.5)),list(q(.3))]
        before=repr((a,b,ws));optimize(a,b,ws,guard_segment=lambda a,b:'')
        self.assertEqual(repr((a,b,ws)),before)


if __name__ == '__main__': unittest.main()
