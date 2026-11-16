"""Filesystem/callback fixtures, not a native guard/profile or real Runtime."""
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
import json,sys,tempfile,types,unittest
OWN=Path(__file__).resolve().parents[1];ROOT=OWN.parents[1]
SOURCE=ROOT/'consumer-deliveries/AINAV-CLIMB-PREPARATION-CANDIDATES-20261113-v1/common-source'
sys.path[:0]=[str(OWN),str(SOURCE)]
blocked=[]
def fence(event,args):
    if event=='import'and str(args[0]).split('.')[0]in('numpy','torch','mujoco','onnxruntime'):
        blocked.append(str(args[0]));raise RuntimeError('Explicit filesystem/callback fixture only')
    if event in('socket.connect','socket.bind','socket.getaddrinfo','subprocess.Popen'):
        blocked.append(event);raise RuntimeError('No network/child')
sys.addaudithook(fence)
import live_driver
from parallel_alias_guard import make_parallel_guard,WORKERS

class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.owned=self.root/'owned.py';self.owned.write_text('SOFTWARE')
        self.other=self.root/'other.py';self.other.write_text('SOFTWARE')
        self.modules={};self.callback=object();self.owner_calls=0
        sim=NS(model=object(),data=object(),queue=object(),controller=object(),box_push_target=object())
        def owner():self.owner_calls+=1
        self.host=NS(owner_guard=owner,r=NS(sim=sim),_stow_allowed={self.owned},
            _stow_installed={str(self.owned):self.callback},_stow_callback_name='SOFTWARE_CALLBACK')
        self.host._world=(sim,sim.model,sim.data,sim.queue,sim.controller,sim.box_push_target)
        raw=live_driver._original_methods()['_native_guards']
        self.original=types.FunctionType(raw.__code__,dict(raw.__globals__,sys=NS(modules=self.modules)),raw.__name__)
        self.guard=make_parallel_guard(self.original,enabled=True);self.addCleanup(self.guard.engine.close)
    def alias(self,key,path,valid=True):
        module=NS(__file__=str(path))
        if valid:setattr(module,'SOFTWARE_CALLBACK',self.callback)
        self.modules[key]=module;return module
    def test_default_off_and_bool_optin_create_no_pool_or_world(self):
        self.assertIsNone(make_parallel_guard())
        with self.assertRaises(ValueError):make_parallel_guard(enabled=1)
        self.assertIsNone(self.guard.engine._pool);self.assertEqual(WORKERS,8)
    def test_original_bytecode_globals_and_source_guard_remain_unchanged(self):
        self.alias('owned',self.owned);self.modules['none']=None
        before=dict(self.original.__globals__);self.guard(self.host)
        self.assertIs(self.guard.original_guard_code,self.original.__code__)
        self.assertEqual(self.original.__globals__,before);self.assertIs(self.original.__globals__['Path'],Path)
        self.assertEqual(self.owner_calls,3);self.assertFalse(self.guard.cross_tick_cache)
    def test_arbitrary_filename_symlink_keeps_full_identity_checks(self):
        link=self.root/'unrelated-name.py';link.symlink_to(self.owned)
        self.alias('arbitrary_alias',link,valid=False)
        with self.assertRaises(ValueError):self.guard(self.host)
    def test_new_alias_between_filesystem_passes_is_not_omitted(self):
        self.alias('ordinary',self.other);original=self.guard.engine._resolve_paths;count=0
        def resolve(paths):
            nonlocal count
            result=original(paths);count+=1
            if count==2:self.alias('late_alias',self.owned,valid=False)
            return result
        with patch.object(self.guard.engine,'_resolve_paths',side_effect=resolve):
            with self.assertRaises(ValueError):self.guard(self.host)
    def test_new_valid_alias_after_second_read_uses_fresh_original_fallback(self):
        self.alias('ordinary',self.other);original=self.guard.engine._resolve_paths;count=0
        def resolve(paths):
            nonlocal count
            result=original(paths);count+=1
            if count==2:self.alias('late_valid_alias',self.owned,valid=True)
            return result
        with patch.object(self.guard.engine,'_resolve_paths',side_effect=resolve):self.guard(self.host)
    def test_duplicate_path_inconsistent_resolution_is_refused(self):
        with self.assertRaises(ValueError):self.guard.engine._lookup(('same','same'),(self.owned,self.other))
    def test_changed_original_source_file_is_not_accepted(self):
        fake=self.root/'bad-source.py';fake.write_text('class ComplexSceneDriver: pass\n')
        bad=types.FunctionType(self.original.__code__.replace(co_filename=str(fake)),self.original.__globals__)
        with self.assertRaises(ValueError):make_parallel_guard(bad,enabled=True)
    def test_callback_changed_after_second_filesystem_pass_is_not_cached(self):
        module=self.alias('owned',self.owned);original=self.guard.engine._resolve_paths;count=0
        def resolve(paths):
            nonlocal count
            result=original(paths);count+=1
            if count==2:module.SOFTWARE_CALLBACK=object()
            return result
        with patch.object(self.guard.engine,'_resolve_paths',side_effect=resolve):
            with self.assertRaises(ValueError):self.guard(self.host)
    def test_world_change_after_second_read_is_still_original_guard_failure(self):
        self.alias('ordinary',self.other);original=self.guard.engine._resolve_paths;count=0
        def resolve(paths):
            nonlocal count
            result=original(paths);count+=1
            if count==2:self.host.r.sim.queue=object()
            return result
        with patch.object(self.guard.engine,'_resolve_paths',side_effect=resolve):
            with self.assertRaises(ValueError):self.guard(self.host)
    def test_filesystem_symlink_retarget_in_one_invocation_fails_before_acceptance(self):
        link=self.root/'link.py';link.symlink_to(self.other);self.alias('module',link)
        original=self.guard.engine._resolve_paths;count=0
        def resolve(paths):
            nonlocal count
            result=original(paths);count+=1
            if count==1:link.unlink();link.symlink_to(self.owned)
            return result
        with patch.object(self.guard.engine,'_resolve_paths',side_effect=resolve):
            with self.assertRaises(ValueError):self.guard(self.host)
    def test_no_cross_tick_path_permission_after_retarget(self):
        link=self.root/'link.py';link.symlink_to(self.other);self.alias('module',link,valid=False)
        self.guard(self.host);link.unlink();link.symlink_to(self.owned)
        with self.assertRaises(ValueError):self.guard(self.host)
    def test_missing_path_uses_original_non_strict_semantics(self):
        self.alias('missing',self.root/'missing.py',valid=False);self.original(self.host);self.guard(self.host)
    def test_hardlink_is_not_mistaken_for_original_canonical_alias(self):
        p=self.root/'hard.py';p.hardlink_to(self.owned);self.alias('hard',p,valid=False)
        self.original(self.host);self.guard(self.host)
    def test_symlink_loop_error_is_not_suppressed(self):
        p=self.root/'loop.py';p.symlink_to(p);self.alias('loop',p)
        with self.assertRaises(RuntimeError):self.original(self.host)
        with self.assertRaises(RuntimeError):self.guard(self.host)
    def test_owner_false_denied_before_pool_and_failure_permanently_revokes(self):
        self.host.owner_guard=lambda:False
        with self.assertRaises(ValueError):self.guard(self.host)
        self.assertIsNone(self.guard.engine._pool);self.host.owner_guard=lambda:None
        with self.assertRaises(ValueError):self.guard(self.host)
    def test_closed_guard_cannot_resume(self):
        self.guard.engine.close()
        with self.assertRaises(ValueError):self.guard(self.host)
    def test_non_string_pathlike_is_fresh_original_resolve_not_cached(self):
        self.modules['pathlike']=NS(__file__=self.other);self.original(self.host);self.guard(self.host)
    def test_parent_directory_symlink_keeps_original_alias_check(self):
        parent=self.root/'parent';parent.symlink_to(self.root,target_is_directory=True)
        self.alias('parent_alias',parent/'owned.py',valid=False)
        with self.assertRaises(ValueError):self.guard(self.host)
    def test_proc_fd_alias_keeps_original_current_identity_check(self):
        if not Path('/proc/self/fd').exists():self.skipTest('Linux procfs fixture only')
        with self.owned.open('rb')as stream:
            self.alias('fd_alias',Path('/proc/self/fd')/str(stream.fileno()),valid=False)
            with self.assertRaises(ValueError):self.guard(self.host)
    def test_reentrant_guard_revokes_instead_of_resuming_same_engine(self):
        self.host.owner_guard=lambda:self.guard(self.host)
        with self.assertRaises(ValueError):self.guard(self.host)
        self.assertTrue(self.guard.engine.failed)
    def test_incomplete_batch_cannot_silently_omit_path_verification(self):
        self.alias('ordinary',self.other)
        with patch.object(self.guard.engine,'_resolve_paths',return_value=()):
            with self.assertRaises(ValueError):self.guard(self.host)
    def test_ambient_guard_module_path_is_rejected_before_controller_or_pool(self):
        import parallel_alias_guard as helper
        with patch.object(helper,'__file__',str(self.root/'foreign-helper.py')):
            with self.assertRaisesRegex(ValueError,'ambient parallel guard'):
                live_driver.driver_class(source_root=SOURCE,enabled=True)
    def test_default_driver_installs_bytecode_adapter_without_creating_threads(self):
        cls=live_driver.driver_class(source_root=SOURCE,enabled=True)
        self.assertIsNone(cls._native_guards.engine._pool);self.assertEqual(cls._native_guards.current_full_path_passes,2)
        host=cls.__new__(cls);host.close_metadata_workers()
        self.assertTrue(cls._native_guards.engine.closed)

if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
    print(json.dumps(dict(role='EXPLICIT_SOFTWARE_PARALLEL_FULL_PATH_AND_ORIGINAL_CALLBACK_GUARD_FIXTURES_NOT_NATIVE',checks=result.testsRun,failures=len(result.failures),errors=len(result.errors),forbidden_attempts=blocked,actual_Runtime_Actor_physics_WM_API_calls=0)))
    sys.exit(0 if result.wasSuccessful()and not blocked else 1)
