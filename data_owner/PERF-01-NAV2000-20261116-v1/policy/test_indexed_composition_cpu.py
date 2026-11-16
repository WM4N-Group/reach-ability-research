"""Actual AINav adapter + actual Data watch/budget, SOFTWARE driver only.
Reuse the source owner's exact original-guard fixture; never load native/model.
"""
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parent))
ainav=Path(os.environ['AINAV_INDEXED_GUARD_ROOT'])
sys.path.insert(0,str(ainav))
from scoped_io import ScopeIO,PolicyStop
from resource_watch import ResourceWatch
from runner_outputs import write_json
from indexed_guard import GuardViolation
from install_fresh_driver import install,data_resource_watch_callbacks
spec=importlib.util.spec_from_file_location('_data_ainav_software_fixture',ainav/'tests/test_install_fresh_driver.py')
fixtures=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixtures)

class Combined(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.Tests()
        self.fixture.setUp()
        self.driver=self.fixture.driver
        self.tmp=tempfile.TemporaryDirectory(prefix='data-indexed-combined-')
        self.b=ScopeIO(self.tmp.name,cap_bytes=1024**2,reserve_bytes=262144)
        self.probes=0
        def probe():
            self.probes+=1;self.b.reconcile()
        self.w=ResourceWatch(probe,state=self.b.state,token=object(),fast_health=lambda:True)
        self.w.probe_once()
        fast,ack=data_resource_watch_callbacks(self.w,epoch='SOFTWARE_combined_not_native_lease')
        def tokens(host):
            return dict(session=None if host.executor is None else host.executor.session,
                target=None,goal='FAKE_GOAL',config_epoch='FAKE_CONFIG',queue=host.r.sim.queue)
        install(self.driver,enabled=True,files=self.fixture.files,owner_fast=fast,owner_refresh=ack,tokens=tokens)
        self.engine=type(self.driver)._native_guards.engine
    def tearDown(self):
        if hasattr(self,'engine'):self.engine.close()
        if hasattr(self,'w'):self.w.close()
        if hasattr(self,'tmp'):self.tmp.cleanup()
        self.fixture.doCleanups()
    def test_controlled_output_and_gated_step_no_repeated_external_probe(self):
        write_json(self.b,'progress.json',dict(role='SOFTWARE_FIXTURE'))
        for _ in range(50):self.driver.r.step('SOFTWARE_COMMAND')
        self.assertEqual(self.probes,1)
        self.assertEqual(self.driver.r.step_count,50)
    def test_revoke_before_next_original_issue(self):
        self.b.state.reason='synthetic revocation'
        with self.assertRaises((PolicyStop,GuardViolation)):self.driver.r.step('DO_NOT_ISSUE')
        self.assertEqual(self.driver.r.step_count,0)
    def test_finalization_denies_original_issue(self):
        self.b.begin_finalization()
        with self.assertRaises((PolicyStop,GuardViolation)):self.driver.r.step('DO_NOT_ISSUE')
        self.assertEqual(self.driver.r.step_count,0)
    def test_foreign_runtime(self):
        from types import SimpleNamespace
        self.driver.r=SimpleNamespace(sim=self.driver.r.sim)
        with self.assertRaises(GuardViolation):self.driver._native_guards()
    def test_foreign_queue_before_issue(self):
        self.driver.r.sim.queue=[]
        with self.assertRaises(GuardViolation):self.driver.r.step('DO_NOT_ISSUE')
        self.assertEqual(self.driver.r.step_count,0)
    def test_foreign_session_after_authorized_no_step_boundary(self):
        self.driver._connect_execution();self.driver.executor.start(object())
        self.driver.executor.session=object()
        with self.assertRaises(GuardViolation):self.driver.r.step('DO_NOT_ISSUE')
        self.assertEqual(self.driver.r.step_count,0)

if __name__=='__main__':unittest.main()
