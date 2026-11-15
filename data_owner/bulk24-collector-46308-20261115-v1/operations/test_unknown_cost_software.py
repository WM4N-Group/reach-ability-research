"""New Data ledger UNKNOWN regression only; no Actor/native/GPU fixture calls."""
from pathlib import Path
import sys,types,importlib.util,tempfile,os,json,time
M=Path(__file__).resolve().parent;W=M.parents[1]/'workers'/M.name
p=types.ModuleType('prepare_prefix');p.IDS=('EXPLICIT_SOFTWARE_ONLY',);p.SCOPES={p.IDS[0]:'never-a-native-root'};p.SDK_ROOT=Path('/software-only');sys.modules[p.__name__]=p;adapter=types.ModuleType('per_gpu_lease');adapter.PerGpuLease=type('FakeNoInstancePerGpuLease',(),{});adapter.ResourceStop=type('ExplicitSoftwareResourceStop',(RuntimeError,),{});sys.modules[adapter.__name__]=adapter;os.environ['DATA_PREFIX_CONDITION']=p.IDS[0]
spec=importlib.util.spec_from_file_location('software_only_bulk24_ledger',W/'support.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
with tempfile.TemporaryDirectory(prefix='bulk24-UNKNOWN-EXPLICIT-SOFTWARE-')as d:
 l=mod.Ledger(Path(d),program_sha='SOFTWARE',auth_sha='SOFTWARE',provenance='EXPLICIT_SOFTWARE_TEST');l.claim('zero',time.monotonic());l.observe('zero',sim_s=0.,wall_s=.01);l.close('zero','FAILED_NO_RETRY',sim_s=None,wall_s=.02,report_sha='SOFTWARE',usage_known=False);v=l.read();assert v['rows'][0]['sim_s']is None and not v['rows'][0]['usage_known']and v['stopped']
 try:l.claim('zero',time.monotonic())
 except mod.Stop:pass
 else:raise AssertionError('Unknown failed row cannot resume')
result=dict(passed=True,role='EXPLICIT_SOFTWARE_NEW_LEDGER_UNKNOWN_TAIL_REGRESSION_NOT_NATIVE_OR_RESEARCH',unknown_final_sim_None_not_zero=True,failed_unknown_phase_cannot_resume=True,no_world_Actor_GPU_or_native_scope=True)
with(M/'unknown-cost-software-result.json').open('x')as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps(result))
