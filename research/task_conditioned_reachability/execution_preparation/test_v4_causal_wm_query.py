"""Explicit metadata/dispatch fixtures; no Torch/model/history data loaded."""
import copy
import json
from pathlib import Path
import shutil
import tempfile
from types import SimpleNamespace
import unittest
from .v4_causal_wm_query import checked_query_definitions,CausalWMQueryPort
ROOT=Path(__file__).resolve().parents[3]
SOURCE=ROOT/'inference_source/original_behavior7a6_query'
class FixtureBuffer:
    def __init__(self):self.calls=[]
    def actual_motor(self,*a,**kw):self.calls.append(('motor',a,kw))
    def visual(self,p):self.calls.append(('visual',p))
    def build(self,q,now,body,**kw):
        self.calls.append(('build',q,now,body,kw))
        return 'EXPLICIT_NOT_REAL_BELIEF','EXPLICIT_NOT_REAL_PUBLIC60',dict(query_sha256='a'*64,query_time_s=now,image_time_s=now-.015,input_file='EXPLICIT_FIXTURE',observed_skill='NAV')
class CausalQueryPortTests(unittest.TestCase):
    def test_only_exact_original_three_definitions(self):
        self.assertEqual(set(checked_query_definitions(SOURCE)),{'BehaviorQueryBuffer','filter_full_native','resize_packet'})
    def test_changed_definition_refused_not_training_module_exec(self):
        with tempfile.TemporaryDirectory()as d:
            dest=Path(d)/'source';shutil.copytree(SOURCE,dest)
            with(dest/'filter_full_native.py').open('ab')as f:f.write(b'\n# CHANGED\n')
            with self.assertRaises(ValueError):checked_query_definitions(dest)
    def test_audit_context_remains_rejected_live_role(self):
        port=CausalWMQueryPort(FixtureBuffer(),role='CLOSED_RECORDED_INPUT_AUDIT_NOT_LIVE',software_fixture=True)
        c=port.build('fixture',public_observation=SimpleNamespace(time_s=1.,sha256='b'*64),body45=[],body_observed_time_s=1.,target8_by_option_sha256={})
        self.assertFalse(c['live_policy_context_allowed']);self.assertNotEqual(c['source_role'],'CURRENT_ORIGINAL_SENSOR_AND_ISSUED_HISTORY')
    def test_prospective_skill_cannot_replace_explicit_actual_issued_owner(self):
        buf=FixtureBuffer();port=CausalWMQueryPort(buf,role='CURRENT_ORIGINAL_SENSOR_AND_ISSUED_HISTORY',software_fixture=True)
        port.on_issued([1.]*18,1,.005,actual_issued_skill='NAV',native_owner_id='ACTUAL_SOURCE_OWNER')
        self.assertEqual(buf.calls[0][2],dict(issued_skill='NAV',native_owner_id='ACTUAL_SOURCE_OWNER'))
    def test_body_must_match_original_public_clock(self):
        buf=FixtureBuffer();port=CausalWMQueryPort(buf,role='CLOSED_RECORDED_INPUT_AUDIT_NOT_LIVE',software_fixture=True)
        with self.assertRaises(ValueError):port.build('bad',public_observation=SimpleNamespace(time_s=1.,sha256='a'*64),body45=[],body_observed_time_s=2.,target8_by_option_sha256={})
        self.assertFalse(buf.calls)
    def test_unknown_targets_not_fabricated(self):
        port=CausalWMQueryPort(FixtureBuffer(),role='CURRENT_ORIGINAL_SENSOR_AND_ISSUED_HISTORY',software_fixture=True)
        c=port.build('fixture',public_observation=SimpleNamespace(time_s=1.,sha256='b'*64),body45=[],body_observed_time_s=1.,target8_by_option_sha256={'c'*64:None})
        self.assertIsNone(c['target8_by_option_sha256']['c'*64])
    def test_original_builder_gets_same_geometry_binding_not_recomputed(self):
        buf=FixtureBuffer();port=CausalWMQueryPort(buf,role='CURRENT_ORIGINAL_SENSOR_AND_ISSUED_HISTORY',software_fixture=True)
        port.build('f',public_observation=SimpleNamespace(time_s=1.,sha256='a'*64),body45=[],body_observed_time_s=1.,target8_by_option_sha256={},observed_geometry8=None)
        self.assertIsNone(buf.calls[-1][-1]['observed_geometry8'])
    def test_production_refuses_fixture_even_with_live_label(self):
        with self.assertRaises(ValueError):CausalWMQueryPort(FixtureBuffer(),role='CURRENT_ORIGINAL_SENSOR_AND_ISSUED_HISTORY')
    def test_fixture_mode_cannot_emit_live_context(self):
        p=CausalWMQueryPort(FixtureBuffer(),role='CURRENT_ORIGINAL_SENSOR_AND_ISSUED_HISTORY',software_fixture=True)
        c=p.build('f',public_observation=SimpleNamespace(time_s=1.,sha256='a'*64),body45=[],body_observed_time_s=1.,target8_by_option_sha256={})
        self.assertEqual(c['source_role'],'EXPLICIT_SOFTWARE_FIXTURE_NOT_MODEL_TASK_INPUT')
        self.assertFalse(c['live_policy_context_allowed'])
    def test_unknown_provenance_not_promoted(self):
        with self.assertRaises(ValueError):CausalWMQueryPort(FixtureBuffer(),role='REBRAND_HISTORICAL_DEV_AS_CURRENT')
if __name__=='__main__':unittest.main()
