"""Source/config software fixtures only, never physics or new research samples."""
from pathlib import Path
from types import ModuleType,SimpleNamespace
from dataclasses import dataclass,asdict,replace
import ast,copy,importlib.util,json,math,shutil,sys,tempfile,unittest
FORBIDDEN=[]
def code_only_fence(event,args):
 if event=='import' and str(args[0]).split('.')[0] in ('numpy','torch','mujoco','onnxruntime'):
  FORBIDDEN.append(str(args[0]));raise RuntimeError('No numeric/native imports in source fixture tests')
 if event in ('socket.connect','socket.bind','socket.getaddrinfo','subprocess.Popen'):
  FORBIDDEN.append(event);raise RuntimeError('No network/child in source fixture tests')
sys.addaudithook(code_only_fence)
ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/'consumer-deliveries/AINAV-CLIMB-PREPARATION-CANDIDATES-20261113-v1'
SOURCE=BASE/'common-source'
sys.path.insert(0,str(SOURCE))
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
api=load('g2_registered_layout_api',ROOT/'development/registered_layout_conditions_v1/registered_layout_conditions.py')
candidates=load('g2_published_candidate_api',BASE/'climb_preparation_candidates.py')
deploy=load('g2_original_host_profile',SOURCE/'ainav/deployment.py')
planner=load('g2_explicit_three_request_planner',ROOT/'consumer-deliveries/AINAV-NATIVE-PREFIX-CONDITION-PILOT-20261114-v1/source-delta/probe_execution_judge.py')
from ainav.intents import SkillIntent

def sliced_module(name,path,nodes,globals0):
 m=ModuleType(name);m.__file__=str(path);sys.modules[name]=m;m.__dict__.update(globals0)
 exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),'exec'),m.__dict__);return m
ip=SOURCE/'mujoco_zyh/integrated_course.py';tree=ast.parse(ip.read_text())
integrated=sliced_module('g2_exact_original_protocol_source',ip,[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('plan','protocol','validate_protocol','layout')],
 dict(Path=Path,json=json,SCHEMA='piper-continuous-integrated-course-v1',EXECUTION_REVISION=16,PLAN=ip.with_name('integrated_course_plan_v1.json')))
cp=SOURCE/'ainav/native/course_tools.py';ct=ast.parse(cp.read_text())
reference=sliced_module('g2_exact_original_reference',cp,[n for n in ct.body if isinstance(n,ast.ClassDef) and n.name=='PublicReference'],dict(dataclass=dataclass,math=math,NotAdmitted=ValueError))
fc=ast.parse((SOURCE/'ainav/native/full_course.py').read_text());ctor=next(n for n in next(n for n in fc.body if isinstance(n,ast.ClassDef) and n.name=='FullCourse').body if isinstance(n,ast.FunctionDef) and n.name=='__init__')
start=next(i for i,n in enumerate(ctor.body) if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Attribute) and n.targets[0].attr=='entities')
end=next(i for i,n in enumerate(ctor.body) if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Attribute) and n.targets[0].attr=='references')
ej=ast.parse((SOURCE/'ainav/native/execution_judged_course.py').read_text());cat_node=next(n for n in ast.walk(ej) if isinstance(n,ast.FunctionDef) and n.name=='intent_catalogue')
cat=sliced_module('g2_exact_original_semantic_catalogue',SOURCE/'ainav/native/execution_judged_course.py',[cat_node],dict(SkillIntent=SkillIntent,asdict=asdict))

def actual_catalogue_for_software_case(case):
 # Exact source entity/ref AST. No native support is inferred: ground fixture only.
 state=SimpleNamespace(config={'integrated_case':case},intent_sequence=0,_supported=lambda h:h==0.,_dock=lambda body:False,journal=lambda row:'SOFTWARE-fixture')
 ns=dict(self=state,c=case,g=integrated.layout(case),lane=case['lane_y_m'],PublicReference=reference.PublicReference)
 exec(compile(ast.Module(body=ctor.body[start:end+1],type_ignores=[]),str(SOURCE/'ainav/native/full_course.py')+'[public-reference-only]','exec'),ns)
 return cat.intent_catalogue(state,SimpleNamespace(time_s=0.)),state

