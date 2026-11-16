"""E20 pure geometry/schema/actual rule fixtures, NOT physical success/video.
Original SceneRegistry/PlacementContract/intent/receipt classes are imported;
all runtime/measurements/receipts are explicit software fixtures. No native IO.
"""
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
from copy import deepcopy
from dataclasses import replace
import ast,hashlib,json,struct,sys,unittest
OWN=Path(__file__).resolve().parents[1];ROOT=OWN.parents[1];SOURCE=ROOT/'consumer-deliveries/AINAV-CLIMB-PREPARATION-CANDIDATES-20261113-v1/common-source';sys.path[:0]=[str(OWN),str(SOURCE)]
blocked=[]
def fence(event,args):
    if event=='import'and str(args[0]).split('.')[0]in('numpy','torch','mujoco','onnxruntime','wm_stream_bridge','method_entry','backbone_entry','deepseek'):
        blocked.append(str(args[0]));raise RuntimeError('Explicit E20 metadata only')
    if event in('socket.connect','socket.bind','socket.getaddrinfo','subprocess.Popen'):
        blocked.append(event);raise RuntimeError('No network/child/API')
sys.addaudithook(fence)
import v4_native_asset as asset
import goal_support as support
import native_entry,execution_entry,runtime_terrain,e_entry,live_driver
from elevated_terminal import deck_normal_loads,ElevatedGoalDwell
from capability_boundary import elevated_stop_sample_only
from task_terminal import check_chain_rows
from rule_baseline import RuleBaseline
from public_candidates import declarations,declared_map,intent_catalogue,capability_contract
from ainav.contracts import Observation
from ainav.intents import IntentBatch
from ainav.native import scene_registry as api
from ainav.native.behavior_authority import BehaviorOption,NativeReceipt

class Bytes:
    def __init__(self,values):self.values=values
    def tobytes(self):return struct.pack('<'+'d'*len(self.values),*self.values)
