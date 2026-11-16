"""Explicit E driver-construction fixture, not native execution or video."""
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
import hashlib,json,sys,unittest
OWN=Path(__file__).resolve().parents[1];ROOT=OWN.parents[1];SOURCE=ROOT/'consumer-deliveries/AINAV-CLIMB-PREPARATION-CANDIDATES-20261113-v1/common-source'
sys.path[:0]=[str(OWN),str(SOURCE)];blocked=[]
def fence(event,args):
    forbidden=('numpy','torch','mujoco','onnxruntime','method_entry','backbone_entry','wm_stream_bridge','common_nav_prelude','visual_latent_behavior','visual_latent_world_model','deepseek')
    if event=='import' and str(args[0]).split('.')[0] in forbidden:
        blocked.append(str(args[0]));raise RuntimeError('E-only metadata assembly; no optional models')
    if event in('socket.connect','socket.bind','socket.getaddrinfo','subprocess.Popen'):
        blocked.append(event);raise RuntimeError('No API/transport/child')
sys.addaudithook(fence)
import e_entry
import live_driver
from factor_scope import FactorJournal
from rule_baseline import RuleBaseline
from v4_native_asset import load_scene,SCENE_SHA256

class Tests(unittest.TestCase):
    def setUp(self):
        self.rows=[];self.calls=[]
        self.r=NS(step_count=0,sim=NS(data=NS(time=0.),queue=[]))
        self.components=dict(scene=load_scene(),scene_sha256=SCENE_SHA256,runtime=self.r)
        self.writer=NS(steps=0,append_command=lambda **kw:None,append_visual=lambda *a,**kw:None)
        fixture=self
        class ExplicitDriverFixture:
            def __init__(self,components,**kw):
                fixture.calls.append((components,kw));self.r=components['runtime'];self.arm=kw['arm'];self.planner=kw['planner']
                self.journal=FactorJournal(self.arm,kw['journal']);self.planner.journal=self.journal
                self.loop=None;self.tick=0
        self.cls=ExplicitDriverFixture
    def build(self,**kw):
        args=dict(components=self.components,source_root=SOURCE,bundle='/EXPLICIT_SOFTWARE_NOT_SDK',output_root='/EXPLICIT_SOFTWARE_NOT_OUTPUT',writer=self.writer,journal=lambda row:self.rows.append(row)or'EXPLICIT_SOFTWARE_NOT_NATIVE',guard=lambda:None,enabled=True);args.update(kw)
        with patch.object(live_driver,'driver_class',return_value=self.cls)as mocked:
            result=e_entry.build_E_driver(**args)
        return result,mocked
    def test_default_OFF_no_owner_source_or_driver_initialization(self):
        with patch.object(live_driver,'driver_class',side_effect=AssertionError('No driver')):
            self.assertIsNone(e_entry.build_E_driver())
        with self.assertRaises(ValueError):e_entry.build_E_driver(enabled=1)
    def test_same_unchanged_REAL_E_rule_only_no_optional_method_or_model_imports(self):
        driver,mocked=self.build();mocked.assert_called_once_with(source_root=SOURCE,enabled=True)
        self.assertIs(type(driver.planner),RuleBaseline);self.assertEqual(driver.arm,'E')
        self.assertEqual(driver.planner.decision_count,0);self.assertEqual(driver.planner.native_success_count,0)
        self.assertIs(driver.journal,driver.planner.journal);self.assertIs(driver.r,self.r)
        self.assertFalse(driver.planner.complete);self.assertFalse(blocked)
        self.assertFalse(self.rows[-1]['E_complete_or_video_delivered'])
    def test_missing_or_denied_guard_before_driver(self):
        for guard in (None,lambda:False):
            with self.assertRaises(ValueError):self.build(guard=guard)
        self.assertFalse(self.calls)
    def test_nonfresh_runtime_or_writer_refuses_before_driver(self):
        for attr in ('step','time','queue','writer'):
            self.setUp()
            if attr=='step':self.r.step_count=1
            if attr=='time':self.r.sim.data.time=.005
            if attr=='queue':self.r.sim.queue.append(object())
            if attr=='writer':self.writer.steps=1
            with self.assertRaises(ValueError):self.build()
            self.assertFalse(self.calls)
    def test_other_scene_or_missing_raw_writer_never_assembled(self):
        self.components['scene_sha256']='f'*64
        with self.assertRaises(ValueError):self.build()
        self.components['scene_sha256']=SCENE_SHA256;self.writer.append_command=None
        with self.assertRaises(ValueError):self.build()
        self.assertFalse(self.calls)
    def test_no_external_planner_backend_WM_or_prefix_arguments(self):
        for name in ('planner','backend','wm_evaluator','shared_appearance','common_nav_prelude'):
            with self.assertRaises(TypeError):self.build(**{name:object()})
        self.assertFalse(self.calls)
    def test_original_rule_file_exact_and_compact_runtime_repair_remains_separate(self):
        self.assertEqual(hashlib.sha256((OWN/'rule_baseline.py').read_bytes()).hexdigest(),e_entry.E_RULE_SHA)
        driver,_=self.build();self.assertEqual(driver.planner.max_selections,64)
        self.assertFalse(hasattr(driver,'_v4_common_nav_prelude'));self.assertFalse(hasattr(driver,'_v4_wm_stream_bridge'))
    def test_non_durable_assembly_cannot_return_driver_or_claim_success(self):
        with self.assertRaises(ValueError):self.build(journal=lambda row:None)
        self.assertFalse(blocked)

if __name__=='__main__':
    r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
    print(json.dumps(dict(role='REAL_E_RULE_WITH_EXPLICIT_DRIVER_SOFTWARE_FIXTURE_NOT_NATIVE_OR_VIDEO',checks=r.testsRun,failures=len(r.failures),errors=len(r.errors),forbidden_attempts=blocked,WM_VLM_API_Actor_physics_or_camera_calls=0)))
    sys.exit(0 if r.wasSuccessful()and not blocked else 1)
