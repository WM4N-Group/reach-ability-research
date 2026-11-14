"""Explicit relocations for SEALED OFFLINE consumers, not data-role permissions.

No env lookup, discovery, symlink rewriting, implicit fallback or remote access.
A relocation maps path identity only; the original SHA checks still apply.
Strict mode refuses any unmapped file except the new approved input/output roots.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path

_CONTEXT=ContextVar('reach_offline_analysis_paths',default=None)


def resolve(path):
    path=Path(path)
    cfg=_CONTEXT.get()
    if cfg is None:return path
    absolute=path.absolute()
    if '..' in absolute.parts:raise ValueError('Parent traversal is not an explicit analysis source')
    for old,new in cfg['mappings']:
        if absolute==old or absolute.is_relative_to(old):
            target=new/absolute.relative_to(old)
            # No symlink escape into a different owner/environment.
            if not target.resolve().is_relative_to(new.resolve()):
                raise ValueError('Relocated analysis input escapes its sealed source root')
            return target
    if any(absolute==root or absolute.is_relative_to(root) for root in cfg['allowed_roots']):return absolute
    if cfg['strict']:raise ValueError('Unmapped offline analysis source; explicit path/SHA staging required: '+str(path))
    return path


@contextmanager
def relocated(mappings,*,allowed_roots=(),strict=True):
    rows=[]
    for source,target in mappings.items():
        a,b=Path(source),Path(target)
        if not a.is_absolute() or not b.is_absolute() or '..' in a.parts or '..' in b.parts:
            raise ValueError('Explicit absolute source and destination roots required')
        if not b.is_dir() or b.is_symlink():raise ValueError('Existing nonsymlink staging root required')
        rows.append((a,b))
    # Nested original mappings could shadow one another; do not accept ambiguity.
    for i,(a,_) in enumerate(rows):
        if any(a==b or a.is_relative_to(b) or b.is_relative_to(a) for b,_ in rows[i+1:]):
            raise ValueError('Ambiguous overlapping source relocations')
    roots=tuple(Path(p).absolute() for p in allowed_roots)
    token=_CONTEXT.set(dict(mappings=tuple(rows),allowed_roots=roots,strict=bool(strict)))
    try:yield
    finally:_CONTEXT.reset(token)
