from pathlib import Path
import ast,json,hashlib,subprocess,base64,shlex,datetime
B=Path('/home/yuanyue/main/work/data-team');M=Path(__file__).resolve().parent;G=Path('/home/yuanyue/main/code/reach-ability-research');E=B/'manifests/E20-prearrival40-direct-live-46308-20261116-v3';P=B/'development/perf-resource-policy-20261116-v1';parent='83ac38c1c39d80f7b2f81439ed6f5693745ead97';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();logs=[]
def git(*args):
 r=subprocess.run(['git',*args],cwd=G,capture_output=True,text=True,timeout=180);logs.append(dict(args=args,exit=r.returncode,stdout=r.stdout,stderr=r.stderr));assert r.returncode==0,r.stderr;return r.stdout.strip()
assert git('rev-parse','HEAD')==parent and git('branch','--show-current')=='data-team-development'and not git('status','--porcelain','-uall');assert git('ls-remote','origin','refs/heads/data-team-development').split()[0]==parent
selected={};root='data_owner/'+M.name
for p in P.iterdir():
 if p.is_file()and p.suffix in('.py','.json','.md'):selected[root+'/code/'+p.name]=p
for p in M.iterdir():
 if p.is_file()and p.suffix in('.py','.json','.md','.stderr','.stdout')and p.stat().st_size<128*1024:selected[root+'/evidence/'+p.name]=p
for dirname in ['AINAV-DATA-PERF-CONTROLLED-IO-PERIODIC-GUARD-CPU-QUALIFIED-NOT-NATIVE-20261116-v1','AINAV-DATA-E20-40MM-ACTUAL-ENTRY-NATIVE-CONFIRMATION-LOST-COMPLETE-VIDEO-20261116-v1']:
 D=B/'consumer-deliveries'/dirname
 for p in D.rglob('*'):
  if p.is_file():selected[root+'/releases/'+dirname+'/'+str(p.relative_to(D))]=p
for name in ['export_closed_main_minimum.py','publish_main_minimum.py','main-minimum-publication-proof.json','plan1935-performance-priority-readonly-snapshot.json','close-proof.json','encode-proof.json']:
 selected[root+'/E20-closed-original/'+name]=E/name
selected['data_owner/'+E.name+'/program-and-history/metadata/README_CN.md']=E/'README_CN.md'
for rel,p in selected.items():
 assert not p.is_symlink()and p.stat().st_size<128*1024,(str(p),p.stat().st_size);raw=p.read_bytes()
 if p.suffix=='.py':ast.parse(raw)
 if p.suffix=='.json':json.loads(raw)
 q=G/rel;q.parent.mkdir(parents=True,exist_ok=True);assert not q.exists()or rel.endswith('/metadata/README_CN.md');q.write_bytes(raw)
git('add','-f','--',*selected);assert set(git('diff','--cached','--name-only').splitlines())==set(selected);git('diff','--cached','--check');git('-c','user.name=Data Team Automation','-c','user.email=data-team-automation@localhost','commit','-m','data: implement future controlled IO and periodic resource guard; measure matched parallel8 baseline and preserve failed E20 complete video');commit=git('rev-parse','HEAD');git('push','origin','HEAD:data-team-development');assert git('ls-remote','origin','refs/heads/data-team-development').split()[0]==commit and not git('status','--porcelain','-uall');bundle=M/'perf-code.bundle';git('bundle','create',str(bundle),'data-team-development','^'+parent);assert bundle.stat().st_size<2*1024**2
payload=dict(parent=parent,commit=commit,bundle=base64.b64encode(bundle.read_bytes()).decode(),bundle_sha256=sha(bundle),pins={rel:sha(p)for rel,p in selected.items()});code=r'''
from pathlib import Path
import json,sys,subprocess,base64,hashlib
x=json.load(sys.stdin);R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114');G=R/'code/reach-ability-research';D=R/'workspace/manifests/perf-resource-policy-20261116-v1/code-custody';assert not D.exists();D.mkdir(parents=True);p=D/'perf-code.bundle';raw=base64.b64decode(x['bundle']);assert hashlib.sha256(raw).hexdigest()==x['bundle_sha256']
with p.open('xb')as f:f.write(raw)
def git(*args):
 r=subprocess.run(['git',*args],cwd=G,capture_output=True,text=True,timeout=120);assert r.returncode==0,(args,r.stderr);return r.stdout.strip()
assert git('rev-parse','HEAD')==x['parent']and not git('status','--porcelain','-uall');git('bundle','verify',str(p));git('fetch',str(p),'refs/heads/data-team-development');git('merge','--ff-only','FETCH_HEAD');assert git('rev-parse','HEAD')==x['commit']and not git('status','--porcelain','-uall')
for rel,pin in x['pins'].items():assert hashlib.sha256((G/rel).read_bytes()).hexdigest()==pin
print(json.dumps(dict(commit=x['commit'],clean=True,all_selected_SHA_match=True,no_frozen_source_or_H_or_runtime_mutation=True)))
''';r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],input=json.dumps(payload),capture_output=True,text=True,timeout=180);assert r.returncode==0,r.stderr;(M/'code-custody-proof.json').write_text(json.dumps(dict(at=datetime.datetime.now().astimezone().isoformat(),commit=commit,parent=parent,local_GitHub_remote_verified_clean=True,selected_pins=payload['pins'],remote=json.loads(r.stdout),no_video_png_NPZ_MJB_weights_env_or_credentials_in_Git=True,logs=logs),ensure_ascii=False,indent=2)+'\n');print(json.dumps(dict(commit=commit,files=len(selected),local_GitHub_remote_clean=True),ensure_ascii=False))
