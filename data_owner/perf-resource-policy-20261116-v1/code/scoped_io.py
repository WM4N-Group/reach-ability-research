"""Next-program controlled output accounting. No simulation/model imports.
Not a security sandbox: bypass/unknown writers fail at periodic reconciliation.
"""
from pathlib import Path
import io,os,stat,threading,time,json

class PolicyStop(RuntimeError):pass
class StopState:
 def __init__(self):self.reason=None;self.sealed=False;self.lock=threading.RLock()
 def fail(self,why):
  with self.lock:
   if self.reason is None:self.reason=str(why)
  raise PolicyStop(self.reason)
 def check(self):
  with self.lock:
   if self.reason is not None:raise PolicyStop(self.reason)
   if self.sealed:raise PolicyStop('Native execution sealed for finalization')

class ScopeIO:
 def __init__(self,root,*,cap_bytes,reserve_bytes,state=None,max_open=16,text_buffer_bytes=8192):
  if type(cap_bytes)is not int or type(reserve_bytes)is not int or not 0<reserve_bytes<cap_bytes:raise ValueError('Explicit cap and bounded final/buffer reserve')
  if type(max_open)is not int or not 1<=max_open<=64 or type(text_buffer_bytes)is not int or text_buffer_bytes<=0 or reserve_bytes<max_open*text_buffer_bytes:raise ValueError('Bound all open text buffers inside reserve')
  self.pid=os.getpid();self.root=Path(root).resolve(strict=True);self.cap=cap_bytes;self.reserve=reserve_bytes;self.state=state or StopState();self.max_open=max_open;self.text_buffer=text_buffer_bytes;self.lock=threading.RLock();self.finalizing=False;self.nodes=self._scan();self.active=set();self.used=sum(v[0]for v in self.nodes.values());self.highwater=self.used;self.metrics=dict(write_calls=0,bytes_requested=0,reconcile_calls=0,reconcile_wall_s=0.,paths_opened=0);self._limit(self.used)
 def _check_process(self):
  if os.getpid()!=self.pid:self.state.fail('Counter cannot be inherited by another process')
 def _path(self,path):
  self._check_process();p=Path(path)
  if '..'in p.parts:self.state.fail('Parent traversal denied')
  p=p if p.is_absolute()else self.root/p
  try:rel=p.relative_to(self.root)
  except ValueError:self.state.fail('Foreign output root')
  q=self.root
  for part in rel.parts:
   q=q/part
   if q.is_symlink():self.state.fail('Output symlink denied: '+str(q))
  if not p.resolve(strict=False).is_relative_to(self.root):self.state.fail('Output escaped root')
  return p
 def _scan(self):
  result={};stack=[self.root]
  while stack:
   with os.scandir(stack.pop())as it:
    for entry in it:
     s=entry.stat(follow_symlinks=False)
     if stat.S_ISDIR(s.st_mode):stack.append(Path(entry.path))
     elif stat.S_ISREG(s.st_mode)and s.st_nlink==1:result[Path(entry.path)]=(s.st_size,s.st_dev,s.st_ino)
     else:raise PolicyStop('Unexpected symlink/hardlink/nonregular output: '+entry.path)
  return result
 def _limit(self,total):
  if total>=self.cap-(0 if self.finalizing else self.reserve):self.state.fail('Output cap/reserve exhausted before write')
 def _precharge(self,path,end):
  self._check_process();old,dev,ino=self.nodes[path];total=self.used+max(0,end-old);self._limit(total);self.nodes[path]=(max(old,end),dev,ino);self.used=total;self.highwater=max(self.highwater,total)
 def open(self,path,mode='xb',*,encoding=None,errors=None,newline=None,buffering=-1):
  p=self._path(path);binary='b'in mode
  if any(c in mode for c in 'r+')or mode.replace('b','')not in('x','w','a'):raise ValueError('Only controlled exclusive/append output; reads use original Path')
  if not binary and (encoding not in(None,'utf-8')or errors not in(None,'strict')or newline not in(None,'\n')):raise ValueError('Exact UTF8/LF text ABI')
  with self.lock:
   if not self.finalizing:self.state.check()
   if p in self.active or len(self.active)>=self.max_open:self.state.fail('Duplicate writer or bounded file-handle limit')
   exists=p.exists()
   if exists and p not in self.nodes:self.state.fail('Unregistered existing output')
   if exists and 'a'not in mode:self.state.fail('No silent overwrite of existing output')
   p.parent.mkdir(parents=True,exist_ok=True);flags=os.O_WRONLY|os.O_CREAT|os.O_CLOEXEC|os.O_NOFOLLOW|(os.O_APPEND if 'a'in mode else os.O_EXCL);fd=os.open(p,flags,0o600);s=os.fstat(fd)
   if not stat.S_ISREG(s.st_mode)or s.st_nlink!=1:os.close(fd);self.state.fail('Not an unaliased regular output')
   if exists and self.nodes[p]!=(s.st_size,s.st_dev,s.st_ino):os.close(fd);self.state.fail('Output replaced/changed outside controlled writer')
   self.nodes[p]=(s.st_size,s.st_dev,s.st_ino);self.active.add(p);self.metrics['paths_opened']+=1;f=BinarySink(self,p,os.fdopen(fd,'wb',buffering=0),s.st_size if'a'in mode else 0,append='a'in mode)
   return f if binary else TextSink(f,self.text_buffer)
 def replace(self,src,dst):
  src,dst=self._path(src),self._path(dst)
  with self.lock:
   if not self.finalizing:self.state.check()
   if src in self.active or dst in self.active or src not in self.nodes:self.state.fail('Replace requires known closed source/destination')
   old=self.nodes.get(dst,(0,0,0))[0];os.replace(src,dst);self.nodes[dst]=self.nodes.pop(src);self.used-=old
 def begin_finalization(self):
  # Irreversible; native fast guard uses this SAME state and now refuses steps.
  with self.lock,self.state.lock:self.state.sealed=True;self.finalizing=True
 def reconcile(self):
  self._check_process();start=time.perf_counter()
  try:
   with self.lock:
    actual=self._scan()
    if actual!=self.nodes:self.state.fail('Unknown/missing/replaced/resized output; accounting cannot silently resync')
    self._limit(sum(v[0]for v in actual.values()));return self.used
  except BaseException as e:
   self.state.fail('Reconciliation I/O error: '+repr(e))
  finally:self.metrics['reconcile_calls']+=1;self.metrics['reconcile_wall_s']+=time.perf_counter()-start
 def event_loss(self):self.state.fail('Output observation/event loss; stop rather than undercount')
 def snapshot(self):
  with self.lock:return dict(used_bytes=self.used,controlled_logical_highwater_bytes=self.highwater,reserve_bytes=self.reserve,finalizing=self.finalizing,failed=self.state.reason is not None,failure=self.state.reason,open_files=len(self.active),metrics=dict(self.metrics))

