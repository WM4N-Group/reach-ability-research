"""Analytic derivation tests; no simulator, actors, calibration or outcomes."""
import copy
from decimal import Decimal, localcontext
import json
import math
from pathlib import Path
import unittest

from analytic_chain_bounds import chain_bounds, linear_path_bound
from preparation_theory import path_budget


def body(name, parent, translation, joint=None):
    return dict(name=name, parent=parent, translation_m=translation,
                joint=None if joint is None else dict(name=joint, kind='hinge', pivot_m=[0., 0., 0.]))


def two_link():
    return [body('j1body', 'root', [0., 0., .3], 'j1'),
            body('j2body', 'j1body', [1., 0., 0.], 'j2'),
            body('tool', 'j2body', [1., 0., 0.])]


class AnalyticChainTests(unittest.TestCase):
    def test_radius_includes_fixed_root_mount(self):
        b = chain_bounds(two_link())
        self.assertGreaterEqual(b['point_radius_m'], 2.3)
        self.assertAlmostEqual(b['point_radius_m'], 2.3, places=14)

    def test_joint_levers_exclude_their_incoming_edge(self):
        b = chain_bounds(two_link())

        for value, exact in zip(b['joint_lever_upper_m'], [2., 1.]):
            self.assertGreaterEqual(value, exact)
            self.assertAlmostEqual(value, exact, places=14)
        self.assertGreaterEqual(b['point_jacobian_operator_bound_m_per_rad'], math.sqrt(5))

    def test_tool_offset_and_attached_radius_increase_every_lever(self):
        b = chain_bounds(two_link(), tool_offset_m=[0., .2, 0.], attached_point_radius_m=.1)
        self.assertAlmostEqual(b['point_radius_m'], 2.6)
        self.assertAlmostEqual(b['joint_lever_upper_m'][0], 2.3)
        self.assertAlmostEqual(b['joint_lever_upper_m'][1], 1.3)

    def test_outward_norm_against_high_precision_reference(self):
        chain = [body('a', 'root', [1., 1., 1.], 'j'), body('b', 'a', [.1, .2, .3])]
        b = chain_bounds(chain)
        with localcontext() as ctx:
            ctx.prec = 100
            norm1 = Decimal(3).sqrt()
            norm2 = sum(Decimal.from_float(x)**2 for x in [.1, .2, .3]).sqrt()
            self.assertGreaterEqual(Decimal.from_float(b['point_radius_m']), norm1+norm2)
            self.assertGreaterEqual(Decimal.from_float(b['joint_lever_upper_m'][0]), norm2)

    def test_nonzero_pivot_rejected_not_approximated(self):
        chain = two_link(); chain[0]['joint']['pivot_m'][0] = 1e-30
        with self.assertRaisesRegex(ValueError, 'origin-pivot'):
            chain_bounds(chain)

    def test_prismatic_rejected(self):
        chain = two_link(); chain[0]['joint']['kind'] = 'slide'
        with self.assertRaises(ValueError): chain_bounds(chain)

    def test_broken_chain_rejected(self):
        chain = two_link(); chain[1]['parent'] = 'other'
        with self.assertRaises(ValueError): chain_bounds(chain)

    def test_duplicate_joint_rejected(self):
        chain = two_link(); chain[1]['joint']['name'] = 'j1'
        with self.assertRaises(ValueError): chain_bounds(chain)

    def test_duplicate_body_rejected(self):
        chain = two_link(); chain[-1]['name'] = chain[0]['name']
        with self.assertRaises(ValueError): chain_bounds(chain)

    def test_invalid_numeric_inputs_rejected(self):
        for value in [math.nan, math.inf, True]:
            chain = two_link(); chain[0]['translation_m'][0] = value
            with self.subTest(value=value), self.assertRaises(ValueError): chain_bounds(chain)
        with self.assertRaises(ValueError): chain_bounds(two_link(), attached_point_radius_m=-1.)

    def test_no_joint_and_empty_rejected(self):
        with self.assertRaises(ValueError): chain_bounds([])
        with self.assertRaises(ValueError): chain_bounds([body('fixed', 'root', [1., 0., 0.])])

    def test_analytic_planar_jacobian_frobenius_and_path_derivative(self):
        # Formula evaluated at deterministic synthetic angles; not proof by sampling.
        b = chain_bounds(two_link())
        ku = linear_path_bound(b, [[0., 0.], [1., -2.]])['nominal_point_path_lipschitz_m_per_u']
        self.assertGreaterEqual(ku, 4.)
        self.assertAlmostEqual(ku, 4., places=14)
        for i in range(33):
            q1, q2 = i*.41, -i*.37
            j1 = [-math.sin(q1)-math.sin(q1+q2), math.cos(q1)+math.cos(q1+q2)]
            j2 = [-math.sin(q1+q2), math.cos(q1+q2)]
            self.assertLessEqual(math.hypot(*j1), b['joint_lever_upper_m'][0]+1e-14)
            self.assertLessEqual(math.hypot(*(x-2*y for x,y in zip(j1,j2))), ku+1e-14)

    def test_linear_path_uses_weighted_joint_levers(self):
        b = chain_bounds(two_link())
        value = linear_path_bound(b, [[0., 0.], [1., 2.]])
        self.assertGreaterEqual(value['nominal_point_path_lipschitz_m_per_u'], 4.)
        self.assertAlmostEqual(value['nominal_point_path_lipschitz_m_per_u'], 4., places=14)
        self.assertFalse(value['varying_residual_or_tracking_covered'])

    def test_zero_length_path(self):
        self.assertEqual(linear_path_bound(chain_bounds(two_link()), [[1., 2.], [1., 2.]])['nominal_point_path_lipschitz_m_per_u'], 0.)

    def test_multiple_segments_require_global_parameter_rescaling(self):
        b = chain_bounds(two_link())
        p = linear_path_bound(b, [[0., 0.], [1., 0.], [1., 2.]])
        for value in p['segment_lipschitz_m_per_u']:
            self.assertGreaterEqual(value, 4.)
            self.assertAlmostEqual(value, 4., places=14)
        # Returning local segment bound2 here would be a factor-of-two error.
        self.assertAlmostEqual(p['nominal_point_path_lipschitz_m_per_u'], 4., places=14)

    def test_explicit_unequal_phase_spans(self):
        p = linear_path_bound(chain_bounds(two_link()), [[0.,0.], [1.,0.], [1.,2.]], [0., .25, 1.])
        self.assertGreaterEqual(p['segment_lipschitz_m_per_u'][0], 8.)
        self.assertAlmostEqual(p['segment_lipschitz_m_per_u'][0], 8., places=14)
        self.assertGreaterEqual(p['segment_lipschitz_m_per_u'][1], 2/.75)

    def test_invalid_path_and_phases_rejected(self):
        b = chain_bounds(two_link())
        for points, phases in [([[0.,0.]], None), ([[0.], [1.]], None),
                               ([[0.,0.],[1.,1.]], [0.,0.]),
                               ([[0.,0.],[1.,1.]], [0.,.9]),
                               ([[0.,0.],[1.,1.]], [0.,.5,1.])]:
            with self.subTest(points=points, phases=phases), self.assertRaises(ValueError):
                linear_path_bound(b, points, phases)

    def test_fixed_offset_and_clipping_nonexpansiveness(self):
        # Covers every constant residual branch; a time-varying residual is NOT one.
        q0, q1, c, lo, hi = [-3.,.5], [3.,2.], [.2,-.8], [-1.,0.], [1.,1.]
        for i in range(32):
            u, v = i/32, (i+1)/32
            def clip(t): return [min(h,max(l,a+t*(z-a)+r)) for a,z,r,l,h in zip(q0,q1,c,lo,hi)]
            for x,y,a,z in zip(clip(u),clip(v),q0,q1):
                self.assertLessEqual(abs(x-y), abs(z-a)*(v-u)+1e-14)

    def test_corner_fk_does_not_bound_residual_interior(self):
        # One hinge p(q)=(cos q,sin q), q in [-1,1]. Both corners x=cos1<1.
        self.assertLess(math.cos(-1), 1.)
        self.assertLess(math.cos(1), 1.)
        self.assertEqual(math.cos(0), 1.)

    def test_varying_residual_derivative_not_bounded_by_nominal_ku(self):
        # Constant nominal path has Ku0; c(u)=.02*sin(100*u) does not.
        b = chain_bounds(two_link())
        ku = linear_path_bound(b, [[0.,0.], [0.,0.]])['nominal_point_path_lipschitz_m_per_u']
        self.assertEqual(ku, 0.)
        self.assertGreater(.02*100, ku)


class NativeSnapshotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        repo = Path(__file__).resolve().parents[3]
        cls.evidence = json.loads((repo/'evidence/2026-10-25/native-analytic-chain-bounds-v1/derived-bounds.json').read_text())

    def test_source_bound_native_constants_reproduce(self):
        e = self.evidence
        self.assertEqual(chain_bounds(e['chain']), e['center_bounds'])
        self.assertEqual(linear_path_bound(e['center_bounds'], e['nominal_waypoints_float32_rad']), e['nominal_path'])

    def test_native_profile_overrides_raw_xml_limit(self):
        joints = [b['joint'] for b in self.evidence['chain'] if b['joint']]
        self.assertAlmostEqual(joints[0]['hard_range_rad'][1], 2.6180000032620017)
        self.assertNotAlmostEqual(joints[0]['hard_range_rad'][1], 2.168)
        for q in self.evidence['nominal_waypoints_float32_rad']:
            for value, joint in zip(q,joints):
                lo,hi = joint['hard_range_rad']; self.assertTrue(lo <= value <= hi)

    def test_geometric_bounds_do_not_fill_unknown_errors(self):
        e = self.evidence
        bounds = {key:e['center_bounds'][key] for key in ('point_radius_m','point_jacobian_operator_bound_m_per_rad')}
        bounds.update(nominal_point_path_lipschitz_m_per_u=e['nominal_path']['nominal_point_path_lipschitz_m_per_u'], provenance='analytic source geometry')
        result = path_budget([0.,1.], bounds)
        self.assertIsNone(result['epsilon_m'])
        self.assertEqual(result['missing'], ['relative_translation_error_m','relative_rotation_error_rad',
                                           'joint_tracking_error_norm_rad','unrepresented_geometry_error_m'])
        self.assertFalse(result['execution_authorized'])

    def test_current_gap_bound_is_not_negligible(self):
        # Declared 1mm/5mm are computation-budget illustrations, not tuned gates.
        s = self.evidence['sampling_only']; ku = self.evidence['nominal_path']['nominal_point_path_lipschitz_m_per_u']
        self.assertAlmostEqual(s['analytic_gap_term_m'], ku/80)
        self.assertGreater(s['analytic_gap_term_m'], .039)
        self.assertLessEqual(ku/(2*s['intervals_for_1mm_gap_budget']), .001)
        self.assertGreater(ku/(2*(s['intervals_for_1mm_gap_budget']-1)), .001)

    def test_inputs_not_mutated(self):
        chain = copy.deepcopy(self.evidence['chain']); before = copy.deepcopy(chain)
        chain_bounds(chain); self.assertEqual(chain,before)


if __name__ == '__main__':
    unittest.main()
