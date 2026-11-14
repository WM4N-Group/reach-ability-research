from copy import deepcopy
from pathlib import Path
import json
import math
import unittest
from .observed_handover_analysis import (DATA_ROOT,consume_closed,sha,data_components,
                                         normalize_evaluation,retrospective_compare,consume_lifecycle,handover_tradeoff_table,exit_projection_diagnostic)

FIXTURE=DATA_ROOT/'EXPLICIT-FIXTURE'
EVAL_SHA='12cc1933dc044452add76f7bdaddaa850387b66b14d07047136e1c0059542da3'


def consume_fixture(**kwargs):
    return consume_closed(sidecar=FIXTURE/'sidecar',
        sidecar_pins={n:sha(FIXTURE/'sidecar'/n) for n in ('identity.json','closure.json','events.jsonl')},
        evaluation_path=FIXTURE/'evaluation.json',evaluation_sha256=EVAL_SHA,
        purpose=kwargs.pop('purpose','offline_dev_outcome_analysis'),**kwargs)


def interval(a,b,attempt):
    return dict(start_s=a,end_s=b,seconds=b-a,clock_id='EXPLICIT_UNIT_SOFTWARE_CLOCK',attempt_id=attempt,
                source_refs=['EXPLICIT_UNIT_FIXTURE_start','EXPLICIT_UNIT_FIXTURE_end'],observed_not_prediction=True)


def example(d,*,entry=1.,native=4.,successor=6.,wait=0.,finish=True):
    """Pure FUNCTION fixture, not a Data captured sidecar or registered outcome."""
    identity=json.loads((FIXTURE/'sidecar/identity.json').read_text())
    identity.update(run_id='explicit-unit-fixture-'+str(d),attempt_id='explicit-unit-'+str(d),branch_id='B-'+str(d))
    evaluation=json.loads((FIXTURE/'evaluation.json').read_text())
    evaluation['base_evaluation']['identity'].update(run_id=identity['run_id'],branch_id=identity['branch_id'])
    qend=1.+entry+native;start=qend+wait;end=start+successor
    evaluation['stage_intervals']=dict(query_to_native_receipt=interval(1.,qend,identity['attempt_id']),
        native_push_including_finish=interval(1.+entry,qend,identity['attempt_id']),
        successor_preparation=interval(start,end,identity['attempt_id']))
    evaluation['normal_Finish_complete']=dict(value=finish,valid=True)
    return evaluation,identity


def normalize(d,**kw):
    e,i=example(d,**kw)
    with data_components() as (phase,_,__):return normalize_evaluation(e,i,d,phase.sum_disjoint)


def scope(**kw):
    return dict(purpose='offline_dev_outcome_analysis',fixed_reference_distance_m=.6,**kw)


