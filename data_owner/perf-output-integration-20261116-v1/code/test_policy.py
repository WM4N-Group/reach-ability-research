import unittest,tempfile,os,threading,zipfile,time,json
from pathlib import Path
from scoped_io import ScopeIO,StopState,PolicyStop,scoped_path_class
from resource_watch import ResourceWatch
class PolicyTests(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
 def tearDown(self):self.tmp.cleanup()
 def b(self,**kw):return ScopeIO(self.root,cap_bytes=4096,reserve_bytes=512,max_open=8,text_buffer_bytes=16,**kw)
 def test_binary_text_utf8_exact(self):
  b=self.b()
  with b.open('a','x',encoding='utf-8')as f:f.write('汉字\n');f.flush()
  with b.open('b','xb')as f:f.write(b'123')
  self.assertEqual(b.reconcile(),10)
 def test_cap_admission_before_write(self):
  b=self.b();f=b.open('a','xb')
  with self.assertRaises(PolicyStop):f.write(b'x'*3584)
  self.assertEqual((self.root/'a').stat().st_size,0);f.close()
 def test_final_reserve_and_sealed_guard(self):
  b=self.b();token=object();w=ResourceWatch(lambda:None,state=b.state,token=token);w.probe_once()
  with b.open('a','xb')as f:f.write(b'x'*3500)
  b.begin_finalization()
  with self.assertRaises(PolicyStop):w()
  with b.open('result.json','x')as f:json.dump({'failure':'known'},f)
  self.assertGreater(b.reconcile(),3500);self.assertFalse(b.snapshot()['failed'])
 def test_zip_seek_header_rewrites(self):
  b=self.b()
  with b.open('raw.npz','xb')as f:
   with zipfile.ZipFile(f,'w',zipfile.ZIP_DEFLATED)as z:z.writestr('fixture',b'abcdefgh'*100)
  self.assertEqual(b.reconcile(),(self.root/'raw.npz').stat().st_size)
  with zipfile.ZipFile(self.root/'raw.npz')as z:self.assertEqual(z.read('fixture'),b'abcdefgh'*100)
 def test_atomic_replace_and_peak(self):
  b=self.b()
  with b.open('metadata','xb')as f:f.write(b'old')
  with b.open('new.tmp','xb')as f:f.write(b'newdata')
  self.assertEqual(b.highwater,10);b.replace('new.tmp','metadata');self.assertEqual(b.reconcile(),7)
 def test_unknown_writer(self):
  b=self.b();(self.root/'unknown').write_bytes(b'123')
  with self.assertRaises(PolicyStop):b.reconcile()
  self.assertIsNotNone(b.state.reason)
 def test_deleted_known_file(self):
  b=self.b()
  with b.open('a','xb')as f:f.write(b'123')
  (self.root/'a').unlink()
  with self.assertRaises(PolicyStop):b.reconcile()
 def test_same_size_inode_replace(self):
  b=self.b()
  with b.open('a','xb')as f:f.write(b'123')
  p=self.root/'external';p.write_bytes(b'123');os.replace(p,self.root/'a')
  with self.assertRaises(PolicyStop):b.reconcile()
 def test_symlink_reject(self):
  b=self.b();(self.root/'s').symlink_to('/tmp')
  with self.assertRaises(PolicyStop):b.open('s/escaped','xb')
 def test_hardlink_reject(self):
  (self.root/'a').write_bytes(b'1');os.link(self.root/'a',self.root/'b')
  with self.assertRaises(PolicyStop):self.b()
 def test_foreign_root(self):
  b=self.b()
  with self.assertRaises(PolicyStop):b.open('/tmp/foreign-output','xb')
 def test_duplicate_writer(self):
  b=self.b();f=b.open('a','xb')
  with self.assertRaises(PolicyStop):b.open('a','ab')
  f.close()
 def test_append_cannot_seek_undercount(self):
  b=self.b()
  with b.open('a','xb')as f:f.write(b'123')
  with b.open('a','ab')as f:
   with self.assertRaises(Exception):f.seek(0)
   f.write(b'4')
  self.assertEqual(b.reconcile(),4)
 def test_truncate_exact(self):
  b=self.b()
  with b.open('a','xb')as f:f.write(b'123456');f.truncate(2)
  self.assertEqual(b.reconcile(),2)
 def test_event_loss_stops(self):
  b=self.b()
  with self.assertRaises(PolicyStop):b.event_loss()
  with self.assertRaises(PolicyStop):b.open('later','xb')
 def test_read_error_latched(self):
  b=self.b()
  def no():raise PermissionError('fixture denied')
  b._scan=no
  with self.assertRaises(PolicyStop):b.reconcile()
  self.assertIsNotNone(b.state.reason)
 def test_partial_write_reservation_retained(self):
  b=self.b();f=b.open('a','xb');original=f._f
  class Partial:
   closed=False
   def write(self,d):return len(d)-1
   def close(self):self.closed=True
  f._f=Partial()
  with self.assertRaises(PolicyStop):f.write(b'123')
  self.assertEqual(b.used,3);f.close();original.close()
 def test_hot_guard_no_probe_no_filesystem(self):
  state=StopState();token=object();calls=[];clock=[0.];g=ResourceWatch(lambda:calls.append(1),state=state,token=token,clock=lambda:clock[0]);g.probe_once()
  for _ in range(1000):g()
  self.assertEqual(len(calls),1)
 def test_stale_stops_and_never_recovers(self):
  state=StopState();token=object();clock=[0.];g=ResourceWatch(lambda:None,state=state,token=token,clock=lambda:clock[0]);g.probe_once();clock[0]=2.01
  with self.assertRaises(PolicyStop):g()
  clock[0]=0.
  with self.assertRaises(PolicyStop):g()
 def test_wrong_token(self):
  g=ResourceWatch(lambda:None,state=StopState(),token=object());g.probe_once()
  with self.assertRaises(PolicyStop):g.check(object())
 def test_probe_error_and_false(self):
  for result in [False,0,{}]:
   g=ResourceWatch(lambda:result,state=StopState(),token=object())
   with self.assertRaises(PolicyStop):g.probe_once()
 def test_cheap_health_refusal(self):
  g=ResourceWatch(lambda:None,state=StopState(),token=object(),fast_health=lambda:False);g.probe_once()
  with self.assertRaises(PolicyStop):g()
 def test_closed_watch_cannot_restart(self):
  g=ResourceWatch(lambda:None,state=StopState(),token=object());g.start();g.close()
  with self.assertRaises(PolicyStop):g.start()
  with self.assertRaises(PolicyStop):g()
 def test_private_path_no_global_monkeypatch(self):
  b=self.b();P=scoped_path_class(b)
  with P(self.root/'meta.json').open('x')as f:json.dump({'x':1},f)
  self.assertEqual(b.reconcile(),8);self.assertIs(type(Path()),type(self.root))

class ProbeCompositionTests(unittest.TestCase):
 def test_disk_low_unknown_and_one_lease_call(self):
  from resource_watch import make_scope_probe
  for free in [None,False,0,99]:
   with tempfile.TemporaryDirectory()as td:
    b=ScopeIO(td,cap_bytes=4096,reserve_bytes=512,max_open=8,text_buffer_bytes=16)
    class Lease:
     calls=0
     def check(self,force=False):self.calls+=1;assert force
    lease=Lease();p=make_scope_probe(lease,b,min_free_bytes=100,disk_free=lambda _:free)
    with self.assertRaises(PolicyStop):p()
    self.assertEqual(lease.calls,1)
 def test_lease_revocation_propagates(self):
  from resource_watch import make_scope_probe
  with tempfile.TemporaryDirectory()as td:
   b=ScopeIO(td,cap_bytes=4096,reserve_bytes=512,max_open=8,text_buffer_bytes=16)
   class Lease:
    def check(self,force=False):raise RuntimeError('authority revoked fixture')
   g=ResourceWatch(make_scope_probe(Lease(),b,min_free_bytes=100,disk_free=lambda _:999),state=b.state,token=object())
   with self.assertRaises(PolicyStop):g.probe_once()
   with self.assertRaises(PolicyStop):g()


class AdditionalSafetyTests(unittest.TestCase):
 def budget(self,td):return ScopeIO(td,cap_bytes=4096,reserve_bytes=512,max_open=8,text_buffer_bytes=16)
 def test_failure_record_uses_reserve_without_resuming(self):
  with tempfile.TemporaryDirectory()as td:
   b=self.budget(td)
   with b.open('payload','xb')as f:f.write(b'x'*3500)
   with self.assertRaises(PolicyStop):
    with b.open('overflow','xb')as f:f.write(b'x'*100)
   reason=b.state.reason;b.begin_finalization()
   with b.open('failure.json','x')as f:json.dump({'why':reason},f)
   b.reconcile();self.assertEqual(b.state.reason,reason)
   with self.assertRaises(PolicyStop):b.state.check()
 def test_concurrent_writes_cannot_overreserve(self):
  with tempfile.TemporaryDirectory()as td:
   b=self.budget(td);barrier=threading.Barrier(2);ok=[]
   def write(name):
    f=b.open(name,'xb');barrier.wait()
    try:f.write(b'x'*2000);ok.append(name)
    except PolicyStop:pass
    finally:f.close()
   threads=[threading.Thread(target=write,args=(str(i),))for i in range(2)]
   for t in threads:t.start()
   for t in threads:t.join()
   self.assertEqual(len(ok),1);self.assertEqual(b.used,2000);self.assertEqual(sum(p.stat().st_size for p in Path(td).iterdir()),2000)
 def test_blocked_probe_stales_real_clock(self):
  state=StopState();calls=[];block=threading.Event()
  def probe():
   calls.append(1)
   if len(calls)>1:block.wait(1.)
  g=ResourceWatch(probe,state=state,token=object(),interval_s=.01,max_stale_s=.05).start()
  try:
   time.sleep(.08)
   with self.assertRaises(PolicyStop):g()
  finally:block.set();g.close()


class ShutdownSafetyTests(unittest.TestCase):
 def test_blocked_probe_close_is_not_silently_successful(self):
  state=StopState();block=threading.Event();entered=threading.Event();calls=[]
  def probe():
   calls.append(1)
   if len(calls)>1:entered.set();block.wait(2.)
  g=ResourceWatch(probe,state=state,token=object(),interval_s=.01,max_stale_s=.05).start()
  try:
   self.assertTrue(entered.wait(.5))
   with self.assertRaises(PolicyStop):g.close()
   with self.assertRaises(PolicyStop):g()
  finally:block.set();g.close()

if __name__=='__main__':unittest.main(verbosity=2)
