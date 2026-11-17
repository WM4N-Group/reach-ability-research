"""Only new no-world diagnostic opt-in/config rejection; not old6-case suite."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

P = Path(__file__).with_name('cold_library_probe.py')

class ColdDiagnosticPreparation(unittest.TestCase):
    def test_disabled_import_and_cli_do_not_load_GPU_or_lease(self):
        code = """
import importlib.util,sys
s=importlib.util.spec_from_file_location('new_cold_probe',sys.argv[1]);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
assert m.run(enabled=False) is None and m.prepare(enabled=False) is None
assert not any(n in sys.modules for n in ('torch','mujoco','per_gpu_lease','resource_watch'))
"""
        subprocess.run([sys.executable, '-I', '-B', '-c', code, str(P)], check=True, capture_output=True)
        out = subprocess.run([sys.executable, '-I', '-B', str(P)], check=True, capture_output=True)
        self.assertEqual(out.stdout, b'')
        self.assertEqual(out.stderr, b'')

    def test_wrong_question_rejected_before_any_import_or_freeze_read(self):
        spec=importlib.util.spec_from_file_location('new_cold_probe',P)
        m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
        with tempfile.TemporaryDirectory() as d:
            c=Path(d)/'config.json';c.write_text(json.dumps({'question':'old-D3','owner':m.OWNER}))
            with self.assertRaisesRegex(RuntimeError,'New explicit diagnostic identity'):
                m.prepare(c, 'not-a-freeze', enabled=True)

class ColdControllerCAS(unittest.TestCase):
    def test_real_temp_CAS_keeps_peers_and_mode(self):
        p=P.with_name('cold_probe_control.py')
        spec=importlib.util.spec_from_file_location('new_cold_control',p)
        m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
        with tempfile.TemporaryDirectory() as d:
            m.H=Path(d)/'H.json'
            before={'executing_thread_id':m.OWNER,'peer':{'active':False,'original_unknown':None}}
            m.H.write_text(json.dumps(before));m.H.chmod(0o640)
            def add(h):
                h[m.KEY]={'active':False};return h
            receipt=m.cas(add)
            after=json.loads(m.H.read_bytes())
            self.assertEqual(after['peer'],before['peer'])
            self.assertTrue(receipt['all_peer_old_fields_preserved'] and receipt['mode_preserved'])
            self.assertEqual(m.H.stat().st_mode & 0o7777,0o640)
            old=m.H.read_bytes()
            def wrong(h):
                h['peer']['original_unknown']=0;return h
            with self.assertRaises(AssertionError):m.cas(wrong)
            self.assertEqual(m.H.read_bytes(),old)

if __name__ == '__main__':
    unittest.main()
