import unittest
import numpy as np
from scipy.optimize import linprog
from .model import Problem, cases, SCALES, MODE
from .solvers import LocalFeedback, Oracle, StopBudget, solve


class ContinuationTests(unittest.TestCase):
    def test_gradients_match_central_difference(self):
        p=cases()[8];u=np.array([.5,.4,.2]);f,g,df,J=p.values(u)
        for j in range(3):
            h=np.eye(3)[j]*1e-6
            plus,minus=p.values(u+h),p.values(u-h)
            self.assertAlmostEqual(df[j],(plus[0]-minus[0])/2e-6,places=7)
            np.testing.assert_allclose(J[:,j],(plus[1]-minus[1])/2e-6,atol=1e-8)

    def test_object_and_robot_both_move_not_fixed_object(self):
        p=cases()[0];u=p.initial.copy();base=p.values(u)[1]
        u[2]+=.2;new=p.values(u)[1]
        self.assertLess(new[0],base[0])
        self.assertGreater(new[1],base[1])
        # Push changes both object/base equally, so separation derivative cancels.
        self.assertEqual(p.values(u)[3][1,0],0.)

    def test_support_is_exit_stage_not_push_start(self):
        p=cases()[2];u=p.analytic_witness()
        self.assertTrue(p.feasible(u));self.assertFalse(p.feasible(np.zeros(3)))
        u[2]=.2
        self.assertGreaterEqual(p.values(u)[1][2],p.values(u)[1][0])

    def test_constructive_witness_all_18(self):
        for p in cases():
            with self.subTest(p=p.name):
                self.assertTrue(p.feasible(p.analytic_witness()))

    def test_exit_only_has_exact_constructive_repair(self):
        for p in cases()[0::3]:
            u=p.initial.copy();u[2]=.08/SCALES[2]
            self.assertTrue(p.feasible(u))

    def test_preparation_required_by_bound_not_family_classifier(self):
        for p in cases()[1::3]+cases()[2::3]:
            # Over all legal retreat r, p=0 cannot reach required standoff:
            # (1-k)r-c*r^2 <= (1-k)*r_max < need.
            self.assertLess((1-p.drag)*p.retreat_upper,p.clearance_need)

    def test_joint_case_requires_target_change_even_with_free_p_r(self):
        for p in cases()[2::3]:
            # g_support <= d-need, r>=0; frozen d0 is insufficient.
            self.assertLess(p.initial_d,p.support_need)

    def test_exact_quadratic_remainder_uniform_random_points(self):
        p=cases()[4];u=np.array([.45,.35,.15]);radius=np.array([.2,.2,.2])
        fb=LocalFeedback.build(p,u,radius,p.values(u));rng=np.random.default_rng(33)
        for _ in range(100):
            candidate=u+rng.uniform(-radius,radius)
            self.assertTrue(np.all(p.values(candidate)[1]>=fb.lower_margin(p,candidate)-1e-12))

    def test_mode_and_problem_domain_not_reused(self):
        p,q=cases()[:2];fb=LocalFeedback.build(p,p.initial,np.full(3,.1),p.values(p.initial))
        self.assertIsNone(fb.lower_margin(p,p.initial,mode='another-contact-mode'))
        self.assertIsNone(fb.lower_margin(q,p.initial))
        self.assertIsNone(fb.lower_margin(p,p.initial+np.array([.11,0.,0.])))

    def test_missing_independent_bound_unknown(self):
        p=cases()[0];fb=LocalFeedback.build(p,p.initial,np.full(3,.1),p.values(p.initial),bound_available=False)
        self.assertIsNone(fb.lower_margin(p,p.initial))

    def test_empty_inner_set_is_not_global_infeasibility(self):
        p=cases()[2];u=p.initial;fb=LocalFeedback.build(p,u,np.full(3,.01),p.values(u))
        result=linprog(np.zeros(3),A_ub=-fb.jacobian,b_ub=fb.margins-fb.remainder,
                       bounds=[(-.01,.01)]*3,method='highs')
        self.assertFalse(result.success)
        self.assertTrue(p.feasible(p.analytic_witness()))

    def test_budget_and_cache_no_hidden_model_evals(self):
        p=cases()[0];o=Oracle(p,max_calls=1,max_wall_s=5)
        o.evaluate(p.initial);o.derivative(p.initial,3)
        self.assertEqual(len(o.rows),1)
        with self.assertRaises(StopBudget):o.evaluate(p.initial+np.array([.01,0.,0.]))
        row=solve(p,'local_projection',max_calls=1,max_wall_s=5)
        self.assertEqual(row['status'],'UNKNOWN');self.assertFalse(row['global_infeasibility_claim'])

    def test_all_methods_validate_returned_incumbent(self):
        for method in ('joint_sqp','alternating_sqp','random_search','local_projection','linearized_feedback'):
            p=cases()[2];row=solve(p,method,seed=4,max_calls=48,max_wall_s=5)
            self.assertLessEqual(row['full_evaluations'],48)
            self.assertFalse(row['execution_authorized'])
            if row['best'] is not None:
                self.assertTrue(p.feasible(row['best']['u']))
                self.assertAlmostEqual(p.values(row['best']['u'])[0],row['best']['cost_s'])

    def test_projection_predictions_rechecked_not_authorized(self):
        row=solve(cases()[2],'local_projection',max_calls=48,max_wall_s=5)
        for event in row['algorithm_events']:
            self.assertFalse(event['global_cut_created'])
            if 'predicted_feasible' in event:
                self.assertGreaterEqual(event['min_actual_minus_predicted'],-1e-10)
                if event['predicted_feasible']:self.assertTrue(event['actual_feasible'])

    def test_invalid_inputs_rejected(self):
        with self.assertRaises(ValueError):cases()[0].values([float('nan'),0,0])
        with self.assertRaises(ValueError):solve(cases()[0],'stub-benders')
        with self.assertRaises(ValueError):Oracle(cases()[0],max_calls=0)


if __name__=='__main__':unittest.main()
