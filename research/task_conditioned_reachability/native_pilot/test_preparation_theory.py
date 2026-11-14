"""Synthetic algebra/counterexample tests, NOT robot trials or bound calibration."""
import copy
import itertools
import math
import unittest
from preparation_theory import path_budget,path_request,select_candidate
from pose_tube_standoff import robust_request


def bounds(**overrides):
    b=dict(relative_translation_error_m=0.,relative_rotation_error_rad=0.,point_radius_m=1.,
           joint_tracking_error_norm_rad=0.,point_jacobian_operator_bound_m_per_rad=1.,
           nominal_point_path_lipschitz_m_per_u=0.,unrepresented_geometry_error_m=0.,
           provenance='EXPLICIT SYNTHETIC ASSUMPTIONS, not real calibration')
    b.update(overrides);return b


def candidate(name,d,cost,passed=True,witness_d=None):
    return dict(id=name,shift_m=d,nominal_total_cost=cost,witness=dict(evaluated_shift_m=d if witness_d is None else witness_d,
        support_passed=passed,reserve_passed=True,other_original_gates_passed=True,source='SYNTHETIC_FINAL_SHIFT_WITNESS'))


class PathBudgetTests(unittest.TestCase):
    def test_missing_bounds_stay_unknown(self):
        for b in (None,bounds(point_radius_m=None),bounds(provenance='')):
            r=path_request([[-.63,0,0]],[.6,.6,.1],[1,0,0],.015,[0,1],b)
            self.assertIsNone(r['required_shift_m']);self.assertFalse(r['execution_authorized'])
    def test_invalid_knots_rejected(self):
        for u in ([],[0],[.1,1],[0,.9],[0,.5,.5,1],[0,True,1],[0,math.nan,1]):
            with self.assertRaises(ValueError):path_budget(u,bounds())
    def test_components_and_no_input_mutation(self):
        b=bounds(relative_translation_error_m=.001,relative_rotation_error_rad=.02,point_radius_m=.5,
                 joint_tracking_error_norm_rad=.003,point_jacobian_operator_bound_m_per_rad=.4,
                 nominal_point_path_lipschitz_m_per_u=.08,unrepresented_geometry_error_m=.0005)
        saved=copy.deepcopy(b);r=path_budget([0,.25,.5,.75,1],b)
        expected=.001+math.sin(.01)+.4*.003+.08*.25/2+.0005
        self.assertAlmostEqual(r['epsilon_m'],expected);self.assertEqual(b,saved)
        self.assertFalse(r['bounds_independently_validated'])
    def test_midpoint_counterexample_endpoint_only_misses_collision(self):
        # x(u)=-.62+.02*sin(pi*u), inflated front boundary=-.615.
        # Both endpoints are clear; the midpoint lies inside. Ku=.02*pi globally.
        p=[[-.62,0,0],[-.62,0,0]];h=[.6,.6,.1];a=[1,0,0]
        nominal=robust_request(p,h,a,.015,[0,0,0])
        tube=path_request(p,h,a,.015,[0,1],bounds(nominal_point_path_lipschitz_m_per_u=.02*math.pi))
        self.assertEqual(nominal['required_shift_m'],0.)
        self.assertGreater(-.62+.02,-.615)
        self.assertGreater(tube['required_shift_m'],.015)
        d=tube['required_shift_m']
        for i in range(1001):
            x=-.62+.02*math.sin(math.pi*i/1000)-d
            self.assertLessEqual(x,-.615+1e-12)
    def test_finer_sampling_reduces_discretization_budget(self):
        b=bounds(nominal_point_path_lipschitz_m_per_u=.02)
        self.assertGreater(path_budget([0,1],b)['epsilon_m'],path_budget([0,.5,1],b)['epsilon_m'])
    def test_uniform_error_and_retreat_sweep_component_corners(self):
        axis=[math.cos(.07),math.sin(.07),0.];half=[.6,.6,.1]
        points=[[-.62,.614,.11],[-.61,.62,.01],[-.64,.7,.01]]
        r=path_request(points,half,axis,.015,[0,1],bounds(relative_translation_error_m=.002))
        e=r['path_budget']['epsilon_m'];self.assertTrue(r['conditional_within_cap'])
        for d in [r['required_shift_m'],.04]:
            for p in points:
                for signs in itertools.product((-1,1),repeat=3):
                    actual=[p[j]-d*axis[j]+signs[j]*e for j in range(3)]
                    self.assertTrue(any(abs(actual[j])>=half[j]+.015-1e-12 for j in range(3)))
    def test_yz_membership_must_expand_with_error(self):
        p=[[-.61,.617,0]]
        zero=path_request(p,[.6,.6,.1],[1,0,0],.015,[0,1],bounds())
        robust=path_request(p,[.6,.6,.1],[1,0,0],.015,[0,1],bounds(relative_translation_error_m=.003))
        self.assertEqual(zero['finite_cloud_bound']['selected_indices'],[])
        self.assertEqual(robust['finite_cloud_bound']['selected_indices'],[0])
        self.assertGreater(robust['required_shift_m'],0.)
    def test_zero_budget_reuses_existing_rule(self):
        p=[[-.61,0,0],[-.64,.7,0]];h=[.6,.6,.1];a=[1,0,0]
        r=path_request(p,h,a,.015,[0,1],bounds())
        self.assertEqual(r['required_shift_m'],robust_request(p,h,a,.015,[0,0,0])['required_shift_m'])
    def test_out_of_cap_not_robot_infeasibility(self):
        r=path_request([[-.5,0,0]],[.6,.6,.1],[1,0,0],.015,[0,1],bounds())
        self.assertFalse(r['conditional_within_cap']);self.assertFalse(r['whole_robot_dynamic_safety_certified'])
    def test_nonunit_box_axis_rejected(self):
        with self.assertRaisesRegex(ValueError,'unit'):
            path_request([[-.62,0,0]],[.6,.6,.1],[2,0,0],.015,[0,1],bounds())
    def test_derived_overflow_is_not_accepted_as_a_bound(self):
        with self.assertRaisesRegex(ValueError,'overflowed'):
            path_budget([0,1],bounds(point_jacobian_operator_bound_m_per_rad=1e308,joint_tracking_error_norm_rad=1e308))

    def test_long_radius_amplifies_same_orientation_error(self):
        a=path_budget([0,1],bounds(relative_rotation_error_rad=.02,point_radius_m=.3))
        b=path_budget([0,1],bounds(relative_rotation_error_rad=.02,point_radius_m=.6))
        self.assertAlmostEqual(b['epsilon_m'],2*a['epsilon_m'])
    def test_declared_bounds_cannot_be_negative_or_nonfinite(self):
        for key,value in [('relative_rotation_error_rad',math.pi+.1),('relative_translation_error_m',-.1),
                          ('point_radius_m',True),('joint_tracking_error_norm_rad',math.inf)]:
            with self.assertRaises(ValueError):path_budget([0,1],bounds(**{key:value}))


