"""Synthetic payload shape/clock/source checks, NOT actual FK or robot outcomes."""
import copy
import unittest
from native_tip_ablation_shadow import evaluate_native_shadow,map_historical_robot_query,PLAN_SHA,PATH_SHA


def fixture():
    stamp=dict(step=1,time_s=.02)
    pose=dict(stamp,position_m=[0,0,0],quaternion_wxyz=[1,0,0,0])
    names=[f'{leg}_{j}_joint' for leg in ['FR','FL','RR','RL'] for j in ['hip','thigh','calf']]+[f'joint{i}' for i in range(1,7)]
    samples=[dict(nominal_index=i,residual_corner_index=j,point_box_m=[-.61 if i<40 else -.65,0,0]) for i in range(41) for j in range(64)]
    return dict(v317_plan_sha256=PLAN_SHA,frozen_waypoints_sha256=PATH_SHA,query_step=1,query_time_s=.02,
        root_pose_world=copy.deepcopy(pose),box_pose_world=copy.deepcopy(pose),
        named_joint_state=dict(stamp,joint_names=names,q_rad=[0]*18,dq_rad_s=[0]*18),
        tip_cloud_box=dict(stamp,frame='box_local',censored_by_yz_gate=False,samples=samples),
        world_x_in_box=[1,0,0],nominal_translation_w=[0,0,0],source_hand_FK_error_m=0.,
        data_role='synthetic_schema_fixture_NOT_attainable_Piper_FK_or_episode')


class NativeTipShadowTests(unittest.TestCase):
    def test_no_default_box_pose_or_cloud_from_historical_robot_only_packet(self):
        r=evaluate_native_shadow({'measured_state':{'q':[0]*18}},'E2')
        self.assertEqual(r['status'],'not_ready')
        self.assertIn('box_pose_world',r['missing'])
        self.assertIn('tip_cloud_box',r['missing'])

    def test_same_caller_arms_are_shadow_only_and_separate_endpoint_from_path(self):
        p=fixture();before=copy.deepcopy(p)
        results=[evaluate_native_shadow(p,a) for a in ['E0','E1','E2','E3']]
        self.assertEqual(results[0]['minimum_shift_m'],0.)
        self.assertEqual(results[1]['minimum_shift_m'],0.)
        self.assertAlmostEqual(results[2]['minimum_shift_m'],.01)
        self.assertEqual(results[2]['minimum_shift_m'],results[3]['minimum_shift_m'])
        for r in results:
            self.assertFalse(r['execution_authorized'])
            self.assertFalse(r['actual_freshness_certified'])
            self.assertIsNone(r['actual_navigation_success'])
        self.assertEqual(p,before)

    def test_mixed_clock_is_rejected_without_freshness_promotion(self):
        p=fixture();p['box_pose_world']['step']=0
        with self.assertRaisesRegex(ValueError,'Mixed'):
            evaluate_native_shadow(p,'E2')

    def test_censored_or_missing_sample_cannot_be_promoted_to_full_cloud(self):
        p=fixture();p['tip_cloud_box']['censored_by_yz_gate']=True
        with self.assertRaisesRegex(ValueError,'uncensored'):
            evaluate_native_shadow(p,'E3')
        p=fixture();p['tip_cloud_box']['samples'].pop()
        with self.assertRaisesRegex(ValueError,'41x64'):
            evaluate_native_shadow(p,'E3')

    def test_wrong_path_or_joint_names_do_not_silently_remap(self):
        p=fixture();p['frozen_waypoints_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'two-point'):
            evaluate_native_shadow(p,'E2')
        p=fixture();p['named_joint_state']['joint_names'][0]='FL_hip_joint'
        with self.assertRaisesRegex(ValueError,'named18'):
            evaluate_native_shadow(p,'E2')

    def test_projection_axis_must_match_recorded_box_frame(self):
        p=fixture();p['world_x_in_box']=[.98,.198997487421324,0]
        with self.assertRaisesRegex(ValueError,'frame mismatch'):
            evaluate_native_shadow(p,'E3')

    def test_explicit_none_translation_is_valid_measured_recheck_not_missing(self):
        p=fixture();p['nominal_translation_w']=None
        r=evaluate_native_shadow(p,'E2')
        self.assertEqual(r['status'],'shadow_request_only')
        self.assertAlmostEqual(r['minimum_shift_m'],.005)

    def test_historical_mapping_preserves_actual_q_and_never_reads_future_box(self):
        obs=dict(schema='actual-historical-navigation-entry-observation-v1',step=4,time_s=.08,
                 measured_state=dict(root_position=[0,0,.279],root_quaternion=[1,0,0,0],q=[-.00001]*18,dq=[0]*18),
                 joint_names=fixture()['named_joint_state']['joint_names'],source_report_sha256='a'*64,
                 source_control_sha256='b'*64,future_push_box_position=[1.1,0,.1])
        before=copy.deepcopy(obs);mapped=map_historical_robot_query(obs)
        self.assertEqual(mapped['named_joint_state']['q_rad'],[-.00001]*18)
        self.assertIsNone(mapped['box_pose_world'])
        r=evaluate_native_shadow(mapped,'E2')
        self.assertEqual(r['status'],'not_ready')
        self.assertIn('box_pose_world',r['missing'])
        self.assertIn('nominal_translation_w',r['missing'])
        self.assertNotIn('root_pose_world',r['missing'])
        self.assertEqual(obs,before)

    def test_original_FK_guard_is_not_a_new_tuned_threshold(self):
        p=fixture();p['source_hand_FK_error_m']=.0003
        with self.assertRaisesRegex(ValueError,'original'):
            evaluate_native_shadow(p,'E2')


if __name__=='__main__':unittest.main()
