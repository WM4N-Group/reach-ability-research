"""Same CLOSED-tree logical sizes + same deterministic fixture call schedule.
No content/model replay, no native call, no end-to-end simulator speed claim.
"""
from pathlib import Path
import tempfile,json,time,sys,statistics
from scoped_io import ScopeIO,StopState
from resource_watch import ResourceWatch

def fresh_size(root):
 import os,stat
 total=0;stack=[str(root)]
 while stack:
  with os.scandir(stack.pop())as entries:
   for entry in entries:
    if entry.is_dir(follow_symlinks=False):stack.append(entry.path)
    else:
     s=entry.stat(follow_symlinks=True)
     if stat.S_ISREG(s.st_mode):total+=s.st_size
 return total

def benchmark(tree,rounds=3,calls=5000,interval_s=.005,temp_root=None,baseline_factory=None):
 with tempfile.TemporaryDirectory(prefix='closed-tree-fixture-',dir=temp_root)as td:
  root=Path(td)
  for row in tree:
   p=root/row['path'];assert p.resolve().is_relative_to(root);p.parent.mkdir(parents=True,exist_ok=True)
   with p.open('xb')as f:f.truncate(row['bytes'])
  expected=sum(row['bytes']for row in tree);assert fresh_size(root)==expected;out=[]
  for k in range(rounds):
   baseline=baseline_factory()if baseline_factory else None
   scan=baseline if baseline is not None else fresh_size
   t=time.perf_counter()
   for _ in range(calls):assert scan(root)==expected
   old=time.perf_counter()-t
   if baseline is not None:baseline.close()
   t=time.perf_counter();budget=ScopeIO(root,cap_bytes=1024**3,reserve_bytes=64*1024**2);clock=[0.];token=object()
   def probe():budget.reconcile()
   guard=ResourceWatch(probe,state=budget.state,token=token,clock=lambda:clock[0]);guard.probe_once();boot=time.perf_counter()-t;hot=0.;start=time.perf_counter();last_probe=0.;periodic=0
   for i in range(calls):
    clock[0]=i*interval_s  # synthetic wall-clock call trace; NOT actual run timestamps
    if clock[0]-last_probe>=1.:
     guard.probe_once();last_probe=clock[0];periodic+=1
    t=time.perf_counter();guard();hot+=time.perf_counter()-t
   elapsed=time.perf_counter()-start
   out.append(dict(round=k,hot_calls=calls,fixture_trace_seconds=(calls-1)*interval_s,old_full_scans=calls,new_full_scans=budget.metrics['reconcile_calls']+1,periodic_probe_calls=periodic,old_scope_scan_wall_s=old,new_bootstrap_wall_s=boot,new_hot_guard_exclusive_wall_s=hot,new_reconcile_inclusive_wall_s=budget.metrics['reconcile_wall_s'],new_probe_inclusive_wall_s=guard.probe_wall_s,new_loop_wall_s=elapsed,component_ratio_old_to_new=old/(boot+elapsed)))
  return dict(schema='Data-controlled-output-policy-same-host-tree-fixture-benchmark-v1',tree_files=len(tree),logical_tree_bytes=expected,fixture_sparse_sizes_no_original_content=True,tree_size_source='closed E20 original path/stat metadata only',timing_trace='same deterministic synthetic uniform call times; not original per-call timestamps',call_interval_s=interval_s,same_tree_and_call_trace_per_arm=True,rounds=out,median_component_ratio=statistics.median(q['component_ratio_old_to_new']for q in out),no_native_or_GPU_or_training=True,not_end_to_end_5x_evidence=True,baseline_implementation='current_parallel8_frozen_helper'if baseline_factory else'serial_fixture',new_policy_not_equal_detection_latency_to_old=True)
if __name__=='__main__':
 tree=json.loads(Path(sys.argv[1]).read_bytes());print(json.dumps(benchmark(tree),ensure_ascii=False))
