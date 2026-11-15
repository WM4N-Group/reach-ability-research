"""EXPLICIT SOFTWARE fixtures. No actual view, NAV, WM, Actor, world or API."""
from dataclasses import replace
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'owner_snapshot/native-prefix-20261114/inputs/AINav/common-source'))
from ainav.contracts import Observation, canonical
from ainav.intents import IntentBatch, SkillIntent
from ainav.native.behavior_authority import BehaviorOption, NativeReceipt
from . import test_v4_methods as fixtures
from .v4_common_nav_prelude import CommonNavObservationPrelude, TARGET_REF, PARAMETERS


class CommonPreludeTests(unittest.TestCase):
    def setUp(self):
        self.source = fixtures.SourceSeamTests(); self.source.setUp(); self.addCleanup(self.source.doCleanups)
        self.journal = fixtures.Journal()
    def batch(self, now=0., *, target=TARGET_REF, parameters=PARAMETERS):
        value=self.source.batch(now).observation.value
        value['declared_map']['anchors'].append(dict(target_ref=TARGET_REF,position_xyz_m=[.22,0.,0.],
            uncertainty_xyz_m=[0.,0.,0.],description='EXPLICIT_SOFTWARE_COMMON_REFERENCE_NOT_NATIVE'))
        obs=Observation.create(value)
        option=SkillIntent('FIXTURE-COMMON-NAV','NAV',target,parameters)
        return IntentBatch('FIXTURE-PRELUDE-'+str(now),obs,(option,),canonical(dict(
            source_ref='EXPLICIT_SOFTWARE',skills=['NAV'],constraints=['Not native admission'])))
    def policy(self, arm='A', **kwargs):
        return CommonNavObservationPrelude(arm=arm,journal=kwargs.get('journal',self.journal),
            enabled=kwargs.get('enabled',True),software_fixture=True)
    def outcome(self, batch, status='succeeded'):
        intent=batch.options[0]
        actual=BehaviorOption('FIXTURE-NATIVE-NAV','NAV',intent.target_ref,intent.parameters,60.,'FIXTURE_JUDGE')
        return actual,NativeReceipt(actual.sha256,1.,status,'a'*64,'FIXTURE_ACTUAL_COMMAND_NOT_A_PREDICTION')
    def test_default_off_and_not_an_arm_method(self):
        p=CommonNavObservationPrelude(arm='B',journal=self.journal,software_fixture=True)
        with self.assertRaises(ValueError):p.select(self.batch())
        self.assertEqual(p.status,'NEW');self.assertFalse(self.journal)
        self.assertIn('NOT_ARM_METHOD',p.decision_source)
    def test_all_five_use_exact_same_common_public_option_and_no_optimizer_event(self):
        batch=self.batch();selections=[]
        for arm in 'ABCDE':selections.append(self.policy(arm).select(batch).option_sha256)
        self.assertEqual(len(set(selections)),1)
        self.assertTrue(all(e['counts_as_arm_method_or_optimizer_decision']is False for e in self.journal))
        self.assertFalse(any(e['event']=='reach_v4_shared_optimizer_choice'for e in self.journal))
    def test_auxiliary_policy_does_not_expose_a_fake_optimizer_treatment_flag(self):
        for arm in 'ABCDE':
            p=self.policy(arm)
            self.assertTrue(p.prelude_enabled)
            self.assertFalse(hasattr(p,'enabled'))  # Original factor gate must not accept this as B/D.
    def test_one_selection_no_repeat_or_replan_while_pending(self):
        p=self.policy();p.select(self.batch())
        with self.assertRaises(ValueError):p.select(self.batch(.1))
        self.assertEqual(len(self.journal),1)
    def test_missing_or_different_candidate_is_unavailable_not_alternate_view(self):
        for batch in (self.batch(target='seen-1'),self.batch(parameters=tuple(sorted(dict(
            goal_world_x_m=.37,goal_world_y_m=0.,surface_height_m=0.).items())))):
            p=self.policy()
            with self.assertRaises(ValueError):p.select(batch)
            self.assertEqual(p.status,'UNAVAILABLE')
    def test_wrong_or_missing_public_anchor_cannot_be_fabricated(self):
        batch=self.batch();value=batch.observation.value
        value['declared_map']['anchors'][-1]['position_xyz_m'][0]=.37
        bad=IntentBatch('BAD',Observation.create(value),batch.options,batch.capability_contract)
        with self.assertRaises(ValueError):self.policy().select(bad)
    def test_only_native_success_allows_fresh_method_boundary_not_WM_ready(self):
        p=self.policy();batch=self.batch();p.select(batch);actual,receipt=self.outcome(batch)
        p.observe_intent(batch.options[0],actual,receipt,'FIXTURE_BINDING')
        self.assertEqual(p.status,'SUCCEEDED')
        result=p.require_fresh_method_observation(self.batch(1.).observation)
        self.assertTrue(result['WM_ready_or_task_success_not_inferred'])
        with self.assertRaises(ValueError):p.select(self.batch(1.))
    def test_wrong_intent_native_option_or_parameters_cannot_complete_prefix(self):
        for kind in ('intent','receipt','parameters'):
            p=self.policy();batch=self.batch();p.select(batch);actual,receipt=self.outcome(batch)
            intent=batch.options[0]
            if kind=='intent':intent=SkillIntent('CLONE','NAV',TARGET_REF,PARAMETERS)
            elif kind=='receipt':receipt=replace(receipt,option_sha256='b'*64)
            else:actual=replace(actual,parameters=tuple(sorted(dict(goal_world_x_m=.37,goal_world_y_m=0.,surface_height_m=0.).items())))
            with self.assertRaises(ValueError):p.observe_intent(intent,actual,receipt,'FIXTURE_BINDING')
            self.assertEqual(p.status,'PENDING')
    def test_all_unsuccessful_outcomes_are_unavailable_not_success_or_retry(self):
        for status in ('failed','hard_stop','budget_expired'):
            p=self.policy();batch=self.batch();p.select(batch);actual,receipt=self.outcome(batch,status)
            p.observe_intent(batch.options[0],actual,receipt,'FIXTURE_BINDING')
            self.assertEqual(p.status,'UNAVAILABLE');self.assertIsNone(p.completed_time_s)
            with self.assertRaises(ValueError):p.select(self.batch(1.))
    def test_receipt_cannot_precede_this_actual_public_selection(self):
        p=self.policy();batch=self.batch(2.);p.select(batch);actual,receipt=self.outcome(batch)
        with self.assertRaises(ValueError):p.observe_intent(batch.options[0],actual,receipt,'FIXTURE_BINDING')
        self.assertEqual(p.status,'PENDING')
    def test_admitted_or_started_is_not_a_success_terminal(self):
        for status in ('admitted','started'):
            p=self.policy();batch=self.batch();p.select(batch);actual,receipt=self.outcome(batch,status)
            with self.assertRaises(ValueError):p.observe_intent(batch.options[0],actual,receipt,'FIXTURE_BINDING')
    def test_judge_rejection_is_not_a_fake_native_failed_receipt(self):
        p=self.policy();batch=self.batch();p.select(batch)
        p.reject_intent(batch.options[0],'FIXTURE_NOT_READY','FIXTURE_JUDGE')
        self.assertEqual(p.status,'UNAVAILABLE')
        self.assertFalse(self.journal[-1]['native_failed_receipt_created'])
    def test_no_method_boundary_before_success_with_old_image_or_past_clock(self):
        p=self.policy();batch=self.batch();p.select(batch)
        with self.assertRaises(ValueError):p.require_fresh_method_observation(self.batch(1.).observation)
        actual,receipt=self.outcome(batch);p.observe_intent(batch.options[0],actual,receipt,'FIXTURE_BINDING')
        for obs in (batch.observation,self.batch(.5).observation):
            with self.assertRaises(ValueError):p.require_fresh_method_observation(obs)
    def test_original_coordinator_auxiliary_phase_can_return_to_same_arm_method(self):
        from ainav.native.intent_execution import IntentExecutionCoordinator
        p=self.policy();batch=self.batch();bound=[]
        def judge(intent,now):
            return 'READY',BehaviorOption('FIXTURE-NATIVE','NAV',intent.target_ref,intent.parameters,60.,'FIXTURE_JUDGE'),'FIXTURE_BIND'
        coordinator=IntentExecutionCoordinator(planner=p,observe=lambda now:self.batch(now).observation,
            catalogue=lambda obs:self.batch(obs.time_s).options,judge=judge,bind=bound.append,
            snapshot=lambda:'EXPLICIT_SOFTWARE_UNCHANGED_WORLD',protection=lambda now:None,
            journal=self.journal,capability_contract=batch.capability_contract)
        native_batch=coordinator(0.);coordinator.select(native_batch)
        actual=native_batch.options[0]
        coordinator.observe(actual,NativeReceipt(actual.sha256,1.,'succeeded','a'*64,'FIXTURE_MOTOR'))
        self.assertEqual(p.status,'SUCCEEDED');self.assertIsNone(coordinator.intent)
        class MethodCalled(Exception):pass
        class SameArmMethod:
            def __init__(self):self.calls=0
            def select(self,batch):self.calls+=1;raise MethodCalled('FIXTURE_NO_API')
        original_arm_method=SameArmMethod()
        p.require_fresh_method_observation(self.batch(1.).observation)
        # This is the source coordinator seam, NOT replacing host.planner or
        # installing this auxiliary policy as the genuine A/B/C/D/E method.
        coordinator.model=original_arm_method
        with self.assertRaises(MethodCalled):coordinator(1.)
        self.assertEqual(original_arm_method.calls,1);self.assertEqual(len(bound),1)

    def test_no_durable_record_means_no_dispatch_or_completed_prefix(self):
        p=self.policy(journal=lambda row: None)
        with self.assertRaises(ValueError):p.select(self.batch())
        self.assertEqual(p.status,'UNAVAILABLE');self.assertIsNone(p.pending)


if __name__=='__main__':unittest.main()
