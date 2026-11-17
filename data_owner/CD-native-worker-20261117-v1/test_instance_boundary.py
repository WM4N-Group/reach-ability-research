"""One new Data instance-hook integration check, synthetic engine/driver only."""
import importlib.util
from contextlib import contextmanager
from pathlib import Path
import sys
from types import MethodType,SimpleNamespace as NS
import unittest
from unittest.mock import patch
HERE=Path(__file__).resolve().parent
GUARD=Path('/home/yuanyue/main/code/reach-ability-research/data_owner/perf-output-integration-20261116-v1/evidence/AINav-reviewed-local-cpu-snapshot/development/indexed_identity_guard_v1')


class TestInstanceHook(unittest.TestCase):
    def test_real_installer_enters_boundary_and_calls_task_instance_hook_once(self):
        with patch.object(sys,'path',[str(GUARD),*sys.path]):
            spec=importlib.util.spec_from_file_location('_cd_actual_installer_source',HERE/'cd_install_fresh_driver.py')
            module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        events=[]
        class Previous:
            state=_pool=None;closed=failed=False
            original=lambda *a:None
            def close(self):events.append('old_guard_closed')
        class Engine:
            def __init__(self):self.depth=0
            @contextmanager
            def boundary(self,driver,label):
                self.depth+=1;events.append('boundary_enter')
                try:yield
                finally:self.depth-=1;events.append('boundary_exit')
            def before_issue(self,driver):events.append('preissue')
            def seal(self,driver,label):return {'sealed':True}
        engine=Engine();previous=Previous()
        class Driver:
            _native_guards=NS(engine=previous)
            source_receipt={}
            def _connect_execution(self):raise AssertionError('must not bypass instance DEV task hook')
            def judge_intent(self,*a):return 'original-judge'
        d=Driver();d.r=NS(step_count=0,sim=NS(data=NS(time=0.)),step=lambda command:events.append('physical_step'));d.executor=None
        def task(this):
            self.assertIs(this,d);self.assertEqual(engine.depth,1);events.append('DEV_task_hook')
            d.executor=NS(start=lambda *a:None,session=None)
            return 'original-result'
        d._connect_execution=MethodType(task,d)
        with patch.object(module,'make_indexed_guard',return_value=NS(engine=engine)):
            receipt=module.install(d,enabled=True,tokens=lambda host:{})
        self.assertTrue(receipt['sealed']);self.assertEqual(d._connect_execution(),'original-result')
        self.assertEqual(events,['old_guard_closed','boundary_enter','DEV_task_hook','boundary_exit'])
        d.r.step('command');self.assertEqual(events[-2:],['preissue','physical_step'])


if __name__=='__main__':unittest.main(verbosity=2)
