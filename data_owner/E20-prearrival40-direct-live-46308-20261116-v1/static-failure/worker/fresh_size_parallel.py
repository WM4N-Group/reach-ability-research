"""Fresh all-files size scan; no TTL, retained DirEntry, or byte-account cache.

Candidate for Data's NEXT program only. Data owns resource policy and must bind
this implementation explicitly. No file is skipped, no symlink directory is
traversed, ordinary file symlinks retain the original follow=True behavior.
Every error propagates; a failed scanner cannot be reused. No Runtime/physics.
"""
import os,stat,threading,time
from concurrent.futures import ThreadPoolExecutor

class FreshSizeScanner:
    def __init__(self,*,workers=8):
        if type(workers)is not int or not 1<=workers<=8:raise ValueError('Bounded workers 1..8')
        self.workers=workers
        self._pool=None;self._lock=threading.Lock();self.failed=False;self.closed=False
        self.metrics=dict(calls=0,directories_requested=0,wall_s=0.)
    @staticmethod
    def _scan_directory(path):
        total=0;subdirs=[]
        with os.scandir(path)as entries:
            for entry in entries:
                if entry.is_dir(follow_symlinks=False):subdirs.append(entry.path)
                else:
                    info=entry.stat(follow_symlinks=True)
                    if stat.S_ISREG(info.st_mode):total+=info.st_size
        return total,subdirs
    def __call__(self,root):
        if self.failed or self.closed:raise RuntimeError('Failed/closed scanner cannot resume')
        if not self._lock.acquire(blocking=False):
            self.failed=True;raise RuntimeError('Concurrent/reentrant size scan refused')
        started=time.monotonic()
        try:
            if self._pool is None:self._pool=ThreadPoolExecutor(max_workers=self.workers,thread_name_prefix='e-size-read')
            total=0;stack=[os.fspath(root)]
            while stack:
                width=self.workers*4;batch=stack[-width:];del stack[-width:]
                self.metrics['directories_requested']+=len(batch)
                for size,subdirs in self._pool.map(self._scan_directory,batch):
                    total+=size;stack.extend(subdirs)
            if self.failed or self.closed:raise RuntimeError('Size scanner concurrently failed or closed')
            return total
        except BaseException:
            self.failed=True
            if self._pool is not None:self._pool.shutdown(wait=False,cancel_futures=True)
            raise
        finally:
            self.metrics['calls']+=1;self.metrics['wall_s']+=time.monotonic()-started
            self._lock.release()
    def close(self):
        self.closed=True
        if self._pool is not None:self._pool.shutdown(wait=True,cancel_futures=True)
    def __enter__(self):return self
    def __exit__(self,*_):self.close()
