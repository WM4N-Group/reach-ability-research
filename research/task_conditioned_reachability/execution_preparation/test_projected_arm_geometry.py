import ast
from pathlib import Path
import json
import unittest
from .projected_arm_geometry import GeometryStudyProfile,compare

EVIDENCE=Path(__file__).resolve().parents[3]/'evidence/2026-11-12/afternoon-sufficiency-geometry-v1/geometry/geometry.json'


class GeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.g=json.loads(EVIDENCE.read_text())

    def test_default_profile_is_singleton_no_extension_permission(self):
        self.assertEqual(GeometryStudyProfile().validate().values_m,(.58,))
        with self.assertRaises(ValueError):GeometryStudyProfile(values_m=(.545,.58,.615)).validate()
        with self.assertRaises(ValueError):GeometryStudyProfile(True,(.545,.58,.615),'native_already_safe').validate()

    def test_actual_source_hulls_and_nominal_FK_not_quadratic_toy(self):
        self.assertEqual(self.g['FK_calls'],65)
        self.assertTrue(set(self.g['represented_body_set'])>={'Piper','link1','link2','link3','link4','link5'})
        self.assertGreater(sum(x['vertices'] for x in self.g['shapes']),100)
        self.assertFalse(self.g['physical_safety_certified'])

    def test_continuum_curve_allowance_covers_all_sampled_points(self):
        self.assertGreaterEqual(self.g['maximum_x_upper_model_m'],max(x['proximal_hull_max_base_x_m'] for x in self.g['FK_trace']))
        self.assertTrue(all(x['model_path_Ku_m']>=0 for x in self.g['shapes']))
        self.assertTrue(all(x['sample_to_curve_allowance_m']>=0 for x in self.g['shapes']))

    def test_base_shift_couples_real_geometric_margin_not_new_WM_input(self):
        profile=GeometryStudyProfile(True,(.545,.58,.615),'HYPOTHETICAL_CLEARANCE_SCALE_ONLY_NOT_NATIVE_DOMAIN')
        r=compare(profile,self.g);a,b,c=r['rows']
        self.assertAlmostEqual(b['model_front_plane_margin_m']-a['model_front_plane_margin_m'],.035)
        self.assertAlmostEqual(c['model_front_plane_margin_m']-b['model_front_plane_margin_m'],.035)
        self.assertFalse(a['native_parameter_allowed']);self.assertFalse(c['native_parameter_allowed'])
        self.assertIn('UNKNOWN',a['old7a6_action11_preparation_applicability'])

    def test_exact_same_finite_problem_enumeration_and_generic_MILP(self):
        profile=GeometryStudyProfile(True,(.545,.58,.615),'HYPOTHETICAL_CLEARANCE_SCALE_ONLY_NOT_NATIVE_DOMAIN')
        r=compare(profile,self.g)
        self.assertEqual(r['methods']['full_enumeration']['best']['standoff_m'],r['methods']['generic_MILP']['best']['standoff_m'])
        self.assertEqual(r['methods']['full_enumeration']['best']['standoff_m'],.58)
        self.assertFalse(r['physical_dispatch']);self.assertEqual(r['native_dispatch_domain_m'],[.58])

    def test_no_physics_forward_or_renderer_in_geometry_source(self):
        source=Path(__file__).with_name('projected_arm_geometry.py').read_text()
        calls=[n.func.attr for n in ast.walk(ast.parse(source)) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)]
        self.assertIn('mj_kinematics',calls)
        for prohibited in ('mj_step','mj_forward','Renderer'):self.assertNotIn(prohibited,calls)


if __name__=='__main__':unittest.main()
