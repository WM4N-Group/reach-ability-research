"""New finite API/parent lifecycle CPU checks, no API/native or old suite repeat."""
import ast
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch
HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE),str(HERE.parent/'cd-dev-pair-20261117-v1')]
from api_accounting import CDAPILedger,AuditedOpener,construct_original_backend
import worker


class LedgerTests(unittest.TestCase):
    def ledger(self, expected=None):
        self.rows=[]
        return CDAPILedger(lambda row:self.rows.append(row) or 'durable',expected_served_model=expected)
    def driver(self, ledger, function):
        driver=NS(r=NS(step_count=0),coordinator=None,planner=NS())
        def select(batch):return function(batch)
        driver.planner.select=select;ledger.install_method_limit(driver);return driver
    def response(self, model='actual-label'):
        return dict(event='vlm_response',role='evaluator',raw_response='{"nodes":[]}',provider_metadata=dict(response_model=model,usage=dict(total_tokens=11,prompt_tokens=7,completion_tokens=4,unknown_private_field='NOT_RETAIN'),requested_model='deepseek-flash',elapsed_wall_s=.1,cumulative_api_calls=1,cumulative_total_tokens=11))
    def test_response_actual_label_usage_raw_tree_persisted_and_unknown_fields_removed(self):
        ledger=self.ledger();driver=self.driver(ledger,lambda b:(ledger(dict(event='vlm_request',backend={'provider':'DeepSeek','opener':'DO_NOT_RETAIN'})),ledger(self.response())))
        driver.planner.select(NS(sha256='actual-query'))
        self.assertEqual(ledger.snapshot()['actual_served_model'],'actual-label');self.assertEqual(ledger.role_responses,1)
        self.assertNotIn('opener',self.rows[0]['backend']);self.assertNotIn('unknown_private_field',self.rows[1]['provider_metadata']['usage']);self.assertIn('raw_response',self.rows[1])
    def test_cross_arm_mismatch_cost_recorded_before_refusal_no_retry(self):
        ledger=self.ledger('C-label');driver=self.driver(ledger,lambda b:(ledger(dict(event='vlm_request',backend={})),ledger(self.response('D-other'))))
        with self.assertRaises(RuntimeError):driver.planner.select(NS(sha256='task-query'))
        self.assertEqual(len(self.rows),2);self.assertEqual(ledger.role_responses,1);self.assertTrue(ledger.failed)
        with self.assertRaises(RuntimeError):driver.planner.select(NS(sha256='retry'))
        self.assertEqual(ledger.queries,1)
    def test_six_queries_next_query_refused_before_original_select(self):
        ledger=self.ledger();calls=[];d=self.driver(ledger,lambda b:calls.append(b.sha256))
        for i in range(6):d.planner.select(NS(sha256=str(i)))
        with self.assertRaises(RuntimeError):d.planner.select(NS(sha256='7'))
        self.assertEqual(len(calls),6)
    def test_eight_roles_ninth_refused_before_transport(self):
        ledger=self.ledger()
        def f(b):
            for i in range(9):ledger(dict(event='vlm_request',backend={}))
        d=self.driver(ledger,f)
        with self.assertRaises(RuntimeError):d.planner.select(NS(sha256='query'))
        self.assertEqual(ledger.role_attempts,8);self.assertEqual(len(self.rows),8)
    def test_exception_args_not_written_in_role_failure(self):
        ledger=self.ledger();ledger(dict(event='vlm_role_failed',error='RuntimeError: SECRET_TEST_SENTINEL',role='advisor'))
        self.assertNotIn('SECRET_TEST_SENTINEL',repr(self.rows));self.assertEqual(self.rows[0]['error_type'],'RuntimeError')
    def test_transport_counts_only_original_endpoints_without_reading_headers_or_body(self):
        ledger=self.ledger();calls=[]
        class Request:
            full_url='https://test.invalid/models'
            def get_method(self):return 'GET'
            @property
            def headers(self):raise AssertionError('must never inspect')
            @property
            def data(self):raise AssertionError('must never inspect')
        opener=AuditedOpener(NS(open=lambda request,timeout:calls.append(timeout)or'original-response'),ledger,'https://test.invalid')
        self.assertEqual(opener.open(Request(),timeout=30),'original-response');self.assertEqual(ledger.transport['models_attempts'],1)
        self.assertEqual(calls,[30])
    def test_transport_failure_type_only_and_no_hidden_retry(self):
        ledger=self.ledger();calls=[]
        def fail(request,timeout):calls.append(1);raise ValueError('SECRET_TEST_SENTINEL')
        opener=AuditedOpener(NS(open=fail),ledger,'https://test.invalid');request=NS(full_url='https://test.invalid/chat/completions',get_method=lambda:'POST')
        with self.assertRaises(ValueError):opener.open(request,timeout=30)
        self.assertEqual(calls,[1]);self.assertEqual(ledger.transport_errors,['ValueError']);self.assertNotIn('SECRET_TEST_SENTINEL',repr(ledger.snapshot()))
    def test_constructor_error_retains_attempt_time_and_rejects_replacement(self):
        ledger=self.ledger();calls=[]
        class Backend:
            BASE='https://test.invalid'
            def __init__(self,**kw):calls.append(kw);raise RuntimeError('SECRET_TEST_SENTINEL')
        with patch('urllib.request.build_opener',return_value=object()),self.assertRaises(RuntimeError):
            construct_original_backend(NS(DeepSeekBackend=Backend,_NoRedirect=lambda:None),{'model':'deepseek-flash'},ledger)
        self.assertEqual(ledger.constructor_attempts,1);self.assertEqual(ledger.constructor_completed,0);self.assertIsNotNone(ledger.constructor_wall_s)
        with self.assertRaises(RuntimeError):construct_original_backend(None,None,ledger)
        self.assertEqual(len(calls),1)
    def test_failed_role_parse_keeps_whitelisted_backend_last_usage(self):
        ledger=self.ledger();ledger.failed=True
        metadata=dict(response_model='actual-label',usage=dict(total_tokens=13,headers='DO_NOT_RETAIN'),cumulative_api_calls=1)
        result=ledger.snapshot(NS(calls=1,total_tokens=13,last_response_metadata=metadata))
        self.assertEqual(result['last_backend_response_metadata']['usage'],{'total_tokens':13})
        self.assertFalse(result['all_attempt_role_usage_known'])
        self.assertNotIn('DO_NOT_RETAIN',repr(result));self.assertIsNone(result['money_amount'])
    def test_method_exception_closes_active_query_without_resuming(self):
        ledger=self.ledger()
        def fail(b):raise ValueError('synthetic')
        d=self.driver(ledger,fail)
        with self.assertRaises(ValueError):d.planner.select(NS(sha256='q'))
        self.assertIsNone(ledger.query);self.assertTrue(ledger.failed)


