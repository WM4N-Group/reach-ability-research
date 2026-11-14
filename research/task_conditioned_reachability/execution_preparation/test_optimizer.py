"""Numerical optimizer software tests; synthetic references, NOT robot samples."""
import copy
import itertools
import math
import unittest

from optimizer import GATES, digest, generate_plans, optimize_preparation, synchronized_time


def problem():
    return dict(request_id='synthetic-fixed-intent',observation_id='fixture-current',
                executor_id='SYNTHETIC-no-native-executor',frame_id='fixture-frame',
                cost_contract_id='synthetic-same-second-cost-v1',
                intent=dict(skill='PUSH',target_ref='same-object',push_distance_m=.6,
                            immutable_goal_ref='original-goal-unchanged'),
                successor_requirement=dict(skill='CLIMB',target_ref='same-object',height_change_m=.2),
                support_requirement=dict(minimum_normal_n=12.,original_protections_required=True),
                source_support_ref='same-level',current_base_se2=[0.,0.,0.],current_arm_q=[0.,0.])


def domain():
    return dict(executor_id='SYNTHETIC-no-native-executor',source_id='synthetic-reference-domain',
                base_motion_model_source='synthetic-command-model-not-measured-robot-time',
                arm_rate_model_source='synthetic-rate-model',
                base_translation_speed_m_s=.01,base_yaw_rate_rad_s=1.,arm_rates_rad_s=[1.,1.],
                common_search_overhead_s=None,max_plan_evaluations=12,
                base_goals=[dict(id='base'+str(i),se2=[x,0.,0.],source_support_ref='same-level')
                            for i,x in enumerate([0.,.01,.02])],
                arm_paths=[dict(id='direct',waypoints=[[0.,0.],[1.,0.]]),
                           dict(id='detour',waypoints=[[0.,0.],[0.,.2],[1.,0.]])],
                support_references=[dict(id='nominal',reference=dict(height_m=.33,roll_pitch_rad=[0.,0.]),
                                         source_id='synthetic-nominal',nominal_settle_s=.1),
                                    dict(id='loaded',reference=dict(height_m=.32,roll_pitch_rad=[0.,0.]),
                                         source_id='synthetic-loaded',nominal_settle_s=.3)])


def report(plan, *, valid=True, future_s=1.):
    return dict(plan_sha256=plan['plan_sha256'],problem_sha256=plan['binding']['problem_sha256'],
                producer_id='SYNTHETIC-analytic-constraint-fixture',
                cost_source_id='synthetic-time-equation',cost_contract_id=problem()['cost_contract_id'],
                operation_and_transfer_s=future_s,gates={key:valid for key in GATES})


def slab_intersects(start,end,low,high):
    """Exact line/axis-aligned-box intersection formula for the TOY joint space."""
    left,right=0.,1.
    for a,b,lo,hi in zip(start,end,low,high):
        delta=b-a
        if delta==0:
            if not lo<=a<=hi:return False
        else:
            u,v=(lo-a)/delta,(hi-a)/delta
            left=max(left,min(u,v));right=min(right,max(u,v))
            if left>right:return False
    return left<=right


def analytic_toy_backend(plan):
    """Toy joint-space obstacle, not physical FK or the current robot executor."""
    r=report(plan)
    path=plan['arm']['waypoints']
    intersects=any(slab_intersects(a,b,[.4,-.05],[.6,.05]) for a,b in zip(path,path[1:]))
    r['gates']['preparation_geometry']=(plan['base']['goal_se2'][0]>=.02 or not intersects)
    r['gates']['successor_entry_and_transfer']=plan['support']['id']=='loaded'
    return r


