"""Original API seam SOFTWARE checks only. No native scene or robot success."""
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from .complex_intent_planner import ComplexIntentPlanner
from .complex_public_model import NominalState, Decision
from .finite_multistep_planner import Arc
from .successor_aware_choice import digest


class SoftwareModel:
    initial=NominalState((0.,),(0.,0.))
    def key(self,s):return(s.object_x_m,s.robot_reference_xy_m)
    def is_goal(self,s):return s==NominalState((1.,),(2.,0.))
    def arcs(self,s):
        if s.object_x_m==(0.,):
            yield Arc(Decision('PUSH_WITH_NAV_ROUTE','object',(1.,0.),((0.,0.),(.1,0.))),
                      NominalState((1.,),(1.,0.)),1.,'POSSIBLE')
        elif not self.is_goal(s):
            yield Arc(Decision('NAV_AND_ORIGINAL_TERMINAL_STOP',None,(2.,0.),((1.,0.),(2.,0.))),
                      NominalState((1.,),(2.,0.)),1.,'POSSIBLE')


def option(skill,ref,x,token='SOFTWARE_INTENT'):
    params=(('goal_world_x_m',x),('goal_world_y_m',0.),('surface_height_m',0.))
    return SimpleNamespace(skill=skill,target_ref=ref,parameters=params,token=token,
                           sha256=digest(dict(skill=skill,ref=ref,x=x,token=token)))


class SoftwareIntentBatch(SimpleNamespace):
    semantic_intents_only=True


class ComplexIntentSeamTests(unittest.TestCase):
    def setUp(self):
        self.rows=[]
        guard=patch('research.task_conditioned_reachability.execution_preparation.complex_intent_planner._original_intent_batch_type',return_value=SoftwareIntentBatch)
        guard.start();self.addCleanup(guard.stop)
        def journal(row):self.rows.append(row);return'SOFTWARE_JOURNAL:'+str(len(self.rows))
        self.planner=ComplexIntentPlanner(SoftwareModel(),method='multistep',journal=journal,
            terminal_target_ref='remote',selection_factory=lambda batch,opt,ref:opt)
    def select(self,opt):
        return self.planner.select(SoftwareIntentBatch(options=[opt],sha256='b'*64))
    def complete_request(self,opt,status='succeeded'):
        actual=option(opt.skill,opt.target_ref,dict(opt.parameters)['goal_world_x_m'],'SOFTWARE_NATIVE')
        receipt=SimpleNamespace(option_sha256=actual.sha256,status=status,evidence_ref='SOFTWARE_RECEIPT')
        self.planner.observe_intent(opt,actual,receipt,'SOFTWARE_BINDING')
    def test_live_option_matching_and_terminal_not_inferred_from_nominal_plan(self):
        for opt in (option('NAV','route',.1),option('PUSH','object',1.),option('NAV','remote',2.)):
            self.assertIs(self.select(opt),opt);self.assertFalse(self.planner.complete);self.complete_request(opt)
        self.assertFalse(self.planner.complete);self.assertTrue(self.planner.awaiting_terminal)
        with self.assertRaisesRegex(RuntimeError,'terminal/12N'):
            self.select(option('NAV','remote',2.))
        self.planner.confirm_original_task_terminal(evidence_ref='SOFTWARE_ORIGINAL_TERMINAL_VERIFIER')
        self.assertTrue(self.planner.complete)
        self.assertEqual(self.planner.native_success_count,3)
        self.assertEqual(self.planner.decision_count,2)
    def test_missing_source_waypoint_never_silently_skipped_or_created(self):
        with self.assertRaisesRegex(ValueError,'never a private ExecutionBatch'):
            self.planner.select(SimpleNamespace(options=[],sha256='x'*64))
        with self.assertRaisesRegex(ValueError,'semantic option missing'):
            self.select(option('PUSH','object',1.))
        self.assertIsNone(self.planner.pending)
        self.assertEqual(self.planner.nominal_context,SoftwareModel.initial)
    def test_failed_actual_push_does_not_advance_to_forecast_state(self):
        nav=option('NAV','route',.1);self.select(nav);self.complete_request(nav)
        push=option('PUSH','object',1.);self.select(push)
        with self.assertRaisesRegex(RuntimeError,'ORIGINAL_NATIVE_INTERACTION_failed'):
            self.complete_request(push,'failed')
        self.assertEqual(self.planner.nominal_context.object_x_m,(0.,))
        self.assertFalse(self.planner.complete)
    def test_wrong_receipt_identity_and_unregistered_terminal_are_refused(self):
        nav=option('NAV','route',.1);self.select(nav)
        bad=SimpleNamespace(option_sha256='0'*64,status='succeeded',evidence_ref='SOFTWARE_RECEIPT')
        with self.assertRaisesRegex(ValueError,'exact intent/native'):
            self.planner.observe_intent(nav,nav,bad,'SOFTWARE_BINDING')
        with self.assertRaisesRegex(ValueError,'External ORIGINAL'):
            self.planner.confirm_original_task_terminal(evidence_ref='SOFTWARE_FAKE_EARLY_TERMINAL')


if __name__=='__main__':unittest.main()
