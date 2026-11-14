from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from .native_domain_v0 import load_domain, VERSION
from .discrete_selection import select_discrete,geometric_relations,COST_TERMS,EvidenceError,select_from_bundle

TEST_SHA=hashlib.sha256(b'explicit_synthetic_selector_fixture_v1').hexdigest()
TRUST={'unit-fixture':TEST_SHA}


def problem():
    return dict(executor_version=VERSION,scene_id='SYNTHETIC_NOT_NATIVE_SCENE',object_ref='B',
                current_observation_ref='SYNTHETIC_NOT_SENSOR_DATA',query_time_s=10.,
                successor_requirement_id='SYNTHETIC_NEXT_SUPPORT',axis_id='SYNTHETIC_LONGITUDINAL_X',
                requirement_source_ref='analytic_unit_fixture_not_robot_geometry',
                requirements=dict(box_length_m=2.,destination_front_m=3.,minimum_overlap_m=.1,
                                  exit_reference_separation_m=.5),objective='minimum_supplied_total_cost_upper_s')


def effect(distance,*,front=1.2,robot=.5,cost=4.,entry=True):
    p=problem()
    identity={k:p[k] for k in ('executor_version','scene_id','object_ref','current_observation_ref','query_time_s','successor_requirement_id','axis_id')}
    identity['push_distance_m']=distance
    return dict(identity=identity,source=dict(name='unit-fixture',sha256=TEST_SHA,tier='synthetic_test',
                online_use_allowed=True,information_time_s=9.,assumptions=['analytic_fixture_not_robot_outcome']),
                geometry_phase='after_original_Finish',box_exit_front_m=[front,front],robot_exit_x_m=[robot,robot],
                entry_model_eligible=entry,predicted_next_ready=None,
                costs=dict(unit='s',terms=dict(zip(COST_TERMS,([1.,1.],[cost,cost],[2.,2.])))))


def run(effects,**kw):
    return select_discrete(load_domain(),problem(),effects,trusted_sources=TRUST,allow_synthetic=True,**kw)


