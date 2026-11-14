"""Private complete-state review tests, no physical integration or new episode."""
import ast
from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile
import unittest
import numpy as np
from mujoco_zyh.collect import validate_protocol
from mujoco_zyh.runtime_adapter import construct_runtime
from mujoco_zyh.review_capture import WorldStateRecorder,state_records,load_display_model


def protocol():return json.loads(Path(__file__).with_name('composite_review_protocol_v1.json').read_text())


def minimal_runtime():
    import mujoco
    from types import SimpleNamespace
    model=mujoco.MjModel.from_xml_string('<mujoco><worldbody><body pos="0 0 .5"><freejoint/><geom type="sphere" size=".1" mass="1"/></body></worldbody></mujoco>')
    return SimpleNamespace(sim=SimpleNamespace(model=model,data=mujoco.MjData(model)),step_count=0)


class ReviewProtocol(unittest.TestCase):
    def test_new_review_not_same_root_retry_or_independent_research(self):
        p=validate_protocol(protocol());self.assertTrue(p['full_state_review']);self.assertFalse(p['independent_sample'])
        self.assertNotEqual(p['source_id'],'mujoco-zyh-migration-20261024-v1')
        self.assertEqual(p['source_group'],'mujoco-zyh-340d7d8-native-route-development')
    def test_native_scope_cannot_masquerade_as_recovery_scene(self):
        p=protocol();p.update(scene_recipe='research_threebox',selected_object_id='light',scenario='nav-push')
        with self.assertRaises(ValueError):validate_protocol(p)
    def test_explicit_byte_budget_and_boolean_flag(self):
        for k,v in [('max_review_state_bytes',0),('max_total_episode_bytes',1024),('full_state_review','yes')]:
            p=protocol();p[k]=v
            with self.subTest(k=k),self.assertRaises(ValueError):validate_protocol(p)
    def test_original_protocol_keeps_optional_capture_disabled(self):
        old=json.loads(Path(__file__).with_name('migration_protocol_v1.json').read_text())
        self.assertFalse(validate_protocol(old).get('full_state_review',False))
    def test_state_recorder_never_sets_or_steps_live_state(self):
        p=Path(__file__).with_name('review_capture.py');tree=ast.parse(p.read_text())
        for n in ast.walk(tree):
            if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute):
                self.assertNotIn(n.func.attr,('mj_step','mj_setState','mj_resetData','set_action'))
    def test_offline_render_has_no_integration_or_actor_execution(self):
        p=Path(__file__).with_name('render_scene_review.py');tree=ast.parse(p.read_text())
        for n in ast.walk(tree):
            if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute):
                self.assertNotIn(n.func.attr,('mj_step','mj_resetData','set_action','forward'))


class ZeroStepState(unittest.TestCase):
    def test_actual_state_binary_roundtrip_readonly_and_close(self):
        import mujoco
        p=protocol()
        r=minimal_runtime()
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'review';recorder=WorldStateRecorder(root,r,p)
            before=recorder.actual_state().copy();recorder.capture(0)
            with self.assertRaises(ValueError):recorder.capture(0)
            closure=recorder.close();self.assertEqual(closure['frames'],1)
            self.assertTrue(np.array_equal(before,recorder.actual_state()));self.assertEqual(r.step_count,0)
            rows=list(state_records(root));self.assertEqual(len(rows),1)
            model=load_display_model(root);data=mujoco.MjData(model)
            mujoco.mj_setState(model,data,rows[0][2],mujoco.mjtState.mjSTATE_INTEGRATION)
            mujoco.mj_forward(model,data)
            self.assertEqual(data.time,0.);self.assertTrue(np.array_equal(data.qpos,r.sim.data.qpos))
            self.assertTrue(np.array_equal(data.qvel,r.sim.data.qvel))
            with self.assertRaises(ValueError):recorder.capture(5)
    def test_model_or_chunk_corruption_is_rejected(self):
        p=protocol()
        r=minimal_runtime()
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'review';recorder=WorldStateRecorder(root,r,p);recorder.capture(0);recorder.close()
            metadata=json.loads((root/'metadata.json').read_text())
            with Path(metadata['model_path']).open('ab') as f:f.write(b'not-the-original-model')
            with self.assertRaises(ValueError):list(state_records(root))


if __name__=='__main__':unittest.main()
