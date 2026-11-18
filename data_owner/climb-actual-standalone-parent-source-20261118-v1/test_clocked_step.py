"""Eight NEW SOFTWARE counter fixtures; no real SDK import/model/Actor/physics."""
from pathlib import Path
from types import SimpleNamespace as NS
from collections import deque
import importlib.util,json,resource,sys,time,unittest
START=time.perf_counter();HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('_clocked_original_step_fixture',HERE/'standalone_parent.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
import numpy as np
class Command:
 def __init__(self,*rows):self.rows=list(rows)if rows else[np.zeros(18)for _ in range(5)]
 def array(self):return np.stack(self.rows)
def fixture(mode='normal'):
 sim=NS(data=NS(time=0.),model=NS(opt=NS(timestep=.005)),queue=deque(maxlen=5),steps=0,elapsed=0.)
 calls=[];flags=dict(guard=True,context=True);marker=RuntimeError('SOFTWARE_NATIVE_CALLBACK_ERROR')
 def callback(command):
  calls.append(command)
  if mode=='before-error':raise marker
  if mode!='no-clock':sim.data.time+=.01 if mode=='double'else .005
  if mode=='after-error':raise marker
 counter=m.ClockedOriginalStep(sim,callback,Command,parent_check=lambda:flags['guard'],active_context=lambda:flags['context'])
 return sim,counter,calls,flags,marker
class Checks(unittest.TestCase):
 def test_01_one_real_reader_clock_advance_counter_not_control_steps(self):
  sim,c,calls,flags,error=fixture();cmd=Command();c.issue(cmd)
  self.assertEqual((c.tick,c.attempts,sim.steps,sim.elapsed,len(calls)),(1,1,0,0.,1));self.assertEqual(sim.data.time,.005)
 def test_02_original_partial_error_after_integration_preserves_clock_count_and_object(self):
  sim,c,calls,flags,error=fixture('after-error')
  with self.assertRaises(RuntimeError)as got:c.issue(Command())
  self.assertIs(got.exception,error);self.assertEqual((c.tick,c.attempts),(1,1));self.assertEqual(c.partial_clock,.005)
  self.assertIsNotNone(c.last);self.assertTrue(c.failed)
  with self.assertRaises(ValueError):c.issue(Command())
  self.assertEqual(len(calls),1)
 def test_03_error_before_step_does_not_invent_advance(self):
  sim,c,calls,flags,error=fixture('before-error')
  with self.assertRaises(RuntimeError)as got:c.issue(Command())
  self.assertIs(got.exception,error);self.assertEqual(c.tick,0);self.assertIsNone(c.last);self.assertEqual(c.partial_clock,0.)
 def test_04_no_clock_or_double_clock_is_not_one_ack(self):
  for mode in ('no-clock','double'):
   sim,c,calls,flags,error=fixture(mode)
   with self.assertRaises(ValueError):c.issue(Command())
   self.assertTrue(c.failed);self.assertEqual(c.tick,0);self.assertEqual(c.attempts,1)
 def test_05_actual_issued_copy_does_not_alias_mutable_request(self):
  sim,c,calls,flags,error=fixture();cmd=Command();c.issue(cmd);cmd.rows[0][:]=3.
  np.testing.assert_array_equal(c.last.array()[0],np.zeros(18))
 def test_06_guard_context_world_or_dt_refusal_before_native_callback(self):
  for mode in ('guard','context','world','dt'):
   sim,c,calls,flags,error=fixture()
   if mode=='guard':flags['guard']=False
   if mode=='context':flags['context']=False
   if mode=='world':sim.queue=deque(maxlen=5)
   if mode=='dt':sim.model.opt.timestep=.01
   with self.assertRaises(ValueError):c.issue(Command())
   self.assertEqual(len(calls),0);self.assertTrue(c.failed)
 def test_07_inactive_context_is_not_a_source_permission_or_lease_probe(self):
  with self.assertRaises(ValueError):m.checked(lambda:False)
  self.assertIsNone(m.checked(lambda:None))
  self.assertIsNone(m.prepare(enabled=False))
  with self.assertRaises(ValueError):m.require_native_context(dict(question='PUSH'),None)
  self.assertFalse(any(k=='mujoco'or k.startswith(('mujoco.','torch'))for k in sys.modules))
 def test_08_unreadable_partial_clock_never_replaces_original_native_error(self):
  sim,c,calls,flags,error=fixture()
  class MissingClock:
   @property
   def time(self):raise RuntimeError('SOFTWARE_SECONDARY_CLOCK_READ_ERROR')
  def callback(command):sim.data=MissingClock();raise error
  c.actual_physics=callback
  with self.assertRaises(RuntimeError)as got:c.issue(Command())
  self.assertIs(got.exception,error);self.assertTrue(c.failed);self.assertIsNone(c.partial_clock)
  self.assertEqual(c.tick,0)

if __name__=='__main__':
 result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
 print(json.dumps(dict(stage='CLIMB_CLOCKED_STEP_SOURCE_EIGHT_NEW_SOFTWARE_CASES_NOT_NATIVE',tests=result.testsRun,passed=result.wasSuccessful(),failures=len(result.failures),errors=len(result.errors),
  wall_s=time.perf_counter()-START,maxrss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
  fake_callbacks_clocks_not_actual_physics=True,no_SDK_model_Actor_GPU_lease_or_registered_qualification=True),indent=2))
 raise SystemExit(0 if result.wasSuccessful()else 1)
