"""Composition of actual Data watch with AINav callbacks; external probes synthetic.
No mock ResourceWatch, no native lease claim. Does not install the native driver.
"""
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parent))
sys.path.insert(0,os.environ['AINAV_INDEXED_GUARD_ROOT'])
from scoped_io import ScopeIO,PolicyStop
from resource_watch import ResourceWatch
from install_fresh_driver import data_resource_watch_callbacks

class Bridge(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='data-watch-bridge-')
        self.root=Path(self.tmp.name)
        self.b=ScopeIO(self.root,cap_bytes=1024**2,reserve_bytes=262144)
        self.probes=0;self.healthy=True
        def probe():
            self.probes+=1
            if not self.healthy:raise RuntimeError('SYNTHETIC external revocation')
            self.b.reconcile()
        self.w=ResourceWatch(probe,state=self.b.state,token=object(),fast_health=lambda:True)
        self.w.probe_once()
        self.fast,self.ack=data_resource_watch_callbacks(self.w,epoch='SOFTWARE_scope_authority_epoch')
    def tearDown(self):
        self.w.close();self.tmp.cleanup()
    def test_original_success_timestamp_no_duplicate_external_probe(self):
        at=self.w.last_observation_stamp[0]
        for _ in range(1000):
            stamp=self.fast(None);self.ack(None)
            self.assertEqual((stamp.checked_at,stamp.valid_until),(at,at+2.))
        self.assertEqual(self.probes,1)
    def test_actual_probe_failure_latches_both_callbacks(self):
        self.healthy=False
        with self.assertRaises(PolicyStop):self.w.probe_once()
        for callback in(self.fast,self.ack):
            with self.assertRaises(PolicyStop):callback(None)
    def test_unknown_output_latches_at_reconcile_not_silently_rebased(self):
        (self.root/'foreign').write_bytes(b'out-of-band fixture')
        with self.assertRaises(PolicyStop):self.w.probe_once()
        with self.assertRaises(PolicyStop):self.fast(None)
    def test_stale_uses_genuine_age_no_self_refresh(self):
        now=time.monotonic();self.w.last_observation_stamp=(now-2.01,now-.01);self.w.last_ok=now-.01
        with self.assertRaises(PolicyStop):self.fast(None)
        self.assertEqual(self.probes,1)
    def test_finalization_seal_denies_both_callbacks(self):
        self.b.begin_finalization()
        for callback in(self.fast,self.ack):
            with self.assertRaises(PolicyStop):callback(None)
    def test_foreign_process_token_denied(self):
        self.w.token=object()
        with self.assertRaises(PolicyStop):self.fast(None)
    def test_real_periodic_thread_refreshes_without_guard_probes(self):
        # A short explicit SOFTWARE interval, same <=2s freshness requirement.
        self.w.interval=.02
        self.w.start()
        before=self.w.last_ok
        deadline=time.monotonic()+1.
        while self.w.last_ok==before and time.monotonic()<deadline:time.sleep(.005)
        self.assertGreater(self.w.last_ok,before)
        n=self.probes
        self.fast(None);self.ack(None)
        self.assertGreaterEqual(self.probes,n)

if __name__=='__main__':unittest.main()
