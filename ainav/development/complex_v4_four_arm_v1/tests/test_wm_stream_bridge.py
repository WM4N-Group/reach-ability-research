"""Explicit recorder/typed-session/port software fixtures, NOT live/WM input.

No numpy/torch, sensor render, model restore, query build/forward or physics.
Original NativeOptionSession/Executor are __new__ metadata shells, never entered.
Use the REAL Reach port with an explicitly marked fake buffer and method route.
"""
from pathlib import Path
from types import SimpleNamespace as NS
from collections import deque
from unittest.mock import patch
import os,sys,struct,json,unittest
OWN=Path(__file__).resolve().parents[1];ROOT=OWN.parents[1]
SOURCE=ROOT/'consumer-deliveries/AINAV-CLIMB-PREPARATION-CANDIDATES-20261113-v1/common-source'
REACH=Path(os.environ.get('AINAV_V4_REACH_SOURCE_ROOT',str(ROOT/'manifests/V4_four_arm_source_20261115_v1/reach-wm-stream-readonly-reference')))
sys.path[:0]=[str(OWN),str(SOURCE)]
blocked=[]
def fence(event,args):
    if event=='import'and str(args[0]).split('.')[0]in('numpy','torch','mujoco','onnxruntime'):
        blocked.append(str(args[0]));raise RuntimeError('Explicit stream metadata fixture only')
    if event in('socket.connect','socket.bind','socket.getaddrinfo','subprocess.Popen'):
        blocked.append(event);raise RuntimeError('No transport/child/probe')
sys.addaudithook(fence)
import wm_stream_bridge as bridge
from factor_scope import FactorJournal
adapters,causal,raw,native=bridge._checked_sources(SOURCE,REACH)

class Array:
    def __init__(self,values,shape):self.values=tuple(values);self.shape=shape;self.dtype='float32'
    def tobytes(self):return struct.pack('<'+'f'*len(self.values),*self.values)
    def copy(self):return Array(self.values,self.shape)
    def __iter__(self):return iter(self.values)
    def __getitem__(self,key):
        if len(self.shape)==2:return Array(self.values[key*self.shape[1]:(key+1)*self.shape[1]],(self.shape[1],))
        return self.values[key]
class Time:
    shape=(1,1)
    def __init__(self,value):self.value=value
    def __getitem__(self,key):return self.value
class ExplicitFixtureBuffer:
    _reach_query_software_fixture=True
    def __init__(self,trace):
        self.frames=deque(maxlen=3);self.commands=deque(maxlen=64);self.owner=self.observed_skill=self.owner_started=None;self.trace=trace
    def visual(self,packet):
        self.trace.append(('port_visual',float(packet['timestamps_s'][0,0])))
        self.frames.append(dict(time_s=float(packet['timestamps_s'][0,0]),EXPLICIT_SOFTWARE_NOT_RGBD=True))
    def actual_motor(self,position,physical_tick,time_s,*,issued_skill,native_owner_id):
        self.trace.append(('port_motor',physical_tick,issued_skill,position.shape))
        self.commands.append((physical_tick,position.copy()));self.owner=(issued_skill,native_owner_id);self.observed_skill=issued_skill
    def build(self,*args,**kwargs):raise AssertionError('Never build a WM query or fabricate observations')
class ExplicitRawWriter:
    def __init__(self,trace):self.trace=trace;self.steps=0;self.visual=[];self.commands=[];self.fail=False
    def append_command(self,**kw):
        self.trace.append(('raw_motor',kw['physical_tick']))
        if self.fail:raise RuntimeError('EXPLICIT_SOFTWARE_writer_failed')
        self.commands.append(kw);self.steps+=1;return 'EXPLICIT_RAW_command_return'
    def append_visual(self,packet,**kw):
        self.trace.append(('raw_visual',kw['control_tick']));self.visual.append((packet,kw));return 'EXPLICIT_RAW_visual_return'
    def finish(self):self.trace.append(('raw_finish',));return 'EXPLICIT_RAW_finish_return'