class FiniteSelectionTests(unittest.TestCase):
    def test_support_nonmonotone_counterexample_max_is_wrong(self):
        rows=[candidate('d0',0.,0.),candidate('d20',.02,2.,False),candidate('d30',.03,3.)]
        r=select_candidate(rows,.015)
        self.assertEqual(r['selected']['id'],'d30')
        self.assertNotEqual(r['selected']['shift_m'],max(0.,.015))
        self.assertTrue(r['conditional_optimal_value_proven'])
    def test_total_nominal_cost_not_always_smallest_retreat(self):
        r=select_candidate([candidate('small',.02,5.),candidate('larger',.03,3.)],.01)
        self.assertEqual(r['selected']['id'],'larger');self.assertIsNone(r['task_success'])
    def test_witness_at_smaller_pre_reserve_shift_not_transferred(self):
        r=select_candidate([candidate('wrong_witness',.02,1.,witness_d=.015),candidate('valid',.03,2.)],.01)
        self.assertEqual(r['selected']['id'],'valid');self.assertFalse(r['conditional_optimal_value_proven'])
        self.assertEqual(r['unknown_cheaper_candidate_ids'],['wrong_witness'])
    def test_missing_cheaper_support_blocks_optimality_not_candidate(self):
        r=select_candidate([candidate('unknown',.02,1.,None),candidate('valid',.03,2.)],.01)
        self.assertEqual(r['status'],'CONDITIONAL_best_known_candidate')
        self.assertFalse(r['execution_authorized'])
    def test_missing_cost_cannot_be_zero_or_silently_excluded(self):
        r=select_candidate([candidate('unknown_cost',.02,None),candidate('valid',.03,2.)],.01)
        self.assertFalse(r['conditional_optimal_value_proven'])
    def test_unavailable_or_no_candidate_not_physical_failure(self):
        for rows,m in [([],0.),([candidate('too_small',.01,1.)],.02),([candidate('valid',.02,1.)],None)]:
            r=select_candidate(rows,m);self.assertIsNone(r['selected']);self.assertIsNone(r['task_success'])
    def test_all_64_boolean_support_tables_equal_exhaustive_optimum(self):
        for mask in range(64):
            rows=[candidate(f'c{i}',i*.005,float(7-i),bool(mask&(1<<i))) for i in range(6)]
            r=select_candidate(rows,.01)
            feasible=[x for x in rows if x['shift_m']>=.01 and x['witness']['support_passed']]
            expected=min(feasible,key=lambda x:(x['nominal_total_cost'],x['shift_m'],x['id'])) if feasible else None
            self.assertEqual(None if r['selected'] is None else r['selected']['id'],None if expected is None else expected['id'])
    def test_more_required_clearance_only_shrinks_certified_set(self):
        rows=[candidate(f'c{i}',i*.005,float(i)) for i in range(9)]
        previous=None
        for m in [0.,.005,.01,.02,.04,.05]:
            r=select_candidate(rows,m)
            ids={x['id'] for x in r['classified'] if x['status']=='conditionally_eligible'}
            if previous is not None:self.assertTrue(ids<=previous)
            previous=ids
    def test_boolean_evaluated_shift_does_not_bind_zero_shift_witness(self):
        raw=candidate('zero',0.,0.);raw['witness']['evaluated_shift_m']=False
        r=select_candidate([raw],0.)
        self.assertEqual(r['status'],'UNKNOWN');self.assertIsNone(r['selected'])

    def test_bad_candidate_identity_or_boolean_rejected(self):
        with self.assertRaises(ValueError):select_candidate([candidate('x',.02,1),candidate('x',.03,2)],0.)
        with self.assertRaises(ValueError):select_candidate([candidate('x',.02,1,'true')],0.)

if __name__=='__main__':unittest.main()