class BinarySink:
 def __init__(self,budget,path,f,pos,append=False):self.b,self.path,self._f,self.pos,self.append=budget,path,f,pos,append
 @property
 def closed(self):return self._f.closed
 @property
 def name(self):return str(self.path)
 def fileno(self):return self._f.fileno()  # trusted fsync only; arbitrary os.write is NOT covered.
 def writable(self):return True
 def readable(self):return False
 def read(self,*_):raise io.UnsupportedOperation('Write-only controlled sink')
 def seekable(self):return True
 def tell(self):return self.pos
 def write(self,data):
  data=memoryview(data)
  with self.b.lock:
   if not self.b.finalizing:self.b.state.check()
   self.b._precharge(self.path,self.pos+data.nbytes)
   try:n=self._f.write(data)
   except BaseException as e:self.b.state.fail('Controlled write I/O error: '+repr(e))
   if n!=data.nbytes:self.b.state.fail('Partial write; reservation retained and scope stopped')
   self.pos+=n;self.b.metrics['write_calls']+=1;self.b.metrics['bytes_requested']+=n;return n
 def seek(self,offset,whence=0):
  if self.append:raise io.UnsupportedOperation('Append streams cannot seek')
  with self.b.lock:
   self.pos=self._f.seek(offset,whence);return self.pos
 def truncate(self,size=None):
  if self.append:raise io.UnsupportedOperation('Append streams cannot truncate')
  with self.b.lock:
   size=self.pos if size is None else size
   if not self.b.finalizing:self.b.state.check()
   old=self.b.nodes[self.path][0];self.b._precharge(self.path,size)
   try:n=self._f.truncate(size)
   except BaseException as e:self.b.state.fail('Truncate I/O error: '+repr(e))
   current,dev,ino=self.b.nodes[self.path];self.b.nodes[self.path]=(size,dev,ino);self.b.used-=current-size;return n
 def flush(self):
  try:self._f.flush()
  except BaseException as e:self.b.state.fail('Flush I/O error: '+repr(e))
 def close(self):
  if self.closed:return
  try:self._f.close()
  finally:
   with self.b.lock:self.b.active.discard(self.path)
 def __enter__(self):return self
 def __exit__(self,*_):self.close()

class TextSink:
 encoding='utf-8';errors='strict'
 def __init__(self,binary,limit):self.binary=binary;self.limit=limit;self.pending=bytearray()
 @property
 def closed(self):return self.binary.closed
 @property
 def name(self):return self.binary.name
 def fileno(self):return self.binary.fileno()
 def writable(self):return True
 def tell(self):return self.binary.tell()+len(self.pending)
 def write(self,text):
  if not self.binary.b.finalizing:self.binary.b.state.check()
  if not isinstance(text,str):raise TypeError('text required')
  raw=text.encode('utf-8')
  for start in range(0,len(raw),self.limit):
   if len(self.pending)+min(self.limit,len(raw)-start)>self.limit:self.flush()
   self.pending.extend(raw[start:start+self.limit])
   if len(self.pending)>=self.limit:self.flush()
  return len(text)
 def flush(self):
  if self.pending:self.binary.write(self.pending);self.pending.clear()
  self.binary.flush()
 def close(self):
  if self.closed:return
  try:self.flush()
  finally:self.binary.close()
 def __enter__(self):return self
 def __exit__(self,*_):self.close()

def scoped_path_class(budget):
 """Private globals injection ONLY; never patch pathlib/original loaded module."""
 class BudgetPath(type(Path())):
  def open(self,mode='r',buffering=-1,encoding=None,errors=None,newline=None):
   if any(c in mode for c in 'wxa+'):return budget.open(str(self),mode,buffering=buffering,encoding=encoding,errors=errors,newline=newline)
   return Path(str(self)).open(mode,buffering=buffering,encoding=encoding,errors=errors,newline=newline)
  def replace(self,target):budget.replace(str(self),str(target));return type(self)(target)
 return BudgetPath
