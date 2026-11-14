import unittest
import numpy as np
from mujoco_zyh.visible_surface_goal import front_plane,FrontPlaneConfig,describe_visible_goal

class VisibleFrontTests(unittest.TestCase):
    def points(self):
        y,z=np.meshgrid(np.linspace(-.4,.4,30),np.linspace(-.25,-.05,12));return np.stack([np.ones(y.size),y.ravel(),z.ravel()],1)
    def test_plane_is_relative_and_robust_to_outliers_without_object_truth(self):
        p=self.points();r=np.random.default_rng(5);bad=r.uniform([.3,-1,-.5],[1.8,1,.2],size=(50,3))
        before=p.copy();result=front_plane(np.r_[p,bad])
        self.assertAlmostEqual(result['plane_offset_body_m'],1.,places=4);self.assertGreater(result['normal_body_xyz'][0],.9999)
        self.assertTrue(np.array_equal(p,before));self.assertFalse(result['full_box_center_or_extent_inferred'])
    def test_visible_front_plane_can_be_minority_beside_larger_top_surface(self):
        front=self.points();x,y=np.meshgrid(np.linspace(1.02,3.,50),np.linspace(-.4,.4,30))
        top=np.stack([x.ravel(),y.ravel(),np.full(x.size,-.05)],1)
        result=front_plane(np.r_[front,top]);self.assertGreater(result['normal_body_xyz'][0],.999)
        self.assertAlmostEqual(result['plane_offset_body_m'],1.,places=4)
        self.assertLess(result['inlier_fraction'],.5)

    def test_flat_horizontal_or_too_short_surfaces_are_rejected(self):
        p=self.points();p[:,0],p[:,2]=p[:,2].copy(),p[:,0].copy()
        with self.assertRaises(ValueError):front_plane(p)
        p=self.points();p[:,2]*=.001
        with self.assertRaises(ValueError):front_plane(p)
    def test_stale_pixels_or_declared_nonfinite_standoff_fail_closed(self):
        rgb=np.zeros((32,48,3),np.uint8);depth=np.ones((32,48));K=np.array([[30.,0,24],[0,30,16],[0,0,1.]])
        with self.assertRaises(ValueError):describe_visible_goal(rgb,depth,K,np.eye(4),frame_local_ref='old',current_RGB_sha256='bad',standoff_m=1.05)
        with self.assertRaises(ValueError):describe_visible_goal(rgb,depth,K,np.eye(4),frame_local_ref='old',current_RGB_sha256='bad',standoff_m=float('nan'))
    def test_plane_does_not_turn_side_face_into_frontal_target(self):
        p=self.points();a=np.deg2rad(65);R=np.array([[np.cos(a),-np.sin(a),0],[np.sin(a),np.cos(a),0],[0,0,1]])
        with self.assertRaises(ValueError):front_plane(p@R.T)
