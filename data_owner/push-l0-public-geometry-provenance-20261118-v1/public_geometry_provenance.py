"""Source-only provenance for this exact original L0 public cuboid declaration.

Never suppress the original resolver's public geometry/registry SHA predicate.
No model/world construction, fallback to GT, source mutation or authorization.
"""
import ast
import hashlib
import math
from pathlib import Path

DECLARING_SOURCE_SHA256='f4f05e117486a7b00583cf5cc1eacf0d14a612544bfb91a5984279db34bb9d22'

def public_geometry(registry=None,*,source_path=None,enabled=False):
    if enabled is not True:return None
    p=Path(source_path)
    if not p.is_absolute()or p.is_symlink()or p.resolve(strict=True)!=p:
        raise ValueError('Exact frozen public geometry declaration path required')
    raw=p.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=DECLARING_SOURCE_SHA256:
        raise ValueError('Changed public geometry declaring source')
    fn=next(n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef)and n.name=='registry')
    ret=fn.body[0].value
    if len(fn.body)!=1 or not isinstance(ret,ast.Call)or ast.unparse(ret.func)!='api.SceneRegistry':
        raise ValueError('Original source declaration shape required')
    specs=ret.args[0].elts
    expected={ast.literal_eval(n.args[1]):tuple(ast.literal_eval(n.args[2]))for n in specs}
    actual={}
    for o in registry.objects.values():
        size=tuple(o.size_m)
        if o.body_name in actual or len(size)!=3 or any(type(x)not in(int,float)or not math.isfinite(x)or x<=0 for x in size):
            raise ValueError('Exact finite public cuboid body/dimensions required')
        actual[o.body_name]=size
    if actual!=expected or len(actual)!=len(specs):
        raise ValueError('Current public geometry differs from pinned declaring source')
    return actual,DECLARING_SOURCE_SHA256
