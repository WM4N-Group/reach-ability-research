"""Mathematical toy LPs, no robot/learned predictor or hidden-state oracle."""
import math
import unittest
import numpy as np

from handover_envelope import (tightened_deficit,solve_envelope,observable_cell_value,
                               skew,relative_hand_linearization,support_moment_linearization)


def one_dim(deficit,price=1.):
    # z>=deficit, z>=0, z<=2, cost=price*z. Correction duration proxy only.
    return dict(cost=[price],matrix=[[1.],[1.],[-1.]],deficit=[deficit,0.,-2.])


class EnvelopeTests(unittest.TestCase):
    def test_robust_tightening_keeps_physical_directions(self):
        d=tightened_deficit([.1,-.2],[[1.,-2.],[0.,3.]],[.02,.01],[.005,0.])
        self.assertAlmostEqual(d[0],-.055)
        self.assertAlmostEqual(d[1],.23)

    def test_missing_input_is_unknown_not_zero(self):
        r=solve_envelope([1.],[[1.]],None)
        self.assertEqual(r['status'],'UNKNOWN');self.assertIsNone(r['value_s'])

    def test_zero_repair_cost_for_already_satisfied_incremental_entry(self):
        r=solve_envelope(**one_dim(-.2))
        self.assertEqual(r['value_s'],0.)
        self.assertFalse(r['execution_authorized'])

    def test_primal_dual_value_and_physical_price(self):
        r=solve_envelope(**one_dim(.3,price=4.))
        self.assertAlmostEqual(r['value_s'],1.2)
        self.assertAlmostEqual(r['dual_prices'][0],4.)
        self.assertLess(r['residuals']['primal_dual_gap'],1e-8)

    def test_dual_price_matches_finite_difference_at_regular_point(self):
        x=.3;eps=1e-5
        base=solve_envelope(**one_dim(x,price=4.))
        derivative=(solve_envelope(**one_dim(x+eps,price=4.))['value_s']-
                    solve_envelope(**one_dim(x-eps,price=4.))['value_s'])/(2*eps)
        self.assertAlmostEqual(derivative,base['dual_prices'][0],places=8)

    def test_dual_is_global_affine_lower_cut_for_fixed_matrix_and_cost(self):
        base=solve_envelope(**one_dim(.3,price=4.));lam=base['dual_prices'][0]
        for d in [-.2,0.,.1,.5,1.9]:
            value=solve_envelope(**one_dim(d,price=4.))['value_s']
            self.assertGreaterEqual(value+1e-12,base['value_s']+lam*(d-.3))

    def test_two_repairs_choose_faster_supported_mode(self):
        r=solve_envelope([2.,1.],[[1.,1.],[1.,0.],[0.,1.],[-1.,0.],[0.,-1.]],
                         [.6,0.,0.,-.2,-.4])
        self.assertAlmostEqual(r['value_s'],.8)
        self.assertAlmostEqual(r['repair'][0],.2)
        self.assertAlmostEqual(r['repair'][1],.4)

    def test_minimum_margin_cannot_distinguish_different_repair_price(self):
        self.assertAlmostEqual(solve_envelope(**one_dim(.1,price=1.))['value_s'],.1)
        self.assertAlmostEqual(solve_envelope(**one_dim(.1,price=10.))['value_s'],1.)

    def test_more_initial_preparation_can_reduce_total(self):
        no_prepare=0.+solve_envelope(**one_dim(1.))['value_s']
        prepare=.4+solve_envelope(**one_dim(.2))['value_s']
        self.assertAlmostEqual(no_prepare,1.)
        self.assertAlmostEqual(prepare,.6)
        self.assertLess(prepare,no_prepare)

    def test_uncertainty_growth_never_lowers_envelope_with_same_domain(self):
        values=[]
        for radius in [0.,.1,.2]:
            d=tightened_deficit([-.2],[[1.]],[radius],[0.])[0]
            values.append(solve_envelope(**one_dim(d))['value_s'])
        self.assertEqual(values,sorted(values))

    def test_repair_cap_is_not_global_physical_unreachability(self):
        r=solve_envelope(**one_dim(3.))
        self.assertEqual(r['status'],'NO_CERTIFIED_REPAIR_IN_DECLARED_LP')
        self.assertFalse(r['physical_feasibility_proven'])

    def test_same_observation_requires_one_repair_for_hidden_alternatives(self):
        # Hidden states require r>=1 or r<=-1, indistinguishable observation.
        # One common correction cannot satisfy both; clairvoyant +/-1 can.
        same=solve_envelope([0.,1.],[[1.,0.],[-1.,0.],[-1.,1.],[1.,1.],[0.,1.]],
                            [1.,1.,0.,0.,0.])
        self.assertEqual(same['status'],'NO_CERTIFIED_REPAIR_IN_DECLARED_LP')
        separate=observable_cell_value([
            dict(observation_cell_id='observably-left',cost=[0.,1.],
                 matrix=[[1.,0.],[-1.,1.],[1.,1.],[0.,1.]],deficit=[1.,0.,0.,0.]),
            dict(observation_cell_id='observably-right',cost=[0.,1.],
                 matrix=[[-1.,0.],[-1.,1.],[1.,1.],[0.,1.]],deficit=[1.,0.,0.,0.])])
        self.assertEqual(separate['value_s'],1.)
        self.assertFalse(separate['observable_partition_independently_verified'])

    def test_distinct_observation_cost_is_worst_case_not_sum(self):
        r=observable_cell_value([dict(observation_cell_id='o1',**one_dim(.2)),
                                 dict(observation_cell_id='o2',**one_dim(.7))])
        self.assertAlmostEqual(r['value_s'],.7)

    def test_same_observation_id_cannot_create_two_oracle_repairs(self):
        with self.assertRaises(ValueError):observable_cell_value([
            dict(observation_cell_id='same',**one_dim(.2)),
            dict(observation_cell_id='same',**one_dim(.7))])

    def test_zero_std_not_accepted_as_missing_physical_data(self):
        r=solve_envelope(None,None,None)
        self.assertEqual(r['status'],'UNKNOWN')

    def test_invalid_shapes_negative_bounds_and_nonfinite_data(self):
        with self.assertRaises(ValueError):tightened_deficit([0.],[[1.]],[-.1],[0.])
        with self.assertRaises(ValueError):solve_envelope([1.],[[1.,2.]],[0.])
        with self.assertRaises(ValueError):solve_envelope([True],[[1.]],[0.])
        with self.assertRaises(ValueError):solve_envelope([1.],[[1.]],[math.nan])


