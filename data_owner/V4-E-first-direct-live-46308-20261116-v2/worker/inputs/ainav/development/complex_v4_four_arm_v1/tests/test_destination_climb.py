"""Exact source-binder arithmetic and original planner callbacks, no native use."""
from pathlib import Path
from types import SimpleNamespace as NS
import sys,ast,math,json,unittest
OWN=Path(__file__).resolve().parents[1];ROOT=OWN.parents[1];SOURCE=ROOT/'consumer-deliveries/AINAV-CLIMB-PREPARATION-CANDIDATES-20261113-v1/common-source';sys.path[:0]=[str(OWN),str(SOURCE)];blocked=[]
def fence(event,args):
 if event=='import'and str(args[0]).split('.')[0]in('numpy','torch','mujoco','onnxruntime'):blocked.append(str(args[0]));raise RuntimeError('Software only')
 if event in('socket.connect','socket.bind','socket.getaddrinfo','subprocess.Popen'):blocked.append(event);raise RuntimeError('No network/child')
sys.addaudithook(fence)
import destination_climb as d
from ainav.native import registered_climb as original
from ainav.native.behavior_authority import BehaviorOption,NativeReceipt
from ainav.intents import SkillIntent
from ainav.contracts import Primitive,SkillPlan
from ainav.planner import AinavPlanner,Selection
class Tests(unittest.TestCase):
 def setUp(self):
  self.query='f'*64;self.source_height=0.;self.top=.2;self.target=NS(target_ref='SOFTWARE-opaque',query_sha256=self.query,body_name='SOFTWARE-box',body_id=23)
  self.registry=NS(objects={'cuboid_c':NS(ref='cuboid_c',body_name='SOFTWARE-box')},surfaces={'ground':NS(top_z_m=0.)},retired_objects=frozenset())
  self.host=NS(registry=self.registry,runtime=NS(sim=NS(model=NS(body=lambda name:NS(id=23)),data=NS(qpos=[0.,0.]))),resolver=NS(targets_for_query=lambda runtime,query:[self.target]))
 def pure_bind(self,destination=.2):
  # Isolate only the changed exact function. Its single dependency import is
  # replaced by an explicit SOFTWARE geometry fixture, never production code.
  changed,_=d._changed_bind_source((SOURCE/'ainav/native/registered_climb.py').read_text());tree=ast.parse(changed);tree.body[0].body=[n for n in tree.body[0].body if not isinstance(n,(ast.Import,ast.ImportFrom))]
  registry_tree=ast.parse((SOURCE/'ainav/native/scene_registry.py').read_text());cls=next(n for n in registry_tree.body if isinstance(n,ast.ClassDef)and n.name=='RegisteredTerrain');fn=next(n for n in cls.body if isinstance(n,ast.FunctionDef)and n.name=='climb_geometry');ns={'math':math};exec(compile(ast.Module(body=[fn],type_ignores=[]),'SOFTWARE-original-height-predicate','exec'),ns);height_check=ns['climb_geometry'];test=self
  class Terrain:
   def __init__(self,registry):pass
   def surface_geometry(self,sim,ref):return dict(top=test.top,front=.58,length=2.4,width=1.4,lane_y_m=0.)
   def climb_geometry(self,sim,ref,*,source_surface_height_m):return height_check(self,sim,ref,source_surface_height_m=source_surface_height_m)
  namespace=dict(math=math,RegisteredTerrain=Terrain,ClimbBinding=original.ClimbBinding,check_climb_native_domain=original.check_climb_native_domain);exec(compile(tree,'SOFTWARE-exact-bind-with-explicit-geometry-fixture','exec'),namespace)
  option=BehaviorOption('SOFTWARE-native','CLIMB','SOFTWARE-opaque',(('surface_height_m',destination),),60.,'SOFTWARE-only');before=(option.parameters,option.sha256);result=namespace['bind'](self.host,NS(sha256=self.query),(option,),'ground');self.assertEqual(before,(option.parameters,option.sha256));return option,result[option.sha256]
 def test_default_off_and_original_construct_inherited_exactly(self):
  self.assertIsNone(d.adapter_class());cls=d.adapter_class(source_root=SOURCE,enabled=True);self.assertIs(cls.construct,original.RegisteredClimbAdapter.construct);self.assertTrue(cls.source_delta_receipt['source_delta_exactly_invertible'])
 def test_destination_kept_while_source_height_only_in_private_binding(self):
  option,b=self.pure_bind();self.assertEqual(dict(option.parameters)['surface_height_m'],.2);self.assertEqual(dict(b.geometry)['base_height'],0.);self.assertEqual(dict(b.geometry)['top'],.2);self.assertEqual(b.option_sha256,option.sha256)
 def test_public_destination_mismatch_is_not_ignored(self):
  with self.assertRaisesRegex(ValueError,'destination differs'):self.pure_bind(.4)
 def test_original40cm_rejection_not_relaxed(self):
  self.registry.surfaces['ground'].top_z_m=.2;self.top=.6
  with self.assertRaisesRegex(ValueError,'Original 20cm'):self.pure_bind(.6)
 def test_static_deck_still_not_movable_RGBD_object(self):
  self.registry.objects={}
  with self.assertRaisesRegex(ValueError,'registered climb body'):self.pure_bind()
 def test_wrong_current_query_still_refuses(self):
  self.target.query_sha256='e'*64
  with self.assertRaisesRegex(ValueError,'current RGBD'):self.pure_bind()
 def test_actual_wrapper_requires_live_source_witness_before_any_native_use(self):
  cls=d.adapter_class(source_root=SOURCE,enabled=True);instance=cls(self.host.runtime,self.registry,self.host.resolver,journal=lambda row:'SOFTWARE-only')
  with self.assertRaises(ValueError):instance.bind(NS(),(), 'ground')
  self.assertFalse(blocked)
 def test_original_AINav_same_params_and_receipt_hash_checks_work_unchanged(self):
  option,binding=self.pure_bind();intent=SkillIntent('SOFTWARE-intent','CLIMB','cuboid_c:upper-entry',(('surface_height_m',.2),));primitive=Primitive.from_option(intent)
  def planner():
   p=AinavPlanner(NS(),lambda row:'SOFTWARE-only');p.tree.add((SkillPlan('SOFTWARE',(primitive,),False),));p.pending=Selection(self.query,intent.token,intent.sha256,primitive.key,p.tree.revision,'SOFTWARE-only');return p
  p=planner();receipt=NativeReceipt(option.sha256,1.,'succeeded','d'*64,'SOFTWARE-actual-hash-fixture');p.observe_intent(intent,option,receipt,'SOFTWARE-private-binding');self.assertEqual(len(p.tree.history),1);self.assertIsNone(p.pending)
  wrong=BehaviorOption('SOFTWARE-source-parameter','CLIMB','SOFTWARE-opaque',(('surface_height_m',0.),),60.,'SOFTWARE-only');p=planner()
  with self.assertRaises(ValueError):p.observe_intent(intent,wrong,NativeReceipt(wrong.sha256,1.,'succeeded','d'*64,'SOFTWARE'), 'SOFTWARE')
  self.assertFalse(p.tree.history)
if __name__=='__main__':
 r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests));print(json.dumps(dict(role='V4_CLIMB_DESTINATION_SOURCE_MAPPING_SOFTWARE_ONLY_ORIGINAL_CHECKS_RETAINED',checks=r.testsRun,failures=len(r.failures),errors=len(r.errors),forbidden_attempts=blocked,actual_native_construct_step_Actor_API_calls=0)));sys.exit(0 if r.wasSuccessful()and not blocked else 1)
