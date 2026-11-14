"""Interface/negative tests only. Toy reversals are NOT physical H1 evidence."""
from dataclasses import replace
import unittest
from .successor_aware_choice import (Task,Candidate,Domain,InputValue,DecisionInput,InputSchema,Bounds,Costs,
    Estimate,ObservedBranch,evaluate_shared,select_all,replay_observed,digest)


PIN='a'*64
MODEL='b'*64


def domain(role='CPU_TEST_ONLY',third=False,schema=None):
    task=Task('declared-common-task',PIN,PIN,'BEFORE_CURRENT_INTENT',schema.sha256 if schema else PIN)
    candidates=(Candidate('original',task.sha256,PIN,'owner:original','original-control','original'),
                Candidate('direct',task.sha256,PIN,'owner:guarded-direct','guarded-direct-control','direct'))
    if third:candidates+=(Candidate('alternative',task.sha256,PIN,'owner:alternative','distinct-alternative-control','owner_registered_alternative'),)
    return Domain(task,candidates,'original','direct',role)


def inputs(d,values=()):return DecisionInput(d.task.sha256,d.task.information_schema_sha256,1.,'REACH_NATIVE_LOCAL',values)


def estimates(d,ip,*,future_unknown=False,gate='PASS'):
    rows={}
    for c in d.candidates:
        costs=Costs(Bounds(0,0),Bounds(2,2) if c.candidate_id=='original' else Bounds(1,1),
                    None if future_unknown else Bounds(1,1),
                    None if future_unknown else Bounds(1,1) if c.candidate_id=='original' else Bounds(4,4))
        rows[c.candidate_id]=Estimate(c.sha256,ip.sha256,MODEL,gate,'CPU_TEST_ONLY',costs)
    return rows


def record(d,cid,current,total,*,current_status='SUCCESS',chain_status='SUCCESS',spent=10.):
    return ObservedBranch(cid,d.task.sha256,'PREDECLARED_PAIR_NOT_HIDDEN_STATE_PROOF',digest({'record':cid}),
                          current_status,chain_status,current,total,spent)