class Tests(unittest.TestCase):
    def setUp(self):self.scene=asset.load_scene();self.reg=asset.registry(self.scene,api);self.rows=[]
    def components(self):
        sim=NS(model=object(),data=NS(time=0.,qpos=Bytes([0.]*7),qvel=Bytes([0.]*6)),queue=[],controller=object(),box_push_target=object())
        r=NS(sim=sim,step_count=0,last=NS(array=lambda:Bytes([0.]*90)))
        return dict(scene=self.scene,scene_sha256=asset.SCENE_SHA256,registry=self.reg,runtime=r)
    def sample(self,**kw):
        s=dict(time_s=0.,tick=0,feet_world_m=[[11.3,-2.8,.222],[11.3,-2.4,.222],[11.9,-2.8,.222],[11.9,-2.4,.222]],foot_normal_N=[20.]*4,foot_speed_m_s=[0.]*4,foot_support_refs=['cuboid_c']*4,base_linear_speed_m_s=0.,base_angular_speed_rad_s=0.,tilt_rad=0.)
        s.update(kw);return s
    def test_exact_new_scene_original_V4_unchanged_and_safety_proto_retained(self):
        old=json.loads((ROOT/'development/complex_v4_four_arm_v1/scene.json').read_bytes())
        self.assertEqual(hashlib.sha256((ROOT/'development/complex_v4_four_arm_v1/scene.json').read_bytes()).hexdigest(),'6394740eb54b99ec0e0b4b35b0f804e7875dfc29255d9f897ba57b1ac0b48d20')
        self.assertEqual(self.scene['objects'],old['objects']);self.assertEqual(self.scene['platforms'][0]['top_z_m'],.2)
        for k,v in old['private_terminal_acceptance'].items():
            if k not in ('required_goal_support_ref','required_goal_support_height_m'):self.assertEqual(self.scene['private_terminal_acceptance'][k],v)
        self.assertEqual(self.scene['task']['goal_surface_ref'],'cuboid_c');self.assertNotEqual(self.scene['scene_id'],old['scene_id'])
    def test_dynamic_goal_not_inserted_or_mislabelled_as_fixed_surface(self):
        support.assert_declared_goal(self.reg,self.scene)
        self.assertIs(type(self.reg),support.registry_type(api));self.assertEqual(self.reg.goal.surface_ref,'cuboid_c')
        self.assertNotIn('cuboid_c',self.reg.surfaces);self.assertEqual(set(self.reg.surfaces),{'ground','goal_deck'})
        self.assertIs(type(self.reg).verify_compiled,api.SceneRegistry.verify_compiled)
    def test_original_registry_still_rejects_movable_goal_no_global_patch(self):
        with self.assertRaisesRegex(ValueError,'declared surface'):
            api.SceneRegistry(self.reg.objects.values(),self.reg.surfaces.values(),self.reg.goal)
        self.assertIsNot(type(self.reg),api.SceneRegistry)
    def test_declared_goal_has_no_current_support_or_task_success_authority(self):
        self.assertTrue(self.reg.dynamic_goal_is_declaration_not_current_support)
        self.assertFalse(hasattr(self.reg,'validate'));self.assertFalse(hasattr(self.reg,'complete'))
        with self.assertRaises(ValueError):support.actual_nav_goal_registry(self.reg,api.SurfaceSpec('ground','ground',(-20,20,-10,10),0.),'cuboid_c')
    def test_actual_source_private_registry_uses_registered_C_geom_and_goal_alias(self):
        surface=api.SurfaceSpec('climb_nav_source__cuboid_c','complex_box_c_geom',(10.4,12.8,-3.3,-1.9),.2)
        result=support.actual_nav_goal_registry(self.reg,surface,'cuboid_c')
        self.assertIs(type(result),api.SceneRegistry);self.assertEqual(result.goal.surface_ref,surface.ref)
        self.assertEqual(result.surfaces[surface.ref],surface);self.assertNotIn(surface.ref,self.reg.surfaces)
        self.assertEqual(result.goal.bounds_xy_m,tuple(self.scene['task']['goal_bounds_xy_m']))
    def test_wrong_object_wrong_geom_height_and_goal_extent_refuse_source_registry(self):
        good=api.SurfaceSpec('climb_nav_source__cuboid_c','complex_box_c_geom',(10.4,12.8,-3.3,-1.9),.2)
        for surface,obj in [(replace(good,top_z_m=.6),'cuboid_c'),(replace(good,geom_name='goal_deck'),'cuboid_c'),(good,'cuboid_b'),(replace(good,bounds_xy_m=(0.,1.,0.,1.)),'cuboid_c')]:
            with self.assertRaises(ValueError):support.actual_nav_goal_registry(self.reg,surface,obj)
    def test_cold_terrain_installer_accepts_exact_dynamic_goal_type_original_geometry(self):
        components=self.components();r=components['runtime'];before=runtime_terrain._snapshot(r)
        result=runtime_terrain.install_cold_registered_terrain(components,source_root=SOURCE,guard=lambda:None,journal=lambda row:self.rows.append(row)or'EXPLICIT_SOFTWARE_NOT_PHYSICS',enabled=True)
        self.assertEqual(runtime_terrain._snapshot(r),before);self.assertIsInstance(r.staircase,api.RegisteredTerrain)
        self.assertIs(type(r.staircase).height_at,api.RegisteredTerrain.height_at);self.assertEqual(len(result['six_contract_sha256']),6)
    def test_entry_native_constructs_cold_metadata_then_terrain_no_runtime_instantiation(self):
        components=self.components()
        with patch.object(native_entry,'_bound_original',return_value=lambda **kwargs:components):
            out=native_entry.construct_cold_components(enabled=True,source_root=SOURCE,guard=lambda:None,journal=lambda row:'EXPLICIT_SOFTWARE')
        self.assertIs(out,components);self.assertTrue(out['V4_runtime_terrain_ABI_receipt']['original_registered_terrain_bound'])
    def test_six_unchanged_original_placement_contracts_and29_public_intents(self):
        contracts=execution_entry.finite_placement_contracts(self.scene,source_root=SOURCE);self.assertEqual(len(contracts),6);self.assertEqual(len(declarations(self.scene)),29)
        rows=[r for r in declarations(self.scene)if r['target_ref']=='v4-goal-elevated'];self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['parameters'],dict(goal_world_x_m=11.6,goal_world_y_m=-2.6,surface_height_m=.2))
        for c in contracts.values():self.assertEqual((c.public_XY_tolerance_m,c.original_dock_tolerance_m,c.original_native_settled_distance_m),(.02,.01,.12))
    def test_one_original20cm_CLIMB_required_never_ground_or40cm(self):
        row=dict(time_s=1.,source_height_m=0.,destination_height_m=.2,target_ref='cuboid_c',native_stop_success=True)
        self.assertTrue(check_chain_rows([row],goal_ref='cuboid_c',goal_height=.2))
        for rows in ([],[dict(row,target_ref='goal_deck')],[dict(row,destination_height_m=.6)],[dict(row,native_stop_success=False)]):
            with self.assertRaises(ValueError):check_chain_rows(rows,goal_ref='cuboid_c',goal_height=.2)
    def test_current_goal_geometry_rejects_static_alias_initial_pose_or_drift(self):
        kw=dict(box_size=[2.4,1.4,.2],actual_geom_body_id=5,selected_body_id=5,geom_is_box=True,xyz=[11.6,-2.6,.1],rotation=[[1.,0.,0.],[0.,1.,0.],[0.,0.,1.]])
        self.assertTrue(support.check_current_goal_geometry(self.scene,**kw))
        for patch_kw in (dict(actual_geom_body_id=0),dict(selected_body_id=0,actual_geom_body_id=0),dict(xyz=[11.,-2.6,.1]),dict(xyz=[11.6,-2.6,.5]),dict(geom_is_box=False),dict(box_size=[2.4,1.4,.6])):
            with self.assertRaises(ValueError):support.check_current_goal_geometry(self.scene,**dict(kw,**patch_kw))
    def test_original_contact_normal_calculus_and_goal_height_load_thresholds(self):
        loads=deck_normal_loads({1:0,2:1,3:2,4:3},10,[(10,i,[0.,0.,1.],12.)for i in range(1,5)])
        self.assertEqual(loads,[12.]*4);self.assertTrue(elevated_stop_sample_only(self.scene,self.sample()))
        for sample in (self.sample(foot_support_refs=['goal_deck']*4),self.sample(feet_world_m=[[11.3,-2.8,.022]]*4),self.sample(foot_normal_N=[11.99]*4)):
            self.assertFalse(elevated_stop_sample_only(self.scene,sample))
    def test_contiguous_half_second_dwell_not_single_sample_or_clock_jump(self):
        monitor=ElevatedGoalDwell(self.scene);self.assertFalse(monitor.observe(self.sample()))
        for tick in range(1,101):value=monitor.observe(self.sample(time_s=tick*.005,tick=tick))
        self.assertTrue(value);self.assertFalse(monitor.observe(self.sample(time_s=.505,tick=101,foot_support_refs=['ground']*4)))
    def test_REAL_unchanged_E_rule_three_SOFTWARE_placements_CLIMB_C_then_final_NAV(self):
        self.assertEqual(hashlib.sha256((OWN/'rule_baseline.py').read_bytes()).hexdigest(),'43998a23f4e49161074658bdc26b72c47b6b501b97830b906b84b50751c98634')
        planner=RuleBaseline(self.scene,journal=lambda row:'EXPLICIT_SOFTWARE_RECEIPTS_NOT_NATIVE')
        selections=[]
        for tick in range(1,6):
            objects=[dict(target_ref='EXPLICIT_SOFTWARE_'+o['public_ref'],label=o['public_ref']+'; current original RGBD one-to-one association',bbox_xyxy=[1,1,9,9],evidence_ref='EXPLICIT_SOFTWARE',geometry=dict(status='unknown',source='unavailable',values={},uncertainty={}))for o in self.scene['objects']]
            obs=Observation.create(dict(time_s=float(tick),rgb=dict(path='/EXPLICIT_SOFTWARE_NOT_IMAGE',sha256='0'*64,time_s=float(tick),width=192,height=128),objects=objects,public_state={},declared_map=declared_map(self.scene),goal=self.scene['task']['instruction'],events=[]))
            batch=IntentBatch('EXPLICIT_SOFTWARE_%s'%tick,obs,intent_catalogue(self.scene,obs,sequence=tick),capability_contract());selected=planner.select(batch);intent=next(o for o in batch.options if o.sha256==selected.option_sha256);selections.append((intent.skill,intent.target_ref))
            actual=BehaviorOption('EXPLICIT_SOFTWARE_native_%s'%tick,intent.skill,intent.target_ref,intent.parameters,60.,'EXPLICIT_SOFTWARE_BINDING',**(dict(attempt_id='EXPLICIT_SOFTWARE',original_push_goal_sha256='a'*64)if intent.skill=='PUSH'else{}))
            receipt=NativeReceipt(actual.sha256,float(tick),'succeeded','a'*64,'EXPLICIT_SOFTWARE_NOT_COMMAND');planner.observe_intent(intent,actual,receipt,'EXPLICIT_SOFTWARE_BINDING')
        self.assertEqual(selections,[('PUSH','cuboid_a'),('PUSH','cuboid_b'),('PUSH','cuboid_c'),('CLIMB','cuboid_c:upper-entry'),('NAV','v4-goal-elevated')])
        self.assertTrue(planner.awaiting_terminal);self.assertFalse(planner.complete)
        with self.assertRaises(RuntimeError):planner.confirm_original_task_terminal(evidence_ref='not-a-proof')
    def test_only_goal_registry_view_delta_retains_actual_source_and_proof_gates(self):
        parent=ROOT/'development/complex_v4_four_arm_v1'
        old=(parent/'climb_nav_adapter.py').read_text()
        before="self.registry=SceneRegistry(r.objects.values(),(*r.surfaces.values(),observation.surface),r.goal,retired_objects=r.retired_objects)"
        after="from goal_support import actual_nav_goal_registry\n        self.registry=actual_nav_goal_registry(r,observation.surface,self.object_ref)"
        self.assertEqual((OWN/'climb_nav_adapter.py').read_text(),old.replace(before,after,1))
        def symbol(text,cls,name):
            tree=ast.parse(text);c=next(n for n in tree.body if isinstance(n,ast.ClassDef)and n.name==cls)
            return ast.get_source_segment(text,next(n for n in c.body if isinstance(n,ast.FunctionDef)and n.name==name))
        for cls,name in [('ActualClimbChain','record_current'),('VerifiedV4TaskTerminal','confirm_rule')]:
            self.assertEqual(symbol((parent/'task_terminal.py').read_text(),cls,name),symbol((OWN/'task_terminal.py').read_text(),cls,name))
        self.assertEqual((OWN/'capability_boundary.py').read_text().split('def elevated_stop_sample_only',1)[1],(parent/'capability_boundary.py').read_text().split('def elevated_stop_sample_only',1)[1])
    def test_model_world_API_default_OFF_and_native_Actor_sources_unchanged(self):
        self.assertIsNone(native_entry.construct_cold_components());self.assertIsNone(e_entry.build_E_driver())
        self.assertEqual(hashlib.sha256((SOURCE/'ainav/native/scene_registry.py').read_bytes()).hexdigest(),support.API_SHA)
        self.assertFalse(blocked)

if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
    print(json.dumps(dict(role='AUTHORIZED_E_SKILL20_ENVIRONMENT_AND_REAL_RULE_SOFTWARE_ONLY_NOT_NATIVE_OR_VIDEO',checks=result.testsRun,failures=len(result.failures),errors=len(result.errors),forbidden_attempts=blocked,world_Model_Runtime_Actor_render_API_or_WM_calls=0)))
    sys.exit(0 if result.wasSuccessful()and not blocked else 1)
