import ast,io,json,unittest,tempfile,copy
from pathlib import Path
from types import SimpleNamespace
from mujoco_zyh.causal_task_client import choose_tasks,Client
from mujoco_zyh.causal_model_protocol import validate

class Tests(unittest.TestCase):
 def tasks(self):return [dict(skill='nav',goal=[.05,-2.]),dict(skill='climb',surface='B',approach=[.05,-2.]),dict(skill='nav',goal=[2.55,-2.],surface_height=.2),dict(skill='climb',surface='HIGH',approach=[2.55,-2.]),dict(skill='nav',goal=[6.,-2.],surface_height=.4)]
 def test_only_first_goal_x_changed(self):
  old=self.tasks();new=choose_tasks(old,'B_STEP_HIGH_PLATFORM',.02)
  self.assertAlmostEqual(new[0]['goal'][0],.07);self.assertEqual(new[1:],old[1:]);self.assertEqual(old[0]['goal'][0],.05)
 def test_nonregistered_or_other_stage_rejected(self):
  for stage,dx in [('BRIDGE_CLIMB_AND_CROSS',.02),('B_STEP_HIGH_PLATFORM',.03),('B_STEP_HIGH_PLATFORM',True),('B_STEP_HIGH_PLATFORM',float('nan'))]:
   with self.assertRaises(ValueError):choose_tasks(self.tasks(),stage,dx)
 def test_goal_not_silently_rebased(self):
  t=self.tasks();t[0]['goal'][0]=.04
  with self.assertRaises(ValueError):choose_tasks(t,'B_STEP_HIGH_PLATFORM',.02)
 def test_exact_profiles_keep_native_guards_and_no_training(self):
  profiles=json.loads(Path(__file__).with_name('causal_model_profiles.json').read_text())
  for p in profiles.values():
   self.assertEqual(validate(p),p);self.assertFalse(p['training_allowed']);self.assertEqual(p['training_runs'],0);self.assertEqual(p['max_sim_seconds'],420)
   for key,value in [('max_wall_seconds',2401),('seed',2),('training_allowed',True)]:
    q=copy.deepcopy(p);q[key]=value
    with self.assertRaises(ValueError):validate(q)
 def test_frozen_parent_class_actually_consumes_model_parameter_fixture(self):
  source=Path(__file__).with_name('integrated_course.py').read_text();node=next(n for n in ast.parse(source).body if isinstance(n,ast.ClassDef) and n.name=='IntegratedRouter')
  ns={'json':json};exec(compile(ast.Module(body=[node],type_ignores=[]),'[unchanged parent class AST fixture]','exec'),ns)
  router=object.__new__(ns['IntegratedRouter']);router.r=SimpleNamespace(sim=SimpleNamespace(data=SimpleNamespace(time=1.)))
  router.prefix=SimpleNamespace(close=lambda:None);router.log=io.StringIO();router.extra_events=[];router.chunks=[];router.stage='A_FAIL_RECOVER_RESELECT_B'
  class NativeFixture:
   def __init__(self,r,tasks):self.tasks=tasks
   def enter(self):self.entered=True
  router.Native=NativeFixture
  observer=SimpleNamespace(snapshot=lambda:0,unchanged=lambda a,b:a==b)
  with tempfile.TemporaryDirectory() as tmp:
   p=dict(causal_model_policy=dict(normalizer=dict(mean=[0.]*45,scale=[1.]*45),method='dino',checkpoint_sha256='fixture'))
   client=Client(router,observer,p,tmp)
   client.request=lambda tasks,stage:(.02,dict(model_forecasts=3,request_sha256='fixture',checkpoint_sha256='fixture'))
   router.start_chunk(self.tasks(),'B_STEP_HIGH_PLATFORM')
   self.assertAlmostEqual(router.active.tasks[0]['goal'][0],.07);self.assertTrue(router.active.entered);self.assertEqual(client.accepted,1)
   with self.assertRaises(ValueError):router.start_chunk(self.tasks(),'B_STEP_HIGH_PLATFORM')
   router.close()
 def test_no_private_object_or_stepping_accessor_in_client(self):
  tree=ast.parse(Path(__file__).with_name('causal_task_client.py').read_text());attrs={n.attr for n in ast.walk(tree) if isinstance(n,ast.Attribute)}
  self.assertFalse(attrs & {'xpos','xquat','body_mass','reset','mj_step','step','private_catalog'})

if __name__=='__main__':unittest.main()
