"""Software-only interface regression; no tensors/native/Actor/world."""
from pathlib import Path
import tempfile,importlib.util,json,unittest
P=Path('/home/yuanyue/main/work/data-team/workers/T-COMPLEX-01-full-program-46308-20261115-v1/private_catalog_writer.py');spec=importlib.util.spec_from_file_location('private_adapter',P);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Recorder:
 def __init__(self):self.rows=[]
 def append_visual(self,packet,**kw):self.rows.append((packet,kw))
 def close(self,**kwargs):return kwargs
class Boundary(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.r=Recorder();self.w=m.PrivateCatalogWriter(self.r,Path(self.tmp.name)/'original.jsonl');self.catalog=dict(schema='ainav-private-registered-object-catalog-v1',model_input=False,control_tick=0,time_s=0.,objects=[dict(object_id='fixture_only')])
 def tearDown(self):self.w.original_catalog.close();self.tmp.cleanup()
 def test_literal_preserved_public_packet_identical(self):
  packet=object();self.w.append_visual(packet,control_tick=0,private_catalog=self.catalog);self.assertIs(self.r.rows[0][0],packet);self.assertNotIn('model_input_allowed',self.catalog);adapted=self.r.rows[0][1]['private_catalog'];self.assertIs(adapted['model_input_allowed'],False);self.assertEqual(adapted['actual_sim_time_s'],0.);self.assertEqual(json.loads((Path(self.tmp.name)/'original.jsonl').read_text())['original_catalog'],self.catalog)
 def test_reject_wrong_flag(self):
  with self.assertRaises(ValueError):self.w.append_visual(object(),control_tick=0,private_catalog=dict(self.catalog,model_input=True))
 def test_reject_tick(self):
  with self.assertRaises(ValueError):self.w.append_visual(object(),control_tick=5,private_catalog=self.catalog)
 def test_reject_ambiguous_alias(self):
  with self.assertRaises(ValueError):self.w.append_visual(object(),control_tick=0,private_catalog=dict(self.catalog,model_input_allowed=False))
 def test_close_original(self):self.assertEqual(self.w.close(outcome='SOFTWARE_ONLY'),dict(outcome='SOFTWARE_ONLY'));self.assertTrue(self.w.original_catalog.closed)
if __name__=='__main__':unittest.main()
