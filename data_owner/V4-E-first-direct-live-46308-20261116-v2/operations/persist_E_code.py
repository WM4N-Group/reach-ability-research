"""One code-only custody update and exact incremental remote lean ff; not runtime deployment."""
from pathlib import Path
import ast,os,json,subprocess,hashlib,base64,shlex,datetime
M=Path(__file__).resolve().parent;B=M.parent.parent;G=Path('/home/yuanyue/main/code/reach-ability-research');name=M.name;sha=lambda raw:hashlib.sha256(raw).hexdigest()
parent='5e6a3ade86332cd95cafbd51909c73128b13150c'
logs=[]
def git(*args):
 r=subprocess.run(['git',*args],cwd=G,text=True,capture_output=True,timeout=180);logs.append(dict(args=args,exit=r.returncode,stdout=r.stdout,stderr=r.stderr));assert r.returncode==0,r.stderr;return r.stdout.strip()
assert git('rev-parse','HEAD')==parent and git('branch','--show-current')=='data-team-development' and not git('status','--porcelain','-uall')
assert git('ls-remote','origin','refs/heads/data-team-development').split()[0]==parent
selected={}
W=B/'workers'/name
for q in W.rglob('*'):
 if q.is_file()and'__pycache__'not in q.parts and q.suffix in('.py','.json','.md'):
  selected['data_owner/'+name+'/worker/'+str(q.relative_to(W))]=q
for q in M.glob('*.py'):selected['data_owner/'+name+'/operations/'+q.name]=q
for f in ['source59.original.json','source-staging-proof.json']:
 selected['data_owner/'+name+'/'+f]=M/f
for path,origin in selected.items():
 raw=origin.read_bytes();assert len(raw)<128*1024
 if origin.suffix=='.py':ast.parse(raw,filename=str(origin))
 if origin.suffix=='.json':json.loads(raw)
 p=G/path;assert not p.exists();p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
git('add','-f','--',*selected);assert set(git('diff','--cached','--name-only').splitlines())==set(selected);git('diff','--cached','--check')
git('-c','user.name=Data Team Automation','-c','user.email=data-team-automation@localhost','commit','-m','data: freeze corrected E authority envelope and dispatch prerequisites; preserve metadata-only v1 no-physical failure')
commit=git('rev-parse','HEAD');git('push','origin','HEAD:data-team-development');assert git('ls-remote','origin','refs/heads/data-team-development').split()[0]==commit and not git('status','--porcelain','-uall')
bundle=M/'code.bundle';git('bundle','create',str(bundle),'data-team-development','^'+parent);assert bundle.stat().st_size<2*1024**2
payload=dict(parent=parent,commit=commit,bundle=base64.b64encode(bundle.read_bytes()).decode(),bundle_sha256=sha(bundle.read_bytes()),files={p:sha((G/p).read_bytes())for p in selected})
code=r'''
from pathlib import Path
import sys,json,hashlib,base64,subprocess
x=json.load(sys.stdin);R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114');G=R/'code/reach-ability-research';D=R/'workspace/manifests/V4-E-first-direct-live-46308-20261116-v2'
assert D.exists();p=D/'code.bundle';raw=base64.b64decode(x['bundle']);assert hashlib.sha256(raw).hexdigest()==x['bundle_sha256']
with p.open('xb')as f:f.write(raw)
def git(*args):
 r=subprocess.run(['git',*args],cwd=G,capture_output=True,text=True,timeout=120);assert r.returncode==0,(args,r.stderr);return r.stdout.strip()
assert git('rev-parse','HEAD')==x['parent']and not git('status','--porcelain','-uall');git('bundle','verify',str(p));git('fetch',str(p),'refs/heads/data-team-development');git('merge','--ff-only','FETCH_HEAD');assert git('rev-parse','HEAD')==x['commit']and not git('status','--porcelain','-uall')
for name,pin in x['files'].items():
 raw=(G/name).read_bytes();assert hashlib.sha256(raw).hexdigest()==pin
 # Separate diagnostic directory only; no deployment to worker/authority/closed-runtime paths.
 # Code custody only. Full distinct worker was staged and will be frozen separately.
 pass
print(json.dumps(dict(commit=x['commit'],clean=True,all_selected_SHA_match=True,no_runtime_source_or_H_mutation=True)))
'''
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],input=json.dumps(payload),text=True,capture_output=True,timeout=240)
for suffix,text in [('stdout',r.stdout),('stderr',r.stderr),('exit',str(r.returncode))]:
 with (M/('code-deployment.'+suffix)).open('x')as f:f.write(text)
assert r.returncode==0,r.stderr
proof=dict(at=datetime.datetime.now().astimezone().isoformat(),parent=parent,commit=commit,local_GitHub_remote_verified=True,clean=True,files=payload['files'],remote=json.loads(r.stdout),code_only_no_raw_models_env_or_credentials=True,logs=logs)
with (M/'code-custody-proof.json').open('x')as f:json.dump(proof,f,indent=2,ensure_ascii=False);f.write('\n')
print(json.dumps(dict(commit=commit,files=len(selected),remote=json.loads(r.stdout)),indent=2))
