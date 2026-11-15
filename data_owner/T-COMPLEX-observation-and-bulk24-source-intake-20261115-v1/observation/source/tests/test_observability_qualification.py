"""SOFTWARE contract fixtures only, not physical NAV/views/binding qualification."""
from pathlib import Path
from types import SimpleNamespace
import sys,json,unittest
ROOT=Path(__file__).resolve().parents[3];OWN=Path(__file__).resolve().parents[1];SOURCE=ROOT/'consumer-deliveries/AINAV-CLIMB-PREPARATION-CANDIDATES-20261113-v1/common-source';sys.path[:0]=[str(OWN),str(SOURCE)]
blocked=[]
def fence(e,a):
 if e=='import'and str(a[0]).split('.')[0]in('numpy','torch','mujoco','onnxruntime'):blocked.append(str(a[0]));raise RuntimeError('Software only')
 if e in('socket.connect','socket.bind','socket.getaddrinfo','subprocess.Popen'):blocked.append(e);raise RuntimeError('No network/child')
sys.addaudithook(fence)
from complex_scene import load_scene,public_task
from scene_driver import ComplexSceneDriver,nav_declarations
from observability_qualification import *
from ainav.contracts import Observation,canonical
from ainav.intents import IntentBatch
from ainav.native.behavior_authority import BehaviorOption,NativeReceipt

