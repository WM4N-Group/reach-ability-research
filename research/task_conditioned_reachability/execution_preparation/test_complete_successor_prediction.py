"""Complete-successor semantics regressions; NO physical/learned predictions."""
from dataclasses import replace
import unittest
from .public_preparation_selector import build_problem,choose,CompleteSuccessorEstimate
from .successor_aware_choice import Estimate,Costs,Bounds
from .test_public_preparation_selector import owner_api,reference

IDS=('original','lateral_plus_0p04','lateral_minus_0p04')
MODEL='b'*64


class CompleteSuccessorTests(unittest.TestCase):
    def setUp(self):self.problem=build_problem(reference(),public_candidates=owner_api().public_candidates)

    def provider(self,statuses=('PASS','PASS','PASS'),*,legacy=False,current=('PASS','PASS','PASS'),missing_cost=()):
        calls=[]
        def evaluate(inputs,candidate):
            cid=candidate.candidate_id;i=IDS.index(cid);calls.append(cid)
            seconds=(3.,1.,4.)[i]
            estimate=Estimate(candidate.sha256,inputs.sha256,MODEL,current[i],'CPU_TEST_ONLY',
                Costs(current_composite_remaining=Bounds((1.,.5,2.)[i],(1.,.5,2.)[i]),successor_approach=Bounds(0.,0.),
                      successor_execution_complete=None if cid in missing_cost else Bounds(seconds,seconds)))
            return estimate if legacy else CompleteSuccessorEstimate(estimate,statuses[i],
                source_ref=None if statuses[i]=='UNKNOWN' else 'CPU_PROSPECTIVE_SEMANTICS_FIXTURE_NOT_NATIVE_OR_CALIBRATED')
        return calls,evaluate

    def run_choice(self,evaluator,**kw):return choose(self.problem,evaluator=evaluator,evaluator_sha256=MODEL,**kw)

    def test_cost_only_legacy_result_does_not_imply_complete_successor_feasibility(self):
        calls,evaluate=self.provider(legacy=True);out=self.run_choice(evaluate,on_unknown='abstain')
        self.assertEqual(calls,list(IDS));self.assertEqual(out['reason'],'UNKNOWN_COMPLETE_SUCCESSOR_FEASIBILITY')
        self.assertIsNone(out['optimized_candidate_id']);self.assertIsNone(out['proposed_payload'])
        self.assertEqual(out['methods']['current_greedy']['candidate_id'],'lateral_plus_0p04')
        self.assertEqual(set(out['complete_successor_prediction_status'].values()),{'UNKNOWN'})

    def test_legacy_unknown_may_keep_original_but_not_claim_an_optimized_choice(self):
        _,evaluate=self.provider(legacy=True);out=self.run_choice(evaluate)
        self.assertTrue(out['used_original_default_fallback']);self.assertEqual(out['proposed_payload']['candidate_id'],'original')
        self.assertIsNone(out['optimized_candidate_id']);self.assertFalse(out['execution_authorized'])

    def test_fast_predicted_refusal_not_chosen_by_full_or_converted_to_big_time_penalty(self):
        calls,evaluate=self.provider(('PASS','REFUSED','PASS'));out=self.run_choice(evaluate)
        self.assertEqual(calls,list(IDS));self.assertEqual(out['methods']['current_greedy']['candidate_id'],'lateral_plus_0p04')
        self.assertEqual(out['optimized_candidate_id'],'original')
        self.assertEqual(out['methods']['successor_aware']['objective_upper_s'],4.)
        self.assertEqual(out['known_complete_successor_refusals'],['lateral_plus_0p04'])
        self.assertTrue(out['refusal_not_replaced_by_large_time_penalty'])

    def test_unknown_competitor_not_dropped_to_create_false_full_winner(self):
        _,evaluate=self.provider(('PASS','UNKNOWN','PASS'));out=self.run_choice(evaluate,on_unknown='abstain')
        self.assertIsNone(out['optimized_candidate_id']);self.assertEqual(out['reason'],'UNKNOWN_COMPLETE_SUCCESSOR_FEASIBILITY')
        self.assertEqual(out['shared_evaluation_count'],3)

    def test_all_full_refusals_never_fallback_into_known_refusal(self):
        _,evaluate=self.provider(('REFUSED','REFUSED','REFUSED'));out=self.run_choice(evaluate)
        self.assertIsNone(out['proposed_payload']);self.assertFalse(out['used_original_default_fallback'])
        self.assertEqual(out['reason'],'NO_PREDICTED_COMPLETE_SUCCESSOR_FEASIBLE_CANDIDATE')

    def test_original_full_refusal_blocks_fallback_when_another_branch_unknown(self):
        _,evaluate=self.provider(('REFUSED','UNKNOWN','PASS'));out=self.run_choice(evaluate)
        self.assertIsNone(out['proposed_payload']);self.assertFalse(out['used_original_default_fallback'])

    def test_current_refused_candidates_do_not_require_future_pass_or_cost(self):
        _,evaluate=self.provider(('PASS','PASS','UNKNOWN'),current=('PASS','PASS','REFUSED'),missing_cost=('lateral_minus_0p04',))
        out=self.run_choice(evaluate);self.assertEqual(out['optimized_candidate_id'],'lateral_plus_0p04')
        self.assertEqual(out['shared_evaluation_count'],3)

    def test_full_pass_still_requires_all_completion_cost_heads(self):
        _,evaluate=self.provider(missing_cost=('lateral_plus_0p04',));out=self.run_choice(evaluate,on_unknown='abstain')
        self.assertIsNone(out['optimized_candidate_id']);self.assertEqual(out['reason'],'UNKNOWN_REQUIRED_COST_HEADS')

    def test_ready_or_geometry_only_and_audit_labels_not_complete_successor_prediction(self):
        _,evaluate=self.provider();sample=evaluate(self.problem.inputs,self.problem.domain.candidates[0])
        for scope in ('READY_ONLY','NECESSARY_GEOMETRY_ONLY'):
            with self.assertRaisesRegex(ValueError,'not complete successor'):
                replace(sample,successor_scope=scope)
        with self.assertRaisesRegex(ValueError,'audit outcomes'):replace(sample,role='AUDIT_ONLY')
        with self.assertRaisesRegex(ValueError,'provenance'):replace(sample,source_ref=None)

    def test_full_prediction_cannot_bypass_candidate_input_or_model_binding(self):
        _,evaluate=self.provider()
        def wrong(inputs,candidate):
            row=evaluate(inputs,candidate)
            return replace(row,estimate=replace(row.estimate,input_sha256='c'*64))
        with self.assertRaisesRegex(ValueError,'another candidate/input/model'):
            self.run_choice(wrong)

    def test_current_gate_unknown_still_blocks_choice_even_if_future_prediction_passes(self):
        _,evaluate=self.provider(current=('PASS','UNKNOWN','PASS'))
        out=self.run_choice(evaluate,on_unknown='abstain')
        self.assertIsNone(out['optimized_candidate_id']);self.assertEqual(out['reason'],'UNRESOLVED_COMMON_FEASIBILITY')

    def test_equal_complete_costs_keep_original_tie_break_without_extra_queries(self):
        calls=[]
        def tied(inputs,candidate):
            calls.append(candidate.candidate_id)
            return CompleteSuccessorEstimate(
                Estimate(candidate.sha256,inputs.sha256,MODEL,'PASS','CPU_TEST_ONLY',
                    Costs(current_composite_remaining=Bounds(1.,1.),successor_approach=Bounds(0.,0.),successor_execution_complete=Bounds(1.,1.))),
                'PASS',source_ref='CPU_EQUAL_COST_FIXTURE_NOT_PHYSICAL')
        out=self.run_choice(tied)
        self.assertEqual(out['optimized_candidate_id'],'original');self.assertEqual(len(calls),3)
        self.assertFalse(out['prediction_source_or_calibration_verified_by_this_function'])

    def test_fixed_and_greedy_share_future_outputs_without_getting_extra_model_calls(self):
        calls,evaluate=self.provider(('PASS','REFUSED','PASS'));out=self.run_choice(evaluate,method='current_greedy')
        self.assertEqual(calls,list(IDS));self.assertEqual(out['optimized_candidate_id'],'lateral_plus_0p04')
        self.assertEqual(out['methods']['original_fixed']['candidate_id'],'original')
        self.assertEqual({v['shared_candidate_evaluations'] for v in out['methods'].values()},{3})
        self.assertFalse(out['actual_native_feasibility_or_motor_difference_proven'])


if __name__=='__main__':unittest.main()
