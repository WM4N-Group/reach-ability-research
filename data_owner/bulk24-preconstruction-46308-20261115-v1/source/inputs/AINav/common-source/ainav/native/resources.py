"""Reuse canonical existing locks; never create a parallel empty lock."""
import fcntl
import os
from pathlib import Path


class ResourceLease:
    def __init__(self, paths):
        if not paths or len(set(str(Path(p).resolve()) for p in paths)) != len(paths):
            raise ValueError('Distinct explicit canonical resource locks required')
        self.paths = tuple(Path(p).absolute() for p in paths)
        self.handles = []
        self.evidence = []

    def __enter__(self):
        try:
            for path in self.paths:
                before = path.stat()  # MUST already exist; no create/new lock.
                fd = os.open(path, os.O_RDWR | os.O_CLOEXEC)
                self.handles.append(fd)
                actual = os.fstat(fd)
                if (before.st_dev, before.st_ino) != (actual.st_dev, actual.st_ino):
                    raise RuntimeError('Canonical lock identity changed during admission')
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                after = path.stat()
                if (after.st_dev, after.st_ino) != (actual.st_dev, actual.st_ino):
                    raise RuntimeError('Canonical lock path was replaced')
                self.evidence.append(dict(path=str(path), device=actual.st_dev, inode=actual.st_ino,
                                          admission='actual_fcntl_exclusive_nonblocking', pid=os.getpid()))
            return self
        except BaseException:
            self.__exit__(None, None, None)
            raise

    def __exit__(self, *args):
        for fd in reversed(self.handles):
            os.close(fd)
        self.handles.clear()
