"""Independent focused executable joints; no producer suite or SDK import."""
import ast,contextlib,copy,hashlib,io,json,os,subprocess,sys,tempfile,traceback
from pathlib import Path
from types import SimpleNamespace as NS
from unittest import mock
OUT=Path(__file__).resolve().parent
SRC=Path('/home/yuanyue/re-nav -piper-deploy/artifacts/go2-piper/sim2sim-current-20261008-a/wm07-old714-firststep-baseline-v001r2')
SHA='6ea9b36cb0f083cc8911c01e358b1586461eb332a99829d5f908e7473c7fbf6d'
sys.dont_write_bytecode=True;sys.path.insert(0,str(SRC))
import binding as b
import run_source as r
cases=[]
def case(name,fn):
 try:cases.append({'name':name,'status':'CONFIRMED_BLOCKER' if (v:=fn()).get('blocking_reproduction') else 'PASS',**v})
 except BaseException:cases.append({'name':name,'status':'AUDIT_ERROR','error':traceback.format_exc()})

def inventory(rows='',marker=True):
 d={'collector_pid':9,'ps':{'returncode':0,'stdout':'PID PGID STAT COMMAND\n1 1 Ss init\n'+rows,'stderr':''},'gpu':{'returncode':0,'stdout':'0, GPU-other, 1, 0\n1, '+r.P['CUDA_VISIBLE_DEVICES']+', 1, 0\n','stderr':''},'apps':{'returncode':0,'stdout':'','stderr':''}}
 if marker:d['owner_marker']={'source_id':r.SOURCE,'pid':100,'pgid':100}
 return d

def manifest_layout():
 m=b.read(SRC/'package-manifest.json');assert b.H(SRC/'package-manifest.json')==SHA
 assert all(b.H(SRC/n)==h for n,h in m['files_sha256'].items())
 prior=json.loads((OUT.parent/'preparation_evidence.json').read_text());pins=prior['original_authority_derived_pins']
 inherited={'source/run_piper_integrated_course_v2.py':'caller','scene.json':'scene','climb-jobs/jobs.json':'jobs','climb-jobs/stage-bank.json':'stage_bank',**{'source/'+n:n for n in ('entry_pose_planner.py','four_support_body.py','loaded_entry_hold.py','piper_integrated_scene_v2.py')}}
 for dest,old in inherited.items():assert m['files_sha256'][dest]==pins[old]['sha256']
 idx=b.read(SRC/'runtime-index.json');parent=SRC.parent/'wm07-old714-firststep-baseline-preparation-a/runtime-snapshot-index.json'
 old_idx=b.read(parent);assert {x['relative']:x['sha256'] for x in idx['files']}=={x['relative']:x['sha256'] for x in old_idx['files']}
 paths=b.read(SRC/'paths.json');assert (SRC/'climb-jobs/train').is_symlink() and (SRC/'climb-jobs/train').resolve()==Path(paths['local_iy_train']).resolve()
 blob=subprocess.run(['git','-C','/home/yuanyue/re-nav/GO2-PIPER','cat-file','blob','714b8e6d071ee58c5fe7f22dcf2756aea447e5af:scripts/piper_world_model/causal_bridge_scene.py'],check=True,capture_output=True).stdout
 assert hashlib.sha256(blob).hexdigest()==m['files_sha256']['source/causal_bridge_scene.py']
 for n in m['files_sha256']:
  if n.endswith('.py'):ast.parse((SRC/n).read_text())
 args=b.argv('/not-executed-output',True)
 assert args[args.index('--device')+1]=='cuda:0' and '--stop-after-step' in args
 assert args[args.index('--nav-actor')+1]==paths['actors']['nav']['remote']
 return {'members':len(m['files_sha256']),'inherited_copy_hashes_matched':len(inherited),'old23_matrix_rerun':False,'runtime_index_membership_114_inherited':True,'adjacent_helpers_and_Git714_transitive_helper':True,'local_iy_symlink':str((SRC/'climb-jobs/train').resolve()),'remote_argv_mapping':True}

def collector_status():
 calls=[]
 def run(cmd,**kw):
  calls.append(cmd)
  if cmd[0]=='ps':return NS(returncode=0,stdout='PID PGID STAT COMMAND\n1 1 Ss init\n',stderr='')
  if '--query-compute-apps=pid,gpu_uuid' in cmd:return NS(returncode=9,stdout='',stderr='')
  return NS(returncode=0,stdout=inventory()['gpu']['stdout'],stderr='')
 stream=io.StringIO()
 with mock.patch.object(subprocess,'run',side_effect=run),mock.patch.object(sys,'argv',['collector']),contextlib.redirect_stdout(stream):exec(r.SNAPSHOT_CODE,{})
 s=json.loads(stream.getvalue());assert len(calls)==3 and s['apps']['returncode']==9
 try:r.quiet(s)
 except ValueError as ex:assert 'Mandatory inventory failed: apps' in str(ex)
 else:raise AssertionError('failed collector component was accepted')
 return {'actual_collector_code_executed_with_CPU_command_stubs':True,'three_separate_calls':True,'failed_apps_status_preserved_and_rejected':True}

def owned_python_c():
 regular=inventory('101 100 S /usr/bin/python3 worker.py\n');assert r.quiet(regular) is False
 hidden=inventory('101 100 S /usr/bin/python3 -c "import time; time.sleep(999)"\n')
 assert r.quiet(hidden) is True
 leader=inventory('100 100 S /usr/bin/python3 -c "import time; time.sleep(999)"\n')
 assert r.quiet(leader) is True
 # The skip is command-text based, not confined to collector_pid=9.
 return {'blocking_reproduction':True,'owner_pgid':100,'live_descendant_pid':101,'collector_pid':9,'ordinary_owned_child_quiet':False,'python_c_owned_child_quiet':True,'python_c_owned_leader_quiet':True,'GPU_apps_successfully_empty':True,'source_line':52}

