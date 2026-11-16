"""Bounded SAME module/file corpus + SAME synthetic call timelines, no native.

Only guard wall is compared. fake owner/world, NOT an end-to-end speedup/lease
qualification. Cold inventory SHA costs are separate, and audit delays differ.
"""
from pathlib import Path
from types import SimpleNamespace as NS
import ast,hashlib,importlib.util,json,os,statistics,sys,time
start=time.perf_counter();blocked=[]
def fence(event,args):
 if event=='import'and str(args[0]).split('.')[0]in('mujoco','onnxruntime'):
  blocked.append(str(args[0]));raise RuntimeError('CPU loaded-file corpus only, no native')
 if event in('socket.connect','socket.bind','socket.getaddrinfo','subprocess.Popen'):
  blocked.append(event);raise RuntimeError('No network/child')
sys.addaudithook(fence)
import torch,numpy,scipy.optimize,osqp,PIL.Image
torch.set_num_threads(2)
root=Path(sys.argv[1]);old_dir=root/'development/complex_e_skill20_arrival_v3';sys.path[:0]=[str(Path(__file__).resolve().parent),str(old_dir)]
import indexed_guard as new
spec=importlib.util.spec_from_file_location('explicit_old_batch32_guard',old_dir/'parallel_alias_guard.py');old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
p=root/'development/complex_dual_route_v1/scene_driver.py';text=p.read_text();tree=ast.parse(text);cls=next(n for n in tree.body if isinstance(n,ast.ClassDef)and n.name=='ComplexSceneDriver');fn=next(n for n in cls.body if isinstance(n,ast.FunctionDef)and n.name=='_native_guards')
modules=dict(sys.modules);cb=object();modules['EXPLICIT_SOFTWARE_CRITICAL_ALIAS']=NS(__file__=str(p),CB=cb);registry=NS(modules=modules)
clock={'now':100.,'checked':100.};owner_full_calls=0;refresh_calls=0
# Synthetic cached ownership is explicitly not a resource/lease proof.
def full():
 global owner_full_calls
 owner_full_calls+=1;clock['checked']=clock['now']
def refresh(host):
 global refresh_calls
 refresh_calls+=1;clock['checked']=clock['now']
def fast(host):return new.OwnerStamp('EXPLICIT_FAKE_OWNER',clock['checked'],clock['checked']+2.,True)
sim=NS(model=object(),data=NS(time=0.),queue=[],controller=object(),box_push_target=object());host=NS(r=NS(sim=sim,step_count=0),owner_guard=full,_stow_allowed={p},_stow_installed={str(p):cb},_stow_callback_name='CB');host._world=(sim,sim.model,sim.data,sim.queue,sim.controller,sim.box_push_target)
ns=dict(sys=registry,Path=Path,need=new.need);exec(compile(ast.Module(body=[fn],type_ignores=[]),str(p),'exec'),ns);original=ns['_native_guards']
baseline=old.make_parallel_guard(original,enabled=True);baseline.engine._ensure_pool()
# Thread machinery is warm before sealing the SAME immutable module dictionary.
paths=new.module_paths(registry);missing=[p for p in paths if not Path(p).exists()]
t=time.perf_counter();inventory=new.FrozenFiles.measure(paths,roots=['/'],allow_missing=missing);inventory_wall=time.perf_counter()-t
corpus_digest=new.digest({k:dict(sha256=v.sha256,signature=v.signature)for k,v in inventory.records.items()})
traces={
 'steady_16_preissue_calls':tuple(i*.005 for i in range(16)),
 # Deliberately sparse scripted wall timeline exercises all production tiers.
 # These are NOT claims about native physics or captured step latencies.
 'bounded_periodic_audits_12_calls':(0.,.25,.5,1.,5.,6.,10.,20.,40.,59.,60.,61.),
}
rows=[];cold=[]
def tokens(host):return dict(session=None,target=None,goal='FAKE_GOAL',config_epoch='FAKE_CONFIG')
def run_old(timeline):
 before=dict(baseline.engine.metrics);owner_before=owner_full_calls;t=time.perf_counter();latencies=[]
 for stamp in timeline:
  clock['now']=100+stamp;clock['checked']=clock['now'];a=time.perf_counter();baseline(host);latencies.append(time.perf_counter()-a)
 elapsed=time.perf_counter()-t
 return dict(seconds=elapsed,latency_s=latencies,owner_full_calls=owner_full_calls-owner_before,
  metrics={k:baseline.engine.metrics[k]-before[k]for k in before})
