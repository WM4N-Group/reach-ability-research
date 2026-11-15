"""ONLY synthetic NPZ/RGB CPU fixtures, never a method/task/physical trial."""
from pathlib import Path
import hashlib, json, os, tempfile, unittest
import numpy as np
from encode_five_arm_originals import Original, ARMS, FIXTURE, canonical, encode, panel, read, same_capture, sha

def write(path, value):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,indent=2)+'\n')

def fixture(base, arm, *, tick=40, width=960, height=540, passed=True, task=None):
    root=base/arm;raw=root/'main/raw-third-view';(raw/'raw-rgb').mkdir(parents=True)
    scope='SOFTWARE-FIXTURE-NOT-PHYSICS-'+arm;program=hashlib.sha256(scope.encode()).hexdigest()
    v=dict(phase='main',scope_id=scope,program_sha256=program,provenance=FIXTURE,PID=99999999,
           passed=passed,task_success=task,actual_main_world_sim_s=tick*.005)
    write(root/'main/result.json',v);write(root/'accounting/ledger.json',dict(provenance=FIXTURE,scope_id=scope,program_sha256=program,rows=[dict(phase='main',closed=True,report_sha256=sha(root/'main/result.json'))]))
    camera=dict(kind='fixed_free',width=width,height=height,stride_physics_ticks=20,chunk_frames=10,max_bytes=1024**3,lookat=[6.5,0.,.3],distance=18.,azimuth=90.,elevation=-55.)
    camera_sha=hashlib.sha256(canonical(camera)).hexdigest()
    meta=dict(scope_id=scope,program_sha256=program,origin='DIRECT_CURRENT_LIVE_MUJOCO_RGB',camera_spec=camera,camera_spec_sha256=camera_sha)
    write(raw/'metadata.json',meta);ticks=np.arange(tick//20+1,dtype=np.int64)*20
    rgb=np.zeros((len(ticks),height,width,3),dtype=np.uint8);rgb[:,:,:]=dict(A=[180,0,0],B=[0,180,0],C=[0,0,180],D=[160,100,0],E=[70,90,110])[arm]
    np.savez_compressed(raw/'raw-rgb/000000.npz',rgb=rgb,physics_tick=ticks,actual_sim_time_s=ticks*.005)
    row=dict(path='raw-rgb/000000.npz',sha256=sha(raw/'raw-rgb/000000.npz'),frames=len(ticks),first_physics_tick=int(ticks[0]),last_physics_tick=int(ticks[-1]),raw_RGB_bytes_sha256=hashlib.sha256(rgb.tobytes()).hexdigest())
    cl=dict(scope_id=scope,program_sha256=program,origin='DIRECT_CURRENT_LIVE_MUJOCO_RGB',metadata_sha256=sha(raw/'metadata.json'),camera_spec_sha256=camera_sha,
            final_physics_tick=tick,actual_run_end_time_s=tick*.005,complete_for_capture_grid=True,archived_frames=len(ticks),captured_frames=len(ticks),state_replay_or_rerender_used=False,sampling_or_interpolation_of_missing_frames=False,chunks=[row])
    write(raw/'closure.json',cl);return root

class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='Data-CPU-only-five-panel-fixture-');self.base=Path(self.tmp.name)
    def tearDown(self):self.tmp.cleanup()
    def sources(self):
        ticks=[40,20,10,40,20]
        return {a:Original(a,fixture(self.base,a,tick=ticks[i],passed=a!='B',task=None if a=='C'else False),fixture=True)for i,a in enumerate(ARMS)}
    def test_same_clock_and_unknown_vs_failure_preserved(self):
        s=self.sources();same_capture(s);self.assertEqual([s[a].count for a in ARMS],[3,2,1,3,2]);self.assertFalse(s['B'].evidence()['original_phase_passed']);self.assertIsNone(s['C'].evidence()['original_task_success']);self.assertEqual(s['C'].end_s,.05)
    def test_panel_preserves_RGB_and_post_end_black_not_last_frame(self):
        s=self.sources();frame=next(s['C'].frames());im=np.asarray(panel(s['C'],frame,0,fixture=True));self.assertTrue(np.array_equal(im[96:],frame));slate=np.asarray(panel(s['C'],None,1,fixture=True));self.assertFalse(slate[96:].any())
        with self.assertRaises(ValueError):panel(s['A'],None,1,fixture=True)
    def test_duplicate_root_cannot_be_five_arms(self):
        s=self.sources();s['D']=s['A']
        with self.assertRaises(ValueError):same_capture(s)
    def test_camera_mismatch_rejected_no_upscale(self):
        s=self.sources();s['B'].camera=dict(s['B'].camera,distance=19.)
        with self.assertRaises(ValueError):same_capture(s)
        with self.assertRaises(ValueError):Original('D',fixture(self.base/'small','D',width=192,height=128),fixture=True)
    def test_corrupt_original_chunk_rejected_without_repair(self):
        root=fixture(self.base,'A');p=root/'main/raw-third-view/raw-rgb/000000.npz';p.write_bytes(p.read_bytes()+b'corruption')
        with self.assertRaises(ValueError):Original('A',root,fixture=True)
    def test_missing_grid_frame_even_with_recomputed_file_SHA_rejected(self):
        root=fixture(self.base,'A');p=root/'main/raw-third-view/raw-rgb/000000.npz'
        with np.load(p,allow_pickle=False)as d:rgb=d['rgb'];ticks=d['physics_tick'].copy();times=d['actual_sim_time_s']
        ticks[1]=0;np.savez_compressed(p,rgb=rgb,physics_tick=ticks,actual_sim_time_s=times);cl=read(root/'main/raw-third-view/closure.json');cl['chunks'][0]['sha256']=sha(p);write(root/'main/raw-third-view/closure.json',cl)
        s=Original('A',root,fixture=True)
        with self.assertRaises(ValueError):list(s.frames())
    def test_source_change_detected_not_reencoded(self):
        s=self.sources();p=s['A'].main/'result.json';p.write_bytes(p.read_bytes()+b' ');self.assertFalse(s['A'].unchanged())
    def test_fixture_cannot_be_promoted_by_encoder_mode(self):
        s=self.sources()
        with self.assertRaises(ValueError):encode(s,self.base/'wrong-mode',fixture=False,cpus=tuple(sorted(os.sched_getaffinity(0))[:2]))
        self.assertFalse((self.base/'wrong-mode').exists())
    def test_six_MP4_fixtures_frame_denominators_and_5_horizontal_lanes(self):
        s=self.sources();cpus=tuple(sorted(os.sched_getaffinity(0))[:2]);out=self.base/'encoded';v=encode(s,out,fixture=True,cpus=cpus,wall_cap_s=120,output_cap_bytes=8*1024**2)
        self.assertEqual(v['role'],FIXTURE);self.assertTrue(v['source_SHA_before_after_identical']);self.assertEqual([v['artifacts'][a]['frames']for a in ARMS],[3,2,1,3,2]);stream=v['artifacts']['five-panel']['probe']['streams'][0]
        self.assertEqual((stream['width'],stream['height'],int(stream['nb_read_frames'])),(4800,636,3));self.assertTrue(all(s0.unchanged()for s0 in s.values()))
        with self.assertRaises(FileExistsError):encode(s,out,fixture=True,cpus=cpus)
    def test_E_individual_release_does_not_wait_for_WM_or_A_D(self):
        source=Original('E',fixture(self.base,'E',tick=10,passed=False,task=None),fixture=True);sources={'E':source};cpus=tuple(sorted(os.sched_getaffinity(0))[:2]);out=self.base/'E-early'
        v=encode(sources,out,individual_only=True,fixture=True,cpus=cpus,wall_cap_s=120,output_cap_bytes=8*1024**2)
        self.assertEqual(tuple(v['artifacts']),('E',));self.assertTrue(v['individual_only_delivery']);self.assertFalse(v['full_comparison_video_delivered']);self.assertFalse(v['five_horizontal_columns_same_original_sim_clock']);self.assertIsNone(v['source']['E']['original_task_success']);self.assertFalse((out/'five-panel-direct-original-1x.mp4').exists())
    def test_E_only_cannot_claim_full_five_arm_comparison(self):
        source=Original('E',fixture(self.base,'E',tick=10),fixture=True);out=self.base/'missing-A-D';cpus=tuple(sorted(os.sched_getaffinity(0))[:2])
        with self.assertRaises(ValueError):encode({'E':source},out,fixture=True,cpus=cpus)
        self.assertFalse(out.exists())
if __name__=='__main__':unittest.main(verbosity=2)
