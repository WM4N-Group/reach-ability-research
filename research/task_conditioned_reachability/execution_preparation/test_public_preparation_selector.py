"""Deterministic branch tests, not extra seeds/physical H1 or trained models."""
from dataclasses import asdict,replace
import importlib.util
import hashlib
import os
from pathlib import Path
import sys
import unittest

from .public_preparation_selector import (PublicReference,build_problem,choose,
    materialize_fresh_plan,IDS,CompleteSuccessorEstimate)
from .successor_aware_choice import Estimate,Costs,Bounds

# Relocatable software test input; exact original API source, not a fixture port.
# The existing worktree has the owner delivery; the custody repo includes its
# code-only copy. Neither location confers native runtime qualification.
_REPO_API=Path(__file__).resolve().parents[3]/'owner_snapshot/native-prefix-20261114/inputs/AINav/climb_preparation_candidates.py'
_LEGACY_API=Path('/home/yuanyue/main/work/ainav/consumer-deliveries/AINAV-CLIMB-PREPARATION-CANDIDATES-20261113-v1/climb_preparation_candidates.py')
OWNER=Path(os.environ['REACH_AINAV_PUBLIC_API']) if 'REACH_AINAV_PUBLIC_API' in os.environ else (_REPO_API if _REPO_API.is_file() else _LEGACY_API)
OWNER_SHA='1c40a748bd1d93e3684853b60f2dc038e673f019976d60cf33eb8195ff9942d0'


def owner_api():
    name='_Reach_selector_test_actual_AINav_public_API'
    if name in sys.modules:return sys.modules[name]
    if hashlib.sha256(OWNER.read_bytes()).hexdigest()!=OWNER_SHA:
        raise ValueError('Software test requires exact original AINav public API source')
    spec=importlib.util.spec_from_file_location(name,OWNER)
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module
    try:spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(name,None)
        raise
    return module


def reference():return PublicReference('cuboid-2:upper-entry',(.050000000000000044,-2.),0.,True,'PUBLIC_REGISTERED_REFERENCE_CPU_EXAMPLE_NOT_ACTUAL_OBSERVATION')


