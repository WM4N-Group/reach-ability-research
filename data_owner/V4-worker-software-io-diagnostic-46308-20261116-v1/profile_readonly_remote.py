"""One bounded CPU/filesystem metadata diagnostic; never import the worker or native code.
No lease, no live-authority surrogate and no closed-root writes. All output is stdout.
Independent I/O probes use only an explicitly new diagnostic directory.
"""
from pathlib import Path
import os, sys, json, hashlib, datetime, time, resource, signal, subprocess, ast, statistics
start=time.monotonic()
signal.signal(signal.SIGALRM,lambda *_: (_ for _ in ()).throw(TimeoutError('90s CPU metadata diagnostic cap')))
signal.alarm(90)
resource.setrlimit(resource.RLIMIT_CORE,(0,0))
resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,512*1024**2))
os.nice(15)
assert os.environ.get('CUDA_VISIBLE_DEVICES')==''
R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114'); B=R/'workspace'
N='V4-bounded-climb-nav-native-46308-20261116-v2'; W=B/'workers'/N
H=B/'registry/handoff_current_status_20261115.json'; A=B/'registry/V4_BOUNDED_CLIMB_NAV_AUTHORITY_20261116_v2.json'
ROOT=R/'runtime/workers/data-46308-V4-bounded-climb-nav-native-20261116-v2'
D=B/'development/V4-worker-software-io-diagnostic-46308-20261116-v1'
owner='01a1d3aa-a0d5-7de0-b886-9d92ed5f1480'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
hraw=H.read_bytes(); h=json.loads(hraw); assert h['executing_thread_id']==owner
assert all(not v['active'] for k,v in h.items() if k.startswith('active_') and isinstance(v,dict) and 'active' in v)
oldpins={str(p):sha(p) for p in [H,A,W/'worker.py',W/'protocol.json',ROOT/'result.json',ROOT/'ledger.json',ROOT/'events.jsonl']}
active=[]
for p in Path('/proc').glob('[0-9]*'):
 try: argv=[s.decode(errors='replace') for s in (p/'cmdline').read_bytes().split(b'\0') if s]
 except OSError: continue
 if any(s.startswith((str(R/'runtime')+'/',str(B/'workers')+'/')) for s in argv): active.append(int(p.name))
assert not active,active
locks=[]
# No flock acquired here: kernel /proc/locks inventory and O_NOFOLLOW inode observation only.
locktext=Path('/proc/locks').read_text()
for idx,inos in [(0,[3428729629,3428729630]),(1,[3428459217,3428459218])]:
 for kind,ino in zip(('physics','sdk'),inos):
  p=R/f'resource-locks/native-observer-{kind}-gpu{idx}.lock'; fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
  try:
   st=os.fstat(fd); assert (st.st_dev,st.st_ino)==(51,ino)==(p.stat().st_dev,p.stat().st_ino)
   held=[line for line in locktext.splitlines() if any(x.endswith(':'+str(ino)) for x in line.split())]
   assert not held,held
   locks.append(dict(path=str(p),device=51,inode=ino,proc_locks_matches=held,not_a_lease=True))
  finally:os.close(fd)
measurements={}
def sample(name,fn,n=3):
 rows=[]; value=None
 for i in range(n):
  t=time.perf_counter(); c=time.process_time(); value=fn(); rows.append(dict(wall_s=time.perf_counter()-t,cpu_s=time.process_time()-c))
 measurements[name]=dict(samples=rows,median_wall_s=statistics.median(r['wall_s'] for r in rows))
 return value
# Exact code slices, not guard invocation. Closed active=False remains unchanged and cannot authorize anything.
sample('H_read_bytes',H.read_bytes)
sample('H_json_parse_in_memory',lambda:json.loads(hraw))
sample('authority_two_JSON_reads_plus_AUTH_SHA',lambda:(json.loads(H.read_bytes()),json.loads(A.read_bytes()),sha(A)))
row=[json.loads((R/f'resource-locks/{f}').read_bytes()) for f in ('46308-gpu0-bulk-canonical-binding-20261115-v1.json','46308-canonical-binding-20261115-v1.json')]
sample('binding_SHA_read',lambda:sha(R/'resource-locks/46308-gpu0-bulk-canonical-binding-20261115-v1.json'))
fds=[]
try:
 for x in row[0]['locks']:fds.append((os.open(x['path'],os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC),Path(x['path'])))
 sample('lease_inode_check_without_flock_or_lease',lambda:[(os.fstat(fd),p.stat(),p.stat()) for fd,p in fds])
finally:
 for fd,p in fds:os.close(fd)
