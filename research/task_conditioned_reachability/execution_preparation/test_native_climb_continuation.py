from copy import deepcopy
import unittest
from .native_climb_continuation import load_requirements,assess_climb_b,assess_later_B_HIGH,phase_cost,STAGE_BOUNDARIES,adapt_recorded_rows,select_native_assessments,consume_wm_phase_v2
from .recorded_v9_diagnostics import load_recorded_owner_sources


class NativeClimbTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.req=load_requirements();cls.public,cls.rows=load_recorded_owner_sources()

    def state(self):
        return dict(box_front_world_x_m=1.1,robot_xy_world_m=[.05,-2.],lane_y_m=-2.,
                    heading_error_rad=0.,linear_speed_m_s=.02,tilt_rad=.01,source_support_height_m=0.,
                    model_source_normal_loads_N=[5.,5.,5.,5.],max_absolute_arm_q_rad=.1,
                    model_common_loaded_top_ground_support=True,
                    phase='AFTER_REGISTERED_SUCCESSOR_PREPARATION_BEFORE_CLIMB_ENTRY_CHECK')

    def costs(self):
        return [dict(name=k,start_event=a,end_event=b,duration_s=d,clock_origin_id='synthetic_clock',
                     observation_ref='fixture',distance_m=.4,source_role='synthetic_test')
                for (k,(a,b)),d in zip(STAGE_BOUNDARIES.items(),(2.,10.,3.))]

    def test_source_bound_real_constants(self):
        r=self.req;self.assertEqual(r['approach_standoff_m'],1.05)
        self.assertEqual(r['limits']['approach_radius_m'],.16)
        self.assertEqual(r['source_loaded_force_strict_gt_N'],4.)
        self.assertEqual(r['later_B_HIGH_docking_tolerance_m'],.01)
        self.assertIsNone(r['free_exit_separation_threshold_m'])

    def test_immediate_B_is_ground_source_not_B_HIGH(self):
        state=self.state();state['box_front_world_x_m']=.7;state['robot_xy_world_m']=[-.35,-2.]
        r=assess_climb_b(state,self.req)
        self.assertFalse(r['B_HIGH_docking_required_for_this_immediate_successor'])
        self.assertEqual(r['necessary_margins']['approach_radius_m']['status'],'PASS_NOMINAL_NECESSARY')
        self.assertFalse(r['whole_candidate_infeasible'])

    def test_load_threshold_strict_not_greater_equal(self):
        state=self.state();state['model_source_normal_loads_N']=[4.,5.,5.,5.]
        r=assess_climb_b(state,self.req)
        self.assertEqual(r['necessary_margins']['four_source_loads_N']['status'],'FAIL_DIRECT_NOMINAL_NECESSARY')

    def test_arm_pose_not_owner_or_Actor_gate(self):
        r=assess_climb_b(self.state(),self.req)
        self.assertIsNone(r['native_entry_ready']);self.assertIsNone(r['actual_next_ready'])
        self.assertTrue(r['original_ClimbEntry_and_Actor_gate_still_required'])
        self.assertFalse(r['full_chain_feasibility_proven'])

    def test_approach_fail_can_need_NAV_not_candidate_global_failure(self):
        state=self.state();state['robot_xy_world_m']=[.7,-2.]
        r=assess_climb_b(state,self.req)
        self.assertTrue(r['direct_handover_needs_NAV_preparation_if_this_point_were_Finish_state'])
        self.assertFalse(r['whole_candidate_infeasible'])

    def test_exit_standoff_never_assumed_from_push_standoff(self):
        r=assess_climb_b(dict(box_front_world_x_m=1.1,lane_y_m=-2.),self.req)
        self.assertAlmostEqual(r['nominal_approach_world_xy_m'][0],.05)
        self.assertIsNone(r['nominal_distance_to_approach_m'])

    def test_signed_seam_rejects_excess_overlap_as_well_as_gap(self):
        self.assertEqual(assess_later_B_HIGH(1.1,2.4,3.5,self.req)['status'],'PASS_POINT_GEOMETRY_ONLY')
        for front in (.7,1.158744682):
            r=assess_later_B_HIGH(front,2.4,3.5,self.req)
            self.assertLess(r['symmetric_docking_margin_m'],0.)
            self.assertTrue(r['inference_is_not_actual_rejection'])

    def test_real_three_candidate_table_and_forecast_need_prep(self):
        r=adapt_recorded_rows(self.public,self.rows,self.req)
        approaches=[x['immediate_requested_CLIMB_B']['nominal_approach_world_xy_m'][0] for x in r['rows']]
        for a,b in zip(approaches,(-.35,-.15,.05)):self.assertAlmostEqual(a,b)
        m=r['rows'][2]['recorded_model_diagnostic'];self.assertGreater(m['nominal_distance_to_approach_m'],.56)
        self.assertFalse(m['phase_matched_for_entry']);self.assertFalse(r['rows'][2]['selector_eligible'])
        self.assertEqual(r['selection_status'],'UNKNOWN');self.assertEqual(r['real_physical_exclusions'],[])

    def test_source_height_matters_but_missing_values_unknown(self):
        state=self.state();state['source_support_height_m']=.2
        self.assertEqual(assess_climb_b(state,self.req)['necessary_margins']['source_height_m']['status'],'FAIL_DIRECT_NOMINAL_NECESSARY')
        self.assertIn('four_source_loads_N',assess_climb_b({},self.req)['future_gate_values_missing'])

    def test_nonoverlapping_stage_cost_numeric(self):
        r=phase_cost(self.costs(),observation_ref='fixture',distance=.4,allow_synthetic=True)
        self.assertEqual(r['total_s'],15.)

    def test_elapsed_option_purpose_not_native_operation(self):
        rows=self.costs();rows[1]['start_event']='QUERY';rows[1]['end_event']='OPTION_PURPOSE_TERMINAL'
        rows[1]['duration_s']=20.678873062
        r=phase_cost(rows,observation_ref='fixture',distance=.4,allow_synthetic=True)
        self.assertIsNone(r['total_s']);self.assertIn('scope_mismatch',r['reason'])

    def test_Finish_double_count_rejected(self):
        rows=self.costs();rows.append(dict(rows[1],name='extra_Finish'))
        self.assertIsNone(phase_cost(rows,observation_ref='fixture',distance=.4,allow_synthetic=True)['total_s'])

    def test_clock_candidate_and_roles_not_silently_converted(self):
        for key,value in (('clock_origin_id','other'),('distance_m',.6),('source_role','observed_historical')):
            rows=self.costs();rows[1][key]=value
            self.assertIsNone(phase_cost(rows,observation_ref='fixture',distance=.4,allow_synthetic=True)['total_s'])
        self.assertIsNone(phase_cost(self.costs(),observation_ref='fixture',distance=.4)['total_s'])

    def test_native_profile_adapter_reduces_numeric_cost_not_an_empty_callback(self):
        assessment=assess_climb_b(self.state(),self.req)
        self.assertTrue(assessment['eligible_in_declared_state_model'])
        rows=[dict(distance_m=d,prepared_successor_state_model=assessment,
                   phase_cost=dict(status='COMPLETE_DECLARED_PHASE_COST_MODEL_ONLY',total_s=c))
              for d,c in ((.2,5.),(.4,3.),(.6,8.))]
        r=select_native_assessments(rows)
        self.assertEqual(r['best_candidate']['distance_m'],.4)
        self.assertFalse(r['execution_authorized']);self.assertIsNone(r['actual_next_ready'])
        rows[0]['prepared_successor_state_model']=None
        self.assertIn('SUBSET',select_native_assessments(rows)['selection_status'])

    def test_model_load_numbers_alone_do_not_prove_top_source(self):
        state=self.state();state['model_common_loaded_top_ground_support']=None
        self.assertFalse(assess_climb_b(state,self.req)['eligible_in_declared_state_model'])

    def test_combined_query_to_success_span_not_forced_into_native_duration(self):
        rows=self.costs();combined=dict(rows[0],name='current_preparation_and_push_including_original_Finish',
                                     end_event='PUSH_NATIVE_SUCCEEDED_AFTER_FINISH',duration_s=12.)
        r=phase_cost([combined,rows[2]],observation_ref='fixture',distance=.4,allow_synthetic=True)
        self.assertEqual(r['total_s'],15.)
        self.assertFalse(r['native_elapsed_inferred'])
        r=phase_cost([combined,rows[0],rows[2]],observation_ref='fixture',distance=.4,allow_synthetic=True)
        self.assertIsNone(r['total_s']);self.assertIn('overlapping',r['reason'])

    def test_partial_phase_cost_retained_without_ranking_total(self):
        r=phase_cost(self.costs()[:2],observation_ref='fixture',distance=.4,allow_synthetic=True)
        self.assertEqual(r['partial_model_cost_s'],12.)
        self.assertIsNone(r['total_s']);self.assertEqual(r['missing_terms'],['successor_preparation'])

    def test_cost_comparison_does_not_require_fabricating_actual_next_ready(self):
        rows=[dict(distance_m=d,prepared_successor_state_model=None,
                   phase_cost=dict(status='COMPLETE_DECLARED_PHASE_COST_MODEL_ONLY',total_s=c))
              for d,c in ((.2,5.),(.4,3.),(.6,8.))]
        r=select_native_assessments(rows)
        self.assertIsNone(r['best_candidate']);self.assertEqual(r['selection_status'],'UNKNOWN')
        self.assertEqual(r['cost_only_diagnostic_best']['distance_m'],.4)
        self.assertIsNone(r['actual_next_ready']);self.assertFalse(r['execution_authorized'])

    def test_new_WM_event_clock_success_or_failure_not_success_cost(self):
        r=consume_wm_phase_v2(self.public,self.rows)
        span=r['recorded_event_span']
        self.assertTrue(span['terminal_head_is_not_conditioned_on_success'])
        self.assertEqual(span['intended_end_event'],'NATIVE_OPTION_TERMINAL_EVENT_SUCCESS_OR_FAILURE')
        self.assertAlmostEqual(span['predicted_event_time_s'],72.3538730621)
        self.assertIsNone(r['owner_cost_admissibility']['cost_component'])
        self.assertIsNone(r['successful_phase_total_s'])
        self.assertFalse(r['actual_outcome_ledger_opened'])

    def test_new_WM_clock_not_borrowed_for_new_observation(self):
        p=deepcopy(self.public);p['input_sha256']='different'
        with self.assertRaises(ValueError):consume_wm_phase_v2(p,self.rows)

    def test_missing_duration_not_zero(self):
        rows=self.costs();rows[1]['duration_s']=None
        self.assertIsNone(phase_cost(rows,observation_ref='fixture',distance=.4,allow_synthetic=True)['total_s'])


if __name__=='__main__':unittest.main()
