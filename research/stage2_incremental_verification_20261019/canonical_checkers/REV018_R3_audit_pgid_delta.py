"""Independent DEV019 exact-delta/PGID checks. No SDK/import of caller/producer tests."""
import ast,contextlib,copy,datetime,difflib,hashlib,io,json
from pathlib import Path
from unittest import mock
OUT=Path(__file__).resolve().parent
BASE=Path('/home/yuanyue/re-nav -piper-deploy/artifacts/go2-piper/sim2sim-current-20261008-a')
OLD=BASE/'wm07-old714-firststep-baseline-v001r2';NEW=BASE/'wm07-old714-firststep-baseline-v001r3'
SHA='1fa50a30f008c00e7dde7199a86e283bf854f49e9bfe534fde6fde8295413a8a'
read=lambda p:json.loads(Path(p).read_text());h=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert h(NEW/'package-manifest.json')==SHA
assert h(OLD/'package-manifest.json')=='6ea9b36cb0f083cc8911c01e358b1586461eb332a99829d5f908e7473c7fbf6d'
m=read(NEW/'package-manifest.json');old_m=read(OLD/'package-manifest.json')
assert all(h(NEW/n)==s for n,s in m['files_sha256'].items())
old_src=(OLD/'run_source.py').read_text();new_src=(NEW/'run_source.py').read_text()
a=ast.parse(old_src);b=ast.parse(new_src)
funcs=lambda t:{x.name:x for x in t.body if isinstance(x,ast.FunctionDef)}
afn=funcs(a);bfn=funcs(b)
changed=[n for n in afn if ast.dump(afn[n],include_attributes=False)!=ast.dump(bfn[n],include_attributes=False)]
assert changed==['quiet'] and afn.keys()==bfn.keys()
clone=copy.deepcopy(b)
for i,n in enumerate(clone.body):
 if isinstance(n,ast.FunctionDef) and n.name=='quiet':clone.body[i]=copy.deepcopy(afn['quiet'])
assert ast.dump(a,include_attributes=False)==ast.dump(clone,include_attributes=False)
assert ast.dump(afn['gates'],include_attributes=False)==ast.dump(bfn['gates'],include_attributes=False)
unchanged=[n for n in old_m['files_sha256'] if n in m['files_sha256'] and old_m['files_sha256'][n]==m['files_sha256'][n]]
assert all(n in unchanged for n in ['check_sdk0env.py','binding.py','paths.json','runtime-index.json','scene.json','climb-jobs/jobs.json','climb-jobs/stage-bank.json',*[n for n in old_m['files_sha256'] if n.startswith('source/')]])
p=read(NEW/'protocol.json');op=read(OLD/'protocol.json');pd={k:{'old':op.get(k),'new':p.get(k)} for k in op.keys()|p.keys() if op.get(k)!=p.get(k)}
expected={'source_id','version','SDK0env_allowed_once','formal_remote_package','formal_remote_run','local_run_preparation','parent_executable_manifest_sha256','SDK0env_status'}
assert set(pd)==expected
assert p['argv_template']==op['argv_template'] and p['budget']==op['budget']
def need(ok,why):
 if not ok:raise ValueError(why)
def load(tree):
 ns={'need':need,'P':p,'SOURCE':p['source_id'],'best_effort':best,'snapshot':None,'time':mock.Mock()}
 exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('validate_snapshot','quiet','wait_stopped')],type_ignores=[]),'<exact runner PGID AST>','exec'),ns)
 return ns
def best(f):
 try:f()
 except Exception:pass
old=load(a);new=load(b)
def snap(rows):
 return {'collector_pid':9,'owner_marker':{'source_id':p['source_id'],'pid':100,'pgid':100},'ps':{'returncode':0,'stderr':'','stdout':'PID PGID STAT COMMAND\n1 1 Ss init\n'+'\n'.join(rows)+('\n' if rows else '')},'gpu':{'returncode':0,'stderr':'','stdout':'0, GPU-other, 1, 0\n1, '+p['CUDA_VISIBLE_DEVICES']+', 1, 0\n'},'apps':{'returncode':0,'stderr':'','stdout':''}}
results=[]
for name,row in [('noncollector_owned_group_c_worker','101 100 S /usr/bin/python3 -c "sleep"'),('owned_leader_different_group_c','100 700 S /usr/bin/python3 -c "sleep"')]:
 s=snap([row]);before=old['quiet'](s);after=new['quiet'](s)
 assert before is True and after is False
 results.append({'case':name,'r2_quiet':before,'r3_quiet':after,'finding_closed':True})
controls={'actual_collector':['9 9 S python3 -c "isaac-python inventory text"'],'owned_zombie':['101 100 Z python3 -c "defunct"'],'no_owned_rows':[],'unowned_inventory_shell':['200 200 S python3 -c "inventory harmless"']}
for name,rows in controls.items():assert new['quiet'](snap(rows)) is True
seq=[snap(['101 100 S python3 -c "sleep"']),snap(['100 700 S python3 -c "sleep"']),snap(controls['actual_collector'])]
get=mock.Mock(side_effect=seq);notify=mock.Mock(side_effect=OSError(28,'fixture notification ENOSPC'));sleep=mock.Mock()
class Broken(io.StringIO):
 def write(self,x):raise BrokenPipeError('fixture notification pipe')
with contextlib.redirect_stdout(Broken()):returned=new['wait_stopped'](get,notify,sleep)
assert returned is seq[-1] and get.call_count==3 and sleep.call_count==2 and notify.call_count==1
# Read-set equivalence is not used to relax the exact machine gate.
result={'schema':'rev018-dev019-pgid-delta-independent-v1','at':datetime.datetime.now().astimezone().isoformat(),'source_id':p['source_id'],'source_manifest_sha256':SHA,'source_members_verified':len(m['files_sha256']),'only_runner_function_changed':changed,'whole_runner_AST_otherwise_equal':True,'SDK_machine_gate_AST_unchanged':True,'unchanged_member_hashes_inherited':{n:m['files_sha256'][n] for n in unchanged},'protocol_identity_precheck_metadata_delta':pd,'configuration_argv_and_budget_unchanged':True,'counterexamples':results,'positive_controls':list(controls),'wait_sequence':{'gets':3,'sleeps':2,'notifications':1,'notification_ENOSPC_and_BrokenPipe_did_not_return_early':True,'returned_only_after_quiet_snapshot':True},'finding_status':{'REV018-PGID-01':'CLOSED_BY_INDEPENDENT_FOCUSED_CPU_DELTA'},'producer11_suite_rerun':False,'old23_or_readset_or_old_suites_reaudited':False,'SDK_started_by_verification':False,'physics_started_by_verification':False,'shared_lock_touched':False,'SDK_inheritance_gate_relaxed':False,'SDK_r3_status':'PENDING_DELIVERED_NEW_ACTUAL_SDK_ORIGINALS','final_source_acceptance':'PENDING_NEW_R3_SDK_RECEIPT_NO_PREACCEPTANCE','run_authorized':False}
(OUT/'pgid_delta_result.json').write_text(json.dumps(result,indent=2)+'\n')
(OUT/'r2-to-r3-runner.independent.diff').write_text(''.join(difflib.unified_diff(old_src.splitlines(True),new_src.splitlines(True),fromfile=str(OLD/'run_source.py'),tofile=str(NEW/'run_source.py'))))
print(json.dumps({k:v for k,v in result.items() if k not in ('unchanged_member_hashes_inherited','protocol_identity_precheck_metadata_delta')},indent=2))
