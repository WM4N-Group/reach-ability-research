"""Common declaration/loader metadata fixtures plus REAL Reach constructor.
No real new MJB/read, runtime, geometry detector/plane, VLM/WM/Actor/physics.
Every constructed context is explicitly fixture=True and cannot enter live driver.
"""
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
import copy,hashlib,importlib,json,os,sys,unittest
OWN=Path(__file__).resolve().parents[1];ROOT=OWN.parents[1]
SOURCE=ROOT/'consumer-deliveries/AINAV-CLIMB-PREPARATION-CANDIDATES-20261113-v1/common-source'
REACH=Path(os.environ.get('AINAV_V4_REACH_PUBLIC_PALETTE_ROOT',str(ROOT/'manifests/V4_four_arm_source_20261115_v1/reach-public-palette-readonly-reference')))
sys.path[:0]=[str(OWN),str(SOURCE),str(REACH)];blocked=[]
def fence(event,args):
    if event=='import'and str(args[0]).split('.')[0]in('numpy','torch','mujoco','onnxruntime'):
        blocked.append(str(args[0]));raise RuntimeError('Common declaration metadata fixture only')
    if event in('socket.connect','socket.bind','socket.getaddrinfo','subprocess.Popen'):
        blocked.append(event);raise RuntimeError('No transport/child/probe')
sys.addaudithook(fence)
import shared_appearance_public as common
import public_candidates as public
import live_driver
from ainav.contracts import Observation
from ainav.intents import IntentBatch
from rule_baseline import RuleBaseline
producer=importlib.import_module('research.task_conditioned_reachability.execution_preparation.v4_declared_palette_association')
pins={'v4_declared_palette_association.py':'f03aecbb94e32626603b0faeae2954640aff14ee96ac5b2d46fc632b16d8c46e',
      'v4_anchor_target8.py':'d0ba31e797ce3c799df6585389b71f2d628bc7850b8610721e668432f34060bf',
      'v4_successor_choice.py':'bb0d6ca0a7243354eea5e88f88534fc58bbaeea0eca9cbbf4fc7bcdf911eb1c9'}
for name,pin in pins.items():
 p=REACH/'research/task_conditioned_reachability/execution_preparation'/name;assert hashlib.sha256(p.read_bytes()).hexdigest()==pin
assert Path(producer.__file__).resolve()==REACH/'research/task_conditioned_reachability/execution_preparation/v4_declared_palette_association.py'

