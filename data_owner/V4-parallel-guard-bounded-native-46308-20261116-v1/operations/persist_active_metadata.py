"""One code-only custody update and exact incremental remote lean ff; not runtime deployment."""
from pathlib import Path
import ast,os,json,subprocess,hashlib,base64,shlex,datetime
M=Path(__file__).resolve().parent;B=M.parent.parent;G=Path('/home/yuanyue/main/code/reach-ability-research');name=M.name;sha=lambda raw:hashlib.sha256(raw).hexdigest()
parent='12ecbc8e338c75f64e83720552906d20fbb260f4'
logs=[]
def git(*args):
 r=subprocess.run(['git',*args],cwd=G,text=True,capture_output=True,timeout=180);logs.append(dict(args=args,exit=r.returncode,stdout=r.stdout,stderr=r.stderr));assert r.returncode==0,r.stderr;return r.stdout.strip()
assert git('rev-parse','HEAD')==parent and git('branch','--show-current')=='data-team-development' and not git('status','--porcelain','-uall')
assert git('ls-remote','origin','refs/heads/data-team-development').split()[0]==parent
selected={}
for f in ['observe_readonly.py','publish_active_current.py','persist_active_metadata.py']:
 selected['data_owner/'+name+'/operations/'+f]=M/f
for f in ['Data-source41-exact-program-active.json','active-current-publication-proof.json']:
 selected['data_owner/'+name+'/observations/'+f]=M/f
for path,origin in selected.items():
 raw=origin.read_bytes();assert len(raw)<128*1024
 if origin.suffix=='.py':ast.parse(raw,filename=str(origin))
 if origin.suffix=='.json':json.loads(raw)
 p=G/path;assert not p.exists();p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
git('add','-f','--',*selected);assert set(git('diff','--cached','--name-only').splitlines())==set(selected);git('diff','--cached','--check')
git('-c','user.name=Data Team Automation','-c','user.email=data-team-automation@localhost','commit','-m','data: record exact41 new bounded qualification active and read-only phase observer without hot changes')
commit=git('rev-parse','HEAD');git('push','origin','HEAD:data-team-development');assert git('ls-remote','origin','refs/heads/data-team-development').split()[0]==commit and not git('status','--porcelain','-uall')
bundle=M/'post-launch-code.bundle';git('bundle','create',str(bundle),'data-team-development','^'+parent);assert bundle.stat().st_size<512*1024
payload=dict(parent=parent,commit=commit,bundle=base64.b64encode(bundle.read_bytes()).decode(),bundle_sha256=sha(bundle.read_bytes()),files={p:sha((G/p).read_bytes())for p in selected})
code=r'''
from pathlib import Path
import sys,json,hashlib,base64,subprocess
x=json.load(sys.stdin);R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114');G=R/'code/reach-ability-research';D=R/'workspace/manifests/V4-parallel-guard-bounded-native-46308-20261116-v1'
assert D.exists();p=D/'post-launch-code.bundle';raw=base64.b64decode(x['bundle']);assert hashlib.sha256(raw).hexdigest()==x['bundle_sha256']
with p.open('xb')as f:f.write(raw)
def git(*args):
 r=subprocess.run(['git',*args],cwd=G,capture_output=True,text=True,timeout=120);assert r.returncode==0,(args,r.stderr);return r.stdout.strip()
assert git('rev-parse','HEAD')==x['parent']and not git('status','--porcelain','-uall');git('bundle','verify',str(p));git('fetch',str(p),'refs/heads/data-team-development');git('merge','--ff-only','FETCH_HEAD');assert git('rev-parse','HEAD')==x['commit']and not git('status','--porcelain','-uall')
for name,pin in x['files'].items():
 raw=(G/name).read_bytes();assert hashlib.sha256(raw).hexdigest()==pin
 # Separate diagnostic directory only; no deployment to worker/authority/closed-runtime paths.
 # Preserve current worker freeze. Add small observation code/metadata only.
 q=D/Path(name).name
 if q.exists():assert q.read_bytes()==raw
 else:
  with q.open('xb')as f:f.write(raw)
print(json.dumps(dict(commit=x['commit'],clean=True,all_selected_SHA_match=True,no_runtime_source_or_H_mutation=True)))
'''
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],input=json.dumps(payload),text=True,capture_output=True,timeout=240)
for suffix,text in [('stdout',r.stdout),('stderr',r.stderr),('exit',str(r.returncode))]:
 with (M/('post-launch-code-deployment.'+suffix)).open('x')as f:f.write(text)
assert r.returncode==0,r.stderr
proof=dict(at=datetime.datetime.now().astimezone().isoformat(),parent=parent,commit=commit,local_GitHub_remote_verified=True,clean=True,files=payload['files'],remote=json.loads(r.stdout),code_only_no_raw_models_env_or_credentials=True,logs=logs)
with (M/'post-launch-code-custody-proof.json').open('x')as f:json.dump(proof,f,indent=2,ensure_ascii=False);f.write('\n')
print(json.dumps(dict(commit=commit,files=len(selected),remote=json.loads(r.stdout)),indent=2))
