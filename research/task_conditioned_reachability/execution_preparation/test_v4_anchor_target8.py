"""Metadata-only explicit geometry fixtures; real original NumPy smoke is remote.

No local sensor frames, model, Torch, native engine or original trainer imports.
"""
import copy
import hashlib
from pathlib import Path
import shutil
import tempfile
from types import SimpleNamespace
import unittest
from .v4_anchor_target8 import AnchorTarget8Provider,checked_geometry_sources,PINS
from .v4_causal_wm_query import CausalWMQueryPort

SOURCE = Path(__file__).resolve().parents[3]/'inference_source/original_behavior7a6_geometry'
class FixtureArray:
    def __init__(self, shape, raw=b'EXPLICIT_SOFTWARE_FIXTURE_NOT_SENSOR'):
        self.shape=shape; self.raw=raw
    def tobytes(self): return self.raw

class AnchorGeometryTests(unittest.TestCase):
    def setUp(self):
        self.anchor=dict(rgb=FixtureArray((64,96,3)),depth_m=FixtureArray((64,96)),camera_K='FIXTURE',
            T_base_optical='FIXTURE',time_s=1.)
        self.obs=SimpleNamespace(time_s=1.015)
        self.options=(SimpleNamespace(sha256='a'*64),)
        self.calls=[]
        def describe(rgb,depth,K,mount,**kwargs):
            self.calls.append((rgb,depth,K,mount,kwargs))
            return dict(RGB_sha256=hashlib.sha256(rgb.tobytes()).hexdigest(),calibration_sha256='FIXTURE_CAL',
                frame_local_ref=kwargs['frame_local_ref'],uses_only_current_RGBD_and_calibration=True,
                physical_action_admitted=False,EXPLICIT_SOFTWARE_FIXTURE=True)
        self.api=SimpleNamespace(describe_visible_goal=describe,geometry_vector=lambda proof:(1,0,0,1,1,.001,.8,1),
            visual_calibration_sha=lambda K,T:'FIXTURE_CAL',source_pins=dict(PINS))
    def association(self,obs,options,anchor):
        return dict(WM_anchor_RGB_bytes_sha256=hashlib.sha256(anchor['rgb'].tobytes()).hexdigest(),
            WM_anchor_time_s=anchor['time_s'],WM_anchor_calibration_sha256='FIXTURE_CAL',
            frame_local_ref_by_option_sha256={'a'*64:dict(frame_local_ref='visual-proposal-0',declared_standoff_m=1.05)})
    def provider(self,association=None):
        return AnchorTarget8Provider(association_provider=self.association if association is None else association,
            software_fixture=True,fixture_api=self.api)
    def test_original_geometry_byte_pins_without_importing_numpy_or_trainer(self):
        self.assertEqual(set(checked_geometry_sources(SOURCE)),set(PINS))
    def test_source_and_manifest_cannot_both_be_rewritten_to_claim_original(self):
        import json
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'geometry';shutil.copytree(SOURCE,root)
            p=root/'geometry_vector.py';p.write_bytes(p.read_bytes()+b'\n# changed\n')
            manifest=json.loads((root/'SOURCE_INVENTORY.json').read_text())
            manifest['files'][p.name]['custody_sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
            (root/'SOURCE_INVENTORY.json').write_text(json.dumps(manifest))
            with self.assertRaises(ValueError):checked_geometry_sources(root)
    def test_same_actual_anchor_vector_and_fixture_label_not_native_permission(self):
        out=self.provider()(self.obs,self.options,self.anchor)
        self.assertEqual(out['target8_by_option_sha256']['a'*64],(1.,0.,0.,1.,1.,.001,.8,1.))
        self.assertEqual(out['source_role'],'EXPLICIT_SOFTWARE_FIXTURE_NOT_MODEL_TASK_INPUT')
        self.assertIsNot(self.calls[0][0],self.anchor['rgb'])
        self.assertEqual(self.calls[0][0].tobytes(),self.anchor['rgb'].tobytes())
        self.assertEqual(self.calls[0][1].tobytes(),self.anchor['depth_m'].tobytes())
    def test_missing_association_stays_none_not_masked_zero(self):
        p=AnchorTarget8Provider(software_fixture=True,fixture_api=self.api)
        out=p(self.obs,self.options,self.anchor)
        self.assertIsNone(out['target8_by_option_sha256']['a'*64]);self.assertFalse(self.calls)
    def test_original_plane_refusal_stays_unknown_not_success_or_padded_geometry(self):
        def refuse(*args,**kwargs):raise ValueError('Original ambiguous same-color components')
        self.api.describe_visible_goal=refuse
        out=self.provider()(self.obs,self.options,self.anchor)
        self.assertIsNone(out['target8_by_option_sha256']['a'*64])
        self.assertEqual(out['target8_evidence_by_option_sha256']['a'*64]['status'],'UNKNOWN')
    def test_raw_onboard_or_fresh_off_grid_refs_are_not_model_anchor_refs(self):
        for field,value in [('WM_anchor_RGB_bytes_sha256','b'*64),('WM_anchor_time_s',.9),
                            ('WM_anchor_calibration_sha256','OTHER')]:
            def other(obs,options,anchor,field=field,value=value):
                out=self.association(obs,options,anchor);out[field]=value;return out
            with self.assertRaises(ValueError):self.provider(other)(self.obs,self.options,self.anchor)
        self.assertFalse(self.calls)
    def test_actual_WM_resized_shape_not_original192x128_or_VLM_image(self):
        self.anchor['rgb']=FixtureArray((128,192,3))
        with self.assertRaises(ValueError):self.provider()(self.obs,self.options,self.anchor)
    def test_other_candidate_or_hidden_body_information_is_not_input(self):
        def hidden(obs,options,anchor):
            out=self.association(obs,options,anchor)
            out['frame_local_ref_by_option_sha256']['a'*64]['private_body_id']=17
            return out
        with self.assertRaises(ValueError):self.provider(hidden)(self.obs,self.options,self.anchor)
        def incomplete(obs,options,anchor):
            out=self.association(obs,options,anchor);out['frame_local_ref_by_option_sha256']={};return out
        with self.assertRaises(ValueError):self.provider(incomplete)(self.obs,self.options,self.anchor)
    def test_source_callback_cannot_mutate_depth_or_timestamp_and_get_a_descriptor(self):
        for field,value in [('depth_m',FixtureArray((64,96),b'CHANGED')),('time_s',.99)]:
            before=self.anchor[field]
            def mutate(obs,options,anchor):
                out=self.association(obs,options,anchor);anchor[field]=value;return out
            with self.assertRaises(ValueError):self.provider(mutate)(self.obs,self.options,self.anchor)
            self.assertIs(self.anchor[field],before)
    def test_no_zero_mask_policy_relaxation_disguised_as_original_geometry(self):
        self.api.geometry_vector=lambda proof:(0,)*8
        with self.assertRaises(ValueError):self.provider()(self.obs,self.options,self.anchor)
    def test_explicit_standoff_is_diagnostic_not_new_unbounded_native_control(self):
        for value in (.49,1.51,float('nan'),True):
            def bad(obs,options,anchor):
                out=self.association(obs,options,anchor)
                out['frame_local_ref_by_option_sha256']['a'*64]['declared_standoff_m']=value;return out
            with self.assertRaises(ValueError):self.provider(bad)(self.obs,self.options,self.anchor)
    def test_query_port_preserves_target_proof_and_fixture_provenance(self):
        frames=[self.anchor,self.anchor,self.anchor]  # Metadata-only fixture, not real causal history.
        class FixtureBuffer:
            def __init__(self):self.frames=frames
            def build(self,q,now,body,**kwargs):
                return 'FIXTURE_BELIEF','FIXTURE_PUBLIC60',dict(query_sha256='b'*64,
                    query_time_s=now,image_time_s=1.,input_file='FIXTURE_NOT_SENSOR')
        state={name:[0.]*size for name,size in [('q',18),('dq',18),('gravity',3),
            ('angular_velocity',3),('linear_velocity',3)]}
        self.obs.value=dict(public_state=state);self.obs.sha256='c'*64
        port=CausalWMQueryPort(FixtureBuffer(),role='CURRENT_ORIGINAL_SENSOR_AND_ISSUED_HISTORY',
            software_fixture=True,target_provider=self.provider())
        result=port(SimpleNamespace(observation=self.obs),self.options)
        self.assertEqual(result['target8_by_option_sha256']['a'*64][7],1.)
        self.assertEqual(result['target8_evidence_by_option_sha256']['a'*64]['status'],
            'CURRENT_VISIBLE_PLANE_NOT_NATIVE_ASSOCIATION_OR_WORLD_POSE')
        self.assertEqual(result['source_role'],'EXPLICIT_SOFTWARE_FIXTURE_NOT_MODEL_TASK_INPUT')
        self.assertFalse(result['live_policy_context_allowed'])
    def test_fixture_api_and_target_provider_cannot_be_promoted_to_production(self):
        with self.assertRaises(ValueError):AnchorTarget8Provider(fixture_api=self.api)
        buffer=SimpleNamespace(_reach_query_software_fixture=False)
        with self.assertRaisesRegex(ValueError,'fixture target descriptor'):
            CausalWMQueryPort(buffer,role='CURRENT_ORIGINAL_SENSOR_AND_ISSUED_HISTORY',target_provider=self.provider())

if __name__=='__main__':unittest.main()
