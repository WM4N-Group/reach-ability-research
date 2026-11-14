import unittest
from .retrospective_ainav_costs import summarize


def example():
    # Explicit function fixtures, not modified actual records or physics cases.
    decisions=[]
    for i,(skill,execs) in enumerate((('PUSH',[('preparation','NAV',1.,3.),('interaction','PUSH',3.1,8.)]),
                                     ('CLIMB',[('preparation','NAV',8.1,10.),('interaction','CLIMB',10.1,12.)]))):
        rows=[]
        for j,(role,native,start,end) in enumerate(execs):
            rows.append(dict(native_option_sha256=f'fixture{i}-{j}',native_option=dict(skill=native),execution_role=role,
                first_started_time_s=start,literal_terminal_time_s=end,literal_terminal_status='succeeded',
                receipts=[dict(status='started'),dict(status='succeeded')],execution_evidence='EXPLICIT_FUNCTION_FIXTURE'))
        decisions.append(dict(intent_sha256=f'fixture-intent-{i}',selected_intent=dict(skill=skill,target_ref='fixture',parameters=[]),native_executions=rows))
    return dict(schema='Data-AINav-intent-native-evidence-index-v1',role='EVIDENCE_NOT_PLANNER_INPUT',
                historical_source_manifest_sha256='a'*64,decisions=decisions)


class PhaseCostsTests(unittest.TestCase):
    def summarize(self,x):return summarize(x,selected_manifest_sha256='a'*64)

    def test_chain_counts_gap_once_and_keeps_query_unknown(self):
        r=self.summarize(example());c=r['push_chains'][0]
        self.assertAlmostEqual(c['own_push_native_window_s'],4.9)
        self.assertAlmostEqual(c['observed_next_preparation_windows_s'],1.9)
        self.assertAlmostEqual(c['push_terminal_to_next_preparation_end_s'],2.)
        self.assertAlmostEqual(c['push_native_start_to_next_preparation_end_s'],6.9)
        self.assertIsNone(c['query_to_next_preparation_end_s']);self.assertIsNone(c['actual_Actor_ready_at_preparation_end'])

    def test_accounting_ablation_not_control_benefit(self):
        r=self.summarize(example());a=r['accounting_ablation']
        self.assertAlmostEqual(a['omitted_known_preparation_s'],3.9)
        self.assertFalse(a['different_policy_executed']);self.assertIsNone(a['actual_runtime_saved_s'])
        self.assertEqual(r['matched_alternative_candidates'],0)

    def test_missing_start_not_zero_or_unexecuted(self):
        x=example();x['decisions'][0]['native_executions'][0]['first_started_time_s']=None
        r=self.summarize(x)
        self.assertIsNone(r['rows'][0]['observed_native_window_s'])
        self.assertFalse(r['accounting']['window_coverage_complete_for_bound_options'])
        self.assertEqual(r['denominators']['bound_native_options'],4)

    def test_guard_window_preserved_without_fast_success(self):
        x=example();e=x['decisions'][1]['native_executions'][0]
        e['literal_terminal_status']=None;e['literal_terminal_time_s']=None;e['receipts']=[dict(status='started'),dict(status='hard_stop')]
        r=self.summarize(x);self.assertIsNone(r['push_chains'][0]['push_native_start_to_next_preparation_end_s'])
        self.assertIn('hard_stop',r['rows'][2]['literal_receipt_statuses'])
        self.assertEqual(r['denominators']['unobserved_terminal'],1)

    def test_nonfinite_partial_clock_is_not_a_legal_unknown(self):
        x=example();e=x['decisions'][0]['native_executions'][0]
        e['first_started_time_s']=None;e['literal_terminal_time_s']=float('nan')
        with self.assertRaises(ValueError):self.summarize(x)

    def test_failed_push_does_not_get_successful_chain_cost(self):
        x=example();x['decisions'][0]['native_executions'][1]['literal_terminal_status']='failed'
        r=self.summarize(x);self.assertIsNone(r['push_chains'][0]['own_push_native_window_s'])
        self.assertIsNone(r['push_chains'][0]['push_terminal_to_next_preparation_end_s'])

    def test_overlapping_options_cannot_be_summed(self):
        x=example();x['decisions'][0]['native_executions'][1]['first_started_time_s']=2.
        with self.assertRaises(ValueError):self.summarize(x)

    def test_duplicate_option_cannot_count_twice(self):
        x=example();x['decisions'][1]['native_executions'][0]['native_option_sha256']='fixture0-0'
        with self.assertRaises(ValueError):self.summarize(x)

    def test_new_plain_Data_index_can_have_unknown_source_without_being_historical(self):
        x=example();x.pop('historical_source_manifest_sha256')
        with self.assertRaises(ValueError):self.summarize(x)
        r=summarize(x,selected_manifest_sha256='a'*64,allow_unverified_source=True)
        self.assertIsNone(r['selected_executor_source_matches'])
        self.assertIsNone(r['source_manifest_sha256'])
        self.assertEqual(r['source_scope'],'UNKNOWN_SOURCE_COST_DIAGNOSTIC_ONLY')
        self.assertNotIn('HISTORICAL',r['role'])
        self.assertAlmostEqual(r['accounting']['known_disjoint_native_window_sum_s'],10.7)

    def test_diagnostic_mode_does_not_accept_known_wrong_source(self):
        x=example();x['historical_source_manifest_sha256']='b'*64
        with self.assertRaises(ValueError):
            summarize(x,selected_manifest_sha256='a'*64,allow_unverified_source=True)

    def test_different_version_or_input_role_rejected(self):
        for key,value in (('historical_source_manifest_sha256','b'*64),('role','CAUSAL_MODEL_INPUT')):
            x=example();x[key]=value
            with self.assertRaises(ValueError):self.summarize(x)


if __name__=='__main__':unittest.main()
