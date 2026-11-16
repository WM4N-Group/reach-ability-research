"""New actual original-IntentBatch public seam fixtures; no native/API/WM."""
from pathlib import Path
import sys,json,unittest
OWN=Path(__file__).resolve().parents[1];ROOT=OWN.parents[1];SOURCE=ROOT/'consumer-deliveries/AINAV-CLIMB-PREPARATION-CANDIDATES-20261113-v1/common-source';sys.path[:0]=[str(OWN),str(SOURCE)];blocked=[]
def fence(event,args):
 if event=='import'and str(args[0]).split('.')[0]in('numpy','torch','mujoco','onnxruntime'):blocked.append(str(args[0]));raise RuntimeError('Software only')
 if event in('socket.connect','socket.bind','socket.getaddrinfo','subprocess.Popen'):blocked.append(event);raise RuntimeError('No network/child')
sys.addaudithook(fence)
from public_candidates import *
from v4_native_asset import load_scene
from ainav.contracts import Observation
from ainav.intents import IntentBatch
from rule_baseline import RuleBaseline
class Tests(unittest.TestCase):
 def setUp(self):self.scene=load_scene()
 def observation(self,visible=()):
  objects=[dict(target_ref='SOFTWARE-opaque-'+r,label=r+'; current original RGBD one-to-one association',bbox_xyxy=[1,1,10,10],evidence_ref='SOFTWARE-only',geometry=dict(status='unknown',source='unavailable',values={},uncertainty={}))for r in visible]
  return Observation.create(dict(time_s=1.,rgb=dict(path='/SOFTWARE-only',sha256='0'*64,time_s=1.,width=192,height=128),objects=objects,public_state={},declared_map=declared_map(self.scene),goal=self.scene['task']['instruction'],events=[]))
 def batch(self,visible=()):
  o=self.observation(visible);return IntentBatch('SOFTWARE-only',o,intent_catalogue(self.scene,o,sequence=1),capability_contract())
 def test_exact_original_IntentBatch_targets_and_semantic_options(self):
  b=self.batch();self.assertIs(type(b),IntentBatch);self.assertEqual({o.skill for o in b.options},{'NAV','PUSH','CLIMB'});self.assertLessEqual(len(b.options),128)
 def test_elevated_terminal_is_never_a_ground_goal_or_NAV_under_deck(self):
  b=self.scene['platforms'][0]['bounds_xy_m'];rows=declarations(self.scene)
  for r in rows:
   if r['skill']=='NAV'and r['parameters']['surface_height_m']==0.:
    p=r['parameters'];self.assertFalse(b[0]<=p['goal_world_x_m']<=b[1]and b[2]<=p['goal_world_y_m']<=b[3])
  goal=next(r for r in rows if r['target_ref']=='v4-goal-elevated');self.assertEqual(goal['parameters']['surface_height_m'],.6)
 def test_all_PUSHas_ground_immutable_declared_goals_not_011m_added(self):
  rows=[r for r in declarations(self.scene)if r['skill']=='PUSH'];self.assertEqual(len(rows),6)
  for r in rows:
   obj=next(o for o in self.scene['objects']if o['public_ref']==r['target_ref']);self.assertIn(r['parameters']['goal_world_x_m'],obj['allowed_placement_x_m']);self.assertEqual(r['parameters']['surface_height_m'],0.)
 def test_CLIMB_destination_semantics_not_fake_current_source_or_mapping(self):
  rows=[r for r in declarations(self.scene)if r['skill']=='CLIMB'];self.assertEqual(len(rows),4);self.assertTrue(all(set(r['parameters'])=={'surface_height_m'}for r in rows));e=next(e for e in public_effects(self.scene)['effects']if e['skill']=='CLIMB'and e['target_ref']=='goal_deck');self.assertEqual(e['destination_height_m'],.6);self.assertEqual(e['source_height_m'],'CURRENT_VERIFIED_SUPPORT_REQUIRED');self.assertFalse(e['complete_transition_qualified'])
 def test_actual_E_selects_same_catalogue_visible_goal_and_unknown_approach(self):
  b=self.batch(['cuboid_a']);p=RuleBaseline(self.scene,journal=lambda row:'SOFTWARE');s=p.select(b);o=next(o for o in b.options if o.sha256==s.option_sha256);self.assertEqual((o.skill,o.target_ref),('PUSH','cuboid_a'));self.assertEqual(dict(o.parameters)['goal_world_x_m'],2.6)
  b=self.batch();p=RuleBaseline(self.scene,journal=lambda row:'SOFTWARE');s=p.select(b);o=next(o for o in b.options if o.sha256==s.option_sha256);self.assertEqual(o.skill,'NAV');self.assertAlmostEqual(dict(o.parameters)['goal_world_x_m'],.22)
 def test_effect_export_has_no_private_state_or_cost_or_padded_WM_features(self):
  d=public_effects(self.scene);text=json.dumps(d);self.assertNotIn('body_name',text);self.assertNotIn('private_terminal_acceptance',text);self.assertNotIn('review_climb_geometry',text);self.assertFalse(d['source_native_qualified']);self.assertTrue(all(e['complete_successor_cost_s']is None and e['actual_exit_pose']is None and e['success_probability']is None for e in d['effects']))
 def test_stable_same_order_and_no_method_exclusive_catalogue(self):
  self.assertEqual(declarations(self.scene),declarations(self.scene));self.assertNotIn('method',declarations(self.scene)[0]);self.assertEqual(len({o.sha256 for o in self.batch().options}),len(self.batch().options))
if __name__=='__main__':
 r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests));print(json.dumps(dict(role='V4_SHARED_PUBLIC_CATALOGUE_ACTUAL_CONTRACT_SOFTWARE_NOT_NATIVE',checks=r.testsRun,failures=len(r.failures),errors=len(r.errors),forbidden_attempts=blocked,worlds_API_WM_or_fits=0)));sys.exit(0 if r.wasSuccessful()and not blocked else 1)