class ObservedHandoverTests(unittest.TestCase):
    def test_actual_Data_fixture_consumption_not_new_capture_or_ready(self):
        r=consume_fixture(allow_fixture=True)
        self.assertEqual(r['provenance'],'EXPLICIT_FIXTURE')
        self.assertAlmostEqual(r['native_push_including_Finish_s'],2.005)
        self.assertAlmostEqual(r['query_to_native_receipt_s'],3.005)
        self.assertIsNone(r['query_to_successor_preparation_end_s'])
        self.assertTrue(r['original_entry_check']['value'])
        self.assertIsNone(r['actual_next_ready']);self.assertFalse(r['online_input_allowed'])

    def test_private_or_fixture_default_cannot_be_online_provider(self):
        with self.assertRaises(ValueError):consume_fixture()
        with self.assertRaises(ValueError):consume_fixture(allow_fixture=True,purpose='online_prediction')
        with self.assertRaises(ValueError):consume_fixture(allow_fixture=True,purpose='fit_or_norm')

    def test_closed_pins_not_silently_replaced(self):
        with self.assertRaises(ValueError):
            consume_closed(sidecar=FIXTURE/'sidecar',sidecar_pins={n:'0'*64 for n in ('identity.json','closure.json','events.jsonl')},
                evaluation_path=FIXTURE/'evaluation.json',evaluation_sha256=EVAL_SHA,purpose='offline_dev_outcome_analysis',allow_fixture=True)

    def test_full_cost_uses_query_and_successor_endpoint_not_double_Finish(self):
        r=normalize(.2,entry=1.,native=4.,successor=6.)
        self.assertEqual(r['query_to_successor_preparation_end_s'],11.)
        self.assertEqual(r['receipt_to_successor_preparation_end_s'],6.)
        self.assertEqual(r['native_push_including_Finish_s'],4.)
        self.assertIsNone(r['actual_next_ready'])

    def test_wait_between_receipt_and_next_preparation_is_not_free(self):
        r=normalize(.2,entry=1.,native=4.,successor=6.,wait=2.)
        self.assertEqual(r['query_to_successor_preparation_end_s'],13.)
        self.assertEqual(r['receipt_to_successor_preparation_end_s'],8.)

    def test_hypothesis_is_numeric_not_fixed_distance_classifier(self):
        records=[normalize(.2,native=4.,successor=6.),normalize(.4,native=6.,successor=1.),normalize(.6,native=8.,successor=2.)]
        r=retrospective_compare(records,comparison_scope=scope(controlled_initial_state_design=True,state_equivalence_evidence_refs=['EXPLICIT_UNIT_FIXTURE_design_not_native']))
        self.assertEqual(r['operation_cost_only_retrospective_minimum']['distance_m'],.2)
        self.assertEqual(r['full_enumeration_retrospective_minimum']['distance_m'],.4)
        self.assertEqual(r['reference_disagreement']['observed_endpoint_cost_difference_s'],3.)
        self.assertFalse(r['causal_method_gain_established']);self.assertIsNone(r['best_online_action'])

    def test_shorter_guard_stop_not_efficiency_gain(self):
        e,i=example(.2,native=.1,successor=.1);e['base_evaluation']['measured_guard_stop']=dict(original_evidence_sha256='a'*64)
        e['base_evaluation']['status']='MEASURED_STOP'
        with data_components() as (phase,_,__):failed=normalize_evaluation(e,i,.2,phase.sum_disjoint)
        self.assertIsNone(failed['query_to_successor_preparation_end_s'])
        r=retrospective_compare([failed,normalize(.4)],comparison_scope=scope())
        self.assertEqual(r['denominator']['attempts'],2);self.assertEqual(r['denominator']['PUSH_and_Finish_completions'],1)
        self.assertEqual(r['full_enumeration_retrospective_minimum']['distance_m'],.4)
        self.assertFalse(r['all_three_observed_complete_endpoints'])

    def test_missing_Finish_or_successor_does_not_become_zero(self):
        r=normalize(.2,finish=False);self.assertIsNone(r['native_push_including_Finish_s'])
        real_fixture=consume_fixture(allow_fixture=True)
        result=retrospective_compare([real_fixture],comparison_scope=scope())
        self.assertIsNone(result['full_enumeration_retrospective_minimum'])
        self.assertEqual(result['missing_handover_endpoint_distances_m'],[.2,.4,.6])

    def test_same_public_hash_does_not_prove_same_hidden_state(self):
        a,b=normalize(.2),normalize(.4)
        self.assertEqual(a['identity']['input_query_sha256'],b['identity']['input_query_sha256'])
        r=retrospective_compare([a,b],comparison_scope=scope())
        self.assertFalse(r['matched_state_declared']);self.assertFalse(r['matched_state_certified_by_analyzer'])
        self.assertEqual(r['scope_basis'],'OBSERVATIONAL_UNMATCHED_PREFIX_STATE')

    def test_no_repetition_filtering_or_mixed_executor_averaging(self):
        with self.assertRaises(ValueError):retrospective_compare([normalize(.2),normalize(.2)],comparison_scope=scope())
        a,b=normalize(.2),normalize(.4);b['identity']['program_sha256']='b'*64
        with self.assertRaises(ValueError):retrospective_compare([a,b],comparison_scope=scope())
        b=normalize(.4);b['provenance']='QUALIFIED_NEW_CAPTURE'
        with self.assertRaises(ValueError):retrospective_compare([a,b],comparison_scope=scope())

    def test_stage_overlap_clock_or_bad_length_rejected(self):
        for field,value in (('start_s',1.),('clock_id','other'),('seconds',float('nan'))):
            e,i=example(.2);e['stage_intervals']['successor_preparation'][field]=value
            with data_components() as (phase,_,__):
                with self.assertRaises(ValueError):normalize_evaluation(e,i,.2,phase.sum_disjoint)

    def test_Data_PM_guard_and_storage_remain_failure_or_incomplete(self):
        root=Path('/home/yuanyue/main/work/data-team/consumer-deliveries/IROS2027-Common-V9-Prefix-Hook-Lifecycle-CPU-20261112-PM-v1/EXPLICIT-FIXTURES')
        pins={'normal':'addc2067d326b1c4f5bf1bda534834bb63384a0243c008131b8be195a8f2c248',
              'original-guard':'396eed6723e33819059d9c4e48722c7b8161268d699a3e5bc46f0536ff5f8a5f',
              'storage-after-issued':'9fa6cdb6b40070af92840edd32ab26dfdfe43cfb713a2d472c0e7bbd9b47bc47'}
        rows={}
        for name,h in pins.items():
            sidecar=root/name/'capture/phase-capture'
            rows[name]=consume_lifecycle(lifecycle_path=root/name/'lifecycle/lifecycle-closure.json',lifecycle_sha256=h,
                sidecar=sidecar,sidecar_pins={n:sha(sidecar/n) for n in ('identity.json','closure.json','events.jsonl')},
                purpose='offline_dev_outcome_analysis',allow_fixture=True)
        self.assertEqual(rows['normal']['observed_issued_count'],405)
        self.assertTrue(rows['normal']['normalized_observation']['PUSH_and_normal_Finish_complete'])
        self.assertFalse(rows['original-guard']['normalized_observation']['PUSH_and_normal_Finish_complete'])
        self.assertIsNone(rows['original-guard']['normalized_observation']['query_to_successor_preparation_end_s'])
        storage=rows['storage-after-issued']
        self.assertEqual(storage['observed_issued_count'],2);self.assertEqual(storage['persisted_issued_count'],1)
        self.assertEqual(storage['status'],'INCOMPLETE_EVIDENCE_NOT_NOT_RUN_OR_SUCCESS')
        self.assertIsNone(storage['normalized_observation']);self.assertTrue(storage['issued_actions_observed'])

    def test_pure_normalizer_cannot_promote_prediction_to_actual_interval(self):
        e,i=example(.2);e['stage_intervals']['query_to_native_receipt']['observed_not_prediction']=False
        with data_components() as (phase,_,__):
            with self.assertRaises(ValueError):normalize_evaluation(e,i,.2,phase.sum_disjoint)

    def test_tradeoff_reversal_condition_is_derived_from_costs(self):
        records=[normalize(.2,native=4.,successor=6.),normalize(.4,native=6.,successor=1.)]
        result=handover_tradeoff_table(records)
        self.assertEqual(len(result),1)
        self.assertEqual(result[0]['native_time_saving_s'],2.)
        self.assertEqual(result[0]['omitted_entry_plus_handover_difference_s'],5.)
        self.assertTrue(result[0]['observed_completion_order_reversed'])
        self.assertEqual(handover_tradeoff_table([consume_fixture(allow_fixture=True)]),[])

    def test_exit_LABEL_geometry_robot_and_object_coupling_not_ready(self):
        geometry=dict(box_length_m=2.4,HIGH_front_m=3.5,CLIMB_B_standoff_m=1.05,
                      lane_y_m=-2.,approach_radius_m=.16,HIGH_dock_tolerance_m=.01,source_ref='explicit_unit_fixture_registered_rule')
        corners=[[x,y,z] for x in (1.1,3.5) for y in (-2.7,-1.3) for z in (0.,.2)]
        payload=dict(stage='AFTER_NORMAL_FINISH',frame='WORLD_POSITIVE_X',derived_from_requested_goal=False,
                     box_corners_world_xyz_m=corners,robot_support_footprint_world_xy_m=[[-.1,-2.1],[-.1,-1.9],[.1,-2.1],[.1,-1.9]],
                     robot_base_world_xyz_m=[.7,-2.,.3],sample_physical_tick=800,private_state_evidence_sha256='a'*64,source_support_ref='GROUND')
        r=exit_projection_diagnostic(payload,registered_geometry=geometry,purpose='offline_dev_outcome_analysis')
        self.assertAlmostEqual(r['measured_base_to_original_reference_m'],.65)
        self.assertTrue(r['direct_NAV_repair_may_be_needed']);self.assertFalse(r['whole_PUSH_infeasible'])
        self.assertAlmostEqual(r['later_HIGH_actual_corner_projection_gap_m'],0.)
        self.assertIsNone(r['actual_next_ready']);self.assertFalse(r['online_input_allowed'])
        with self.assertRaises(ValueError):exit_projection_diagnostic(payload,registered_geometry=geometry,purpose='online_prediction')

    def test_only_completed_endpoints_rank_and_fixed_missing_stays_missing(self):
        r=retrospective_compare([normalize(.4)],comparison_scope=scope())
        self.assertIsNone(r['fixed_reference']);self.assertEqual(r['missing_distances_m'],[.2,.6])
        self.assertFalse(r['task_success_rate_effect_established']);self.assertFalse(r['execution_authorized'])


if __name__=='__main__':unittest.main()
