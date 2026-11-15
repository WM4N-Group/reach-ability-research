"""Original judgement/software caller fixtures. NO native or image execution."""
from pathlib import Path
from types import SimpleNamespace as NS
from dataclasses import replace
from unittest.mock import patch
import math,sys,json,unittest
OWN=Path(__file__).resolve().parents[1];ROOT=OWN.parents[1]
SOURCE=ROOT/'consumer-deliveries/AINAV-CLIMB-PREPARATION-CANDIDATES-20261113-v1/common-source'
sys.path[:0]=[str(OWN),str(SOURCE)]
blocked=[]
def fence(event,args):
    if event=='import' and str(args[0]).split('.')[0] in ('numpy','torch','mujoco','onnxruntime'):
        blocked.append(str(args[0]));raise RuntimeError('Source fixture only')
    if event in ('socket.connect','socket.bind','socket.getaddrinfo','subprocess.Popen'):
        blocked.append(event);raise RuntimeError('No network/child')
sys.addaudithook(fence)
import live_driver as driver
import execution_entry
from ainav.intents import SkillIntent
from ainav.native import scene_registry
from v4_native_asset import load_scene
from public_candidates import declarations

class Vec:
    def __init__(self,values):self.values=values
    def tolist(self):return self.values
class Matrix:
    def reshape(self,*shape):return self
    def __getitem__(self,key):
        if type(key)is tuple:return 1. if key[0]==key[1] else 0.
        return self
class Feet:
    def __getitem__(self,key):return Vec([[-.1,-.1,.022],[-.1,.1,.022],[.1,-.1,.022],[.1,.1,.022]])
class Forces:
    def __init__(self,fixture):self.fixture=fixture
    def __getitem__(self,key):return Vec([self.fixture.load]*4)

