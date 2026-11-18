"""Private original held-check copy; only the serial GPU-reading block changes.

Lease construction, entry (real CLI), FDs, authority, binding SHA, cache,
absolute caps and exit remain original. No monkeypatch, retry, second owner
probe, stamp, readiness decision or policy-cycle change here.
"""
import ast
import copy
from dataclasses import dataclass,field
from collections import deque
from hashlib import sha256
from pathlib import Path
import time
import types

ORIGINAL='d44b3176255d177d432a4243da2b4a9a472881222fc1079224c82a9140dd9857'
OLD_GPU_TARGETS=('args','gpu','v',None,'apps','torch','initialized','used')
NEW_BLOCK='''
def _initialized_after_GPU_read():
    torch = sys.modules.get('torch')
    return torch is not None and torch.cuda.is_initialized()
reading = _data_real_GPU_read(initialized=_initialized_after_GPU_read,free_floor_mib=1024)
v = dict(UUID=self.profile['UUID'], index=self.index, free_MiB=reading.free_mib, utilization_percent=reading.utilization)
need(v['free_MiB'] >= 1024, 'Shared free safety1GiB exhausted; stop new dispatch, do not evict')
used = reading.own_bytes
'''

def need(ok,why):
    if not ok:raise ValueError(why)

def code_id(c):
    return(c.co_code,tuple(code_id(x)if isinstance(x,types.CodeType)else x for x in c.co_consts),c.co_names,
           c.co_varnames,c.co_freevars,c.co_cellvars,c.co_argcount,c.co_kwonlyargcount,c.co_posonlyargcount,c.co_flags)

@dataclass(frozen=True)
class TraceRow:
    started:float
    completed:float
    transport:str='direct_NVML_no_subprocess'
    error_type:str|None=None
    own_compute_bytes:int|None=None

@dataclass
class Trace:
    last_gpu_read:TraceRow|None=None
    GPU_read_calls:int=0
    tail:deque=field(default_factory=lambda:deque(maxlen=128))
    actual_method_code_authoritative_for_non_transport:bool=True
    diagnostic_only_not_watch_stamp:bool=True


def build_direct_held_check(bound_original=None,reader=None,*,enabled=False):
    need(type(enabled)is bool,'Explicit new program option')
    if not enabled:return None
    from per_gpu_lease import PerGpuLease
    need(isinstance(bound_original,types.MethodType) and type(bound_original.__self__)is PerGpuLease
         and bound_original.__func__ is PerGpuLease.check and bound_original.__self__.index==0 and callable(reader),
         'One exact original GPU0 lease instance and callable metadata transport')
    f=bound_original.__func__;p=Path(f.__code__.co_filename)
    raw=p.read_bytes();need(not p.is_symlink() and sha256(raw).hexdigest()==ORIGINAL,'Exact held lease source bytes')
    tree=ast.parse(raw);cls=next(n for n in tree.body if isinstance(n,ast.ClassDef)and n.name=='PerGpuLease')
    old=next(n for n in cls.body if isinstance(n,ast.FunctionDef)and n.name=='check')
    module_code=compile(tree,str(p),'exec',dont_inherit=True)
    cls_code=next(n for n in module_code.co_consts if isinstance(n,types.CodeType)and n.co_name=='PerGpuLease')
    expected=next(n for n in cls_code.co_consts if isinstance(n,types.CodeType)and n.co_name=='check')
    need(code_id(f.__code__)==code_id(expected) and f.__defaults__==(False,),'Exact live held-check implementation')
    node=copy.deepcopy(old);b=node.body[-2].body;original_block=copy.deepcopy(b[2:10]);patch=ast.parse(NEW_BLOCK).body
    targets=tuple(t.targets[0].id if isinstance(t,ast.Assign) else None for t in original_block)
    need(len(b)==15 and targets==OLD_GPU_TARGETS and len(patch)==5,'Reviewed original command/identity/floor/accounting block')
    b[2:10]=patch
    restored=copy.deepcopy(node);restored.body[-2].body[2:2+len(patch)]=original_block
    need(ast.dump(restored,include_attributes=False)==ast.dump(old,include_attributes=False),
         'Private transform retains all non-GPU logic exactly, including caps and owner/PID/FD checks')
    trace=Trace()
    def read_once(**kwargs):
        t=time.monotonic();trace.GPU_read_calls+=1
        try:
            r=reader(**kwargs)
        except BaseException as e:
            trace.last_gpu_read=TraceRow(t,time.monotonic(),error_type=type(e).__name__);trace.tail.append(trace.last_gpu_read);raise
        trace.last_gpu_read=TraceRow(t,time.monotonic(),own_compute_bytes=r.own_bytes)
        trace.tail.append(trace.last_gpu_read);return r
    ns=dict(f.__globals__);ns['_data_real_GPU_read']=read_once
    unit=ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[]))
    exec(compile(unit,str(Path(__file__).resolve())+'[private-original-held-source]','exec',dont_inherit=True),ns)
    return types.MethodType(ns['check'],bound_original.__self__),trace
