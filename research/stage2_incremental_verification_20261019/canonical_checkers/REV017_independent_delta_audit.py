"""Focused independent CPU checks. No producer suite, SDK, GPU, or shared lock.
All writes are under this review directory. Run with python3 -B.
"""
import ast,contextlib,errno,fcntl,hashlib,importlib.util,io,json,os,subprocess,sys,tempfile,traceback
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

OUT=Path(__file__).resolve().parent
SRC=Path('/home/yuanyue/re-nav -piper-deploy/artifacts/go2-piper/sim2sim-current-20261008-a/wm07-gravity-order-probe-v023r2g')
sys.dont_write_bytecode=True
sys.path.insert(0,str(SRC))
import probe_runner as r
import diagnostic_watchdog as w
SHA='fa3712e778523fe09a72275c54c5247730944ee6a9b309fa5ca702b8ac2a689e'
INV='0, gpu-zero\n1, gpu-one\n'
results=[]

def record(name,fn):
 try:
  detail=fn();results.append(dict(name=name,status='CONFIRMED' if detail.get('blocking_reproduction') else 'PASS',**detail))
 except BaseException:
  results.append(dict(name=name,status='AUDIT_ERROR',error=traceback.format_exc()))

@contextlib.contextmanager
def fixture():
 with tempfile.TemporaryDirectory(dir=OUT,prefix='cpu-fixture-') as d:yield Path(d)

class Clock:
 def __init__(self):self.t=0
 def monotonic(self):return self.t
 def sleep(self,seconds):self.t+=max(seconds,.001)

def race(still_live):
 with fixture() as root:
  clock=Clock()
  class Child:
   pid=95101
   returncode=None
   def poll(self):return self.returncode
   def wait(self,timeout):
    self.timeout=timeout
    if still_live:raise subprocess.TimeoutExpired('synthetic CPU child',timeout)
    self.returncode=-15;return self.returncode
  child=Child()
  # Child returncode is deliberately stale after cleanup; final inventory is fresh.
  owned={95101:('S',os.getpid(),95101,1)} if still_live else {}
  with mock.patch.object(w,'time',clock),mock.patch.object(w,'_subreaper'), \
       mock.patch.object(w.subprocess,'Popen',return_value=child), \
       mock.patch.object(w,'_owned_live',return_value=owned), \
       mock.patch.object(w,'_stop_owned',return_value=(False,[])):
   report=w.run_command(['never-executed'],root,cap_s=.02,term_grace_s=.01,kill_confirm_s=.01)
  assert report['decision']==('UNRESOLVED_CHILDREN' if still_live else 'TIMEOUT_TERMINATED'),report
  assert report['child_reaped'] is not still_live
  assert bool(report['survivors']) is still_live
  return dict(decision=report['decision'],child_reaped=report['child_reaped'],survivors=report['survivors'],wait_timeout_s=child.timeout,synthetic_only=True)

def stale_failure():
 with fixture() as root:
  run=root/'run';run.mkdir()
  old={'pgid':200,'decision':'UNRESOLVED_CHILDREN','survivors':{'201':{'state':'poll_running_or_unknown'}}}
  (run/'watchdog-result.json').write_text(json.dumps(old))
  (run/'unresolved.json').write_text('{"reason":"PHYSICAL_DEADLINE_UNCONFIRMED"}\n')
  before={n:r.digest(run/n) for n in ('watchdog-result.json','unresolved.json')}
  stopped,e=r.classify_fresh_stop(old,'200','', '',INV)
  assert stopped and e['failure_only'] and not e['watchdog_stop_confirmed']
  with mock.patch.object(r,'LOCAL_RUN',run),mock.patch.object(r,'RUNTIME',root), \
       mock.patch.object(r,'copy_optional_remote',return_value=(False,'synthetic absence')):
   rc=r.close_failed_source(SHA,e,124,None,'stale immutable unknown, fresh quiescence',179,0,2400)
  c=json.loads((run/'failure-closure.json').read_text());ledger=json.loads((root/'control_dev_physical_runs.jsonl').read_text())
  assert rc==2 and c['status']=='FAILED' and ledger['event']=='closed'
  assert c['progress']['environment_created']=='unknown' and c['progress']['completed_ticks_observed']=='unknown'
  assert c['full_task_success'] is False and c['no_retry'] is True
  assert before=={n:r.digest(run/n) for n in before}
  return dict(status_observed=c['status'],immutable_originals_preserved=True,missing_progress_unknown=True,ledger_closed=True)

