"""Synthetic condition packets only; NOT task samples, future truth or actor runs."""
import copy
import math
import unittest

from preparation_theory import BOUND_KEYS
from wm_reach_interface import (candidate_context, forecast_capabilities,
                                assess_conditions, planner_record, adapt_native_support_plan,
                                native_plan_digest, NATIVE_SUPPORT_SHA256)


def candidate(**updates):
    value = dict(decision_id='synthetic-decision', observation_id='real-anchor-id-fixture',
                 candidate_id='fixture-push-A', executor_id='frozen-executor-fixture',
                 target_id='A', skill='PUSH', horizon_s=.4, output_shift_m=.02,
                 reserve_required=True, postcondition_endpoint='min_horizon_first_PUSH_exit')
    return dict(value, **updates)


def forecast(c=None, **updates):
    c = candidate() if c is None else c
    value = dict(binding=candidate_context(c), contract='terminated_push_v2',
                 forecast_id='synthetic-forecast-not-a-model-output', horizon_s=c['horizon_s'],
                 endpoint=c['postcondition_endpoint'])
    return dict(value, **updates)


def geometry(c=None, phase='preparation', f=None):
    c = candidate() if c is None else c
    binding = dict(candidate_context(c), phase=phase,
                   state_id='synthetic-'+phase+'-state', frame_id='fixed-orthonormal-box',
                   path_id='identified-two-knot-point-path')
    if phase == 'postcondition':
        f = forecast(c) if f is None else f
        binding.update(forecast_id=f['forecast_id'], endpoint=c['postcondition_endpoint'])
    bounds = {k:0. for k in BOUND_KEYS}
    bounds['provenance'] = 'SYNTHETIC EXPLICIT ZERO ERRORS, NOT ROBOT BOUNDS'
    return dict(binding=binding, bounds_binding=copy.deepcopy(binding),
                producer=dict(producer_id='synthetic-external-geometry-only',
                              artifact_id='fixture-not-WM-output-or-measurement',
                              state_semantics='measured_current_state' if phase == 'preparation'
                              else 'externally_declared_nominal_future'),
                knots=[0., 1.], point_trajectories=[dict(point_id='tip', points_m=[[-.29,0.,0.],[-.29,0.,0.]])],
                half_size_m=[.3,.3,.1], axis=[1.,0.,0.], inflation_m=0., bounds=bounds)


def witnesses(g):
    return {k:dict(binding=copy.deepcopy(g['binding']), passed=True,
                   producer_id='synthetic-native-witness-fixture', rule_id=k+'-fixture-rule')
            for k in ('support', 'reserve', 'original_gates')}


def evaluate(c=None, phase='preparation'):
    c = candidate() if c is None else c
    f = forecast(c); g = geometry(c, phase, f)
    return assess_conditions(c, phase=phase, geometry=g, witnesses=witnesses(g), forecast=f)


class ForecastContractTests(unittest.TestCase):
    def test_narrow_prediction_never_provides_geometry(self):
        value = forecast_capabilities(candidate(), forecast())
        self.assertEqual(value['status'], 'MATCHED_prediction_contract_only')
        self.assertFalse(value['geometry_from_heads_available'])
        self.assertFalse(value['uncertainty_is_error_bound'])
        self.assertIn('interpretable_future_geometry', value['missing'])

    def test_partial_deltas_scores_and_latent_do_not_create_geometry(self):
        f = forecast(); f.update(mean=[.1,.2], std=[0.,0.], latent=[0.]*20,
                                boundary_support_probability=1., failure_probability=0.)
        r = assess_conditions(candidate(), phase='postcondition', forecast=f)
        self.assertEqual(r['status'], 'UNKNOWN')
        self.assertIsNone(r['geometry'])
        self.assertFalse(r['execution_authorized'])

    def test_all_forecast_binding_fields_must_match(self):
        c = candidate()
        for field in candidate_context(c):
            f = forecast(c); value = f['binding'][field]
            f['binding'][field] = not value if type(value) is bool else value+1 if isinstance(value,float) else value+'-different'
            with self.subTest(field=field):
                self.assertEqual(forecast_capabilities(c,f)['status'], 'UNKNOWN')

    def test_requested_horizon_not_automatically_validated(self):
        self.assertIn('matching_horizon', forecast_capabilities(candidate(),forecast(horizon_s=.8))['missing'])
        c = candidate(horizon_s=2.)
        self.assertEqual(forecast_capabilities(c,forecast(c))['status'],'UNKNOWN')

    def test_first_exit_is_not_fixed_horizon_continuation(self):
        c = candidate(postcondition_endpoint='fixed_horizon')
        f = forecast(c, endpoint='min_horizon_first_PUSH_exit')
        r = forecast_capabilities(c,f)
        self.assertIn('postcondition_endpoint_matches_predicted_estimand',r['missing'])

    def test_declaring_wrong_endpoint_does_not_rename_contract(self):
        c = candidate(postcondition_endpoint='fixed_horizon')
        r = forecast_capabilities(c,forecast(c))
        self.assertIn('honest_output_endpoint_semantics',r['missing'])

    def test_narrow_push_cannot_forecast_nav_or_climb(self):
        for skill in ('NAV','CLIMB'):
            c = candidate(skill=skill)
            self.assertIn('skill_supported_by_output_contract',forecast_capabilities(c,forecast(c))['missing'])

    def test_visual_M_partial_heads_still_not_full_robot_state(self):
        c = candidate(postcondition_endpoint='macro_boundary')
        f = forecast(c, contract='visual_latent_macro_v1')
        r = forecast_capabilities(c,f)
        self.assertIn('robot_dz_anchor_body',r['heads'])
        self.assertFalse(r['geometry_from_heads_available'])
        self.assertFalse(r['model_quality_or_calibration_verified'])

    def test_unknown_contract_or_missing_forecast(self):
        self.assertEqual(forecast_capabilities(candidate(),None)['missing'],['forecast'])
        self.assertEqual(forecast_capabilities(candidate(),forecast(contract='anything'))['missing'],['known_output_contract'])


