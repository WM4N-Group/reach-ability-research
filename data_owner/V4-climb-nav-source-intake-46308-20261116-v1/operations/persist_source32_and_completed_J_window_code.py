"""Persist selected Data code/small receipts only; do not publish raw/logs/weights or mutate H."""
from pathlib import Path
import json,hashlib,subprocess,base64,shlex,datetime,ast
B=Path('/home/yuanyue/main/work/data-team');M=Path(__file__).resolve().parent;K=B/'manifests/bulk24-collector-46308-20261115-v1';J=B/'manifests/V-JEPA-J1-resource-response-46308-20261116-v1';G=Path('/home/yuanyue/main/code/reach-ability-research');parent='8fb70491988fd5084fbf6b28f4b13087ed93766b';logs=[];sha=lambda b:hashlib.sha256(b).hexdigest()
def git(*args):
 r=subprocess.run(['git',*args],cwd=G,text=True,capture_output=True,timeout=150);logs.append(dict(args=args,exit=r.returncode,stdout=r.stdout,stderr=r.stderr));assert r.returncode==0,r.stderr;return r.stdout.strip()
assert git('branch','--show-current')=='data-team-development'and git('rev-parse','HEAD')==parent and not git('status','--porcelain','-uall')
assert git('ls-remote','origin','refs/heads/data-team-development').split()[0]==parent
selected={}
for p in M.glob('*.py'):selected['data_owner/'+M.name+'/operations/'+p.name]=p
for name in ['README.md','source-byte-verification.json','Data-climb-nav-source32-consumption-not-handoff.json','Data-only-report-location-correction-proof.json','J-ACTUAL_WEIGHT_AND_CPU_TECHNICAL_MILESTONE.original.json','J-Data_technical_window_completion_ack.original.json']:
 selected['data_owner/'+M.name+'/'+name]=M/name
for name in ['README.md','Data-J1-download-completion-report-consumed.json','Data-J1-completed-CPU-technical-window-consumed.json','Data-J1-window0415-expired-technically-complete.json']:
 selected['data_owner/'+J.name+'/'+name]=J/name
for name,p in selected.items():
 data=p.read_bytes();assert len(data)<128*1024
 if p.suffix=='.py':ast.parse(data,filename=str(p))
 if p.suffix=='.json':json.loads(data)
 out=G/name;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(data)
paths=sorted(selected);git('add','-f','--',*paths);assert set(git('diff','--cached','--name-only').splitlines())==set(paths);git('diff','--cached','--check');git('-c','user.name=Data Team Automation','-c','user.email=data-team-automation@localhost','commit','-m','data: consume exact32 CLIMB NAV source observer and completed bounded J1 CPU metadata; keep closed scopes immutable');commit=git('rev-parse','HEAD');git('push','origin','HEAD:data-team-development');assert git('ls-remote','origin','refs/heads/data-team-development').split()[0]==commit and not git('status','--porcelain','-uall')
files={n:sha((G/n).read_bytes())for n in paths}
with(M/'code-publication.json').open('x')as f:json.dump(dict(at=datetime.datetime.now().astimezone().isoformat(),commit=commit,parent=parent,files=files,GitHub_verified=True,clean=True,no_raw_weights_ENV_credential_or_active_frozen_source_in_selected=True,logs=logs),f,ensure_ascii=False,indent=2);f.write('\n')
bundle=M/'incremental-code.bundle';git('bundle','create',str(bundle),'data-team-development','^'+parent);assert bundle.stat().st_size<1024**2
code=r'''
from pathlib import Path
import sys,json,base64,hashlib,subprocess
x=json.load(sys.stdin);R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114');G=R/'code/reach-ability-research';M=R/'workspace/manifests/V4-climb-nav-source-intake-46308-20261116-v1';M.mkdir(exist_ok=True);p=M/'incremental-code.bundle';raw=base64.b64decode(x['bundle']);assert hashlib.sha256(raw).hexdigest()==x['bundle_sha256']
with p.open('xb')as f:f.write(raw)
logs=[]
def git(*a):
 r=subprocess.run(['git',*a],cwd=G,capture_output=True,text=True,timeout=120);logs.append(dict(args=a,exit=r.returncode,stdout=r.stdout,stderr=r.stderr));assert r.returncode==0,r.stderr;return r.stdout.strip()
assert not git('status','--porcelain','-uall')and git('rev-parse','HEAD')==x['parent'];git('bundle','verify',str(p));git('fetch',str(p),'refs/heads/data-team-development');git('merge','--ff-only','FETCH_HEAD');assert git('rev-parse','HEAD')==x['commit']and not git('status','--porcelain','-uall')
for name,pin in x['files'].items():assert hashlib.sha256((G/name).read_bytes()).hexdigest()==pin
print(json.dumps(dict(commit=x['commit'],all_selected_SHA_match=True,clean=True,H_and_active_workers_and_closed_programs_not_written=True,logs=logs)))
'''
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],input=json.dumps(dict(bundle=base64.b64encode(bundle.read_bytes()).decode(),bundle_sha256=sha(bundle.read_bytes()),parent=parent,commit=commit,files=files)),capture_output=True,text=True,timeout=220)
for suffix,data in [('stdout',r.stdout),('stderr',r.stderr),('exit',str(r.returncode)+'\n')]:
 with(M/('code-deployment.'+suffix)).open('x')as f:f.write(data)
assert r.returncode==0,r.stderr
with(M/'code-deployment.json').open('x')as f:json.dump(json.loads(r.stdout),f,indent=2);f.write('\n')
print(json.dumps(dict(commit=commit,selected_files=len(files),local_GitHub_remote_verified=True,clean=True,no_H_or_native_phase_or_program_changes=True)))
