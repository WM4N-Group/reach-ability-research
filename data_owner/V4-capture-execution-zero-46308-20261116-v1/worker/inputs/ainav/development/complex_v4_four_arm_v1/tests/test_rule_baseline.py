"""E software contracts only; synthetic receipts are not physical evidence."""
from pathlib import Path
import sys,json,unittest
OWN=Path(__file__).resolve().parents[1];ROOT=OWN.parents[1];SOURCE=ROOT/'consumer-deliveries/AINAV-CLIMB-PREPARATION-CANDIDATES-20261113-v1/common-source';sys.path[:0]=[str(OWN),str(SOURCE)]
blocked=[]
def fence(event,args):
 if event=='import'and str(args[0]).split('.')[0]in('numpy','torch','mujoco','onnxruntime'):blocked.append(str(args[0]));raise RuntimeError('Software only')
 if event in('socket.connect','socket.bind','socket.getaddrinfo','subprocess.Popen'):blocked.append(event);raise RuntimeError('No network/child')
sys.addaudithook(fence)
from v4_native_asset import load_scene
from rule_baseline import RuleBaseline
from ainav.contracts import Observation,canonical
from ainav.intents import IntentBatch,SkillIntent
from ainav.native.behavior_authority import BehaviorOption,NativeReceipt
class Tests(unittest.TestCase):
 def setUp(self):self.scene=load_scene();self.logs=[];self.p=RuleBaseline(self.scene,journal=lambda row:self.logs.append(row)or'SOFTWARE-only')
 def batch(self,t,visible=()):
  options=[];anchors=[]
  def add(skill,ref,params,xyz):options.append(SkillIntent('SOFTWARE-%d'%len(options),skill,ref,tuple(sorted(params.items()))));anchors.append(dict(target_ref=ref,description='SOFTWARE public declaration',position_xyz_m=xyz,uncertainty_xyz_m=[0.,0.,0.]))
  for o in self.scene['objects']:
   x,y=o['initial_xy_m'];a=x-o['size_m'][0]/2-.58
   add('NAV',o['public_ref']+':approach',dict(goal_world_x_m=a,goal_world_y_m=y,surface_height_m=0.),[a,y,0.])
   x,y=o['required_goal_xy_m'];add('PUSH',o['public_ref'],dict(goal_world_x_m=x,goal_world_y_m=y,surface_height_m=0.),[x,y,0.])
   add('CLIMB',o['public_ref']+':upper-entry',dict(surface_height_m=.2),[x,y,.2])
  add('CLIMB','goal_deck',dict(surface_height_m=.6),[14.1,-2.6,.6]);add('NAV','goal-elevated',dict(goal_world_x_m=14.1,goal_world_y_m=-2.6,surface_height_m=.6),[14.1,-2.6,.6])
  objects=[dict(target_ref='SOFTWARE-opaque-'+r,label=r+'; current original RGBD one-to-one association',bbox_xyxy=[1,1,10,10],evidence_ref='SOFTWARE-only',geometry=dict(status='unknown',source='unavailable',values={},uncertainty={}))for r in visible]
  obs=Observation.create(dict(time_s=t,rgb=dict(path='/SOFTWARE-only',sha256='0'*64,time_s=t,width=192,height=128),objects=objects,public_state={},declared_map=dict(source_ref='SOFTWARE-only',anchors=anchors),goal='SOFTWARE no mission evidence',events=[]))
  return IntentBatch('SOFTWARE-'+str(t),obs,tuple(options),canonical(dict(source_ref='SOFTWARE',skills=['NAV','PUSH','CLIMB'],constraints=['Software only no physical permission'])))
 def choose(self,batch):
  s=self.p.select(batch);return next(o for o in batch.options if o.sha256==s.option_sha256)
 def receipt(self,intent,t,status='succeeded'):
  option=BehaviorOption('SOFTWARE-native',intent.skill,intent.target_ref,intent.parameters,60.,'SOFTWARE-only',attempt_id='SOFTWARE-only'if intent.skill=='PUSH'else'',original_push_goal_sha256='e'*64 if intent.skill=='PUSH'else'');receipt=NativeReceipt(option.sha256,t,status,'f'*64,'SOFTWARE-only');self.p.observe_intent(intent,option,receipt,'SOFTWARE-only')
 def test_original_public_push_and_only_actual_receipt_advances_fixed_order(self):
  intent=self.choose(self.batch(1.,['cuboid_a']));self.assertEqual((intent.skill,intent.target_ref),('PUSH','cuboid_a'));self.assertFalse(self.p.placed)
  self.receipt(intent,1.5);self.assertEqual(self.p.placed,{'cuboid_a'});next_intent=self.choose(self.batch(2.,['cuboid_b']));self.assertEqual(next_intent.target_ref,'cuboid_b');self.assertFalse(self.p.complete);self.assertEqual(self.logs[0]['VLM_calls'],0);self.assertEqual(self.logs[0]['WM_calls'],0)
 def test_unknown_association_one_declared_NAV_then_no_scan_or_cached_alias(self):
  intent=self.choose(self.batch(1.));self.assertEqual(intent.skill,'NAV');self.receipt(intent,1.5)
  with self.assertRaisesRegex(RuntimeError,'association_still_unknown'):self.p.select(self.batch(2.))
  with self.assertRaises(ValueError):self.p.select(self.batch(3.,['cuboid_a']))
 def test_native_failure_does_not_count_as_placement_or_retry(self):
  intent=self.choose(self.batch(1.,['cuboid_a']))
  with self.assertRaises(RuntimeError):self.receipt(intent,1.5,'failed')
  self.assertFalse(self.p.placed)
  with self.assertRaises(ValueError):self.p.select(self.batch(2.,['cuboid_a']))
 def test_climb_choice_uses_public_one_hop_distance_not_a_letter_route(self):
  self.p.placed={o['public_ref']for o in self.scene['objects']} # Explicit SOFTWARE state, not actual placement evidence.
  intent=self.choose(self.batch(1.));self.assertEqual(intent.skill,'CLIMB');self.assertEqual(intent.target_ref,'cuboid_c:upper-entry');self.receipt(intent,1.5);self.assertEqual(self.p.support_height,.2)
  with self.assertRaisesRegex(RuntimeError,'original20cm'):self.p.select(self.batch(2.))
  self.assertFalse(self.p.complete)
 def test_empty_terminal_proof_can_never_self_certify_full_V4(self):
  with self.assertRaises(RuntimeError):self.p.confirm_original_task_terminal(evidence_ref='SOFTWARE fake proof')
  self.assertFalse(self.p.complete)
 def test_duplicate_pending_query_and_cap_exhaustion_refuse_no_fallback(self):
  b=self.batch(1.,['cuboid_a']);self.choose(b)
  with self.assertRaises(ValueError):self.p.select(b)
  self.p=RuleBaseline(self.scene,journal=lambda row:'SOFTWARE-only',max_selections=1);i=self.choose(self.batch(2.,['cuboid_a']));self.receipt(i,2.5)
  with self.assertRaises(ValueError):self.p.select(self.batch(3.,['cuboid_b']))
if __name__=='__main__':
 r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests));print(json.dumps(dict(role='V4_E_SOFTWARE_RULES_NOT_NATIVE_OR_METHOD_RESULTS',checks=r.testsRun,failures=len(r.failures),errors=len(r.errors),forbidden_attempts=blocked,worlds=0,API_or_WM=0)));sys.exit(0 if r.wasSuccessful()and not blocked else 1)
