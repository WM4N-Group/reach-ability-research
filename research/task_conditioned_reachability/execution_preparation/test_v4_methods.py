"""EXPLICIT software fixtures only: no real VLM/WM, Runtime, native or model fit."""
import copy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest

ORIGINAL=Path(__file__).resolve().parents[3]/'owner_snapshot/native-prefix-20261114/inputs/AINav/common-source'
sys.path.insert(0,str(ORIGINAL))
from ainav.contracts import Observation, Primitive, canonical, file_sha
from ainav.intents import SkillIntent, IntentBatch
from ainav.planner import AinavPlanner
from ainav.native.behavior_authority import BehaviorOption, NativeReceipt
from .v4_successor_choice import PublicPath, NominalCost, choose
from .v4_backbone_adapters import AinavSuccessorAdapter, VLMWMIntentPlanner, build_v4_planner
from .v4_raw_wm_adapter import public_action11, OriginalBehaviorWMAdapter


def path(name, root):
    return PublicPath(name,root*64,(canonical(dict(skill='NAV',target_ref='goal',parameters={},preconditions=[])),))


class SharedChoiceTests(unittest.TestCase):
    def setUp(self):
        self.paths=(path('p0','a'),path('p1','b'));self.q='c'*64
    def choose(self,costs,**kwargs):
        return choose(self.paths,query_sha256=self.q,baseline_root_sha256='a'*64,
            evaluate=lambda p:NominalCost(p.path_id,self.q,*costs[p.path_id],evidence_ref='EXPLICIT_FIXTURE'),**kwargs)
    def test_delayed_successor_cost_not_local_fastest(self):
        local={'p0':1,'p1':2};successor={'p0':100,'p1':0}
        out=self.choose({k:('KNOWN_NOMINAL',local[k]+successor[k],True)for k in local})
        self.assertEqual(out['selected_root_sha256'],'b'*64);self.assertTrue(out['choice_changed'])
    def test_any_unknown_preserves_exact_baseline_not_optimistic_zero(self):
        out=self.choose({'p0':('UNKNOWN',None,False),'p1':('KNOWN_NOMINAL',0.,True)})
        self.assertFalse(out['optimization_applied']);self.assertEqual(out['selected_root_sha256'],'a'*64)
    def test_raw_or_local_cost_not_complete_successor_scope(self):
        out=self.choose({'p0':('KNOWN_NOMINAL',1.,False),'p1':('KNOWN_NOMINAL',2.,True)})
        self.assertFalse(out['optimization_applied'])
    def test_same_query_required_not_future_or_other_arm(self):
        with self.assertRaises(ValueError):choose(self.paths,query_sha256=self.q,baseline_root_sha256='a'*64,
            evaluate=lambda p:NominalCost(p.path_id,'d'*64,'KNOWN_NOMINAL',1.,True,'FIXTURE'))
    def test_no_subset_optimum_when_domain_budget_exhausted(self):
        out=self.choose({'p0':('KNOWN_NOMINAL',10.,True),'p1':('KNOWN_NOMINAL',1.,True)},max_paths=1)
        self.assertEqual(out['evaluated_paths'],0);self.assertFalse(out['optimization_applied'])
    def test_callback_overshoot_does_not_override(self):
        ticks=iter((0.,0.,.3,.3))
        out=self.choose({'p0':('KNOWN_NOMINAL',1.,True),'p1':('KNOWN_NOMINAL',0.,True)},clock=lambda:next(ticks))
        self.assertFalse(out['optimization_applied'])
    def test_all_refuted_is_not_native_unsafe_proof_or_synthetic_route(self):
        out=self.choose({'p0':('REFUTED_NOMINAL',None,True),'p1':('REFUTED_NOMINAL',None,True)})
        self.assertEqual(out['selected_root_sha256'],'a'*64);self.assertFalse(out['actual_success_or_safety_claimed'])
    def test_audit_data_role_or_missing_zero_or_negative_cost_rejected(self):
        for status,cost,role in [('UNKNOWN',0.,'DECLARED_GEOMETRY_NOMINAL_NOT_NATIVE_CERTIFICATE'),
                                 ('KNOWN_NOMINAL',-1.,'DECLARED_GEOMETRY_NOMINAL_NOT_NATIVE_CERTIFICATE'),
                                 ('KNOWN_NOMINAL',1.,'HISTORICAL_AUDIT_ONLY')]:
            with self.assertRaises(ValueError):NominalCost('p',self.q,status,cost,True,'FIXTURE',role)
    def test_stable_candidate_order_tie(self):
        out=self.choose({'p0':('KNOWN_NOMINAL',1.,True),'p1':('KNOWN_NOMINAL',1.,True)})
        self.assertEqual(out['selected_path'].path_id,'p0')


