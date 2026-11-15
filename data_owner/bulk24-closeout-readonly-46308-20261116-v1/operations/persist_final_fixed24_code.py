"""Persist changed Data code and final small receipts only; do not stage inherited work or raw assets."""
from pathlib import Path
import json,hashlib,subprocess,base64,shlex,datetime,ast
B=Path('/home/yuanyue/main/work/data-team');M=Path(__file__).resolve().parent;K=B/'manifests/bulk24-collector-46308-20261115-v1';V=B/'manifests/V4-legacy-common-policy-source-intake-46308-20261116-v1';F=B/'manifests/V4-pre-main-factor-and-bootstrap-review-46308-20261116-v1';G=Path('/home/yuanyue/main/code/reach-ability-research');parent='7b660a7e5e78c88f5cdeda6a8c76ac43e757914f';logs=[];sha=lambda b:hashlib.sha256(b).hexdigest()
def git(*args):
 r=subprocess.run(['git',*args],cwd=G,text=True,capture_output=True,timeout=150);logs.append(dict(args=args,exit=r.returncode,stdout=r.stdout,stderr=r.stderr));assert r.returncode==0,r.stderr;return r.stdout.strip()
assert git('branch','--show-current')=='data-team-development'and git('rev-parse','HEAD')==parent and not git('status','--porcelain','-uall');assert git('ls-remote','origin','refs/heads/data-team-development').split()[0]==parent
selected={}
for p in M.glob('*.py'):selected['data_owner/'+M.name+'/operations/'+p.name]=p
pointer=json.loads((M/'latest-snapshot-pointer.json').read_bytes())
for name in ['README.md','latest-snapshot-pointer.json',pointer['file'],'fixed24-final-original-release-proof.json','fixed24-final-authority-resource-proof.json','Data-only-final-publication-proof.json','final-publication-proof-name-erratum.json']:
 selected['data_owner/'+M.name+'/'+name]=M/name
D=Path(json.loads((M/'fixed24-final-original-release-proof.json').read_bytes())['local_release_path']).parent
for p in D.glob('*.json'):selected['data_owner/'+M.name+'/final-original-closeout/'+p.name]=p
for name in ['README.md','consume_resolved_legacy_policy.py','source-byte-verification.json','Data-resolved-legacy-common-policy-consumption.json']:
 selected['data_owner/'+V.name+'/'+name]=V/name
selected['data_owner/'+V.name+'/PREPARATION_FACTOR_POLICY.json']=V/'source-8105e755/PREPARATION_FACTOR_POLICY.json'
selected['data_owner/'+F.name+'/README.md']=F/'README.md'
for name in ['README.md','export_closed_ordinal24_originals.py','run_export_closed_ordinal24.py','closed24-original-release-index.json']:
 selected['data_owner/'+K.name+'/'+name]=K/name
changed=[]
for name,p in selected.items():
 data=p.read_bytes();assert len(data)<256*1024
 if p.suffix=='.py':ast.parse(data,filename=str(p))
 if p.suffix=='.json':json.loads(data)
 out=G/name
 if not out.exists()or out.read_bytes()!=data:changed.append(name)
 out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(data)
assert changed;git('add','-f','--',*sorted(changed));assert set(git('diff','--cached','--name-only').splitlines())==set(changed);git('diff','--cached','--check');git('-c','user.name=Data Team Automation','-c','user.email=data-team-automation@localhost','commit','-m','data: close fixed24 originals with complete bounded ledgers; consume explicit common-H and new-successor policy');commit=git('rev-parse','HEAD');git('push','origin','HEAD:data-team-development');assert git('ls-remote','origin','refs/heads/data-team-development').split()[0]==commit and not git('status','--porcelain','-uall');files={name:sha((G/name).read_bytes())for name in selected}
with(M/'fixed24-final-code-publication.json').open('x')as f:json.dump(dict(at=datetime.datetime.now().astimezone().isoformat(),commit=commit,parent=parent,changed_files=sorted(changed),files=files,GitHub_verified=True,clean=True,no_raw_arrays_images_MJB_weights_ENV_credential_or_active_frozen_source_changed=True,logs=logs),f,ensure_ascii=False,indent=2);f.write('\n')
bundle=M/'fixed24-final-code.bundle';git('bundle','create',str(bundle),'data-team-development','^'+parent);assert bundle.stat().st_size<1024**2
code=r'''
from pathlib import Path
import sys,json,base64,hashlib,subprocess
x=json.load(sys.stdin);R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114');G=R/'code/reach-ability-research';M=R/'workspace/manifests/bulk24-closeout-readonly-46308-20261116-v1';M.mkdir(exist_ok=True);p=M/'fixed24-final-code.bundle';raw=base64.b64decode(x['bundle']);assert hashlib.sha256(raw).hexdigest()==x['bundle_sha256']
with p.open('xb')as f:f.write(raw)
logs=[]
def git(*a):
 r=subprocess.run(['git',*a],cwd=G,capture_output=True,text=True,timeout=120);logs.append(dict(args=a,exit=r.returncode,stdout=r.stdout,stderr=r.stderr));assert r.returncode==0,r.stderr;return r.stdout.strip()
assert not git('status','--porcelain','-uall')and git('rev-parse','HEAD')==x['parent'];git('bundle','verify',str(p));git('fetch',str(p),'refs/heads/data-team-development');git('merge','--ff-only','FETCH_HEAD');assert git('rev-parse','HEAD')==x['commit']and not git('status','--porcelain','-uall')
for name,pin in x['files'].items():assert hashlib.sha256((G/name).read_bytes()).hexdigest()==pin
print(json.dumps(dict(commit=x['commit'],all_selected_SHA_match=True,clean=True,H_and_original_closed_programs_not_written=True,logs=logs)))
'''
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],input=json.dumps(dict(bundle=base64.b64encode(bundle.read_bytes()).decode(),bundle_sha256=sha(bundle.read_bytes()),parent=parent,commit=commit,files=files)),text=True,capture_output=True,timeout=220)
for suf,data in [('stdout',r.stdout),('stderr',r.stderr),('exit',str(r.returncode))]:
 with(M/('fixed24-final-code-deployment.'+suf)).open('x')as f:f.write(data)
assert r.returncode==0,r.stderr
with(M/'fixed24-final-code-deployment.json').open('x')as f:json.dump(json.loads(r.stdout),f,indent=2);f.write('\n')
print(json.dumps(dict(commit=commit,changed_files=len(changed),selected_custody_files=len(files),local_GitHub_remote_verified=True,clean=True,no_closed_scope_or_H_changes=True)))