class RegisteredLayoutSourceTests(unittest.TestCase):
 def setUp(self):self.profile=deploy.HostProfile('G2-source-only','/mnt/explicit-owned-root','cuda:0',0,True)
 def build(self,layout='full-4',side='left',candidate='original',**kw):
  return api.build_condition(selection=api.LayoutCondition(layout,side,candidate),source_root=SOURCE,integrated=integrated,host_profile=self.profile,candidate_api=candidates,enabled=True,**kw)
 def test_default_off_no_source_or_module_touch(self):
  self.assertIsNone(api.build_condition(source_root=object(),integrated=object(),host_profile=object(),candidate_api=object()))
  with self.assertRaises(ValueError):api.build_condition(enabled=1)
 def test_full4_existing_G1_requests_exactly_unchanged(self):
  old=json.loads((ROOT/'consumer-deliveries/AINAV-NATIVE-PREFIX-CONDITION-PILOT-20261114-v1/FIXED_TWO_CONDITIONS.json').read_bytes())
  for c in old['conditions']:
   side=c['condition_id'].rsplit('_',1)[1];v=self.build(side=side)
   self.assertEqual(v['requested_intents'],c['requested_intents']);self.assertEqual(v['runtime_config']['integrated_case']['case_id'],'full-4')
 def test_full2_ground_goals_match_original_source_catalogue(self):
  for side in api.SIDES:
   v=self.build('full-2',side);opts,state=actual_catalogue_for_software_case(v['original_native_protocol']['integrated_case'])
   for req in v['requested_intents']:
    matches=[x for x in opts if x.skill==req['skill'] and x.target_ref==req['target_ref'] and dict(x.parameters)==req['parameters']]
    self.assertEqual(len(matches),1)
   self.assertEqual(v['requested_intents'][1]['parameters']['goal_world_y_m'],-1.9)
   self.assertEqual(v['declared_CLIMB_reference_xy'],list(next(x for x in state.references if x.ref=='cuboid-2:upper-entry').xy))
 def test_all_finite_candidates_use_existing_payload_API(self):
  for layout in api.LAYOUTS:
   for side in api.SIDES:
    for candidate in api.CANDIDATES:
     v=self.build(layout,side,candidate);selected=candidates.selection_from_payload(v['preparation_payload'])
     self.assertEqual(selected.candidate_id,candidate);self.assertEqual(tuple(x['candidate_id'] for x in v['public_prepare_candidates']),api.CANDIDATES)
     self.assertFalse(v['scope_allocated'] or v['physical_admission'] or v['dispatch'] or v['qualified_dynamic_domain'] or v['source_grouping_or_training_roles_assigned'])
 def test_no_other_case_continuous_side_or_candidate(self):
  for args in [('full-1','left','original'),('full-3','left','original'),('full-4','center','original'),('full-2',.15,'original'),('full-2','right','winner'),(True,'left','original')]:
   with self.assertRaises(ValueError):api.LayoutCondition(*args)
 def test_same_materials_seed_and_device_only_overlay(self):
  a=self.build();b=self.build('full-2')
  self.assertEqual(a['original_native_protocol']['registered_materials'],b['original_native_protocol']['registered_materials'])
  self.assertEqual(a['runtime_config']['seed'],b['runtime_config']['seed'])
  for x in [a,b]:
   self.assertEqual({k for k in set(x['original_native_protocol'])|set(x['runtime_config']) if x['original_native_protocol'].get(k)!=x['runtime_config'].get(k)},{'actor_device'})
 def test_source_drift_and_foreign_profile_fail_closed(self):
  with tempfile.TemporaryDirectory() as t:
   new=Path(t)/'AINav/common-source'
   for rel in api.PINS:
    out=new/rel;out.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(SOURCE/rel,out)
   f=new/'mujoco_zyh/integrated_course_plan_v1.json';f.write_bytes(f.read_bytes()+b'\n')
   with self.assertRaisesRegex(ValueError,'source mismatch'):api.build_condition(selection=api.LayoutCondition('full-2','left'),source_root=new,integrated=integrated,host_profile=self.profile,candidate_api=candidates,enabled=True)
  class ForeignProfile:
   def runtime_config(self,p):raise AssertionError('Foreign profile must not be invoked')
  with self.assertRaises(ValueError):api.build_condition(selection=api.LayoutCondition('full-2','left'),source_root=SOURCE,integrated=integrated,host_profile=ForeignProfile(),candidate_api=candidates,enabled=True)
 def test_real_optin3_planner_constructor_accepts_new_exact_requests(self):
  for layout in api.LAYOUTS:
   for side in api.SIDES:
    v=self.build(layout,side);p=planner.RequestedIntentPlanner(copy.deepcopy(v['requested_intents']),lambda row:'SOFTWARE-fixture',**v['planner_constructor_keyword'])
    self.assertEqual(len(p.requests),3);self.assertEqual(p.index,0);self.assertIsNone(p.pending);self.assertFalse(p.complete)
    # Default remains original2. This checks only new request compatibility.
    with self.assertRaises(ValueError):planner.RequestedIntentPlanner(v['requested_intents'],lambda row:'SOFTWARE-fixture')
 def test_foreign_protocol_callable_is_not_accepted(self):
  foreign=ModuleType('g2_foreign_protocol');foreign.__dict__.update(integrated.__dict__);foreign.protocol=lambda case:None
  with self.assertRaisesRegex(ValueError,'callable namespace'):api.build_condition(selection=api.LayoutCondition('full-2','left'),source_root=SOURCE,integrated=foreign,host_profile=self.profile,candidate_api=candidates,enabled=True)
 def test_returns_copies_not_mutated_original_registration(self):
  v=self.build('full-2');v['runtime_config']['integrated_case']['lane_y_m']=99.;v['requested_intents'][0]['parameters']['goal_world_y_m']=99.
  fresh=self.build('full-2');self.assertEqual(fresh['original_native_protocol']['integrated_case']['lane_y_m'],-1.9);self.assertEqual(fresh['requested_intents'][0]['parameters']['goal_world_y_m'],-1.75)

if __name__=='__main__':
 result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(RegisteredLayoutSourceTests))
 print(json.dumps({'role':'SOURCE_SOFTWARE_ONLY_NOT_PHYSICAL_OR_RESEARCH_SAMPLE','tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skips':len(result.skipped),'forbidden_attempts':FORBIDDEN,'Runtime_Actor_world_or_training':False},sort_keys=True))
 sys.exit(0 if result.wasSuccessful() and not FORBIDDEN else 1)