class Journal(list):
    def __call__(self,row):self.append(row);return 'EXPLICIT_SOFTWARE_JOURNAL#'+str(len(self))


class Roles:
    def __init__(self):self.calls=[]
    def run(self,role,payload,obs):
        self.calls.append(role);actions=payload['admitted_first_actions']
        if role=='object_proposer':return dict(plans=[dict(plan_id='p'+str(i),objects=[a['target_ref']],strategy='EXPLICIT_FIXTURE')for i,a in enumerate(actions[:2])])
        if role=='skill_proposer':
            return dict(plans=[dict(plan_id='p'+str(i),steps=[{k:copy.deepcopy(a[k])for k in('skill','target_ref','parameters','preconditions')},
                dict(skill='CLIMB',target_ref='goal',parameters=dict(surface_height_m=.6),preconditions=['EXPLICIT_FIXTURE'])],reaches_goal=True)for i,a in enumerate(actions[:2])])
        if role=='evaluator':return dict(nodes=[dict(node_id=n['node_id'],executable=True,
            reward=.8 if n['step']['target_ref']=='seen-2'else .4,evidence='EXPLICIT_FIXTURE')for n in payload['tree']['nodes']])
        if role=='advisor':return dict(replan=False,triggers=[],reason='EXPLICIT_FIXTURE')
        if role=='arborist':return dict(prune_node_ids=[],expand=True,reason='EXPLICIT_FIXTURE')
        raise AssertionError(role)


class FakeWM:
    def __init__(self):self.calls=0;self.unsupported=False
    def evaluate(self,batch):
        self.calls+=1
        return dict(query_sha256=batch.sha256,actual_model_forward_batches=0 if self.unsupported else 1,
                    known_raw_predictions=0 if self.unsupported else len(batch.options),
                    role='EXPLICIT_SOFTWARE_FIXTURE_NOT_REAL_WM',raw=[],unknown=[])


class FakeBackend:
    kind='openai_compatible_vision_api'
    identity=dict(role='EXPLICIT_SOFTWARE_FIXTURE_NOT_API')
    def __init__(self):self.requests=[];self.bad=False
    def generate(self,request,*,timeout_s):
        self.requests.append(request);actions=request['payload']['admitted_first_actions']
        plans=[dict(plan_id='p'+str(i),steps=[{k:copy.deepcopy(a[k])for k in('skill','target_ref','parameters','preconditions')},
            dict(skill='CLIMB',target_ref='goal',parameters=dict(surface_height_m=.6),preconditions=[])],reaches_goal=True)for i,a in enumerate(actions[:2])]
        if self.bad:plans[0]['steps'][0]['parameters']['goal_world_x_m']=999.
        return canonical(dict(plans=plans,selected_plan_id='p1'))


class SourceSeamTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.frame=Path(self.tmp.name)/'SOFTWARE.ppm';self.frame.write_bytes(b'P6\n2 2\n255\n'+b'\0\x80\0'*4)
        self.roles=Roles();self.journal=Journal()
    def batch(self,now=0.):
        obs=Observation.create(dict(time_s=now,rgb=dict(path=str(self.frame),sha256=file_sha(self.frame),time_s=now,width=2,height=2),
            objects=[dict(target_ref=x,label='EXPLICIT_SOFTWARE_BOX',bbox_xyxy=[0,0,1,1],evidence_ref='FIXTURE',
                geometry=dict(status='unknown',source='unavailable',values={},uncertainty={}))for x in('seen-1','seen-2')],public_state={},
            declared_map=dict(source_ref='EXPLICIT_SOFTWARE_MAP',anchors=[dict(target_ref='goal',description='EXPLICIT_SOFTWARE_DECK',position_xyz_m=[2.,0.,.6],uncertainty_xyz_m=[.1,.1,.1])]),
            goal='EXPLICIT_SOFTWARE_ELEVATED_GOAL',events=[]))
        opts=tuple(SkillIntent('intent-'+str(i),'NAV','seen-'+str(i+1),tuple(sorted(dict(goal_world_x_m=float(i),goal_world_y_m=0.,surface_height_m=0.).items())))for i in range(2))
        return IntentBatch('SOFTWARE-'+str(now),obs,opts,canonical(dict(source_ref='EXPLICIT_SOFTWARE_NOT_NATIVE',skills=['NAV','PUSH','CLIMB'],constraints=['No native admission from this fixture'])))
    def cost(self,obs,p,*,query_sha256):
        first=json.loads(p.steps_json[0]);return NominalCost(p.path_id,query_sha256,'KNOWN_NOMINAL',
            1. if first['target_ref']=='seen-1'else 10.,True,'EXPLICIT_SOFTWARE_FULL_SCOPE')
    def native(self,intent,status='succeeded'):
        actual=BehaviorOption('native',intent.skill,intent.target_ref,intent.parameters,60.,'FIXTURE_ORIGINAL_JUDGE')
        return actual,NativeReceipt(actual.sha256,.02,status,'a'*64,'EXPLICIT_SOFTWARE_COMMAND')
    def test_production_routes_refuse_fixture_roles_or_fake_WM(self):
        base=AinavPlanner(self.roles,self.journal,plan_count=2)
        with self.assertRaisesRegex(ValueError,'Production C/D'):
            AinavSuccessorAdapter(base,journal=self.journal)
        with self.assertRaisesRegex(ValueError,'Production A/B'):
            VLMWMIntentPlanner(FakeBackend(),FakeWM(),journal=self.journal)
    def test_fixture_complete_cost_provider_cannot_be_promoted_to_production(self):
        from .v4_reference_cost import CompleteReferenceCost
        cost=CompleteReferenceCost(initial_state=lambda *a,**k:None,forecast=lambda *a,**k:None,
            is_terminal=lambda s:None,journal=self.journal,software_fixture=True)
        base=AinavPlanner(self.roles,self.journal,plan_count=2)
        with self.assertRaisesRegex(ValueError,'Fixture cost provider'):
            AinavSuccessorAdapter(base,path_cost=cost,journal=self.journal)
        with self.assertRaisesRegex(ValueError,'Fixture cost provider'):
            VLMWMIntentPlanner(FakeBackend(),FakeWM(),path_cost=cost,journal=self.journal)

    def test_actual_cost_accountant_missing_source_preserves_original_C_D_selection(self):
        from .v4_reference_cost import CompleteReferenceCost
        cost=CompleteReferenceCost(initial_state=lambda *a,**k:None,forecast=lambda *a,**k:None,
            is_terminal=lambda s:None,journal=self.journal,software_fixture=True)
        base=AinavPlanner(self.roles,self.journal,plan_count=2)
        planner=AinavSuccessorAdapter(base,optimizer_enabled=True,path_cost=cost,
            journal=self.journal,software_fixture=True)
        selection=planner.select(self.batch())
        self.assertFalse(planner.last_choice['optimization_applied'])
        self.assertEqual(selection,base.pending)
        self.assertTrue(any(e['event']=='reach_v4_complete_reference_cost'for e in self.journal))

    def test_four_arm_factory_keeps_both_factors_explicit(self):
        base=AinavPlanner(self.roles,self.journal,plan_count=2)
        a=build_v4_planner('A',backend=FakeBackend(),wm_evaluator=FakeWM(),journal=self.journal,software_fixture=True)
        b=build_v4_planner('B',backend=FakeBackend(),wm_evaluator=FakeWM(),journal=self.journal,software_fixture=True)
        c=build_v4_planner('C',ainav_baseline=base,journal=self.journal,software_fixture=True)
        d=build_v4_planner('D',ainav_baseline=base,journal=self.journal,software_fixture=True)
        self.assertFalse(a.enabled);self.assertTrue(b.enabled);self.assertFalse(c.enabled);self.assertTrue(d.enabled)
        self.assertIs(type(a),type(b));self.assertIs(type(c),type(d))
    def test_D_cannot_silently_add_WM_or_A_alias_unchanged_AINav(self):
        base=AinavPlanner(self.roles,self.journal,plan_count=2)
        with self.assertRaises(ValueError):build_v4_planner('D',ainav_baseline=base,wm_evaluator=FakeWM(),journal=self.journal,software_fixture=True)
        with self.assertRaises(ValueError):build_v4_planner('A',ainav_baseline=base,journal=self.journal,software_fixture=True)
    def test_C_optimizer_off_is_exact_original_selection_and_roles(self):
        base=AinavPlanner(self.roles,self.journal,plan_count=2)
        p=AinavSuccessorAdapter(base,optimizer_enabled=False,path_cost=lambda *a:(_ for _ in()).throw(AssertionError('OFF must not evaluate')),journal=self.journal,software_fixture=True)
        b=self.batch();s=p.select(b)
        self.assertEqual(s.option_sha256,b.options[1].sha256);self.assertIs(s,base.pending)
        self.assertEqual(self.roles.calls,['object_proposer','skill_proposer','evaluator'])
    def test_D_real_original_pending_override_reaches_completion_hook(self):
        base=AinavPlanner(self.roles,self.journal,plan_count=2);self.current=b=self.batch()
        p=AinavSuccessorAdapter(base,optimizer_enabled=True,path_cost=self.cost,journal=self.journal,software_fixture=True);s=p.select(b)
        self.assertEqual(s.option_sha256,b.options[0].sha256);self.assertIs(s,base.pending)
        actual,receipt=self.native(b.options[0]);p.observe_intent(b.options[0],actual,receipt,'FIXTURE_BINDING')
        self.assertEqual(base.tree.history[0]['step']['target_ref'],'seen-1');self.assertIsNone(base.pending)
        self.assertTrue(p.last_choice['optimization_applied']);self.assertEqual(self.roles.calls,['object_proposer','skill_proposer','evaluator'])
    def test_D_missing_V4_source_cost_keeps_original_not_fake_optimized(self):
        base=AinavPlanner(self.roles,self.journal,plan_count=2);p=AinavSuccessorAdapter(base,optimizer_enabled=True,journal=self.journal,software_fixture=True)
        b=self.batch();s=p.select(b);self.assertEqual(s.option_sha256,b.options[1].sha256)
        self.assertFalse(p.last_choice['optimization_applied'])
    def test_D_rejection_preserves_original_advisor_arborist_replan(self):
        base=AinavPlanner(self.roles,self.journal,plan_count=2);self.current=b=self.batch()
        p=AinavSuccessorAdapter(base,optimizer_enabled=True,path_cost=self.cost,journal=self.journal,software_fixture=True)
        p.select(b);p.reject_intent(b.options[0],'FIXTURE_NATIVE_NOT_READY','FIXTURE_JUDGE')
        self.current=b2=self.batch(.1);p.select(b2)
        self.assertIn('advisor',self.roles.calls);self.assertFalse(base.tree.history)
    def test_D_refuses_wrong_receipt_not_predicted_advance(self):
        base=AinavPlanner(self.roles,self.journal,plan_count=2);self.current=b=self.batch()
        p=AinavSuccessorAdapter(base,optimizer_enabled=True,path_cost=self.cost,journal=self.journal,software_fixture=True);p.select(b)
        actual,receipt=self.native(b.options[1])
        with self.assertRaises(ValueError):p.observe_intent(b.options[0],actual,receipt,'WRONG')
        self.assertFalse(base.tree.history)
    def test_A_direct_VLM_WM_consumes_current_WM_and_full_VLM_plans(self):
        backend=FakeBackend();wm=FakeWM();p=VLMWMIntentPlanner(backend,wm,journal=self.journal,software_fixture=True)
        b=self.batch();s=p.select(b)
        self.assertEqual(s.option_sha256,b.options[1].sha256);self.assertEqual(wm.calls,1)
        self.assertIn('raw_WM',backend.requests[0]['payload']);self.assertFalse(p.last_choice['optimization_applied'])
        actual,receipt=self.native(b.options[1]);p.observe_intent(b.options[1],actual,receipt,'FIXTURE_BINDING')
        p.select(self.batch(.1));self.assertEqual(len(backend.requests),2)
        self.assertEqual(backend.requests[1]['payload']['actual_feedback'][0]['kind'],'completion')
        b2=self.batch(.1);actual,receipt=self.native(b2.options[1],status='budget_expired')
        p.observe_intent(p.pending,actual,receipt,'FIXTURE_EXPIRED_INTERVAL')
        p.select(self.batch(.2));self.assertEqual(backend.requests[-1]['payload']['actual_feedback'][0]['kind'],'revaluation')
    def test_B_uses_same_shared_selector_not_extra_WM_or_fake_API0(self):
        backend=FakeBackend();wm=FakeWM();self.current=b=self.batch()
        p=VLMWMIntentPlanner(backend,wm,optimizer_enabled=True,path_cost=self.cost,journal=self.journal,software_fixture=True);s=p.select(b)
        self.assertEqual(s.option_sha256,b.options[0].sha256);self.assertTrue(p.last_choice['optimization_applied'])
        self.assertEqual(wm.calls,1);self.assertEqual(len(backend.requests),1)
    def test_B_D_emit_one_same_schema_factor_event_matching_returned_selection(self):
        for arm in ('B','D'):
            with self.subTest(arm=arm):
                journal=Journal();b=self.batch()
                if arm=='B':
                    planner=VLMWMIntentPlanner(FakeBackend(),FakeWM(),optimizer_enabled=True,
                        path_cost=self.cost,journal=journal,software_fixture=True)
                else:
                    planner=AinavSuccessorAdapter(AinavPlanner(self.roles,journal,plan_count=2),
                        optimizer_enabled=True,path_cost=self.cost,journal=journal,software_fixture=True)
                selected=planner.select(b)
                rows=[e for e in journal if e['event']=='reach_v4_shared_optimizer_choice']
                self.assertEqual(len(rows),1)
                self.assertEqual(rows[0]['selected_root_sha256'],selected.option_sha256)
                self.assertEqual(rows[0]['baseline_option_sha256'],b.options[1].sha256)
                self.assertTrue(rows[0]['optimization_applied']);self.assertTrue(rows[0]['choice_changed'])
                self.assertFalse(rows[0]['physical_action_issued']);self.assertTrue(rows[0]['software_fixture'])
                json.dumps(rows)  # Never put a PublicPath/dataclass in the durable source journal.
                if arm=='B':
                    selection_row=next(e for e in journal if e['event']=='reach_v4_vlm_wm_selection')
                    self.assertEqual(selection_row['shared_optimizer_choice_ref'],
                        'EXPLICIT_SOFTWARE_JOURNAL#'+str(journal.index(rows[0])+1))

    def test_A_C_never_emit_new_treatment_event(self):
        for arm in ('A','C'):
            journal=Journal()
            planner=(VLMWMIntentPlanner(FakeBackend(),FakeWM(),journal=journal,software_fixture=True)
                if arm=='A' else AinavSuccessorAdapter(AinavPlanner(self.roles,journal,plan_count=2),
                    journal=journal,software_fixture=True))
            planner.select(self.batch())
            self.assertFalse(any(e['event']=='reach_v4_shared_optimizer_choice'for e in journal))

    def test_B_fallback_is_countable_but_not_effective_or_physical_optimization(self):
        planner=VLMWMIntentPlanner(FakeBackend(),FakeWM(),optimizer_enabled=True,
            journal=self.journal,software_fixture=True)
        b=self.batch();selected=planner.select(b)
        row=next(e for e in self.journal if e['event']=='reach_v4_shared_optimizer_choice')
        self.assertFalse(row['optimization_applied']);self.assertFalse(row['choice_changed'])
        self.assertEqual(row['selected_root_sha256'],selected.option_sha256)
        self.assertEqual(selected.option_sha256,b.options[1].sha256)
        self.assertGreater(row['unknown_or_partial_paths'],0)

    def test_B_D_missing_shared_event_journal_ref_blocks_dispatch_even_on_fallback(self):
        class MissingSharedRef(Journal):
            def __call__(self,row):
                ref=super().__call__(row)
                return None if row['event']=='reach_v4_shared_optimizer_choice' else ref
        for arm in ('B','D'):
            journal=MissingSharedRef()
            planner=(VLMWMIntentPlanner(FakeBackend(),FakeWM(),optimizer_enabled=True,
                journal=journal,software_fixture=True) if arm=='B' else
                AinavSuccessorAdapter(AinavPlanner(self.roles,journal,plan_count=2),optimizer_enabled=True,
                    journal=journal,software_fixture=True))
            with self.assertRaisesRegex(ValueError,'Durable shared optimizer'):
                planner.select(self.batch())

    def test_A_B_no_known_current_WM_predictions_cannot_claim_method_identity(self):
        backend=FakeBackend();wm=FakeWM();wm.unsupported=True
        p=VLMWMIntentPlanner(backend,wm,journal=self.journal,software_fixture=True)
        with self.assertRaisesRegex(ValueError,'WM-in-name-only'):p.select(self.batch())
        self.assertFalse(backend.requests);self.assertIsNone(p.pending)
    def test_B_missing_complete_successor_model_does_not_silently_enable_optimizer(self):
        p=VLMWMIntentPlanner(FakeBackend(),FakeWM(),optimizer_enabled=True,journal=self.journal,software_fixture=True)
        b=self.batch();s=p.select(b);self.assertEqual(s.option_sha256,b.options[1].sha256)
        self.assertFalse(p.last_choice['optimization_applied'])
    def test_VLM_invented_action_not_matched_by_nearest(self):
        backend=FakeBackend();backend.bad=True;p=VLMWMIntentPlanner(backend,FakeWM(),journal=self.journal,software_fixture=True)
        with self.assertRaises(ValueError):p.select(self.batch())
        self.assertIsNone(p.pending)
    def test_rejection_is_not_native_failure_and_requires_fresh_observation(self):
        b=self.batch();p=VLMWMIntentPlanner(FakeBackend(),FakeWM(),journal=self.journal,software_fixture=True)
        p.select(b);p.reject_intent(b.options[1],'SOURCE_GATE','FIXTURE_JUDGE')
        with self.assertRaises(ValueError):p.select(b)
        p.select(self.batch(.1));self.assertIsNotNone(p.pending)
    def test_same_clock_native_rejection_can_replan_on_new_query_with_real_feedback(self):
        b=self.batch();p=VLMWMIntentPlanner(FakeBackend(),FakeWM(),journal=self.journal,software_fixture=True)
        p.select(b);p.reject_intent(b.options[1],'FIXTURE_READONLY_NATIVE_REJECTION','FIXTURE_JUDGE')
        b2=replace(b,decision_id='FRESH_QUERY_AFTER_READONLY_REJECTION')
        p.select(b2);self.assertIsNotNone(p.pending)
    def test_no_second_select_before_actual_terminal(self):
        p=VLMWMIntentPlanner(FakeBackend(),FakeWM(),journal=self.journal,software_fixture=True);p.select(self.batch())
        with self.assertRaises(ValueError):p.select(self.batch(.1))
    def test_VLM_episode_budget_is_not_silent_handcoded_fallback(self):
        p=VLMWMIntentPlanner(FakeBackend(),FakeWM(),journal=self.journal,max_episode_calls=1,software_fixture=True);b=self.batch();p.select(b)
        actual,receipt=self.native(b.options[1]);p.observe_intent(b.options[1],actual,receipt,'FIXTURE')
        with self.assertRaises(ValueError):p.select(self.batch(.1))