class ConditionAdapterTests(unittest.TestCase):
    def test_preparation_can_be_computed_without_WM(self):
        r = evaluate()
        self.assertEqual(r['status'],'CONDITIONAL_declared_conditions_only')
        self.assertAlmostEqual(r['geometry']['required_shift_m'],.01)
        self.assertIsNone(r['chosen_candidate'])
        self.assertFalse(r['prospective_inputs_independently_verified'])
        self.assertFalse(r['actual_feasibility_proven'])

    def test_preparation_missing_geometry_is_unknown(self):
        self.assertEqual(assess_conditions(candidate(),phase='preparation')['status'],'UNKNOWN')

    def test_future_geometry_is_explicit_external_assumption_not_decoded_head(self):
        r = evaluate(phase='postcondition')
        self.assertEqual(r['status'],'CONDITIONAL_declared_conditions_only')
        self.assertFalse(r['forecast_capabilities']['geometry_from_heads_available'])
        self.assertEqual(r['geometry_producer_assumed']['producer_id'],'synthetic-external-geometry-only')
        self.assertFalse(r['dynamic_safety_certified'])

    def test_future_query_rejects_every_context_mismatch(self):
        c = candidate();f = forecast(c)
        for field in ('forecast_id','endpoint','state_id','frame_id','path_id','phase','output_shift_m'):
            g = geometry(c,'postcondition',f);w = witnesses(g)
            # Wrong geometry identity: core fields are caught immediately;
            # state/frame/path must also match bounds and native witnesses.
            value=g['binding'][field]
            g['binding'][field] = value+.001 if isinstance(value,float) else value+'-other'
            r = assess_conditions(c,phase='postcondition',forecast=f,geometry=g,witnesses=w)
            with self.subTest(field=field): self.assertEqual(r['status'],'UNKNOWN')

    def test_measured_final_zero_shift_needs_its_own_context(self):
        # New measured-state query has relative extra shift0, not old plan shift20mm.
        old = geometry();oldw=witnesses(old)
        c = candidate(output_shift_m=0.)
        g = geometry(c);g['binding']['state_id']='different-measured-final-state';g['bounds_binding']=copy.deepcopy(g['binding'])
        g['point_trajectories'][0]['points_m']=[[-.31,0.,0.],[-.31,0.,0.]]
        r = assess_conditions(c,phase='preparation',geometry=g,witnesses=oldw)
        self.assertEqual(r['status'],'UNKNOWN')
        r = assess_conditions(c,phase='preparation',geometry=g,witnesses=witnesses(g))
        self.assertEqual(r['status'],'CONDITIONAL_declared_conditions_only')

    def test_smaller_grid_witness_cannot_be_borrowed_for_final_output(self):
        g=geometry(); w=witnesses(g)
        for witness in w.values():witness['binding']['output_shift_m']=.015
        r=assess_conditions(candidate(),phase='preparation',geometry=g,witnesses=w)
        self.assertEqual(r['status'],'UNKNOWN')
        self.assertEqual(r['witnesses']['support']['status'],'UNKNOWN')

    def test_different_phase_path_state_frame_or_rule_cannot_borrow_witness(self):
        for field in ('phase','path_id','state_id','frame_id'):
            g=geometry();w=witnesses(g);w['support']['binding'][field]='other'
            with self.subTest(field=field):
                r=assess_conditions(candidate(),phase='preparation',geometry=g,witnesses=w)
                self.assertEqual(r['status'],'UNKNOWN')
        w=witnesses(g);del w['support']['rule_id']
        self.assertEqual(assess_conditions(candidate(),phase='preparation',geometry=g,witnesses=w)['status'],'UNKNOWN')

    def test_no_support_monotonicity_assumed(self):
        g=geometry();w=witnesses(g);w['support']['passed']=False
        r=assess_conditions(candidate(),phase='preparation',geometry=g,witnesses=w)
        self.assertEqual(r['status'],'NOT_CERTIFIED_by_declared_conditions')
        self.assertFalse(r['actual_feasibility_proven'])

    def test_reserve_false_and_unknown_not_replaced_by_model_score(self):
        f=forecast();f['boundary_support_probability']=1.
        for passed,status in [(False,'NOT_CERTIFIED_by_declared_conditions'),(None,'UNKNOWN')]:
            g=geometry(phase='postcondition',f=f);w=witnesses(g);w['reserve']['passed']=passed
            with self.subTest(passed=passed):
                self.assertEqual(assess_conditions(candidate(),phase='postcondition',forecast=f,geometry=g,witnesses=w)['status'],status)

    def test_reserve_only_optional_if_explicit_candidate_contract_says_so(self):
        c=candidate(reserve_required=False);g=geometry(c);w=witnesses(g);del w['reserve']
        r=assess_conditions(c,phase='preparation',geometry=g,witnesses=w)
        self.assertEqual(r['status'],'CONDITIONAL_declared_conditions_only')
        self.assertEqual(r['witnesses']['reserve']['status'],'NOT_REQUIRED')
        with self.assertRaises(ValueError):candidate_context(dict(c,reserve_required=None))

    def test_missing_prospective_error_remains_unknown_not_filled_from_std(self):
        g=geometry();g['bounds']['joint_tracking_error_norm_rad']=None
        r=assess_conditions(candidate(),phase='preparation',geometry=g,witnesses=witnesses(g))
        self.assertEqual(r['status'],'UNKNOWN')
        self.assertIsNone(r['geometry']['required_shift_m'])
        self.assertIsNone(r['geometry']['path_budget']['epsilon_m'])

    def test_bounds_cannot_be_borrowed_from_another_domain(self):
        g=geometry();g['bounds_binding']['path_id']='different-path'
        r=assess_conditions(candidate(),phase='preparation',geometry=g,witnesses=witnesses(g))
        self.assertEqual(r['reasons'],['error_bounds_not_bound_to_geometry_query'])

    def test_out_of_cap_is_not_physical_unreachability(self):
        g=geometry();g['point_trajectories'][0]['points_m']=[[.1,0.,0.],[.1,0.,0.]]
        r=assess_conditions(candidate(),phase='preparation',geometry=g,witnesses=witnesses(g))
        self.assertEqual(r['status'],'NOT_CERTIFIED_by_declared_conditions')
        self.assertGreater(r['geometry']['required_shift_m'],.04)
        self.assertFalse(r['actual_feasibility_proven'])

    def test_identified_point_trajectories_must_cover_every_knot(self):
        for kind in ('short','duplicate','empty','bad-point'):
            g=geometry()
            if kind=='short':g['point_trajectories'][0]['points_m'].pop()
            if kind=='duplicate':g['point_trajectories']*=2
            if kind=='empty':g['point_trajectories']=[]
            if kind=='bad-point':g['point_trajectories'][0]['points_m'][0]=[1.,2.]
            with self.subTest(kind=kind),self.assertRaises(ValueError):
                assess_conditions(candidate(),phase='preparation',geometry=g)

    def test_invalid_phase_witness_and_numeric_values_rejected(self):
        with self.assertRaises(ValueError):assess_conditions(candidate(),phase='anything')
        for passed in (1,'true'):
            g=geometry();w=witnesses(g);w['support']['passed']=passed
            with self.assertRaises(ValueError):assess_conditions(candidate(),phase='preparation',geometry=g,witnesses=w)
        for invalid in (True,math.nan,math.inf,-.01,.041):
            with self.subTest(invalid=invalid),self.assertRaises(ValueError):candidate_context(candidate(output_shift_m=invalid))

    def test_external_producer_declaration_is_required_but_not_certification(self):
        g=geometry();g['producer']={}
        self.assertEqual(assess_conditions(candidate(),phase='preparation',geometry=g)['status'],'UNKNOWN')
        g=geometry(phase='postcondition');g['producer']['state_semantics']='measured_current_state'
        self.assertEqual(assess_conditions(candidate(),phase='postcondition',forecast=forecast(),geometry=g)['status'],'UNKNOWN')

    def test_inputs_immutable(self):
        c=candidate();f=forecast();g=geometry();w=witnesses(g);before=copy.deepcopy((c,f,g,w))
        assess_conditions(c,phase='preparation',geometry=g,witnesses=w,forecast=f)
        self.assertEqual((c,f,g,w),before)


