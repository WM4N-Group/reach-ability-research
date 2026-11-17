"""NEW boundary-only control fixtures; not native or the earlier seven tests."""
from pathlib import Path
from types import SimpleNamespace as NS
import importlib.util
import sys
import time
import unittest

HERE = Path(__file__).resolve().parent
ROOT = Path(sys.argv[1]).resolve(strict=True)
sys.argv[1:] = []
sys.path[:0] = [str(HERE), str(ROOT/'push-L0-arm-admission-observer-20261118-v1'),
               str(ROOT/'push-original-L0-parent-20261118-v1'),
               str(ROOT/'push-original-L0-entry-20261118-v1'), str(ROOT/'push-standard-parent-20261118-v1')]
spec = importlib.util.spec_from_file_location('_boundary_only_new_cpu', HERE/'boundary_driver.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def objects(step):
    state = object()
    class Budget:
        finalizing = False
        def begin_finalization(self):
            self.finalizing = True
    budget = Budget(); budget.state = state
    class Watch:
        calls = 0
        def __call__(self):
            self.calls += 1
    watch = Watch(); watch.state = state
    class Video:
        calls = 0
        def capture_if_due(self):
            self.calls += 1
    video = Video()
    driver = NS(r=NS(step_count=0, sim=NS(data=NS(time=0.))), boundary_reached=False,
                loop=None, executor=None, factory=None,
                startup=NS(arm_gate_audit=None, report=lambda: dict(software_fixture=True)))
    driver.step_one = lambda: step(driver)
    return driver, watch, budget, video


class BoundaryOnly(unittest.TestCase):
    def test_default_off_does_not_construct_or_loop(self):
        self.assertIsNone(m.driver_class(enabled=False))
        self.assertIsNone(m.run_case(enabled=False))
        spec = importlib.util.spec_from_file_location('_arm_boundary_worker_default_off',HERE/'worker.py')
        worker = importlib.util.module_from_spec(spec);spec.loader.exec_module(worker)
        self.assertIsNone(worker.prepare(enabled=False))
        self.assertEqual(worker.QUESTION,'PUSH_ORIGINAL_L0_FIRST_ARM_GATE_BOUNDARY_SAME_CALL_OBSERVATION_ONLY')
        self.assertFalse({'torch','mujoco','pynvml','OpenGL'} & set(sys.modules))

    def test_connection_override_stops_at_witness_without_original_skill_connect(self):
        import ast
        calls = []
        marker = object()
        class Base:
            def __init__(self):
                self.r = NS(step_count=2,sim=NS(data=NS(time=.01)))
                self.loop = self.executor = self.factory = None
                self.startup = NS(r=self.r,witness=None,arm_gate_attempts=0,arm_gate_audit=None,
                    startup=NS(finished=True,failed=False,original_result=dict(stable=True),issued=2,last_two=[1,2]),
                    report=lambda:dict(software_fixture=True))
            def _connect_execution(self):
                raise AssertionError('Original skill connect must never be called')
            def _write_boundary(self,row):
                calls.append(row['event'])
        def constructor(owner):
            calls.append('constructor-once')
            owner.arm_gate_attempts+=1
            owner.arm_gate_audit=dict(original_guard_calls=1)
            return marker
        original,old_constructor=m._original_driver_class,m._OriginalL0Witness
        try:
            m._original_driver_class=lambda **kwargs:Base
            m._OriginalL0Witness=constructor
            driver=m.driver_class(enabled=True)()
            driver._connect_execution()
        finally:
            m._original_driver_class=original
            m._OriginalL0Witness=old_constructor
        self.assertTrue(driver.boundary_reached)
        self.assertEqual(driver.startup.arm_gate_attempts,1)
        self.assertEqual(calls,['constructor-once','original_arm_admission_boundary_reached_NO_SKILL_SELECTED'])
        self.assertIsNone(driver.executor)
        tree=ast.parse((HERE/'boundary_driver.py').read_bytes())
        connect=next(n for n in ast.walk(tree)if isinstance(n,ast.FunctionDef)and n.name=='_connect_execution')
        self.assertFalse(any(isinstance(n,ast.Call)and isinstance(n.func,ast.Attribute)and n.func.attr in ('finish','validate')for n in ast.walk(connect)))
        self.assertEqual(sum(isinstance(n,ast.Call)and isinstance(n.func,ast.Name)and n.func.id=='_OriginalL0Witness'for n in ast.walk(connect)),1)
        original_tree=ast.parse((ROOT/'push-original-L0-parent-20261118-v1/l0_witness.py').read_bytes())
        finish=next(n for n in ast.walk(original_tree)if isinstance(n,ast.FunctionDef)and n.name=='finish')
        old_needs=[n.value for n in finish.body if isinstance(n,ast.Expr)and isinstance(n.value,ast.Call)and isinstance(n.value.func,ast.Name)and n.value.func.id=='need'][:2]
        class Rename(ast.NodeTransformer):
            def visit_Name(self,node):
                return ast.copy_location(ast.Name(id='owner',ctx=node.ctx),node)if node.id=='self'else node
        expected=[ast.dump(Rename().visit(n),include_attributes=False)for n in old_needs]
        new_needs=[n.value for n in connect.body if isinstance(n,ast.Expr)and isinstance(n.value,ast.Call)and isinstance(n.value.func,ast.Name)and n.value.func.id=='need']
        actual=[ast.dump(n,include_attributes=False)for n in new_needs]
        self.assertTrue(all(n in actual for n in expected),'Both exact original finish preconditions retained')

    def test_boundary_completion_is_not_skill_success_or_additional_step(self):
        def step(driver):
            driver.r.step_count += 1
            driver.r.sim.data.time += .005
            if driver.r.step_count == 2:
                driver.boundary_reached = True
        driver, watch, budget, video = objects(step)
        result = m.run_case(driver, watch=watch, budget=budget, video=video,
                            scope_start_mono=time.monotonic(), enabled=True)
        self.assertFalse(result['full_case_success'])
        self.assertTrue(result['diagnostic_boundary_reached'])
        self.assertEqual(result['driver_calls'], 2)
        self.assertEqual(video.calls, 2)
        self.assertEqual(result['root_terminal_receipts'], [])
        self.assertTrue(budget.finalizing)

    def test_original_refusal_is_preserved_and_never_retried(self):
        error = ValueError('synthetic gate refusal, not 3b405 data')
        calls = []
        def step(driver):
            calls.append(1)
            driver.startup.arm_gate_audit = dict(sample_complete=True, stage='ORIGINAL_GUARD_RETURNED')
            raise error
        driver, watch, budget, video = objects(step)
        with self.assertRaises(m.CaseLoopError) as caught:
            m.run_case(driver, watch=watch, budget=budget, video=video,
                       scope_start_mono=time.monotonic(), enabled=True)
        self.assertIs(caught.exception.original_error, error)
        self.assertTrue(caught.exception.receipt['diagnostic_guard_returned'])
        self.assertFalse(caught.exception.receipt['full_case_success'])
        self.assertEqual(calls, [1])
        self.assertEqual(video.calls, 0)
        self.assertTrue(budget.finalizing)

    def test_terminal_no_executor_profile_keeps_identity_boundary_and_blocks_queries(self):
        import ast
        from contextlib import nullcontext
        tree = ast.parse((HERE/'boundary_install.py').read_bytes())
        install = next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='install')
        connect = next(n for n in install.body if isinstance(n,ast.FunctionDef) and n.name=='connect')
        judge = next(n for n in install.body if isinstance(n,ast.FunctionDef) and n.name=='judge')
        calls = []
        driver = NS(executor=None,loop=None,factory=None,boundary_reached=True)
        def need(ok, message):
            if not ok: raise ValueError(message)
        env = dict(driver=driver,need=need,boundary_only=True,
                   engine=NS(boundary=lambda *args: nullcontext()),
                   original_connect=lambda *args,**kwargs: calls.append('original') or 'result',
                   wrap_start=lambda executor: calls.append('wrap-executor'),
                   original_judge=lambda *args,**kwargs: calls.append('judge'))
        exec(compile(ast.Module(body=[connect,judge],type_ignores=[]),'<source-boundary-profile>','exec'),env)
        self.assertEqual(env['connect'](driver), 'result')
        self.assertEqual(calls, ['original'])
        with self.assertRaises(ValueError): env['judge'](driver)
        driver.boundary_reached=False
        with self.assertRaises(ValueError): env['connect'](driver)
        env['boundary_only']=False
        driver.executor=object()
        env['connect'](driver)
        self.assertEqual(calls[-1], 'wrap-executor')

    def test_resource_stamp_uses_oldest_atomic_pair_not_completed_and_no_extra_probe(self):
        import ast
        from collections import namedtuple
        tree = ast.parse((HERE/'boundary_install.py').read_bytes())
        callback = next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='data_resource_watch_callbacks')
        Stamp = namedtuple('Stamp','epoch checked_at expires_at active')
        def need(ok, message):
            if not ok: raise ValueError(message)
        env = dict(need=need,OwnerStamp=Stamp)
        exec(compile(ast.Module(body=[callback],type_ignores=[]),'<source-owner-stamp>','exec'),env)
        class Watch:
            max_stale=2.
            token=object()
            last_ok=10.7
            last_observation_stamp=(10.,10.7)
            calls=0
            def check(self, token):
                self.calls+=1
                assert token is self.token
        watch=Watch()
        fast,ack=env['data_resource_watch_callbacks'](watch,epoch='software-only')
        stamp=fast(None)
        self.assertEqual(stamp.checked_at,10.)
        self.assertEqual(stamp.expires_at,12.)
        self.assertEqual(watch.calls,1)
        ack(None)
        self.assertEqual(watch.calls,2)  # Cheap check, not another hardware/composite probe.
        watch.last_observation_stamp=None
        with self.assertRaises(ValueError):fast(None)

    def test_expired_cap_censors_before_any_issue(self):
        def step(driver):
            raise AssertionError('No issue after cap')
        driver, watch, budget, video = objects(step)
        result = m.run_case(driver, watch=watch, budget=budget, video=video,
                            scope_start_mono=time.monotonic()-301., enabled=True)
        self.assertEqual(result['driver_calls'], 0)
        self.assertEqual(result['stop_reason'], 'FINITE_BOUNDARY_DIAGNOSTIC_CENSORED')
        self.assertFalse(result['full_case_success'])
        self.assertEqual(video.calls, 0)


if __name__ == '__main__':
    unittest.main()