class RawWMMappingTests(unittest.TestCase):
    def option(self,skill,**params):return SimpleNamespace(skill=skill,parameters=tuple(sorted(params.items())))
    def test_NAV_maps_only_declared_world_action11(self):
        a,why=public_action11(self.option('NAV',goal_world_x_m=2.,goal_world_y_m=-1.,surface_height_m=0.))
        self.assertIsNone(why);self.assertEqual(a[:6],(1.,0.,0.,0.,0.,0.));self.assertEqual(a[6:8],(.2,-.1))
    def test_absolute_push_not_guessed_from_scene_initial_or_goal(self):
        a,why=public_action11(self.option('PUSH',goal_world_x_m=11.6,goal_world_y_m=-2.6,surface_height_m=0.))
        self.assertIsNone(a);self.assertIn('NO_CAUSAL_PUBLIC_RELATIVE',why)
    def test_climb_surface_only_not_fake_approach(self):
        a,why=public_action11(self.option('CLIMB',surface_height_m=.6));self.assertIsNone(a)
    def test_relative_push_preserves_original_no_standoff_channel(self):
        a,why=public_action11(self.option('PUSH',push_distance_m=.6,surface_height_m=0.))
        self.assertEqual(a[6:8],(0.,0.));self.assertEqual(a[9],.6)
        a,why=public_action11(self.option('PUSH',push_distance_m=.6,surface_height_m=0.,standoff_m=.5))
        self.assertIsNone(a)
    def test_untrained_exit_not_scored(self):
        a,why=public_action11(self.option('EXIT_PUSH',push_distance_m=.6,surface_height_m=0.));self.assertIsNone(a)
    def test_bad_numeric_parameter_rejected(self):
        with self.assertRaises(ValueError):public_action11(self.option('NAV',goal_world_x_m=float('nan'),goal_world_y_m=0.,surface_height_m=0.))
    def test_model_loader_does_not_auto_download_or_accept_other_weights(self):
        with tempfile.TemporaryDirectory()as d:
            p=Path(d)/'fake.pt';p.write_bytes(b'EXPLICIT_SOFTWARE_NOT_REAL_WEIGHTS')
            with self.assertRaisesRegex(ValueError,'original7a6'):OriginalBehaviorWMAdapter(SimpleNamespace(training=False,predict_behavior=lambda:None),{},checkpoint_path=p,loaded_checkpoint_sha256='0'*64,query_provider=lambda *x:None)