size=sample('exact_closed_ROOT_output_size_rglob_isfile_stat',lambda:sum(p.stat().st_size for p in ROOT.rglob('*') if p.is_file()))
sample('RSS_getrusage',lambda:resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
args=['nvidia-smi','--id=GPU-297c1146-bcec-a8ee-8437-d9603392a2e1']
gpu=sample('lease_gpu_query_subprocess',lambda:subprocess.check_output(args+['--query-gpu=index,uuid,memory.free,utilization.gpu','--format=csv,noheader,nounits'],text=True,timeout=10))
apps=sample('lease_compute_apps_query_subprocess',lambda:subprocess.check_output(args+['--query-compute-apps=pid,used_gpu_memory,gpu_uuid','--format=csv,noheader,nounits'],text=True,timeout=10))
# Probe only our new, bounded CPU diagnostic metadata file; not old journal/episode or a real writer replay.
D.mkdir(parents=True,exist_ok=False); probe=D/'independent-4096byte-fsync-probe.bin'
with probe.open('xb') as f:
 for i in range(3):
  t=time.perf_counter();c=time.process_time();f.write(b'0'*4096);f.flush();os.fsync(f.fileno())
  measurements.setdefault('independent_4KiB_flush_fsync',dict(samples=[]))['samples'].append(dict(wall_s=time.perf_counter()-t,cpu_s=time.process_time()-c))
measurements['independent_4KiB_flush_fsync']['median_wall_s']=statistics.median(x['wall_s'] for x in measurements['independent_4KiB_flush_fsync']['samples'])
# Read-only AST method/line inventory: does not compile/execute native code or import package.
paths=[W/'worker.py',W/'inputs/ainav/development/complex_dual_route_v1/scene_driver.py',W/'inputs/ainav/development/complex_v4_four_arm_v1/live_driver.py',W/'inputs/ainav/development/complex_v4_four_arm_v1/execution_entry.py',B/'workers/new-critic-cohort-46308-20261115-v1/inputs/AINav/common-source/ainav/native/loop.py']
methods=[]
for path in paths:
 text=path.read_text(); tree=ast.parse(text)
 for node in ast.walk(tree):
  if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name in ('authority','guard','check','_native_guards','_after_guard','_guard','checked_guard','guards','step_one'):
   methods.append(dict(file=str(path),file_sha256=hashlib.sha256(text.encode()).hexdigest(),method=node.name,line=node.lineno,end_line=node.end_lineno,method_sha256=hashlib.sha256(ast.get_source_segment(text,node).encode()).hexdigest(),direct_calls=[dict(line=n.lineno,expression=ast.unparse(n.func)) for n in ast.walk(node) if isinstance(n,ast.Call) and (any(s in ast.unparse(n.func) for s in ('guard','rglob','resolve','stat','authority')))]))
assert all(sha(p)==pin for p,pin in oldpins.items()),'Closed evidence or authority changed during probe'
assert not any(name.split('.')[0] in ('torch','mujoco','onnxruntime','numpy','scipy','ainav','mujoco_zyh') for name in sys.modules)
owned=int(subprocess.check_output(['du','-sx','-B1','/mnt/yuanyue/data-team'],text=True,timeout=30).split()[0]);assert owned<40*1024**3
signal.alarm(0)
print(json.dumps(dict(at=datetime.datetime.now().astimezone().isoformat(),role='BOUNDED_CPU_METADATA_SLICES_OF_EXACT_DATA_WORKER_NOT_LIVE_GUARD_OR_NATIVE_PROFILE',scope_closed=True,authority_guard_not_invoked_or_bypassed=True,CUDA_VISIBLE_DEVICES=os.environ['CUDA_VISIBLE_DEVICES'],native_model_import_constructor_forward_API_or_physics_calls=0,old_pins_unchanged=oldpins,Data_native_workers=active,canonical_inode_observations=locks,measurements=measurements,closed_output_size_bytes=size,closed_output_file_count=sum(1 for p in ROOT.rglob('*') if p.is_file()),H_bytes=len(hraw),GPU=gpu,GPU_apps=apps,own_GPU_usage_not_claimed_no_context_or_lease=True,methods=methods,wall_s=time.monotonic()-start,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,owned_bytes=owned,provider_quota_unknown=True,new_independent_probe_bytes=probe.stat().st_size,limitations=['No original per-tick profile or full native step attribution','No Torch/CUDA memory call timing','Closed-tree size measurement is not time-varying live writer size','Independent fsync sample not original per-event I/O cost','No source39 native qualification, safety weakening, budget change, or dispatch']),ensure_ascii=False,indent=2))
