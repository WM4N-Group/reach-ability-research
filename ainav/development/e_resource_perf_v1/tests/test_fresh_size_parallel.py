"""CPU filesystem fixtures, never an actual resource lease/physical dispatch."""
from pathlib import Path
from unittest.mock import patch
import sys,unittest,tempfile,os,stat
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
blocked=[]
def fence(event,args):
    if event=='import'and str(args[0]).split('.')[0]in('numpy','torch','mujoco','onnxruntime'):
        blocked.append(str(args[0]));raise RuntimeError('CPU filesystem fixtures only')
    if event in('socket.connect','socket.bind','socket.getaddrinfo','subprocess.Popen'):
        blocked.append(event);raise RuntimeError('No network/child')
sys.addaudithook(fence)
from fresh_size_parallel import FreshSizeScanner

def original(root):
    total=0;stack=[os.fspath(root)]
    while stack:
        with os.scandir(stack.pop())as entries:
            for entry in entries:
                if entry.is_dir(follow_symlinks=False):stack.append(entry.path)
                else:
                    info=entry.stat(follow_symlinks=True)
                    if stat.S_ISREG(info.st_mode):total+=info.st_size
    return total

class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.scanner=FreshSizeScanner()
        self.addCleanup(self.scanner.close)
    def test_empty(self):self.assertEqual(self.scanner(self.root),0)
    def test_nested_many_and_hardlinks_preserve_each_path_count(self):
        for i in range(1325):
            d=self.root/str(i%17);d.mkdir(exist_ok=True);(d/str(i)).write_bytes(b'x'*(i%31))
        p=self.root/'one';p.write_bytes(b'abc');(self.root/'hard').hardlink_to(p)
        self.assertEqual(self.scanner(self.root),original(self.root))
    def test_regular_symlink_followed_directory_symlink_not_traversed(self):
        (self.root/'file').write_bytes(b'abc');(self.root/'sym').symlink_to(self.root/'file')
        (self.root/'dir').symlink_to(self.root,target_is_directory=True)
        self.assertEqual(self.scanner(self.root),6)
    def test_mutations_visible_without_cache(self):
        p=self.root/'one';p.write_bytes(b'a');self.assertEqual(self.scanner(self.root),1)
        p.write_bytes(b'12345');(self.root/'two').write_bytes(b'abc');self.assertEqual(self.scanner(self.root),8)
        p.unlink();self.assertEqual(self.scanner(self.root),3)
    def test_retarget_regular_symlink_fresh(self):
        a=self.root/'a';b=self.root/'b';a.write_bytes(b'a');b.write_bytes(b'bbb');p=self.root/'sym';p.symlink_to(a)
        self.assertEqual(self.scanner(self.root),5);p.unlink();p.symlink_to(b)
        self.assertEqual(self.scanner(self.root),7)
    def test_dangling_link_fails_and_revokes(self):
        (self.root/'bad').symlink_to(self.root/'missing')
        with self.assertRaises(FileNotFoundError):original(self.root)
        with self.assertRaises(FileNotFoundError):self.scanner(self.root)
        (self.root/'bad').unlink()
        with self.assertRaises(RuntimeError):self.scanner(self.root)
    def test_loop_fails_closed(self):
        p=self.root/'loop';p.symlink_to(p)
        with self.assertRaises(OSError):original(self.root)
        with self.assertRaises(OSError):self.scanner(self.root)
    def test_scan_io_error_propagates_and_revokes(self):
        with patch('fresh_size_parallel.os.scandir',side_effect=PermissionError('fixture')):
            with self.assertRaises(PermissionError):self.scanner(self.root)
        with self.assertRaises(RuntimeError):self.scanner(self.root)
    def test_leaf_io_error_propagates(self):
        (self.root/'file').write_bytes(b'a')
        with patch.object(self.scanner,'_scan_directory',side_effect=OSError('fixture')):
            with self.assertRaises(OSError):self.scanner(self.root)
        self.assertTrue(self.scanner.failed)
    def test_close_refuses_reuse(self):
        self.scanner.close()
        with self.assertRaises(RuntimeError):self.scanner(self.root)
    def test_reentrancy_refuses_and_revokes(self):
        self.scanner._lock.acquire()
        try:
            with self.assertRaises(RuntimeError):self.scanner(self.root)
        finally:self.scanner._lock.release()
        self.assertTrue(self.scanner.failed)
    def test_bounds(self):
        for kwargs in ({'workers':True},{'workers':0},{'workers':9}):
            with self.assertRaises(ValueError):FreshSizeScanner(**kwargs)
    def test_fifo_not_counted(self):
        os.mkfifo(self.root/'fifo');self.assertEqual(self.scanner(self.root),0)

    def test_many_directory_frontiers_preserve_full_size_and_count(self):
        for i in range(65):
            sub=self.root/str(i)/'deep';sub.mkdir(parents=True);(sub/'f').write_bytes(b'abc')
        self.assertEqual(self.scanner(self.root),65*3)
        self.assertEqual(self.scanner.metrics['directories_requested'],131)
        self.assertEqual(self.scanner.metrics['calls'],1)
    def test_no_directory_is_dropped_by_future_bound(self):
        for i in range(129):(self.root/str(i)).mkdir()
        self.assertEqual(self.scanner(self.root),0)
        self.assertEqual(self.scanner.metrics['directories_requested'],130)
    def test_missing_root_fails_like_original(self):
        root=self.root/'absent'
        with self.assertRaises(FileNotFoundError):original(root)
        with self.assertRaises(FileNotFoundError):self.scanner(root)
    def test_scan_uses_new_direntries_each_invocation(self):
        with patch('fresh_size_parallel.os.scandir',wraps=os.scandir)as scan:
            self.scanner(self.root);self.scanner(self.root)
        self.assertEqual(scan.call_count,2)

if __name__=='__main__':
    import json
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
    print(json.dumps(dict(checks=result.testsRun,failures=len(result.failures),errors=len(result.errors),forbidden_attempts=blocked,native_or_GPU_calls=0)))
    sys.exit(0 if result.wasSuccessful()and not blocked else 1)
