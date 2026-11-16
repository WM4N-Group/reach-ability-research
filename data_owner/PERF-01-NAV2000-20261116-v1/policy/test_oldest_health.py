import math
import os
from pathlib import Path
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from scoped_io import StopState,PolicyStop
from resource_watch import ResourceWatch
from fast_health import make_original_fast_health

class Oldest(unittest.TestCase):
    def test_slow_probe_cannot_rejuvenate_on_completion(self):
        clock=[10.];state=StopState()
        def probe():clock[0]+=2.01
        w=ResourceWatch(probe,state=state,token=object(),clock=lambda:clock[0])
        with self.assertRaises(PolicyStop):w.probe_once()
        self.assertIsNone(w.last_observation_stamp)
    def test_fresh_completion_old_observation_expires(self):
        clock=[10.];state=StopState()
        def probe():clock[0]+=1.9
        w=ResourceWatch(probe,state=state,token=object(),clock=lambda:clock[0]);w.probe_once()
        self.assertEqual(w.last_observation_stamp,(10.,11.9))
        clock[0]=12.01
        with self.assertRaises(PolicyStop):w()
    def test_atomic_success_pair_and_no_reprobe(self):
        clock=[10.];state=StopState();calls=[]
        def probe():calls.append(1);clock[0]+=.2
        w=ResourceWatch(probe,state=state,token=object(),clock=lambda:clock[0]);w.probe_once()
        for _ in range(1000):w()
        self.assertEqual(calls,[1]);self.assertEqual(w.last_observation_stamp,(10.,10.2))
    def test_completion_only_timestamp_refused(self):
        w=ResourceWatch(lambda:None,state=StopState(),token=object());w.last_ok=time.monotonic()
        with self.assertRaises(PolicyStop):w()

class Health(unittest.TestCase):
    def make(self,cuda=None,**kwargs):
        self.state=StopState();self.clock=[10.]
        if cuda is None:cuda=SimpleNamespace(is_initialized=lambda:False)
        return make_original_fast_health(SimpleNamespace(cuda=cuda),state=self.state,start_mono=10.,wall_cap_s=60.,rss_cap_bytes=8*1024**3,gpu_cap_bytes=3*1024**3,clock=lambda:self.clock[0],**kwargs)
    def test_true_RSS_and_never_initialize_CUDA(self):
        health=self.make();self.assertTrue(health());self.assertGreater(health.metrics['peak_RSS_bytes'],0)
        self.assertFalse(health.metrics['CUDA_seen_initialized'])
    def test_original_wall_teardown_reserve(self):
        health=self.make();self.clock[0]=40.
        with self.assertRaises(PolicyStop):health()
    def test_explicit_GPU_highwater_overcap(self):
        cuda=SimpleNamespace(is_initialized=lambda:True,memory_reserved=lambda **_:1,max_memory_reserved=lambda **_:3*1024**3+1)
        health=self.make(cuda)
        with self.assertRaises(PolicyStop):health()
    def test_GPU_unknown_not_zero(self):
        cuda=SimpleNamespace(is_initialized=lambda:True,memory_reserved=lambda **_:None,max_memory_reserved=lambda **_:0)
        health=self.make(cuda)
        with self.assertRaises(PolicyStop):health()
    def test_CPU_to_initialized_valid_and_regression_denied(self):
        initialized=[False];cuda=SimpleNamespace(is_initialized=lambda:initialized[0],memory_reserved=lambda **_:3,max_memory_reserved=lambda **_:4)
        health=self.make(cuda);health();initialized[0]=True;health()
        self.assertEqual(health.metrics['peak_Torch_reserved_bytes'],4)
        initialized[0]=False
        with self.assertRaises(PolicyStop):health()
    def test_None_health_forbidden(self):
        with self.assertRaises(ValueError):make_original_fast_health(None,state=StopState(),start_mono=10.,wall_cap_s=60.,rss_cap_bytes=1,gpu_cap_bytes=1)

if __name__=='__main__':unittest.main()
