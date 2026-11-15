"""Software seam fixtures; no actual MjSpec, camera, RGBD, gate, or episode."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import sys,unittest,json,hashlib,argparse
args=argparse.ArgumentParser();args.add_argument('--reach-root',type=Path,required=True);ARGS=args.parse_args()
ROOT=Path(__file__).resolve().parents[3];OWN=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'consumer-deliveries/AINAV-CLIMB-PREPARATION-CANDIDATES-20261113-v1/common-source'
sys.path[:0]=[str(OWN),str(SOURCE)]
blocked=[]
def fence(event,args):
    if event=='import' and str(args[0]).split('.')[0]in('numpy','torch','mujoco','onnxruntime'):
        blocked.append(str(args[0]));raise RuntimeError('No numerical/native modules in software fixtures')
    if event in('socket.connect','socket.bind','socket.getaddrinfo','subprocess.Popen'):
        blocked.append(event);raise RuntimeError('No network/child')
sys.addaudithook(fence)
import camera_abi as camera
import complex_scene as scene
import public_planner_binding as binding

class SeamTests(unittest.TestCase):
    def test_original_camera_pins_are_actual_published_sources(self):
        for name,pin in [('scene',camera.SCENE_SHA),('observer',camera.OBSERVER_SHA)]:
            self.assertEqual(hashlib.sha256((SOURCE/'mujoco_zyh'/(name+'.py')).read_bytes()).hexdigest(),pin)
    def test_hot_fifo_or_preexisting_camera_reject_before_loading_native_hook(self):
        for time,queue,ncam in [(.005,[],0),(0.,[object()],0),(0.,[],1)]:
            sim=SimpleNamespace(data=SimpleNamespace(time=time),queue=queue,model=SimpleNamespace(ncam=ncam))
            with patch.object(camera,'original_camera_source',side_effect=AssertionError('must refuse first')):
                with self.assertRaises(ValueError):camera.install_original_camera(sim,source_root=SOURCE)
    def test_forward_exact_original_camera_only_hook_not_a_new_mount_recipe(self):
        sim=SimpleNamespace(data=SimpleNamespace(time=0.),queue=[],model=SimpleNamespace(ncam=0),spec=object())
        calls=[]
        def hook(holder,actual,spec,config):
            self.assertIs(actual,sim);self.assertIs(spec,sim.spec);calls.append(config)
            holder.wm_scene_receipt=dict(camera=dict(name='wm_onboard_rgbd',width=192,height=128))
            return 0,holder.box_y
        with patch.object(camera,'original_camera_source',return_value=SimpleNamespace(configure_scene=hook)):
            receipt=camera.install_original_camera(sim,source_root=SOURCE)
        self.assertEqual(calls,[dict(width=192,height=128,scene_recipe='zyh_native_single_box')])
        self.assertTrue(receipt['transient_hook_scene_identity_not_used'])
    def test_original_hook_that_changes_clock_is_rejected(self):
        sim=SimpleNamespace(data=SimpleNamespace(time=0.),queue=[],model=SimpleNamespace(ncam=0),spec=object())
        def hook(*args):sim.data.time=.005;return 0,0.
        with patch.object(camera,'original_camera_source',return_value=SimpleNamespace(configure_scene=hook)):
            with self.assertRaises(ValueError):camera.install_original_camera(sim,source_root=SOURCE)
    def _planner(self,**kwargs):
        s=scene.load_scene(OWN/'scene_v2_three_choices.json')
        hashes=json.loads((OWN/'REACH_METHOD_SOURCE_BINDING.json').read_bytes())['files_sha256']
        return binding.make_public_planner(s,reach_source_root=ARGS.reach_root,expected_module_hashes=hashes,
            method='greedy',journal=lambda event:None,**kwargs)
    def test_wrapper_uses_actual_source_bound_fourth_module_and_public_assets(self):
        planner=self._planner()
        self.assertEqual(type(planner).__name__,'SourceBoundComplexIntentPlanner')
        self.assertTrue(callable(planner._validate_catalogue))
        self.assertEqual(planner.source_pins['public_task']['sha256'],json.loads((OWN/'SOURCE_SELECTION_V2.json').read_bytes())['public_task_sha256'])
    def test_direct_three_module_bypass_and_ceiling_change_are_rejected(self):
        s=scene.load_scene(OWN/'scene_v2_three_choices.json')
        with self.assertRaises(ValueError):binding.make_public_planner(s,reach_source_root=ARGS.reach_root,expected_module_hashes={},method='greedy',journal=lambda e:None)
        with self.assertRaises(ValueError):self._planner(limits=dict(max_depth=9,max_transitions=256,max_wall_s=.25))
    def test_v1_or_mismatched_public_projection_is_not_silently_accepted(self):
        s=scene.load_scene();hashes=json.loads((OWN/'REACH_METHOD_SOURCE_BINDING.json').read_bytes())['files_sha256']
        with self.assertRaises(ValueError):binding.make_public_planner(s,reach_source_root=ARGS.reach_root,expected_module_hashes=hashes,method='greedy',journal=lambda e:None)
        with self.assertRaises(ValueError):self._planner(public_task_path=OWN/'PUBLIC_TASK.json')
if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(SeamTests))
    print(json.dumps(dict(role='SOFTWARE_SEAMS_NOT_NATIVE_QUALIFICATION_OR_RESEARCH_SAMPLES',checks=result.testsRun,failures=len(result.failures),errors=len(result.errors),forbidden_attempts=blocked,worlds=0,fit=0)))
    sys.exit(0 if result.wasSuccessful()and not blocked else 1)
