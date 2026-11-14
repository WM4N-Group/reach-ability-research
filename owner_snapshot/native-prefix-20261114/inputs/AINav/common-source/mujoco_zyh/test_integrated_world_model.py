"""Data clocks, source isolation and actual recurrent training gradient checks."""
import json,tempfile,unittest
from pathlib import Path
import numpy as np
import torch
from mujoco_zyh.streams import sha
from mujoco_zyh.integrated_dataset import ordered_intervals,Windows
from mujoco_zyh.integrated_world_model import RecurrentWorldModel,loss_terms

class DatasetContracts(unittest.TestCase):
    def test_preserves_all_ordered_substeps_not_just_average_or_last_action(self):
        commands=np.arange(44*90).reshape(44,5,18)
        a,tail=ordered_intervals(commands,np.arange(1,45),np.array([0,5,10]))
        self.assertEqual(a.shape,(2,20,5,18));self.assertEqual(tail,4)
        self.assertTrue(np.array_equal(a[0],commands[:20]));self.assertTrue(np.array_equal(a[1],commands[20:40]))
    def test_missing_or_reordered_motor_clock_is_rejected(self):
        commands=np.zeros((40,5,18));ticks=np.arange(1,41);ticks[2]=4
        with self.assertRaises(ValueError):ordered_intervals(commands,ticks,[0,5,10])
        with self.assertRaises(ValueError):ordered_intervals(commands[:39],np.arange(1,40),[0,5,10])
        with self.assertRaises(ValueError):ordered_intervals(commands,np.arange(1,41),[0,5,11])
    def test_training_loader_does_not_open_holdout_and_does_not_pad_terminal_future(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);packed=root/'train.npz';n=12
            with packed.open('wb') as f:np.savez_compressed(f,rgb=np.zeros((n,64,96,3),np.uint8),depth_m=np.zeros((n,64,96),np.float16),depth_valid=np.zeros((n,64,96),bool),proprio=np.tile(np.arange(n)[:,None],(1,45)).astype(np.float32),actions=np.zeros((n-1,20,5,18),np.float32))
            manifest=root/'manifest.json';manifest.write_text(json.dumps(dict(training=dict(context_frames=3,rollout_frames=4),episodes=[dict(role='train',source_group='train',packed=str(packed),packed_sha256=sha(packed)),dict(role='test',source_group='test',packed='/DO_NOT_READ_HELDOUT',packed_sha256='invalid')])) )
            data=Windows(manifest,'train');self.assertEqual(len(data),2)
            self.assertTrue(np.array_equal(data[1]['proprio'][:,0],np.arange(5,12)))
            self.assertEqual(data[1]['actions'].shape,(6,1800))
    def test_actual_rgbd_and_dynamics_receive_finite_training_gradients(self):
        torch.set_num_threads(2);torch.manual_seed(5);model=RecurrentWorldModel()
        visual=torch.rand(1,2,5,64,96);proprio=torch.rand(1,2,45);action=torch.rand(1,3,1800)
        before=visual.clone();pv,pp=model(visual,proprio,action,2)
        target=torch.rand_like(pv);target[:,:,4]=(target[:,:,4]>.5).float()
        terms=loss_terms(pv,pp,target,torch.rand_like(pp));terms['loss'].backward()
        self.assertTrue(torch.isfinite(terms['loss']))
        self.assertGreater(float(model.action_encoder[0].weight.grad.abs().sum()),0.)
        self.assertGreater(float(model.encoder[0].weight.grad.abs().sum()),0.)
        self.assertTrue(torch.equal(before,visual));self.assertEqual(pv.shape,(1,2,5,64,96))
    def test_action_substep_order_changes_the_same_context_prediction(self):
        torch.set_num_threads(2);torch.manual_seed(7);model=RecurrentWorldModel().eval()
        v=torch.rand(1,2,5,64,96);p=torch.zeros(1,2,45);a=torch.randn(1,3,20,90)
        with torch.no_grad():
            left=model(v,p,a.reshape(1,3,1800),2)[0]
            right=model(v,p,a.flip(2).reshape(1,3,1800),2)[0]
        self.assertFalse(torch.allclose(left,right,atol=1e-7,rtol=0))

