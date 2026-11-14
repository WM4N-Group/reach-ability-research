import importlib.util
import io
import json
from pathlib import Path
import tempfile
import subprocess
import sys
import unittest
from unittest.mock import patch
import numpy as np
import fcntl

HERE=Path(__file__).resolve().parent

def module(name):
    spec=importlib.util.spec_from_file_location('reach_runtime_'+name,HERE/(name+'.py'))
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value

video=module('native_video');entry=module('runtime_entry')

class FakeProcess:
    def __init__(self,*a,**k):self.stdin=io.BytesIO()
    def wait(self,timeout):return 0


class RuntimePreparationTests(unittest.TestCase):
    def test_isolated_resource_waiter_cli_imports_owned_runtime_without_world(self):
        p=subprocess.run([sys.executable,'-I','-B',str(HERE/'schedule_zero_once.py'),'--help'],capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertIn('--wait-s',p.stdout)

    def test_native_frame_bytes_only_no_state_reconstruction_or_padding(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(video.subprocess,'Popen',FakeProcess):
            v=video.NativeCameraVideo(tmp,4,2,10.)
            image=np.arange(24,dtype=np.uint8).reshape(2,4,3)
            v.write(image,0.);v.write(image,.1);v.write(image,.1)
            self.assertEqual(v.frames,2);self.assertEqual(v.duplicates,1)
            self.assertEqual(v.proc.stdin.getvalue(),image.tobytes()*2)
            v.close();p=json.loads((Path(tmp)/'native-camera-provenance.json').read_text())
            self.assertFalse(p['log_or_state_reconstruction']);self.assertFalse(p['interpolation_or_padding'])

    def test_missing_native_frame_is_not_interpolated(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(video.subprocess,'Popen',FakeProcess):
            v=video.NativeCameraVideo(tmp,4,2);image=np.zeros((2,4,3),np.uint8);v.write(image,0.)
            with self.assertRaises(RuntimeError):v.write(image,.2)
            self.assertEqual(v.frames,1);v.close()

    def test_no_rgb_resize_or_dtype_coercion(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(video.subprocess,'Popen',FakeProcess):
            v=video.NativeCameraVideo(tmp,4,2)
            for bad in (np.zeros((2,4,3),float),np.zeros((3,4,3),np.uint8)):
                with self.assertRaises(ValueError):v.write(bad,0.)
            v.write(np.zeros((2,4,3),np.uint8),0.);v.close()

    def test_resource_busy_snapshot_releases_partial_locks_and_starts_no_world(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);names=['first.lock','second.lock']
            for name in names:(root/name).touch()
            with (root/names[1]).open('r+') as held:
                fcntl.flock(held,fcntl.LOCK_EX|fcntl.LOCK_NB)
                r=entry.readiness(root,names);self.assertFalse(r['available'])
                with (root/names[0]).open('r+') as check:fcntl.flock(check,fcntl.LOCK_EX|fcntl.LOCK_NB)
            self.assertEqual({p.name for p in root.iterdir()},set(names))

    def test_resource_available_is_snapshot_not_permission_or_claim(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'first.lock').touch();r=entry.readiness(root,['first.lock'])
            self.assertTrue(r['available']);self.assertTrue(r['snapshot_only'])
            self.assertEqual(len(list(root.iterdir())),1)

    def test_main_refuses_before_world_or_claim_without_new_admission(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'A').mkdir();(root/'A/main-admission.json').write_text('{"admitted":false}')
            with patch.object(entry.sys,'argv',['entry','--release',str(root),'--arm','A','--mode','main']):
                with self.assertRaisesRegex(ValueError,'NOT admitted'):entry.main()
            self.assertFalse(list(root.rglob('*.claim')))


if __name__=='__main__':unittest.main()
