"""Selected code/small custody metadata only; no native freeze or H mutation."""
from pathlib import Path
import os,json,hashlib,datetime,subprocess,base64,shlex,ast
B=Path('/home/yuanyue/main/work/data-team');M=Path(__file__).resolve().parent;K=B/'manifests/bulk24-collector-46308-20261115-v1';G=Path('/home/yuanyue/main/code/reach-ability-research');sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();logs=[]
def git(*args):
 r=subprocess.run(['git',*args],cwd=G,capture_output=True,text=True,timeout=150);logs.append(dict(args=list(args),exit=r.returncode,stdout=r.stdout,stderr=r.stderr));assert r.returncode==0,r.stderr;return r.stdout.strip()
assert not git('status','--porcelain') and git('branch','--show-current')=='data-team-development';git('fetch','origin','data-team-development');git('merge','--ff-only','origin/data-team-development');parent=git('rev-parse','HEAD')
selected={}
for name in ['export_second_boundary_readonly.py','run_export_second_boundary.py','audit_completed_study_readonly.py','run_completed_study_audit.py','audit_completed_study_readonly_v2.py','run_completed_study_audit_v2.py','close_completed_study_metadata_v2.py','run_close_completed_study_metadata_v2.py','export_completed_study_readonly.py','run_export_completed_study.py','publish_completed_study_and_bulk_current.py','persist_completed_study_code.py']:
 selected['data_owner/'+M.name+'/operations/'+name]=M/name
for name in ['reconcile_fourth_terminal_metadata_only.py','drive_unstarted_suffix20_once.py']:selected['data_owner/'+K.name+'/operations/'+name]=K/name
for folder in(M,K):selected['data_owner/'+folder.name+'/README.md']=folder/'README.md'
for name,source in selected.items():
 p=G/name;p.parent.mkdir(parents=True,exist_ok=True);data=source.read_bytes();p.write_bytes(data)
 if p.suffix=='.py':ast.parse(data.decode(),filename=str(p))
rpath=B/'consumer-deliveries/AINAV-DATA-T-OBS-THREE-FIXED-BOUNDARIES-COMPLETE-NOT-TASK-20261115-v1/release.json';r=json.loads(rpath.read_bytes())
provenance=G/'data_owner'/M.name/'completed-study-custody-index.json';provenance.write_text(json.dumps(dict(at=datetime.datetime.now().astimezone().isoformat(),original_release_path=str(rpath),original_release_sha256=sha(rpath),original_scope_id=r['scope_id'],program_sha256=r['program_sha256'],source_owner_commit=r['source_owner_commit'],measurement_complete=True,task_success=False,AB_comparison=False,public_aliases_initial_left_right=[[],['cuboid_a'],[]],bulk_first_four_closed_PASS3_original_FF_failed1=True,original_metadata_CAS_rejection_preserved_and_reconciled_without_physics=True,remaining_suffix20_driver_only_unstarted_ordinals5_through24=True,original_actor_FF_12N_4s_QP_FIFO_CLIMB_stop_and_caps_unchanged=True,raw_MJB_weights_env_video_not_in_Git=True,not_a_physical_authority_or_current_critic_training_permission=True,code_files={name:sha(p)for name,p in selected.items()}),ensure_ascii=False,indent=2)+'\n')
paths=list(selected)+[str(provenance.relative_to(G))];git('add','--',*paths);staged=git('diff','--cached','--name-only').splitlines();assert set(staged)==set(paths);assert all(p.startswith('data_owner/')and Path(p).suffix in('.py','.md','.json')for p in staged)
git('diff','--cached','--check');git('-c','user.name=Data Team Automation','-c','user.email=data-team-automation@localhost','commit','-m','data: close fixed-view observability study and preserve bulk native failure; roll unstarted suffix only');commit=git('rev-parse','HEAD');git('push','origin','HEAD:data-team-development');assert git('ls-remote','origin','refs/heads/data-team-development').split()[0]==commit and not git('status','--porcelain')
proof=dict(at=datetime.datetime.now().astimezone().isoformat(),commit=commit,parent=parent,files={p:sha(G/p)for p in paths},GitHub_branch_verified=True,clean=True,native_W_D_and_caps_not_modified=True,H_not_written=True,logs=logs)
with(M/'completed-study-code-publication.json').open('x')as f:json.dump(proof,f,indent=2);f.write('\n')
bundle=M/'completed-study-code.bundle';git('bundle','create',str(bundle),'data-team-development','^981c094b13ad4d1fdc752600b6d8660f626009eb');assert bundle.stat().st_size<5*1024**2
remote=r'''
from pathlib import Path
import sys,json,base64,hashlib,subprocess,datetime
x=json.load(sys.stdin);R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114');G=R/'code/reach-ability-research';M=R/'workspace/manifests/T-COMPLEX-observability-study-46308-20261115-v1';p=M/'completed-study-code.bundle';raw=base64.b64decode(x['bundle']);assert hashlib.sha256(raw).hexdigest()==x['bundle_sha256']
with p.open('xb')as f:f.write(raw)
logs=[]
def git(*args):
 r=subprocess.run(['git',*args],cwd=G,capture_output=True,text=True,timeout=120);logs.append(dict(args=list(args),exit=r.returncode,stdout=r.stdout,stderr=r.stderr));assert r.returncode==0,r.stderr;return r.stdout.strip()
assert not git('status','--porcelain');assert git('rev-parse','HEAD')=='981c094b13ad4d1fdc752600b6d8660f626009eb';git('bundle','verify',str(p));git('fetch',str(p),'refs/heads/data-team-development');git('merge','--ff-only','FETCH_HEAD');assert git('rev-parse','HEAD')==x['commit']and not git('status','--porcelain')
for name,pin in x['files'].items():assert hashlib.sha256((G/name).read_bytes()).hexdigest()==pin
print(json.dumps(dict(at=datetime.datetime.now().astimezone().isoformat(),commit=x['commit'],all_selected_code_SHA_match=True,no_H_write_no_frozen_native_source_write=True,checkout_clean=True,logs=logs)))
'''
rp=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(remote)],input=json.dumps(dict(bundle=base64.b64encode(bundle.read_bytes()).decode(),bundle_sha256=sha(bundle),commit=commit,files=proof['files'])),capture_output=True,text=True,timeout=250)
for suffix,text in [('stdout',rp.stdout),('stderr',rp.stderr),('exit',str(rp.returncode)+'\n')]:
 with(M/('completed-study-code-deployment.'+suffix)).open('x')as f:f.write(text)
assert rp.returncode==0,rp.stderr;deployment=json.loads(rp.stdout)
with(M/'completed-study-code-deployment.json').open('x')as f:json.dump(deployment,f,indent=2);f.write('\n')
print(json.dumps(dict(commit=commit,selected_files=len(paths),GitHub_and_remote_code_verified=True,raw_not_copied=True,H_not_written=True),indent=2))