class PipelineIsolation(unittest.TestCase):
    def test_training_freeze_opens_only_bootstrap_and_registered_training_sources(self):
        from unittest.mock import patch
        from mujoco_zyh import integrated_training_pipeline as pipeline
        from mujoco_zyh.integrated_batch import plan as load_plan
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);summary=base/'integrated-course-five-complete-20261026-v1/five-complete-summary.json'
            summary.parent.mkdir();batch=base/'batch';batch.mkdir();rows=[]
            def root_data(root):
                (root/'episode').mkdir(parents=True)
                for name in ('protocol.json','freeze.json','episode/episode.json','episode/index.json','episode/closure.json'):(root/name).write_text('{}')
                (root/'report.json').write_text(json.dumps(dict(task_success=True,frames=40,physical_steps=800,error=None)))
                ap=root/'audit.json';ap.write_text(json.dumps(dict(original_motor_and_visual_audit=dict(data_integrity_pass=True),report_sha256=sha(root/'report.json'))));return ap
            for i in range(1,6):
                root=base/f'bootstrap-{i}';ap=root_data(root)
                rows.append(dict(case_id=f'full-{i}',root=str(root),report_sha256=sha(root/'report.json'),independent_audit=str(ap),audit_sha256=sha(ap)))
            summary.write_text(json.dumps(dict(rows=rows)));registered=load_plan();registered['bootstrap_summary_sha256']=sha(summary)
            for row in registered['cases']:
                if row['role']=='train':
                    root=base/row['case_id'];ap=root_data(root);(batch/(row['case_id']+'-independent-audit.json')).write_text(ap.read_text())
            with patch.object(pipeline,'BASE',base),patch.object(pipeline,'plan',lambda:registered),patch.object(pipeline,'root_for',lambda r:base/r['case_id']):
                self.assertTrue(pipeline.training_audits_ready(batch))
                d=pipeline.freeze_training_sources(batch,base/'training-manifest.json')
            self.assertEqual(len(d['episodes']),9);self.assertEqual(len(d['reserved_heldout_sources']),4)
            self.assertTrue(all(e['role']=='train' for e in d['episodes']))
            self.assertFalse(d['heldout_observations_or_outcomes_read'])
            self.assertTrue(all(not (base/r['case_id']).exists() for r in registered['cases'] if r['role']!='train'))

    def test_evaluation_packing_reuses_frozen_training_statistics(self):
        from unittest.mock import patch
        from mujoco_zyh import integrated_dataset as dataset
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);packed=base/'train.npz'
            np.savez_compressed(packed,camera_K=np.eye(3),T_base_optical=np.eye(4),proprio=np.zeros((30,45)),actions=np.zeros((29,20,5,18)))
            cfg=dict(context_frames=5,rollout_frames=20,image_height=64,image_width=96)
            normalization=dict(fit_split='train_only',proprio_mean=[2.]*45,proprio_std=[3.]*45,action_mean=[4.]*90,action_std=[5.]*90)
            train=dict(root='/raw-training',role='train',source_group='training',report_sha256='unchanged',packed=str(packed),packed_sha256=sha(packed),frames=30,windows_stride5=2)
            old=base/'old.json';old.write_text(json.dumps(dict(training=cfg,episodes=[train],normalization=normalization)))
            heldout=dict(root='/raw-holdout',role='test',source_group='test',report_sha256='heldout')
            raw=base/'raw.json';raw.write_text(json.dumps(dict(training=cfg,episodes=[{k:v for k,v in train.items() if k not in ('packed','packed_sha256')},heldout],bootstrap_new_training_authorization='explicit')))
            def pack(entry,output,config):
                np.savez_compressed(output,camera_K=np.eye(3),T_base_optical=np.eye(4),proprio=np.ones((30,45))*1e6,actions=np.ones((29,20,5,18))*1e6)
                return dict(**entry,packed=str(output),packed_sha256=sha(output),frames=30,windows_stride5=2)
            with patch.object(dataset,'pack_source',pack):dataset.prepare(raw,base/'evaluation',reuse_training_manifest=old)
            d=json.loads((base/'evaluation/packed-manifest.json').read_text())
            self.assertEqual(d['normalization'],normalization);self.assertEqual(d['episodes'][0]['packed'],str(packed))
