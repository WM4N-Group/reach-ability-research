"""Five new bounded source/provenance fixtures, no native qualification."""
from pathlib import Path
from types import SimpleNamespace
import tempfile,unittest
from public_geometry_provenance import public_geometry,DECLARING_SOURCE_SHA256
SOURCE=Path(__file__).resolve().parent.parent/'push-original-L0-parent-20261118-v1/standard_runtime.py'
def reg(size=(1.2,1.2,.2),body='push_box'):
    return SimpleNamespace(objects={'sdk_box':SimpleNamespace(body_name=body,size_m=size)})
class Geometry(unittest.TestCase):
    def test_default_off(self):self.assertIsNone(public_geometry())
    def test_exact_declared_mapping_and_real_source_SHA(self):
        g,s=public_geometry(reg(),source_path=SOURCE,enabled=True);self.assertEqual(g,{'push_box':(1.2,1.2,.2)});self.assertEqual(s,DECLARING_SOURCE_SHA256)
    def test_changed_dimensions_refused(self):
        with self.assertRaises(ValueError):public_geometry(reg((1.2,1.2,.4)),source_path=SOURCE,enabled=True)
    def test_changed_body_refused(self):
        with self.assertRaises(ValueError):public_geometry(reg(body='other_box'),source_path=SOURCE,enabled=True)
    def test_source_drift_refused(self):
        with tempfile.TemporaryDirectory()as tmp:
            p=Path(tmp)/'standard_runtime.py';p.write_bytes(SOURCE.read_bytes()+b'\n# changed\n')
            with self.assertRaises(ValueError):public_geometry(reg(),source_path=p,enabled=True)
if __name__=='__main__':unittest.main()
