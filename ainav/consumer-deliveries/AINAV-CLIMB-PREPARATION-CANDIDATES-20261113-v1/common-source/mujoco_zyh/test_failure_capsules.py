"""Pure CPU fixtures for private evidence. Never real recovery acceptance."""
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

import numpy as np

from mujoco_zyh import failure_capsules as fc
from mujoco_zyh.stall_stow import unload_reference


def fake_snapshot(*a,**kw):
    return dict(qpos=np.array([1.,2.]),point=np.array([float('nan'),0.,0.])),dict(
        actual_time_s=1.25,selected_box_body_id=29,fixture_only=True)


class BoundedEvidence(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.r=NS();self.out=Path(self.tmp.name)/'capsules'
        self.rec=fc.PrivateFailureCapsules(self.out,self.r,fc.CONFIG)
        self.r.wm_private_capsules=self.rec
        self.mock=patch.object(fc,'snapshot',side_effect=fake_snapshot);self.mock.start();self.addCleanup(self.mock.stop)

    def test_lossless_private_NPZ_and_strict_JSON(self):
        row=self.rec.capture('fixture',extra=dict(missing=np.nan,raw=np.array([1.,np.inf])))
        with np.load(self.out/row['path'],allow_pickle=False) as z:
            meta=json.loads(z['metadata_utf8'].tobytes());self.assertTrue(np.isnan(z['point'][0]))
        self.assertIsNone(meta['extra']['missing']);self.assertIsNone(meta['extra']['raw'][1])
        self.assertTrue(meta['fixture_only']);self.assertEqual(meta['event'],'fixture')

    def test_closure_says_private_no_physics(self):
        self.rec.capture('fixture');x=self.rec.close()
        self.assertTrue(x['all_required_captures_complete']);self.assertFalse(x['model_input_allowed'])
        self.assertEqual(x['new_physics_or_actor_or_WM_forwards'],0)

    def test_eight_capsules_exact_count_no_unbounded_logging(self):
        for _ in range(8):self.rec.capture('fixture')
        with self.assertRaisesRegex(ValueError,'count'):self.rec.capture('fixture')
        self.assertEqual(len(list(self.out.glob('*.npz'))),8)

    def test_compressed_byte_quota_refuses_without_partial_evidence(self):
        self.rec.bytes=fc.CONFIG['max_bytes']
        with self.assertRaisesRegex(ValueError,'byte budget'):self.rec.capture('fixture')
        self.assertEqual(list(self.out.iterdir()),[])

    def test_old_path_never_reused_or_overwritten(self):
        with self.assertRaises(FileExistsError):fc.PrivateFailureCapsules(self.out,self.r,fc.CONFIG)

    def test_duplicate_file_cannot_overwrite_previous_evidence(self):
        row=self.rec.capture('fixture');content=(self.out/row['path']).read_bytes();self.rec.rows=[]
        with self.assertRaises(FileExistsError):self.rec.capture('fixture')
        self.assertEqual(content,(self.out/row['path']).read_bytes())

    def test_closed_recorder_cannot_capture_or_close_again(self):
        self.rec.close()
        with self.assertRaises(ValueError):self.rec.capture('fixture')
        with self.assertRaises(ValueError):self.rec.close()

    def test_unsafe_event_name_refused(self):
        for event in ('../escape','UPPER','a/b','', 'a'*65):
            with self.subTest(event=event),self.assertRaises(ValueError):self.rec.capture(event)

    def test_absent_recorder_is_noop_for_old_protocols(self):
        self.assertIsNone(fc.emit(NS(),'soft_progress_abort'))
        fc.snapshot.assert_not_called()

    def test_required_soft_capture_failure_stops_not_continues_recovery(self):
        fc.snapshot.side_effect=RuntimeError('fixture read failed')
        with self.assertRaisesRegex(RuntimeError,'required_private_failure_capsule_refused'):
            fc.emit(self.r,'soft_progress_abort')
        self.assertEqual(len(self.rec.errors),1)

    def test_hard_guard_primary_is_not_masked_by_diagnostic_failure(self):
        fc.snapshot.side_effect=RuntimeError('fixture read failed')
        original=RuntimeError('selected_B_invalid_hand_contact_200Hz')
        try:
            fc.emit(self.r,'selected_b_hard_guard',preserve_primary_failure=True)
            raise original
        except RuntimeError as seen:self.assertIs(seen,original)
        self.assertFalse(self.rec.close()['all_required_captures_complete'])

    def test_exact_config_cannot_be_silently_expanded(self):
        for key,value in [('max_bytes',999999999),('max_capsules',999),('model_input_allowed',True),('training_allowed',True)]:
            config=dict(fc.CONFIG);config[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):fc.validate_config(config)


class BeforeFirstStepAdmission(unittest.TestCase):
    def runtime(self):return NS(step_count=0,sim=NS(data=NS(time=0.),queue=[]))
    def test_install_once_before_any_issuance(self):
        with tempfile.TemporaryDirectory() as tmp:
            r=self.runtime();rec=fc.install(r,tmp,fc.CONFIG);self.assertIs(r.wm_private_capsules,rec)
            with self.assertRaises(ValueError):fc.install(r,tmp,fc.CONFIG)

    def test_nonzero_step_clock_or_queue_prevents_late_enable(self):
        for field in ('step','clock','queue'):
            r=self.runtime()
            if field=='step':r.step_count=1
            elif field=='clock':r.sim.data.time=.005
            else:r.sim.queue=[np.zeros((5,18))]
            with tempfile.TemporaryDirectory() as tmp,self.subTest(field=field),self.assertRaises(ValueError):fc.install(r,tmp,fc.CONFIG)


class CoupledRefusalPayload(unittest.TestCase):
    def inputs(self):
        return dict(goal=np.ones(6)*.3,start=np.ones(6)*.2,reference=np.ones(6)*.2,velocity=np.zeros(6),
                    q=np.ones(6)*.2,dq=np.zeros(6),kp=np.ones(6)*50,kd=np.ones(6)*3,
                    gravity=np.ones(6)*-2.,effort=np.ones(6)*20,limits=np.tile([-1.,1.],(6,1)),age=.005)
    def test_original_error_type_and_text_preserved(self):
        p=self.inputs();p['q'][1]=.9
        with self.assertRaisesRegex(RuntimeError,'^unload_coupled_reference_intersection_empty:1$') as seen:unload_reference(**p)
        self.assertIs(type(seen.exception),RuntimeError)
        self.assertEqual(seen.exception.wm_reference_inputs['failing_joint_zero_based'],1)

    def test_all_six_gravity_and_actual_fields_are_copied_not_recomputed(self):
        p=self.inputs();p['q'][1]=.9
        try:unload_reference(**p)
        except RuntimeError as error:payload=error.wm_reference_inputs
        for key in ('goal','start','reference','velocity','q','dq','kp','kd','gravity','effort','limits'):
            self.assertTrue(np.array_equal(payload[key],p[key]));self.assertFalse(np.shares_memory(payload[key],p[key]))
        p['gravity'][:]=500.;self.assertTrue((payload['gravity']==-2.).all())

    def test_payload_exactly_reproduces_math_refusal_without_physics(self):
        p=self.inputs();p['q'][1]=.9
        try:unload_reference(**p)
        except RuntimeError as error:payload=error.wm_reference_inputs
        args={key:payload[key] for key in p};args['dt']=payload['dt']
        with self.assertRaisesRegex(RuntimeError,'unload_coupled_reference_intersection_empty:1'):unload_reference(**args)

    def test_feasible_math_output_unchanged_and_no_input_writes(self):
        p=self.inputs();before={key:value.copy() if isinstance(value,np.ndarray) else value for key,value in p.items()}
        ref,vel,ff,receipt=unload_reference(**p)
        self.assertEqual(len(receipt),6);self.assertTrue(np.isfinite(np.r_[ref,vel,ff]).all())
        for key in p:self.assertTrue(np.array_equal(p[key],before[key]))


class BeforeRaiseWiring(unittest.TestCase):
    def recorder(self,r):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        rec=fc.PrivateFailureCapsules(Path(tmp.name)/'private',r,fc.CONFIG);r.wm_private_capsules=rec
        return rec

    def test_B_exact_hard_guard_emits_before_raise_and_uses_B_view(self):
        from collections import deque
        from mujoco_zyh.reselect_B import ReselectBRouter
        box=NS(forbidden_box_contact=lambda view:[False],invalid_hand_contact=lambda view,cfg:[True],box_tipped=lambda view:[False])
        p=NS(data=NS(qpos=np.zeros(18),qvel=np.zeros(18)),model=NS(jnt_range=np.tile([-1.,1.],(18,1))),
             qids=np.arange(18),dids=np.arange(18),jids=np.arange(18))
        r=NS(sim=p,last=NS(position=np.zeros(18)),push={'model':NS(SPEED=np.ones(18)),'bridge':NS(box_push=box)})
        router=ReselectBRouter.__new__(ReselectBRouter);router.r=r;router.stage='B_PUSH_ACTIVE';router.bound_runtime=NS()
        router.view=NS(refresh=lambda:None,hand_cfg=NS());router.last_two=deque(maxlen=2)
        rec=self.recorder(r)
        with patch.object(fc,'snapshot',side_effect=fake_snapshot) as capture:
            with self.assertRaisesRegex(RuntimeError,'selected_B_invalid_hand_contact_200Hz'):router.after_step()
        self.assertIs(capture.call_args.args[1],router.view)
        self.assertEqual(rec.rows[0]['event'],'selected_b_hard_guard')

    def test_reference_before_raise_includes_actual_gravity_inputs(self):
        import torch
        from mujoco_zyh.stall_stow import ProtectedStow
        p=NS(data=NS(time=.005,qpos=np.zeros(18),qvel=np.zeros(18)),qids=np.arange(18),dids=np.arange(18),
             robot=NS(joint_names=['joint'+str(i) for i in range(1,7)],get_gravity_compensation_forces=lambda:torch.ones((1,6))*-2.))
        p.data.qpos[12:]=.2;p.data.qpos[13]=.9
        r=NS(sim=p);rec=self.recorder(r)
        stow=ProtectedStow.__new__(ProtectedStow);stow.r=r;stow.s=p;stow.native=NS();stow.started=0.;stow.last_update=-np.inf
        stow.phase='UNLOAD_CAPTURE';stow.unload_target=np.ones(6)*.3;stow.reference_start=np.ones(6)*.2
        stow.reference=np.ones(6)*.2;stow.velocity=np.zeros(6);stow.limits=np.tile([-1.,1.],(6,1))
        stow.pm=NS(KP=np.ones(18)*50,KD=np.ones(18)*3,EFFORT=np.ones(18)*20)
        with patch.object(fc,'snapshot',side_effect=fake_snapshot):
            with self.assertRaisesRegex(RuntimeError,'unload_coupled_reference_intersection_empty:1'):stow.command()
        self.assertEqual(rec.rows[0]['event'],'unload_reference_refusal')
        with np.load(rec.root/rec.rows[0]['path'],allow_pickle=False) as z:
            meta=json.loads(z['metadata_utf8'].tobytes())
        self.assertEqual(meta['extra']['reference_inputs']['gravity'],[-2.]*6)

    def test_soft_abort_hook_capture_precedes_recovery_construction(self):
        import io,torch
        from mujoco_zyh.stall_stow import StallStowRouter,SoftStall
        p=NS(data=NS(time=1.,xpos=np.array([[1.,0.,0.]])),box_id=0,box_push_target=torch.tensor([[2.,0.,0.]]),
             controller=NS(motion_ready=[True]),targets=np.zeros(18),hand_cfg=NS(),scene=NS(sensors={
                 'box_contact_hand':NS(data=NS(force_matrix_w=torch.tensor([[[[-2.,0.,0.]]]]))) }))
        r=NS(sim=p,last=NS(position=np.zeros(18)),push={'bridge':NS(box_push=NS(hand_contact=lambda *a:[True]))})
        router=StallStowRouter.__new__(StallStowRouter);router.r=r;router.recovery=None;router.native=NS(kind='push',phase='active')
        router.original_termination=lambda:dict(box_settled=False);router.control_tick=1;router.log=io.StringIO()
        router.monitor=NS(observe=lambda sample:NS(status='soft_abort',elapsed_contact_s=.06,observed_forward_dx_m=.001,new_soft_abort_request=True))
        rec=self.recorder(r)
        with patch.object(fc,'snapshot',side_effect=fake_snapshot):
            with self.assertRaises(SoftStall):router.termination()
        self.assertIsNone(router.recovery);self.assertEqual(rec.rows[0]['event'],'soft_progress_abort')


    def test_speed_envelope_capsule_keeps_original_guard_and_metrics(self):
        import torch
        from mujoco_zyh.stall_stow import ProtectedStow
        p=NS(data=NS(time=1.),box_push_target=torch.zeros((1,3)))
        r=NS(sim=p);rec=self.recorder(r)
        stow=ProtectedStow.__new__(ProtectedStow);stow.r=r;stow.s=p;stow.started=0.
        stow.original_goal=np.zeros((1,3));stow.retired_history_sha='same'
        stow.measure=lambda:dict(base_horizontal_displacement_m=.001,base_linear_speed=.151)
        with patch('mujoco_zyh.stall_stow.history_sha',return_value='same'),patch.object(fc,'snapshot',side_effect=fake_snapshot):
            with self.assertRaisesRegex(RuntimeError,'^measured_unload_retreat_outside_original_envelope$'):stow.update()
        self.assertEqual(rec.rows[0]['event'],'unload_envelope_refusal')


class HeterogeneousNativeHistory(unittest.TestCase):
    def test_all_seven_native_term_widths_saved_separately(self):
        values=[np.arange(3*n,dtype=np.float32).reshape(3,n) for n in (3,3,18,18,18,3,7)]
        arrays={};layout=fc.copy_history_terms(arrays,[('selected',NS(history=values))])
        self.assertEqual([item['shape'] for item in layout['selected']],[[3,n] for n in (3,3,18,18,18,3,7)])
        for original,item in zip(values,layout['selected']):self.assertTrue(np.array_equal(original,arrays[item['key']]))
    def test_none_history_preserved_as_empty_layout_without_object_arrays(self):
        arrays={};layout=fc.copy_history_terms(arrays,[('selected',NS(history=None))])
        self.assertEqual(layout,{'selected':[]});self.assertEqual(arrays,{})
    def test_history_copies_do_not_alias_or_update_native_cache(self):
        h=np.ones((3,18));arrays={};layout=fc.copy_history_terms(arrays,[('selected',NS(history=[h]))])
        arrays[layout['selected'][0]['key']][0,0]=9.;self.assertEqual(h[0,0],1.)
    def test_different_dtypes_are_retained_not_coerced_to_common_stack(self):
        a=np.ones((3,3),np.float32);b=np.ones((3,18),np.float64);arrays={}
        layout=fc.copy_history_terms(arrays,[('selected',NS(history=[a,b]))])
        self.assertEqual([item['dtype'] for item in layout['selected']],['float32','float64'])


if __name__=='__main__':unittest.main()
