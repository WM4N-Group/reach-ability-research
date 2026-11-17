"""Data-specific D3 derivation/binding/finite stop checks, synthetic no world/API."""
import ast
import copy
import hashlib
import io
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import source_revision as sources
from target_sink import TargetSinkOwner
import diagnostic_loop as loop
BASE=Path('/home/yuanyue/main/work/data-team/workers/new-critic-cohort-46308-20261115-v1/inputs/AINav/common-source')


class Tests(unittest.TestCase):
    def test_source_defaults_OFF_no_read(self):
        self.assertEqual(sources.derive_bundle_verifier(b'not SDK',original_source_sha256='bad'),b'not SDK')
        self.assertEqual(sources.derive_selected_context(b'not context'),b'not context')
    def test_true_original_strict_verifier_only_exact_override_and_truthful_provenance(self):
        raw=(BASE/'mujoco_zyh/source_bundle.py').read_bytes()
        new=sources.derive_bundle_verifier(raw,original_source_sha256=sources.VERIFIER_SHA,enabled=True)
        text=new.decode();ast.parse(text)
        self.assertIn("checksums['push/controller/box_push.py'] = '"+sources.NEW_PREDICATE+"'",text)
        self.assertIn('actual == set(checksums)',text);self.assertIn('not path.is_symlink()',text)
        self.assertIn('original_actor_weights_modified=False',text)
        self.assertIn('base_manifest_not_a_claim_of_unmodified_published_bundle=True',text)
        self.assertIn("digest((root / 'MANIFEST.json').read_bytes()) == MANIFEST_SHA256",text)
    def test_wrong_verifier_or_context_not_fuzzy_accepted(self):
        raw=(BASE/'mujoco_zyh/source_bundle.py').read_bytes()
        with self.assertRaises(ValueError):sources.derive_bundle_verifier(raw,original_source_sha256='f'*64,enabled=True)
        with self.assertRaises(ValueError):sources.derive_selected_context(b'changed',enabled=True)
    def test_context_only_hook_after_fresh_clock_before_return_and_runtime_error(self):
        raw=(BASE/'ainav/native/registered_target_context.py').read_bytes();new=sources.derive_selected_context(raw,enabled=True).decode()
        self.assertLess(new.index('view.settled=ClockedNativeSettled'),new.index('_data_d3_bind(view)'))
        self.assertLess(new.index('_data_d3_bind(view)'),new.index('    return view,dict('))
        self.assertIn("raise RuntimeError('D3 sink binding failed",new)
        before=ast.parse(raw);after=ast.parse(new)
        a=next(n for n in before.body if isinstance(n,ast.FunctionDef)and n.name=='make_target_context')
        b=next(n for n in after.body if isinstance(n,ast.FunctionDef)and n.name=='make_target_context')
        b.body=b.body[:-4]+[b.body[-1]]
        self.assertEqual(ast.dump(a,include_attributes=False),ast.dump(b,include_attributes=False))
    def test_phase_reader_uses_only_original_phase_fields_no_report_or_term(self):
        class Bomb:
            def report(self):raise AssertionError('no report')
            def termination(self):raise AssertionError('no term')
        machine=Bomb();machine.phase='run';machine.finish=NS(phase='retract')
        owner=TargetSinkOwner(runtime=None,driver_reader=lambda:NS(executor=NS(session=NS(machine=machine))),budget=None,output_path=None,bind_sink=lambda **kw:None,scope_id='test')
        self.assertEqual(owner.phase(),'machine:run|finish:retract')
    def test_owner_exact_selected_view_binding_and_second_refused(self):
        calls=[];runtime=object();view=object()
        with tempfile.TemporaryDirectory()as td:
            p=Path(td)/'rows';budget=NS(open=lambda path,mode:open(path,mode));sink=NS(report=lambda:{'records':0})
            def bind(**kw):calls.append(kw);kw['write_record'](b'row\n');return sink
            owner=TargetSinkOwner(runtime=runtime,driver_reader=lambda:None,budget=budget,output_path=p,bind_sink=bind,scope_id='new-test')
            self.assertIs(owner.bind(view),sink);self.assertIs(calls[0]['env'],view);self.assertIs(calls[0]['runtime'],runtime)
            self.assertEqual(calls[0]['world_role'],'task');self.assertEqual(calls[0]['max_records'],4096)
            with self.assertRaises(RuntimeError):owner.bind(view)
            owner.close();self.assertEqual(p.read_bytes(),b'row\n')
    def fixture(self, step):
        state=NS(sealed=False);budget=NS(state=state,finalizing=False)
        def seal():budget.finalizing=True;state.sealed=True
        budget.begin_finalization=seal
        driver=NS(arm='E',r=NS(step_count=0,sim=NS(data=NS(time=0.))),executor=None,complete=False,_D3_first_push_terminal=None)
        driver.step_one=lambda:step(driver)
        class Watch:
            def __call__(self):return True
        watch=Watch();watch.state=state
        return driver,watch,budget,NS(capture_if_due=lambda:None)
    def test_finite_loop_first_original_terminal_stops_without_next_step(self):
        def step(d):d._D3_first_push_terminal=dict(actual_task_steps=0,status='succeeded')
        d,w,b,v=self.fixture(step);r=loop.run_diagnostic(d,watch=w,budget=b,video=v,scope_start_mono=loop.time.monotonic(),enabled=True)
        self.assertEqual(r['driver_calls'],1);self.assertTrue(r['original_first_PUSH_terminal_observed']);self.assertTrue(b.state.sealed)
        self.assertFalse(r['full_task_success_claimed'])
    def test_finite_cap_is_censored_no_native_fail_or_retries(self):
        d,w,b,v=self.fixture(lambda d:None)
        r=loop.run_diagnostic(d,watch=w,budget=b,video=v,scope_start_mono=loop.time.monotonic()-1201,enabled=True)
        self.assertEqual(r['driver_calls'],0);self.assertEqual(r['stop_reason'],'FINITE_CAP_CENSORED');self.assertFalse(r['automatic_retry'])
    def test_driver_error_preserves_type_and_native_seal_without_args(self):
        def fail(d):raise RuntimeError('PRIVATE_TEST_SENTINEL')
        d,w,b,v=self.fixture(fail)
        with self.assertRaises(loop.D3LoopError)as error:loop.run_diagnostic(d,watch=w,budget=b,video=v,scope_start_mono=loop.time.monotonic(),enabled=True)
        self.assertTrue(b.state.sealed);self.assertEqual(error.exception.receipt['primary_error_type'],'RuntimeError');self.assertNotIn('PRIVATE_TEST_SENTINEL',repr(error.exception.receipt))
    def test_loop_and_receipt_hook_defaults_OFF(self):
        self.assertIsNone(loop.run_diagnostic('/NO_READ'));self.assertIsNone(loop.install_first_push_receipt_stop('/NO_READ'))


if __name__=='__main__':unittest.main(verbosity=2)
