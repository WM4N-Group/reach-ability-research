"""Opt-in SAME-PROCESS fd1/fd2 capture to ScopeIO, before the identity seal.

All file writes remain in this process and use the same budget as native writers.
No fork counter, external output filename, unbounded queue or child launcher.
Pipe overflow backpressures writers. On sink failure, latch stop then drain/drop
with explicit byte counters to avoid deadlocking a printing native error path.
"""
import ctypes
import fcntl
import os
import sys
import threading
import time
from scoped_io import PolicyStop

_active_lock=threading.Lock()


class FDCapture:
    CHUNK=8192
    def __init__(self,budget,*,stdout_path='stdout.bin',stderr_path='stderr.bin',enabled=False):
        if enabled is not True:raise ValueError('Explicit new-runner opt-in')
        if threading.current_thread() is not threading.main_thread():
            raise ValueError('Process FD installation requires main thread')
        if sys.stdout.fileno()!=1 or sys.stderr.fileno()!=2:
            raise ValueError('Exact process standard streams required')
        if not _active_lock.acquire(blocking=False):
            raise PolicyStop('Only one same-process FD capture; no hot replacement')
        self.budget=budget;self.pid=os.getpid();self.saved={};self.writefds=[]
        self.threads=[];self.pipes={};self.sinks={};self.errors=[];self.lock=threading.Lock()
        self.closed=False;self.pipe_capacities={};self.rows={name:dict(read_bytes=0,written_bytes=0,discarded_after_error_bytes=0)
                                    for name in ('stdout','stderr')}
        try:
            self.libc=ctypes.CDLL(None)
            self.libc.fflush.argtypes=[ctypes.c_void_p];self.libc.fflush.restype=ctypes.c_int
            self._flush_streams()
            for fd,name in ((1,'stdout'),(2,'stderr')):
                self.sinks[name]=budget.open(stdout_path if name=='stdout'else stderr_path,'xb')
                self.saved[fd]=(os.dup(fd),os.get_inheritable(fd))
                read,write=os.pipe2(os.O_CLOEXEC);self.writefds.append(write)
                self.pipe_capacities[name]=fcntl.fcntl(write,fcntl.F_GETPIPE_SZ)
                if (sum(self.pipe_capacities.values())+4*self.CHUNK+
                    budget.max_open*budget.text_buffer)>budget.reserve:
                    os.close(read)
                    raise ValueError('Capture pipe/read/stdio buffers must fit final reserve')
                self.pipes[name]=os.fdopen(read,'rb',buffering=0)
                t=threading.Thread(target=self._drain,args=(name,),daemon=True,
                                   name='data-same-process-'+name)
                t.start();self.threads.append(t)
                os.dup2(write,fd,inheritable=True)
            for write in self.writefds:os.close(write)
            self.writefds=[]
        except BaseException:
            for fd,(saved,inheritable)in self.saved.items():
                os.dup2(saved,fd,inheritable=inheritable);os.close(saved)
            for write in self.writefds:os.close(write)
            for t in self.threads:t.join(timeout=.2)
            for name,sink in self.sinks.items():
                if not any(t.is_alive()for t in self.threads):
                    if name in self.pipes:self.pipes[name].close()
                    sink.close()
            _active_lock.release()
            raise

    def _flush_streams(self):
        sys.stdout.flush();sys.stderr.flush()
        if self.libc.fflush(None)!=0:raise PolicyStop('C stdio flush failed')

    def _error(self,message):
        with self.lock:self.errors.append(message)
        try:self.budget.state.fail(message)
        except PolicyStop:pass

    def _drain(self,name):
        row=self.rows[name];pipe=self.pipes[name];sink=self.sinks[name];failed=False
        try:
            while True:
                data=pipe.read(self.CHUNK)
                if not data:break
                row['read_bytes']+=len(data)
                if failed:
                    row['discarded_after_error_bytes']+=len(data);continue
                try:
                    sink.write(data);row['written_bytes']+=len(data)
                except BaseException as e:
                    failed=True;row['discarded_after_error_bytes']+=len(data)
                    self._error(name+' capture incomplete: '+repr(e))
        except BaseException as e:self._error(name+' pipe read failed: '+repr(e))
        finally:
            try:pipe.close();sink.close()
            except BaseException as e:self._error(name+' capture close failed: '+repr(e))

    def close(self,*,join_s=2.):
        if self.closed:raise PolicyStop('FD capture already closed')
        if os.getpid()!=self.pid:raise PolicyStop('No cross-process capture close')
        if not self.budget.state.sealed:
            raise PolicyStop('Seal native irreversibly before closing process capture')
        if not 0<join_s<float('inf'):raise ValueError('Finite capture close deadline')
        try:
            try:self._flush_streams()
            except BaseException as e:self._error('Final Python/C flush failed: '+repr(e))
            for fd,(saved,inheritable)in self.saved.items():
                os.dup2(saved,fd,inheritable=inheritable);os.close(saved)
            self.saved.clear()
            until=time.monotonic()+join_s
            for t in self.threads:t.join(max(0.,until-time.monotonic()))
            if any(t.is_alive()for t in self.threads):
                self._error('FD capture blocked/inherited pipe still open at close')
            self.closed=True
        finally:_active_lock.release()
        receipt=self.snapshot()
        if self.errors:
            error=PolicyStop('Incomplete same-process FD capture; keep failure receipt')
            error.receipt=receipt;raise error
        return receipt

    def snapshot(self):
        return dict(closed=self.closed,complete=self.closed and not self.errors,
            streams={k:dict(v)for k,v in self.rows.items()},errors=list(self.errors),
            per_reader_userspace_chunk_bytes=self.CHUNK,
            highwater_only_persisted_controlled_logical_bytes=True,
            cross_process_counter=False,kernel_pipe_capacity_bytes=dict(self.pipe_capacities),blocked_kernel_or_descendant_close_bound_guaranteed=False)
