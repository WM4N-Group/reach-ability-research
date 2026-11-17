"""New CPU attribution only. Real original class, synthetic GPU/authority output,
real TEMP-file stat/SHA. No lease __enter__, canonical locks, nvidia or world.
"""
import importlib.util
from pathlib import Path
import os,sys,tempfile,hashlib
from types import SimpleNamespace as NS
import unittest
HERE=Path(__file__).resolve().parent
ORIGINAL=HERE.parent/'bulk-resource-adapter-46308-20261115-v1'
sys.path[:0]=[str(HERE),str(ORIGINAL)]
import lease_leaf_timing as timing
spec=importlib.util.spec_from_file_location('_Data_CPU_original_lease',ORIGINAL/'per_gpu_lease.py');source=importlib.util.module_from_spec(spec);spec.loader.exec_module(source)

class Tests(unittest.TestCase):
    def fixture(self,root,fail_query=None):
        calls=[];p=Path(root);binding=p/'binding.json';binding.write_bytes(b'CPU_ONLY_FIXTURE_NOT_AUTHORITY')
        lease=source.PerGpuLease(physical_index=0,authority_check=lambda:calls.append('authority'))
        lease.profile=dict(source.PROFILES[0],binding=binding,sha256=hashlib.sha256(binding.read_bytes()).hexdigest())
        for i in range(2):
            file=p/('synthetic-lock'+str(i));file.write_bytes(b'');fd=os.open(file,os.O_RDONLY);st=os.fstat(fd)
            lease.fds.append(fd);lease.rows.append(dict(path=str(file),device=st.st_dev,inode=st.st_ino))
        def query(args,**kw):
            kind='gpu'if any(a.startswith('--query-gpu=')for a in args)else'apps';calls.append((kind,tuple(args),dict(kw)))
            if kind==fail_query:raise RuntimeError('DO_NOT_SERIALIZE_ARGUMENTS')
            return '0, '+lease.profile['UUID']+', 20000, 0\n'if kind=='gpu'else str(os.getpid())+', 200, '+lease.profile['UUID']+'\n'
        return lease,calls,query
    def test_default_OFF_does_not_inspect_foreign_object(self):self.assertIsNone(timing.build_timed_check('/DO_NOT_READ'))
    def test_same_original_queries_order_results_and_no_module_mutation(self):
        with tempfile.TemporaryDirectory()as a,tempfile.TemporaryDirectory()as b:
            x,cx,qx=self.fixture(a);y,cy,qy=self.fixture(b);original_method=source.PerGpuLease.check
            try:
                from unittest.mock import patch
                with patch.object(source,'subprocess',NS(check_output=qx)):expected=x.check(force=True)
                with patch.object(source,'subprocess',NS(check_output=qy)):
                    check,trace=timing.build_timed_check(y.check,enabled=True);actual=check(force=True)
                self.assertEqual(expected,actual);self.assertIs(actual,y.last_gpu)
                self.assertEqual(cx,cy);self.assertIs(source.PerGpuLease.check,original_method)
                self.assertIs(y.check.__func__,original_method)
                self.assertEqual(trace.last_attempt.original_query_count,2)
                self.assertTrue(trace.last_attempt.diagnostic_only_not_owner_stamp)
                self.assertIsNone(trace.last_attempt.error_type)
                labels=[z[0]for z in trace.last_attempt.stages]
                self.assertEqual(labels.count('original_authority_callback'),1)
                self.assertEqual(labels.count('held_lock_fstat'),2);self.assertEqual(labels.count('held_lock_path_stat'),4)
                self.assertLess(labels.index('original_nvidia_GPU_inventory_query'),labels.index('original_nvidia_PID_memory_query'))
            finally:x.__exit__();y.__exit__()
    def test_GPU_query_exception_same_type_no_retry_or_exception_args_in_trace(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory()as td:
            lease,calls,query=self.fixture(td,fail_query='gpu')
            try:
                with patch.object(source,'subprocess',NS(check_output=query)):
                    check,trace=timing.build_timed_check(lease.check,enabled=True)
                    with self.assertRaisesRegex(RuntimeError,'DO_NOT_SERIALIZE_ARGUMENTS'):check(force=True)
                self.assertEqual([c[0]for c in calls if type(c)is tuple],['gpu'])
                self.assertEqual(trace.last_attempt.error_type,'RuntimeError');self.assertFalse(trace.last_attempt.cached_original_GPU_result)
                self.assertNotIn('DO_NOT_SERIALIZE_ARGUMENTS',repr(trace.last_attempt))
            finally:lease.__exit__()
    def test_foreign_PID_original_guard_still_refuses_before_queries(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory()as td:
            lease,calls,query=self.fixture(td);lease.pid+=1
            try:
                with patch.object(source,'subprocess',NS(check_output=query)):
                    check,trace=timing.build_timed_check(lease.check,enabled=True)
                    with self.assertRaises(source.ResourceStop):check(force=True)
                self.assertEqual(calls,[]);self.assertEqual(trace.last_attempt.error_type,'ResourceStop')
            finally:lease.__exit__()
    def test_stable_original_cache_path_adds_no_authority_or_GPU_probe(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory()as td:
            lease,calls,query=self.fixture(td);sentinel={'original-cached':True};lease.last_gpu=sentinel;lease.last_at=source.time.monotonic()
            try:
                with patch.object(source,'subprocess',NS(check_output=query)):
                    check,trace=timing.build_timed_check(lease.check,enabled=True);self.assertIs(check(),sentinel)
                self.assertEqual(calls,[]);self.assertEqual(trace.last_attempt.original_query_count,0);self.assertTrue(trace.last_attempt.cached_original_GPU_result)
            finally:lease.__exit__()
    def test_original_inode_substitution_guard_not_ignored(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory()as td:
            lease,calls,query=self.fixture(td);lease.rows[0]['inode']+=1
            try:
                with patch.object(source,'subprocess',NS(check_output=query)):
                    check,trace=timing.build_timed_check(lease.check,enabled=True)
                    with self.assertRaises(source.ResourceStop):check(force=True)
                self.assertEqual(calls,[])
            finally:lease.__exit__()

if __name__=='__main__':unittest.main(verbosity=2)