class FiveArmSummaryTests(unittest.TestCase):
    def row(self,arm,**extra):
        value=dict(arm=arm,scene_sha256='a'*64,source_result_sha256='b'*64,source_result_ref='EXPLICIT_SOFTWARE_NOT_NATIVE',
                   task_success=False,resource_censored=False,api_censored=False,VLM_calls=0 if arm=='E'else 1,
                   WM_forward_batches=1 if arm in 'AB'else 0,effective_optimizer_choices=1 if arm in 'BD'else 0,
                   success_elapsed_sim_s=None)
        value.update(extra);return value
    def summary(self,rows):
        from .v4_outcome_summary import summarize
        return summarize(rows,scene_sha256='a'*64)
    def test_missing_arms_never_filled_with_zero_or_inferred_wins(self):
        v=self.summary([self.row('E')]);self.assertEqual(v['missing_arms'],list('ABCD'))
        self.assertFalse(v['all_five_original_results_available'])
    def test_WM_enabled_without_forward_invalidates_AB_identity(self):
        v=self.summary([self.row('A',WM_forward_batches=0),self.row('B')])
        self.assertEqual(v['primary_contrasts']['B-A']['status'],'METHOD_CONTRAST_NOT_ESTABLISHED')
    def test_optimized_switch_with_all_unknown_not_established(self):
        v=self.summary([self.row('C'),self.row('D',effective_optimizer_choices=0)])
        self.assertEqual(v['primary_contrasts']['D-C']['status'],'METHOD_CONTRAST_NOT_ESTABLISHED')
    def test_E_cannot_use_API_WM_or_added_optimizer(self):
        for k in ('VLM_calls','WM_forward_batches','effective_optimizer_choices'):
            with self.assertRaises(ValueError):self.summary([self.row('E',**{k:1})])
    def test_ground_XY_and_process_exit_not_complete_elevated_success(self):
        with self.assertRaises(ValueError):self.summary([self.row('C',task_success=True,success_elapsed_sim_s=1.)])
    def test_failure_elapsed_is_not_success_time(self):
        with self.assertRaises(ValueError):self.summary([self.row('C',success_elapsed_sim_s=1.)])
    def test_censor_kept_but_not_native_failure_or_winning_cost(self):
        v=self.summary([self.row('A',api_censored=True),self.row('B')])
        self.assertTrue(v['primary_contrasts']['B-A']['baseline_censored'])
        self.assertIsNone(v['primary_contrasts']['B-A']['successful_sim_delta'])
    def test_duplicate_arm_is_not_extra_independent_trial(self):
        with self.assertRaises(ValueError):self.summary([self.row('E'),self.row('E')])


if __name__=='__main__':unittest.main()
