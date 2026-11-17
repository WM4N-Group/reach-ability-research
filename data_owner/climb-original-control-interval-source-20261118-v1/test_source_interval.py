"""Four NEW private-CPU fixtures, fake Actor/NumPy state; no model/world/GPU."""
from pathlib import Path
from types import SimpleNamespace as NS
import importlib.util,json,resource,sys,tempfile,time,unittest
START=time.perf_counter();HERE=Path(__file__).resolve().parent;PLAY=Path(sys.argv[1]);sys.argv[1:]=[]
spec=importlib.util.spec_from_file_location('_climb_interval_source',HERE/'source_interval.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
import numpy as np
text,proof=m.derive(PLAY,enabled=True)
class Tensor:
 def __init__(self,array):self.array=array
 def unsqueeze(self,n):return self
 def to(self,device):return self
 def cpu(self):return self
 def numpy(self):return np.asarray(self.array)
class Mode:
 def __enter__(self):pass
 def __exit__(self,*args):pass

def fixture(with_stop=True):
 counts=dict(actor=0,set_action=0,policy=0,physics=0,after_step=0,status=0,stop_status=0,obs=0)
 class Sim:
  ready=False
  data=NS(time=0.,qpos=np.zeros(25),qvel=np.zeros(24))
  def set_action(self,a):counts['set_action']+=1
  def policy_command(self):counts['policy']+=1;return object()
  def physics_step(self,*args):raise AssertionError('Source may NOT step hidden physics')
  def status(self):counts['status']+=1;return 'running',''
  def observation(self):counts['obs']+=1;return np.full(923,counts['obs'])
 class Stop:
  def command(self,c):return c
  def after_step(self):counts['after_step']+=1
  def status(self,state,reason):counts['stop_status']+=1;return state,reason
 def actor(t):counts['actor']+=1;return Tensor(np.zeros((1,18)))
 namespace=dict(np=np,torch=NS(inference_mode=Mode,from_numpy=Tensor))
 exec(compile(text,'[original CLIMB interval source with explicit SOFTWARE backend]','exec'),namespace)
 sim=Sim();stop=Stop()if with_stop else None
 gen=namespace['original_control_interval_requests'](sim,actor,NS(device='SOFTWARE_FIXTURE'),dict(decimation=4),stop,np.zeros(923))
 return sim,gen,counts

def external_fixture_issue(sim,counts,command):
 # Explicit fake external step/count, never original physics or new MjData.
 if command is None:sim.policy_command()
 sim.data.time+=.005;counts['physics']+=1

class Checks(unittest.TestCase):
 def test_01_Actor_called_at_control0_even_not_ready_and_NO_hidden_physics(self):
  sim,g,c=fixture();self.assertFalse(sim.ready)
  cmd=next(g)
  self.assertEqual((c['actor'],c['set_action'],c['physics'],c['status'],sim.data.time),(1,1,0,0,0.))
  self.assertIsNotNone(cmd)
 def test_02_after_step_once_per_5ms_status_once_after_four_ACKs_then_drain(self):
  sim,g,c=fixture()
  for tick in range(4):
   cmd=next(g)
   self.assertEqual(c['after_step'],tick);self.assertEqual(c['status'],0)
   external_fixture_issue(sim,c,cmd)
  with self.assertRaises(StopIteration)as got:next(g)
  self.assertEqual((c['actor'],c['set_action'],c['policy'],c['physics'],c['after_step'],c['status'],c['stop_status'],c['obs']),(1,1,4,4,4,1,1,1))
  self.assertEqual(got.exception.value[:2],('running',''));self.assertAlmostEqual(sim.data.time,.02)
  with self.assertRaises(StopIteration):next(g)
  self.assertEqual(c['actor'],1) # Draining one interval never invokes next Actor.
 def test_03_ascent_None_preserves_original_physics_default_not_fabricated_zero(self):
  sim,g,c=fixture(False)
  for tick in range(4):
   cmd=next(g);self.assertIsNone(cmd);self.assertEqual(c['policy'],tick)
   external_fixture_issue(sim,c,cmd)
  with self.assertRaises(StopIteration):next(g)
  self.assertEqual((c['actor'],c['policy'],c['after_step'],c['status'],c['stop_status']),(1,4,0,1,0))
 def test_04_disabled_drift_rejected_and_no_native_modules(self):
  self.assertIsNone(m.derive(enabled=False))
  with tempfile.TemporaryDirectory(prefix='data-climb-source-CPU-')as d:
   p=Path(d)/'play.py';p.write_bytes(PLAY.read_bytes()+b'\n')
   with self.assertRaises(ValueError):m.derive(p,enabled=True)
  self.assertFalse(any(k=='mujoco'or k.startswith(('mujoco.','torch'))for k in sys.modules))

if __name__=='__main__':
 result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
 print(json.dumps(dict(stage='CLIMB_ONE_ORIGINAL_CONTROL_INTERVAL_SOURCE_ONLY_NEW_FOUR_CPU_CHECKS',tests=result.testsRun,
  passed=result.wasSuccessful(),failures=len(result.failures),errors=len(result.errors),wall_s=time.perf_counter()-START,
  maxrss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,source_proof=proof,
  actual_world_Actor_GPU_lease_or_registered_owner_or_native_prepare=False),indent=2))
 raise SystemExit(0 if result.wasSuccessful()else 1)
