"""Original state machine + explicit fake native services. NO physical success."""
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
import sys,unittest,copy,json
OWN=Path(__file__).resolve().parents[1];ROOT=OWN.parents[1];SOURCE=ROOT/'consumer-deliveries/AINAV-CLIMB-PREPARATION-CANDIDATES-20261113-v1/common-source'
sys.path[:0]=[str(OWN),str(SOURCE)]
blocked=[]
def fence(event,args):
 if event=='import'and str(args[0]).split('.')[0]in('numpy','torch','mujoco','onnxruntime'):
  blocked.append(str(args[0]));raise RuntimeError('Explicit fake services only')
 if event in('socket.connect','socket.bind','socket.getaddrinfo','subprocess.Popen'):
  blocked.append(event);raise RuntimeError('No network/child')
sys.addaudithook(fence)
import pre_arrival_brake as helper
from ainav.native.placement_handoff import TwoPhasePlacementMachine as Base
from ainav.native.placement_contract import PlacementContract

class Tests(unittest.TestCase):
 def setUp(self):
  self.cls=helper.machine_class(source_root=SOURCE,enabled=True)
  self.contract=PlacementContract('fixture',(2.6,0.),3.8,(2.4,1.4,.2),0.,.11,'declared_native_stop_offset')
  self.rows=[];self.ready=False;self.steps=0;self.brake_updates=0;self.begins=0
  self.phase='prepare';self.pose=[2.565,0.,.1];self.velocity=[.3,0.,0.]
  self.native=NS(phase='prepare',finish=None,results=[],update=lambda:setattr(self,'steps',self.steps+1))
  self.brake=NS(complete=False,update=lambda:setattr(self,'brake_updates',self.brake_updates+1),report=lambda:dict(explicit_software_fixture=True),command=lambda:'original_brake_command',after_step=lambda:None)
  self.session=NS(machine=None)
  self.services=NS(native=self.native,session=self.session,contract=self.contract,assert_immutable=lambda:None,measure=self.measure,native_ready=lambda:self.ready,clock_report=lambda:dict(explicit_software_fixture=True),promote_confirmed_landing=lambda brake:False,begin_brake=self.begin)
  self.session.machine=Base(self.native,self.services,self.rows.append)
  self.old=self.session.machine;self.machine=self.cls.attach_pristine(self.session);self.native.phase='run'
 def measure(self):
  m=self.contract.evaluate(box_position=self.pose,rotation_world_from_box=((1.,0.,0.),(0.,1.,0.),(0.,0.,1.)),native_goal_xy=self.contract.drive_goal_xy_m)
  m.update(time_s=1.,actual_box_position_m=self.pose.copy(),actual_box_linear_velocity_m_s=self.velocity.copy(),task_geometry_pass=bool(m['public_XY_error_m']<.02 and abs(m['actual_signed_dock_gap_m'])<=.01))
  return m
 def begin(self,*,confirmed):
  self.begins+=1;return self.brake,dict(explicit_software_fixture=True,confirmed=confirmed)
 def test_default_off_and_bool(self):
  self.assertIsNone(helper.machine_class())
  with self.assertRaises(ValueError):helper.machine_class(enabled=1)
 def test_original_module_and_safety_methods_not_patched(self):
  self.assertIs(self.cls.original_base,Base)
  for name in ('_begin','_confirmation','_verify_complete','next_command','after_step','complete','results'):
   self.assertIs(getattr(self.cls,name),getattr(Base,name))
 def test_constructor_keeps_same_native_services_journal(self):
  self.assertIs(self.machine.native,self.old.native);self.assertIs(self.machine.services,self.old.services);self.assertIs(self.machine.journal,self.old.journal)
 def test_margin_enters_original_brake_without_relabelling_geometry(self):
  m=self.measure();self.assertFalse(m['placement_geometry_verified']);self.machine.update()
  self.assertEqual(self.begins,1);self.assertEqual(self.steps,0);self.assertEqual(self.brake_updates,1)
  event=next(r for r in self.rows if r['event']=='DEV_pre_arrival_original_brake_entry')
  self.assertFalse(event['placement_geometry_verified']);self.assertFalse(event['task_success_declared']);self.assertFalse(event['native_confirmation']);self.assertFalse(self.machine.complete)
 def test_only_one_entry_no_brake_reset(self):
  self.machine.update();self.machine.update();self.assertEqual(self.begins,1)
 def test_far_state_original_native_updates(self):
  self.pose[0]=2.5;self.machine.update();self.assertEqual(self.begins,0);self.assertEqual(self.steps,1)
 def test_stationary_state_no_new_entry(self):
  self.velocity[0]=0.;self.machine.update();self.assertEqual(self.begins,0)
 def test_reverse_state_no_new_entry(self):
  self.velocity[0]=-.1;self.machine.update();self.assertEqual(self.begins,0)
 def test_outside_y_no_new_entry(self):
  self.pose[1]=.03;self.machine.update();self.assertEqual(self.begins,0)
 def test_outside_height_no_new_entry(self):
  self.pose[2]=.13;self.machine.update();self.assertEqual(self.begins,0)
 def test_after_plane_not_new_entry(self):
  self.pose[0]=2.63;self.machine.update();self.assertEqual(self.begins,0)
 def test_original_arrival_branch_unchanged(self):
  self.pose[0]=2.6;self.machine.update();self.assertEqual(self.begins,1)
  self.assertFalse(any(r['event']=='DEV_pre_arrival_original_brake_entry'for r in self.rows))
 def test_early_brake_cannot_complete_without_native_clock(self):
  self.machine.update();self.brake.complete=True
  with self.assertRaisesRegex(RuntimeError,'original native PUSH success'):self.machine.complete
 def test_native_clock_and_stow_cannot_replace_geometry(self):
  self.machine.update();self.ready=True;self.brake.complete=True
  with self.assertRaisesRegex(RuntimeError,'placement lost after stow'):self.machine.complete
 def test_same_original_three_proofs_in_explicit_software_fixture(self):
  self.machine.update();self.ready=True;self.brake.complete=True;self.pose[0]=2.6;self.velocity[0]=0
  self.assertTrue(self.machine.complete);self.assertEqual(len(self.machine.results),1)
  self.assertTrue(self.machine.results[0]['task_success_not_inferred'])
 def test_original_begin_failure_not_suppressed(self):
  self.services.begin_brake=lambda **_:(_ for _ in ()).throw(RuntimeError('original_FIFO_fixture'))
  with self.assertRaisesRegex(RuntimeError,'original_FIFO_fixture'):self.machine.update()
  self.assertIsNone(self.machine.brake)
 def test_no_hot_attach_after_original_phase_run(self):
  self.session.machine=self.old
  with self.assertRaises(ValueError):self.cls.attach_pristine(self.session)
 def test_cannot_attach_twice(self):
  with self.assertRaises(ValueError):self.cls.attach_pristine(self.session)
 def test_nonfinite_state_refused(self):
  self.pose[0]=float('nan')
  with self.assertRaises(ValueError):helper.entry_candidate(self.measure(),self.contract)
 def test_exact_original_source_pin(self):
  with patch.object(helper,'HANDOFF_SHA','0'*64):
   with self.assertRaises(ValueError):helper.machine_class(source_root=SOURCE,enabled=True)

 def test_selected_factory_call_connects_pristine_push_only(self):
  import ast
  path=OWN/'task_factory.py';text=path.read_text();tree=ast.parse(text)
  factory=next(n for n in ast.walk(tree)if isinstance(n,ast.ClassDef)and n.name=='V4TaskFactory')
  node=next(n for n in factory.body if isinstance(n,ast.FunctionDef)and n.name=='__call__')
  def construct(host,inner):return self.session
  ns=dict(task=NS(RegisteredTaskSessionFactory=NS(__call__=construct)),arrival_machine=self.cls,
          require=lambda ok,msg:None if ok else (_ for _ in ()).throw(ValueError(msg)))
  exec(compile(ast.Module(body=[node],type_ignores=[]),str(path),'exec'),ns)
  for skill in ('PUSH','NAV'):
   self.native.phase='prepare';self.session.machine=self.old
   outer=NS(sha256='fixture',skill=skill,target_ref='fixture')
   host=NS(_outer_batch=NS(options=(outer,)),api=NS(world_snapshot=lambda _: 'same'),r=object(),
           _outer_world='same',_constructor_options={'fixture':NS(sha256='fixture-inner')},
           _prepared_public={'fixture':(None,None,self.contract)},journal=self.rows.append)
   result=ns['__call__'](host,outer)
   self.assertIs(result,self.session)
   self.assertEqual(type(result.machine)is self.cls,skill=='PUSH')
   self.assertIsNone(host._constructing_inner);self.assertIsNone(host._constructing_outer)
 def test_ambient_helper_refused_by_factory(self):
  import task_factory
  with patch.object(helper,'__file__','/not-the-new-package/pre_arrival_brake.py'):
   with self.assertRaisesRegex(ValueError,'ambient pre-arrival helper'):
    task_factory.factory_class(source_root=SOURCE,enabled=True)

if __name__=='__main__':
 r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
 print(json.dumps(dict(role='EXPLICIT_SOFTWARE_EARLY_BRAKE_CANDIDATE_NOT_NATIVE_SUCCESS',checks=r.testsRun,failures=len(r.failures),errors=len(r.errors),forbidden_attempts=blocked,physics_Actor_model_API_calls=0)))
 sys.exit(0 if r.wasSuccessful()and not blocked else 1)
