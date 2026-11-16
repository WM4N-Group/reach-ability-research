"""Same-process pure IO: no child, model, Runtime, renderer or physics."""
import ctypes
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from scoped_io import ScopeIO,PolicyStop
from runner_outputs import write_json,finish_accounting
from fd_capture import FDCapture

class CaptureTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='data-fd-software-');self.root=Path(self.tmp.name)
        self.b=ScopeIO(self.root,cap_bytes=2*1024**2,reserve_bytes=524288)
        self.capture=None
    def tearDown(self):
        if self.capture is not None and not self.capture.closed:
            self.b.begin_finalization()
            try:self.capture.close()
            except PolicyStop:pass
        self.tmp.cleanup()
    def install(self):
        self.capture=FDCapture(self.b,enabled=True);return self.capture
    def finish(self):
        self.b.begin_finalization();return self.capture.close()
    def test_Python_OS_C_stdio_and_same_counter_metadata(self):
        c=self.install()
        print('Python字节',end='\n',flush=True)
        os.write(1,b'os.stdout\n');os.write(2,b'os.stderr\n')
        c.libc.puts.argtypes=[ctypes.c_char_p];c.libc.puts.restype=ctypes.c_int
        c.libc.puts(b'C.stdio')
        write_json(self.b,'progress.json',dict(actual='SYNTHETIC_IO_FIXTURE'))
        r=self.finish();self.assertTrue(r['complete'])
        self.assertEqual((self.root/'stdout.bin').read_bytes(),'Python字节\nos.stdout\nC.stdio\n'.encode())
        self.assertEqual((self.root/'stderr.bin').read_bytes(),b'os.stderr\n')
        self.assertEqual(self.b.reconcile(),sum(p.stat().st_size for p in self.root.iterdir()))
    def test_cap_error_drains_printing_error_path_no_deadlock(self):
        self.b=ScopeIO(self.root,cap_bytes=1024**2,reserve_bytes=524288)
        c=self.install();chunk=b'x'*8192
        for _ in range(160):
            offset=0
            while offset<len(chunk):offset+=os.write(1,chunk[offset:])
        self.b.begin_finalization()
        with self.assertRaises(PolicyStop)as e:c.close()
        self.assertFalse(e.exception.receipt['complete'])
        self.assertGreater(e.exception.receipt['streams']['stdout']['discarded_after_error_bytes'],0)
        self.assertLess(self.b.used,self.b.cap-self.b.reserve)
        with self.assertRaises(PolicyStop):self.b.state.check()
    def test_cannot_close_before_native_seal(self):
        c=self.install()
        with self.assertRaises(PolicyStop):c.close()
        self.assertFalse(c.closed);self.finish()
    def test_disabled_no_files_or_FD_changes(self):
        with self.assertRaises(ValueError):FDCapture(self.b)
        self.assertEqual(list(self.root.iterdir()),[])
    def test_duplicate_capture_refused(self):
        self.install()
        with self.assertRaises(PolicyStop):FDCapture(self.b,enabled=True)
        self.finish()
    def test_native_failure_can_still_drain_and_preserve_failure(self):
        c=self.install();os.write(1,b'before stop')
        deadline=time.monotonic()+1.
        while c.rows['stdout']['written_bytes']!=11 and time.monotonic()<deadline:time.sleep(.001)
        self.b.state.reason='SYNTHETIC original native gate failure'
        self.b.begin_finalization();r=c.close()
        self.assertTrue(r['complete']);self.assertIsNotNone(self.b.state.reason)
        write_json(self.b,'result.json',dict(native_pass=False,error=self.b.state.reason))
        self.assertGreater(self.b.reconcile(),11)
    def test_restore_original_FD_identity(self):
        before=[(os.fstat(i).st_dev,os.fstat(i).st_ino,os.get_inheritable(i))for i in(1,2)]
        self.install();self.finish()
        after=[(os.fstat(i).st_dev,os.fstat(i).st_ino,os.get_inheritable(i))for i in(1,2)]
        self.assertEqual(before,after)
    def test_exact_final_accounting_includes_itself_after_capture(self):
        c=self.install();os.write(1,b'exact counted output');self.finish()
        write_json(self.b,'result.json',dict(software=True))
        value=finish_accounting(self.b,self.root/'final-accounting.json')
        self.assertEqual(value['final_controlled_logical_bytes'],sum(p.stat().st_size for p in self.root.iterdir()))
        self.assertEqual(value['controlled_logical_highwater_bytes'],self.b.highwater)
    def test_too_small_reserve_refuses_before_execution(self):
        b=ScopeIO(self.root,cap_bytes=65536,reserve_bytes=1024,max_open=4,text_buffer_bytes=16)
        with self.assertRaises(ValueError):FDCapture(b,enabled=True)
        self.assertEqual(b.active,set())

if __name__=='__main__':unittest.main()
