"""CPU/source/zero-step model tests. No native physics stepping, training or WM."""
from copy import deepcopy
import ast
import json
import os
from pathlib import Path
import tempfile
import unittest
import numpy as np
import torch
from mujoco_zyh.source_bundle import parse_checksums,verify_bundle,digest
from mujoco_zyh.scene import calibration,IDENTITY
from mujoco_zyh.runtime_adapter import prepare_runtime_source,construct_runtime
from mujoco_zyh.collect import validate_protocol
from mujoco_zyh.streams import ChunkedEpisodeWriter,ByteBudgetExceeded,write_json,sha
from mujoco_zyh.audit import audit


def protocol():return json.loads(Path(__file__).with_name('migration_protocol_v1.json').read_text())


def packet(tick):
    return dict(rgb=torch.zeros(1,1,16,24,3,dtype=torch.uint8),depth_m=torch.ones(1,1,16,24,1),
        camera_K=torch.tensor([[[6.,0,12],[0,6,8],[0,0,1]]]),T_base_optical=torch.eye(4)[None],
        proprio=torch.zeros(1,1,45),actions_previous=torch.zeros(1,1,18),action_valid=torch.tensor([[tick>0]]),
        timestamps_s=torch.tensor([[tick*.02]],dtype=torch.float64))


class Contracts(unittest.TestCase):
    def test_protocol_is_one_new_backend_episode_not_old_dispatch(self):
        p=validate_protocol(protocol());self.assertEqual(p['episodes'],1);self.assertEqual(p['auxiliary_calibration_worlds_allowed'],1)
    def test_no_retry_or_reset_or_WM(self):
        for k,v in [('automatic_retry',True),('reset_after_initial_allowed',1),('WM_forwards',1),('training_runs',1),('episodes',2)]:
            p=protocol();p[k]=v
            with self.subTest(k=k),self.assertRaises(ValueError):validate_protocol(p)
    def test_auxiliary_world_cannot_be_hidden(self):
        p=protocol();p['auxiliary_calibration_worlds_allowed']=0
        with self.assertRaises(ValueError):validate_protocol(p)
    def test_B_cannot_be_relabelled_without_executor(self):
        p=protocol();p['scene_recipe']='research_threebox';p['scenario']='nav-push';p['selected_object_id']='middle'
        with self.assertRaisesRegex(ValueError,'Selected B executor'):validate_protocol(p)
    def test_40cm_cannot_be_mislabeled_as_20cm_climb(self):
        p=protocol();p['scene_recipe']='research_threebox';p['selected_object_id']='light'
        with self.assertRaisesRegex(ValueError,'40cm'):validate_protocol(p)
    def test_budget_bounds_fail_closed(self):
        for k,v in [('max_sim_seconds',181),('max_wall_seconds',3601),('max_payload_bytes',0),('max_sim_seconds',float('nan'))]:
            p=protocol();p[k]=v
            with self.subTest(k=k),self.assertRaises(ValueError):validate_protocol(p)
    def test_scene_identity_not_mass_renamed(self):
        self.assertEqual([(k,v['mass_kg']) for k,v in IDENTITY.items()],[('light',20.),('middle',.5),('heavy',1.)])
    def test_calibration_preserves_field_of_view_and_right_handed_optical_frame(self):
        a,T=calibration(192,128);b,_=calibration(384,256)
        self.assertTrue(np.array_equal(a[:2]*2,b[:2]));self.assertAlmostEqual(np.linalg.det(T[:3,:3]),1.)
        self.assertTrue(np.allclose(T[:3,:3].T@T[:3,:3],np.eye(3)))
    def test_no_invalid_camera(self):
        for size in [(192,120),(15,10),(0,0)]:
            with self.assertRaises(ValueError):calibration(*size)
    def test_source_path_traversal_or_duplicate_refused(self):
        for text in [('a'*64)+'  ../escape',('a'*64)+'  /absolute',('a'*64)+'  x\n'+('a'*64)+'  x']:
            with self.assertRaises(ValueError):parse_checksums(text)
    def test_collector_and_observer_do_not_write_physical_states_or_clear_queues(self):
        for file in ['collect.py','observer.py']:
            tree=ast.parse(Path(__file__).with_name(file).read_text())
            for n in ast.walk(tree):
                if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute):
                    self.assertNotIn(n.func.attr,('mj_resetData','reset','mj_step','clear','write_root_pose_to_sim'))


