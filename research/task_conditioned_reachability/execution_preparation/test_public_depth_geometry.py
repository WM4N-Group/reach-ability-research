"""Geometry/role semantics checks only, no rendered or measured test scenes."""
from copy import deepcopy
import math
import unittest
from .public_depth_geometry import visible_point

K=[[100.,0.,50.],[0.,100.,50.],[0.,0.,1.]]
T=[[0.,0.,1.,.2],[-1.,0.,0.,0.],[0.,-1.,0.,.1],[0.,0.,0.,1.]]


class PublicDepthGeometryTests(unittest.TestCase):
    def point(self,uv=(50.,50.),depth=2.,**kwargs):
        params=dict(image_size_wh=(100,100),acquisition_time_s=10.,decision_time_s=10.,
                    source_role='ONLINE_PUBLIC',source_ref='CPU_PUBLIC_GEOMETRY_NOT_ACTUAL_PACKET')
        params.update(kwargs)
        return visible_point(uv,depth,K,T,**params)

    def test_principal_ray_and_optical_to_body_axis_convention(self):
        p=self.point();self.assertEqual(p['optical_xyz_m'],[0.,0.,2.]);self.assertEqual(p['body_xyz_m'],[2.2,0.,.1])

    def test_off_axis_is_optical_z_not_euclidean_range(self):
        p=self.point((60.,60.));self.assertEqual(p['optical_xyz_m'],[.2,.2,2.])
        self.assertAlmostEqual(p['body_xyz_m'][1],-.2);self.assertAlmostEqual(p['body_xyz_m'][2],-.1)
        self.assertGreater(math.hypot(*p['optical_xyz_m']),2.)
        with self.assertRaisesRegex(ValueError,'not Euclidean'):self.point(depth_convention='RAY_RANGE')

    def test_surface_point_not_published_as_object_center_or_native_reference_pose(self):
        p=self.point();self.assertFalse(p['object_identity_or_center_inferred'])
        self.assertEqual(p['public_object_geometry'],dict(status='unknown',source='unavailable',values={},uncertainty={}))
        self.assertIsNone(p['registered_reference_relative_pose']);self.assertIsNone(p['depth_error_bound_m'])
        self.assertEqual(p['native_READY_or_support_or_cost_prediction'],'UNKNOWN')

    def test_audit_role_retained_never_promoted_to_online_feature(self):
        p=self.point(source_role='AUDIT_ONLY',decision_time_s=20.)
        self.assertEqual(p['source_role'],'AUDIT_ONLY');self.assertIsNotNone(p['body_xyz_m'])
        self.assertFalse(p['prospective_feature_from_historical_audit_allowed']);self.assertFalse(p['execution_authorized'])

    def test_future_depth_rejected_and_stale_online_kept_unknown(self):
        with self.assertRaisesRegex(ValueError,'Causal'):self.point(decision_time_s=9.)
        p=self.point(decision_time_s=10.2);self.assertEqual(p['status'],'UNKNOWN_STALE_PUBLIC_DEPTH');self.assertIsNone(p['body_xyz_m'])

    def test_missing_nan_nonpositive_or_bool_depth_not_zero_filled(self):
        for depth in (None,float('nan'),float('inf'),0.,-1.,True):
            p=self.point(depth=depth);self.assertEqual(p['status'],'UNKNOWN_NO_VALID_DEPTH');self.assertIsNone(p['body_xyz_m'])

    def test_outside_or_boolean_pixel_rejected(self):
        for uv in ((-1.,0.),(100.,50.),(50.,100.),(True,50.)):
            with self.assertRaisesRegex(ValueError,'pixel inside'):self.point(uv)

    def test_nonrigid_reflected_and_bad_intrinsics_rejected(self):
        args=dict(image_size_wh=(100,100),acquisition_time_s=10.,decision_time_s=10.,source_role='ONLINE_PUBLIC',source_ref='CPU')
        for change in ('scale','reflection','bottom'):
            matrix=deepcopy(T)
            if change=='scale':matrix[0][2]=2.
            elif change=='reflection':matrix[0][2]=-1.
            else:matrix[3][3]=2.
            with self.assertRaises(ValueError):visible_point((50.,50.),2.,K,matrix,**args)
        bad=deepcopy(K);bad[0][0]=0.
        with self.assertRaisesRegex(ValueError,'intrinsics'):visible_point((50.,50.),2.,bad,T,**args)

    def test_numeric_validation_tolerance_is_not_a_physical_error_bound(self):
        p=self.point();self.assertIsNone(p['physical_calibration_error_bound_m'])
        self.assertFalse(p['exact_pixel_center_alignment_proven'])

    def test_no_private_geometry_role_or_calibration_mutation(self):
        with self.assertRaisesRegex(ValueError,'never private'):self.point(source_role='PRIVATE_GT')
        before=deepcopy((K,T));self.point();self.assertEqual((K,T),before)


if __name__=='__main__':unittest.main()
