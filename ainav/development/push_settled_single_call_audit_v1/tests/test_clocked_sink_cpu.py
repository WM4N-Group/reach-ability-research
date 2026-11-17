"""NEW clock/predicate/sink integration, real CPU Torch, synthetic env only.
The driver supplies SOURCE_BYTES/BUILDER_MODULE/SINK_MODULE/CLOCK_MODULE/TMPROOT.
"""
import ast,copy,json,types,unittest
from pathlib import Path
import torch

torch.set_num_threads(1)
patched=BUILDER_MODULE.instrument_push_settled_source(SOURCE_BYTES,enabled=True)
sdk=Path(TMPROOT)/'box_push.py';sdk.write_bytes(patched)
cls=next(n for n in ast.parse(patched).body if isinstance(n,ast.ClassDef)and n.name=='PushSettled')
class Base:
 def __init__(self,*args):pass
def cfg(*a,**k):return None
def hand(env,asset):env.calls.append('hand');return env.hand.clone()
def target(env):env.calls.append('target');return env.target
def tip(env):env.calls.append('tip');return env.tip.clone()
def forbidden(env):env.calls.append('forbidden');return env.forbidden.clone()
ns=dict(torch=torch,ManagerTermBase=Base,SceneEntityCfg=cfg,hand_contact=hand,push_target=target,box_tipped=tip,forbidden_box_contact=forbidden)
exec(compile(ast.Module(body=[cls],type_ignores=[]),str(sdk),'exec'),ns)
Native=ns['PushSettled'];Clock=CLOCK_MODULE.ClockedNativeSettled
class Tests(unittest.TestCase):
 def setup(self,**overrides):
  e=types.SimpleNamespace(num_envs=1,device='cpu',step_dt=.02,data=types.SimpleNamespace(time=0.),calls=[])
  e.hand=torch.ones(1,dtype=torch.bool);e.tip=e.forbidden=torch.zeros(1,dtype=torch.bool);e.target=torch.zeros((1,3))
  e.scene={'box':types.SimpleNamespace(data=types.SimpleNamespace(root_pos_w=torch.zeros((1,3)),root_lin_vel_w=torch.zeros((1,3))))}
  native=Native(None,e);e.settled=Clock(native,e);runtime=types.SimpleNamespace(sim=types.SimpleNamespace(data=e.data),step_count=0)
  phase=types.SimpleNamespace(value='native');rows=[]
  def writer(encoded):rows.append(json.loads(encoded));return 'SYNTHETIC_DURABLE:'+str(len(rows))
  args=dict(enabled=True,env=e,runtime=runtime,write_record=writer,phase_reader=lambda:phase.value,phase_source_ref='SOFTWARE_PHASE_FIELD',scope_id='SOFTWARE_NEW_D3_NOT_A_RUN',world_role='task',max_records=100,max_payload_bytes=1024*1024);args.update(overrides)
  sink=SINK_MODULE.bind_clocked_settled_sink(**args)
  return e,runtime,phase,rows,sink
 def at(self,e,runtime,now):e.data.time=now;runtime.step_count=round(now/.005);return e.settled(e)
 def test_01_default_off_and_single_call_before_original_clock_accounting(self):
  self.assertIsNone(SINK_MODULE.bind_clocked_settled_sink())
  e,r,p,rows,s=self.setup();self.at(e,r,.02)
  for _ in range(4):e.settled(e)
  self.assertEqual(e.calls,['hand','target','tip','forbidden']);self.assertEqual(len(rows),1)
  c=rows[0]['context'];self.assertEqual(c['physical_tick'],4);self.assertEqual(c['original_clock_advances_before_current'],0)
  self.assertEqual(e.settled.advances,1);self.assertAlmostEqual(e.settled.report()['native_duration_s'],.02)
  self.assertFalse(s.report()['failed'])
 def test_02_first_true_then_false_flags_current_phase_without_report_repoll(self):
  e,r,p,rows,s=self.setup()
  for i in range(1,26):self.at(e,r,i*.02)
  self.assertIsNotNone(s.report()['first_confirmed']);p.value='brake';e.scene['box'].data.root_lin_vel_w[0,2]=.09
  self.at(e,r,.52);summary=s.report();self.assertEqual(summary['first_loss']['phase'],'brake')
  self.assertEqual(summary['first_loss']['false_original_flags'],['speed_3d_lt_original_008'])
  self.assertEqual(summary['first_loss']['time_s'],.52);self.assertEqual(e.settled.advances,26)
  self.assertEqual(len(rows),26);self.assertEqual(e.settled.report()['native_duration_s'],0.)
 def test_03_capacity_failure_is_closed_no_skipping_or_resume(self):
  e,r,p,rows,s=self.setup(max_records=1);self.at(e,r,.02)
  with self.assertRaises(ValueError):self.at(e,r,.04)
  self.assertTrue(s.failed);self.assertTrue(e.settled.failed);self.assertEqual(len(rows),1)
  self.assertGreater(float(e.settled.native.duration[0]),.02) # State already updated, never rollback.
  with self.assertRaises(RuntimeError):e.settled(e)
 def test_04_writer_error_marks_unknown_tail_and_preserves_exception(self):
  error=OSError('SYNTHETIC_IO_ERROR_NOT_A_NATIVE_FAILURE')
  def writer(encoded):raise error
  e,r,p,rows,s=self.setup(write_record=writer)
  with self.assertRaises(OSError)as result:self.at(e,r,.02)
  self.assertIs(result.exception,error);self.assertTrue(s.report()['writer_tail_unknown']);self.assertEqual(s.records,0)
  self.assertEqual(s.writer_attempts,1);self.assertTrue(e.settled.failed)
 def test_05_context_mismatch_fails_without_a_second_predicate(self):
  e,r,p,rows,s=self.setup();e.data.time=.02;r.step_count=5
  with self.assertRaises(ValueError):e.settled(e)
  self.assertEqual(e.calls,['hand','target','tip','forbidden']);self.assertEqual(rows,[]);self.assertTrue(e.settled.failed)
 def test_06_bind_selected_view_once_not_parent_callable_copy_or_history_reset(self):
  e,r,p,rows,s=self.setup();parent=types.SimpleNamespace(data=e.data)
  self.assertFalse(hasattr(parent,'_ainav_push_settled_audit'));self.assertIs(e._ainav_push_settled_audit,s)
  with self.assertRaises(ValueError):SINK_MODULE.bind_clocked_settled_sink(enabled=True,env=e,runtime=r,write_record=lambda b:'x',phase_reader=lambda:'native',phase_source_ref='SOFTWARE',scope_id='SOFTWARE',world_role='task',max_records=10,max_payload_bytes=10000)
  self.assertEqual(e.settled.advances,0);self.assertEqual(e.settled.last_duration,0.)
 def test_07_payload_limit_and_ack_are_real_gates_not_best_effort_logger(self):
  for kwargs in (dict(max_payload_bytes=1),dict(write_record=lambda b:None)):
   e,r,p,rows,s=self.setup(**kwargs)
   with self.assertRaises(ValueError):self.at(e,r,.02)
   self.assertTrue(s.failed);self.assertTrue(e.settled.failed);self.assertEqual(s.records,0)

result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
assert result.wasSuccessful(),'New D3 sink integration failed, not native evidence'
print('NEW_CLOCK_PREDICATE_SINK_CPU_CASES='+str(result.testsRun))
