"""New finite-parent deltas only; fixtures are NOT native commands or receipts."""
from pathlib import Path
import sys
from types import SimpleNamespace as NS
import unittest
sys.path[:0] = [str(Path(__file__).resolve().parent), str(Path(__file__).resolve().parent.parent/'push-standard-parent-20261118-v1')]
import driver


class FiniteLoopTests(unittest.TestCase):
    def fixture(self, *, complete=False, steps=0, fail_video=False):
        state = object()
        calls = []
        class Budget:
            finalizing = False
            def begin_finalization(this):this.finalizing=True;calls.append('sealed')
        budget = Budget();budget.state=state
        class Watch:
            def __call__(this):calls.append('watch')
        watch=Watch();watch.state=state
        class Video:
            def capture_if_due(this):
                calls.append('video')
                if fail_video:raise BlockingIOError(11,'private-error-not-retained')
        d=NS(r=NS(step_count=0,sim=NS(data=NS(time=0.))),complete=complete,
             planner=NS(receipts=[]),executor=None)
        def step():
            calls.append('step');d.r.step_count+=1;d.r.sim.data.time=d.r.step_count*.005
            if steps and d.r.step_count>=steps:d.complete=True
            return False  # Deliberately NOT a success signal.
        d.step_one=step
        return d,watch,budget,Video(),calls

    def test_false_step_is_not_success_and_live_video_follows_actual_step(self):
        import time
        d,w,b,v,calls=self.fixture(steps=2)
        r=driver.run_case(d,watch=w,budget=b,video=v,scope_start_mono=time.monotonic(),enabled=True)
        self.assertTrue(r['full_case_success']);self.assertEqual(r['driver_calls'],2)
        self.assertEqual(calls.count('video'),2);self.assertEqual(calls.count('sealed'),1)

    def test_finite_cap_censors_not_native_failure_no_further_command(self):
        import time
        d,w,b,v,calls=self.fixture()
        # Finite driver-call cap with no physical progress, not a success return.
        d.step_one=lambda:False
        r=driver.run_case(d,watch=w,budget=b,video=v,scope_start_mono=time.monotonic(),enabled=True)
        self.assertFalse(r['full_case_success']);self.assertEqual(r['driver_calls'],27300)
        self.assertEqual(r['stop_reason'],'PROSPECTIVE_FINITE_CAP_CENSORED')
        self.assertEqual(calls.count('video'),0);self.assertTrue(b.finalizing)

    def test_capture_error_keeps_original_errno_leaf_actual_step_and_seals(self):
        import time
        d,w,b,v,calls=self.fixture(fail_video=True)
        with self.assertRaises(driver.CaseLoopError) as caught:
            driver.run_case(d,watch=w,budget=b,video=v,scope_start_mono=time.monotonic(),enabled=True)
        r=caught.exception.receipt
        self.assertEqual(r['task_steps'],1);self.assertEqual(r['original_error']['errno'],11)
        self.assertEqual(r['original_error']['frames'][-1]['function'],'capture_if_due')
        self.assertNotIn('private-error',str(r));self.assertFalse(r['full_case_success']);self.assertTrue(b.finalizing)

    def test_default_off_does_not_read_components(self):
        self.assertIsNone(driver.driver_class(enabled=False))
        self.assertIsNone(driver.run_case(enabled=False))

    def test_original_NAV_and_PUSH_approach_are_not_conflated(self):
        self.assertEqual(driver.NAV_GOAL,(-.02,0.))
        self.assertEqual(driver.PUSH_APPROACH,(-.08,0.))

    def test_worker_default_off_no_imported_native_lifecycle(self):
        import subprocess
        p=Path(__file__).with_name('worker.py')
        r=subprocess.run([sys.executable,'-I','-B',str(p)],capture_output=True,check=True)
        self.assertEqual((r.stdout,r.stderr),(b'',b''))

    def test_new_controller_closes_then_finalizes_before_tail_proof(self):
        # Specific new controller AST order, not rerunning the old D3 fixture.
        import ast
        text=Path(__file__).with_name('phase_control.py').read_text()
        tree=ast.parse(text)
        fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='execute')
        statements=[ast.unparse(n)for n in fn.body]
        a=statements.index('closure_proof = cas(finish)')
        self.assertEqual(statements[a+1],'budget.begin_finalization()')
        self.assertEqual(statements[a+2],"write_json(budget, L / 'result-CAS-proof.json', closure_proof)")
        self.assertNotIn("write_json(budget,L/'result-CAS-proof.json',cas(finish))",text)

if __name__=='__main__':unittest.main()
