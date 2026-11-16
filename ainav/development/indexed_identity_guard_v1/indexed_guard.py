"""Revised static audit policy. NOT old per-tick fresh-resolution equivalence.

No Runtime/model/physics imports. Data must supply real owner stamps, immutable
file inventory, boundary integration and the unchanged dynamic native guards.
Persistent metadata changes: poll<=5s; canonical-only rebindings: poll<=60s.
Arbitrary transient filesystem changes between polls are NOT guaranteed caught.
Imports/exec/new function code are denied while sealed, not silently reindexed.
"""
from pathlib import Path
from dataclasses import dataclass
from types import MappingProxyType
from contextlib import contextmanager
import ast,hashlib,json,math,os,stat,sys,time,weakref

ORIGINAL_METHOD_SHA='e6e848ce969ed0a94f4ccf52310a542fc8c4ff326c1a8a4607c415b7838b070f'
POLICY_ID='AINAV_INDEXED_STATIC_IDENTITY_BOUNDED_AUDIT_20261116_v1'

class GuardViolation(RuntimeError):pass

def need(ok,msg):
    if not ok:raise GuardViolation(msg)

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()

@dataclass(frozen=True)
class AuditPolicy:
    module_poll_calls:int=20
    module_poll_s:float=.25
    metadata_poll_s:float=5.
    canonical_poll_s:float=60.
    audit_budget_s:float=5.
    owner_max_age_s:float=2.
    def __post_init__(self):
        need(type(self.module_poll_calls)is int and 1<=self.module_poll_calls<=20,'Bounded module polling calls')
        need(all(type(x)in(int,float)and math.isfinite(x)and x>0 for x in
                 (self.module_poll_s,self.metadata_poll_s,self.canonical_poll_s,self.audit_budget_s,self.owner_max_age_s)),
             'Finite positive audit/owner deadlines')
        need(self.module_poll_s<=.25 and self.metadata_poll_s<=5 and self.canonical_poll_s<=60 and
             self.audit_budget_s<=5 and self.owner_max_age_s<=2,'Do not silently widen the published audit bounds')

@dataclass(frozen=True)
class OwnerStamp:
    epoch:str
    checked_at:float
    valid_until:float
    valid:bool


def _signature(path,*,follow=True,missing=False):
    try:s=os.stat(path,follow_symlinks=follow)
    except (FileNotFoundError,NotADirectoryError):
        if missing:return None
        raise
    return(s.st_dev,s.st_ino,s.st_mode,s.st_size,s.st_mtime_ns,s.st_ctime_ns)


def _hash_file(path):
    h=hashlib.sha256()
    with open(path,'rb')as f:
        while chunk:=f.read(1024*1024):h.update(chunk)
    return h.hexdigest()

@dataclass(frozen=True)
class FilePin:
    signature:tuple|None
    sha256:str|None
    writable_at_freeze:bool

