"""Public/private source contract fixtures only, no native robot or mock success."""
from pathlib import Path
import json,sys,unittest
ROOT=Path(__file__).resolve().parents[3];SOURCE=ROOT/'consumer-deliveries/AINAV-CLIMB-PREPARATION-CANDIDATES-20261113-v1/common-source'
sys.path[:0]=[str(Path(__file__).resolve().parents[1]),str(SOURCE)]
blocked=[]
def fence(event,args):
    if event=='import'and str(args[0]).split('.')[0]in('numpy','torch','mujoco','onnxruntime'):blocked.append(str(args[0]));raise RuntimeError('Source fixture only')
    if event in('socket.connect','socket.bind','socket.getaddrinfo','subprocess.Popen'):blocked.append(event);raise RuntimeError('No network/child')
sys.addaudithook(fence)
import complex_scene as s
from scene_driver import nav_declarations
from semantic_factory import private_entry_observation,factory_class
from ainav.contracts import Observation,canonical
from ainav.intents import ExecutionBatch
from ainav.native.behavior_authority import BehaviorOption
class SemanticSourceTests(unittest.TestCase):
    def test_v2_independent_asset_has_three_required_light_reconstructions(self):
        v=s.load_scene(Path(s.SCENE).with_name('scene_v2_three_choices.json'));self.assertEqual(len(v['objects']),3);self.assertEqual(v['task']['minimum_distinct_reconstructions'],3);self.assertEqual(len(s.finite_placements(v)),6)
        r=s.registry(v,source_root=SOURCE);self.assertEqual(len(r.objects),3)
        nav=nav_declarations(v);self.assertEqual(len(nav),len({n['xy']for n in nav}));self.assertEqual(sum(n['target_ref']=='cx-goal'for n in nav),1)
        self.assertLess(len(nav)+6,128)
        self.assertEqual(len(s.load_scene()['objects']),2) # v1 preserved, not overwritten.
        from terminal_stop import FinalSupportedStop
        from types import SimpleNamespace
        stop=FinalSupportedStop.__new__(FinalSupportedStop);stop.complete=True;stop.r=SimpleNamespace(sim=SimpleNamespace(data=SimpleNamespace(time=.5)))
        stop.placements=SimpleNamespace(records={o['public_ref']:object()for o in v['objects']},scene=v)
        self.assertEqual(stop.results[0]['original_placement_count'],3);self.assertEqual(stop.results[0]['required_reconstructions'],3);self.assertNotIn('two_original_placements',stop.results[0])
    def test_same_acquisition_private_entry_reference_never_changes_public_sensor(self):
        obs=Observation.create(dict(time_s=0.,rgb=dict(path='/SOFTWARE-NOT-EXPERIMENT/rgb.png',sha256='0'*64,time_s=0.,width=8,height=8),objects=[],public_state={},declared_map=dict(source_ref='SOFTWARE-only',anchors=[dict(target_ref='cuboid_a',description='declared INITIAL task reference only',position_xyz_m=[1.7,0.,0.],uncertainty_xyz_m=[0.,0.,0.])]),goal='SOFTWARE-only',events=[]))
        raw=obs.encoded;o=BehaviorOption('source','NAV','cuboid_a',tuple(sorted(dict(goal_world_x_m=-.08,goal_world_y_m=.006,surface_height_m=0.).items())),60.,'SOFTWARE-only')
        private=private_entry_observation(obs,o);self.assertEqual(obs.encoded,raw);self.assertEqual(private.value['rgb'],obs.value['rgb']);self.assertEqual(private.value['public_state'],obs.value['public_state']);self.assertEqual(private.time_s,obs.time_s)
        self.assertNotEqual(private.sha256,obs.sha256)
        batch=ExecutionBatch('SOFTWARE-private',private,(o,),canonical(dict(source_ref='SOFTWARE-only',skills=['NAV'],constraints=['Software fixture, not real sensor/entry.'])))
        with self.assertRaises(ValueError):batch.public()
    def test_semantic_factory_default_off_does_not_touch_source(self):
        self.assertIsNone(factory_class());cls=factory_class(source_root=SOURCE,enabled=True);self.assertTrue(callable(cls.prepare_public_push));self.assertTrue(callable(cls.bind_batch))
if __name__=='__main__':
    r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(SemanticSourceTests));print(json.dumps(dict(role='SOURCE_SOFTWARE_ONLY_NOT_NATIVE_OR_RESEARCH_SAMPLES',checks=r.testsRun,failures=len(r.failures),errors=len(r.errors),forbidden_attempts=blocked,actual_native_or_fit=0)));sys.exit(0 if r.wasSuccessful()and not blocked else 1)
