"""Selected Data postprocess/intake custody only. No datasets or native writes."""
from pathlib import Path
import ast,json,hashlib,datetime,subprocess,shlex,base64
B=Path('/home/yuanyue/main/work/data-team');M=Path(__file__).resolve().parent;G=Path('/home/yuanyue/main/code/reach-ability-research');V=B/'manifests/V4-five-arm-intake-46308-20261115-v1';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();logs=[]
def git(*args):
 r=subprocess.run(['git',*args],cwd=G,capture_output=True,text=True,timeout=150);logs.append(dict(args=args,exit=r.returncode,stdout=r.stdout,stderr=r.stderr));assert r.returncode==0,r.stderr;return r.stdout.strip()
assert not git('status','--porcelain')and git('branch','--show-current')=='data-team-development';git('fetch','origin','data-team-development');git('merge','--ff-only','origin/data-team-development');parent=git('rev-parse','HEAD');selected={}
for count in ['four','five']:
 n=f'V4-{count}-arm-video-postprocess-46308-20261115-v1';D=B/'development'/n
 for name in [f'encode_{count}_arm_originals.py',f'test_{count}_arm_originals.py','run_remote_software_tests.py','README.md']:selected['data_owner/'+n+'/implementation/'+name]=D/name
 O=B/'manifests'/n
 for p in O.glob('publish*.py'):selected['data_owner/'+n+'/operations/'+p.name]=p
for folder in ['bulk24-collector-46308-20261115-v1','T-COMPLEX-observability-study-46308-20261115-v1','V4-five-arm-intake-46308-20261115-v1']:selected['data_owner/'+folder+'/README.md']=B/'manifests'/folder/'README.md'
selected['data_owner/'+V.name+'/Data-plan-2253-five-arm-intake.json']=V/'Data-plan-2253-five-arm-intake.json';selected['data_owner/'+M.name+'/operations/persist_video_code_custody.py']=M/'persist_video_code_custody.py'
for name,source in selected.items():
 dest=G/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(source.read_bytes())
 if dest.suffix=='.py':ast.parse(dest.read_text(),filename=name)
summary={}
for count,expected in [('four',9),('five',11)]:
 n=f'V4-{count}-arm-video-postprocess-46308-20261115-v1';r=json.loads((B/'manifests'/n/'software-fixture-test-result.json').read_bytes());assert r['exit_code']==0 and f'Ran {expected} tests'in r['stderr'];assert all(sha(B/'development'/n/name)==pin for name,pin in r['source_pins'].items());summary[count]=dict(software_tests=expected,exit0=True,source_pins=r['source_pins'],software_fixtures_only=True,no_physical_or_actual_method_qualification=True)
index=G/'data_owner'/M.name/'code-custody-index.json';index.write_text(json.dumps(dict(at=datetime.datetime.now().astimezone().isoformat(),active_main_plan_sha256='26b67d55d0d8d8a6312ac8e19ec85de50f3f753bc8e503aaef8fb0eed20a7e9d',current_comparison_arms=['A','B','C','D','E'],current_task='T-COMPLEX-01-V4-FIVE-ARM',E_can_qualify_and_run_before_WM=True,early_individual_video_delivery_supported=True,four_version_preserved_not_current_full_comparison=True,software=summary,new_V4_zero0_main0_video0=True,native_sources_caps_counts_H_not_changed=True,raw_weights_env_MJB_movies_credentials_and_logs_not_in_Git=True,selected_files={name:sha(p)for name,p in selected.items()}),ensure_ascii=False,indent=2)+'\n')
paths=list(selected)+[str(index.relative_to(G))];git('add','--',*paths);assert set(git('diff','--cached','--name-only').splitlines())==set(paths)and all(p.startswith('data_owner/')and Path(p).suffix in('.py','.md','.json')for p in paths);git('diff','--cached','--check');git('-c','user.name=Data Team Automation','-c','user.email=data-team-automation@localhost','commit','-m','data: implement direct-raw five-arm video with early E-only delivery; preserve native failures');commit=git('rev-parse','HEAD');git('push','origin','HEAD:data-team-development');assert git('ls-remote','origin','refs/heads/data-team-development').split()[0]==commit and not git('status','--porcelain');files={p:sha(G/p)for p in paths}
with(M/'five-video-code-publication.json').open('x')as f:json.dump(dict(at=datetime.datetime.now().astimezone().isoformat(),commit=commit,parent=parent,files=files,GitHub_verified=True,clean=True,native_W_D_H_not_changed=True,logs=logs),f,indent=2);f.write('\n')
bundle=M/'five-video-code.bundle';git('bundle','create',str(bundle),'data-team-development','^c3d8f4ea0cbbdb06c3cea6db50bcba01880569a1');assert bundle.stat().st_size<5*1024**2
code=r'''
from pathlib import Path
import sys,json,base64,hashlib,subprocess
x=json.load(sys.stdin);R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114');G=R/'code/reach-ability-research';M=R/'workspace/manifests/V4-five-arm-video-postprocess-46308-20261115-v1';M.mkdir(exist_ok=True);p=M/'five-video-code.bundle';raw=base64.b64decode(x['bundle']);assert hashlib.sha256(raw).hexdigest()==x['bundle_sha256']
with p.open('xb')as f:f.write(raw)
logs=[]
def git(*a):
 r=subprocess.run(['git',*a],cwd=G,capture_output=True,text=True,timeout=120);logs.append(dict(args=a,exit=r.returncode,stdout=r.stdout,stderr=r.stderr));assert r.returncode==0,r.stderr;return r.stdout.strip()
assert not git('status','--porcelain')and git('rev-parse','HEAD')=='c3d8f4ea0cbbdb06c3cea6db50bcba01880569a1';git('bundle','verify',str(p));git('fetch',str(p),'refs/heads/data-team-development');git('merge','--ff-only','FETCH_HEAD');assert git('rev-parse','HEAD')==x['commit']and not git('status','--porcelain')
for name,pin in x['files'].items():assert hashlib.sha256((G/name).read_bytes()).hexdigest()==pin
print(json.dumps(dict(commit=x['commit'],all_selected_SHA_match=True,H_native_W_D_unmodified=True,clean=True,logs=logs)))
'''
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],input=json.dumps(dict(bundle=base64.b64encode(bundle.read_bytes()).decode(),bundle_sha256=sha(bundle),commit=commit,files=files)),capture_output=True,text=True,timeout=220)
for suffix,text in [('stdout',r.stdout),('stderr',r.stderr),('exit',str(r.returncode)+'\n')]:
 with(M/('five-video-code-deployment.'+suffix)).open('x')as f:f.write(text)
assert r.returncode==0,r.stderr
with(M/'five-video-code-deployment.json').open('x')as f:json.dump(json.loads(r.stdout),f,indent=2);f.write('\n')
print(json.dumps(dict(commit=commit,selected_files=len(files),local_GitHub_remote_verified=True,new_native_or_H_changes=False),indent=2))