class FrozenFiles:
    """Measured bootstrap inventory, NOT a signature/security sandbox.

    Data must authorize/bind its digest and verify known source/asset hashes.
    roots alone never authorize a new file: it must be measured in this map.
    No chmod/mount changes. Root/native attackers can bypass Python monitoring.
    """
    def __init__(self,roots,records,missing):
        self.roots=tuple(roots);self.records=MappingProxyType(dict(records));self.missing=frozenset(missing)
        self.record=dict(policy=POLICY_ID,roots=list(roots),files={k:dict(signature=v.signature,sha256=v.sha256,
            writable_at_freeze=v.writable_at_freeze)for k,v in sorted(records.items())},missing=sorted(missing),
            readonly_enforcement_proven=False,initial_trust='OWNER_AUTHORIZED_BOOTSTRAP_MEASUREMENT_NOT_EXTERNAL_AUTHENTICITY')
        self.sha256=digest(self.record)
    @classmethod
    def measure(cls,paths,*,roots,expected_hashes=None,allow_missing=()):
        roots=tuple(str(Path(r).resolve(strict=True))for r in roots);need(roots,'Explicit allowed source/asset roots')
        missing={str(Path(p).absolute())for p in allow_missing};records={};allowed_missing=set();expected_hashes=expected_hashes or {}
        for raw in dict.fromkeys(os.fspath(p)for p in paths):
            raw=str(Path(raw).absolute());canonical=str(Path(raw).resolve())
            need(any(Path(canonical).is_relative_to(r)for r in roots),'File outside authorized inventory roots: '+raw)
            before=_signature(canonical,missing=raw in missing)
            if before is None:
                need(raw in missing,'Explicit missing-module declaration required');allowed_missing.add(raw);continue
            need(stat.S_ISREG(before[2]),'Only regular source/weight/asset files can be pinned')
            if canonical not in records:
                value=_hash_file(canonical);after=_signature(canonical)
                need(before==after,'File changed during bootstrap SHA measurement')
                expected=expected_hashes.get(canonical,expected_hashes.get(raw))
                need(expected is None or value==expected,'Frozen expected source/asset SHA mismatch')
                records[canonical]=FilePin(before,value,os.access(canonical,os.W_OK))
        return cls(roots,records,allowed_missing)

_active=None
_hook_installed=False

def _audit(event,args):
    engine=None if _active is None else _active()
    if engine is None or engine.state not in ('RUNNING','AUDITING'):return
    if event in ('import','exec','function.__new__')or(event=='object.__setattr__'and len(args)>1 and args[1]=='__code__'):
        engine.state='FAILED';engine.failure='Unplanned code/import installation outside paused boundary'
        raise GuardViolation(engine.failure)

def _install_hook(engine):
    global _active,_hook_installed
    previous=None if _active is None else _active()
    need(previous is None or previous is engine or previous.state in ('FAILED','CLOSED'),
         'One sealed identity guard per process, not multiple worlds')
    if not _hook_installed:sys.addaudithook(_audit);_hook_installed=True
    _active=weakref.ref(engine)

def _verify_original(original):
    need(callable(original)and getattr(original,'__code__',None)is not None and
         original.__code__.co_name=='_native_guards'and original.__globals__.get('Path')is Path,
         'Exact original native metadata guard and Path dependency')
    p=Path(original.__code__.co_filename);need(not p.is_symlink(),'No redirected original guard source')
    text=p.read_text();tree=ast.parse(text)
    c=next((n for n in tree.body if isinstance(n,ast.ClassDef)and n.name=='ComplexSceneDriver'),None)
    n=None if c is None else next((n for n in c.body if isinstance(n,ast.FunctionDef)and n.name=='_native_guards'),None)
    need(n is not None and hashlib.sha256(ast.get_source_segment(text,n).encode()).hexdigest()==ORIGINAL_METHOD_SHA,
         'Exact reviewed original callback/world guard source')

def _file(module):
    value=getattr(module,'__file__',None)
    need(value is None or type(value)is str,'Unsupported nonliteral module.__file__; qualify explicitly, not skip')
    return value

def module_paths(registry=sys):
    return tuple(dict.fromkeys(p for _,m in tuple(registry.modules.items())if(p:=_file(m))is not None))

def _callback_stamp(cb):
    return(cb,getattr(cb,'__code__',None),getattr(cb,'__defaults__',None),getattr(cb,'__kwdefaults__',None))

def _same_objects(a,b):return len(a)==len(b)and all(x is y for x,y in zip(a,b))

def _token_capture(values):
    need(type(values)is dict and {'session','target','goal','config_epoch'}<=values.keys(),
         'Actual session/target/immutable goal/config tokens required')
    need(all(type(k)is str for k in values),'Literal identity token names')
    # Keep object references, never trust id() alone or ndarray value equality.
    return tuple((k,v,type(v)in(str,bytes,int,float,bool,type(None)))for k,v in sorted(values.items()))

