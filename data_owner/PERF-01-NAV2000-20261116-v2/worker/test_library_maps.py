"""Only critical parser/mutation cases for real EGL-memfd admission correction."""
import unittest
from library_maps import _capture,MappingAdmissionError
POL=dict(kind='OBSERVED_EGL_MEMFD_RX_8192_PINNED_DRIVER_BOOTSTRAP_V1',name='/memfd:/.glXXXXXX (deleted)',evidence_result_sha256='a'*64,driver_files_sha256={'FIXTURE_NOT_NATIVE_DRIVER':'b'*64})
BASE='100000-110000 r-xp 0000 08:02 22 /FIXTURE_ONLY/driver.so'
ROW='40841000-40843000 r-xs 00000000 00:01 107853 /memfd:/.glXXXXXX (deleted)'
class Tests(unittest.TestCase):
 def snap(self,row=ROW,policy=POL,sha='c'*64):return _capture([BASE,row],policy,lambda lo,hi:sha)
 def test_exact_evidenced_shape_recorded_not_dropped(self):
  s=self.snap();self.assertEqual(set(s),{'/FIXTURE_ONLY/driver.so'});self.assertEqual(len(s.generated),1)
 def test_no_policy_still_refuses_with_complete_identity(self):
  with self.assertRaisesRegex(MappingAdmissionError,'mapping_identity=.*glXXXXXX'):self.snap(policy=None)
 def test_arbitrary_deleted_file_not_allowed(self):
  with self.assertRaises(MappingAdmissionError):self.snap(ROW.replace('/memfd:/.glXXXXXX','/tmp/arbitrary.so'))
 def test_wrong_permissions_size_offset_rejected(self):
  for r in(ROW.replace('r-xs','rwxp'),ROW.replace('40843000','40844000'),ROW.replace('00000000','00001000')):
   with self.assertRaises(MappingAdmissionError):self.snap(r)
 def test_changed_RX_or_inode_not_equal_to_frozen(self):
  a=self.snap();self.assertNotEqual(a,self.snap(sha='d'*64));self.assertNotEqual(a,self.snap(ROW.replace('107853','107854')))
 def test_unknown_RX_read_not_accepted(self):
  with self.assertRaises(MappingAdmissionError):self.snap(sha=None)
if __name__=='__main__':unittest.main()
