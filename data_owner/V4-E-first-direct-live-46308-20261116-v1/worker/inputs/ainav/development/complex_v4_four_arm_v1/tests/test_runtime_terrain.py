"""Actual RegisteredTerrain/PlacementTerrain, explicit metadata/array fixtures.
No native Runtime, selected controller/session, MuJoCo, numpy, Actor or step.
"""
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
import ast,hashlib,json,struct,sys,unittest
OWN=Path(__file__).resolve().parents[1];ROOT=OWN.parents[1]
SOURCE=ROOT/'consumer-deliveries/AINAV-CLIMB-PREPARATION-CANDIDATES-20261113-v1/common-source'
sys.path[:0]=[str(OWN),str(SOURCE)];blocked=[]
def fence(event,args):
    if event=='import' and str(args[0]).split('.')[0]in('numpy','torch','mujoco','onnxruntime'):
        blocked.append(str(args[0]));raise RuntimeError('Explicit terrain metadata only')
    if event in('socket.connect','socket.bind','socket.getaddrinfo','subprocess.Popen'):
        blocked.append(event);raise RuntimeError('No network/child/API probe')
sys.addaudithook(fence)
import runtime_terrain as entry
import native_entry
from v4_native_asset import load_scene,registry,SCENE_SHA256
from ainav.native import scene_registry,placement_contract

class Vec:
    def __init__(self,values):self.values=values
    def tobytes(self):return struct.pack('<'+'d'*len(self.values),*self.values)
    def tolist(self):return list(self.values)
class Mat:
    def reshape(self,*args):return self
    def tolist(self):return [[1.,0.,0.],[0.,1.,0.],[0.,0.,1.]]
class Goal:
    def __init__(self,xy):self.xy=xy
    def detach(self):return self
    def cpu(self):return self
    def numpy(self):return self
    def __getitem__(self,key):return Vec([*self.xy,0.][key[1]])
class Model:
    names=['complex_box_a','complex_box_b','complex_box_c']
    def body(self,key):return NS(name=self.names[key],id=key)if type(key)is int else NS(name=key,id=self.names.index(key))

