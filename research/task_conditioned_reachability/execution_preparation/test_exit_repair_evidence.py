from copy import deepcopy
import math
import json
import hashlib
from .observed_handover_analysis import DATA_ROOT,sha
import unittest
from .exit_repair_evidence import repair_snapshot,repair_comparison,distance_to_reference_ball,repair_against_original_option,original_check_feedback
from .test_observed_handover_analysis import normalize,scope,consume_fixture


def projection(distance):
    return dict(role='OFFLINE_LABEL_PROJECTION_NOT_PREDICTION_OR_NATIVE_READY',phase='AFTER_NORMAL_FINISH',
                measured_base_to_original_reference_m=distance,CLIMB_B_original_reference_world_xy_m=[.05,-2.],
                sample_physical_tick=800,source_state_sha256='a'*64)


class ExitRepairTests(unittest.TestCase):
    def test_distance_to_real_native_gate_not_a_new_standoff(self):
        r=repair_snapshot(projection(.65))
        self.assertAlmostEqual(r['conditional_geometric_reference_lower_bound_m'],.49)
        self.assertEqual(r['source_approach_radius_m'],.16)
        self.assertIsNone(r['seconds_lower_bound']);self.assertIsNone(r['actual_next_ready'])

    def test_bound_is_exact_distance_to_snapshot_ball_in_free_space(self):
        radius=.16;target=(.05,-2.)
        for point in ((.7,-2.),(.05,-1.),(.05,-2.)):
            d=math.hypot(point[0]-target[0],point[1]-target[1]);b=repair_snapshot(projection(d))['conditional_geometric_reference_lower_bound_m']
            if d>radius:
                closest=tuple(target[k]+radius*(point[k]-target[k])/d for k in range(2))
                self.assertAlmostEqual(math.hypot(point[0]-closest[0],point[1]-closest[1]),b)
            else:self.assertEqual(b,0.)

    def test_zero_distance_repair_does_not_certify_ready(self):
        r=repair_snapshot(projection(.1),observed_yaw_rad=0.)
        self.assertEqual(r['conditional_geometric_reference_lower_bound_m'],0.)
        self.assertEqual(r['heading_correction_lower_bound_rad'],0.)
        self.assertTrue(r['later_box_motion_can_change_reference'])
        self.assertFalse(r['execution_authorized']);self.assertFalse(r['whole_candidate_infeasible'])

    def test_heading_wrapped_and_not_added_to_distance_or_time(self):
        r=repair_snapshot(projection(.65),observed_yaw_rad=2*math.pi+.4)
        self.assertAlmostEqual(r['heading_correction_lower_bound_rad'],.15)
        self.assertAlmostEqual(r['conditional_geometric_reference_lower_bound_m'],.49)
        self.assertIsNone(r['seconds_lower_bound'])

    def test_no_exit_LABEL_stays_unknown_not_zero(self):
        r=repair_snapshot(None)
        self.assertIsNone(r['conditional_geometric_reference_lower_bound_m'])
        base=consume_fixture(allow_fixture=True)
        result=repair_comparison([base],comparison_scope=scope())
        self.assertEqual(result['measured_repair_candidates'],0)
        self.assertIsNone(result['minimum_conditional_geometric_reference_demand'])

    def test_missing_successor_time_does_not_hide_available_geometric_demand(self):
        records=[]
        for d,dist in ((.2,.65),(.4,.30)):
            row=normalize(d);row['query_to_successor_preparation_end_s']=None;row['receipt_to_successor_preparation_end_s']=None
            row['observed_exit_projection_diagnostic']=projection(dist);records.append(row)
        r=repair_comparison(records,comparison_scope=scope())
        self.assertAlmostEqual(r['conditional_geometric_reference_demand_spread_m'],.35)
        self.assertEqual(r['minimum_conditional_geometric_reference_demand']['distance_m'],.4)
        self.assertFalse(r['full_success_cost_comparable']);self.assertIsNone(r['best_online_action'])
        self.assertFalse(r['claim_of_causal_action_effect'])

    def test_different_goal_or_forecast_phase_is_not_EXIT_geometry(self):
        for field,value in (('phase','PUSH_END'),('role','CAUSAL_PREDICTION')):
            p=projection(.65);p[field]=value
            with self.assertRaises(ValueError):repair_snapshot(p)
        for bad in (float('nan'),True,-1.):
            with self.assertRaises(ValueError):repair_snapshot(projection(bad))

    def test_original_option_goal_can_differ_from_exit_geometry_proxy(self):
        geometric=distance_to_reference_ball([.7,-2.],[.05,-2.],.16)
        actual_bound_goal=distance_to_reference_ball([.7,-2.],[-.1,-2.],.16)
        self.assertAlmostEqual(geometric,.49);self.assertAlmostEqual(actual_bound_goal,.64)
        r=repair_snapshot(projection(.65))
        self.assertIsNone(r['translation_lower_bound_m'])
        self.assertFalse(r['original_selected_CLIMB_goal_xy_available'])
        self.assertIn('UNBOUND',r['status'])

    def test_original_option_source_validation_and_digest_bind_actual_goal(self):
        option=dict(token='EXPLICIT_FUNCTION_FIXTURE_NOT_ACTUAL_OPTION',skill='CLIMB',target_ref='B',
            parameters=[['goal_world_x_m',-.1],['goal_world_y_m',-2.],['surface_height_m',.2]],
            budget_s=.5,native_preconditions_receipt='EXPLICIT_FIXTURE_NO_ACTUAL_NATIVE_RECEIPT',
            attempt_id='',original_push_goal_sha256='',mandatory_protection=False)
        digest=hashlib.sha256(json.dumps(option,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
        state=dict(stage='AFTER_NORMAL_FINISH',frame='WORLD_POSITIVE_X',derived_from_requested_goal=False,
                   robot_base_world_xyz_m=[.7,-2.,.3],private_state_evidence_sha256='a'*64,sample_physical_tick=800)
        r=repair_against_original_option(state,option,checked_option_sha256=digest,purpose='offline_dev_outcome_analysis')
        self.assertAlmostEqual(r['translation_lower_bound_m'],.64)
        self.assertEqual(r['actual_selected_goal_world_xy_m'],[-.1,-2.])
        self.assertIsNone(r['actual_next_ready']);self.assertFalse(r['execution_authorized'])
        changed=deepcopy(option);changed['parameters'][0][1]=.05
        with self.assertRaises(ValueError):repair_against_original_option(state,changed,checked_option_sha256=digest,purpose='offline_dev_outcome_analysis')
        missing=repair_against_original_option(state,None,checked_option_sha256=digest,purpose='offline_dev_outcome_analysis')
        self.assertIsNone(missing['translation_lower_bound_m'])

    def test_existing_Data_original_check_reasons_retained_without_goal_or_full_ready(self):
        sidecar=DATA_ROOT/'EXPLICIT-FIXTURE/sidecar'
        pins={name:sha(sidecar/name) for name in ('identity.json','closure.json','events.jsonl')}
        feedback=original_check_feedback(sidecar,pins)
        self.assertTrue(feedback['ready'])
        self.assertEqual(feedback['check_scope'],'AFTER_FINISH_BEFORE_SUCCESSOR_PREP')
        self.assertIsNone(feedback['selected_goal_world_xy']);self.assertIsNone(feedback['full_next_ready'])
        obs=consume_fixture(allow_fixture=True);obs['original_entry_check_feedback']=feedback
        result=repair_comparison([obs],comparison_scope=scope())
        self.assertEqual(len(result['original_check_patterns']),1)
        self.assertEqual(result['native_option_bound_reference_candidates'],0)

    def test_failed_native_attempt_not_admitted_into_geometry_reference_minimum(self):
        row=normalize(.2,finish=False);row['observed_exit_projection_diagnostic']=projection(.01)
        r=repair_comparison([row],comparison_scope=scope())
        self.assertEqual(r['measured_repair_candidates'],0)
        self.assertIsNone(r['minimum_conditional_geometric_reference_demand'])


if __name__=='__main__':unittest.main()
