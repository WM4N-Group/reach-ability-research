"""Four NEW stdlib observer control fixtures; fake lease, no lock/physics."""
from pathlib import Path
import ast,importlib.util,json,sys,time,unittest
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('_native_single_lease_observer_software',HERE/'lease_site_observer.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
# Deliberately replaces only metadata reader in SOFTWARE fixture, not actual native code.
reads=[]
def metadata(lease,frame):reads.append(lease);return dict(software_fixture=True,before_cleanup=not lease.cleaned)
m.snapshot_fd_site=metadata
class Lease:
 def __init__(self,error=None):self.enter_calls=0;self.exit_calls=0;self.cleaned=False;self.error=error;self.fds=[]
 def __enter__(self):
  self.enter_calls+=1
  try:
   if self.error is not None:raise self.error
   return self
  except BaseException:self.__exit__();raise
 def __exit__(self,*args):self.exit_calls+=1;self.cleaned=True
class Checks(unittest.TestCase):
 def test_01_success_single_original_call_no_extra_exit_and_trace_restored(self):
  lease=Lease();events=[];self.assertIs(m.enter_once(lease,events),lease)
  self.assertEqual((lease.enter_calls,lease.exit_calls),(1,0));self.assertIsNone(sys.gettrace())
  self.assertEqual(events[-1]['calls'],1);self.assertTrue(events[0]['site']['before_cleanup'])
 def test_02_original_error_and_before_original_cleanup_evidence(self):
  marker=BlockingIOError(11,'SOFTWARE_CONTEND');lease=Lease(marker);events=[]
  with self.assertRaises(BlockingIOError)as got:m.enter_once(lease,events)
  self.assertIs(got.exception,marker);self.assertEqual((lease.enter_calls,lease.exit_calls),(1,1))
  self.assertTrue(events[0]['site']['before_cleanup']);self.assertEqual(events[0]['errno'],11);self.assertIsNone(sys.gettrace())
 def test_03_no_event_reuse_or_ambient_trace_replace(self):
  lease=Lease()
  with self.assertRaises(ValueError):m.enter_once(lease,[dict(old=True)])
  def existing(*args):return None
  try:
   sys.settrace(existing)
   with self.assertRaises(ValueError):m.enter_once(lease,[])
   self.assertIs(sys.gettrace(),existing)
  finally:sys.settrace(None)
  self.assertEqual(lease.enter_calls,0)
 def test_04_metadata_failure_cannot_replace_primary(self):
  old=m.snapshot_fd_site
  def failing(*args):raise ValueError('SOFTWARE_METADATA_ONLY')
  try:
   m.snapshot_fd_site=failing;marker=BlockingIOError(11,'SOFTWARE_ORIGINAL');lease=Lease(marker);events=[]
   with self.assertRaises(BlockingIOError)as got:m.enter_once(lease,events)
   self.assertIs(got.exception,marker);self.assertEqual(lease.enter_calls,1);self.assertIsNone(sys.gettrace())
  finally:m.snapshot_fd_site=old
if __name__=='__main__':
 started=time.perf_counter();r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
 print(json.dumps(dict(stage='LEASE_SITE_OBSERVER_FOUR_NEW_SOFTWARE_TESTS_NOT_LOCK_QUALIFICATION',tests=r.testsRun,passed=r.wasSuccessful(),wall_s=time.perf_counter()-started,original_lock_or_world_calls=0),indent=2))
 raise SystemExit(0 if r.wasSuccessful()else 1)