class Tests(unittest.TestCase):
    def setUp(self):
        self.rows=[];self.scene=load_scene();self.registry=registry(self.scene,scene_registry)
        self.sim=NS(model=Model(),data=NS(time=0.,qpos=Vec([0.]*7),qvel=Vec([0.]*6),xpos={},xmat={}),queue=[],controller=object(),box_push_target=object())
        self.r=NS(step_count=0,sim=self.sim,last=NS(array=lambda:Vec([0.]*90)))
        self.components=dict(runtime=self.r,registry=self.registry,scene=self.scene,scene_sha256=SCENE_SHA256)
        self.journal=lambda row:self.rows.append(row)or'EXPLICIT_SOFTWARE_NO_NATIVE_INSTALLATION'
    def install(self,**kw):
        args=dict(components=self.components,source_root=SOURCE,guard=lambda:None,journal=self.journal,enabled=True);args.update(kw)
        return entry.install_cold_registered_terrain(**args)
    def view(self,contract):
        index=['cuboid_a','cuboid_b','cuboid_c'].index(contract.target_ref)
        self.sim.data.xpos[index]=Vec([*contract.public_goal_xy_m,.1]);self.sim.data.xmat[index]=Mat()
        return NS(model=self.sim.model,data=self.sim.data,queue=self.sim.queue,box_id=index,box_push_target=Goal(contract.drive_goal_xy_m))
    def test_default_OFF_no_owner_or_source_access(self):
        with patch.object(entry,'_original',side_effect=AssertionError('No source read')):
            self.assertIsNone(entry.install_cold_registered_terrain())
        with self.assertRaises(ValueError):entry.install_cold_registered_terrain(enabled=1)
    def test_missing_false_or_throwing_guard_before_any_hardware_import(self):
        for guard in (None,lambda:False,lambda:(_ for _ in ()).throw(PermissionError('EXPLICIT_SOFTWARE_denied'))):
            with self.assertRaises((ValueError,PermissionError)):self.install(guard=guard)
            self.assertFalse(hasattr(self.r,'staircase'))
        self.assertFalse(blocked)
    def test_actual_registered_geometry_inherited_and_no_flat_or_success_stub(self):
        before=entry._snapshot(self.r);receipt=self.install();terrain=self.r.staircase
        self.assertIsInstance(terrain,scene_registry.RegisteredTerrain);self.assertIs(terrain.registry,self.registry)
        for name in ('height_at','surface_geometry','climb_geometry'):
            self.assertIs(getattr(type(terrain),name),getattr(scene_registry.RegisteredTerrain,name))
        self.assertFalse(hasattr(terrain,'push_ready'));self.assertEqual(entry._snapshot(self.r),before)
        self.assertEqual(len(receipt['six_contract_sha256']),6);self.assertFalse(receipt['actual_PUSH_constructor_qualified'])
    def test_all_six_dock_diagnostics_use_exact_original_PlacementTerrain_reader(self):
        self.install()
        for contract in self.r.staircase.placement_contracts.values():
            view=self.view(contract);before=entry._snapshot(self.r)
            measured=self.r.staircase.dock_metrics(view)
            self.assertEqual(measured,placement_contract.PlacementTerrain(contract).dock_metrics(view))
            self.assertEqual(measured['contract_sha256'],contract.sha256)
            self.assertTrue(measured['native_goal_confirmed_separately_required']);self.assertTrue(measured['protected_stow_completion_separately_required'])
            self.assertEqual(entry._snapshot(self.r),before)
    def test_exact_original_eager_fetch_previously_fails_then_actual_AttemptTerrain_delegates(self):
        path=SOURCE/'ainav/native/registered_push_api.py';tree=ast.parse(path.read_bytes())
        f=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='_selected_registered_push_session')
        assign=next(n for n in f.body if isinstance(n,ast.Assign)and ast.unparse(n)=='terrain = runtime.staircase')
        cls=next(n for n in f.body if isinstance(n,ast.ClassDef)and n.name=='AttemptTerrain')
        code=compile(ast.Module(body=[assign,cls],type_ignores=[]),str(path)+':two_ABI_nodes_only','exec');ns={'runtime':self.r}
        with self.assertRaises(AttributeError):exec(code,ns)
        self.install();exec(code,ns);attempt=ns['AttemptTerrain']();c=next(iter(self.r.staircase.placement_contracts.values()))
        self.assertFalse(attempt.push_ready(None,False));self.assertTrue(attempt.push_ready(None,True))
        self.assertEqual(attempt.dock_metrics(self.view(c)),self.r.staircase.dock_metrics(self.view(c)))
        self.assertIs(attempt.height_at.__func__,scene_registry.RegisteredTerrain.height_at)
    def test_cold_native_entry_calls_real_installer_after_original_constructor_not_compile(self):
        called=[]
        def bound(name):
            self.assertEqual(name,'construct_cold_components')
            def original(**kw):called.append(kw);return self.components
            return original
        with patch.object(native_entry,'_bound_original',side_effect=bound):
            out=native_entry.construct_cold_components(enabled=True,source_root=SOURCE,guard=lambda:None,journal=self.journal)
        self.assertIs(out,self.components);self.assertTrue(out['V4_runtime_terrain_ABI_receipt']['original_registered_terrain_bound'])
        self.assertEqual(len(called),1);self.assertFalse(out['V4_whole_chain_or_method_admission'])
    def test_step_time_queue_existing_None_or_legacy_terrain_cannot_install(self):
        for change in ('step','time','queue','None','legacy'):
            with self.subTest(change=change):
                self.setUp()
                if change=='step':self.r.step_count=1
                if change=='time':self.sim.data.time=.005
                if change=='queue':self.sim.queue.append(Vec([0.]*18))
                if change=='None':self.r.staircase=None
                if change=='legacy':self.r.staircase=object()
                with self.assertRaises(ValueError):self.install()
    def test_duplicate_install_refuses_without_replacing_real_registered_object(self):
        self.install();old=self.r.staircase
        with self.assertRaises(ValueError):self.install()
        self.assertIs(self.r.staircase,old)
    def test_scene_or_registry_change_rejected_before_installation(self):
        self.components['scene_sha256']='f'*64
        with self.assertRaises(ValueError):self.install()
        self.components['scene_sha256']=SCENE_SHA256;self.registry.retired_objects=frozenset(('cuboid_a',))
        with self.assertRaises(ValueError):self.install()
        self.assertFalse(hasattr(self.r,'staircase'))
    def test_wrong_view_world_queue_goal_or_retired_body_cannot_produce_diagnostics(self):
        self.install();c=next(iter(self.r.staircase.placement_contracts.values()))
        for change in ('model','data','queue','goal','retired'):
            v=self.view(c)
            if change=='model':v.model=Model()
            if change=='data':v.data=NS()
            if change=='queue':v.queue=[]
            if change=='goal':v.box_push_target=Goal((100.,100.))
            if change=='retired':self.registry.retired_objects=frozenset((c.target_ref,))
            with self.assertRaises(ValueError):self.r.staircase.dock_metrics(v)
    def test_non_durable_journal_or_guard_refusal_never_publishes_terrain(self):
        with self.assertRaises(ValueError):self.install(journal=lambda row:None)
        self.assertFalse(hasattr(self.r,'staircase'))
        calls=[]
        def guard():calls.append(1);return None if len(calls)==1 else False
        with self.assertRaises(ValueError):self.install(guard=guard)
        self.assertFalse(hasattr(self.r,'staircase'))
    def test_original_sources_unchanged_no_Physics_or_API_import_attempts(self):
        for n,pin in entry.PINS.items():self.assertEqual(hashlib.sha256((SOURCE/'ainav/native'/n).read_bytes()).hexdigest(),pin)
        self.assertFalse(blocked)

if __name__=='__main__':
    r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
    print(json.dumps(dict(role='V4_COLD_ACTUAL_REGISTERED_TERRAIN_ABI_SOFTWARE_ONLY_NOT_PUSH_NATIVE_QUALIFICATION',checks=r.testsRun,failures=len(r.failures),errors=len(r.errors),forbidden_attempts=blocked,Runtime_controller_constructor_Actor_physics_API_calls=0)))
    sys.exit(0 if r.wasSuccessful()and not blocked else 1)
