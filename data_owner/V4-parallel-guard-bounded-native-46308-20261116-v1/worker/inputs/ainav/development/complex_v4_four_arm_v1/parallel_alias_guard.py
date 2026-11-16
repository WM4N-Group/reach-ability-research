"""Parallel CURRENT filesystem reads around the unchanged original alias guard.

Full path resolution, every current module and the original callback/world/owner
checks remain. Resolve the initial paths twice inside ONE invocation, reject
filesystem rebinding, then run the original guard again. Unknown/new paths are
resolved normally by the original predicate. No cross-tick path/callback cache.
No physics, model, GPU, import hook, monkeypatch of another module or dispatcher.
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import ast,hashlib,threading,types
from v4_native_asset import require

ORIGINAL_METHOD_SHA='e6e848ce969ed0a94f4ccf52310a542fc8c4ff326c1a8a4607c415b7838b070f'
WORKERS=8  # Shared implementation for every arm, NOT B/D treatment.


def _verify_original(original):
    require(callable(original)and getattr(original,'__code__',None)is not None
            and original.__code__.co_name=='_native_guards'
            and original.__globals__.get('Path') is Path,'Exact original source guard/Path dependency')
    path=Path(original.__code__.co_filename)
    require(not path.is_symlink(),'No redirected original guard source')
    text=path.read_text();tree=ast.parse(text)
    cls=next((n for n in tree.body if isinstance(n,ast.ClassDef)and n.name=='ComplexSceneDriver'),None)
    node=None if cls is None else next((n for n in cls.body if isinstance(n,ast.FunctionDef)and n.name=='_native_guards'),None)
    require(node is not None and hashlib.sha256(ast.get_source_segment(text,node).encode()).hexdigest()==ORIGINAL_METHOD_SHA,
            'Exact original guard source bytes required before installing private read adapter')


class CurrentParallelGuard:
    def __init__(self,original):
        _verify_original(original)
        self.original=original;self.module_registry=original.__globals__['sys']
        self._pool=None;self._lock=threading.Lock();self.failed=False;self.closed=False
    def _ensure_pool(self):
        if self._pool is None:
            self._pool=ThreadPoolExecutor(max_workers=WORKERS,thread_name_prefix='v4-path-read')
            self._pool.submit(lambda:None).result()  # Warm standard-library worker machinery BEFORE snapshot.
    @staticmethod
    def _resolve_path(path):return Path(path).resolve()
    def _resolve_paths(self,paths):return tuple(self._pool.map(self._resolve_path,paths))
    @staticmethod
    def _lookup(paths,resolved):
        require(len(paths)==len(resolved),'Every current module path must have a complete filesystem read')
        result={}
        for path,value in zip(paths,resolved):
            require(isinstance(value,Path),'Original canonical Path result required')
            require(path not in result or result[path]==value,'Duplicate module path rebound during guard read')
            result[path]=value
        return result
    def _original_pass(self,host,lookup):
        class CurrentPath:
            def __init__(self,path):self.path=path
            def resolve(self):
                # Only literal file strings read this invocation use its results.
                # New/unknown/path-like values use original fresh Path.resolve.
                if type(self.path)is str and self.path in lookup:return lookup[self.path]
                return Path(self.path).resolve()
        namespace=dict(self.original.__globals__);namespace['Path']=CurrentPath
        checked=types.FunctionType(self.original.__code__,namespace,self.original.__name__,
            self.original.__defaults__,self.original.__closure__)
        checked.__kwdefaults__=self.original.__kwdefaults__
        return checked(host)
    def __call__(self,host):
        require(not self.closed and not self.failed,'Closed/failed metadata guard cannot resume')
        if not self._lock.acquire(blocking=False):
            self.failed=True
            raise ValueError('Concurrent or reentrant guard invocation refused')
        try:
            require(host.owner_guard()is not False,'Actual owner/resource guard refused before metadata reads')
            self._ensure_pool()
            modules=tuple(self.module_registry.modules.values())
            paths=tuple(path for module in modules if type(path:=getattr(module,'__file__',None))is str)
            before=self._resolve_paths(paths);first=self._lookup(paths,before)
            self._original_pass(host,first)
            after=self._resolve_paths(paths)
            require(before==after,'Module path resolution changed during current guard invocation')
            # Re-read callback/module/world identities AFTER filesystem verification.
            # The original code enumerates CURRENT modules; newly loaded paths
            # absent from the initial list take the normal fresh resolve branch.
            result=self._original_pass(host,self._lookup(paths,after))
            require(not self.failed and not self.closed,'Metadata guard concurrently failed or closed')
            return result
        except BaseException:
            self.failed=True
            if self._pool is not None:self._pool.shutdown(wait=False,cancel_futures=True)
            raise
        finally:
            self._lock.release()
    def close(self):
        self.closed=True
        if self._pool is not None:self._pool.shutdown(wait=True,cancel_futures=True)


def make_parallel_guard(original=None,*,enabled=False):
    require(type(enabled)is bool,'Explicit source owner opt-in')
    if not enabled:return None
    engine=CurrentParallelGuard(original)
    def guard(host):return engine(host)
    guard.engine=engine
    guard.original_guard_code=original.__code__
    guard.original_guard_source_sha256=ORIGINAL_METHOD_SHA
    guard.current_full_path_passes=2
    guard.cross_tick_cache=False
    return guard