def rotation(v):
    v=np.asarray(v);a=np.linalg.norm(v)
    if a==0:return np.eye(3)
    K=skew(v/a)
    return np.eye(3)+math.sin(a)*K+(1-math.cos(a))*(K@K)


class PhysicalDifferentialTests(unittest.TestCase):
    def test_relative_hand_map_matches_analytic_transform_differential(self):
        Ro=rotation([.1,-.2,.3]);Rb=rotation([-.2,.1,.2]);f=np.array([.4,.1,.2])
        J=np.array([[.2,0.],[0.,.3],[.1,-.2]]);base=np.array([1.,2.,.3]);obj=np.array([1.1,2.1,.1])
        p=Ro.T@(base+Rb@f-obj)
        r=relative_hand_linearization(Ro,Rb,f,J,p)
        dz=np.array([.1,-.2,.3,.01,.02,-.03,.05,-.04]);de=np.array([.02,.01,-.03,-.01,.02,.03])
        eps=1e-6
        def point(t):
            return (Ro@rotation(t*de[3:])).T@(base+t*dz[:3]+Rb@rotation(t*dz[3:6])@(f+J@(t*dz[6:]))-obj-t*de[:3])
        measured=(point(eps)-point(-eps))/(2*eps)
        predicted=r['repair_matrix']@dz+r['object_error_matrix']@de
        np.testing.assert_allclose(measured,predicted,rtol=0.,atol=2e-10)

    def test_support_moment_map_and_bilinear_remainder_exactly(self):
        feet=np.array([[.3,.2,0.],[.3,-.2,0.],[-.3,.2,0.],[-.3,-.2,0.]])
        c=np.array([0.,0.,.3]);h=np.array([.5,0.,.2]);f=np.array([[1.,0.,50.]]*4);F=np.array([-10.,0.,0.])
        dc=np.array([.01,.02,-.01]);dh=np.array([.02,-.01,.03]);df=np.array([[.1,-.2,.3]]*4);dF=np.array([.2,.1,-.3])
        r=support_moment_linearization(feet,c,h,f,F)
        def moment(c,h,f,F):return np.cross(feet-c,f).sum(axis=0)+np.cross(h-c,F)
        linear=r['foot_force_matrix']@df.ravel()+r['com_matrix']@dc+r['hand_position_matrix']@dh+r['hand_force_matrix']@dF
        remainder=-np.cross(dc,df).sum(axis=0)+np.cross(dh-dc,dF)
        np.testing.assert_allclose(moment(c+dc,h+dh,f+df,F+dF)-moment(c,h,f,F),linear+remainder,atol=2e-14)
        bound=np.linalg.norm(dc)*np.linalg.norm(df,axis=1).sum()+np.linalg.norm(dh-dc)*np.linalg.norm(dF)
        self.assertLessEqual(np.linalg.norm(remainder),bound)

    def test_geometric_signed_margin_row_has_physical_units(self):
        r=relative_hand_linearization(np.eye(3),np.eye(3),[.5,0.,0.],[[0.],[.2],[0.]],[.2,0.,0.])
        normal=np.array([-1.,0.,0.])
        row=normal@r['repair_matrix']
        self.assertEqual(row[0],-1.) # One metre world-x changes plane margin by minus one metre.
        self.assertEqual(row[1],0.)
        self.assertFalse(np.allclose(normal@r['object_error_matrix'],0.))

    def test_wrong_frame_or_contact_mode_rejected(self):
        with self.assertRaises(ValueError):relative_hand_linearization(2*np.eye(3),np.eye(3),[0.,0.,0.],[[0.],[0.],[0.]],[0.,0.,0.])
        with self.assertRaises(ValueError):support_moment_linearization([[0.,0.,0.]]*3,[0.,0.,0.],[0.,0.,0.],[[0.,0.,1.]]*3,[0.,0.,0.])


if __name__=='__main__':unittest.main()
