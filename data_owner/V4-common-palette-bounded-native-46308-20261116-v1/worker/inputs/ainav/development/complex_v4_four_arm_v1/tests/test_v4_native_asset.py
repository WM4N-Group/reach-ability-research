# Software only: real pure frozen APIs, no world/Actor/native compile/network.
import sys
OWN=__import__('pathlib').Path(__file__).resolve().parents[1]
ROOT=OWN.parents[1]
SOURCE=ROOT/'consumer-deliveries/AINAV-CLIMB-PREPARATION-CANDIDATES-20261113-v1/common-source'
sys.path.insert(0,str(OWN))
blocked=[]
def fence(event,args):
 if event=='import'and str(args[0]).split('.')[0]in('numpy','torch','mujoco','onnxruntime'):blocked.append(str(args[0]));raise RuntimeError('Software only')
 if event in('socket.connect','socket.bind','socket.getaddrinfo','subprocess.Popen'):blocked.append(event);raise RuntimeError('No network/child')
sys.addaudithook(fence)
import unittest, copy, importlib.util, hashlib
from pathlib import Path
from types import SimpleNamespace
import v4_native_asset as v4

REG=SOURCE/'ainav/native/scene_registry.py'
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
 def test_selected_original_rise_domain_rejects_V4_second_leg(self):
  from capability_boundary import selected_climb_rise_audit
  r=selected_climb_rise_audit(self.s,common_source_root=SOURCE)
  self.assertTrue(r['legs'][0]['original_pure_height_predicate_accepts']);self.assertFalse(r['legs'][1]['original_pure_height_predicate_accepts']);self.assertFalse(r['planned_two_leg_chain_in_selected_height_domain']);self.assertTrue(r['static_goal_deck_not_a_registered_movable_object'])
 def sample(self,z=.622,support='goal_deck'):
  return dict(feet_world_m=[[14.,-2.6,z]]*4,foot_normal_N=[12.]*4,foot_speed_m_s=[0.]*4,base_linear_speed_m_s=0.,base_angular_speed_rad_s=0.,tilt_rad=0.,foot_support_refs=[support]*4)
 def test_elevated_sample_accepts_only_necessary_not_task_evidence(self):
  from capability_boundary import elevated_stop_sample_only
  self.assertTrue(elevated_stop_sample_only(self.s,self.sample()))
 def test_same_goal_XY_on_ground_is_not_V4_stop(self):
  from capability_boundary import elevated_stop_sample_only
  self.assertFalse(elevated_stop_sample_only(self.s,self.sample(.022)))
 def test_false_height_or_wrong_contact_support_cannot_pass(self):
  from capability_boundary import elevated_stop_sample_only
  self.assertFalse(elevated_stop_sample_only(self.s,self.sample(.622,'ground')))
  sample=self.sample();sample['foot_normal_N'][0]=11.999
  self.assertFalse(elevated_stop_sample_only(self.s,sample))
 def test_original_foot_speed_and_stop_thresholds_unchanged(self):
  from capability_boundary import elevated_stop_sample_only
  sample=self.sample();sample['foot_speed_m_s'][0]=.03
  self.assertFalse(elevated_stop_sample_only(self.s,sample))
if __name__=='__main__':
 import json
 result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
 print(json.dumps(dict(role='V4_SOURCE_AND_CAPABILITY_SOFTWARE_ONLY_NOT_NATIVE_OR_RESEARCH_RESULT',checks=result.testsRun,failures=len(result.failures),errors=len(result.errors),forbidden_attempts=blocked,worlds=0,fit=0)))
 sys.exit(0 if result.wasSuccessful()and not blocked else 1)
