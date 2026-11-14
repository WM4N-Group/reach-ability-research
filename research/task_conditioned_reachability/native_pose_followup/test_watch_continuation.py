import tempfile
import unittest
from pathlib import Path
from watch_continuation import finished,publish

class ContinuationReportTests(unittest.TestCase):
    def test_running_never_terminal(self):
        self.assertFalse(finished(dict(continuation=dict(status='PHYSICAL_RUNNING'),active=None)))
    def test_active_cell_not_terminal_even_if_stop_field_appears(self):
        self.assertFalse(finished(dict(continuation=dict(status='STOPPED_GPU_BUSY_UNSPENT_RESERVED'),active={'fixture':True})))
    def test_resource_and_error_stops_report_partial(self):
        for status in ['STOPPED_GPU_BUSY_UNSPENT_RESERVED','STOPPED_TECHNICAL_OR_SEVERE_NO_RETRY','COMPLETED_REGISTERED_SIX']:
            self.assertTrue(finished(dict(continuation=dict(status=status),active=None)))
    def test_new_marker_preserves_earlier_result_and_problem_archive(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)
            for n in ['当前进展.md','下一步计划.md','问题与待确认事项.md']:(p/n).write_text('# Title\n\n<!-- native-pose-six-result:fixture -->\nOld result\n')
            original=(p/'问题与待确认事项.md').read_text()
            result=dict(source_manifest_sha256='fixture',ledger_status='COMPLETED_REGISTERED_SIX',starts=6,closed_pairs=3,registered_success_delta=0.,matched_input_success_delta=None)
            publish(p,p/'out',result);first=(p/'当前进展.md').read_text();publish(p,p/'out',result)
            self.assertEqual(first,(p/'当前进展.md').read_text());self.assertIn('Old result',first)
            self.assertEqual(original,(p/'问题与待确认事项.md').read_text())
