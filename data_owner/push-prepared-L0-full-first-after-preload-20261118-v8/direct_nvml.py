"""GPU0 metadata transport for the pinned 46308 driver.

No lease, authority, watchdog, resource admission, physics, or integration with
PerGpuLease. Never turns a returned sample into a fresh stamp; the unchanged ResourceWatch owns it.
"""
import ctypes as C
from dataclasses import dataclass
import hashlib
from pathlib import Path
import os
import platform
import time

LIB=Path('/usr/lib/x86_64-linux-gnu/libnvidia-ml.so.580.82.07')
DRIVER_SHA='008cc04afc61b8317ed4ddccfa2d1bd367ceb6e71334eb352dc846e0ac450340'
LIB_ID=(2050,29127223,2271320)
UUID='GPU-297c1146-bcec-a8ee-8437-d9603392a2e1'
MAX_ROWS=256
U32_MAX=(1<<32)-1
U64_MAX=(1<<64)-1
MIB=1<<20
CAP=3<<30

class NvmlReadError(RuntimeError):pass

def need(ok,message):
    if not ok:raise NvmlReadError(message)

class Memory(C.Structure):
    _fields_=[('version',C.c_uint),('total',C.c_ulonglong),('reserved',C.c_ulonglong),
              ('free',C.c_ulonglong),('used',C.c_ulonglong)]

class Process(C.Structure):
    _fields_=[('pid',C.c_uint),('memory',C.c_ulonglong),('gpu_instance',C.c_uint),('compute_instance',C.c_uint)]

class Utilization(C.Structure):
    _fields_=[('gpu',C.c_uint),('memory',C.c_uint)]


def own_bytes(rows,*,pid,initialized):
    need(type(pid)is int and 0<pid<=U32_MAX and type(initialized)is bool,'Exact own PID/CUDA observation state')
    values=set()
    for p,used,gi,ci in rows:
        need(0<p<=U32_MAX and gi==ci==U32_MAX,'Only exact non-MIG physical process rows')
        if p==pid:
            need(0<=used<U64_MAX,'Own GPU memory unknown')
            values.add(used)
    need(len(values)<=1,'Conflicting same-UUID/PID memory observations')
    if not values:
        need(not initialized,'Initialized CUDA PID missing; unknown is not zero')
        return None
    value=next(iter(values));need(value<=CAP,'Own 3 GiB exact-byte cap exceeded')
    return value

@dataclass(frozen=True)
class Reading:
    oldest:float
    completed:float
    free_mib:int
    utilization:int
    own_bytes:int|None
    compute_rows:int

class DirectNvml:
    def __init__(self,*,enabled=False):
        need(enabled is True,'Explicit readonly diagnostic only')
        need(platform.machine()=='x86_64' and C.sizeof(Process)==24 and C.sizeof(Memory)==40 and C.sizeof(Utilization)==8,
             'Exact reviewed driver ABI shape')
        need(LIB.resolve(strict=True)==LIB and LIB.is_file(),'Pinned canonical NVML object')
        st=LIB.stat();need((st.st_dev,st.st_ino,st.st_size)==LIB_ID and hashlib.sha256(LIB.read_bytes()).hexdigest()==DRIVER_SHA,
             'Exact known driver object, not searched via environment')
        self.dll=C.CDLL(str(LIB));self.pid=os.getpid();self.closed=True
        self.init=self._fn('nvmlInit_v2');self._shutdown=self._fn('nvmlShutdown');self._handle=self._fn('nvmlDeviceGetHandleByIndex_v2',C.c_uint,C.POINTER(C.c_void_p))
        self._index=self._fn('nvmlDeviceGetIndex',C.c_void_p,C.POINTER(C.c_uint));self._uuid=self._fn('nvmlDeviceGetUUID',C.c_void_p,C.POINTER(C.c_char),C.c_uint)
        self._memory=self._fn('nvmlDeviceGetMemoryInfo_v2',C.c_void_p,C.POINTER(Memory));self._util=self._fn('nvmlDeviceGetUtilizationRates',C.c_void_p,C.POINTER(Utilization))
        self._processes=self._fn('nvmlDeviceGetComputeRunningProcesses_v3',C.c_void_p,C.POINTER(C.c_uint),C.POINTER(Process))
        self.call(self.init);self.closed=False

    def _fn(self,name,*args):
        fn=getattr(self.dll,name);fn.argtypes=list(args);fn.restype=C.c_int;return fn

    @staticmethod
    def call(fn,*args):
        rc=fn(*args);need(rc==0,f'{fn.__name__} returned {rc}; no retry, fallback, or unknown-as-zero')

    def observe(self,*,initialized,free_floor_mib):
        need(not self.closed and os.getpid()==self.pid,'Same live non-inherited diagnostic process')
        need(type(free_floor_mib)is int and free_floor_mib in (1024,4096),'Original explicit memory floor')
        begin=time.monotonic();device=C.c_void_p();self.call(self._handle,0,C.byref(device))
        idx=C.c_uint(U32_MAX);uuid=C.create_string_buffer(96)
        self.call(self._index,device,C.byref(idx));self.call(self._uuid,device,uuid,len(uuid));need(idx.value==0 and uuid.value==UUID.encode('ascii'),'Exact physical GPU index/UUID, not cached')
        mem=Memory();mem.version=C.sizeof(Memory)|(2<<24);util=Utilization(U32_MAX,U32_MAX)
        self.call(self._memory,device,C.byref(mem));self.call(self._util,device,C.byref(util))
        need(0<=mem.free<=mem.total<U64_MAX and mem.total>0 and util.gpu<=100,'Finite native inventory counters')
        free=mem.free//MIB
        need(free>=free_floor_mib,'Original shared free capacity floor: refuse before PID accounting')
        count=C.c_uint(MAX_ROWS);buf=(Process*MAX_ROWS)();self.call(self._processes,device,C.byref(count),buf)
        need(count.value<=MAX_ROWS,'Bounded native PID rows: no truncation')
        initialized=initialized() if callable(initialized) else initialized  # original CUDA state read AFTER actual process query
        used=own_bytes(((r.pid,r.memory,r.gpu_instance,r.compute_instance)for r in buf[:count.value]),pid=self.pid,initialized=initialized)
        return Reading(begin,time.monotonic(),free,util.gpu,used,count.value)

    def close(self):
        need(not self.closed and os.getpid()==self.pid,'Exactly one same-process NVML close')
        self.closed=True;self.call(self._shutdown)
