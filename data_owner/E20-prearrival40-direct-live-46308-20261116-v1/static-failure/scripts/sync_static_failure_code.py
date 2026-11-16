from pathlib import Path
import ast,json,hashlib,subprocess,base64,shlex,datetime
B=Path('/home/yuanyue/main/work/data-team');M=B/'manifests/E20-prearrival40-direct-live-46308-20261116-v1';G=Path('/home/yuanyue/main/code/reach-ability-research');D=B/'consumer-deliveries/AINAV-DATA-E20-PREARRIVAL40-STATIC-ASSET-GEOM-LOOKUP-FAILED-NO-ZERO-MAIN-20261116-v1';parent='a6f260b8df93bde0994ee6c0882eefd29d4709fc';sha=lambda b:hashlib.sha256(b).hexdigest();logs=[]
def git(*args):
 r=subprocess.run(['git',*args],cwd=G,capture_output=True,text=True,timeout=180);logs.append(dict(args=args,exit=r.returncode,stdout=r.stdout,stderr=r.stderr));assert r.returncode==0,r.stderr;return r.stdout.strip()
assert git('rev-parse','HEAD')==parent and git('branch','--show-current')=='data-team-development'and not git('status','--porcelain','-uall');assert git('ls-remote','origin','refs/heads/data-team-development').split()[0]==parent
scripts=['control.py','phase.py','publish_static_failure.py','update_static_failure_status.py','sync_static_failure_code.py']
for name in scripts:ast.parse((M/name).read_bytes())
selected={};root='data_owner/'+M.name+'/static-failure'
for name in scripts:selected[root+'/scripts/'+name]=M/name
W=B/'workers'/M.name
for p in W.rglob('*'):
 if p.is_file():
  assert not p.is_symlink() and '__pycache__' not in p.parts
  selected[root+'/worker/'+str(p.relative_to(W))]=p
for name in ['DATA_ONE_NEW_DEV_PREARRIVAL_PROGRAM_SOURCE_NOT_DISPATCH.json','USER_ENVIRONMENT_SKILL_DOMAIN_ADJUSTMENT_AUTHORIZED_20261116_v1.json','local-unfrozen-intake-path-error.json']:
 selected[root+'/intake/'+name]=M/name
for p in D.rglob('*'):
 if p.is_file():selected[root+'/release/'+str(p.relative_to(D))]=p
for name in ['static-failure-publication-proof.json','static-failure-Data-only-status-proof.json']:
 selected[root+'/proof/'+name]=M/name
for rel,p in selected.items():
 raw=p.read_bytes();assert len(raw)<128*1024
 if p.suffix=='.json':json.loads(raw)
 q=G/rel;assert not q.exists();q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(raw)
git('add','-f','--',*selected);assert set(git('diff','--cached','--name-only').splitlines())==set(selected);git('diff','--cached','--check');git('-c','user.name=Data Team Automation','-c','user.email=data-team-automation@localhost','commit','-m','data: preserve E20 preregistered brake program and closed static geom lookup failure zero0 main0');commit=git('rev-parse','HEAD');git('push','origin','HEAD:data-team-development');assert git('ls-remote','origin','refs/heads/data-team-development').split()[0]==commit and not git('status','--porcelain','-uall');bundle=M/'E20-static-code.bundle';git('bundle','create',str(bundle),'data-team-development','^'+parent);assert bundle.stat().st_size<512*1024
payload=dict(parent=parent,commit=commit,bundle=base64.b64encode(bundle.read_bytes()).decode(),sha256=sha(bundle.read_bytes()),pins={rel:sha(p.read_bytes())for rel,p in selected.items()});code=r'''
from pathlib import Path
import json,sys,subprocess,base64,hashlib
x=json.load(sys.stdin);R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114');G=R/'code/reach-ability-research';D=R/'workspace/manifests/E20-prearrival40-direct-live-46308-20261116-v1/E20-static-code-custody';assert not D.exists();D.mkdir();bundle=D/'E20-static-code.bundle';raw=base64.b64decode(x['bundle']);assert hashlib.sha256(raw).hexdigest()==x['sha256']
with bundle.open('xb')as f:f.write(raw)
def git(*args):
 r=subprocess.run(['git',*args],cwd=G,capture_output=True,text=True,timeout=120);assert r.returncode==0,(args,r.stderr);return r.stdout.strip()
assert git('rev-parse','HEAD')==x['parent']and not git('status','--porcelain','-uall');git('bundle','verify',str(bundle));git('fetch',str(bundle),'refs/heads/data-team-development');git('merge','--ff-only','FETCH_HEAD');assert git('rev-parse','HEAD')==x['commit']and not git('status','--porcelain','-uall')
for rel,pin in x['pins'].items():assert hashlib.sha256((G/rel).read_bytes()).hexdigest()==pin
print(json.dumps(dict(commit=x['commit'],clean=True,all_selected_SHA_match=True,no_runtime_source_or_H_change=True)))
'''
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],input=json.dumps(payload),capture_output=True,text=True,timeout=180);assert r.returncode==0,r.stderr;proof=dict(at=datetime.datetime.now().astimezone().isoformat(),parent=parent,commit=commit,local_GitHub_remote_verified_clean=True,selected_files=payload['pins'],no_video_raw_models_env_or_credentials_in_Git=True,remote=json.loads(r.stdout),logs=logs);(M/'E20-static-code-custody-proof.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n');print(json.dumps(dict(commit=commit,files=len(selected),local_GitHub_remote_clean=True),ensure_ascii=False))