class ScheduleTests(unittest.TestCase):
    def test_piecewise_synchronized_rates_compute_cost_not_input_score(self):
        self.assertEqual(synchronized_time([[0.,0.],[1.,2.],[2.,1.]],[1.,1.]),[2.,1.])
        self.assertEqual(synchronized_time([[0.,0.],[1.,2.]],[2.,4.]),[.5])

    def test_zero_length_segment_not_a_physical_ready_claim(self):
        self.assertEqual(synchronized_time([[1.,2.],[1.,2.]],[1.,1.]),[0.])

    def test_invalid_rate_or_waypoint_rejected(self):
        for rates in ([0.,1.],[-1.,1.],[math.inf,1.],[True,1.]):
            with self.subTest(rates=rates),self.assertRaises(ValueError):synchronized_time([[0.,0.],[1.,1.]],rates)
        with self.assertRaises(ValueError):synchronized_time([[0.],[1.,1.]],[1.,1.])
        with self.assertRaises(ValueError):synchronized_time([[0.,0.]],[1.,1.])

    def test_generate_joint_base_path_support_combinations(self):
        rows=list(generate_plans(problem(),domain()))
        self.assertEqual(len(rows),12)
        self.assertEqual(len({r['plan_sha256'] for r in rows}),12)
        for row in rows:
            self.assertEqual(row['intent'],problem()['intent'])
            self.assertEqual(row['successor_requirement'],problem()['successor_requirement'])
            self.assertEqual(row['support_requirement'],problem()['support_requirement'])

    def test_explicit_yaw_translation_arm_support_schedule(self):
        d=domain();d['base_goals']=[dict(id='rot-trans',se2=[.03,.04,.2],source_support_ref='same-level')]
        row=next(generate_plans(problem(),d))
        self.assertAlmostEqual(row['nominal_preparation_s'],.2+5.+1.+.1)
        self.assertEqual(row['schedule'],('base_yaw','base_translation','arm_reference','support_settle'))

    def test_yaw_is_not_silently_wrapped(self):
        d=domain();d['base_goals'][0]['se2'][2]=2*math.pi
        row=next(generate_plans(problem(),d))
        self.assertAlmostEqual(row['base']['nominal_yaw_s'],2*math.pi)

    def test_plan_hash_changes_with_support_path_base_or_task(self):
        p=problem();d=domain();first=next(generate_plans(p,d))['plan_sha256']
        for field in ('intent','successor_requirement','support_requirement'):
            altered=copy.deepcopy(p);altered[field]['new-bound-condition']=True
            self.assertNotEqual(first,next(generate_plans(altered,d))['plan_sha256'])
        altered=copy.deepcopy(d);altered['support_references'][0]['reference']['height_m']=.31
        self.assertNotEqual(first,next(generate_plans(p,altered))['plan_sha256'])

    def test_no_silent_endpoint_rewrite_or_extra_preparation_choices(self):
        d=domain();d['base_goals']=d['base_goals'][:1];d['arm_paths']=d['arm_paths'][:1];d['support_references']=d['support_references'][:1]
        rows=list(generate_plans(problem(),d));self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['base']['goal_se2'],[0.,0.,0.])

    def test_executor_and_support_seam_mismatch_rejected(self):
        d=domain();d['executor_id']='different'
        with self.assertRaises(ValueError):list(generate_plans(problem(),d))
        d=domain();d['base_goals'][0]['source_support_ref']='different-level'
        with self.assertRaises(ValueError):list(generate_plans(problem(),d))

    def test_arm_path_starts_from_declared_state(self):
        d=domain();d['arm_paths'][0]['waypoints'][0]=[.1,0.]
        with self.assertRaises(ValueError):list(generate_plans(problem(),d))

    def test_empty_duplicate_domains_or_missing_native_model_sources_rejected(self):
        for name in ('base_goals','arm_paths','support_references'):
            d=domain();d[name]=[]
            with self.subTest(name=name),self.assertRaises(ValueError):list(generate_plans(problem(),d))
            d=domain();d[name]*=2
            with self.subTest(name=name),self.assertRaises(ValueError):list(generate_plans(problem(),d))
        d=domain();del d['arm_rate_model_source']
        with self.assertRaises(ValueError):list(generate_plans(problem(),d))

    def test_missing_task_or_non_contact_intent_rejected(self):
        for field in ('intent','successor_requirement','support_requirement'):
            p=problem();p[field]={}
            with self.subTest(field=field),self.assertRaises(ValueError):list(generate_plans(p,domain()))
        p=problem();p['intent']['skill']='choose-another-object'
        with self.assertRaises(ValueError):list(generate_plans(p,domain()))