def _token_equal(a,b):
    if len(a)!=len(b):return False
    for (ka,va,scalar),(kb,vb,other_scalar)in zip(a,b):
        if ka!=kb or scalar!=other_scalar or type(va)is not type(vb):return False
        if scalar:
            if va!=vb:return False
        elif va is not vb:return False
    return True

class IndexedIdentityGuard:
    def __init__(self,original,*,files,owner_fast,owner_refresh,tokens,policy=None,clock=time.monotonic):
        _verify_original(original)
        need(isinstance(files,FrozenFiles)and callable(owner_fast)and callable(owner_refresh)and callable(tokens),
             'Frozen inventory + actual fast owner/refresh/session-token callbacks required')
        self.original=original;self._original_code=original.__code__;self.registry=original.__globals__['sys']
        self.files=files;self.owner_fast=owner_fast;self.owner_refresh=owner_refresh;self.tokens=tokens
        self.policy=AuditPolicy()if policy is None else policy;self.clock=clock;self.state='NEW';self.failure=None
        self.host=None;self._depth=0;self._call_count=0;self._module_count_at_check=0
        self.metrics={k:0 for k in ('fast_checks','module_audits','metadata_audits','canonical_audits','boundaries',
            'canonical_resolves','stat_calls','full_original_calls','owner_refresh_calls')}
        self.metrics.update({k:0. for k in ('owner_fast_wall_s','memory_wall_s','module_audit_wall_s',
            'metadata_audit_wall_s','canonical_audit_wall_s','boundary_wall_s','owner_refresh_wall_s')})
    def _timed(self,key,fn,*args,**kwargs):
        start=time.perf_counter()
        try:return fn(*args,**kwargs)
        finally:self.metrics[key]+=time.perf_counter()-start
    def _owner(self,host):
        s=self.owner_fast(host);now=self.clock();need(type(s)is OwnerStamp,'A real expiring owner stamp, never return True')
        need(type(s.valid)is bool and s.valid and type(s.epoch)is str and s.epoch and
             all(math.isfinite(v)for v in(s.checked_at,s.valid_until))and s.checked_at<=now<=s.valid_until and
             0<=s.valid_until-s.checked_at<=self.policy.owner_max_age_s,'Revoked/expired/invalid owner stamp')
        if hasattr(self,'owner_epoch'):need(s.epoch==self.owner_epoch,'Owner epoch changed')
        else:self.owner_epoch=s.epoch
    def _refresh_owner(self,host):
        self.metrics['owner_refresh_calls']+=1
        need(self.owner_refresh(host)is not False,'Actual owner/resource refresh refused')
    def _step(self,host):
        n=host.r.step_count;t=float(host.r.sim.data.time)
        need(type(n)is int and n>=0 and math.isfinite(t),'Actual task step/clock required')
        return(n,t)
    def _capture_modules(self):
        mapping=self.registry.modules;need(type(mapping)is dict,'Exact dict module registry required')
        return tuple((k,m,_file(m))for k,m in tuple(mapping.items()))
    def _memory(self,host,*,transition=False):
        need(host is self.host and host.r is self.runtime,'Foreign host/runtime')
        p=host.r.sim;current=(p,p.model,p.data,p.queue,p.controller,p.box_push_target)
        need(_same_objects(current,self.world)and host._world is self.world_declaration,'Foreign model/data/FIFO/target world')
        need(self.registry.modules is self.module_map,'Module registry object replaced')
        need(self.original.__code__ is self._original_code and self.original.__globals__.get('Path')is Path,
             'Original guard code/dependency identity changed')
        need(host._stow_installed is self.installed and host._stow_callback_name==self.callback_name and
             frozenset(host._stow_allowed)==self.allowed and len(host._stow_installed)==len(self.installed_items),
             'Callback installation/configuration changed, not an authorized new program')
        for key,stamp in self.installed_items:
            need(_same_objects(_callback_stamp(host._stow_installed.get(key)),stamp),'Callback object/code/default identity changed')
        for key,module,raw,cb in self.critical:
            need(self.module_map.get(key)is module and _file(module)==raw and vars(module).get(self.callback_name)is cb,
                 'Critical alias/path/callback changed')
        if not transition:
            need(len(self.module_map)==len(self.modules),'New/deleted module requires paused boundary')
            need(_token_equal(_token_capture(self.tokens(host)),self.token_snapshot),'Session/target/goal/config binding changed')
    def _index(self,host):
        before=self._capture_modules();raws=dict.fromkeys(raw for _,_,raw in before if raw is not None)
        index={};monitored={};critical=[]
        for raw in raws:
            canonical=str(Path(raw).resolve());self.metrics['canonical_resolves']+=1
            absolute=str(Path(raw).absolute());pin=self.files.records.get(canonical)
            if pin is None:
                need(absolute in self.files.missing and _signature(raw,missing=True)is None,
                     'Unapproved/missing module file: '+raw)
            else:
                need(_signature(raw)==pin.signature and _signature(canonical)==pin.signature,
                     'File metadata changed since owner-authorized SHA snapshot')
            index[raw]=canonical
            for p,follow in ((raw,True),(raw,False),(canonical,True)):
                monitored[p,follow]=_signature(p,follow=follow,missing=pin is None);self.metrics['stat_calls']+=1
        for path,pin in self.files.records.items():
            # Includes explicitly frozen weights/assets, not only module source.
            monitored[path,True]=pin.signature
        for key,module,raw in before:
            if raw is not None and Path(index[raw])in self.allowed:
                canonical=index[raw];cb=vars(module).get(self.callback_name)
                need(canonical in self.installed and cb is self.installed[canonical],'Unbound original source alias/callback')
                critical.append((key,module,raw,cb))
        after=self._capture_modules()
        need(len(before)==len(after)and all(a[0]==b[0]and a[1]is b[1]and a[2]==b[2]for a,b in zip(before,after)),
             'Module set changed while building frozen index')
        self.modules=before;self.index=index;self.monitored=monitored;self.critical=tuple(critical)
        self.token_snapshot=_token_capture(self.tokens(host));self.module_map=self.registry.modules
    def seal(self,host,*,label='initial-loaded-snapshot'):
        need(self.state in ('NEW','BOUNDARY'),'Seal only at an explicitly paused boundary')
        start=time.perf_counter();initial=self.state=='NEW';self.state='BOUNDARY'
        try:
            if initial:
                self.host=host;self.runtime=host.r;p=host.r.sim
                self.world=(p,p.model,p.data,p.queue,p.controller,p.box_push_target);self.world_declaration=host._world
                need(_same_objects(self.world,self.world_declaration),'Original actual root aliases required')
                self.installed=host._stow_installed;self.callback_name=host._stow_callback_name
                self.allowed=frozenset(host._stow_allowed)
                self.installed_items=tuple((k,_callback_stamp(v))for k,v in self.installed.items())
                self.module_map=self.registry.modules;self.critical=()
            else:self._memory(host,transition=True)
            self.metrics['full_original_calls']+=1;self.original(host)  # Boundary only, includes original owner check.
            # Load the real owner's own dependencies before snapshotting. A second
            # refresh after the blocking SHA/index work renews its bounded stamp.
            self._timed('owner_refresh_wall_s',self._refresh_owner,host)
            self._index(host);self._timed('owner_refresh_wall_s',self._refresh_owner,host)
            self._timed('owner_fast_wall_s',self._owner,host)
            self._memory(host);now=self.clock()
            self.last_module=self.last_metadata=self.last_canonical=now;self._module_count_at_check=self._call_count
            self.metrics['boundaries']+=1;self.state='RUNNING';_install_hook(self)
            return dict(policy=POLICY_ID,label=label,inventory_sha256=self.files.sha256,
                        modules=len(self.modules),unique_raw_paths=len(self.index),critical_aliases=len(self.critical),
                        changed_detection_latency=True,old_per_tick_resolution_equivalence=False)
        except BaseException:
            self.state='FAILED';raise
        finally:self.metrics['boundary_wall_s']+=time.perf_counter()-start
    def _modules_check(self):
        current=self._capture_modules()
        need(len(current)==len(self.modules)and all(a[0]==b[0]and a[1]is b[1]and a[2]==b[2]
             for a,b in zip(current,self.modules)),'Module/path/alias metadata changed outside paused boundary')
        self.metrics['module_audits']+=1;self.last_module=self.clock();self._module_count_at_check=self._call_count
    def _metadata_check(self):
        for (path,follow),expected in self.monitored.items():
            actual=_signature(path,follow=follow,missing=expected is None);self.metrics['stat_calls']+=1
            need(actual==expected,'Frozen file/symlink metadata changed: '+path)
        self.metrics['metadata_audits']+=1;self.last_metadata=self.clock()
    def _canonical_check(self):
        for raw,expected in self.index.items():
            value=str(Path(raw).resolve());self.metrics['canonical_resolves']+=1
            need(value==expected,'Canonical alias changed: '+raw)
        self.metrics['canonical_audits']+=1;self.last_canonical=self.clock()
    def check(self,host):
        need(self.state in ('RUNNING','BOUNDARY'),'Failed/closed/unsealed guard cannot issue or resume')
        try:
            self.metrics['fast_checks']+=1;self._call_count+=1
            self._timed('owner_fast_wall_s',self._owner,host)
            self._timed('memory_wall_s',self._memory,host,transition=self.state=='BOUNDARY')
            if self.state=='BOUNDARY':return None  # Metadata construction allowed; before_issue still REFUSES.
            now=self.clock()
            if now-self.last_module>=self.policy.module_poll_s or self._call_count-self._module_count_at_check>=self.policy.module_poll_calls:
                self._timed('module_audit_wall_s',self._modules_check)
            io=False;started=self.clock();self.state='AUDITING'
            if now-self.last_metadata>=self.policy.metadata_poll_s:
                self._timed('metadata_audit_wall_s',self._metadata_check);io=True
            if now-self.last_canonical>=self.policy.canonical_poll_s:
                self._timed('canonical_audit_wall_s',self._canonical_check);io=True
            need(self.clock()-started<=self.policy.audit_budget_s,'Audit exceeded deadline; do not issue commands')
            self.state='RUNNING'
            if io:self._timed('owner_refresh_wall_s',self._refresh_owner,host)
            self._timed('owner_fast_wall_s',self._owner,host)
        except BaseException:
            self.state='FAILED';raise
    def before_issue(self,host):
        if self.state!='RUNNING':
            self.state='FAILED';raise GuardViolation('Physical issue forbidden during boundary/audit/failure')
        return self.check(host)
    @contextmanager
    def boundary(self,host,label):
        need(type(label)is str and label,'Explicit named no-step boundary')
        if self._depth:
            need(self.state=='BOUNDARY','Nested boundary on failed guard')
            self._depth+=1
            try:yield
            except BaseException:self.state='FAILED';raise
            finally:self._depth-=1
            return
        self.check(host);self._modules_check();stamp=self._step(host);self.state='BOUNDARY';self._depth=1
        try:
            yield
            need(self.state=='BOUNDARY'and self._step(host)==stamp,'Boundary advanced physics or lost audit authority')
            self.seal(host,label=label)
        except BaseException:self.state='FAILED';raise
        finally:self._depth=0
    def close(self):self.state='CLOSED'


def make_indexed_guard(original=None,*,enabled=False,**kwargs):
    need(type(enabled)is bool,'Explicit new-program owner opt-in')
    if not enabled:return None
    engine=IndexedIdentityGuard(original,**kwargs)
    def guard(host):return engine.check(host)
    guard.engine=engine;guard.before_issue=engine.before_issue;guard.boundary=engine.boundary
    guard.cross_tick_canonical_index=True;guard.old_per_tick_equivalent=False;guard.policy=POLICY_ID
    return guard