class Streams(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)/'episode';self.p=protocol()
        self.p.update(command_chunk_steps=3,visual_chunk_frames=1,delay_steps=[2]*18,effort_limits_nm=[10.]*18)
        self.w=ChunkedEpisodeWriter(self.root,self.p)
    def tearDown(self):
        if not self.w.closed:self.w.close(outcome='test_cleanup',terminal_time_s=self.w.steps*.005,censored=True)
        self.tmp.cleanup()
    def command(self,step):
        u=np.zeros((5,18));u[2]=1.
        self.w.append_command(issued=u,delayed=u,torque=np.zeros(18),raw_torque=np.zeros(18),q_before=np.zeros(18),dq_before=np.zeros(18),physical_tick=step,time_s=step*.005)
    def frame(self,tick):self.w.append_visual(packet(tick),control_tick=tick,private_catalog=dict(model_input_allowed=False,control_tick=tick))
    def test_sparse_frames_keep_every_intervening200Hz_command(self):
        self.frame(0)
        for i in range(1,21):self.command(i)
        self.frame(5);self.w.close(outcome='synthetic_censor',terminal_time_s=.1,censored=True)
        result=audit(self.root);self.assertTrue(result['data_integrity_pass'],result)
        self.assertEqual(result['actual_physical_command_steps'],20);self.assertEqual(result['actual_visual_frames'],2)
    def test_nonconstant_delay_and_PD_recompute_across_chunk_boundaries(self):
        from collections import deque
        self.frame(0);history=deque(maxlen=5)
        for step in range(1,21):
            u=np.zeros((5,18));u[0]=step*.001;u[1]=.02;u[2]=30.;u[3]=.6;u[4]=.01
            history.append(u.copy());d=history[max(0,len(history)-3)].copy()
            q=np.ones(18)*.01;dq=np.ones(18)*.03
            raw=d[2]*(d[0]-q)+d[3]*(d[1]-dq)+d[4]
            self.w.append_command(issued=u,delayed=d,torque=np.clip(raw,-10.,10.),raw_torque=raw,q_before=q,dq_before=dq,physical_tick=step,time_s=step*.005)
        p=packet(5);p['actions_previous'][:]=.02
        self.w.append_visual(p,control_tick=5,private_catalog=dict(model_input_allowed=False,control_tick=5))
        self.w.close(outcome='synthetic',terminal_time_s=.1,censored=True)
        result=audit(self.root);self.assertTrue(result['data_integrity_pass'],result)
    def test_sparse_visual_cannot_claim_a_different_previous_target(self):
        self.frame(0)
        for i in range(1,21):self.command(i)
        p=packet(5);p['actions_previous'][:]=1.
        self.w.append_visual(p,control_tick=5,private_catalog=dict(model_input_allowed=False,control_tick=5))
        self.w.close(outcome='synthetic',terminal_time_s=.1,censored=True)
        self.assertFalse(audit(self.root)['data_integrity_pass'])
    def test_visual_without_full_action_interval_refused(self):
        self.frame(0)
        with self.assertRaises(ValueError):self.frame(5)
    def test_first_action_missing_not_fake_zero_history(self):
        p=packet(0);p['action_valid'][:]=True
        with self.assertRaises(ValueError):self.w.append_visual(p,control_tick=0,private_catalog=dict(model_input_allowed=False,control_tick=0))
    def test_duplicate_or_gapped_physical_step_refused(self):
        self.command(1)
        for step in (1,3):
            with self.assertRaises(ValueError):self.command(step)
    def test_truth_fields_cannot_enter_model_packet(self):
        p=packet(0);p['box_mass']=torch.ones(1)
        with self.assertRaises(ValueError):self.w.append_visual(p,control_tick=0,private_catalog=dict(model_input_allowed=False,control_tick=0))
    def test_partial_chunk_flush_and_source_closure(self):
        self.frame(0);self.command(1)
        result=self.w.close(outcome='native_failure',terminal_time_s=.005,censored=True)
        self.assertEqual(result['physical_command_steps'],1);self.assertTrue(result['storage_complete'])
        with self.assertRaises(ValueError):self.command(2)
    def test_byte_quota_cannot_be_silently_exceeded(self):
        self.w.metadata['max_payload_bytes']=1
        with self.assertRaises(ByteBudgetExceeded):self.frame(0)
        result=self.w.close(outcome='quota',terminal_time_s=0.,censored=True)
        self.assertFalse(result['storage_complete'])
    def test_changed_calibration_refused(self):
        self.frame(0)
        for i in range(1,21):self.command(i)
        p=packet(5);p['camera_K'][0,0,0]+=1
        with self.assertRaises(ValueError):self.w.append_visual(p,control_tick=5,private_catalog=dict(model_input_allowed=False,control_tick=5))
    def test_audit_detects_edited_source_file(self):
        self.frame(0);self.w.close(outcome='end',terminal_time_s=0.,censored=True)
        with (self.root/'private-catalog.jsonl').open('a') as f:f.write('{}\n')
        self.assertFalse(audit(self.root)['data_integrity_pass'])