def wait_does_not_hold_on_python_c():
 bad=inventory('101 100 S /usr/bin/python3 -c "import time; time.sleep(999)"\n')
 sleep=mock.Mock();notify=mock.Mock()
 result=r.wait_stopped(get=lambda:bad,notify=notify,sleep=sleep)
 assert result==bad and not sleep.called and not notify.called
 return {'blocking_reproduction':True,'actual_wait_stopped_returned_before_live_owned_group_stopped':True,'notification_calls':notify.call_count,'sleep_calls':sleep.call_count,'shared_lock_touched':False}

def budget_and_guard():
 source=(SRC/'run_source.py').read_text();t=ast.parse(source)
 local=next(n for n in t.body if isinstance(n,ast.FunctionDef) and n.name=='local_run')
 assert ast.unparse(local.body[0]).startswith('local_origin = time.monotonic()')
 # Old origin translated conservatively; clock query round trip cannot add source budget.
 local_elapsed=12.;remote_observed=10000.;origin=remote_observed-local_elapsed
 assert remote_observed-origin==local_elapsed
 assert 'remaining=origin+2340-time.monotonic()-6' in source
 assert "['timeout','--signal=TERM','--kill-after=2',str(remaining)" in source
 assert 'remote_origin=observed-(time.monotonic()-local_origin)' in source
 assert all(r.P['budget'][k]==v for k,v in {'total_sim_s':468,'core_wall_s':2340,'reporting_reserve_s':60,'outer_wall_s':2400,'maximum_starts':1,'retries':0}.items())
 guard=(SRC/'check_sdk0env.py').read_text()
 assert "envs_module=importlib.import_module('isaaclab.envs')" in guard and "sim_module=importlib.import_module('isaaclab.sim')" in guard
 assert 'cfg.push_distance==.6' in guard and "scene['step_push_goal_dx_m']==.5" in guard
 old=(SRC/'source/run_piper_integrated_course_v2.py').read_text();assert 'config.push_distance = 0.60' in old
 return {'local_origin_before_gates':True,'remote_origin_accounts_for_preparation':True,'timeout_and_cleanup_reserve_present':True,'budgets_preserved':True,'guard_direct_submodule_alias_static':True,'original_cfg_point60_and_event_point50_preserved':True,'dynamic_SDK_success_not_asserted':True}

def reduction(fault):
 with tempfile.TemporaryDirectory(dir=OUT,prefix='reducer-fixture-') as folder:
  remote=Path(folder);(remote/'attempt').mkdir()
  raw={'first_step_platform_reached':True,'failure':fault,'success':False,'integrated_task_success':False}
  (remote/'attempt/report.json').write_text(json.dumps(raw));original=b.H(remote/'attempt/report.json')
  sig=[]
  child=NS(pid=501,wait=lambda **kw:0)
  realH=r.H
  with mock.patch.object(r,'ROOT',Path(r.P['formal_remote_package'])),mock.patch.object(r,'REMOTE',remote),mock.patch.object(r,'gates'),mock.patch.object(r,'new',wraps=r.new), \
       mock.patch.object(r,'H',side_effect=lambda p:SHA if Path(p).name=='package-manifest.json' else realH(p)), \
       mock.patch.object(r.subprocess,'Popen',return_value=child) as popen,mock.patch.object(r.os,'killpg',side_effect=lambda pid,s:sig.append([pid,int(s)])), \
       mock.patch.object(r,'time',NS(monotonic=lambda:1100.,sleep=lambda x:None)):
   rc=r.remote_execute(1000.)
  term=json.loads((remote/'terminal.json').read_text())
  assert term['baseline_first_step_event_achieved']==(fault=='first_step_only')
  assert term['current_goal_completed'] is False and term['integrated_task_success'] is False
  assert b.H(remote/'attempt/report.json')==original
  assert popen.call_args.kwargs['start_new_session'] is True
  assert popen.call_args.kwargs['env']['CUDA_VISIBLE_DEVICES']==r.P['CUDA_VISIBLE_DEVICES']
  assert '--device' in popen.call_args.args[0] and popen.call_args.args[0][-1]=='cuda:0'
  assert sig==[[501,15],[501,9]]
  return {'raw_failure':fault,'baseline_first_step_event_achieved':term['baseline_first_step_event_achieved'],'raw_bytes_unchanged':True,'current_goal_completed':False,'spawn_mocked_no_SDK':True,'PGID_TERM_KILL_mocked':True,'returncode':rc}

case('manifest_layout_inherited_copies_and_transitive_helper',manifest_layout)
case('actual_snapshot_collector_explicit_component_status',collector_status)
case('owned_PGID_python_c_exemption_reproduction',owned_python_c)
case('wait_returns_on_live_owned_python_c',wait_does_not_hold_on_python_c)
case('wall_origin_budget_and_guard_alias_static',budget_and_guard)
case('baseline_raw_stop_reduction',lambda:reduction('first_step_only'))
case('baseline_original_fault_not_relabelled',lambda:reduction('original_fault'))
result={'schema':'rev018-v001r2-executable-delta-cpu-v1','source_manifest_sha256':SHA,'cases':cases,'passed':sum(c['status']=='PASS' for c in cases),'confirmed_counterexamples':sum(c['status']=='CONFIRMED_BLOCKER' for c in cases),'audit_errors':sum(c['status']=='AUDIT_ERROR' for c in cases),'SDK_started':False,'physics_started':False,'producer_suite_rerun':False,'old23_pin_matrix_rerun':False,'shared_lock_touched':False}
(OUT/'independent_cpu_result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
raise SystemExit(1 if result['audit_errors'] else 0)
