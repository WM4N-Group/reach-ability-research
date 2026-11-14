"""Synthetic diagnostics and tamper tests, never new simulator validation."""
import hashlib,json,math,tempfile,unittest
from pathlib import Path
import numpy as np
from diagnose_stopped_pilot import diagnose_cloud_change,verify_raw,planned_orientation_shadow,scalar_replay

class DiagnosisTests(unittest.TestCase):
    def fixture(self):
        return dict(nominal_indices=[40,40],residual_corner_indices=[0,1],
            tip_cloud_box_m=[[-.62,0,.11],[-.63,.1,.1]],box_size_m=[1.2,1.2,.2],
            forecast_margin_m=.005,world_x_in_box=[1,0,0],box_quaternion_wxyz=[1,0,0,0],
            root_quaternion_wxyz=[1,0,0,0],root_position_w=[0,0,0],box_position_w=[1,0,0],nominal_translation_w=[0,0,0])
    def test_identity_point_reconstruction_has_no_pose_change(self):
        q=self.fixture();d=diagnose_cloud_change(q,q)
        self.assertAlmostEqual(d['rigid_pose_reconstruction_max_residual_m'],0)
        self.assertEqual(d['observed_axiswise_displacement_m'],[0,0,0])
        self.assertIn('EX_POST',d['ex_post_pose_tube_result']['usage'])
        self.assertFalse(d['ex_post_pose_tube_result']['prospective_bound_verified'])
    def test_rotated_point_reconstruction_without_FK(self):
        q=self.fixture();m=json.loads(json.dumps(q));angle=.02
        m['root_quaternion_wxyz']=[math.cos(angle/2),0,math.sin(angle/2),0]
        rotation=np.array([[math.cos(angle),0,math.sin(angle)],[0,1,0],[-math.sin(angle),0,math.cos(angle)]])
        points=np.array(q['tip_cloud_box_m'])+[1,0,0]
        m['tip_cloud_box_m']=(points@rotation.T-[1,0,0]).tolist()
        d=diagnose_cloud_change(q,m)
        self.assertLess(d['rigid_pose_reconstruction_max_residual_m'],1e-12)
        self.assertAlmostEqual(d['root_rotation_change_rad'],angle)
    def test_reference_shadow_uses_same_query_not_future_state(self):
        q=dict(self.fixture(),step=10,time_s=.2)
        row=dict(step=10,time_s=.2,stance_orientation_target=[1,0,0,0])
        value=planned_orientation_shadow(q,row)
        self.assertFalse(value['used_future_measured_pose_or_cloud']);self.assertFalse(value['runtime_control_authority'])
        for arm,expected in scalar_replay(q)['requests'].items():
            self.assertAlmostEqual(value['candidate_requests']['requests'][arm]['request_m'],expected['request_m'])
        self.assertIn('UNKNOWN',value['pose_error_bound_status'])
        row['step']=11
        with self.assertRaisesRegex(ValueError,'same query'):planned_orientation_shadow(q,row)
    def test_raw_evidence_tamper_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'source';source.mkdir()
            helper=Path(__file__).with_name('runtime_tip_envelope.py').read_bytes()
            (source/'box_approach_standoff.py').write_bytes(helper)
            h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
            (source/'manifest.json').write_text(json.dumps({'files':{'box_approach_standoff.py':h(source/'box_approach_standoff.py')}}))
            out=root/'runs/case';out.mkdir(parents=True)
            entry={'output_name':'case'}
            for name,key in [('report.json','report_sha256'),('control.jsonl','control_sha256'),('entry_geometry.jsonl','geometry_sha256')]:
                (out/name).write_text('{}\n');entry[key]=h(out/name)
            ledger={'source_manifest_sha256':h(source/'manifest.json'),'entries':[entry]}
            verify_raw(root,ledger,source)
            (out/'entry_geometry.jsonl').write_text('{"tampered":true}\n')
            with self.assertRaisesRegex(ValueError,'hash mismatch'):verify_raw(root,ledger,source)
    def test_changed_frozen_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp);(source/'manifest.json').write_text('{"files":{}}')
            with self.assertRaisesRegex(ValueError,'manifest mismatch'):verify_raw(source,{'source_manifest_sha256':'wrong'},source)

if __name__=='__main__':unittest.main()
