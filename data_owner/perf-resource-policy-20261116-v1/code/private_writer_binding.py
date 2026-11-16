"""Bind unchanged recorder bytecode to controlled output in a PRIVATE namespace.
This intentionally changes I/O globals; it is NOT a claim of old audit-policy equivalence.
"""
from pathlib import Path
import hashlib,types,sys
from scoped_io import scoped_path_class

def load_private_writer(source_path,expected_sha256,budget,*,name,package=None,enabled=False):
 if type(enabled)is not bool:raise ValueError('Explicit opt-in')
 if not enabled:return None
 source_path=Path(source_path);raw=source_path.read_bytes()
 if source_path.is_symlink()or hashlib.sha256(raw).hexdigest()!=expected_sha256:raise ValueError('Exact original recorder source')
 if name in sys.modules:raise ValueError('No private writer hot-reload')
 module=types.ModuleType(name);module.__file__=str(source_path);module.__package__=package;sys.modules[name]=module
 try:
  exec(compile(raw,str(source_path),'exec'),module.__dict__)
  module.Path=scoped_path_class(budget)
  module.DATA_controlled_output_policy='future-1s-reconcile-2s-stale-and-prewrite-counter-v1'
  return module
 except BaseException:
  del sys.modules[name];raise
