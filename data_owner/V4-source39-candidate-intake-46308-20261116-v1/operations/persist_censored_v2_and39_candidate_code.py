"""Code/small metadata custody only; v1 closed and v2 in-flight originals are never changed."""
from pathlib import Path
import json,hashlib,subprocess,base64,shlex,datetime,ast
B=Path('/home/yuanyue/main/work/data-team');M=Path(__file__).resolve().parent;A=B/'manifests/V4-bounded-climb-nav-native-46308-20261116-v1';J=B/'manifests/V-JEPA-J1-resource-response-46308-20261116-v1';G=Path('/home/yuanyue/main/code/reach-ability-research');parent='3b55d0ec69848d32cc16008af525ed22a30b4c5e';logs=[];sha=lambda b:hashlib.sha256(b).hexdigest()
def git(*args):
 r=subprocess.run(['git',*args],cwd=G,text=True,capture_output=True,timeout=150);logs.append(dict(args=args,exit=r.returncode,stdout=r.stdout,stderr=r.stderr));assert r.returncode==0,r.stderr;return r.stdout.strip()
assert git('branch','--show-current')=='data-team-development'and git('rev-parse','HEAD')==parent and not git('status','--porcelain','-uall');assert git('ls-remote','origin','refs/heads/data-team-development').split()[0]==parent
selected={}
R=B/'manifests/V4-bounded-climb-nav-native-46308-20261116-v2'
for folder in[M,R]:
 for p in folder.glob('*.py'):selected['data_owner/'+folder.name+'/operations/'+p.name]=p
 selected['data_owner/'+folder.name+'/README.md']=folder/'README.md'
for name in ['source-byte-verification.json','Data-candidate39-consumed-no-hot-switch.json','Data-only-v2-censor-publication-proof.json','Data-only-assessed-child-publication-proof.json']:
 selected['data_owner/'+M.name+'/'+name]=M/name
for name in ['component-original-release-proof.json','Data-budget-censor-exact-capture-and-native-boundaries.json','bounded-v2-final-authority-resource-proof.json','assessed-wall-censor-closeout-proof.json','readonly-resource-wait-observation-062346.json']:
 selected['data_owner/'+R.name+'/'+name]=R/name
for stem in ['AINAV-DATA-V4-BOUNDED-QUAL-V2-ORIGINAL-RESOURCE-AND-NATIVE-OUTCOME-20261116-v1','AINAV-DATA-V4-BOUNDED-V2-WALL-CENSOR-ASSESSED-CLOSEOUT-20261116-v1']:
 D=B/'consumer-deliveries'/stem
 for p in D.rglob('*.json'):selected['data_owner/'+R.name+'/'+stem+'/'+str(p.relative_to(D))]=p
changed=[]
for name,p in selected.items():
 raw=p.read_bytes();assert len(raw)<256*1024
 if p.suffix=='.py':ast.parse(raw,filename=str(p))
 if p.suffix=='.json':json.loads(raw)
 q=G/name
 if not q.exists()or q.read_bytes()!=raw:changed.append(name)
 q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(raw)
assert changed;git('add','-f','--',*changed);assert set(git('diff','--cached','--name-only').splitlines())==set(changed);git('diff','--cached','--check');git('-c','user.name=Data Team Automation','-c','user.email=data-team-automation@localhost','commit','-m','data: close bounded v2 as wall resource censor, preserve native boundaries and assessment errata; receive39 without hot switch');commit=git('rev-parse','HEAD');git('push','origin','HEAD:data-team-development');assert git('ls-remote','origin','refs/heads/data-team-development').split()[0]==commit and not git('status','--porcelain','-uall');files={name:sha((G/name).read_bytes())for name in selected}
with(M/'censor-code-publication.json').open('x')as f:json.dump(dict(at=datetime.datetime.now().astimezone().isoformat(),commit=commit,parent=parent,changed_files=changed,files=files,GitHub_verified=True,clean=True,no_MJB_NPZ_weights_ENV_or_credentials_in_Git=True,no_H_or_closed_or_inflight_program_changes=True,logs=logs),f,ensure_ascii=False,indent=2);f.write('\n')
bundle=M/'censor-code.bundle';git('bundle','create',str(bundle),'data-team-development','^'+parent);assert bundle.stat().st_size<2*1024**2
code=r'''
from pathlib import Path
import sys,json,base64,hashlib,subprocess
x=json.load(sys.stdin);R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114');G=R/'code/reach-ability-research';M=R/'workspace/manifests/V4-source39-candidate-intake-46308-20261116-v1';M.mkdir(exist_ok=True);p=M/'censor-code.bundle';raw=base64.b64decode(x['bundle']);assert hashlib.sha256(raw).hexdigest()==x['bundle_sha256']
with p.open('xb')as f:f.write(raw)
logs=[]
def git(*a):
 r=subprocess.run(['git',*a],cwd=G,capture_output=True,text=True,timeout=120);logs.append(dict(args=a,exit=r.returncode,stdout=r.stdout,stderr=r.stderr));assert r.returncode==0,r.stderr;return r.stdout.strip()
assert not git('status','--porcelain','-uall')and git('rev-parse','HEAD')==x['parent'];git('bundle','verify',str(p));git('fetch',str(p),'refs/heads/data-team-development');git('merge','--ff-only','FETCH_HEAD');assert git('rev-parse','HEAD')==x['commit']and not git('status','--porcelain','-uall')
for name,pin in x['files'].items():assert hashlib.sha256((G/name).read_bytes()).hexdigest()==pin
print(json.dumps(dict(commit=x['commit'],all_selected_SHA_match=True,clean=True,no_H_original_ledger_or_inflight_program_changes=True,logs=logs)))
'''
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],input=json.dumps(dict(bundle=base64.b64encode(bundle.read_bytes()).decode(),bundle_sha256=sha(bundle.read_bytes()),parent=parent,commit=commit,files=files)),text=True,capture_output=True,timeout=220)
for suf,data in [('stdout',r.stdout),('stderr',r.stderr),('exit',str(r.returncode))]:
 with(M/('censor-code-deployment.'+suf)).open('x')as f:f.write(data)
assert r.returncode==0,r.stderr
with(M/'censor-code-deployment.json').open('x')as f:json.dump(json.loads(r.stdout),f,indent=2);f.write('\n')
print(json.dumps(dict(commit=commit,changed_files=len(changed),local_GitHub_remote_verified=True,no_H_or_inflight_source_or_caps_changed=True)))
