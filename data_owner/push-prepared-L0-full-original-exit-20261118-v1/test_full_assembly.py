"""New FULL assembly's finite-loop/result wiring: stdlib fakes only, not native."""
import ast
from pathlib import Path
import time,types,unittest
P=Path(__file__).resolve().parent

def need(x,msg):
    if not x:raise RuntimeError(msg)

def exact_loop():
    tree=ast.parse((P/'push_l0_driver.py').read_text())
    nodes=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))and n.name in ('run_case','CaseLoopError')]
    ns=dict(need=need,time=time,bounded_exception=lambda e:dict(type=type(e).__name__))
    exec(compile(ast.Module(body=nodes,type_ignores=[]),'[exact-full-loop-fake]','exec'),ns)
    return ns

class FullAssembly(unittest.TestCase):
    def fake(self,complete=False,error=None,steps=0):
        state=object();budget=types.SimpleNamespace(state=state,finalizing=False)
        def finalize():budget.finalizing=True
        budget.begin_finalization=finalize
        runtime=types.SimpleNamespace(step_count=0,sim=types.SimpleNamespace(data=types.SimpleNamespace(time=0.)))
        d=types.SimpleNamespace(r=runtime,complete=complete,censored=False,planner=types.SimpleNamespace(receipts=[]),startup=types.SimpleNamespace(report=lambda:dict(fake=True)))
        calls=[]
        def step():
            calls.append(1)
            if error is not None:raise error
            runtime.step_count=steps;runtime.sim.data.time=steps*.005
        d.step_one=step
        watch=lambda:None;watch.state=state
        return d,budget,watch,types.SimpleNamespace(capture_if_due=lambda:None),calls
    def test_full_success_no_extra_physics(self):
        ns=exact_loop();d,b,w,v,c=self.fake(complete=True)
        r=ns['run_case'](d,watch=w,budget=b,video=v,scope_start_mono=time.monotonic(),enabled=True)
        self.assertTrue(r['full_case_success']);self.assertEqual(c,[]);self.assertEqual(r['root_terminal_receipts'],[]);self.assertTrue(b.finalizing)
    def test_original_exception_kept_no_retry(self):
        ns=exact_loop();err=ValueError('fake original failure');d,b,w,v,c=self.fake(error=err)
        with self.assertRaises(ns['CaseLoopError'])as caught:ns['run_case'](d,watch=w,budget=b,video=v,scope_start_mono=time.monotonic(),enabled=True)
        self.assertIs(caught.exception.original_error,err);self.assertEqual(c,[1]);self.assertFalse(caught.exception.receipt['full_case_success']);self.assertTrue(b.finalizing)
    def test_original_clock_jump_refused(self):
        ns=exact_loop();d,b,w,v,c=self.fake(steps=15000)
        with self.assertRaises(ns['CaseLoopError'])as caught:ns['run_case'](d,watch=w,budget=b,video=v,scope_start_mono=time.monotonic(),enabled=True)
        self.assertEqual(c,[1]);self.assertFalse(caught.exception.receipt['full_case_success']);self.assertTrue(b.finalizing)
    def test_original_finite_cap_is_censor_not_success(self):
        ns=exact_loop();d,b,w,v,c=self.fake()
        # Only exercise the loop's read-only finite-cap branch using a fake
        # watchdog; not evidence that any real watch advances native physics.
        def watch():d.r.step_count=15000;d.r.sim.data.time=75.
        watch.state=b.state
        r=ns['run_case'](d,watch=watch,budget=b,video=v,scope_start_mono=time.monotonic(),enabled=True)
        self.assertEqual(r['stop_reason'],'FINITE_MAIN_CENSORED');self.assertFalse(r['full_case_success']);self.assertEqual(c,[]);self.assertTrue(b.finalizing)
    def test_worker_full_result_mapping(self):
        tree=ast.parse((P/'worker.py').read_text());node=next(n for n in ast.walk(tree)if isinstance(n,ast.Call)and isinstance(n.func,ast.Attribute)and n.func.attr=='update'and any(k.arg=='case_loop'for k in n.keywords))
        for success in [False,True]:
            loop=dict(full_case_success=success,stop_reason='original-terminal');result={}
            exec(compile(ast.fix_missing_locations(ast.Module(body=[ast.Expr(node)],type_ignores=[])),'[actual-update-node]','exec'),dict(result=result,loop_receipt=loop))
            self.assertEqual(result['passed'],success);self.assertEqual(result['full_task_success'],success);self.assertIs(result['case_loop'],loop)
    def test_helper_and_identity_profile_exact_full(self):
        tree=ast.parse((P/'worker.py').read_text());helpers=ast.literal_eval(next(n.value for n in tree.body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='HELPER_NAMES'for t in n.targets)))
        self.assertEqual(len(helpers),24);self.assertEqual(len(set(helpers)),24);self.assertNotIn('boundary_driver',helpers);self.assertIn('push_l0_driver',helpers)
        calls=[n for n in ast.walk(tree)if isinstance(n,ast.Call)and isinstance(n.func,ast.Name)and n.func.id=='install']
        self.assertEqual(len(calls),1);self.assertIs(ast.literal_eval(next(k.value for k in calls[0].keywords if k.arg=='boundary_only')),False)

if __name__=='__main__':unittest.main()
