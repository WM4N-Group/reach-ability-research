"""Software children only: never simulation, training or encoder/native dispatch."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from controlled_process import ControlledProcess
from scoped_io import ScopeIO, PolicyStop


class Outputs(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='data-output-test-')
        self.root = Path(self.tmp.name)
        self.b = ScopeIO(self.root, cap_bytes=1024*1024, reserve_bytes=262144)
    def tearDown(self):
        self.tmp.cleanup()
    def child(self, code, **kw):
        return ControlledProcess([sys.executable, '-I', '-B', '-c', code], self.b,
            stdout_path='out.bin', stderr_path='err.bin', enabled=True, **kw)
    def test_dual_large_pipe_no_deadlock(self):
        p = self.child("import os\nfor i in range(100):\n os.write(1,b'x'*2048);os.write(2,b'y'*2048)")
        r = p.finish(timeout_s=5.)
        self.assertTrue(r['complete'])
        self.assertEqual((self.root/'out.bin').read_bytes(), b'x'*204800)
        self.assertEqual((self.root/'err.bin').read_bytes(), b'y'*204800)
        self.assertEqual(self.b.reconcile(), 409600)
    def test_over_cap_latches_and_terminates_only_own_child(self):
        p = self.child("import os\nwhile True: os.write(1,b'x'*8192)")
        with self.assertRaises(PolicyStop) as e:
            p.finish(timeout_s=5.)
        self.assertFalse(e.exception.receipt['complete'])
        self.assertIsNotNone(p.process.poll())
        self.assertLess(self.b.used, self.b.cap-self.b.reserve)
        self.assertIsNotNone(self.b.state.reason)
        self.assertGreater(e.exception.receipt['streams']['stdout']['refused_bytes'],0)
    def test_timeout_records_incomplete(self):
        p = self.child('import time;time.sleep(10)')
        with self.assertRaises(PolicyStop) as e:
            p.finish(timeout_s=.05)
        self.assertTrue(e.exception.receipt['timed_out'])
    def test_nonzero_not_success(self):
        p = self.child("import os;os.write(2,b'failed');raise SystemExit(7)")
        with self.assertRaises(PolicyStop) as e:
            p.finish(timeout_s=5.)
        self.assertEqual(e.exception.receipt['returncode'], 7)
        self.assertEqual((self.root/'err.bin').read_bytes(), b'failed')
    def test_stdin_pipe_no_parent_counter_in_child(self):
        p = self.child('import sys;sys.stdout.buffer.write(sys.stdin.buffer.read())',stdin=subprocess.PIPE)
        p.stdin.write(b'abc\xe5\xad\x97');p.stdin.close()
        self.assertTrue(p.finish(timeout_s=5.)['complete'])
        self.assertEqual(self.b.reconcile(),6)
    def test_disabled_no_files_or_child(self):
        with self.assertRaises(ValueError):
            ControlledProcess([sys.executable],self.b,stdout_path='a',stderr_path='b')
        self.assertEqual(list(self.root.iterdir()),[])
    def test_missing_executable_closes_handles(self):
        with self.assertRaises(FileNotFoundError):
            ControlledProcess(['/no-such-executable'],self.b,stdout_path='a',stderr_path='b',enabled=True)
        self.assertEqual(self.b.active,set())
    def test_final_report_drain_after_irreversible_seal(self):
        self.b.begin_finalization()
        p=self.child("import os;os.write(1,b'encoder-fixture-not-video')")
        self.assertTrue(p.finish(timeout_s=5.)['complete'])
        self.assertEqual(self.b.reconcile(),25)
        with self.assertRaises(PolicyStop):self.b.state.check()

if __name__=='__main__':unittest.main()
