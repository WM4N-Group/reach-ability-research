import unittest, copy, importlib.util, hashlib
from pathlib import Path
from types import SimpleNamespace
import v4_native_asset as v4

REG=Path('/home/yuanyue/main/work/ainav/src/ainav/native/scene_registry.py')
def load(name,path):
 import sys
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
class Tests(unittest.TestCase):
 def setUp(self):self.s=v4.load_scene()
 def test_registry_elevated(self):
  r=v4.registry(self.s,load('actual_registry_v4_test',REG))
  self.assertEqual(r.goal.surface_ref,'goal_deck');self.assertEqual(r.surfaces['goal_deck'].top_z_m,.6);self.assertEqual(len(r.objects),3)
 def test_ground_goal_rejected(self):
  self.s['task']['goal_surface_ref']='ground'
  with self.assertRaises(ValueError):v4.validate(self.s)
 def test_no_fake_height(self):
  self.s['platforms'][0]['top_z_m']=.4
  with self.assertRaises(ValueError):v4.validate(self.s)
 def test_no_missing_climb(self):
  self.s['private_terminal_acceptance']['requires_actual_CLIMB_success_receipts']=False
  with self.assertRaises(ValueError):v4.validate(self.s)
 def test_no_two_object_terminal(self):
  self.s['private_terminal_acceptance']['required_distinct_original_placement_receipts']=2
  with self.assertRaises(ValueError):v4.validate(self.s)
 def test_no_changed_material(self):
  self.s['objects'][0]['mass_kg']=20.
  with self.assertRaises(ValueError):v4.validate(self.s)
 def test_public_no_route(self):
  base=load('actual_complex_v4_test',v4.BASE_PATH);r=v4.public_task(self.s,base)
  self.assertNotIn('review_climb_geometry',r);self.assertTrue(r['correct_order_or_route_not_provided']);self.assertEqual(r['platforms'][0]['top_z_m'],.6)
 def test_construct_order_fixture_not_physics(self):
  calls=[];geoms=[]
  def add(**kw):calls.append(kw);geoms.append(SimpleNamespace(name=kw['name']))
  def construct(sim,**kw):
   self.assertEqual(geoms[0].name,'goal_deck');return {'software_fixture':True}
  base=SimpleNamespace(__file__=__file__,validate=lambda s:None,construct_into_native_spec=construct)
  sim=SimpleNamespace(data=SimpleNamespace(time=0.),queue=[],spec=SimpleNamespace(geoms=geoms,bodies=[],worldbody=SimpleNamespace(add_geom=add)))
  args=dict(scene=self.s,main_steps=0,base_module=base,expected_base_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),mujoco_api=SimpleNamespace(mjtGeom=SimpleNamespace(mjGEOM_BOX=6)))
  out=v4.construct_into_native_spec(sim,**args);self.assertFalse(out['physical_dispatch_authorized']);self.assertEqual(calls[0]['pos'][2],.3)
  with self.assertRaises(ValueError):v4.construct_into_native_spec(sim,**args)
 def test_no_live_state(self):
  sim=SimpleNamespace(data=SimpleNamespace(time=1.),queue=[])
  with self.assertRaises(ValueError):v4.construct_into_native_spec(sim,scene=self.s,main_steps=0,base_module=None,expected_base_sha256='',mujoco_api=None)
if __name__=='__main__':unittest.main()
