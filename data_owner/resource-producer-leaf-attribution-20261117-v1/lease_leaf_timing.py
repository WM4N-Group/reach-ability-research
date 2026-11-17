"""Default-OFF private original PerGpuLease.check leaf timings, NOT a repair.

No lease acquisition/GPU/subprocess/IO on build, no original module/instance edit,
no extra probe/query or owner stamp. Caller may select this only in a NEW frozen
program. ResourceWatch must still publish real atomic oldest/completed and fail
above2s; timing records never confer authority/freshness or resurrect a scope.
"""
import ast
import copy
from dataclasses import dataclass
import hashlib
from pathlib import Path
import time
import threading
import types

SOURCE_SHA='d44b3176255d177d432a4243da2b4a9a472881222fc1079224c82a9140dd9857'
HOOK='_data_original_lease_measure_leaf'
LABELS={'os.fstat':'held_lock_fstat','p.stat':'held_lock_path_stat',
        'self.authority':'original_authority_callback','sha':'held_binding_file_SHA',
        'parse_gpu':'parse_original_GPU_identity','torch.cuda.is_initialized':'original_CUDA_initialized_read',
        'own_memory_bytes':'original_PID_memory_parse'}

@dataclass(frozen=True)
class LeafAttempt:
    started:float
    completed:float
    stages:tuple
    error_type:str|None
    original_query_count:int
    cached_original_GPU_result:bool
    diagnostic_only_not_owner_stamp:bool=True

class LeafTrace:
    def __init__(self):self.last_attempt=None


def _identity(code):
    return(code.co_code,tuple(_identity(x)if isinstance(x,types.CodeType)else x for x in code.co_consts),
           code.co_names,code.co_varnames,code.co_freevars,code.co_cellvars,code.co_argcount,
           code.co_kwonlyargcount,code.co_posonlyargcount,code.co_flags)


def build_timed_check(bound_original=None, *, enabled=False):
    """Return (private bound callable, bounded immutable trace); no installation."""
    if type(enabled)is not bool:raise ValueError('Explicit future instrumentation opt-in')
    if not enabled:return None
    if not isinstance(bound_original,types.MethodType):raise ValueError('Exact original bound check method')
    function=bound_original.__func__;path=Path(function.__code__.co_filename)
    if path.is_symlink()or hashlib.sha256(path.read_bytes()).hexdigest()!=SOURCE_SHA:
        raise ValueError('Exact original held-lease source, never a changed/foreign implementation')
    tree=ast.parse(path.read_bytes());cls=next(n for n in tree.body if isinstance(n,ast.ClassDef)and n.name=='PerGpuLease')
    node=next(n for n in cls.body if isinstance(n,ast.FunctionDef)and n.name=='check')
    rootcode=compile(tree,str(path),'exec',dont_inherit=True)
    classcode=next(x for x in rootcode.co_consts if isinstance(x,types.CodeType)and x.co_name=='PerGpuLease')
    expected=next(x for x in classcode.co_consts if isinstance(x,types.CodeType)and x.co_name=='check')
    if _identity(function.__code__)!=_identity(expected)or function.__defaults__!=(False,):
        raise ValueError('Original code/defaults required; no hot/foreign callback')
    selected=[]
    class Instrument(ast.NodeTransformer):
        def visit_Call(self,n):
            # Keep original expressions, args/kwargs/order/short-circuit intact.
            n=self.generic_visit(n);name=ast.unparse(n.func)
            label=LABELS.get(name)
            if name=='subprocess.check_output':
                query=ast.literal_eval(n.args[0].right)[0]
                label='original_nvidia_GPU_inventory_query' if query.startswith('--query-gpu=')else'original_nvidia_PID_memory_query'
            if label is None:return n
            selected.append(label)
            return ast.copy_location(ast.Call(func=ast.Name(id=HOOK,ctx=ast.Load()),
                args=[ast.Constant(label),ast.Lambda(args=ast.arguments(posonlyargs=[],args=[],kwonlyargs=[],kw_defaults=[],defaults=[]),body=n)],keywords=[]),n)
    changed=Instrument().visit(copy.deepcopy(node));ast.fix_missing_locations(changed)
    class Strip(ast.NodeTransformer):
        def visit_Call(self,n):
            if isinstance(n.func,ast.Name)and n.func.id==HOOK:return self.visit(n.args[1].body)
            return self.generic_visit(n)
    restored=Strip().visit(copy.deepcopy(changed));ast.fix_missing_locations(restored)
    if ast.dump(restored,include_attributes=False)!=ast.dump(node,include_attributes=False):raise ValueError('Only timing wrappers permitted')
    if len(selected)!=10 or selected.count('original_nvidia_GPU_inventory_query')!=1 or selected.count('original_nvidia_PID_memory_query')!=1:
        raise ValueError('Exact finite ten source sites, two original GPU queries')
    trace=LeafTrace();local=threading.local()
    def measure(label,action):
        before=time.monotonic()
        try:return action()
        finally:local.stack[-1].append((label,before,time.monotonic()))
    namespace=dict(function.__globals__);namespace[HOOK]=measure
    unit=ast.fix_missing_locations(ast.Module(body=[changed],type_ignores=[]));exec(compile(unit,str(Path(__file__).resolve())+'[private-original-check-leaf-timing]','exec',dont_inherit=True),namespace)
    private=namespace['check'];private.__defaults__=function.__defaults__
    def check(self,force=False):
        started=time.monotonic();stages=[];error=None
        stack=getattr(local,'stack',None)
        if stack is None:stack=[];local.stack=stack
        stack.append(stages)
        try:return private(self,force)
        except BaseException as exc:error=type(exc).__name__;raise
        finally:
            stack.pop();queries=sum(label.startswith('original_nvidia_')for label,_,_ in stages)
            trace.last_attempt=LeafAttempt(started,time.monotonic(),tuple(stages),error,queries,queries==0 and error is None)
    return types.MethodType(check,bound_original.__self__),trace
