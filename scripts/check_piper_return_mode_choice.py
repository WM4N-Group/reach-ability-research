"""Synthetic guards for the zero-budget return-choice screen; no source runs."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from screen_piper_return_mode_choice import (
    PREFIX_FIELDS, QUERY_EVENT, SUCCESS, outcome, preferred, prefix_comparison,
    query_event, summarize, verify,
)


def result(success, seconds=None):
    return dict(task_completed=success, successful_completion_time_s=seconds)


def pair(seed, a, b, eligible=True):
    return dict(seed_audit_only=seed, pair_eligible=eligible, A=a, B=b,
                preference=preferred(a,b) if eligible else None)


class ReturnModeChoiceChecks(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)

    def test_short_native_failure_never_earns_speed_credit(self):
        self.assertEqual(preferred(result(True,60.),result(False,None)),'A')
        self.assertEqual(preferred(result(False,None),result(True,64.)),'B')

    def test_completed_time_only_compares_successes(self):
        self.assertEqual(preferred(result(True,60.),result(True,64.)),'A')
        self.assertEqual(preferred(result(True,65.),result(True,64.)),'B')

    def test_equal_time_ties_not_artificial_gain(self):
        self.assertEqual(preferred(result(True,60.),result(True,60.)),'tie')

    def test_two_failures_do_not_rank_failed_elapsed_time(self):
        self.assertEqual(preferred(result(False,None),result(False,None)),'tie_both_failed')

    def test_unknown_is_not_failure_or_an_oracle_selection(self):
        self.assertIsNone(preferred(result(True,60.),result(None,None)))
        s=summarize([pair(1,result(True,60.),result(None,None))])
        self.assertEqual(s['requested_pairs'],1);self.assertEqual(s['fully_observed_rankable_pairs'],0)
        self.assertFalse(s['all_pairs_supported']);self.assertIsNone(s['oracle_added_successes_vs_A'])

    def test_observed_dominance_implies_zero_ceiling(self):
        ps=[pair(1,result(True,60.),result(True,64.)),pair(2,result(True,60.),result(False,None))]
        s=summarize(ps)
        self.assertEqual((s['always_A_completed'],s['always_B_completed'],s['hindsight_oracle_completed']),(2,1,2))
        self.assertTrue(s['B_empirically_dominated_for_original_task_completion_time'])
        self.assertEqual(s['oracle_added_successes_vs_A'],0);self.assertEqual(s['oracle_completed_time_gain_vs_A_s'],0.)

    def test_opposite_preferences_are_not_called_dominance(self):
        ps=[pair(1,result(True,60.),result(False,None)),pair(2,result(False,None),result(True,60.))]
        s=summarize(ps);self.assertFalse(s['B_empirically_dominated_for_original_task_completion_time'])
        self.assertEqual(s['hindsight_oracle_completed'],2);self.assertEqual(s['B_better_pair_ids'],[2])

    def test_invalid_pair_retained_not_silently_excluded_for_global_ceiling(self):
        ps=[pair(1,result(True,60.),result(True,64.)),pair(2,result(True,60.),result(False,None),False)]
        s=summarize(ps)
        self.assertEqual(s['requested_pairs'],2);self.assertEqual(s['ineligible_pair_ids'],[2])
        self.assertFalse(s['all_pairs_supported']);self.assertFalse(s['B_empirically_dominated_for_original_task_completion_time'])

    def test_duplicate_query_event_rejected(self):
        event=dict(event=QUERY_EVENT,step=1,time_s=.02,goal=[0.,0.,0.])
        with self.assertRaises(ValueError):query_event(dict(control_events=[event,event]))

    def test_nonfinite_goal_rejected(self):
        with self.assertRaises(ValueError):query_event(dict(control_events=[dict(event=QUERY_EVENT,step=1,time_s=.02,goal=[float('nan'),0.,0.])]))

    def rows(self):
        rows=[]
        for i in range(4):
            row={k:[0.] for k in PREFIX_FIELDS}
            row.update(step=i,time_s=i*.02,clearance_m=.05,torque_ratio=.2,history_valid_frames=3,gates={'ready':True})
            rows.append(row)
        return rows

    def write(self,name,rows):
        p=self.root/name;p.write_text(''.join(json.dumps(x)+'\n' for x in rows));return p

    def test_actual_prefix_equal_and_post_query_future_ignored(self):
        a=self.rows();b=deepcopy(a);b[3]['q']=[999.]
        s=prefix_comparison(self.write('a',a),self.write('b',b),2,.02)
        self.assertTrue(s['passed']);self.assertEqual(s['rows_checked'],3)
        self.assertNotIn(999.,s['decision_observation']['q'])

    def test_same_seed_cannot_hide_actual_state_or_command_difference(self):
        for field in ('q','pd_target','history_valid_frames'):
            a=self.rows();b=deepcopy(a);b[1][field]=[9.] if field!='history_valid_frames' else 2
            s=prefix_comparison(self.write('a',a),self.write('b',b),2,.02)
            self.assertFalse(s['passed']);self.assertEqual(s['first_different_field'],field)

    def test_missing_prefix_row_or_gap_rejected(self):
        a=self.rows();b=deepcopy(a);b[1]['step']=2
        with self.assertRaises(ValueError):prefix_comparison(self.write('a',a),self.write('b',b),2,.02)
        with self.assertRaises(ValueError):prefix_comparison(self.write('a',a),self.write('b',a[:1]),2,.02)

    def test_source_sha_mismatch_is_not_an_eligible_pair(self):
        p=self.write('source',self.rows())
        with self.assertRaises(ValueError):verify(dict(path=str(p),sha256='wrong'))

    def test_success_with_native_failure_flags_is_rejected(self):
        report=dict(outcome=SUCCESS,samples=2,control_dt=.02,terminal={'arm_effort_safety':True})
        checked=dict(status='success',outcome=SUCCESS,samples=2,end_time_s=.02)
        with self.assertRaises(ValueError):outcome(report,checked)

    def test_runtime_failure_remains_unknown_task_consequence(self):
        report=dict(outcome='runtime_error',samples=2,control_dt=.02,terminal={})
        checked=dict(status='failure',outcome='runtime_error',samples=2,end_time_s=.02)
        self.assertIsNone(outcome(report,checked)['task_completed'])

    def test_native_failure_has_no_successful_completion_time(self):
        report=dict(outcome='native_termination_during_exit',samples=2,control_dt=.02,terminal={'arm_effort_safety':True})
        checked=dict(status='failure',outcome=report['outcome'],samples=2,end_time_s=.02)
        o=outcome(report,checked);self.assertIs(o['task_completed'],False);self.assertIsNone(o['successful_completion_time_s'])


    def test_native_action_or_applied_command_mismatch_cannot_hide_behind_same_pd_target(self):
        for field in ('native_action','applied_joint_command'):
            a=self.rows();b=deepcopy(a)
            a[1][field]=[0.];b[1][field]=[1.]
            s=prefix_comparison(self.write('a',a),self.write('b',b),2,.02)
            self.assertFalse(s['passed']);self.assertEqual(s['first_different_field'],field)

    def test_boolean_and_number_not_treated_as_identical_history(self):
        a=self.rows();b=deepcopy(a);b[1]['gates']['ready']=1
        s=prefix_comparison(self.write('a',a),self.write('b',b),2,.02)
        self.assertFalse(s['passed'])

    def test_mismatched_extra_logged_field_rejected(self):
        a=self.rows();b=deepcopy(a);b[1]['new_history_channel']=[0.]
        with self.assertRaisesRegex(ValueError,'field set'):prefix_comparison(self.write('a',a),self.write('b',b),2,.02)


if __name__=='__main__':unittest.main()