class PinnedNativeZeroStep(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.bundle=Path(os.environ['ZYH_BUNDLE'])
    def test_all148_payloads_verified_including_real_actors_not_LFS_pointers(self):
        r=verify_bundle(self.bundle);self.assertEqual(r['verified_files'],148)
    def test_runtime_hook_inverse_retains_all_native_algorithms(self):
        source=(self.bundle/'switch/runtime.py').read_text();prepared,r=prepare_runtime_source(source)
        self.assertTrue(r['inverse_restores_original']);self.assertEqual(r['constructor_only_hunks'],3)
        with self.assertRaises(ValueError):prepare_runtime_source('class Runtime: pass')
    def test_original_native_scene_and_all_actors_construct_without_physics_steps(self):
        p=protocol();p.update(scenario='nav-nav',auxiliary_calibration_worlds_allowed=0,auxiliary_calibration_max_sim_seconds=0)
        r,m,receipt=construct_runtime(self.bundle,p)
        self.assertEqual(r.sim.data.time,0.);self.assertEqual(r.step_count,0)
        self.assertEqual(r.sim.model.nu,18);self.assertEqual(receipt['source']['verified_files'],148)
        self.assertFalse(m.complete)
    def test_native_observation_and_all_four_actor_interfaces_without_stepping(self):
        p=protocol();p.update(scenario='nav-nav',auxiliary_calibration_worlds_allowed=0,auxiliary_calibration_max_sim_seconds=0)
        r,m,receipt=construct_runtime(self.bundle,p)
        from runtime import infer
        nav=r.n.observation();climb=r.c.observation()
        with r.push.active():push=r.sim.observation()
        self.assertEqual(nav.shape,(210,));self.assertEqual(climb.shape,(923,));self.assertEqual(push.shape,(226,))
        for actor,obs,dim in [(r.nav_actor,nav,18),(r.climb_actor,climb,18),(r.push_actors[0],push,12),(r.push_actors[1],push,19)]:
            value=infer(actor,obs,'cpu');self.assertEqual(value.shape,(dim,));self.assertTrue(np.isfinite(value).all())
        self.assertEqual(r.sim.data.time,0.)
    def test_threebox_identity_camera_and40cm_platform_compile_without_stepping(self):
        p=protocol();p.update(scenario='nav-nav',scene_recipe='research_threebox',selected_object_id='light',auxiliary_calibration_worlds_allowed=0,auxiliary_calibration_max_sim_seconds=0)
        r,m,receipt=construct_runtime(self.bundle,p)
        self.assertEqual(r.sim.data.time,0.);self.assertEqual(r.sim.model.nv,42)
        for key,item in IDENTITY.items():self.assertAlmostEqual(r.sim.model.body_mass[r.sim.model.body(item['body']).id],item['mass_kg'])
        self.assertTrue(np.allclose(r.sim.model.geom('wm_research_platform').size,[1.,3.,.2]))
        self.assertFalse(receipt['scene']['failed_A_recovery_or_selected_B_binding_implemented'])


if __name__=='__main__':unittest.main()