class DiscreteSelectionTests(unittest.TestCase):
    def test_numeric_cost_not_fixed_largest_distance(self):
        r=run({d:effect(d,cost=c) for d,c in zip((.2,.4,.6),(2.,4.,7.))})
        self.assertEqual(r['best_evaluated_candidate']['parameter_template']['parameters']['push_distance_m'],.2)
        self.assertTrue(r['global_best_in_supplied_model'])
        self.assertEqual(r['best_evaluated_candidate']['score_upper_s'],5.)

    def test_geometry_changes_winner_not_just_scalar_ranking(self):
        r=run({.2:effect(.2,front=.9,cost=1),.4:effect(.4,front=1.,cost=2),.6:effect(.6,front=1.3,cost=4)})
        self.assertEqual(r['best_evaluated_candidate']['parameter_template']['parameters']['push_distance_m'],.6)
        self.assertEqual(r['resolved_count'],3)

    def test_subset_best_not_global(self):
        r=run({.4:effect(.4)});self.assertEqual(r['status'],'BEST_OF_EVALUATED_SUBSET_IN_SUPPLIED_MODEL')
        self.assertFalse(r['global_best_in_supplied_model']);self.assertEqual(r['unknown_candidates'],[.2,.6])

    def test_no_effect_is_unknown_not_default(self):
        r=run({});self.assertEqual(r['status'],'UNKNOWN');self.assertIsNone(r['best_evaluated_candidate'])
        self.assertFalse(r['global_physical_infeasible'])

    def test_cost_unknown_not_zero(self):
        e=effect(.2);e['costs']['terms']['successor_preparation']=None
        r=run({.2:e});self.assertIsNone(r['best_evaluated_candidate']);self.assertIn('unknown_cost',r['rows'][0]['reason'])

    def test_goal_not_exit_prediction(self):
        e=effect(.2);e['source']['tier']='requested_goal_only';e['requested_box_front_m']=[1.3,1.3]
        r=run({.2:e});self.assertIsNotNone(r['rows'][0]['requested_goal_relations'])
        self.assertFalse(r['rows'][0]['rankable'])

    def test_wrong_phase_cannot_borrow_push_endpoint(self):
        e=effect(.2);e['geometry_phase']='after_PUSH_before_Finish'
        self.assertEqual(run({.2:e})['rows'][0]['status'],'REJECTED_EVIDENCE')

    def test_historical_future_not_current(self):
        e=effect(.2);e['source']['tier']='observed_historical'
        self.assertEqual(run({.2:e})['rows'][0]['status'],'REJECTED_EVIDENCE')

    def test_synthetic_forbidden_by_default(self):
        r=select_discrete(load_domain(),problem(),{.2:effect(.2)},trusted_sources=TRUST)
        self.assertEqual(r['rows'][0]['status'],'REJECTED_EVIDENCE')

    def test_source_not_self_authorizing(self):
        r=select_discrete(load_domain(),problem(),{.2:effect(.2)},trusted_sources={},allow_synthetic=True)
        self.assertEqual(r['rows'][0]['status'],'REJECTED_EVIDENCE')

    def test_future_or_wrong_observation_or_action_or_successor(self):
        for field,value in (('current_observation_ref','other'),('push_distance_m',.6),
                            ('successor_requirement_id','other'),('axis_id','other'),('scene_id','other')):
            e=effect(.2);e['identity'][field]=value
            self.assertEqual(run({.2:e})['rows'][0]['status'],'REJECTED_EVIDENCE')
        e=effect(.2);e['source']['information_time_s']=11.
        self.assertEqual(run({.2:e})['rows'][0]['status'],'REJECTED_EVIDENCE')

    def test_units_bool_and_nan_not_scores(self):
        for v in ('m','WM_potential','probability'):
            e=effect(.2);e['costs']['unit']=v
            self.assertEqual(run({.2:e})['rows'][0]['status'],'REJECTED_EVIDENCE')
        for v in (True,float('nan'),float('inf')):
            e=effect(.2);e['box_exit_front_m']=[v,v]
            self.assertEqual(run({.2:e})['rows'][0]['status'],'REJECTED_EVIDENCE')

    def test_robust_interval_straddling_is_unknown(self):
        e=effect(.2);e['box_exit_front_m']=[1.,1.3]
        r=run({.2:e});self.assertFalse(r['rows'][0]['resolved'])
        self.assertIsNone(r['best_evaluated_candidate'])

    def test_clearance_uses_exit_robot_and_object(self):
        a=run({.2:effect(.2,front=1.2,robot=.5)})
        b=run({.2:effect(.2,front=1.2,robot=1.)})
        self.assertTrue(a['rows'][0]['rankable']);self.assertFalse(b['rows'][0]['rankable'])

    def test_enum_does_not_grant_entry(self):
        for value in (None,False):
            r=run({.2:effect(.2,entry=value)})
            self.assertFalse(r['rows'][0]['rankable']);self.assertIsNone(r['native_entry_ready'])

    def test_predicted_ready_is_not_actual_or_dispatch(self):
        e=effect(.2);e['predicted_next_ready']=True
        r=run({.2:e});self.assertTrue(r['rows'][0]['predicted_next_ready'])
        self.assertIsNone(r['actual_next_ready']);self.assertFalse(r['execution_authorized'])
        self.assertFalse(r['full_chain_feasibility_proven']);self.assertFalse(r['physical_dispatch'])

    def test_all_necessary_fail_not_physical_global_infeasibility(self):
        r=run({d:effect(d,front=.1) for d in (.2,.4,.6)})
        self.assertTrue(r['complete_model_enumeration']);self.assertIsNone(r['best_evaluated_candidate'])
        self.assertFalse(r['global_physical_infeasible'])

    def test_domain_expansion_and_rounding_refused(self):
        for d in (.8,.63,.73875):
            with self.assertRaises(EvidenceError):run({d:effect(d)})

    def test_upper_interval_cost_objective_is_explicit(self):
        a,b=effect(.2),effect(.4);a['costs']['terms']['push_including_original_Finish']=[1.,10.]
        r=run({.2:a,.4:b})
        self.assertEqual(r['best_evaluated_candidate']['parameter_template']['parameters']['push_distance_m'],.4)

    def test_incomplete_terms_and_duplicate_cost_scope_refused(self):
        e=effect(.2);e['costs']['terms']['extra_Finish']=[1.,1.]
        self.assertEqual(run({.2:e})['rows'][0]['status'],'REJECTED_EVIDENCE')

    def test_known_model_next_ready_false_blocks_nominal_choice(self):
        e=effect(.2);e['predicted_next_ready']=False
        r=run({.2:e});self.assertFalse(r['rows'][0]['rankable'])
        self.assertEqual(r['rows'][0]['status'],'SUCCESSOR_BLOCKED_IN_SUPPLIED_MODEL')

    def test_geometry_arithmetic_overflow_refused(self):
        p=problem();p['requirements']['box_length_m']=1e308
        e=effect(.2,front=1e308)
        r=select_discrete(load_domain(),p,{.2:e},trusted_sources=TRUST,allow_synthetic=True)
        self.assertEqual(r['rows'][0]['status'],'REJECTED_EVIDENCE')

    def test_pinned_artifact_numeric_path_and_tamper_rejection(self):
        e=effect(.4);source=e.pop('source');source.pop('name');source.pop('sha256')
        bundle=dict(schema='reach-normalized-effect-input-v1',source=source,records=[e])
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'synthetic.json';p.write_text(json.dumps(bundle))
            sha=hashlib.sha256(p.read_bytes()).hexdigest()
            r=select_from_bundle(load_domain(),problem(),p,expected_sha256=sha,allow_synthetic=True)
            self.assertEqual(r['best_evaluated_candidate']['parameter_template']['parameters']['push_distance_m'],.4)
            self.assertFalse(r['global_best_in_supplied_model'])
            p.write_text(p.read_text()+' ')
            with self.assertRaises(EvidenceError):select_from_bundle(load_domain(),problem(),p,expected_sha256=sha)

    def test_artifact_packaging_preserves_goal_role(self):
        from .run_discrete_selection import pack_fixture,fixtures
        bundle=pack_fixture(fixtures()['requested_goal_only_not_prediction'])
        self.assertEqual(bundle['source']['tier'],'requested_goal_only')
        a,b=effect(.2),effect(.4);b['source']['tier']='requested_goal_only'
        with self.assertRaises(ValueError):pack_fixture({.2:a,.4:b})

    def test_domain_version_and_requirements_not_inferred(self):
        p=problem();p['executor_version']='warehouse'
        with self.assertRaises(EvidenceError):select_discrete(load_domain(),p,{},trusted_sources={})
        p=problem();del p['requirements']['minimum_overlap_m']
        with self.assertRaises(EvidenceError):select_discrete(load_domain(),p,{},trusted_sources={})


if __name__=='__main__':unittest.main()
