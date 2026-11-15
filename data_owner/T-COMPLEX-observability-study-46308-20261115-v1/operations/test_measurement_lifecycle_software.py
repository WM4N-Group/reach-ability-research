"""New Data measurement lifecycle checks ONLY; no source fixture/native rerun."""
from pathlib import Path
import ast,json,hashlib,sys,types,importlib.util,tempfile,time
B=Path('/home/yuanyue/main/work/data-team');W=B/'workers/T-COMPLEX-observability-study-46308-20261115-v1';M=Path(__file__).resolve().parent
forbidden=[]
def fence(event,args):
 if event=='import'and str(args[0]).split('.')[0]in ('numpy','torch','mujoco','onnxruntime'):
  forbidden.append(str(args[0]));raise RuntimeError('No native/numeric imports in Data lifecycle check')
 if event in ('socket.connect','subprocess.Popen'):
  forbidden.append(event);raise RuntimeError('No child/network')
sys.addaudithook(fence)
p=json.loads((W/'protocol.json').read_bytes());s=(W/'observation_worker.py').read_text();tree=ast.parse(s)
loops=[ast.unparse(n.test)for n in ast.walk(tree)if isinstance(n,ast.While)]
assert loops==['not planner.motion_complete'] and 'while not host.complete'not in s
assert 'make_public_planner'not in s and 'purpose=QUALIFICATION_PURPOSE'in s
assert "status='OBSERVATION_STUDY_COMPLETE_NOT_TASK_SUCCESS',task_success=False"in s
assert p['purpose']=='OBSERVABILITY_QUALIFICATION_ONLY'and p['order']==['OBS']and not p['training_allowed']and not p['fit_or_critic_model_input']
basis=p['cost_basis'];assert p['scope_caps']['wall_s']>1.2*basis['conservative_observed_ratio_wall_per_task_sim_s']*basis['max_task_sim_from_actual_capture_and_two_original_NAV_budgets']+p['zero_wall_cap_s']
assert p['task_sim_cap_s']>basis['max_task_sim_from_actual_capture_and_two_original_NAV_budgets'] and p['scope_caps']['sim_s']>p['task_sim_cap_s']+2*10.5
pins=json.loads((W/'inputs/SOURCE_FILES_SHA256.json').read_bytes());assert all(hashlib.sha256((W/'inputs/scene'/n).read_bytes()).hexdigest()==pin for n,pin in pins.items())
# Import ONLY the new Data stdlib ledger with explicit SOFTWARE provenance.
cfg=types.ModuleType('observation_config');cfg.R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114');cfg.B=cfg.R/'workspace';cfg.M=cfg.B/'manifests'/W.name;cfg.PROTOCOL=p;cfg.SCOPES={'OBS':p['arms']['OBS']['scope_id']};cfg.ARM='OBS';sys.modules[cfg.__name__]=cfg
spec=importlib.util.spec_from_file_location('Data_observation_ledger_software_only',W/'support.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
with tempfile.TemporaryDirectory(prefix='data-observation-ledger-SOFTWARE-')as d:
 root=Path(d);ledger=mod.Ledger(root,program_sha='SOFTWARE_ONLY',auth_sha='SOFTWARE_ONLY',provenance='EXPLICIT_SOFTWARE_TEST');start=time.monotonic();ledger.claim('zero',start);ledger.close('zero','OWN_ZERO_PASS',sim_s=0.,wall_s=.01,report_sha='SOFTWARE_ONLY');ledger.claim('main',start);ledger.close('main','OBSERVATION_STUDY_COMPLETE_NOT_TASK_SUCCESS',sim_s=.01,wall_s=.02,report_sha='SOFTWARE_ONLY');assert not ledger.read()['stopped']
 try:ledger.claim('main',start)
 except mod.Stop:pass
 else:raise AssertionError('Duplicate main must refuse')
assert not forbidden
v=dict(passed=True,role='NEW_DATA_MEASUREMENT_LIFECYCLE_SOFTWARE_ONLY_NOT_NATIVE_OR_RESEARCH',measurement_termination_not_task=True,purpose_and_no_fit_flags_checked=True,source26_exact_hashes_unchanged=True,new_pre_run_cap_basis_consistent=True,software_ledger_accepts_measurement_not_task_status_and_refuses_duplicate_main=True,no_world_Actor_Renderer_numeric_import_or_network=True,forbidden=forbidden,new_physical_calls=0)
with(M/'measurement-lifecycle-software-result.json').open('x')as f:json.dump(v,f,indent=2);f.write('\n')
print(json.dumps(v,indent=2))
