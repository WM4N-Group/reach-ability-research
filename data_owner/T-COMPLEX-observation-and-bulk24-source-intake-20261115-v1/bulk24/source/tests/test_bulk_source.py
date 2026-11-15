"""SOFTWARE fixtures for new source plan only. No world/Actor/fit/real samples."""
from pathlib import Path
from types import ModuleType,SimpleNamespace
from dataclasses import dataclass,asdict
import ast,copy,importlib.util,json,math,shutil,sys,tempfile,unittest
blocked=[]
def fence(event,args):
 if event=='import'and str(args[0]).split('.')[0]in('numpy','torch','mujoco','onnxruntime'):blocked.append(str(args[0]));raise RuntimeError('Software source only')
 if event in('socket.connect','socket.bind','socket.getaddrinfo','subprocess.Popen'):blocked.append(event);raise RuntimeError('No network/child')
sys.addaudithook(fence)
ROOT=Path(__file__).resolve().parents[3];OWN=Path(__file__).resolve().parents[1];BASE=ROOT/'consumer-deliveries/AINAV-CLIMB-PREPARATION-CANDIDATES-20261113-v1';SOURCE=BASE/'common-source'
sys.path[:0]=[str(OWN),str(SOURCE)]
import bulk_registered_conditions as api
from ainav.intents import SkillIntent

def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m

def sliced(name,path,nodes,values):
 m=ModuleType(name);m.__file__=str(path);sys.modules[name]=m;m.__dict__.update(values);exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),'exec'),m.__dict__);return m

class BulkSourceTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory();cls.source=Path(cls.tmp.name)/'AINav/common-source'
  for rel in api.PINS:
   target=cls.source/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(SOURCE/rel,target)
  plan=cls.source/'mujoco_zyh/integrated_course_plan_v1.json';plan.write_bytes(api.source_delta(enabled=True)['replacement_bytes'])
  cp=cls.source.parent/'climb_preparation_candidates.py';shutil.copyfile(BASE/'climb_preparation_candidates.py',cp);cls.candidates=load('bulk_original_finite_candidates_fixture',cp)
  dep=load('bulk_original_host_fixture',cls.source/'ainav/deployment.py');cls.profile=dep.HostProfile('SOFTWARE-only','/SOFTWARE-not-an-episode','cuda:0',0,True)
  ip=cls.source/'mujoco_zyh/integrated_course.py';tree=ast.parse(ip.read_text());cls.integrated=sliced('bulk_original_protocol_fixture',ip,[n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name in('plan','protocol','validate_protocol','layout')],dict(Path=Path,json=json,SCHEMA='piper-continuous-integrated-course-v1',EXECUTION_REVISION=16,PLAN=plan))
  cp=SOURCE/'ainav/native/course_tools.py';cls.reference=sliced('bulk_original_reference_fixture',cp,[n for n in ast.parse(cp.read_text()).body if isinstance(n,ast.ClassDef)and n.name=='PublicReference'],dict(dataclass=dataclass,math=math,NotAdmitted=ValueError))
  fc=ast.parse((SOURCE/'ainav/native/full_course.py').read_text());ctor=next(n for n in next(n for n in fc.body if isinstance(n,ast.ClassDef)and n.name=='FullCourse').body if isinstance(n,ast.FunctionDef)and n.name=='__init__')
  start=next(i for i,n in enumerate(ctor.body)if isinstance(n,ast.Assign)and isinstance(n.targets[0],ast.Attribute)and n.targets[0].attr=='entities');end=next(i for i,n in enumerate(ctor.body)if isinstance(n,ast.Assign)and isinstance(n.targets[0],ast.Attribute)and n.targets[0].attr=='references');cls.reference_nodes=ctor.body[start:end+1]
  ep=SOURCE/'ainav/native/execution_judged_course.py';cat=next(n for n in ast.walk(ast.parse(ep.read_text()))if isinstance(n,ast.FunctionDef)and n.name=='intent_catalogue');cls.catalogue=sliced('bulk_original_catalogue_fixture',ep,[cat],dict(SkillIntent=SkillIntent,asdict=asdict))
  cls.planner=load('bulk_original_optin3_fixture',ROOT/'consumer-deliveries/AINAV-NATIVE-PREFIX-CONDITION-PILOT-20261114-v1/source-delta/probe_execution_judge.py')
 @classmethod
 def tearDownClass(cls):cls.tmp.cleanup()
 def build(self,group='bulk-g01',side='left',candidate='original',**kw):
  return api.build_condition(selection=api.BulkCondition(group,side,candidate),source_root=self.source,integrated=self.integrated,host_profile=self.profile,candidate_api=self.candidates,enabled=True,**kw)
 def test_default_off_and_no_installation_function(self):
  self.assertIsNone(api.build_condition(source_root=object(),integrated=object()));self.assertIsNone(api.source_delta())
  with self.assertRaises(ValueError):api.source_delta(enabled=1)
  self.assertFalse(api.source_delta(enabled=True)['install_performed'])
 def test_original_five_unchanged_and_ten_real_lane_width_geometries(self):
  old=json.loads((SOURCE/'mujoco_zyh/integrated_course_plan_v1.json').read_bytes());new=self.integrated.plan();self.assertEqual(new['cases'][:5],old['cases']);self.assertEqual(len(new['cases']),15)
  rows=new['cases'][5:];self.assertEqual(len({(v['lane_y_m'],v['step_width_m'])for v in rows}),10)
  base=next(c for c in old['cases']if c['case_id']=='full-4')
  for c in rows:self.assertLessEqual({k for k in base if c[k]!=base[k]},{'case_id','lane_y_m','step_width_m'})
 def test_all_sixty_finite_bindings_match_actual_original_ground_catalogue(self):
  for group in api.GROUPS:
   for side in api.PREFIXES:
    for candidate in api.CANDIDATES:
     v=self.build(group,side,candidate);case=v['runtime_config']['integrated_case'];state=SimpleNamespace(config={'integrated_case':case},intent_sequence=0,_supported=lambda h:h==0.,_dock=lambda body:False,journal=lambda row:'SOFTWARE-only')
     ns=dict(self=state,c=case,g=self.integrated.layout(case),lane=case['lane_y_m'],PublicReference=self.reference.PublicReference)
     exec(compile(ast.Module(body=self.reference_nodes,type_ignores=[]),'<original-public-reference-SOFTWARE-only>','exec'),ns)
     opts=self.catalogue.intent_catalogue(state,SimpleNamespace(time_s=0.))
     for req in v['requested_intents']:self.assertEqual(sum(o.skill==req['skill']and o.target_ref==req['target_ref']and dict(o.parameters)==req['parameters']for o in opts),1)
     p=self.planner.RequestedIntentPlanner(copy.deepcopy(v['requested_intents']),lambda row:'SOFTWARE-only',**v['planner_constructor_keyword']);self.assertEqual(len(p.requests),3);self.assertFalse(p.complete)
 def test_material_seed_actor_source_gates_and_flags_not_changed(self):
  v=self.build();n=v['original_native_protocol'];baseline=self.integrated.protocol(next(c for c in self.integrated.plan()['cases']if c['case_id']=='full-4'))
  self.assertEqual(n['registered_materials'],baseline['registered_materials']);self.assertEqual(n['seed'],4301);self.assertFalse(n['training_allowed']or n['automatic_retry']or n['reset_after_initial_allowed'])
  self.assertEqual({k for k in set(n)|set(v['runtime_config'])if n.get(k)!=v['runtime_config'].get(k)},{'actor_device'})
  self.assertFalse(v['dispatch']or v['physical_admission']or v['qualified_dynamic_domain']or v['source_grouping_or_training_roles_assigned'])
 def test_old_plan_or_source_drift_refuses_not_a_fallback(self):
  with self.assertRaisesRegex(ValueError,'source mismatch'):api.build_condition(selection=api.BulkCondition('bulk-g01','left'),source_root=SOURCE,integrated=self.integrated,host_profile=self.profile,candidate_api=self.candidates,enabled=True)
  p=self.source/'mujoco_zyh/integrated_course_plan_v1.json';raw=p.read_bytes()
  try:
   p.write_bytes(raw+b'\n')
   with self.assertRaisesRegex(ValueError,'source mismatch'):self.build()
  finally:p.write_bytes(raw)
 def test_arbitrary_groups_prefixes_candidates_and_foreign_modules_rejected(self):
  for args in [('full-4','left','original'),('bulk-g11','left','original'),('bulk-g01','center','original'),('bulk-g01','left','best')]:
   with self.assertRaises(ValueError):api.BulkCondition(*args)
  with self.assertRaisesRegex(ValueError,'same-source module'):api.build_condition(selection=api.BulkCondition('bulk-g01','left'),source_root=self.source,integrated=SimpleNamespace(__file__=__file__),host_profile=self.profile,candidate_api=self.candidates,enabled=True)
 def test_all_variants_keep_one_shared_ancestor_not_ten_holdouts(self):
  vals=[self.build(g)for g in api.GROUPS];self.assertEqual(len({v['ancestor_case_canonical_sha256']for v in vals}),1)
  self.assertTrue(all(v['shared_ancestor_family']and not v['independent_scene_group_proven']and v['role']=='UNASSIGNED_NO_FIT_OR_DISPATCH'for v in vals))
if __name__=='__main__':
 r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(BulkSourceTests));print(json.dumps(dict(role='SOFTWARE_SOURCE_MATRIX_NOT_RESEARCH_SAMPLES',checks=r.testsRun,failures=len(r.failures),errors=len(r.errors),forbidden_attempts=blocked,native_worlds_or_fits=0)));sys.exit(0 if r.wasSuccessful()and not blocked else 1)
