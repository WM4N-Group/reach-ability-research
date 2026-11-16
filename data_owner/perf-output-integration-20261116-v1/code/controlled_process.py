"""Opt-in direct-child PIPE output capture; not a launcher or process-tree sandbox.

Only the parent writes files through ScopeIO. Two readers apply pipe backpressure;
no communicate(), unbounded queue, shared fork counter or filename-only accounting.
Callers must pin/authorize the executable and argv in their NEW program freeze.
"""
import os
import subprocess
import threading
import time
from scoped_io import PolicyStop


class ControlledProcess:
    CHUNK = 8192

    def __init__(self, argv, budget, *, stdout_path, stderr_path, cwd=None,
                 env=None, stdin=None, enabled=False):
        if enabled is not True:
            raise ValueError('Explicit new-program subprocess opt-in required')
        if (not isinstance(argv, (list, tuple)) or not argv
                or any(type(x) is not str or not x or '\0' in x for x in argv)
                or not os.path.isabs(argv[0])):
            raise ValueError('Explicit absolute executable and literal argv; no shell')
        if stdin not in (None, subprocess.PIPE):
            raise ValueError('Only DEVNULL or caller-owned bounded PIPE stdin')
        self.budget = budget
        self.process = None
        self.threads = []
        self.errors = []
        self.lock = threading.Lock()
        self.closed = False
        self.metrics = {k: dict(read_bytes=0, written_bytes=0, refused_bytes=0)
                        for k in ('stdout', 'stderr')}
        self.sinks = {}
        try:
            self.sinks['stdout'] = budget.open(stdout_path, 'xb')
            self.sinks['stderr'] = budget.open(stderr_path, 'xb')
            self.process = subprocess.Popen(argv, cwd=cwd, env=env,
                stdin=subprocess.DEVNULL if stdin is None else stdin,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                shell=False, bufsize=0, close_fds=True)
            for name in ('stdout', 'stderr'):
                t = threading.Thread(target=self._drain, args=(name,), daemon=True,
                                     name='data-controlled-' + name)
                self.threads.append(t)
                t.start()
        except BaseException:
            if self.process is not None and self.process.poll() is None:
                self.process.kill()
                self.process.wait(timeout=2.)
            for sink in self.sinks.values():
                sink.close()
            raise

    @property
    def stdin(self):
        return self.process.stdin

    def _record_error(self, message):
        with self.lock:
            self.errors.append(message)
        # No native execution may proceed. Do not mutate/kill any other PID.
        try:
            self.budget.state.fail(message)
        except PolicyStop:
            pass
        if self.process.poll() is None:
            try:
                self.process.kill()
            except ProcessLookupError:
                pass

    def _drain(self, name):
        pipe, sink = getattr(self.process, name), self.sinks[name]
        row = self.metrics[name]
        try:
            while True:
                data = pipe.read(self.CHUNK)
                if not data:
                    break
                row['read_bytes'] += len(data)
                try:
                    sink.write(data)
                    row['written_bytes'] += len(data)
                except BaseException:
                    row['refused_bytes'] += len(data)
                    raise
        except BaseException as e:
            self._record_error(name + ' output incomplete: ' + repr(e))
        finally:
            try:
                pipe.close()
                sink.close()
            except BaseException as e:
                self._record_error(name + ' close error: ' + repr(e))

    def finish(self, *, timeout_s, join_s=2.):
        """Finite wait; timeout kills ONLY our direct child and is never success.

        Native stepping must already be stopped before caller closes stdin/waits.
        Stuck filesystem writes or descendants inheriting pipes are close errors;
        no claim of an absolute blocked-kernel or descendant termination bound.
        """
        if self.closed:
            raise PolicyStop('Controlled child already finalized')
        if not 0 < timeout_s < float('inf') or not 0 < join_s < float('inf'):
            raise ValueError('Finite process and drain deadlines required')
        timed_out = False
        try:
            self.process.wait(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            timed_out = True
            self._record_error('Controlled direct child deadline expired')
            try:
                self.process.wait(timeout=2.)
            except subprocess.TimeoutExpired:
                self._record_error('Direct child not reaped after kill')
        until = time.monotonic() + join_s
        for t in self.threads:
            t.join(max(0., until - time.monotonic()))
        if any(t.is_alive() for t in self.threads):
            self._record_error('Output reader blocked/inherited pipe still open at close')
        if self.process.returncode not in (0, None) and not self.errors:
            self._record_error('Controlled child nonzero exit: ' + str(self.process.returncode))
        self.closed = True
        result = dict(returncode=self.process.returncode, timed_out=timed_out,
            complete=not self.errors and self.process.returncode == 0,
            errors=list(self.errors), streams={k: dict(v) for k,v in self.metrics.items()},
            bounded_userspace_chunk_bytes_per_reader=self.CHUNK,
            kernel_pipe_bytes_not_counted_as_persisted_output=True,
            descendant_or_blocked_kernel_termination_guaranteed=False)
        if not result['complete']:
            error = PolicyStop('Controlled output failed; retain incomplete capture evidence')
            error.receipt = result
            raise error
        return result
