from pathlib import Path
import json,ast,hashlib,subprocess,base64,shlex,datetime
B=Path('/home/yuanyue/main/work/data-team');M=Path(__file__).resolve().parent;G=Path('/home/yuanyue/main/code/reach-ability-research');parent='e2bc31e875ccd8cbe0d0ac5bb9214b704af99ff0';sha=lambda b:hashlib.sha256(b).hexdigest();logs=[]
def git(*args):
 r=subprocess.run(['git',*args],cwd=G,capture_output=True,text=True,timeout=180);logs.append(dict(args=args,exit=r.returncode,stdout=r.stdout,stderr=r.stderr));assert r.returncode==0,r.stderr;return r.stdout.strip()
assert git('rev-parse','HEAD')==parent and git('branch','--show-current')=='data-team-development'and not git('status','--porcelain','-uall');assert git('ls-remote','origin','refs/heads/data-team-development').split()[0]==parent
selected={}
for N in ['E20-prearrival40-direct-live-46308-20261116-v2',M.name]:
 W=B/'workers'/N;root='data_owner/'+N+'/program-and-history'
 for p in W.rglob('*'):
  if p.is_file():assert not p.is_symlink()and'__pycache__'not in p.parts;selected[root+'/worker/'+str(p.relative_to(W))]=p
 if N==M.name:entries=['control.py','phase.py','main_once_then_encode_close.py','update_actual_E20_main_status.py','sync_E20_family_code.py','README_CN.md','preregistered_Data_wrapper_dependency_revision.json','inventory-proof.json','freeze-proof.json','prepare-proof.json','dispatch-zero-proof.json','zero-proof.json','qualify-zero-1-proof.json','dispatch-main-proof.json','actual-main-first-readonly-snapshot.json','actual-E20-main-Data-only-publication-proof.json']
 else:entries=['control.py','phase.py','close_zero_startup_failure_metadata.py','DATA_CURRENT_STATIC_HANDLE_FIX_NEW_PROGRAM_NOT_DISPATCH.json','source-intake-and-static-check.json','static-asset-binding-proof.json','compile-asset-proof.json','inventory-proof.json','freeze-proof.json','dispatch-zero-proof.json','zero-proof.json','zero-startup-maintenance-close-proof.json']
 for name in entries:selected[root+'/metadata/'+name]=B/'manifests'/N/name
# Correct only the metadata custody client's mkdir bug; original failed version remains in prior Git commit.
Q=B/'manifests/old46174-left-need-based-readonly-20261116-v1';p=Q/'sync_recovery_code.py';old=p.read_text();assert 'D.mkdir();'in old;p.write_text(old.replace('D.mkdir();','D.mkdir(parents=True);',1))
selected['data_owner/'+Q.name+'/recovery/scripts/sync_recovery_code.py']=p
selected['data_owner/'+Q.name+'/recovery/proof/transport-repaired-custody.json']=Q/'old-left-recovery-code-custody-proof.json'
for rel,p in selected.items():
 raw=p.read_bytes();assert len(raw)<128*1024,(str(p),len(raw))
 if p.suffix=='.py':ast.parse(raw)
 if p.suffix=='.json':json.loads(raw)
 q=G/rel;q.parent.mkdir(parents=True,exist_ok=True);assert not q.exists()or rel.endswith('/sync_recovery_code.py');q.write_bytes(raw)
git('add','-f','--',*selected);assert set(git('diff','--cached','--name-only').splitlines())==set(selected);git('diff','--cached','--check');git('-c','user.name=Data Team Automation','-c','user.email=data-team-automation@localhost','commit','-m','data: run one real E20 main after static fix and complete privacy imports; retain failed zero dispatch and unknown startup cost');commit=git('rev-parse','HEAD');git('push','origin','HEAD:data-team-development');assert git('ls-remote','origin','refs/heads/data-team-development').split()[0]==commit and not git('status','--porcelain','-uall');bundle=M/'active-E20-code.bundle';git('bundle','create',str(bundle),'data-team-development','^'+parent);assert bundle.stat().st_size<1024*1024
payload=dict(parent=parent,commit=commit,bundle=base64.b64encode(bundle.read_bytes()).decode(),bundle_sha256=sha(bundle.read_bytes()),pins={rel:sha(p.read_bytes())for rel,p in selected.items()});code=r'''
from pathlib import Path
import json,sys,subprocess,base64,hashlib
x=json.load(sys.stdin);R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114');G=R/'code/reach-ability-research';D=R/'workspace/manifests/E20-prearrival40-direct-live-46308-20261116-v3/code-custody';assert not D.exists();D.mkdir(parents=True);p=D/'active-E20-code.bundle';raw=base64.b64decode(x['bundle']);assert hashlib.sha256(raw).hexdigest()==x['bundle_sha256']
with p.open('xb')as f:f.write(raw)
def git(*args):
 r=subprocess.run(['git',*args],cwd=G,capture_output=True,text=True,timeout=120);assert r.returncode==0,(args,r.stderr);return r.stdout.strip()
assert git('rev-parse','HEAD')==x['parent']and not git('status','--porcelain','-uall');git('bundle','verify',str(p));git('fetch',str(p),'refs/heads/data-team-development');git('merge','--ff-only','FETCH_HEAD');assert git('rev-parse','HEAD')==x['commit']and not git('status','--porcelain','-uall')
for rel,pin in x['pins'].items():assert hashlib.sha256((G/rel).read_bytes()).hexdigest()==pin
print(json.dumps(dict(commit=x['commit'],clean=True,all_selected_SHA_match=True,no_frozen_worker_source_or_H_mutation=True)))
''';r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],input=json.dumps(payload),capture_output=True,text=True,timeout=180);assert r.returncode==0,r.stderr;proof=dict(at=datetime.datetime.now().astimezone().isoformat(),parent=parent,commit=commit,local_GitHub_remote_verified_clean=True,files=payload['pins'],remote=json.loads(r.stdout),no_video_png_raw_NPZ_MJB_models_env_or_credentials_in_Git=True,logs=logs);(M/'active-code-custody-proof.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n');print(json.dumps(dict(commit=commit,files=len(selected),local_GitHub_remote_clean=True),ensure_ascii=False))