class SuccessorAwareChoiceTests(unittest.TestCase):
    def test_all_four_methods_share_one_candidate_batch(self):
        d=domain();ip=inputs(d);rows=estimates(d,ip);calls=[]
        def evaluate(x,c):calls.append((x.sha256,c.candidate_id));return rows[c.candidate_id]
        batch=evaluate_shared(d,ip,evaluate,evaluator_sha256=MODEL);out=select_all(batch)
        self.assertEqual(len(calls),2)
        self.assertEqual(out['current_greedy']['candidate_id'],'direct')
        self.assertEqual(out['successor_aware']['candidate_id'],'original')
        self.assertEqual(out['original_fixed']['candidate_id'],'original')
        self.assertEqual(out['direct_strong']['candidate_id'],'direct')
        self.assertEqual({r['domain_sha256'] for r in out.values()},{d.sha256})
        self.assertEqual({r['shared_candidate_evaluations'] for r in out.values()},{2})
        self.assertTrue(all(r['execution_authorized'] is False for r in out.values()))

    def test_missing_dynamic_head_not_filled_with_zero(self):
        d=domain();ip=inputs(d);rows=estimates(d,ip,future_unknown=True)
        out=select_all(evaluate_shared(d,ip,lambda x,c:rows[c.candidate_id],evaluator_sha256=MODEL))
        self.assertEqual(out['current_greedy']['candidate_id'],'direct')
        self.assertIsNone(out['successor_aware']['candidate_id'])
        self.assertEqual(out['successor_aware']['status'],'UNKNOWN_REQUIRED_COST_HEADS')

    def test_current_composite_cost_supported_without_optional_split_clock(self):
        c=Costs(successor_approach=Bounds(2,2),successor_execution_complete=Bounds(3,3),current_composite_remaining=Bounds(4,4))
        self.assertEqual(c.upper(False),4);self.assertEqual(c.upper(True),9)
        with self.assertRaisesRegex(ValueError,'double count'):
            Costs(current_operation_remaining=Bounds(1,1),current_composite_remaining=Bounds(4,4))
        self.assertIsNone(Costs(current_composite_remaining=Bounds(4,4)).upper(True))

    def test_unknown_common_gate_is_not_pass(self):
        d=domain();ip=inputs(d);rows=estimates(d,ip,gate='UNKNOWN')
        out=select_all(evaluate_shared(d,ip,lambda x,c:rows[c.candidate_id],evaluator_sha256=MODEL))
        self.assertTrue(all(x['candidate_id'] is None for x in out.values()))
        self.assertTrue(out['successor_aware']['no_choice_is_not_global_task_infeasibility'])

    def test_refused_direct_falls_back_only_from_shared_precheck(self):
        d=domain();ip=inputs(d);rows=estimates(d,ip);rows['direct']=replace(rows['direct'],current_feasibility='REFUSED')
        out=select_all(evaluate_shared(d,ip,lambda x,c:rows[c.candidate_id],evaluator_sha256=MODEL))
        self.assertEqual({x['candidate_id'] for x in out.values()},{'original'})

    def test_audit_values_and_future_times_cannot_enter_online_input(self):
        d=domain()
        for value in (InputValue('posterior',1.,'AUDIT_ONLY',1.,'actual-result'),InputValue('future',1.,'ONLINE_PUBLIC',2.,'future')):
            with self.assertRaises(ValueError):inputs(d,(value,))

    def test_private_runtime_permission_does_not_expose_to_high_level(self):
        d=domain();v=InputValue('current_q',[0.]*6,'ONLINE_NATIVE_LOCAL',1.,'current-native-proprio')
        self.assertEqual(inputs(d,(v,)).audience,'REACH_NATIVE_LOCAL')
        with self.assertRaises(ValueError):DecisionInput(d.task.sha256,PIN,1.,'HIGH_LEVEL_PLANNER',(v,))

    def test_unknown_input_requires_none(self):
        with self.assertRaises(ValueError):InputValue('velocity',0.,'UNKNOWN',1.,'missing')

    def test_observed_record_cannot_be_a_forecast(self):
        d=domain();ip=inputs(d);r=record(d,'original',1.,3.)
        with self.assertRaises(ValueError):evaluate_shared(d,ip,lambda x,c:r,evaluator_sha256=MODEL)
        audit=domain('AUDIT_REPLAY_ONLY')
        with self.assertRaises(ValueError):evaluate_shared(audit,inputs(audit),lambda x,c:None,evaluator_sha256=MODEL)

    def test_reference_schedule_cannot_masquerade_as_completion_cost(self):
        with self.assertRaises(ValueError):Bounds(.6,1.,'ASSIGNED_REFERENCE_SCHEDULE')
        self.assertIsNone(Costs().upper(True))

    def test_source_input_candidate_model_or_task_mismatch_rejected(self):
        d=domain();ip=inputs(d);rows=estimates(d,ip)
        with self.assertRaises(ValueError):evaluate_shared(d,ip,lambda x,c:rows['direct'],evaluator_sha256=MODEL)
        with self.assertRaises(ValueError):evaluate_shared(d,replace(ip,information_schema_sha256='c'*64),lambda x,c:rows[c.candidate_id],evaluator_sha256=MODEL)
        with self.assertRaises(ValueError):Domain(d.task,(d.candidates[0],replace(d.candidates[1],task_sha256='d'*64)),'original','direct')

    def test_aliases_not_counted_as_two_control_choices(self):
        d=domain()
        with self.assertRaises(ValueError):Domain(d.task,(d.candidates[0],replace(d.candidates[1],control_equivalence_key='original-control')),'original','direct')
        with self.assertRaises(ValueError):Domain(d.task,(d.candidates[0],replace(d.candidates[1],execution_profile_sha256='d'*64)),'original','direct')

    def test_common_budget_and_input_mutation_do_not_favor_a_method(self):
        d=domain();ip=inputs(d);rows=estimates(d,ip)
        with self.assertRaises(ValueError):evaluate_shared(d,ip,lambda x,c:rows[c.candidate_id],evaluator_sha256=MODEL,max_evaluations=1)
        v=InputValue('pose',{'x':0.},'ONLINE_PUBLIC',1.,'current')
        ip=inputs(d,(v,))
        def mutate(x,c):
            x.values[0].value['x']=1.
            return Estimate(c.sha256,x.sha256,MODEL,'PASS','CPU_TEST_ONLY',Costs())
        with self.assertRaisesRegex(ValueError,'mutated'):evaluate_shared(d,ip,mutate,evaluator_sha256=MODEL)
        out=select_all(evaluate_shared(d,inputs(d),lambda x,c:rows[c.candidate_id],evaluator_sha256=MODEL,max_wall_s=1e-30))
        self.assertTrue(all(x['status']=='COMMON_EVALUATION_BUDGET_EXCEEDED' for x in out.values()))

    def test_cpu_test_guard_cannot_qualify_production_evaluator(self):
        schema=InputSchema('owner:CPU_TEST_SCHEMA_NOT_REAL_PERMISSION',());d=domain('OWNER_PROSPECTIVE_REGISTERED',schema=schema);ip=inputs(d);rows=estimates(d,ip)
        with self.assertRaisesRegex(ValueError,'Synthetic'):evaluate_shared(d,ip,lambda x,c:rows[c.candidate_id],evaluator_sha256=MODEL,information_schema=schema)

    def test_production_hash_alone_does_not_register_input_permissions(self):
        d=domain('OWNER_PROSPECTIVE_REGISTERED');ip=inputs(d)
        with self.assertRaisesRegex(ValueError,'explicit owner input schema'):
            evaluate_shared(d,ip,lambda x,c:None,evaluator_sha256=MODEL)

    def test_owner_schema_rejects_unregistered_or_relabeled_fields(self):
        schema=InputSchema('owner:DECLARED_SCHEMA_ONLY',(('q','ONLINE_NATIVE_LOCAL',('REACH_NATIVE_LOCAL',)),))
        d=domain(schema=schema)
        for v in (InputValue('other',0.,'ONLINE_PUBLIC',1.,'source'),InputValue('q',0.,'ONLINE_PUBLIC',1.,'source')):
            with self.assertRaises(ValueError):
                evaluate_shared(d,inputs(d,(v,)),lambda x,c:None,evaluator_sha256=MODEL,information_schema=schema)
        with self.assertRaises(ValueError):InputSchema('owner',(('q','ONLINE_NATIVE_LOCAL',('HIGH_LEVEL_PLANNER',)),))

    def test_explicit_schema_allows_current_local_field_not_a_future_prediction(self):
        schema=InputSchema('owner:DECLARED_SCHEMA_ONLY',(('q','ONLINE_NATIVE_LOCAL',('REACH_NATIVE_LOCAL',)),))
        d=domain(schema=schema);ip=inputs(d,(InputValue('q',[0.]*6,'ONLINE_NATIVE_LOCAL',1.,'current-proprio'),))
        rows=estimates(d,ip,future_unknown=True)
        r=select_all(evaluate_shared(d,ip,lambda x,c:rows[c.candidate_id],evaluator_sha256=MODEL,information_schema=schema))
        self.assertIsNone(r['successor_aware']['candidate_id'])

    def test_direct_baseline_absent_not_invented(self):
        d=domain();d=Domain(d.task,d.candidates,'original',None,'CPU_TEST_ONLY');ip=inputs(d);rows=estimates(d,ip)
        r=select_all(evaluate_shared(d,ip,lambda x,c:rows[c.candidate_id],evaluator_sha256=MODEL))
        self.assertEqual(r['direct_strong']['status'],'NOT_APPLICABLE_NO_OWNER_DIRECT_CANDIDATE')

    def test_offline_toy_reversal_is_explicitly_not_deployment_or_H1_experiment(self):
        d=domain();r=replay_observed(d,(record(d,'original',2.,4.),record(d,'direct',1.,6.)))
        self.assertTrue(r['strict_current_vs_chain_cost_rank_reversal'])
        self.assertTrue(r['CPU_examples_are_not_H1_experiments'])
        self.assertEqual(r['role'],'HINDSIGHT_DIAGNOSTIC_NOT_DEPLOYABLE')
        self.assertFalse(r['online_oracle_or_training_allowed'])

    def test_posthoc_penalty_without_rank_reversal_is_not_H1_positive(self):
        d=domain();r=replay_observed(d,(record(d,'original',2.,5.),record(d,'direct',1.,4.5)))
        self.assertEqual(r['choices']['current_greedy'],r['choices']['successor_aware'])
        self.assertFalse(r['strict_current_vs_chain_cost_rank_reversal'])
        self.assertFalse(r['positive_recorded_preference_change'])

    def test_failed_shorter_branch_not_better_chain_and_fixed_direct_not_oracle_repaired(self):
        d=domain();failed=record(d,'direct',1.,None,chain_status='FAILED',spent=1.5)
        r=replay_observed(d,(record(d,'original',2.,4.),failed))
        self.assertEqual(r['choices']['current_greedy'],'direct')
        self.assertEqual(r['choices']['successor_aware'],'original')
        self.assertTrue(r['failure_compatibility_switch']);self.assertEqual(r['choices']['direct_strong'],'direct')
        self.assertEqual(r['observed_attempts'],2);self.assertEqual(r['chain_successes'],1)
        with self.assertRaises(ValueError):record(d,'direct',1.,1.5,chain_status='FAILED',spent=1.5)

    def test_censored_missing_and_unrun_do_not_allow_success_subset_conclusion(self):
        d=domain()
        for kind in ('CENSORED','NOT_RUN','UNKNOWN'):
            r=replay_observed(d,(record(d,'original',2.,4.),record(d,'direct',1.,None,chain_status=kind,spent=None)))
            self.assertIsNone(r['strict_current_vs_chain_cost_rank_reversal'])
            self.assertIsNone(r['choices']['successor_aware'])
            self.assertFalse(r['cost_accounting_complete'])
        r=replay_observed(d,(record(d,'original',2.,4.),record(d,'direct',1.,None)))
        self.assertEqual(r['status'],'INCOMPLETE_BRANCH_COVERAGE_NO_H1_CONCLUSION')
        with self.assertRaises(ValueError):replay_observed(d,(record(d,'original',2.,4.),))

    def test_pairing_and_task_identity_cannot_change_by_method(self):
        d=domain();a=record(d,'original',2.,4.);b=record(d,'direct',1.,3.)
        with self.assertRaises(ValueError):replay_observed(d,(a,replace(b,pairing_ref='other-initial-condition')))
        with self.assertRaises(ValueError):replay_observed(d,(a,replace(b,task_sha256='d'*64)))

    def test_equal_local_cost_is_tie_break_not_strict_rank_reversal(self):
        d=domain();r=replay_observed(d,(record(d,'original',1.,4.),record(d,'direct',1.,3.)))
        self.assertFalse(r['strict_current_vs_chain_cost_rank_reversal'])
        self.assertTrue(r['successor_breaks_current_cost_tie'])


if __name__=='__main__':unittest.main()