class Tests(unittest.TestCase):
    def setUp(self):self.scene=load_scene()
    def test_default_off_needs_no_root_native_or_owner(self):
        self.assertIsNone(driver.driver_class())
        with self.assertRaises(ValueError):driver.driver_class(enabled=1)
        self.assertFalse(blocked)
    def test_six_helpers_borrowed_old_installer_cannot_overwrite_factor_binding(self):
        cls=driver.driver_class(source_root=SOURCE,enabled=True)
        self.assertEqual(cls.__bases__,(object,));self.assertFalse(cls.full_task_terminal_integrated)
        methods=driver._original_methods();self.assertEqual(set(methods),set(driver.BASE_METHOD_PINS))
        for name,fn in methods.items():
            if name!='_install_common_stow':self.assertIs(getattr(cls,name),fn)
        self.assertFalse(hasattr(cls,'_install_common_stow'))
        self.assertEqual(cls.observe_public.__module__,'live_driver')
        self.assertEqual(cls.judge_intent.__module__,'live_driver')
    def test_owner_explicit_false_or_exception_refuses_before_native_import(self):
        cls=driver.driver_class(source_root=SOURCE,enabled=True)
        for callback in [lambda:False,lambda:(_ for _ in ()).throw(PermissionError('SOFTWARE denied'))]:
            with self.assertRaises((ValueError,PermissionError)):
                cls(None,bundle=None,output_root=None,writer=None,planner=None,journal=lambda row:'SOFTWARE',guard=callback,arm='E')
        with self.assertRaisesRegex(ValueError,'guard refused'):
            execution_entry.build_after_actual_capture(enabled=True,guard=lambda:False,journal=lambda row:'SOFTWARE')
        self.assertFalse(blocked)
    def test_every_exact_shared_intent_matches_and_arbitrary_parameter_refuses(self):
        for i,row in enumerate(declarations(self.scene)):
            intent=SkillIntent('SOFTWARE-%d'%i,row['skill'],row['target_ref'],tuple(sorted(row['parameters'].items())))
            self.assertEqual(driver.exact_declared_intent(self.scene,intent),row)
            p=dict(intent.parameters);p['surface_height_m']+=.01
            with self.assertRaises(ValueError):driver.exact_declared_intent(self.scene,replace(intent,parameters=tuple(sorted(p.items()))))
    def test_current_aliases_empty_frame_discards_old_left_view(self):
        resolver=NS(_observed={'SOFTWARE-opaque':('SOFTWARE-body',{})})
        descriptor=dict(target_ref='SOFTWARE-opaque',descriptor={'pixel_bbox_xyxy':[1,1,9,9]},RGB_sha256='a'*64)
        aliases,objects=driver.current_aliases([descriptor],resolver,{'cuboid_a':'SOFTWARE-body'})
        self.assertEqual(aliases,{'cuboid_a':'SOFTWARE-opaque'})
        self.assertEqual(objects[0]['label'],'cuboid_a; current original RGBD one-to-one association')
        new_aliases,new_objects=driver.current_aliases([],resolver,{'cuboid_a':'SOFTWARE-body'})
        self.assertEqual((new_aliases,new_objects),({},[]));self.assertEqual(aliases,{'cuboid_a':'SOFTWARE-opaque'})
    def test_alias_ambiguity_does_not_pick_largest_or_rename(self):
        resolver=NS(_observed={'SOFTWARE-opaque':('SOFTWARE-body',{})})
        descriptor=dict(target_ref='SOFTWARE-opaque',descriptor={'pixel_bbox_xyxy':[1,1,9,9]},RGB_sha256='a'*64)
        with self.assertRaises(ValueError):driver.current_aliases([descriptor],resolver,{'cuboid_a':'SOFTWARE-body','cuboid_b':'SOFTWARE-body'})
        with self.assertRaises(ValueError):driver.current_aliases([descriptor,descriptor],resolver,{'cuboid_a':'SOFTWARE-body'})
    def setup_judge(self,x=0.,source='ground'):
        cls=driver.driver_class(source_root=SOURCE,enabled=True);self.host=cls.__new__(cls)
        self.logs=[];self.prepared=[];self.load=12.;self.orientation=True;self.top=.2
        self.host.scene=self.scene;self.host.execution_sequence=0;self.host._native_guards=lambda:None;self.host._contact_guard=lambda:None
        self.host.public_body={o['public_ref']:o['body_name']for o in self.scene['objects']}
        self.host.entity_by_public={'cuboid_a':'SOFTWARE-opaque'}
        self.host.registry=NS(surfaces={'ground':NS(bounds_xy_m=(-20.,20.,-10.,10.),top_z_m=0.)})
        witness=NS(support_ref=source,validate=lambda runtime:True)
        self.host.factory=NS(_current_completed_witness=lambda:witness,
            prepare_public_climb=lambda outer,inner:self.prepared.append(('CLIMB',outer,inner)),
            prepare_private_entry_nav=lambda option,judgment:self.prepared.append(('PREPARE',option,judgment)))
        data=NS(time=1.,qpos=[x,0.],xmat=Matrix(),xpos=Feet())
        model=NS(body=lambda name:NS(id=23),geom=lambda name:NS(id=2))
        self.host.r=NS(sim=NS(data=data,model=model,feet_ids=[0,1,2,3],forces=Forces(self),base_id=0))
        self.host.np=NS(allclose=lambda *args,**kwargs:self.orientation,eye=lambda n:Matrix(),arctan2=math.atan2)
        self.host.executor=NS(fatal=False);self.host.api=NS(world_snapshot=lambda runtime:('SOFTWARE-not-physical',))
        self.host.journal=lambda row:self.logs.append(row)or'SOFTWARE-only'
        self.host._selected_placement_ready=lambda obj:True
        original=scene_registry.RegisteredTerrain
        fixture=self
        class SoftwareTerrain:
            def __init__(self,registry):pass
            def surface_geometry(self,sim,ref):return dict(front=1.,lane_y_m=0.,top=fixture.top,length=2.4,width=1.4)
            def climb_geometry(self,sim,ref,*,source_surface_height_m):
                return original.climb_geometry(self,sim,ref,source_surface_height_m=source_surface_height_m)
        self.addCleanup(patch.stopall);patch.object(scene_registry,'RegisteredTerrain',SoftwareTerrain).start()
        return SkillIntent('SOFTWARE-CLIMB','CLIMB','cuboid_a:upper-entry',(('surface_height_m',.2),))
    def test_real_original_judge_READY_maps_destination_without_source_substitution(self):
        intent=self.setup_judge();status,outer,proof=self.host.judge_intent(intent,1.)
        self.assertEqual(status,'READY');self.assertEqual(outer.parameters,intent.parameters)
        self.assertEqual(self.prepared[-1][0],'CLIMB');inner=self.prepared[-1][2]
        self.assertEqual(inner.target_ref,'SOFTWARE-opaque');self.assertEqual(inner.parameters,outer.parameters)
        judgment=next(row for row in self.logs if row['event']=='skill_execution_judgment')
        self.assertEqual(judgment['status'],'READY');self.assertEqual(judgment['spec']['source_height_m'],0.)
        self.assertFalse(judgment['physical_success_claimed']);self.assertFalse(judgment['model_input'])
    def test_far_same_ground_CLIMB_prepares_NAV_not_early_domain_rejection(self):
        intent=self.setup_judge(x=-3.);status,option,proof=self.host.judge_intent(intent,1.)
        self.assertEqual(status,'PREPARE');self.assertEqual(option.skill,'NAV')
        self.assertEqual(dict(option.parameters)['surface_height_m'],0.)
        self.assertEqual(self.prepared[-1][0],'PREPARE');self.assertEqual(self.prepared[-1][2].status,'PREPARE')
    def test_under12N_or_rotated_target_never_ready(self):
        for change in ('load','orientation'):
            with self.subTest(change=change):
                intent=self.setup_judge()
                if change=='load':self.load=11.999
                else:self.orientation=False
                status,reason,proof=self.host.judge_intent(intent,1.)
                self.assertEqual(status,'BLOCKED');self.assertFalse(self.prepared)
                patch.stopall()
    def test_missing_current_alias_or_required_placement_is_not_ready(self):
        for change in ('alias','placement'):
            with self.subTest(change=change):
                intent=self.setup_judge()
                if change=='alias':self.host.entity_by_public={}
                else:self.host._selected_placement_ready=lambda obj:False
                self.assertEqual(self.host.judge_intent(intent,1.)[0],'BLOCKED');self.assertFalse(self.prepared)
                patch.stopall()
    def test_post_CLIMB_dynamic_support_not_faked_as_ground(self):
        intent=self.setup_judge(source='cuboid_a')
        status,reason,proof=self.host.judge_intent(intent,1.)
        self.assertEqual(status,'BLOCKED');self.assertIn('Dynamic-box',reason);self.assertFalse(self.prepared)
    def test_static_deck_and_original40cm_rejection_remain(self):
        intent=self.setup_judge()
        static=SkillIntent('SOFTWARE-deck','CLIMB','goal_deck',(('surface_height_m',.6),))
        self.assertIn('Static goal_deck',self.host.judge_intent(static,1.)[1])
        self.host.registry.surfaces['ground'].top_z_m=.2;self.top=.6
        self.assertIn('Original 20cm',self.host.judge_intent(intent,1.)[1]);self.assertFalse(self.prepared)
    def test_wrong_clock_not_softened_into_task_replanning(self):
        intent=self.setup_judge()
        with self.assertRaisesRegex(ValueError,'entry clock'):self.host.judge_intent(intent,2.)

if __name__=='__main__':
    r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
    print(json.dumps(dict(role='V4_LIVE_OBSERVER_SELECTED_JUDGE_AND_LOOP_SOURCE_FIXTURES_NOT_NATIVE',checks=r.testsRun,failures=len(r.failures),errors=len(r.errors),forbidden_attempts=blocked,actual_camera_Runtime_Actor_physics_API_calls=0)))
    sys.exit(0 if r.wasSuccessful()and not blocked else 1)