def notification_failure(kind):
 with fixture() as root:
  lock=root/'owner.lock';lock.touch()
  error=OSError(errno.ENOSPC,'injected diagnostic record filesystem full') if kind=='record' else BrokenPipeError('injected stdout broken')
  caught=None
  with contextlib.ExitStack() as stack:
   stack.enter_context(mock.patch.object(r,'ssh',side_effect=subprocess.TimeoutExpired('read-only status',.1)))
   stack.enter_context(mock.patch.object(r,'time',SimpleNamespace(monotonic=lambda:100.,sleep=lambda _:None)))
   if kind=='record':stack.enter_context(mock.patch.object(r,'record_unresolved',side_effect=error))
   else:stack.enter_context(mock.patch('builtins.print',side_effect=error))
   try:
    # Same with/flock lifetime as local_run; only a disposable private lock.
    with lock.open('r') as stream:
     fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
     r.wait_stopped(0 if kind=='record' else 1000,2000,root)
   except Exception as exc:caught=exc
  with lock.open('r') as stream:
   fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB);released=True
  assert caught is error and released
  return dict(blocking_reproduction=True,exception=repr(caught),transport_unknown=True,temporary_owner_lock_released=True,shared_owner_lock_touched=False,branch=kind)

class StopAudit(BaseException):pass

def persistent_unknown():
 with fixture() as root:
  stale={'pgid':200,'decision':'UNRESOLVED_CHILDREN','survivors':{'201':{'state':'S'}}}
  live='201 1 301 S detached-child\n'
  output=live+'\n--GPU--\n\n--UUID--\n'+INV+'\n--PGID--\n200\n--WATCHDOG--\n'+json.dumps(stale)
  sleeps=[]
  def sleep(_):sleeps.append(True);raise StopAudit()
  with mock.patch.object(r,'ssh',return_value=SimpleNamespace(stdout=output)), \
       mock.patch.object(r,'time',SimpleNamespace(monotonic=lambda:100.,sleep=sleep)),contextlib.redirect_stdout(io.StringIO()):
   try:r.wait_stopped(0,50,root)
   except StopAudit:pass
   else:raise AssertionError('returned on a live detached recorded survivor')
  assert sleeps and (root/'unresolved.json').is_file() and not (root/'failure-closure.json').exists()
  for malformed in ({'inventory_unknown':True},{'201':{'state':'S'}}):
   # The live recorded PID is rejected by classification; unenumerated identities raise.
   try:stopped,_=r.classify_fresh_stop({**stale,'survivors':malformed},'200',live,'',INV)
   except ValueError:stopped=False
   assert not stopped
  return dict(live_detached_survivor_not_closed=True,unenumerated_survivor_not_closed=True,actionable_record_present=True)

def component_failure(component):
 with fixture() as root:
  report={'pgid':200,'decision':'CLEAN_EXIT','survivors':{}}
  calls=[]
  shell_returncodes=[]
  # Shadow every command in the compound read-only SSH command. Nothing real is inspected.
  # Simulate a failure of one mandatory inventory command, followed by successful cats.
  definitions='''ps() { %s; }; nvidia-smi() { case "$*" in *query-compute-apps*) %s ;; *) printf '0, gpu-zero\\n1, gpu-one\\n';; esac; }; cat() { case "$1" in *process-group.pid) printf '200\\n';; *watchdog-result.json) printf '%%s\\n' '%s';; *) return 2;; esac; };\n''' % (
    'return 7' if component=='ps' else "printf '201 1 200 S detached-child\\n'" if component=='gpu' else ':',
    'return 9' if component=='gpu' else ':',json.dumps(report))
  # For GPU-query failure keep ps free of source/group: a detached GPU process cannot be ruled out.
  if component=='gpu':definitions=definitions.replace("printf '201 1 200 S detached-child\\n'",':')
  def fake_ssh(command,**kwargs):
   p=subprocess.run(['/bin/bash','-c',definitions+command],capture_output=True,text=True,check=True)
   calls.append(command);shell_returncodes.append(p.returncode);return p
  with mock.patch.object(r,'ssh',side_effect=fake_ssh):
   evidence=r.wait_stopped(1000,2000,root)
  assert calls and shell_returncodes==[0] and not evidence['failure_only']
  return dict(blocking_reproduction=True,failed_inventory=component,compound_shell_exit_status=shell_returncodes[0],returned_stop_confirmed=evidence['watchdog_stop_confirmed'],failure_only=evidence['failure_only'],incomplete_inventory_was_accepted=True)

