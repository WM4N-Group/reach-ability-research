"""Software report fixtures only; never new experiment rows or positive claims."""
import ast,json,tempfile,unittest
from pathlib import Path
from build_effect_comparison import case_details
from watch_effect_comparison import TERMINAL,publish

class ReportTests(unittest.TestCase):
    def test_unstarted_has_no_cost_or_invented_binding(self):
        d=case_details(Path('/nonexistent'),dict(source_id='fixture'),None,dict(primary_success=None,status='not_run'))
        self.assertIsNone(d['sim_s']);self.assertIsNone(d['geometry_binding']);self.assertIsNone(d['penalty96_s'])
    def test_failed_task_is_penalized_not_reported_as_faster_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);out=root/'runs/fixture';out.mkdir(parents=True)
            (out/'report.json').write_text(json.dumps(dict(outcome='runtime_error',control_events=[])))
            d=case_details(root,dict(source_id='fixture',output_name='fixture'),dict(end_sim_s=2.,wall_s=3.,severe=True),dict(primary_success=False,status='recorded_start'))
            self.assertEqual(d['penalty96_s'],96.);self.assertTrue(d['technical'])
    def test_publication_is_once_and_does_not_touch_problem_page(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for name in ['当前进展.md','下一步计划.md','问题与待确认事项.md']:(root/name).write_text('# Fixture\n\nHistory\n')
            report=dict(source_manifest_sha256='fixture',complete=False,conclusion='缺失不填',mechanism_note='',starts=1,ledger_status='STOPPED')
            publish(root,root/'output',report);text=(root/'当前进展.md').read_text();publish(root,root/'output',report)
            self.assertEqual((root/'当前进展.md').read_text(),text)
            self.assertEqual((root/'问题与待确认事项.md').read_text(),'# Fixture\n\nHistory\n')
    def test_terminal_set_does_not_treat_running_as_done(self):
        self.assertNotIn('PHYSICAL_SUPERVISOR_RUNNING',TERMINAL);self.assertIn('PHYSICAL_STOPPED_PRESERVE_UNSPENT',TERMINAL)
    def test_watcher_does_not_import_simulators_or_call_launchers(self):
        source=Path(__file__).with_name('watch_effect_comparison.py').read_text();tree=ast.parse(source)
        imports={a.name for n in ast.walk(tree) if isinstance(n,ast.Import) for a in n.names}
        self.assertFalse(imports & {'mujoco','torch','gymnasium','isaaclab'})
        self.assertNotIn('run_supervisor.py',source)

if __name__=='__main__':unittest.main()
