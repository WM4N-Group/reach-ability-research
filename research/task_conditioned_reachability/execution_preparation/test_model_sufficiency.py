from copy import deepcopy
import unittest
import json
from pathlib import Path
from .model_sufficiency import analyze,scope_interval_diagnostic,model_dominance,rows_from_raw_batch,declared_producer_sufficiency
from .recorded_v9_diagnostics import load_recorded_owner_sources
from .native_climb_continuation import load_requirements


class SufficiencyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.public,cls.rows=load_recorded_owner_sources();cls.req=load_requirements()

    def test_actual_single06_not_a_three_action_comparison(self):
        r=analyze(self.public,self.rows,self.req)
        self.assertEqual(r['levels']['model_response_comparison']['available_candidates'],[.6])
        self.assertFalse(r['levels']['model_response_comparison']['pairwise_comparison_possible'])
        self.assertFalse(r['levels']['executable_selection']['sufficient'])
        self.assertTrue(r['structural_insufficiency'])

    def fake_three(self):
        rows=deepcopy(self.rows)
        for row in rows:
            row['effect']=dict(status='EXPLICIT_FAKE_PRODUCER_TEST',source_role='SYNTHETIC_TEST',
                               value=dict(motion_mean_anchor_body_m=[row['push_distance_m'],0.,.3,0.,0.,0.],
                                          predicted_elapsed_s=10.+row['push_distance_m']))
        return rows

    def test_complete_raw_means_do_not_promote_success_cost_or_ready(self):
        r=analyze(self.public,self.fake_three(),self.req,allow_synthetic=True)
        self.assertTrue(r['levels']['model_response_comparison']['all_three_available'])
        self.assertEqual(len(r['levels']['model_response_comparison']['pairwise_numeric_response']),3)
        self.assertAlmostEqual(r['levels']['model_response_comparison']['pairwise_numeric_response'][0]['discrete_secant_m_per_m_NOT_continuous_gradient'][0],1.)
        self.assertFalse(r['levels']['successful_time_comparison']['all_three_comparable'])
        self.assertFalse(r['levels']['executable_selection']['sufficient'])
        self.assertFalse(r['more_same_kind_raw_forecasts_alone_can_fix_structure'])

    def test_fake_or_future_not_allowed_as_current_prediction(self):
        with self.assertRaises(ValueError):analyze(self.public,self.fake_three(),self.req)
        rows=deepcopy(self.rows);rows[0]['effect']['source_role']='HISTORICAL_ACTUAL'
        with self.assertRaises(ValueError):analyze(self.public,rows,self.req)

    def test_std_or_hypothetical_radius_not_real_bound(self):
        for kind in ('MODEL_STD','HYPOTHETICAL','SAMPLED_MAX'):
            r=scope_interval_diagnostic(dict(kind=kind),self.req)
            self.assertEqual(r['status'],'UNKNOWN');self.assertFalse(r['physical_exclusion'])

    def test_valid_interval_scopes_direct_only_not_whole_candidate(self):
        b=dict(kind='ANALYTIC_VALID_MODEL_INTERVAL',source_ref='explicit analytic MODEL ONLY bound',
               phase='AFTER_FINISH',frame='WORLD_X_Y',box_front_world_x_m=[1.1,1.1],robot_x_world_m=[.7,.71],robot_y_world_m=[-2.,-2.],lane_y_m=-2.)
        r=scope_interval_diagnostic(b,self.req)
        self.assertIn('DIRECT_CLIMB_B',r['status']);self.assertFalse(r['exclude_PUSH_candidate'])
        self.assertFalse(r['physical_exclusion'])

    def test_later_HIGH_bound_not_used_at_immediate_B_stage(self):
        b=dict(kind='ANALYTIC_VALID_MODEL_INTERVAL',source_ref='explicit bound in model',phase='BEFORE_HIGH_ENTRY',frame='WORLD_X_Y',box_front_world_x_m=[.7,.71],high_front_m=3.5,box_length_m=2.4)
        r=scope_interval_diagnostic(b,self.req)
        self.assertTrue(r['exclude_fixed_HIGH_chain_mode_in_model']);self.assertFalse(r['physical_exclusion'])
        self.assertIn('AT_BOUND_PHASE_ONLY',r['scope'])

    def test_model_dominance_needs_success_cost_bound_and_same_scope(self):
        rows=deepcopy(self.rows)
        for row,c in zip(rows,([1.,2.],[3.,4.],[1.5,3.5])):
            row['dominance_evidence']=dict(kind='ANALYTIC_VALID_MODEL_INTERVAL',source_ref='explicit analytic test MODEL bound',
                query_input_sha256=self.public['input_sha256'],distance_m=row['push_distance_m'],
                success_cost_scope='SUCCESSFUL_CURRENT_AND_SUCCESSOR_PREPARATION',feasible_in_declared_model=True,
                same_constraint_scope_id='synthetic_math_scope_not_robot_guarantee',cost_s=c)
        r=model_dominance(rows,self.public)
        self.assertEqual([(x['dominating_distance_m'],x['dominated_distance_m']) for x in r],[(.2,.4)])
        self.assertFalse(r[0]['actual_physical_dominance'])
        rows[0]['dominance_evidence']['kind']='HYPOTHETICAL'
        self.assertEqual(model_dominance(rows,self.public),[])

    def test_raw_three_candidate_producer_mapping_retains_structural_limit(self):
        payload=dict(query_input_sha256=self.public['input_sha256'],source_role='SYNTHETIC_TEST',
                     candidate_distances_m=[.2,.4,.6],mean=[[.2,0.,0.,0.,0.,0.],[.4,0.,0.,0.,0.,0.],[.6,0.,0.,0.,0.,0.]],elapsed_s=[10.,12.,14.])
        with self.assertRaises(ValueError):rows_from_raw_batch(self.public,self.rows,payload)
        rows=rows_from_raw_batch(self.public,self.rows,payload,allow_synthetic=True)
        r=analyze(self.public,rows,self.req,allow_synthetic=True)
        self.assertTrue(r['levels']['model_response_comparison']['all_three_available'])
        self.assertEqual(len(r['levels']['model_response_comparison']['pairwise_numeric_response']),3)
        self.assertAlmostEqual(r['levels']['model_response_comparison']['pairwise_numeric_response'][0]['discrete_secant_m_per_m_NOT_continuous_gradient'][0],1.)
        self.assertFalse(r['levels']['successful_time_comparison']['all_three_comparable'])
        self.assertFalse(r['levels']['executable_selection']['sufficient'])

    def test_actual_published_producer_spec_cannot_supply_missing_fields(self):
        p=Path('/home/yuanyue/re-nav/GO2-PIPER/docs/common_v9_effect_producer_preparation_v2.json')
        result=declared_producer_sufficiency(json.loads(p.read_text()))
        self.assertFalse(result['substage_durations_available'])
        self.assertFalse(result['calibrated_error_bound_available'])
        self.assertFalse(result['standoff_action_channel'])
        self.assertFalse(result['real_forward_executed'])

    def test_analyzer_does_not_borrow_an_interval_from_another_query(self):
        rows=deepcopy(self.rows)
        rows[0]['valid_model_bound']=dict(kind='ANALYTIC_VALID_MODEL_INTERVAL',source_ref='another model state',query_input_sha256='other',distance_m=.2)
        r=analyze(self.public,rows,self.req)
        self.assertEqual(r['levels']['necessary_condition_exclusion']['scoped_model_conclusions'],[])
        self.assertEqual(r['rows'][0]['necessary_interval_diagnostic']['status'],'UNKNOWN')

    def test_same_state_and_exact_domain_required(self):
        rows=deepcopy(self.rows);rows[0]['query_input_sha256']='another'
        with self.assertRaises(ValueError):analyze(self.public,rows,self.req)
        with self.assertRaises(ValueError):analyze(self.public,self.rows[:2],self.req)


if __name__=='__main__':unittest.main()
