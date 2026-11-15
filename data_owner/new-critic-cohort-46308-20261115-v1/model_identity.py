"""Actual model numeric identity; no MJB truncation or world construction."""
import hashlib,json

def numeric(model):
 import numpy as np
 arrays={};options={}
 for name in sorted(dir(model)):
  if name.startswith('_'):continue
  a=getattr(model,name)
  if isinstance(a,np.ndarray):
   a=np.ascontiguousarray(a);arrays[name]={'dtype':a.dtype.str,'shape':list(a.shape),'bytes':a.nbytes,'sha256':hashlib.sha256(memoryview(a).cast('B') if a.nbytes else b'').hexdigest()}
 for name in sorted(dir(model.opt)):
  if name.startswith('_'):continue
  a=getattr(model.opt,name)
  if isinstance(a,np.ndarray):options[name]=a.tolist()
  elif isinstance(a,(int,float,bool)):options[name]=a
 return {'arrays':arrays,'options':options}

def identity(model):
 value=numeric(model);raw=json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode();return hashlib.sha256(raw).hexdigest(),value
