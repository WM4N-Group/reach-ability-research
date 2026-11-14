"""New historical-reader unit fixtures; never navigation episodes or SDK calls."""
import json
from pathlib import Path
import tempfile
import time
import unittest

from bind_executed_navigation_baseline import metrics, compare_rows, read_through_step, original_success


class HistoricalBindingTests(unittest.TestCase):
    def test_whole_original_outcome_not_partial_stage_success(self):
        self.assertTrue(original_success(dict(outcome='nav_push_stow_nav_target_stable')))
        self.assertFalse(original_success(dict(outcome='push_settled')))
        self.assertIsNone(original_success({}))

    def test_failure_is_not_faster_success_and_common_success_cost_is_separate(self):
        pairs = [dict(seed=1,left=dict(success=False,end_time_s=5.),right=dict(success=True,end_time_s=60.)),
                 dict(seed=2,left=dict(success=True,end_time_s=58.),right=dict(success=True,end_time_s=59.))]
        m = metrics(pairs,96.)
        self.assertEqual(m['success_difference'], .5)
        self.assertEqual(m['common_success_time_delta_right_minus_left_s'], 1.)
        self.assertEqual(m['failure_penalized_time_delta_right_minus_left_s'], -17.5)
        self.assertEqual(m['win_case_ids'], [1])
        self.assertTrue(m['no_pvalue_or_independent_generalization_claim'])

    def test_missing_terminal_never_dropped_or_filled_with_success(self):
        p=[dict(left=dict(success=None),right=dict(success=True))]
        self.assertEqual(metrics(p,96.)['status'],'NOT_ESTIMABLE_missing_original_terminal')

    def test_exact_prefix_comparison_does_not_hide_small_or_typed_differences(self):
        d=compare_rows(dict(q=[1.],phase='NAV'),dict(q=[1.+1e-12],phase='PUSH'),['q','phase'])
        self.assertGreater(d['q']['max_abs_numeric_difference'],0)
        self.assertEqual(d['phase']['left'],'NAV')
        self.assertIn('q',compare_rows(dict(q=[1]),dict(q=[1.]),['q']))
        self.assertEqual(compare_rows({},dict(q=[]),['q'])['q']['status'],'missing_field')

    def test_prefix_stops_at_query_without_parsing_next_semantic_row(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'raw.jsonl'
            p.write_text(json.dumps(dict(step=0))+'\n'+json.dumps(dict(step=1))+'\nNOT_VALID_JSON_FUTURE\n')
            self.assertEqual(len(read_through_step(p,1,2,time.perf_counter()+2)),2)
            with self.assertRaisesRegex(RuntimeError,'budget'):
                read_through_step(p,1,1,time.perf_counter()+2)


if __name__=='__main__':
    unittest.main()
