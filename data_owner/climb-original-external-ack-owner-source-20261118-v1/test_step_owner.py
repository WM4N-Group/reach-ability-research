"""Twelve NEW private-CPU protocol cases, FAKE Actor/world/clock, no native.

python -I -B this_file SDK_ROOT PINNED_INTERVAL_SOURCE
"""
from pathlib import Path
from types import SimpleNamespace as NS
from collections import deque
import copy,importlib.util,json,resource,sys,tempfile,time,unittest
START=time.perf_counter();HERE=Path(__file__).resolve().parent;SDK,INTERVAL=map(Path,sys.argv[1:3]);sys.argv[1:]=[]
spec=importlib.util.spec_from_file_location('_climb_ACK_protocol_source',HERE/'step_owner.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
import numpy as np

class Tensor:
 def __init__(self,array):self.array=array
 def unsqueeze(self,n):return self
 def to(self,device):return self
 def cpu(self):return self
 def numpy(self):return np.asarray(self.array)
class Mode:
 def __enter__(self):pass
 def __exit__(self,*args):pass
class Command:
 def __init__(self,number=0):
  self.position=np.full(18,float(number));self.velocity=np.zeros(18);self.kp=np.ones(18);self.kd=np.ones(18);self.feedforward=np.zeros(18)
 def array(self):return np.stack([self.position,self.velocity,self.kp,self.kd,self.feedforward])


def fixture(max_controls=1,terminal=False,wrong_counter=False):
 cfg=copy.deepcopy(json.loads((SDK/'climb/policy/contract.json').read_bytes())['configuration']['task'])
 c=dict(actor=0,set_action=0,policy=0,after_step=0,status=0,stop_status=0,observation=0,guard=0)
 class Sim:
  def __init__(self):
   self.cfg=cfg;self.model=NS(opt=NS(timestep=.005));self.height=.2
   self.data=NS(time=0.,qpos=np.zeros(25),qvel=np.zeros(24))
   self.queue=deque(maxlen=5);self.steps=0;self.elapsed=0.;self.history=None;self.ready=False
  def observation(self):c['observation']+=1;self.history=np.array([c['observation']]);return np.zeros(923,dtype=np.float32)
  def set_action(self,action):c['set_action']+=1
  def policy_command(self):c['policy']+=1;return Command(c['policy'])
  def physics_step(self,*args):raise AssertionError('NO hidden native/source physics in protocol tests')
  def status(self):
   c['status']+=1;self.steps+=1;self.elapsed+=.02;return 'running',''
 class Stop:
  def command(self,command):return command
  def after_step(self):
   c['after_step']+=1
   if flags['stop_error']is not None:raise flags['stop_error']
  def status(self,state,reason):c['stop_status']+=1;return ('success','SOFTWARE_FAKE_TERMINAL')if terminal else(state,reason)
 sim=Sim();stop=Stop();parent=NS(tick=0,last=None);flags=dict(guard_ok=True,stop_error=None)
 def actor(t):c['actor']+=1;return Tensor(np.zeros((1,18)))
 def check():c['guard']+=1;return flags['guard_ok']
 args=NS(device='SOFTWARE_FIXTURE_NOT_CUDA')
 kw=dict(counter_reader=(lambda:sim.steps)if wrong_counter else(lambda:parent.tick),issued_reader=lambda:parent.last,
  parent_check=check,interval_source_path=INTERVAL,play_path=SDK/'climb/play.py',bridge_path=SDK/'climb/bridge.py',
  contract_path=SDK/'climb/policy/contract.json',torch_backend=NS(inference_mode=Mode,from_numpy=Tensor),max_controls=max_controls,enabled=True)
 return sim,actor,args,cfg,stop,parent,c,flags,kw

def owner_fixture(**kwargs):
 x=fixture(**kwargs);return x,m.prepare(*x[:5],**x[-1])

def software_issue(x,o,command):
 sim,actor,args,cfg,stop,parent,c,flags,kw=x
 # Explicit fake external issue; no original bridge, torque integration or MjData.
 a=command.array().copy()
 if not sim.queue:sim.queue.extend([a.copy()for _ in range(sim.queue.maxlen)])
 else:sim.queue.append(a)
 parent.tick+=1;sim.data.time+=.005;parent.last=command
 o.after_actual_issue()

class Checks(unittest.TestCase):
 def test_01_disabled_and_initial_observation_once_before_first_actor(self):
  self.assertIsNone(m.prepare(enabled=False))
  x,o=owner_fixture();self.assertEqual((x[6]['observation'],x[6]['actor'],x[0].steps),(1,0,0))
  cmd=o.next_command();self.assertIsNotNone(cmd);self.assertEqual(x[6]['actor'],1)
  self.assertEqual((x[5].tick,x[0].steps,x[0].data.time),(0,0,0.))
 def test_02_four_real_reader_ACKs_drain_after_step_status_IMMEDIATELY_without_next_actor(self):
  x,o=owner_fixture()
  for i in range(4):
   cmd=o.next_command();self.assertEqual(x[6]['status'],0);software_issue(x,o,cmd)
   self.assertEqual(x[6]['after_step'],i+1)
  self.assertEqual((o.issued,o.controls,x[0].steps,x[6]['status'],x[6]['stop_status'],x[6]['observation']),(4,1,1,1,1,2))
  self.assertEqual((x[6]['actor'],x[6]['policy'],o.commands_produced),(1,4,4))
  self.assertTrue(o.censored);self.assertIsNone(o.next_command());self.assertEqual(x[6]['actor'],1)
 def test_03_no_issue_and_duplicate_ACK_cannot_invent_physics(self):
  x,o=owner_fixture();o.next_command()
  with self.assertRaises(ValueError):o.after_actual_issue()
  self.assertTrue(o.failed);self.assertEqual(o.issued,0)
  x,o=owner_fixture();cmd=o.next_command();software_issue(x,o,cmd)
  with self.assertRaises(ValueError):o.after_actual_issue()
  self.assertTrue(o.failed);self.assertEqual(o.issued,1)
 def test_04_original_steps_is_CONTROL_counter_not_physical_reader(self):
  x,o=owner_fixture(wrong_counter=True);cmd=o.next_command()
  x[5].tick=1;x[0].data.time=.005;x[5].last=cmd
  with self.assertRaises(ValueError):o.after_actual_issue()
  self.assertEqual(o.issued,0);self.assertEqual(o.observed_after_error['source_control_steps'],0)
  self.assertEqual(o.observed_after_error['time_s'],.005)
 def test_05_actual_command_drift_after_seal_rejected_without_reset(self):
  x,o=owner_fixture();cmd=o.next_command();cmd.feedforward[0]=1.
  with self.assertRaises(ValueError):software_issue(x,o,cmd)
  self.assertTrue(o.failed);self.assertEqual(o.issued,0);self.assertEqual(x[0].data.time,.005)
  self.assertEqual(x[5].tick,1);self.assertEqual(len(x[0].queue),5)
 def test_06_guard_and_world_cfg_or_interface_change_fail_before_next_actor(self):
  for mode in ('guard','world','cfg','interface'):
   x,o=owner_fixture()
   if mode=='guard':x[7]['guard_ok']=False
   if mode=='world':x[0].queue=deque(maxlen=5)
   if mode=='cfg':x[3]['support_force']+=1.
   if mode=='interface':o.actor=lambda t:Tensor(np.zeros((1,18)))
   with self.assertRaises(ValueError):o.next_command()
   self.assertEqual(x[6]['actor'],0);self.assertTrue(o.failed)
 def test_07_extra_stateful_status_poll_is_rejected_not_silently_resynced(self):
  x,o=owner_fixture();software_issue(x,o,o.next_command());x[0].status()
  with self.assertRaises(ValueError):o.next_command()
  self.assertTrue(o.failed);self.assertEqual((x[5].tick,x[0].steps),(1,1))
 def test_08_native_partial_error_preserves_identity_clock_and_unknown_ACK_not_zero_cost(self):
  x,o=owner_fixture();o.next_command();marker=RuntimeError('SOFTWARE_PARTIAL_NATIVE_ERROR')
  x[0].data.time=.005 # Fake native failed after time advance, before parent counter/issued receipt.
  with self.assertRaises(RuntimeError)as got:o.after_actual_issue(native_error=marker)
  self.assertIs(got.exception,marker);self.assertTrue(o.failed);self.assertEqual(o.issued,0)
  self.assertEqual(o.observed_after_error['time_s'],.005)
  self.assertTrue(o.snapshot()['partial_finally_actual_parent_cost_must_not_be_replaced_by_verified_ACK_count'])
 def test_09_stop_after_step_error_keeps_verified_issue_and_original_exception(self):
  x,o=owner_fixture();marker=RuntimeError('SOFTWARE_STOP_ERROR');x[7]['stop_error']=marker
  with self.assertRaises(RuntimeError)as got:software_issue(x,o,o.next_command())
  self.assertIs(got.exception,marker);self.assertEqual(o.issued,1);self.assertEqual(o.controls,0);self.assertTrue(o.failed)
  with self.assertRaises(ValueError):o.next_command()
 def test_10_two_intervals_are_two_actors_eight_ACKs_and_only_two_status_calls(self):
  x,o=owner_fixture(max_controls=2)
  for _ in range(8):software_issue(x,o,o.next_command())
  self.assertEqual((x[6]['actor'],o.issued,o.controls,x[0].steps,x[6]['status'],x[6]['after_step']),(2,8,2,2,2,8))
  self.assertAlmostEqual(x[0].data.time,.04);self.assertAlmostEqual(x[0].elapsed,.04)
  self.assertIsNone(o.next_command());self.assertEqual(x[6]['actor'],2)
 def test_11_nonfresh_or_source_drift_rejected_before_initial_observation_or_actor(self):
  for mode in ('clock','history','queue','source'):
   x=fixture()
   if mode=='clock':x[0].data.time=.005
   if mode=='history':x[0].history=np.zeros(1)
   if mode=='queue':x[0].queue.append(np.zeros((5,18)))
   if mode=='source':
    with tempfile.TemporaryDirectory(prefix='data-owner-source-CPU-')as d:
     p=Path(d)/'source_interval.py';p.write_bytes(INTERVAL.read_bytes()+b'\n');x[-1]['interval_source_path']=p
     with self.assertRaises(ValueError):m.prepare(*x[:5],**x[-1])
    self.assertEqual(x[6]['observation'],0);continue
   with self.assertRaises(ValueError):m.prepare(*x[:5],**x[-1])
   self.assertEqual((x[6]['observation'],x[6]['actor']),(0,0))
 def test_12_source_terminal_is_not_registered_success_or_authentication(self):
  x,o=owner_fixture(max_controls=3,terminal=True)
  for _ in range(4):software_issue(x,o,o.next_command())
  s=o.snapshot();self.assertEqual(s['source_state'],'success');self.assertTrue(s['source_terminal']);self.assertFalse(s['finite_censored_not_success'])
  self.assertFalse(s['execution_permission']);self.assertFalse(s['physical_or_skill_qualification'])
  self.assertFalse(s['constructor_RNG_Model_Actor_Stop_authentication']);self.assertFalse(s['registered_12N_safety_finally_full_Stop_receipt'])
  self.assertIsNone(o.next_command());self.assertEqual(x[6]['actor'],1)
  self.assertFalse(any(k=='mujoco'or k.startswith(('mujoco.','torch'))for k in sys.modules))

if __name__=='__main__':
 r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
 print(json.dumps(dict(stage='CLIMB_EXTERNAL_STEP_ACK_OWNER_SOURCE_ONLY_TWELVE_NEW_CPU_CASES',tests=r.testsRun,
  passed=r.wasSuccessful(),failures=len(r.failures),errors=len(r.errors),wall_s=time.perf_counter()-START,
  maxrss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
  original_control_steps_elapsed_are_NOT_physical_counter=True,
  fake_Actor_world_clock_ACK_not_a_real_parent_or_physics=True,actual_native_prepare_zero_main=False),indent=2))
 raise SystemExit(0 if r.wasSuccessful()else 1)
