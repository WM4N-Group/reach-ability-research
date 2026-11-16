"""Private fresh-driver adapter fixtures, NOT a native construction/replay."""
from pathlib import Path
from types import SimpleNamespace as NS
import ast,json,sys,tempfile,unittest
OWN=Path(__file__).resolve().parents[1];ROOT=OWN.parents[1];sys.path.insert(0,str(OWN))
import indexed_guard as mod
from indexed_guard import FrozenFiles,OwnerStamp,GuardViolation
from install_fresh_driver import install,data_resource_watch_callbacks
SOURCE=ROOT/'development/complex_dual_route_v1/scene_driver.py'
blocked=[]
def fence(event,args):
 if event=='import'and str(args[0]).split('.')[0]in('numpy','torch','mujoco','onnxruntime'):
  blocked.append(str(args[0]));raise RuntimeError('No real runtime in adapter fixtures')
 if event in('socket.connect','socket.bind','socket.getaddrinfo','subprocess.Popen'):
  blocked.append(event);raise RuntimeError('No network/child')
sys.addaudithook(fence)
class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);p=Path(self.tmp.name)/'owned.py';p.write_text('# fixture')
  callback=object();registry=NS(modules={'owned':NS(__file__=str(p),CB=callback)})
  text=SOURCE.read_text();c=next(n for n in ast.parse(text).body if isinstance(n,ast.ClassDef)and n.name=='ComplexSceneDriver');fn=next(n for n in c.body if isinstance(n,ast.FunctionDef)and n.name=='_native_guards');ns=dict(sys=registry,Path=Path,need=mod.need);exec(compile(ast.Module(body=[fn],type_ignores=[]),str(SOURCE),'exec'),ns)
  self.previous=NS(_pool=None,closed=False,failed=False,original=ns['_native_guards']);self.previous.close=lambda:setattr(self.previous,'closed',True)
  def old(host):return self.previous.original(host)
  old.engine=self.previous
  class FakeRuntime:
   def __init__(self):
    self.step_count=0;self.sim=NS(model=object(),data=NS(time=0.),queue=[],controller=object(),box_push_target=object())
   def step(self,command):self.step_count+=1;self.sim.data.time+=.005;return command
  class Executor:
   def __init__(self):self.session=None
   def start(self,option):self.session=option;return 'software-installed'
  class Driver:
   _native_guards=old
   source_receipt={}
   def __init__(self):
    self.r=FakeRuntime();s=self.r.sim;self._world=(s,s.model,s.data,s.queue,s.controller,s.box_push_target)
    self._stow_installed={str(p):callback};self._stow_allowed={p};self._stow_callback_name='CB';self.executor=None;self.owner_guard=lambda:None
   def _connect_execution(self):self.executor=Executor()
   def judge_intent(self,intent):self._native_guards();return intent
  self.driver=Driver();self.files=FrozenFiles.measure([p,SOURCE],roots=[p.parent,ROOT]);self.checked=mod.time.monotonic()
 def install(self):
  def refresh(host):self.checked=mod.time.monotonic()
  def fast(host):return OwnerStamp('FAKE_OWNER',self.checked,self.checked+2,True)
  def tokens(host):return dict(session=None if host.executor is None else host.executor.session,target=None,goal='FAKE_GOAL',config_epoch='FAKE_CONFIG')
  result=install(self.driver,enabled=True,files=self.files,owner_fast=fast,owner_refresh=refresh,tokens=tokens)
  self.engine=type(self.driver)._native_guards.engine;self.addCleanup(self.engine.close);return result
 def test_default_off_no_driver_access(self):self.assertIsNone(install())
 def test_fresh_install_preserves_original_step_body_with_preissue_gate(self):
  result=self.install();self.assertTrue(self.previous.closed);self.assertFalse(result['old_per_tick_resolution_equivalence'])
  self.assertEqual(self.driver.r.step('SOFTWARE_COMMAND'),'SOFTWARE_COMMAND');self.assertEqual(self.driver.r.step_count,1)
 def test_actual_session_install_in_explicit_no_step_boundary(self):
  self.install();self.driver._connect_execution();option=object();self.assertEqual(self.driver.executor.start(option),'software-installed')
  self.driver._native_guards();self.driver.r.step('SOFTWARE_COMMAND');self.assertIs(self.driver.executor.session,option)
 def test_judgment_can_read_metadata_while_paused(self):
  self.install();self.assertEqual(self.driver.judge_intent('fixture'),'fixture');self.assertEqual(self.driver.r.step_count,0)
 def test_wrapped_runtime_cannot_step_during_constructor_boundary(self):
  self.install()
  with self.assertRaises(GuardViolation):
   with self.engine.boundary(self.driver,'fixture-bad-constructor'):self.driver.r.step('DO_NOT_ISSUE')
  self.assertEqual(self.driver.r.step_count,0)
 def test_runtime_step_wrapper_replacement_detected(self):
  self.install();self.driver.r.step=lambda command:None
  with self.assertRaises(GuardViolation):self.driver._native_guards()
 def test_no_hot_install(self):
  self.driver.r.step_count=1
  with self.assertRaises(GuardViolation):self.install()
 def test_duplicate_install_refused_no_silent_fallback(self):
  self.install()
  with self.assertRaises(GuardViolation):self.install()

 def test_original_brake_constructor_is_explicit_paused_boundary(self):
  self.install();self.driver._connect_execution();code=compile('value=3','<software-original-brake>','exec');scope={}
  def original_brake(**kwargs):exec(code,scope);return 'SOFTWARE_BRAKE'
  session=NS(machine=NS(services=NS(begin_brake=original_brake)))
  self.driver.executor.start(session)
  self.assertEqual(session.machine.services.begin_brake(confirmed=False),'SOFTWARE_BRAKE')
  self.assertEqual(scope['value'],3);self.assertEqual(self.driver.r.step_count,0)
  self.driver._native_guards()
 def test_brake_constructor_wrapper_cannot_issue_physics(self):
  self.install();self.driver._connect_execution()
  def unsafe(**kwargs):return self.driver.r.step('DO_NOT_ISSUE')
  session=NS(machine=NS(services=NS(begin_brake=unsafe)));self.driver.executor.start(session)
  with self.assertRaises(GuardViolation):session.machine.services.begin_brake(confirmed=False)
  self.assertEqual(self.driver.r.step_count,0)

 def test_Data_watch_bridge_keeps_real_timestamp_and_no_extra_probe(self):
  watch=NS(max_stale=2.,token=object(),last_ok=123.,last_observation_stamp=(123.,123.1),checks=0)
  def check(token):
   self.assertIs(token,watch.token);watch.checks+=1
  watch.check=check;fast,ack=data_resource_watch_callbacks(watch,epoch='scope-authority-epoch')
  stamp=fast(self.driver);ack(self.driver)
  self.assertEqual((stamp.checked_at,stamp.valid_until),(123.,125.));self.assertEqual(watch.checks,2)
 def test_Data_watch_bridge_revocation_propagates_not_self_signed_true(self):
  def revoked(token):raise RuntimeError('real supervisor revoked')
  watch=NS(max_stale=2.,token=object(),last_ok=123.,last_observation_stamp=(123.,123.1),check=revoked)
  fast,ack=data_resource_watch_callbacks(watch,epoch='scope-authority-epoch')
  with self.assertRaisesRegex(RuntimeError,'supervisor revoked'):fast(self.driver)
  with self.assertRaisesRegex(RuntimeError,'supervisor revoked'):ack(self.driver)

 def test_Data_watch_timestamp_sampled_once_under_background_refresh(self):
  class ChangingWatch:
   max_stale=2.
   token=object()
   reads=0
   def check(self,token):pass
   @property
   def last_observation_stamp(self):
    self.reads+=1;return(123.+self.reads,123.+self.reads+.1)
  watch=ChangingWatch();fast,_=data_resource_watch_callbacks(watch,epoch='scope-epoch')
  stamp=fast(self.driver)
  self.assertEqual(watch.reads,1);self.assertEqual(stamp.valid_until-stamp.checked_at,2.)

 def test_Data_watch_explicit_false_or_bad_return_refused(self):
  for result in (False,object()):
   watch=NS(max_stale=2.,token=object(),last_ok=123.,check=lambda token,value=result:value)
   fast,ack=data_resource_watch_callbacks(watch,epoch='scope-epoch')
   with self.assertRaises(GuardViolation):fast(self.driver)
   with self.assertRaises(GuardViolation):ack(self.driver)

 def test_legacy_completion_only_stamp_cannot_prove_oldest_age(self):
  watch=NS(max_stale=2.,token=object(),last_ok=4.,check=lambda token:None)
  fast,ack=data_resource_watch_callbacks(watch,epoch='scope-epoch')
  with self.assertRaises(GuardViolation):fast(self.driver)
  with self.assertRaises(GuardViolation):ack(self.driver)

 def test_overage_probe_completion_rejected_without_hot_checks_during_probe(self):
  watch=NS(max_stale=2.,token=object(),last_ok=4.,last_observation_stamp=(1.,4.),check=lambda token:None)
  fast,ack=data_resource_watch_callbacks(watch,epoch='scope-epoch')
  with self.assertRaisesRegex(GuardViolation,'Over-age'):fast(self.driver)
  with self.assertRaisesRegex(GuardViolation,'Over-age'):ack(self.driver)
 def test_deadline_uses_oldest_not_completion(self):
  watch=NS(max_stale=2.,token=object(),last_ok=4.,last_observation_stamp=(3.,4.),check=lambda token:None)
  fast,_=data_resource_watch_callbacks(watch,epoch='scope-epoch')
  stamp=fast(self.driver);self.assertEqual((stamp.checked_at,stamp.valid_until),(3.,5.))

if __name__=='__main__':
 r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
 print(json.dumps(dict(role='FRESH_ADAPTER_EXPLICIT_SOFTWARE_NOT_NATIVE',checks=r.testsRun,failures=len(r.failures),errors=len(r.errors),blocked=blocked,native_Runtime_Actor_physics_GPU_API_calls=0)))
 sys.exit(0 if r.wasSuccessful()and not blocked else 1)
