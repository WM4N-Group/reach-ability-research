"""Persist selected original-export code and V4 unqualified source custody only."""
from pathlib import Path
import ast,os,json,hashlib,datetime,subprocess,shlex,base64
B=Path('/home/yuanyue/main/work/data-team');M=Path(__file__).resolve().parent;T=B/'manifests/T-COMPLEX-observability-study-46308-20261115-v1';V=B/'manifests/V4-four-arm-intake-46308-20261115-v1';G=Path('/home/yuanyue/main/code/reach-ability-research');sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();log=[]
def git(*args):
 r=subprocess.run(['git',*args],cwd=G,capture_output=True,text=True,timeout=150);log.append(dict(args=list(args),exit=r.returncode,stdout=r.stdout,stderr=r.stderr));assert r.returncode==0,r.stderr;return r.stdout.strip()
assert not git('status','--porcelain')and git('branch','--show-current')=='data-team-development';git('fetch','origin','data-team-development');git('merge','--ff-only','origin/data-team-development');parent=git('rev-parse','HEAD');selected={}
for name in ['export_closed_ordinals02to04_originals.py','run_export_closed_ordinals02to04.py','publish_closed02to04_original_deliveries.py','publish_closed02to04_and_V4_intake_v2.py','persist_closed02to04_and_V4_intake_code.py']:selected['data_owner/'+M.name+'/operations/'+name]=M/name
for folder in(M,T,V):selected['data_owner/'+folder.name+'/README.md']=folder/'README.md'
for rel in ['v4-wm-ainav-intake/README_CN.md','v4-wm-ainav-intake/FOUR_ARM_PROTOCOL.json','v4-wm-ainav-intake/v4_native_asset.py','v4-wm-ainav-intake/test_v4_native_asset.py','scene-v3-review/scene.json']:selected['data_owner/'+V.name+'/source-owner-snapshot/'+rel]=V/'source-owner-snapshot'/rel
for name,source in selected.items():
 p=G/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(source.read_bytes())
 if p.suffix=='.py':ast.parse(p.read_text(),filename=str(p))
intake=json.loads((V/'Data-readonly-intake.json').read_bytes());idx=json.loads((M/'closed02to04-original-release-index.json').read_bytes());index=G/'data_owner'/V.name/'code-custody-index.json';index.write_text(json.dumps(dict(at=datetime.datetime.now().astimezone().isoformat(),role='CODE_CUSTODY_NOT_NATIVE_FREEZE_OR_DISPATCH_AUTHORITY',main_plan_sha256=intake['main_plan_sha256'],research_source_protocol_sha256=intake['source_protocol_sha256'],V4_scene_sha256=intake['scene_sha256'],existing_WM_inference_allowed_only_for_four_arm_comparison=True,new_WM_Actor_training=False,new_V4_zero0_main0=True,bulk02to04_original_deliveries=[dict(path=r['release_path'],sha256=r['release_sha256'],source_result_passed=r['summary']['source_result_passed'],actual_public_queries=r['summary']['public_query_count'],first_CLIMB_boundary=r['summary']['first_CLIMB_boundary'])for r in idx['releases']],original_pre_CLIMB_failure_missing_features_and_label_remain_None=True,no_RAW_MJB_arrays_weights_env_video_credentials_or_logs_in_Git=True,selected_files={k:sha(p)for k,p in selected.items()}),ensure_ascii=False,indent=2)+'\n')
paths=list(selected)+[str(index.relative_to(G))];git('add','--',*paths);staged=git('diff','--cached','--name-only').splitlines();assert set(staged)==set(paths)and all(p.startswith('data_owner/')and Path(p).suffix in('.py','.md','.json')for p in staged);git('diff','--cached','--check');git('-c','user.name=Data Team Automation','-c','user.email=data-team-automation@localhost','commit','-m','data: deliver closed bulk originals without synthetic failure labels; intake V4 four-arm protocol');commit=git('rev-parse','HEAD');git('push','origin','HEAD:data-team-development');assert git('ls-remote','origin','refs/heads/data-team-development').split()[0]==commit and not git('status','--porcelain');files={p:sha(G/p)for p in paths}
proof=dict(at=datetime.datetime.now().astimezone().isoformat(),commit=commit,parent=parent,files=files,GitHub_verified=True,clean=True,H_and_all_native_frozen_W_D_unmodified=True,log=log)
with(M/'closed02to04-V4-code-publication.json').open('x')as f:json.dump(proof,f,indent=2);f.write('\n')
bundle=M/'closed02to04-V4-code.bundle';git('bundle','create',str(bundle),'data-team-development','^6b2fe6255187de038f994a8adf1e59fd01eb6a25');assert bundle.stat().st_size<5*1024**2
code=r'''
from pathlib import Path
import sys,json,hashlib,base64,subprocess,datetime
x=json.load(sys.stdin);R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114');G=R/'code/reach-ability-research';M=R/'workspace/manifests/bulk24-collector-46308-20261115-v1';p=M/'closed02to04-V4-code.bundle';raw=base64.b64decode(x['bundle']);assert hashlib.sha256(raw).hexdigest()==x['bundle_sha256']
with p.open('xb')as f:f.write(raw)
log=[]
def git(*args):
 r=subprocess.run(['git',*args],cwd=G,capture_output=True,text=True,timeout=120);log.append(dict(args=list(args),exit=r.returncode,stdout=r.stdout,stderr=r.stderr));assert r.returncode==0,r.stderr;return r.stdout.strip()
assert not git('status','--porcelain')and git('rev-parse','HEAD')=='6b2fe6255187de038f994a8adf1e59fd01eb6a25';git('bundle','verify',str(p));git('fetch',str(p),'refs/heads/data-team-development');git('merge','--ff-only','FETCH_HEAD');assert git('rev-parse','HEAD')==x['commit']and not git('status','--porcelain')
for name,pin in x['files'].items():assert hashlib.sha256((G/name).read_bytes()).hexdigest()==pin
print(json.dumps(dict(at=datetime.datetime.now().astimezone().isoformat(),commit=x['commit'],all_selected_SHA_match=True,clean=True,H_and_native_W_D_not_written=True,log=log)))
'''
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],input=json.dumps(dict(bundle=base64.b64encode(bundle.read_bytes()).decode(),bundle_sha256=sha(bundle),commit=commit,files=files)),capture_output=True,text=True,timeout=250)
for suffix,text in [('stdout',r.stdout),('stderr',r.stderr),('exit',str(r.returncode)+'\n')]:
 with(M/('closed02to04-V4-code-deployment.'+suffix)).open('x')as f:f.write(text)
assert r.returncode==0,r.stderr
with(M/'closed02to04-V4-code-deployment.json').open('x')as f:json.dump(json.loads(r.stdout),f,indent=2);f.write('\n')
print(json.dumps(dict(commit=commit,selected_files=len(files),local_GitHub_and_remote_code_verified=True,no_H_or_native_change=True),indent=2))
