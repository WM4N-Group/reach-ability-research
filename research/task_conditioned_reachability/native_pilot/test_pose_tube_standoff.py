"""Software algebra tests only, including a known-failure regression; no trials."""
import itertools,math,random,unittest
from pose_tube_standoff import robust_request,rigid_pose_error_bound
from runtime_tip_envelope import choose_request
import numpy as np

class PoseTubeTests(unittest.TestCase):
    def test_no_declared_bound_stays_unknown(self):
        r=robust_request([[-.62,0,0]],[.6,.6,.1],[1,0,0],.015)
        self.assertIsNone(r['required_shift_m']);self.assertFalse(r['runtime_control_authority'])
        self.assertIn('UNKNOWN',r['status'])
    def test_zero_error_reduces_to_frozen_swept_expression(self):
        p=np.array([[-.625,0,.1],[-.61,.615,0],[-.59,.8,0]])
        a=np.array([math.cos(.1),math.sin(.1),0.])
        r=robust_request(p,[.6,.6,.1],a,.015,[0,0,0])
        old,_,_=choose_request(p,np.array([0,40,40]),np.array([.6,.6,.1]),a,.015,'E3')
        self.assertAlmostEqual(r['required_shift_m'],old)
    def test_sampled_bounded_errors_and_retreats_satisfy_conditional_lemma(self):
        rng=random.Random(917)
        for _ in range(12):
            a=[math.cos(.07),math.sin(.07),0.];h=[.6,.6,.1];eps=[.002,.001,.003]
            points=[[rng.uniform(-.65,-.605),rng.uniform(-.64,.64),rng.uniform(-.13,.13)] for _ in range(16)]
            r=robust_request(points,h,a,.015,eps)
            self.assertTrue(r['sufficient_within_cap'])
            for d in [r['required_shift_m'],(r['required_shift_m']+.04)/2,.04]:
                for p in points:
                    for signs in itertools.product([-1,1],repeat=3):
                        actual=[p[j]-d*a[j]+signs[j]*eps[j] for j in range(3)]
                        self.assertTrue(any(abs(actual[j])>=h[j]+.015-1e-12 for j in range(3)))
    def test_known_failure_membership_regression_not_new_validation(self):
        # Rounded known logged witness; this regression is explicitly post-exposure.
        p=[[-.614668,.019274,.122311]]
        old,_,_=choose_request(np.array(p),np.array([40]),np.array([.6,.6,.1]),np.array([1.,0,0]),.020,'E3')
        self.assertEqual(old,0.)
        r=robust_request(p,[.6,.6,.1],[1,0,0],.015,[.0011,.001,.0079])
        self.assertEqual(r['selected_indices'],[0]);self.assertGreater(r['required_shift_m'],0)
        self.assertFalse(r['prospective_bound_verified'])
    def test_rigid_pose_norm_bound(self):
        theta=.08;radius=.7;p=.003
        delta=[radius*(math.cos(theta)-1),radius*math.sin(theta),0]
        n=math.sqrt(sum(v*v for v in delta));self.assertAlmostEqual(n,rigid_pose_error_bound(0,theta,radius))
        actual=[v*(1+p/n) for v in delta]
        self.assertAlmostEqual(math.sqrt(sum(v*v for v in actual)),rigid_pose_error_bound(p,theta,radius))
    def test_cap_exceedance_is_not_robot_infeasibility(self):
        r=robust_request([[-.5,0,0]],[.6,.6,.1],[1,0,0],.015,[0,0,0])
        self.assertFalse(r['sufficient_within_cap']);self.assertFalse(r['runtime_control_authority'])
        self.assertNotIn('infeasible',r['status'].lower())
    def test_invalid_error_and_outside_original_cap_fail_closed(self):
        for e in [[-.001,0,0],[float('nan'),0,0]]:
            with self.assertRaises(ValueError):robust_request([[-.62,0,0]],[.6,.6,.1],[1,0,0],.015,e)
        with self.assertRaises(ValueError):robust_request([[-.62,0,0]],[.6,.6,.1],[1,0,0],.015,[0,0,0],.05)

if __name__=='__main__':unittest.main()