class PublicSelectorTests(unittest.TestCase):
    def setUp(self):
        self.owner=owner_api();self.problem=build_problem(reference(),public_candidates=self.owner.public_candidates)

    def test_actual_owner_catalogue_and_materializer_no_host_or_binder(self):
        decision=choose(self.problem)
        selection=materialize_fresh_plan(self.problem,decision,selection_from_payload=self.owner.selection_from_payload,phase='FRESH_PREEXECUTION')
        self.assertEqual(asdict(selection),{'target_ref':'cuboid-2:upper-entry','candidate_id':'original'})
        self.assertIsNone(decision['optimized_candidate_id']);self.assertTrue(decision['used_original_default_fallback'])
        self.assertFalse(decision['execution_authorized'])

    def test_known_geometry_has_meters_but_no_fabricated_distance_or_seconds(self):
        out=choose(self.problem)
        self.assertEqual([r['NAV_goal_xy'][1] for r in out['geometry']],[-2.,-1.96,-2.04])
        self.assertEqual(out['geometry'][0]['nominal_reference_displacement_m'],0.)
        for row in out['geometry']:
            self.assertTrue(row['nominal_reference_inside_original_XY_disk'])
            self.assertIsNone(row['current_NAV_travel_distance_m']);self.assertIsNone(row['NAV_composite_completion_s'])
            self.assertEqual(row['native_current_feasibility'],'UNKNOWN')
            self.assertTrue(row['geometry_margin_is_not_tracking_slack_or_cost'])

    def test_strict_abstention_does_not_materialize_or_silently_choose_original(self):
        out=choose(self.problem,on_unknown='abstain')
        self.assertIsNone(out['proposed_payload']);self.assertFalse(out['used_original_default_fallback'])
        self.assertIsNone(materialize_fresh_plan(self.problem,out,selection_from_payload=self.owner.selection_from_payload,phase='FRESH_PREEXECUTION'))

    def test_all_methods_use_three_common_unknown_evaluations(self):
        out=choose(self.problem)
        self.assertEqual(out['shared_evaluation_count'],3)
        self.assertEqual(out['methods']['current_greedy']['status'],'UNRESOLVED_COMMON_FEASIBILITY')
        self.assertEqual(out['methods']['successor_aware']['status'],'UNRESOLVED_COMMON_FEASIBILITY')
        self.assertEqual(out['methods']['direct_strong']['status'],'NOT_APPLICABLE_NO_OWNER_DIRECT_CANDIDATE')
        self.assertTrue(all(v['candidate_id'] is None for v in out['methods'].values()))
        self.assertEqual(len({v['input_sha256'] for v in out['methods'].values()}),1)

    def provider(self,*,current_known=True,full_known=True,original_gate='PASS'):
        calls=[];p=self.problem;model='b'*64
        def evaluate(inputs,candidate):
            calls.append(candidate.candidate_id)
            local={'original':2.,'lateral_plus_0p04':1.,'lateral_minus_0p04':3.}[candidate.candidate_id]
            successor={'original':1.,'lateral_plus_0p04':4.,'lateral_minus_0p04':4.}[candidate.candidate_id]
            costs=Costs(current_composite_remaining=Bounds(local,local) if current_known else None,
                successor_approach=Bounds(0.,0.) if full_known else None,
                successor_execution_complete=Bounds(successor,successor) if full_known else None)
            return CompleteSuccessorEstimate(
                Estimate(candidate.sha256,inputs.sha256,model,original_gate if candidate.candidate_id=='original' else 'PASS','CPU_TEST_ONLY',costs),
                'PASS',source_ref='CPU_CONDITIONAL_FIXTURE_NOT_CALIBRATED_OR_NATIVE_SUCCESS_PREDICTION')
        return calls,evaluate,model

    def test_supplied_conditional_evaluator_controls_objective_not_private_oracle(self):
        calls,evaluate,model=self.provider()
        out=choose(self.problem,evaluator=evaluate,evaluator_sha256=model)
        self.assertEqual(calls,list(IDS))
        self.assertEqual(out['methods']['current_greedy']['candidate_id'],'lateral_plus_0p04')
        self.assertEqual(out['methods']['successor_aware']['candidate_id'],'original')
        self.assertEqual(out['optimized_candidate_id'],'original');self.assertFalse(out['used_original_default_fallback'])
        self.assertFalse(out['full_cost_or_safety_guaranteed']);self.assertFalse(out['actual_native_feasibility_or_motor_difference_proven'])

    def test_current_known_successor_unknown_does_not_let_greedy_impersonate_full(self):
        calls,evaluate,model=self.provider(full_known=False)
        out=choose(self.problem,evaluator=evaluate,evaluator_sha256=model)
        self.assertEqual(out['methods']['current_greedy']['candidate_id'],'lateral_plus_0p04')
        self.assertIsNone(out['methods']['successor_aware']['candidate_id'])
        self.assertEqual(out['reason'],'UNKNOWN_REQUIRED_COST_HEADS')
        self.assertIsNone(out['optimized_candidate_id']);self.assertTrue(out['used_original_default_fallback'])

    def test_current_greedy_is_executable_on_the_same_cost_batch(self):
        calls,evaluate,model=self.provider(full_known=False)
        out=choose(self.problem,method='current_greedy',evaluator=evaluate,evaluator_sha256=model)
        self.assertEqual(calls,list(IDS));self.assertEqual(out['optimized_candidate_id'],'lateral_plus_0p04')
        selection=materialize_fresh_plan(self.problem,out,selection_from_payload=self.owner.selection_from_payload,phase='FRESH_PREEXECUTION')
        self.assertEqual(selection.candidate_id,'lateral_plus_0p04')

    def test_refused_original_is_not_unsafe_unknown_fallback(self):
        _,evaluate,model=self.provider(full_known=False,original_gate='REFUSED')
        out=choose(self.problem,evaluator=evaluate,evaluator_sha256=model)
        self.assertIsNone(out['proposed_payload']);self.assertFalse(out['used_original_default_fallback'])

    def test_budget_overrun_abstains_without_default_install(self):
        _,evaluate,model=self.provider()
        out=choose(self.problem,evaluator=evaluate,evaluator_sha256=model,max_wall_s=1e-30)
        self.assertEqual(out['reason'],'COMMON_EVALUATION_BUDGET_EXCEEDED')
        self.assertIsNone(out['proposed_payload']);self.assertFalse(out['used_original_default_fallback'])

    def test_no_audit_state_or_private_baseXY_in_input_budget(self):
        self.assertEqual(len(self.problem.inputs.values),4)
        self.assertEqual({v.visibility for v in self.problem.inputs.values},{'ONLINE_PUBLIC'})
        self.assertEqual({v.name for v in self.problem.inputs.values},{
            'registered_CLIMB.target_ref','registered_CLIMB.approach_xy',
            'registered_CLIMB.source_surface_height_m','registered_CLIMB.is_declared'})

    def test_non_ground_unregistered_nonfinite_rejected(self):
        for kw in ({'source_surface_height_m':.2},{'registered_climb':False},{'approach_xy':(float('nan'),0.)},{'approach_xy':(True,0.)}):
            with self.assertRaises(ValueError):replace(reference(),**kw)

    def test_owner_domain_expansion_or_changed_CLIMB_reference_rejected(self):
        def extra(**kw):return self.owner.public_candidates(**kw)+({'candidate_id':'extra'},)
        with self.assertRaisesRegex(ValueError,'exactly'):build_problem(reference(),public_candidates=extra)
        def moved(**kw):
            rows=self.owner.public_candidates(**kw);rows[1]['original_approach_xy']=[0.,0.];return rows
        with self.assertRaisesRegex(ValueError,'Only the published'):build_problem(reference(),public_candidates=moved)

    def test_nominal_float_alias_not_mislabeled_as_three_distinct_goals(self):
        r=replace(reference(),approach_xy=(0.,1e308))
        with self.assertRaisesRegex(ValueError,'numerically alias'):
            build_problem(r,public_candidates=self.owner.public_candidates)

    def test_evaluator_input_mutation_rejected(self):
        def mutate(inputs,candidate):
            inputs.values[1].value[0]=1.
            return Estimate(candidate.sha256,inputs.sha256,'b'*64,'UNKNOWN','CPU_TEST_ONLY',Costs())
        with self.assertRaisesRegex(ValueError,'mutated'):choose(self.problem,evaluator=mutate,evaluator_sha256='b'*64)

    def test_no_runtime_hot_install_through_stable_owner_materializer(self):
        out=choose(self.problem)
        with self.assertRaisesRegex(ValueError,'hot installation'):
            materialize_fresh_plan(self.problem,out,selection_from_payload=self.owner.selection_from_payload,phase='LIVE_PREPARE_BOUNDARY')

    def test_payload_force_override_or_wrong_problem_refused(self):
        out=choose(self.problem);out['proposed_payload']['force']=12.
        with self.assertRaisesRegex(ValueError,'no extra controls'):
            materialize_fresh_plan(self.problem,out,selection_from_payload=self.owner.selection_from_payload,phase='FRESH_PREEXECUTION')
        out=choose(self.problem);out['domain_sha256']='a'*64
        with self.assertRaisesRegex(ValueError,'Same public problem'):
            materialize_fresh_plan(self.problem,out,selection_from_payload=self.owner.selection_from_payload,phase='FRESH_PREEXECUTION')


if __name__=='__main__':unittest.main()
