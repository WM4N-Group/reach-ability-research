"""Recorder boundary fixtures from the closed failure, NOT a real RGBD capture."""
from pathlib import Path
from types import SimpleNamespace as NS
import ast,copy,json,sys,unittest
OWN=Path(__file__).resolve().parents[1];ROOT=OWN.parents[1]
SOURCE=ROOT/'consumer-deliveries/AINAV-CLIMB-PREPARATION-CANDIDATES-20261113-v1/common-source'
sys.path[:0]=[str(OWN),str(SOURCE)]
blocked=[]
def fence(event,args):
    if event=='import'and str(args[0]).split('.')[0]in('numpy','torch','mujoco','onnxruntime'):
        blocked.append(str(args[0]));raise RuntimeError('Explicit metadata fixture only')
    if event in('socket.connect','socket.bind','socket.getaddrinfo','subprocess.Popen'):
        blocked.append(event);raise RuntimeError('No network/child')
sys.addaudithook(fence)
import live_driver as driver

class Tests(unittest.TestCase):
    def catalog(self,tick=0):return dict(schema='ainav-private-registered-object-catalog-v1',model_input=False,
        control_tick=tick,time_s=tick*.02,objects=[{'EXPLICIT_SOFTWARE_PRIVATE_NOT_MODEL':True}],material_truth_included=False)
    def test_original_registered_schema_and_original_writer_disagree_on_marker(self):
        # Compile only the original pure catalog-return statement from its AST;
        # do not import observer/stream modules or create tensor/renderer/Runtime.
        tree=ast.parse((SOURCE/'ainav/native/registered_observer.py').read_text())
        cls=next(n for n in tree.body if isinstance(n,ast.ClassDef))
        fn=next(n for n in cls.body if isinstance(n,ast.FunctionDef)and n.name=='private_catalog')
        ret=next(n for n in fn.body if isinstance(n,ast.Return))
        original=eval(compile(ast.Expression(ret.value),'<original-private-metadata-return>','eval'),
            {'p':NS(data=NS(time=0.)),'tick':0,'objects':[]})
        self.assertIs(original['model_input'],False);self.assertNotIn('model_input_allowed',original)
        stream=(SOURCE/'mujoco_zyh/streams.py').read_text()
        self.assertIn("private_catalog.get('model_input_allowed') is not False",stream)
        self.assertIs(driver.stream_private_catalog(original,control_tick=0,actual_time_s=0.)['model_input_allowed'],False)
    def test_projection_is_private_and_does_not_mutate_actual_metadata(self):
        original=self.catalog(5);before=copy.deepcopy(original)
        result=driver.stream_private_catalog(original,control_tick=5,actual_time_s=.1)
        self.assertEqual(original,before);self.assertEqual(set(result)-set(original),{'model_input_allowed'})
        self.assertIs(result['model_input'],False);self.assertIs(result['model_input_allowed'],False)
        self.assertEqual({k:v for k,v in result.items()if k!='model_input_allowed'},before)
    def test_public_wrong_schema_missing_private_flag_and_conflicting_permission_reject(self):
        for delta in ({'schema':'SOFTWARE-public'}, {'model_input':True}, {'model_input':None},
                      {'model_input_allowed':True},{'model_input_allowed':0}):
            with self.assertRaises(ValueError):driver.stream_private_catalog(dict(self.catalog(),**delta),control_tick=0,actual_time_s=0.)
    def test_stale_fractional_boolean_nonfinite_or_mismatched_clock_rejects(self):
        for delta in ({'control_tick':True},{'control_tick':1},{'time_s':.1},{'time_s':float('nan')},
                      {'time_s':float('inf')},{'time_s':False}):
            with self.assertRaises(ValueError):driver.stream_private_catalog(dict(self.catalog(),**delta),control_tick=0,actual_time_s=0.)
        for tick,now in [(True,0.),(0,.1),(0,float('nan')),(0,False)]:
            with self.assertRaises(ValueError):driver.stream_private_catalog(self.catalog(),control_tick=tick,actual_time_s=now)
    def make_host(self):
        cls=driver.driver_class(source_root=SOURCE,enabled=True);host=cls.__new__(cls)
        host.tick=0;host.last_capture_tick=None;host._last_issued='EXPLICIT_SOFTWARE_REF'
        host.r=NS(sim=NS(data=NS(time=0.)));self.captures=[];self.writes=[]
        def capture(tick,previous):
            self.captures.append((tick,previous));return 'EXPLICIT_SOFTWARE_PACKET',self.catalog(tick)
        host.observer=NS(capture=capture)
        host.writer=NS(append_visual=lambda packet,**kw:self.writes.append((packet,kw)))
        return host
    def test_driver_actual_capture_path_projects_once_per_original_grid_tick(self):
        host=self.make_host();host.capture_grid();host.capture_grid()
        host.tick=4;host.r.sim.data.time=.02;host.capture_grid()
        host.tick=20;host.r.sim.data.time=.1;host.capture_grid()
        self.assertEqual([t for t,_ in self.captures],[0,5]);self.assertEqual(len(self.writes),2)
        self.assertEqual(host.last_capture_tick,20)
        for packet,kw in self.writes:
            self.assertEqual(packet,'EXPLICIT_SOFTWARE_PACKET')
            self.assertIs(kw['private_catalog']['model_input_allowed'],False)
    def test_writer_rejection_never_advances_capture_marker_or_drops_error(self):
        host=self.make_host()
        def reject(*args,**kwargs):raise ValueError('EXPLICIT_SOFTWARE writer refused')
        host.writer.append_visual=reject
        with self.assertRaisesRegex(ValueError,'writer refused'):host.capture_grid()
        self.assertIsNone(host.last_capture_tick)

if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
    print(json.dumps(dict(role='EXPLICIT_SOFTWARE_PRIVATE_CATALOG_STREAM_BOUNDARY_NOT_SENSOR_OR_NATIVE',
        checks=result.testsRun,failures=len(result.failures),errors=len(result.errors),forbidden_attempts=blocked,
        actual_Runtime_Actor_physics_RGBD_sensor_API_calls=0)))
    sys.exit(0 if result.wasSuccessful()and not blocked else 1)