def run_new(timeline):
 clock['now']=clock['checked']=100.;g=new.IndexedIdentityGuard(original,files=inventory,owner_fast=fast,
  owner_refresh=refresh,tokens=tokens,clock=lambda:clock['now'])
 try:
  a=time.perf_counter();receipt=g.seal(host);cold.append(dict(seal_wall_s=time.perf_counter()-a,receipt=receipt))
  before=dict(g.metrics);owner_before=owner_full_calls;refresh_before=refresh_calls;t=time.perf_counter();latencies=[]
  for stamp in timeline:
   clock['now']=100+stamp;clock['checked']=clock['now'];a=time.perf_counter();g.before_issue(host);latencies.append(time.perf_counter()-a)
  elapsed=time.perf_counter()-t
  return dict(seconds=elapsed,latency_s=latencies,owner_full_calls=owner_full_calls-owner_before,owner_refresh_calls=refresh_calls-refresh_before,
   metrics={k:g.metrics[k]-before[k]for k in before})
 finally:g.close()
try:
 for round_no in range(2):
  for trace,timeline in traces.items():
   pair={}
   for variant in (('old','indexed')if round_no==0 else ('indexed','old')):
    pair[variant]=run_old(timeline)if variant=='old'else run_new(timeline)
   rows.append(dict(round=round_no,trace=trace,calls=len(timeline),logical_wall_span_s=timeline[-1]-timeline[0],
     results=pair,old_over_new_guard_only=pair['old']['seconds']/pair['indexed']['seconds']))
finally:baseline.engine.close()
assert not blocked
summary={}
for name,timeline in traces.items():
 selected=[r for r in rows if r['trace']==name];old_s=statistics.median(r['results']['old']['seconds']for r in selected);new_s=statistics.median(r['results']['indexed']['seconds']for r in selected)
 summary[name]=dict(old_median_s=old_s,new_median_s=new_s,guard_only_ratio=old_s/new_s,not_same_detection_latency=True)
print(json.dumps(dict(role='SAME_CPU_LOADED_MODULE_CORPUS_GUARD_ONLY_BENCHMARK_NOT_NATIVE_5X_CLAIM',
 module_entries=len(modules),raw_module_path_occurrences=sum(getattr(m,'__file__',None)is not None for m in modules.values()),
 unique_raw_paths=len(paths),unique_hashed_files=len(inventory.records),corpus_digest=corpus_digest,inventory_sha256=inventory.sha256,
 initial_SHA_snapshot_wall_s=inventory_wall,total_file_bytes=sum(v.signature[3]for v in inventory.records.values()),cold_seal_costs=cold,
 traces={k:list(v)for k,v in traces.items()},paired_rows=rows,summary=summary,
 policy=new.POLICY_ID,delays_s=dict(module_max=.25,file_metadata_max=5.,canonical_max=60.,plus_audit_budget=5.),
 non_security_bootstrap_roots_for_software_benchmark_only=['/'],readonly_enforcement_proven=False,
 original_dynamic_safety_not_removed_but_not_run_in_this_CPU_fixture=True,actual_Runtime_Actor_physics_API_GPU_calls=0,
 forbidden_attempts=blocked,total_benchmark_process_wall_s=time.perf_counter()-start),indent=2))
