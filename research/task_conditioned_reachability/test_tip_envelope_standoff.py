"""Synthetic finite-geometry proofs/regressions, not reachable robot trials."""
import math
import unittest
from tip_envelope_standoff import preview_tip_retreat, translate_cloud, tip_sphere_box_gap


class TipEnvelopeTests(unittest.TestCase):
    def test_aligned_frame_recovers_existing_finite_plane_formula(self):
        points=[[-.61,0,0],[-.63,0,.11]]
        a=preview_tip_retreat(points,[.6,.6,.1],[1,0,0],lateral_membership='fixed')
        b=preview_tip_retreat(points,[.6,.6,.1],[1,0,0],lateral_membership='swept')
        self.assertAlmostEqual(a['minimum_front_plane_request_m'],.01)
        self.assertEqual(a['minimum_front_plane_request_m'],b['minimum_front_plane_request_m'])
        self.assertFalse(b['execution_authorized'])

    def test_rotated_lateral_membership_can_enter_after_retreat(self):
        angle=.3;axis=[math.cos(angle),-math.sin(angle),0]
        points=[[-.62+axis[0]*.04,0,0],[-.562,-.621,0]]
        old=preview_tip_retreat(points,[.6,.6,.1],axis,lateral_membership='fixed')
        new=preview_tip_retreat(points,[.6,.6,.1],axis,lateral_membership='swept')
        self.assertEqual(old['critical_point_ids'],[0])
        self.assertTrue(old['request_within_original_domain'])
        self.assertAlmostEqual(old['minimum_front_plane_request_m'],.04)
        moved=translate_cloud(points,axis,old['minimum_front_plane_request_m'])
        self.assertLess(tip_sphere_box_gap(moved[1],[.6,.6,.1],.01),0.)
        self.assertEqual(new['critical_point_ids'],[0,1])
        self.assertFalse(new['request_within_original_domain'])
        # This is an abstract point cloud, NOT evidence the native Piper ever visits it.

    def test_sufficient_final_finite_cloud_bound_over_deterministic_fixtures(self):
        accepted=0
        for angle in [-.3,0,.3]:
            axis=[math.cos(angle),-math.sin(angle),0]
            for x in [-.7,-.64,-.61,-.59]:
                for y in [-.64,-.621,-.4,0,.4,.621,.64]:
                    for z in [-.14,0,.14]:
                        points=[[-.65,0,0],[x,y,z]]
                        r=preview_tip_retreat(points,[.6,.6,.1],axis)
                        if r['request_within_original_domain']:
                            accepted+=1
                            lo=r['minimum_front_plane_request_m']
                            for delta in [lo,(lo+.04)/2,.04]: # includes original grid rounding/+5mm reserve
                                for p in translate_cloud(points,axis,delta):
                                    self.assertGreaterEqual(tip_sphere_box_gap(p,[.6,.6,.1],.01)+1e-12,.01)
        self.assertGreater(accepted,0)

    def test_missing_or_outside_domain_does_not_turn_into_success(self):
        with self.assertRaisesRegex(ValueError,'Missing'):
            preview_tip_retreat([], [.6,.6,.1],[1,0,0])
        with self.assertRaisesRegex(ValueError,'aligned'):
            preview_tip_retreat([[0,0,0]], [.6,.6,.1],[-1,0,0])
        with self.assertRaisesRegex(ValueError,'40mm'):
            preview_tip_retreat([[0,0,0]], [.6,.6,.1],[1,0,0],max_shift_m=.05)
        r=preview_tip_retreat([[0,0,0]], [.6,.6,.1],[1,0,0])
        self.assertFalse(r['request_within_original_domain'])
        self.assertNotEqual(r['status'],'robot_infeasible')

    def test_points_outside_expanded_swept_band_stay_laterally_outside(self):
        axis=[math.cos(.3),-math.sin(.3),0]
        p=[10.,-.7,0] # intentionally no claim this abstract point is robot-reachable
        r=preview_tip_retreat([p],[.6,.6,.1],axis)
        self.assertEqual(r['critical_points'],0)
        for k in range(11):
            moved=translate_cloud([p],axis,.004*k)[0]
            self.assertGreater(abs(moved[1]),.62)


if __name__=='__main__':unittest.main()
