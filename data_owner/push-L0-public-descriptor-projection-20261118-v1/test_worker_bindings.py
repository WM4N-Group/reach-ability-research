"""Three new constructor/phase binding fixtures, no thread/probe/native calls."""
from pathlib import Path
from types import SimpleNamespace
import ast,math,os,threading,time,unittest
from worker_binding_fixes import patched_worker_source
P=Path(__file__).resolve().parent;OLD=P.parent/'push-prepared-L0-full-half-second-start-20261118-v3/worker.py'
class PolicyStop(RuntimeError):pass
class State:
    def fail(self,message):raise PolicyStop(message)
def need(x,message):
    if not x:raise PolicyStop(message)
def watch_class():
    p=P.parent/'resource-start-cadence-20261118-v1/resource_watch.py';node=next(n for n in ast.parse(p.read_text()).body if isinstance(n,ast.ClassDef)and n.name=='ResourceWatch');ns=dict(os=os,threading=threading,time=time,math=math,PolicyStop=PolicyStop)
    exec(compile(ast.Module(body=[node],type_ignores=[]),'[original-constructor-only-no-start]','exec'),ns);return ns['ResourceWatch']
def constructor(source):
    call=next(n for n in ast.walk(ast.parse(source))if isinstance(n,ast.Call)and isinstance(n.func,ast.Name)and n.func.id=='ResourceWatch')
    return eval(compile(ast.Expression(call),'[actual-caller-kwargs-fixture]','eval'),dict(ResourceWatch=watch_class(),probe=lambda:None,state=State(),object=object,phase_health=lambda:True,c={'resource_poll_s':.5,'resource_oldest_max_age_s':2.}))
def phase_function(source,phase,skill):
    node=next(n for n in ast.walk(ast.parse(source))if isinstance(n,ast.FunctionDef)and n.name=='phase_health');calls=[];ns=dict(health=lambda:calls.append(1),state=State(),driver=SimpleNamespace(executor=SimpleNamespace(option=SimpleNamespace(skill=skill))),need=need,phase=phase,c=dict(full_original_task_execution=True,boundary_only_no_task_skill=False))
    exec(compile(ast.Module(body=[node],type_ignores=[]),'[actual-phase-health-source-fixture]','exec'),ns);return ns['phase_health'],calls
class Binding(unittest.TestCase):
    def test_default_OFF(self):self.assertIsNone(patched_worker_source())
    def test_actual_constructor_exposes_old_label_only_and_new_real_half_s(self):
        before=constructor(OLD.read_text());after=constructor(patched_worker_source(OLD.read_text(),enabled=True))
        self.assertEqual(before.interval,1.);self.assertEqual(after.interval,.5);self.assertEqual(before.max_stale,after.max_stale);self.assertEqual(after.max_stale,2.);self.assertIsNone(after.thread);self.assertEqual(after.probe_calls,0)
    def test_full_PUSH_allowed_but_health_zero_NAV_gates_preserved(self):
        old,oldcalls=phase_function(OLD.read_text(),'main','PUSH')
        with self.assertRaises(PolicyStop):old()
        self.assertEqual(oldcalls,[1]);s=patched_worker_source(OLD.read_text(),enabled=True);good,calls=phase_function(s,'main','PUSH');self.assertTrue(good());self.assertEqual(calls,[1])
        for phase,skill in [('zero','PUSH'),('main','NAV')]:
            bad,calls=phase_function(s,phase,skill)
            with self.assertRaises(PolicyStop):bad()
            self.assertEqual(calls,[1])
if __name__=='__main__':unittest.main()