class Tests(unittest.TestCase):
    def setUp(self):
        self.scene=common.load_scene();self.rows=[];self.journal=lambda row:self.rows.append(row)or'EXPLICIT_SOFTWARE_NO_NATIVE_OR_AUTH'
        colors=common.palette(common.contract());self.ids={name:i for i,name in enumerate(colors)}
        model=NS(geom=lambda name:NS(id=self.ids[name]),geom_rgba=list(colors.values()),geom_matid=[-1]*3)
        self.components=dict(scene=self.scene,scene_sha256=common.SCENE_SHA256,runtime=NS(step_count=0,sim=NS(data=NS(time=0.),queue=[],model=model)),
            construction=dict(static_model_sha256='b'*64,recorded_dynamic_state_loaded=False,actor_weights_modified=False,initialization_only=True,main_motor_steps=0))
        self.e=dict(revision_id=common.contract()['revision_id'],contract_sha256=common.CONTRACT_SHA,new_static_MJB_sha256='b'*64,
            reference_static_MJB_sha256=common.REFERENCE_SHA,all_five_same_new_asset_required=True,
            compiled_render_only_delta_proof=dict(only_changed_array='geom_rgba',only_changed_rows=self.ids,
                engine_options_unchanged=True,topology_names_paths_unchanged=True,
                unchanged_nonRGBA_array_count=1,unchanged_nonRGBA_arrays_sha256={'EXPLICIT_SOFTWARE_ARRAY':'a'*64}))
        self.asset=dict(scene_sha256=common.SCENE_SHA256,model_sha256='b'*64,common_appearance_revision=self.e)
    def build(self,**kwargs):
        args=dict(enabled=True,components=self.components,compiled_asset=self.asset,journal=self.journal,guard=lambda:None,software_fixture=True)
        args.update(kwargs);return common.build_shared_appearance_declaration(**args)
    def obs(self,ctx,visible=False):
        objects=[] if not visible else [dict(target_ref='EXPLICIT_SOFTWARE_current_opaque',label='cuboid_a; current original RGBD one-to-one association',bbox_xyxy=[1,1,9,9],evidence_ref='EXPLICIT_SOFTWARE',geometry=dict(status='unknown',source='unavailable',values={},uncertainty={}))]
        return Observation.create(dict(time_s=1.,rgb=dict(path='/EXPLICIT_SOFTWARE_NOT_IMAGE',sha256='0'*64,time_s=1.,width=192,height=128),objects=objects,public_state={},declared_map=ctx.public_map(),goal=self.scene['task']['instruction'],events=[]))
    def test_default_OFF_no_model_or_file_IO(self):
        with patch.object(common,'contract',side_effect=AssertionError('No file read')):
            self.assertIsNone(common.build_shared_appearance_declaration())
    def test_same_map_for_five_arms_original_schema_geometry_and_domain_unchanged(self):
        ctx=self.build();new=ctx.public_map();base=public.declared_map(self.scene)
        self.assertEqual(set(new),{'source_ref','anchors'});self.assertEqual(len(new['anchors']),27)
        for old,row in zip(base['anchors'],new['anchors']):
            self.assertEqual({k:v for k,v in old.items()if k!='description'},{k:v for k,v in row.items()if k!='description'})
        digests=[]
        for arm in 'ABCDE':
            obs=self.obs(ctx);catalogue=public.intent_catalogue(self.scene,obs,sequence=1,shared_appearance=ctx)
            batch=IntentBatch('EXPLICIT_SOFTWARE_'+arm,obs,catalogue,public.capability_contract())
            self.assertEqual(len(batch.options),30);digests.append(common._sha(obs.value['declared_map']))
        self.assertEqual(len(set(digests)),1);self.assertTrue(self.rows[-1]['all_five_same_static_prior_required_not_actual_runs_attested']);self.assertFalse(self.rows[-1]['current_identity_visibility_pose_native_admission_or_WM_prediction_claimed'])
    def test_REAL_Reach_constructor_accepts_shared_markers_12_NAV_subjects_8_unknown(self):
        ctx=self.build();obj=producer.DeclaredPaletteAnchorAssociation(public_appearance=common.contract(),public_map=ctx.public_map(),
            public_effects=public.public_effects(self.scene),journal=self.journal,enabled=True,
            active_revision_id=self.e['revision_id'],selected_MJB_sha256='b'*64,selected_asset_evidence=self.e,
            software_fixture=True)
        nav=[s for (skill,ref,param),s in obj.subjects.items()if skill=='NAV']
        self.assertEqual((sum(s is not None for s in nav),sum(s is None for s in nav)),(12,8));self.assertIsNone(obj.last_evidence_ref)
    def test_original_Observation_and_catalogue_reject_arbitrary_or_unbound_map(self):
        ctx=self.build();obs=self.obs(ctx)
        with self.assertRaises(ValueError):public.intent_catalogue(self.scene,obs,sequence=1)
        with self.assertRaises(ValueError):public.intent_catalogue(self.scene,obs,sequence=1,shared_appearance={'map':ctx.public_map()})
        altered=copy.deepcopy(self.scene);altered['public_waypoints_xy_m'][0][0]+=.01
        with self.assertRaises(ValueError):public.intent_catalogue(altered,obs,sequence=1,shared_appearance=ctx)
    def test_E_does_not_treat_declared_colour_as_current_visibility_or_permission(self):
        ctx=self.build()
        for visible,expected in [(False,'NAV'),(True,'PUSH')]:
            obs=self.obs(ctx,visible);batch=IntentBatch('EXPLICIT_SOFTWARE',obs,public.intent_catalogue(self.scene,obs,sequence=1,shared_appearance=ctx),public.capability_contract())
            planner=RuleBaseline(self.scene,journal=self.journal);selection=planner.select(batch)
            self.assertEqual(next(o for o in batch.options if o.sha256==selection.option_sha256).skill,expected)
    def test_old_brown_missing_partial_wrong_receipt_or_loaded_colour_refuses(self):
        for kind in ('old','partial','receipt','colour','material'):
            with self.subTest(kind=kind):
                self.setUp()
                if kind=='old':self.asset['model_sha256']=common.REFERENCE_SHA
                elif kind=='partial':self.e['compiled_render_only_delta_proof']['unchanged_nonRGBA_array_count']=2
                elif kind=='receipt':self.components['construction']['static_model_sha256']='c'*64
                elif kind=='colour':self.components['runtime'].sim.model.geom_rgba[0]=(.55,.36,.19,1.)
                else:self.components['runtime'].sim.model.geom_matid[0]=0
                with self.assertRaises(ValueError):self.build()
                self.assertFalse(self.rows)
    def test_midstream_or_other_runtime_cannot_attach_reuse_or_switch_declarations(self):
        ctx=self.build();self.components['runtime'].step_count=1
        with self.assertRaises(ValueError):self.build()
        # Existing static declaration remains bound during actual future motion,
        # but cannot be attached as a new episode/map half way through it.
        ctx.verify_bound_components(self.components)
        wrong=dict(self.components,runtime=copy.deepcopy(self.components['runtime']))
        with self.assertRaises(ValueError):ctx.verify_bound_components(wrong)
    def test_fixture_cannot_be_promoted_or_enter_live_driver_before_native_import(self):
        ctx=self.build()
        with self.assertRaises(ValueError):ctx.software_fixture=False
        with self.assertRaises(ValueError):common.require_live_declaration(ctx)
        with self.assertRaises(ValueError):self.build(software_fixture=False)
        cls=live_driver.driver_class(source_root=SOURCE,enabled=True)
        with self.assertRaises(ValueError):cls(self.components,bundle='EXPLICIT',output_root='EXPLICIT',writer=None,planner=None,journal=self.journal,guard=lambda:None,arm='A',shared_appearance=ctx)
        self.assertFalse(blocked)
    def test_driver_default_map_unchanged_and_explicit_fixture_map_never_live(self):
        cls=live_driver.driver_class(source_root=SOURCE,enabled=True);host=cls.__new__(cls);host.scene=self.scene
        self.assertEqual(host.declared_public_map(),public.declared_map(self.scene))
        host.shared_appearance=self.build();host.components=self.components
        with self.assertRaises(ValueError):host.declared_public_map()
    def test_public_map_copy_and_unknown_asset_metadata_do_not_escape(self):
        self.e['UNTRUSTED_EXTRA_DO_NOT_HASH_OR_COPY']='EXPLICIT_SOFTWARE_extra'
        ctx=self.build();value=ctx.public_map();value['anchors'][0]['description']='changed_copy'
        self.assertNotEqual(ctx.public_map()['anchors'][0]['description'],'changed_copy')
        self.assertNotIn('EXPLICIT_SOFTWARE_extra',json.dumps(self.rows));self.assertNotIn('UNTRUSTED_EXTRA_DO_NOT_HASH_OR_COPY',ctx._evidence_json)
    def test_guard_or_non_durable_journal_refusal_cannot_return_context(self):
        with self.assertRaises(ValueError):self.build(guard=lambda:False)
        with self.assertRaises(ValueError):self.build(journal=lambda row:None)
    def test_source_ref_and_subject_map_are_pinned_no_dynamic_goal_or_hidden_pose(self):
        ctx=self.build();encoded=json.dumps(ctx.public_map())
        self.assertNotIn('body_name',encoded);self.assertNotIn('foot_normal',encoded);self.assertNotIn('live_pose',encoded)
        self.assertEqual(sum('WM_CONDITIONING_SUBJECT='in a['description']for a in ctx.public_map()['anchors']),12)
        with patch.object(common,'MAP_SHA','0'*64):
            with self.assertRaises(ValueError):self.build()

if __name__=='__main__':
    r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
    print(json.dumps(dict(role='COMMON_PUBLIC_DECLARATION_METADATA_AND_ACTUAL_REACH_CONSTRUCTOR_FIXTURES_NOT_LIVE_OR_WM_NATIVE',checks=r.testsRun,failures=len(r.failures),errors=len(r.errors),forbidden_attempts=blocked,real_MJB_reads_Model_Runtime_renderer_Role_WM_Actor_API_or_physics_calls=0)))
    sys.exit(0 if r.wasSuccessful()and not blocked else 1)