class OptimizerTests(unittest.TestCase):
    def test_optimizer_changes_base_path_and_support_not_just_veto(self):
        result=optimize_preparation(problem(),domain(),analytic_toy_backend)
        self.assertEqual(result['status'],'CONDITIONAL_finite_domain_optimum')
        chosen=result['selected_plan']
        self.assertEqual(chosen['base']['id'],'base0')
        self.assertEqual(chosen['arm']['id'],'detour')
        self.assertEqual(chosen['support']['id'],'loaded')
        self.assertAlmostEqual(result['nominal_optimal_known_s'],2.5)
        self.assertTrue(result['conditional_optimal_value_proven'])
        self.assertFalse(result['execution_authorized'])
        self.assertFalse(result['outer_semantic_selection_changed'])

    def test_minimum_cost_is_not_first_feasible_or_minimum_retreat(self):
        # Give the most distant goal first: optimizer must still search/compare.
        d=domain();d['base_goals'].reverse()
        result=optimize_preparation(problem(),d,analytic_toy_backend)
        first=next(r for r in result['classified'] if r['status']=='CONDITIONAL_ELIGIBLE')
        self.assertGreater(first['nominal_total_s'],result['nominal_optimal_known_s'])

    def test_joint_optimization_beats_fixed_direct_reference_in_toy_only(self):
        d=domain();d['arm_paths']=d['arm_paths'][:1]
        fixed=optimize_preparation(problem(),d,analytic_toy_backend)
        joint=optimize_preparation(problem(),domain(),analytic_toy_backend)
        self.assertAlmostEqual(fixed['nominal_optimal_known_s'],4.3)
        self.assertAlmostEqual(joint['nominal_optimal_known_s'],2.5)
        self.assertAlmostEqual(fixed['nominal_optimal_known_s']-joint['nominal_optimal_known_s'],1.8)

    def test_independent_bruteforce_reproduces_objective(self):
        # Direct path needs >=.02 retreat; detour needs no retreat; loaded only.
        values=[x/.01+(1. if path=='direct' else 1.2)+.3+1.
                for x,path in itertools.product([0.,.01,.02],['direct','detour'])
                if x>=.02 or path=='detour']
        r=optimize_preparation(problem(),domain(),analytic_toy_backend)
        self.assertAlmostEqual(r['nominal_optimal_known_s'],min(values))

    def test_more_preparation_can_reduce_transition_and_total_cost(self):
        def backend(plan):
            r=report(plan,future_s=2. if plan['support']['id']=='nominal' else .2)
            return r
        r=optimize_preparation(problem(),domain(),backend)
        self.assertEqual(r['selected_plan']['support']['id'],'loaded')
        self.assertAlmostEqual(r['nominal_optimal_known_s'],1.5)

    def test_dearer_unknown_preparation_does_not_block_value_optimum(self):
        def backend(plan):
            r=report(plan,future_s=0.)
            if plan['base']['id']=='base2':r['gates']['successor_entry_and_transfer']=None
            return r
        r=optimize_preparation(problem(),domain(),backend)
        self.assertTrue(r['conditional_optimal_value_proven'])
        self.assertTrue(any(row['status']=='UNKNOWN' for row in r['classified']))

    def test_cheaper_unknown_must_block_optimality_not_be_removed(self):
        def backend(plan):
            r=report(plan)
            if plan['arm']['id']=='direct':r['gates']['preparation_geometry']=None
            return r
        r=optimize_preparation(problem(),domain(),backend)
        self.assertEqual(r['status'],'CONDITIONAL_best_known_preparation')
        self.assertFalse(r['conditional_optimal_value_proven'])
        self.assertTrue(r['unknown_competitor_ids'])
        self.assertIsNone(r['optimal_nominal_value_s'])

    def test_missing_future_cost_keeps_unknown_not_zero(self):
        r=optimize_preparation(problem(),domain(),lambda plan:report(plan,future_s=None))
        self.assertEqual(r['status'],'UNKNOWN')
        self.assertIsNone(r['selected_plan'])
        self.assertTrue(all(row['nominal_total_s'] is None for row in r['classified']))

    def test_same_cost_contract_required(self):
        def backend(plan):
            r=report(plan);r['cost_contract_id']='unrelated-time-metric'
            return r
        r=optimize_preparation(problem(),domain(),backend)
        self.assertEqual(r['status'],'UNKNOWN')
        self.assertIsNone(r['selected_plan'])

    def test_every_full_plan_recomputed_no_monotonic_support_assumption(self):
        seen=[]
        def backend(plan):
            seen.append(plan['plan_sha256']);r=report(plan)
            r['gates']['support_and_required_reserve']=(plan['base']['id']=='base1')
            return r
        r=optimize_preparation(problem(),domain(),backend)
        self.assertEqual(len(set(seen)),12)
        self.assertEqual(r['selected_plan']['base']['id'],'base1')

    def test_wrong_plan_or_problem_receipt_not_accepted(self):
        for key in ('plan_sha256','problem_sha256'):
            def backend(plan):
                r=report(plan);r[key]='different';return r
            with self.subTest(key=key):
                r=optimize_preparation(problem(),domain(),backend)
                self.assertEqual(r['status'],'UNKNOWN')

    def test_gates_exact_original_protections_never_removed(self):
        def backend(plan):
            r=report(plan);del r['gates']['original_protections_preserved'];return r
        with self.assertRaises(ValueError):optimize_preparation(problem(),domain(),backend)
        def backend2(plan):
            r=report(plan);r['gates']['original_protections_preserved']=False;return r
        r=optimize_preparation(problem(),domain(),backend2)
        self.assertEqual(r['status'],'NO_CERTIFIED_DOMAIN_PLAN')
        self.assertFalse(r['mission_success_or_dynamic_safety_proven'])

    def test_probability_not_bool_or_native_witness(self):
        def backend(plan):
            r=report(plan);r['gates']['support_and_required_reserve']=.99;return r
        with self.assertRaises(ValueError):optimize_preparation(problem(),domain(),backend)

    def test_all_failed_only_means_this_domain_has_no_certified_plan(self):
        r=optimize_preparation(problem(),domain(),lambda plan:report(plan,valid=False))
        self.assertEqual(r['status'],'NO_CERTIFIED_DOMAIN_PLAN')
        self.assertEqual(r['reason'],'not_a_global_physical_infeasibility_proof')

    def test_explicit_preparation_budget_avoids_unneeded_queries(self):
        p=problem();p['preparation_budget_s']=0.;calls=[]
        r=optimize_preparation(p,domain(),lambda plan:calls.append(plan))
        self.assertEqual(calls,[])
        self.assertEqual(r['status'],'NO_CERTIFIED_DOMAIN_PLAN')
        self.assertTrue(all(row['status']=='OUTSIDE_DECLARED_PREPARATION_BUDGET' for row in r['classified']))

    def test_immutable_inputs_and_evaluator_cannot_rewrite_generated_plan(self):
        p=problem();d=domain();before=copy.deepcopy((p,d))
        def backend(plan):
            r=report(plan);plan['intent']['target_ref']='illegal-new-target';return r
        r=optimize_preparation(p,d,backend)
        self.assertEqual((p,d),before)
        self.assertEqual(r['selected_plan']['intent']['target_ref'],'same-object')

    def test_common_search_overhead_unknown_not_filled_zero(self):
        r=optimize_preparation(problem(),domain(),analytic_toy_backend)
        self.assertIsNone(r['nominal_with_common_search_s'])
        d=domain();d.update(common_search_overhead_s=.02,search_overhead_source='synthetic-only')
        r=optimize_preparation(problem(),d,analytic_toy_backend)
        self.assertAlmostEqual(r['nominal_with_common_search_s'],2.52)

    def test_no_stale_forecast_reuse_or_automatic_main_execution(self):
        r=optimize_preparation(problem(),domain(),analytic_toy_backend)
        self.assertFalse(r['actual_prediction_reusable_after_preparation'])
        self.assertTrue(r['fresh_actual_observation_and_native_recheck_required'])
        self.assertTrue(r['preparation_can_change_WM_consequence'])
        self.assertFalse(r['runtime_connected'])

    def test_order_does_not_change_nominal_value(self):
        d=domain()
        for key in ('base_goals','arm_paths','support_references'):d[key].reverse()
        a=optimize_preparation(problem(),domain(),analytic_toy_backend)
        b=optimize_preparation(problem(),d,analytic_toy_backend)
        self.assertEqual(a['nominal_optimal_known_s'],b['nominal_optimal_known_s'])

    def test_same_intent_baseline_comparison_reports_nominal_not_real_gain(self):
        p=problem();p['baseline_reference_ids']=['base2','direct','loaded']
        r=optimize_preparation(p,domain(),analytic_toy_backend)
        self.assertAlmostEqual(r['nominal_saving_vs_baseline_s'],1.8)
        self.assertFalse(r['saving_is_measured_task_benefit'])
        self.assertEqual(r['baseline_preparation']['status'],'CONDITIONAL_ELIGIBLE')

    def test_unknown_or_invalid_baseline_not_fabricated(self):
        p=problem();p['baseline_reference_ids']=['base0','direct','nominal']
        r=optimize_preparation(p,domain(),analytic_toy_backend)
        self.assertIsNone(r['nominal_saving_vs_baseline_s'])
        p['baseline_reference_ids']=['nonexistent','direct','nominal']
        with self.assertRaises(ValueError):optimize_preparation(p,domain(),analytic_toy_backend)

    def test_search_budget_is_explicit_not_auto_enlarged_or_silently_truncated(self):
        d=domain();d['max_plan_evaluations']=11;seen=[]
        with self.assertRaises(ValueError):optimize_preparation(problem(),d,lambda plan:seen.append(plan))
        self.assertEqual(seen,[])
        d['max_plan_evaluations']=True
        with self.assertRaises(ValueError):list(generate_plans(problem(),d))

    def test_nonfinite_negative_costs_rejected(self):
        for value in (-1.,math.inf,math.nan,True):
            with self.subTest(value=value),self.assertRaises(ValueError):
                optimize_preparation(problem(),domain(),lambda plan:report(plan,future_s=value))


if __name__=='__main__':
    unittest.main()