class Tests(unittest.TestCase):
    def setUp(self):
        self.trace=[];self.rows=[];self.buffer=ExplicitFixtureBuffer(self.trace)
        self.port=causal.CausalWMQueryPort(self.buffer,role='EXPLICIT_SOFTWARE_FIXTURE_NOT_MODEL_TASK_INPUT',software_fixture=True)
        wm=raw.OriginalBehaviorWMAdapter.__new__(raw.OriginalBehaviorWMAdapter);wm.provider=self.port;wm.forward_batches=0
        self.ledger=FactorJournal('A',lambda row:self.rows.append(row)or'EXPLICIT_SOFTWARE_NOT_AUTH_OR_NATIVE')
        planner=adapters.build_v4_planner('A',journal=self.ledger,backend=NS(kind='deepseek_vision_api'),wm_evaluator=wm,software_fixture=True)
        self.command=Array(range(90),(5,18));self.raw=ExplicitRawWriter(self.trace)
        r=NS(step_count=0,sim=NS(data=NS(time=0.),queue=[]),last=NS(array=lambda:self.command))
        self.h=NS(arm='A',r=r,loop=None,executor=None,capture=NS(EXPLICIT_SUPPORTED_CAPTURE_METADATA=True),
            writer=self.raw,owner_guard=lambda:None,source_root=SOURCE,planner=planner,journal=self.ledger,_v4_factor_journal=self.ledger,factory=object())
    def attach(self,**kw):
        args=dict(enabled=True,driver=self.h,port=self.port,reach_source_root=REACH,software_fixture=True);args.update(kw)
        return bridge.attach_current_wm_stream(**args)
    def packet(self,time):return {k:Time(time)if k=='timestamps_s'else object()for k in bridge.PACKET_KEYS}
    def command_at(self,n,*,issued=None):
        self.h.r.step_count=n;self.h.r.sim.data.time=n*.005
        return self.h.writer.append_command(issued=self.command if issued is None else issued,
            delayed=object(),torque=object(),raw_torque=object(),q_before=object(),dq_before=object(),physical_tick=n,time_s=n*.005)
    def modelled(self,skill='NAV'):
        session=native.NativeOptionSession.__new__(native.NativeOptionSession)
        session.runtime=self.h.r;session.entered=True;session.exit=session.failure=None;session.machine=NS(tasks=[dict(skill=skill.lower())])
        ex=native.NativeOptionExecutor.__new__(native.NativeOptionExecutor)
        ex.runtime=self.h.r;ex.factory=self.h.factory;ex.fatal=ex.reported_end=False;ex.session=session;ex.sessions=[session];ex.option=NS(skill=skill)
        self.h.executor=ex;self.h.loop=object();return ex
    def test_default_off_no_driver_source_read_or_import(self):
        with patch.object(bridge,'_checked_sources',side_effect=AssertionError('No source read')):
            self.assertIsNone(bridge.attach_current_wm_stream())
    def test_one_fresh_A_B_only_matching_method_provider_and_ledger(self):
        self.attach()
        with self.assertRaises(ValueError):self.attach()
        for arm in 'CDE':
            self.h.arm=arm
            with self.assertRaises(ValueError):self.attach()
        self.assertEqual(len(self.rows),1)
    def test_B_same_stream_no_selector_call_and_mismatched_factor_arm_refuses(self):
        self.h.arm='B';self.h.planner.enabled=True
        with self.assertRaises(ValueError):self.attach()  # Still the actual A factor ledger; cannot relabel it.
        self.ledger=FactorJournal('B',lambda row:self.rows.append(row)or'EXPLICIT_SOFTWARE_B_factor')
        self.h.journal=self.h._v4_factor_journal=self.h.planner.journal=self.ledger
        wrapper=self.attach();self.modelled('NAV');self.command_at(1)
        self.assertEqual(wrapper.report()['actual_command_callbacks'],1)
        self.assertEqual(self.ledger.counts['new_successor_choice_events'],0)
        self.assertTrue(self.rows[-1]['v4_factor_scope']['new_successor_optimizer_enabled'])
    def test_midstream_fixture_relabel_other_port_or_different_journal_refuse(self):
        self.h.r.step_count=1
        with self.assertRaises(ValueError):self.attach()
        self.h.r.step_count=0
        with self.assertRaises(ValueError):self.attach(software_fixture=False)
        another=causal.CausalWMQueryPort(ExplicitFixtureBuffer([]),role='EXPLICIT_SOFTWARE_FIXTURE_NOT_MODEL_TASK_INPUT',software_fixture=True)
        with self.assertRaises(ValueError):self.attach(port=another)
        self.h.planner.journal=lambda row:'other'
        with self.assertRaises(ValueError):self.attach()
        self.assertIs(self.h.writer,self.raw)
    def test_raw_writer_first_exact_return_and_global_position_only_no_private_fields(self):
        wrapper=self.attach();ex=self.modelled('NAV');self.assertEqual(self.command_at(1),'EXPLICIT_RAW_command_return')
        self.assertEqual(self.trace[:2],[('raw_motor',1),('port_motor',1,'NAV',(18,))])
        self.assertEqual(self.buffer.commands[-1][1].values,tuple(range(18)))
        self.assertEqual(self.raw.commands[-1]['issued'].shape,(5,18));self.assertFalse(wrapper.report()['private_catalog_forwarded'])
    def test_capture_revokes_model_window_not_HOLD_NAV_or_RECOVER(self):
        wrapper=self.attach();self.buffer.frames.append({'EXPLICIT_old':True});self.command_at(1)
        self.assertIsNone(self.buffer.observed_skill);self.assertFalse(self.buffer.frames);self.assertFalse(self.buffer.commands)
        self.assertEqual(self.port.context_status()['status'],'CURRENT_ISSUED_OWNER_NOT_IN_ORIGINAL_GENERIC_SKILLS')
        self.assertEqual(wrapper.report()['unmodelled_owner_callbacks'],1)
    def test_only_new_native_owner_then_three_fresh_grid_frames_no_backfill(self):
        self.attach();self.h.writer.append_visual(self.packet(0.),control_tick=0,private_catalog={'DO_NOT_FORWARD':object()})
        for tick in range(1,21):self.command_at(tick)
        self.h.writer.append_visual(self.packet(.1),control_tick=5,private_catalog={'EXPLICIT_capture_PRIVATE':True})
        self.assertFalse(self.buffer.frames)
        self.modelled('NAV')
        for tick in range(21,81):
            self.command_at(tick)
            if tick%20==0:self.h.writer.append_visual(self.packet(tick*.005),control_tick=tick//4,private_catalog={'PRIVATE':True})
            if tick in (40,60):self.assertEqual(self.port.context_status()['status'],'WAIT_THREE_NEW_REAL_GRID_FRAMES')
        self.assertEqual([x['time_s']for x in self.buffer.frames],[.2,.3,.4])
        self.assertEqual(self.port.context_status()['status'],'NECESSARY_CONTEXT_PRESENT_ORIGINAL_BUILD_CHECKS_STILL_REQUIRED')
        self.assertEqual(self.port.completed_queries,0)
    def test_actual_preparation_NAV_not_high_level_PENDING_PUSH_and_Push_Climb_tasks(self):
        self.attach();self.h.pending_semantic_intent=NS(skill='PUSH')
        for tick,skill in enumerate(('NAV','PUSH','CLIMB'),1):
            self.modelled(skill);self.command_at(tick);self.assertEqual(self.buffer.observed_skill,skill)
        self.assertEqual([r[2]for r in self.trace if r[0]=='port_motor'],['NAV','PUSH','CLIMB'])
    def test_protected_exit_unknown_not_relabelled_selected_PUSH(self):
        self.attach();ex=self.modelled('PUSH');ex.session.exit=object();self.command_at(1)
        self.assertIsNone(self.buffer.observed_skill);self.assertEqual(self.port.unmodelled_issued_steps,1)
    def test_gap_fails_closed_without_replaying_or_backfilling_accepted_commands(self):
        wrapper=self.attach();self.modelled();self.command_at(1)
        with self.assertRaises(ValueError):self.command_at(3)
        self.assertTrue(wrapper.report()['failed']);self.assertEqual(wrapper.report()['actual_command_callbacks'],1)
        with self.assertRaises(ValueError):self.command_at(2)
        self.assertEqual(len(self.buffer.commands),1)
    def test_wrong_raw_channel_shape_is_not_transformed_into_native18(self):
        self.attach();self.modelled()
        with self.assertRaises(ValueError):self.command_at(1,issued=Array(range(54),(3,18)))
        self.assertEqual(len(self.raw.commands),1);self.assertFalse(self.buffer.commands)
    def test_inconsistent_typed_native_task_refuses_after_raw(self):
        self.attach();ex=self.modelled('NAV');ex.session.machine.tasks=[dict(skill='push')]
        with self.assertRaises(ValueError):self.command_at(1)
        self.assertEqual(len(self.raw.commands),1);self.assertFalse(self.buffer.commands)
    def test_offgrid_or_stale_visual_never_enters_WM_and_private_catalog_only_raw(self):
        self.attach();private={'EXPLICIT_PRIVATE_catalog_DO_NOT_FORWARD':object()};self.h.writer.append_visual(self.packet(0.),control_tick=0,private_catalog=private)
        self.assertIs(self.raw.visual[-1][1]['private_catalog'],private)
        self.assertEqual(self.trace[:2],[('raw_visual',0),('port_visual',0.)])
        with self.assertRaises(ValueError):self.h.writer.append_visual(self.packet(.02),control_tick=1,private_catalog=private)
        self.assertEqual(len(self.buffer.frames),1)
    def test_raw_writer_failure_no_callback_and_no_bridge_resume(self):
        wrapper=self.attach();self.modelled();self.raw.fail=True
        with self.assertRaises(RuntimeError):self.command_at(1)
        self.assertTrue(wrapper.report()['failed']);self.assertFalse(self.buffer.commands)
        self.raw.fail=False
        with self.assertRaises(ValueError):self.command_at(1)
        self.assertFalse(self.buffer.commands)
    def test_port_failure_preserves_raw_and_source_never_steps_or_restores_model(self):
        wrapper=self.attach();self.modelled()
        with patch.object(self.port,'on_issued',side_effect=ValueError('EXPLICIT_SOFTWARE_callback_failure')):
            with self.assertRaises(ValueError):self.command_at(1)
        self.assertEqual(len(self.raw.commands),1);self.assertTrue(wrapper.report()['failed'])
        self.assertEqual(self.h.r.step_count,1);self.assertFalse(blocked)
    def test_original_writer_finish_forwarded_and_guard_or_source_drift_refuse_attach(self):
        self.h.owner_guard=lambda:False
        with self.assertRaises(ValueError):self.attach()
        self.h.owner_guard=lambda:None
        with patch.dict(bridge.PORT_PINS,{'v4_causal_wm_query.py':'0'*64}):
            with self.assertRaises(ValueError):self.attach()
        self.assertIs(self.h.writer,self.raw);wrapper=self.attach()
        self.assertEqual(wrapper.finish(),'EXPLICIT_RAW_finish_return')
        self.assertEqual(self.h.planner.wm.forward_batches,0);self.assertEqual(self.port.completed_queries,0)

if __name__=='__main__':
    r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
    print(json.dumps(dict(role='EXPLICIT_CURRENT_RECORDER_TYPED_SESSION_AND_REAL_REACH_PORT_WITH_FIXTURE_BUFFER_NOT_MODEL_OR_NATIVE_INPUT',checks=r.testsRun,failures=len(r.failures),errors=len(r.errors),forbidden_attempts=blocked,real_sensor_accepted_command_query_build_WM_restore_forward_Actor_physics_API_calls=0)))
    sys.exit(0 if r.wasSuccessful()and not blocked else 1)