class QualificationTests(unittest.TestCase):
 def setUp(self):
  self.scene=load_scene(OWN/'scene_v2_three_choices.json');self.logs=[];self.p=ObservabilityQualificationPlanner(public_task(self.scene),journal=lambda row:self.logs.append(row)or'SOFTWARE-fixture:not-real-evidence')
 def obs(self,t,visible=False):
  return Observation.create(dict(time_s=t,rgb=dict(path='/SOFTWARE-only/rgb.png',sha256='0'*64,time_s=t,width=192,height=128),objects=[dict(target_ref='SOFTWARE-opaque',label='cuboid_a; current original RGBD one-to-one association',bbox_xyxy=[1,1,10,10],evidence_ref='SOFTWARE-only',geometry=dict(status='unknown',source='unavailable',values={},uncertainty={}))]if visible else [],public_state={},declared_map=dict(source_ref='SOFTWARE-only',anchors=[dict(target_ref=v['target_ref'],description='SOFTWARE declared NAV reference',position_xyz_m=[*v['xy'],0.],uncertainty_xyz_m=[0.,0.,0.])for v in self.p.viewpoints]),goal='SOFTWARE observation qualification, no task',events=[]))
 def driver(self,purpose=QUALIFICATION_PURPOSE):
  d=ComplexSceneDriver.__new__(ComplexSceneDriver);d.purpose=purpose;d.scene=self.scene;d.planner=self.p;d.nav_by_ref={v['target_ref']:v['xy']for v in nav_declarations(self.scene)};d.journal=lambda row:'SOFTWARE-only';d.sequence=1;d.current_observation=self.obs(0.)
  if purpose==QUALIFICATION_PURPOSE:
   d.nav_by_ref.update({v['target_ref']:v['xy']for v in self.p.viewpoints})
  return d
 def step(self,t):
  d=self.driver();d.current_observation=self.obs(t);options=d.intent_catalogue(d.current_observation);batch=IntentBatch('SOFTWARE-%d'%self.p.stage,d.current_observation,options,canonical(dict(source_ref='SOFTWARE-only',skills=['NAV'],constraints=['Explicit software fixture'])));selection=self.p.select(batch);intent=next(o for o in options if o.sha256==selection.option_sha256);opt=BehaviorOption('SOFTWARE-execution','NAV',intent.target_ref,intent.parameters,60.,'SOFTWARE-only');receipt=NativeReceipt(opt.sha256,t+.5,'succeeded','f'*64,'SOFTWARE-only');return intent,opt,receipt
 def test_purpose_is_explicit_and_never_disguises_qualification_as_greedy(self):
  validate_planner_purpose(SimpleNamespace(method='greedy'),COMPARISON_PURPOSE);validate_planner_purpose(self.p,QUALIFICATION_PURPOSE)
  for planner,purpose in [(self.p,COMPARISON_PURPOSE),(SimpleNamespace(method=METHOD),QUALIFICATION_PURPOSE),(self.p,'fallback')]:
   with self.assertRaises(ValueError):validate_planner_purpose(planner,purpose)
  self.assertEqual(self.p.decision_source,SOURCE);self.assertFalse(self.p.complete)
 def test_only_two_original_finite_NAVs_no_PUSH_and_original_comparison_catalogue_unchanged(self):
  d=self.driver();opts=d.intent_catalogue(d.current_observation);self.assertEqual([o.target_ref for o in opts],['cx-observe-left','cx-observe-right']);self.assertEqual([dict(o.parameters)['goal_world_y_m']for o in opts],[.15,-.15]);self.assertEqual({o.skill for o in opts},{'NAV'})
  d=self.driver(COMPARISON_PURPOSE);opts=d.intent_catalogue(d.current_observation);self.assertEqual(sum(o.skill=='PUSH'for o in opts),6);self.assertEqual(sum(o.skill=='NAV'for o in opts),len(nav_declarations(self.scene)));self.assertFalse(any(o.target_ref.startswith('cx-observe')for o in opts))
 def test_exact_scripted_measurement_order_never_certifies_task_or_three_choices(self):
  intent,opt,receipt=self.step(0.);self.assertEqual(intent.target_ref,'cx-observe-left');self.p.observe_intent(intent,opt,receipt,'SOFTWARE-only')
  intent,opt,receipt=self.step(1.);self.assertEqual(intent.target_ref,'cx-observe-right');self.p.observe_intent(intent,opt,receipt,'SOFTWARE-only');self.assertTrue(self.p.motion_complete);self.assertFalse(self.p.complete or self.p.qualification_complete)
  self.assertEqual(len(self.p.records),2);self.assertFalse(any(r['target_visible_under_original_binding']for r in self.p.records))
 def test_failure_cannot_be_retried_or_upgraded_with_another_receipt(self):
  intent,opt,receipt=self.step(0.);failed=NativeReceipt(opt.sha256,.5,'failed','f'*64,'SOFTWARE-only')
  with self.assertRaises(RuntimeError):self.p.observe_intent(intent,opt,failed,'SOFTWARE-only')
  with self.assertRaises(ValueError):self.p.observe_intent(intent,opt,receipt,'SOFTWARE-only')
  with self.assertRaises(ValueError):self.step(1.)
 def test_final_fresh_public_view_and_same_actual_owner_are_required(self):
  with self.assertRaises(ValueError):self.p.finish_from_driver(self.driver())
  for t in [0.,1.]:
   intent,opt,receipt=self.step(t);self.p.observe_intent(intent,opt,receipt,'SOFTWARE-only')
  d=self.driver();d.executor=SimpleNamespace(reported_end=True,last_outcome='succeeded');d.r=SimpleNamespace(sim=SimpleNamespace(data=SimpleNamespace(time=2.)));d.factory=SimpleNamespace(_current_completed_witness=lambda:SimpleNamespace(validate=lambda runtime:None));d._native_guards=lambda:None;d._contact_guard=lambda:None;d._snapshot=lambda runtime:('SOFTWARE-no-world',);d.observe_public=lambda now:self.obs(now);d.complete=False
  result=self.p.finish_from_driver(d);self.assertTrue(result['qualification_complete']);self.assertFalse(result['original_task_success']or result['AB_comparison']or result['visible_in_any_fixed_view']or d.complete or self.p.complete);self.assertEqual(result['fresh_observation_boundaries'],3);self.assertEqual(result['actual_original_NAV_receipts'],2)
  with self.assertRaises(ValueError):self.p.finish_from_driver(d)
 def test_repeated_observation_is_not_a_new_sensor_or_selected_best_frame(self):
  self.p._record(self.obs(1.),'SOFTWARE-only')
  with self.assertRaises(ValueError):self.p._record(self.obs(1.),'SOFTWARE-only')
if __name__=='__main__':
 r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(QualificationTests));print(json.dumps(dict(role='SOFTWARE_QUALIFICATION_CONTRACTS_NOT_PHYSICAL_OR_RESEARCH_SAMPLES',checks=r.testsRun,failures=len(r.failures),errors=len(r.errors),forbidden_attempts=blocked,actual_worlds_NAV_or_fits=0)));sys.exit(0 if r.wasSuccessful()and not blocked else 1)