class SinglePlannerInputTests(unittest.TestCase):
    def test_no_local_selection_even_for_complete_synthetic_conditions(self):
        c=candidate();r=planner_record(c,evaluate(c),evaluate(c,'postcondition'),nominal_cost_s=12.,cost_source_id='synthetic-total-cost-s')
        self.assertTrue(r['ready_for_conditional_cost_comparison'])
        self.assertFalse(r['selected'])
        self.assertFalse(r['execution_authorized'])
        self.assertFalse(r['task_success_predicted'])
        self.assertEqual(r['selection_owner'],'external_single_high_level_planner')

    def test_unknown_future_or_cost_never_becomes_pass_or_zero_cost(self):
        c=candidate();post=assess_conditions(c,phase='postcondition',forecast=forecast())
        r=planner_record(c,evaluate(),post,nominal_cost_s=0.,cost_source_id='fixture')
        self.assertFalse(r['ready_for_conditional_cost_comparison'])
        self.assertEqual(r['condition_status'],'UNKNOWN')
        r=planner_record(c,evaluate(),evaluate(phase='postcondition'))
        self.assertIsNone(r['nominal_cost_s'])
        self.assertFalse(r['ready_for_conditional_cost_comparison'])
        r=planner_record(c,evaluate(),evaluate(phase='postcondition'),nominal_cost_s=1.)
        self.assertFalse(r['ready_for_conditional_cost_comparison'])

    def test_changed_candidate_contract_cannot_reuse_old_records(self):
        for field, value in [('candidate_id','B'),('executor_id','new'),('observation_id','new'),
                             ('output_shift_m',.03),('reserve_required',False),('horizon_s',.8),
                             ('skill','NAV'),('postcondition_endpoint','fixed_horizon')]:
            with self.subTest(field=field),self.assertRaises(ValueError):
                planner_record(candidate(**{field:value}),evaluate(),evaluate(phase='postcondition'))

    def test_wrong_phase_records_cannot_be_combined(self):
        with self.assertRaises(ValueError):planner_record(candidate(),evaluate(),evaluate())

    def test_comparison_record_retains_failed_gate_not_global_infeasibility(self):
        c=candidate();g=geometry();w=witnesses(g);w['original_gates']['passed']=False
        pre=assess_conditions(c,phase='preparation',geometry=g,witnesses=w)
        r=planner_record(c,pre,evaluate(phase='postcondition'),nominal_cost_s=1.,cost_source_id='fixture')
        self.assertEqual(r['condition_status'],'NOT_CERTIFIED')
        self.assertFalse(r['ready_for_conditional_cost_comparison'])


