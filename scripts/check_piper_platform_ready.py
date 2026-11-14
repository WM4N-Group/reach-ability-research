#!/usr/bin/env python3
"""Synthetic checks only: native termination/censor semantics and full-key joins."""
import copy
import unittest
from label_piper_platform_ready import PHASE, READY, align_ready, attach, native_outcome


def success():
    return dict(outcome='nav_climb_nav_platform_target_stable', termination={},
                platform_final_details=dict(complete=True, gates=dict(position=True, native_progress=True, no_failure=True),stable_s=1.))


def aligned():
    gates={str(i): True for i in range(19)}
    ready=dict(time_s=100.,actual_state=dict(episode_step=5000),gates=gates,continuous_stable_s=.5)
    join=dict(report_sha256='a'*64,ready_step=5000,ready_time_s=100.,phase_contract='pre_admission')
    source=dict(case_key='v/seed3701',join=join,input_view=dict(query=dict(original_READY_gates=gates,original_READY_stable_s=.5)))
    table=dict(case_key=source['case_key'],query_join=join,query_phase_canonical=PHASE)
    report=dict(platform_native_ready=ready)
    boundary=[dict(event=READY,time_s=100.,identical_physics_queues_and_histories=True)]
    entry=dict(report_sha256='a'*64,native_ready_s=100.)
    return source,table,report,ready,boundary,entry


class NativeLabels(unittest.TestCase):
    def test_original_success(self):self.assertTrue(native_outcome(success())['value'])

    def test_failure_overrides_stale_success_and_no_failure(self):
        r=success();r['termination']={'transition_effort': True}
        result=native_outcome(r);self.assertFalse(result['value']);self.assertFalse(result['right_censored'])
        self.assertEqual(result['native_failure_names'],['transition_effort'])

    def test_exception_is_unknown_not_physical_failure(self):
        r=native_outcome(dict(outcome='runtime_error'));self.assertIsNone(r['value']);self.assertTrue(r['right_censored'])

    def test_missing_completion_details_are_unknown(self):
        r=success();r['platform_final_details']={};self.assertIsNone(native_outcome(r)['value'])

    def test_timeout_without_verified_goal(self):
        r=native_outcome(dict(outcome='native_termination',termination=dict(time_out=True)))
        self.assertFalse(r['value']);self.assertFalse(r['right_censored'])

    def test_malformed_native_flags_rejected(self):
        with self.assertRaises(ValueError):native_outcome(dict(termination=dict(transition_effort=1)))


class EventJoins(unittest.TestCase):
    def test_first_actual_READY_before_admission(self):
        x=align_ready(*aligned());self.assertTrue(x['valid']);self.assertEqual(x['query_phase_canonical'],PHASE)

    def test_same_seed_wrong_report_rejected(self):
        args=list(copy.deepcopy(aligned()));args[-1]['report_sha256']='b'*64
        with self.assertRaises(ValueError):align_ready(*args)

    def test_late_next_physics_row_not_a_query(self):
        args=list(copy.deepcopy(aligned()));args[0]['join']=dict(args[0]['join'],ready_step=5001,ready_time_s=100.02)
        with self.assertRaises(ValueError):align_ready(*args)

    def test_phase_and_duplicate_READY_rejected(self):
        args=list(copy.deepcopy(aligned()));args[1]['query_phase_canonical']='after_admitted_physics'
        with self.assertRaises(ValueError):align_ready(*args)
        args=list(copy.deepcopy(aligned()));args[4].append(copy.deepcopy(args[4][0]))
        with self.assertRaises(ValueError):align_ready(*args)

    def test_gate_history_mismatch_rejected(self):
        args=list(copy.deepcopy(aligned()));args[0]['input_view']['query']['original_READY_gates']={'wrong': True}
        with self.assertRaises(ValueError):align_ready(*args)

    def test_attachment_keeps_inputs_and_known_failures(self):
        interface=dict(rows=[],missing_numeric_families=['actual joint torque'])
        labels=dict(rows=[])
        for i in range(3):
            join=dict(report_sha256=str(i)*64,ready_step=i,ready_time_s=i,phase_contract='pre_admission')
            key='version'+str(i)+'/seed3701'
            interface['rows'].append(dict(case_key=key,query_join=join,query_phase_canonical=PHASE,
                producer_existing_native_terminal_reference=dict(value=i!=1)))
            labels['rows'].append(dict(case_key=key,query_join=join,transition_ready=dict(query_phase_canonical=PHASE),
                next_skill_complete=dict(value=i!=1)))
        original=copy.deepcopy(interface);result=attach(interface,labels,dict(path='labels',sha256='l'*64))
        self.assertTrue(result['joint_interface_complete']);self.assertEqual(interface,original)
        self.assertEqual(result['missing_numeric_families'],['actual joint torque'])
        labels['rows'][1]['next_skill_complete']['value']=True
        with self.assertRaises(ValueError):attach(interface,labels,dict(path='labels',sha256='l'*64))


if __name__=='__main__':unittest.main(verbosity=2)
