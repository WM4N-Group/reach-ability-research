"""Synthetic config/stream tests; no Isaac App or physical episode."""
import ast
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch
import numpy as np
import torch
from build_video_demo import build,PARENT,sha
from native_recording import NativeRecording,configure_view

class ConfigTests(unittest.TestCase):
    def test_build_has_unchanged_controller_and_only_view_capture_main_changes(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'demo';req=build(root,root)
            def nodes(p):return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(p.read_text()).body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name!='main'}
            self.assertEqual(nodes(root/'source/probe.py'),nodes(PARENT/'source/probe.py'))
            for f in ['prospective_support.py','pose_entry_selection.py','box_approach_standoff.py']:
                self.assertEqual(sha(root/'source'/f),sha(PARENT/'source'/f))
            p=json.loads((root/'source/protocol.json').read_text());self.assertEqual(len(p['schedule']),1)
            self.assertFalse(req['approved']);self.assertEqual(req['budgets']['physical_starts'],1)
    def test_direct_start_forbidden_before_App(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'demo';build(root,root)
            result=subprocess.run([sys.executable,str(root/'source/probe.py')],capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0);self.assertIn('No exact native-video permit',result.stderr)
            self.assertNotIn('No module named',result.stderr)
    def test_camera_view_changes_no_control_config(self):
        cfg=NS(viewer=NS(),sim=NS(dt=.005),decimation=4,control='same');configure_view(cfg)
        self.assertEqual(cfg.viewer.resolution,(960,640));self.assertEqual(cfg.sim.dt,.005);self.assertEqual(cfg.control,'same')
    def test_recorder_contains_no_physics_or_state_reconstruction_call(self):
        tree=ast.parse(Path(__file__).with_name('native_recording.py').read_text())
        calls={n.func.attr for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)}
        self.assertFalse(calls&{'mj_step','mj_forward','write_root_pose_to_sim','write_joint_state_to_sim','step'})
        self.assertIn('render',calls)

class RecordingTests(unittest.TestCase):
    def test_live_frame_sampling_and_final_metadata_no_reconstruction(self):
        with tempfile.TemporaryDirectory() as d:
            robot=NS(data=NS(joint_pos=torch.zeros((1,18)),root_state_w=torch.zeros((1,13))))
            b=NS(scene={'robot':robot},episode_length_buf=torch.tensor([0]))
            class Env:
                unwrapped=b
                def render(self):return np.full((640,960,3),128,dtype=np.uint8)
            child=NS(stdin=io.BytesIO(),wait=lambda timeout:0)
            with patch('native_recording.subprocess.Popen',return_value=child):
                rec=NativeRecording(Env(),Path(d));rec.capture(dict(step=0,time_s=0.));rec.capture(dict(step=1,time_s=.02));rec.capture(dict(step=5,time_s=.1))
                self.assertEqual(rec.count,2);rec.close(dict(outcome='SYNTHETIC_TEST_NOT_A_ROBOT'))
            meta=json.loads((Path(d)/'native-video.json').read_text());self.assertFalse(meta['log_reconstruction']);self.assertEqual(meta['fps'],10)
            self.assertTrue(meta['rendering_without_physics_step_verified'])
    def test_render_state_change_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            robot=NS(data=NS(joint_pos=torch.zeros((1,18)),root_state_w=torch.zeros((1,13))))
            b=NS(scene={'robot':robot},episode_length_buf=torch.tensor([0]))
            class Env:
                unwrapped=b
                def render(self):b.episode_length_buf+=1;return np.ones((640,960,3),dtype=np.uint8)
            child=NS(stdin=io.BytesIO(),wait=lambda timeout:0)
            with patch('native_recording.subprocess.Popen',return_value=child):
                rec=NativeRecording(Env(),Path(d))
                with self.assertRaisesRegex(RuntimeError,'physical state or clock'):rec.capture(dict(step=0,time_s=0.))
                rec.log.close();rec.stderr.close()

if __name__=='__main__':unittest.main()

class BudgetTests(unittest.TestCase):
    def test_one_unused_slot_is_transferred_without_increasing_parent_cap(self):
        import video_authority as a
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'demo';root.mkdir();(root/'source').mkdir();(root/'source/manifest.json').write_text('{}')
            (root/'approval.json').write_text('{}');old=Path(tmp)/'old';old.mkdir();(old/'physical_ledger.json').write_text('{"starts":5}')
            family=Path(tmp)/'family';alloc=family/'pose_allocations';oldphase=alloc/'native-pose-singlefactor-six-20261021-v1';(oldphase/'physical_claims').mkdir(parents=True)
            (oldphase/'reservation.json').write_text('{"max_starts":6}')
            previous=alloc/'prior-eight';previous.mkdir();(previous/'reservation.json').write_text('{"max_starts":8}')
            for i in range(5):(oldphase/'physical_claims'/f'completed{i}.json').write_text('{}')
            p=dict(original_family_root=str(family),allocation_id='recording-one',stopped_parent_root=str(old))
            with patch('video_authority.verify',return_value=p),patch('video_authority.sdk_gate'):
                ticket,nonce=a.issue(root,'physical',[])
                self.assertTrue(ticket.exists());self.assertTrue(nonce)
                release=json.loads((oldphase/'unused-slot-release-for-native-video.json').read_text())
                total=2+sum(json.loads(x.read_text())['max_starts'] for x in alloc.glob('*/reservation.json'))-release['released_starts']
                self.assertEqual(total,16)
                self.assertEqual(json.loads((oldphase/'reservation.json').read_text())['max_starts'],6)
                with self.assertRaises(PermissionError):a.issue(root,'physical',[])
    def test_sdk_claim_cannot_be_repeated(self):
        import video_authority as a
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'demo';root.mkdir();(root/'source').mkdir();(root/'source/manifest.json').write_text('{}');(root/'approval.json').write_text('{}')
            family=Path(tmp)/'family';(family/'pose_allocations').mkdir(parents=True)
            p=dict(original_family_root=str(family),allocation_id='recording-one')
            with patch('video_authority.verify',return_value=p):
                a.issue(root,'sdk',[])
                with self.assertRaises(FileExistsError):a.issue(root,'sdk',[])