class ParentTests(unittest.TestCase):
    def test_default_off_prepare_and_run_read_nothing(self):
        with patch.object(worker.Path,'read_bytes',side_effect=AssertionError):
            self.assertIsNone(worker.prepare('/NO_READ'));self.assertIsNone(worker.run('/NO_READ'))
    def test_cpu_candidate_cannot_enter_native_or_make_root(self):
        with patch.object(worker,'prepare',return_value=({},dict(schema='CD_DEV_CPU_CANDIDATE_NOT_AUTHORITY'))),self.assertRaises(RuntimeError):
            worker.run('no-read','pin','main',enabled=True)
    def test_parent_no_E_factory_or_NAV2000_success_and_uses_accepted_task_gate(self):
        text=(HERE/'worker.py').read_text();tree=ast.parse(text);calls=[ast.unparse(n.func)for n in ast.walk(tree)if isinstance(n,ast.Call)]
        self.assertNotIn('e_entry.build_E_driver',calls);self.assertIn('run_task',calls)
        self.assertIn("loop_receipt['accepted_task_complete']",text);self.assertNotIn("loop_receipt['task_complete']",text)
        self.assertNotIn('while runtime.step_count',text);self.assertNotIn('traceback.format_exc',calls)
    def test_task_layer_after_D_boundary_before_health_seal_and_capture(self):
        text=(HERE.parent/'cd-dev-pair-20261117-v1/cd_entry.py').read_text();body=text[text.index('def assemble_nav_dev_sources'):]
        self.assertLess(body.index('bind_original_d_query_boundary'),body.index('install_nav_dev_task'))
        self.assertIn('task_layer_installed=True',body)
    def test_outer_identity_compiles_whole_pinned_module_not_standalone_function(self):
        text=(HERE/'partial_constructor_cd.py').read_text()
        self.assertIn("check = compile(tree, str(path), 'exec', dont_inherit=True)",text)
        self.assertIn("_identity(original.__code__) != _identity(expected)",text)
        self.assertIn("original.__kwdefaults__ != {'enabled': False}",text)
        self.assertIn('ast.dump(stripped, include_attributes=False) != ast.dump(fn',text)
    def test_real_V4_outer_constructor_bytecode_and_default_OFF_without_world(self):
        import hashlib
        import partial_constructor_cd as partial
        root=Path('/home/yuanyue/main/work/ainav/development/complex_v4_four_arm_v1')
        path=root/'native_entry.py'
        spec=importlib.util.spec_from_file_location('_CD_CPU_original_native_entry',path)
        module=importlib.util.module_from_spec(spec)
        with patch.object(sys,'path',[str(root),*sys.path]):spec.loader.exec_module(module)
        receipt=partial.PartialObjects()
        wrapped=partial.build_receipted_entry(module,receipt,
            source_path=root.parent/'complex_dual_route_v1/native_construction.py',
            entry_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),enabled=True)
        self.assertIsNone(wrapped(enabled=False));self.assertIsNone(receipt.runtime)
        self.assertIsNone(receipt.observer)
    def test_new_installer_retains_effective_task_instance_hook(self):
        text=(HERE/'cd_install_fresh_driver.py').read_text()
        self.assertIn('original_connect=driver._connect_execution',text)
        self.assertIn('result=original_connect(*args,**kwargs)',text)
        self.assertIn('driver._connect_execution=MethodType(connect,driver)',text)
        self.assertIn('audit_constructor=host._connect_execution',text)
        self.assertIn('engine.before_issue(driver)',text)
        self.assertIn("with engine.boundary(driver,'capture-to-original-execution-no-physics')",text)
    def test_selected_Reach_relative_import_closure_includes_original_nominal_connection(self):
        import source_selection
        root=Path('/home/yuanyue/reach-ability-research')
        result=source_selection.verify_reach_sources(root)
        self.assertEqual(len(result),6)
        self.assertTrue(any(p.endswith('/finite_multistep_planner.py') for p in result))
    def test_disjoint_phase_counter_limits_and_single_loop_seal_parent_fallback(self):
        text=(HERE/'worker.py').read_text()
        self.assertIn('ScopeIO(ROOT,',text);self.assertIn('if not budget.finalizing:',text)
        self.assertIn('torch.cuda.manual_seed_all',text);self.assertIn("os.environ.get('PYTHONHASHSEED')=='2026111701'",text)


if __name__=='__main__':unittest.main(verbosity=2)