def native_plan(checked=.015, output=.02, *, reserve_checked=None):
    def row(shift):
        return dict(shift_m=shift, passed=True, max_force_residual=.1, max_moment_residual=.01)
    value=dict(shift_m=output, push_support_shift_m=output, checks=[row(checked)])
    if reserve_checked is not None:value['push_reserve_checks']=[row(reserve_checked)]
    return value


def receipt(plan, binding, **updates):
    return dict(dict(binding=copy.deepcopy(binding), native_source_sha256=NATIVE_SUPPORT_SHA256,
                     raw_plan_sha256=native_plan_digest(plan), consumed_output_field='shift_m'),**updates)


class NativePlanAdapterTests(unittest.TestCase):
    def test_native_plan_without_new_call_receipt_not_silently_bound(self):
        g=geometry();w=adapt_native_support_plan(native_plan(),g['binding'])
        self.assertIsNone(w['support']['passed'])
        self.assertIsNone(w['reserve']['passed'])
        self.assertFalse(w['adapter_metadata']['runtime_call_connected'])

    def test_added_five_mm_does_not_inherit_lower_grid_pass(self):
        g=geometry();p=native_plan();w=adapt_native_support_plan(p,g['binding'],receipt(p,g['binding']))
        self.assertIsNone(w['support']['passed'])
        self.assertEqual(w['support']['reason'],'no_check_at_this_exact_final_output')

    def test_saturated_forty_mm_can_have_same_point_witness(self):
        c=candidate(output_shift_m=.04);g=geometry(c);p=native_plan(.04,.04,reserve_checked=.04)
        w=adapt_native_support_plan(p,g['binding'],receipt(p,g['binding']))
        self.assertIs(w['support']['passed'],True)
        self.assertIs(w['reserve']['passed'],True)
        self.assertIsNone(w['original_gates']['passed'])
        self.assertFalse(w['adapter_metadata']['original_gates_inferred'])

    def test_new_measured_zero_query_has_support_not_unchecked_reserve(self):
        c=candidate(output_shift_m=0.);g=geometry(c);p=native_plan(0.,0.)
        w=adapt_native_support_plan(p,g['binding'],receipt(p,g['binding']))
        self.assertIs(w['support']['passed'],True)
        self.assertIsNone(w['reserve']['passed'])

    def test_wrong_anchor_source_or_raw_plan_hash_stays_unknown(self):
        g=geometry();p=native_plan(.02,.02)
        for field in ('binding','native_source_sha256','raw_plan_sha256','consumed_output_field'):
            r=receipt(p,g['binding']);r[field]={**r[field],'state_id':'other'} if field=='binding' else 'different'
            with self.subTest(field=field):
                w=adapt_native_support_plan(p,g['binding'],r);self.assertIsNone(w['support']['passed'])

    def test_receipt_hash_rejects_plan_mutation(self):
        g=geometry();p=native_plan(.02,.02);r=receipt(p,g['binding'])
        p['checks'][0]['max_force_residual']=.2
        self.assertIsNone(adapt_native_support_plan(p,g['binding'],r)['support']['passed'])

    def test_consumer_field_and_actual_output_must_match(self):
        c=candidate(output_shift_m=.03);g=geometry(c);p=native_plan(.03,.02,reserve_checked=.03);p['push_support_shift_m']=.03
        w=adapt_native_support_plan(p,g['binding'],receipt(p,g['binding']))
        self.assertIsNone(w['support']['passed'])
        w=adapt_native_support_plan(p,g['binding'],receipt(p,g['binding'],consumed_output_field='push_support_shift_m'))
        self.assertIs(w['support']['passed'],True)
        self.assertIs(w['reserve']['passed'],True)

    def test_native_negative_row_not_converted_to_success(self):
        g=geometry();p=native_plan(.02,.02);p['checks'][0].update(passed=False,max_force_residual=.6)
        w=adapt_native_support_plan(p,g['binding'],receipt(p,g['binding']))
        self.assertIs(w['support']['passed'],False)

    def test_contradictory_duplicate_or_nonbool_native_row_rejected(self):
        g=geometry()
        for kind in ('threshold','duplicate','nonbool'):
            p=native_plan(.02,.02)
            if kind=='threshold':p['checks'][0]['max_force_residual']=.6
            if kind=='duplicate':p['checks']*=2
            if kind=='nonbool':p['checks'][0]['passed']=1
            with self.subTest(kind=kind),self.assertRaises(ValueError):
                adapt_native_support_plan(p,g['binding'],receipt(p,g['binding']))

    def test_adapter_integrates_but_other_native_gates_not_fabricated(self):
        c=candidate(output_shift_m=0.,reserve_required=False);g=geometry(c)
        g['point_trajectories'][0]['points_m']=[[-.31,0.,0.],[-.31,0.,0.]]
        p=native_plan(0.,0.);w=adapt_native_support_plan(p,g['binding'],receipt(p,g['binding']))
        r=assess_conditions(c,phase='preparation',geometry=g,witnesses=w)
        self.assertEqual(r['status'],'UNKNOWN')
        # A distinct original-gates producer is required, not an adapter default.
        w['original_gates']=witnesses(g)['original_gates']
        r=assess_conditions(c,phase='preparation',geometry=g,witnesses=w)
        self.assertEqual(r['status'],'CONDITIONAL_declared_conditions_only')


if __name__ == '__main__':
    unittest.main()