def flush_evidence():
 with fixture() as root:
  p=root/'progress.jsonl';calls=[];real=r.os.fsync
  def fsync(fd):calls.append(fd);return real(fd)
  with mock.patch.object(r.os,'fsync',side_effect=fsync):
   for event,fields in [('sdk_import_enter',{}),('app_launcher_enter',{}),('app_launcher_returned_app_ready',{}),('gym_make_returned',{}),('physics_substep_return',{'physics_substep':1}),('tick_enter',{'tick':0})]:r.append_progress(p,event,**fields)
  # Interrupted final write does not erase completed fsynced observations.
  with p.open('a') as f:f.write('{"event":')
  s=r.progress_summary(p)
  assert len(calls)==6 and s['partial_tail'] and s['app_ready_observed'] and s['environment_created'] is True
  assert s['physics_substeps_observed']==1 and s['completed_ticks_observed']==0
  assert r.progress_summary(root/'absent')['completed_ticks_observed']=='unknown'
  return dict(fsync_calls=len(calls),partial_tail_preserves_prior_observations=True,returned_substep_not_promoted_to_tick=True,missing_file_stays_unknown=True)

def static_and_hash():
 assert r.verify_source()==SHA
 p=r.PROTOCOL
 assert [p[k] for k in ('diagnostic_outer_wall_s','watchdog_cap_s','watchdog_term_grace_s','watchdog_kill_confirm_s','source_core_wall_s','source_outer_wall_s','maximum_environment_ticks','maximum_physics_substeps','maximum_environment_starts','maximum_retries')]==[180,177,1,1,2340,2400,8,32,1,0]
 tree=ast.parse((SRC/'probe_runner.py').read_text())
 funcs={n.name:n for n in tree.body if isinstance(n,ast.FunctionDef)}
 remote=ast.get_source_segment((SRC/'probe_runner.py').read_text(),funcs['remote_execute'])
 assert remote.index('AppLauncher(headless=True, device="cuda:0")')<remote.index('from probe_native import run')<remote.index('result = run(')
 native=(SRC/'probe_native.py').read_text();assert 'stream.flush()\n                os.fsync(stream.fileno())' in native
 before=SRC.parent/'wm07-gravity-order-probe-v023r2f'
 unchanged=[n for n in ('probe_math.py','audit_result.py','cache_boundary.py','test_probe_math.py','test_audit_result.py','test_cache_boundary.py') if r.digest(SRC/n)==r.digest(before/n)]
 assert len(unchanged)==6
 return dict(source_manifest_match=True,unchanged_inherited_members=unchanged,constants_preserved=True,app_before_native_import=True,raw_tick_flush_fsync_present=True,default_inspect=r.inspect())

record('manifest_budget_static_reachability',static_and_hash)
record('TERM_cleanup_false_then_fresh_empty_reap',lambda:race(False))
record('TERM_cleanup_false_and_fresh_survivor_keeps_UNKNOWN',lambda:race(True))
record('immutable_UNKNOWN_fresh_stop_failed_closure',stale_failure)
record('normal_unknown_path_retains_wait',persistent_unknown)
record('fsync_partial_progress_boundaries',flush_evidence)
record('unknown_record_IO_failure_unwinds_owner',lambda:notification_failure('record'))
record('unknown_stdout_failure_unwinds_owner',lambda:notification_failure('stdout'))
record('failed_ps_hidden_by_final_cat',lambda:component_failure('ps'))
record('failed_GPU_apps_query_hidden_by_final_cat',lambda:component_failure('gpu'))
summary={'schema':'rev017-independent-increment-cpu-audit-v1','producer_tests_imported':False,'sdk_started':False,'physics_started':False,'shared_lock_touched':False,'source_modified':False,'cases':results,'passed':sum(x['status']=='PASS' for x in results),'confirmed_blocking_reproductions':sum(x['status']=='CONFIRMED' for x in results),'audit_errors':sum(x['status']=='AUDIT_ERROR' for x in results)}
(OUT/'independent_delta_result.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
raise SystemExit(1 if summary['audit_errors'] else 0)
