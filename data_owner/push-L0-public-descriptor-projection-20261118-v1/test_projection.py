"""Four new public-ABI source fixtures; no native/detector/world replay."""
from copy import deepcopy
import unittest
from public_descriptor_projection import project
SHA='a'*64

def record():return dict(target_ref='opaque-fake-test-target',RGB_sha256=SHA,descriptor=dict(appearance_family='FAKE_CURRENT_RGB_COLOR',pixel_bbox_xyxy=[1,2,10,12],pixel_centroid_uv=[5,6],median_observed_RGB=[1,2,3],pixel_count=20,geometry_valid=True))
class Projection(unittest.TestCase):
    def test_default_off(self):self.assertIsNone(project())
    def test_only_four_public_fields_and_input_unmodified(self):
        x=record();before=deepcopy(x);r=project((x,),raw_RGB_sha256=SHA,width=192,height=128,enabled=True)
        self.assertEqual(x,before);self.assertEqual(set(r[0]),{'target_ref','label','bbox_xyxy','evidence_ref'});self.assertEqual(r[0]['target_ref'],x['target_ref']);self.assertEqual(r[0]['bbox_xyxy'],[1,2,10,12]);self.assertNotIn('geometry',r[0]);self.assertIn('RGB-bytes-sha256:',r[0]['evidence_ref'])
    def test_stale_hash_and_private_extra_refused(self):
        for kind in ['hash','private']:
            x=record()
            if kind=='hash':x['RGB_sha256']='b'*64
            else:x['private_catalog']={'body_id':123}
            with self.assertRaises(ValueError):project((x,),raw_RGB_sha256=SHA,width=192,height=128,enabled=True)
    def test_bad_bbox_and_duplicate_ref_refused(self):
        x=record();x['descriptor']['pixel_bbox_xyxy']=[1,2,193,12]
        with self.assertRaises(ValueError):project((x,),raw_RGB_sha256=SHA,width=192,height=128,enabled=True)
        with self.assertRaises(ValueError):project((record(),record()),raw_RGB_sha256=SHA,width=192,height=128,enabled=True)
if __name__=='__main__':unittest.main()
