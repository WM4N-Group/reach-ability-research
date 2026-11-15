"""Persist exact new component source and small role/resource metadata only."""
from pathlib import Path
import ast,json,hashlib,datetime,subprocess,shlex,base64
B=Path('/home/yuanyue/main/work/data-team');M=Path(__file__).resolve().parent;W=B/'workers'/M.name;K=B/'manifests/bulk24-collector-46308-20261115-v1';J=B/'manifests/V-JEPA-J1-resource-response-46308-20261116-v1';G=Path('/home/yuanyue/main/code/reach-ability-research');sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();logs=[]
def git(*a):
 r=subprocess.run(['git',*a],cwd=G,capture_output=True,text=True,timeout=150);logs.append(dict(args=a,exit=r.returncode,stdout=r.stdout,stderr=r.stderr));assert r.returncode==0,r.stderr;return r.stdout.strip()
assert not git('status','--porcelain')and git('branch','--show-current')=='data-team-development';git('fetch','origin','data-team-development');git('merge','--ff-only','origin/data-team-development');parent=git('rev-parse','HEAD');selected={}
for p in W.rglob('*'):
 if p.is_file()and'__pycache__'not in p.parts and p.suffix in('.py','.json','.md'):selected['data_owner/'+M.name+'/worker/'+str(p.relative_to(W))]=p
for p in M.glob('*.py'):selected['data_owner/'+M.name+'/operations/'+p.name]=p
for folder in(M,K,J):selected['data_owner/'+folder.name+'/README.md']=folder/'README.md'
for name in ['Data-J1-received-and-low-priority-window.json','Data-resource-window-license-precondition-addendum.json']:
 selected['data_owner/'+J.name+'/'+name]=J/name
for name,source in selected.items():
 p=G/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(source.read_bytes())
 if p.suffix=='.py':ast.parse(p.read_text(),filename=name)
proof=json.loads((M/'component-original-release-proof.json').read_bytes());q=json.loads((B/'registry/handoff_46308_current_status_20261115.json').read_bytes())['active_V4_native_component_scope'];assert not q['active']and q['component_zero_dispatch_count']==1 and q['task_main_dispatch_count']==0
name='data_owner/'+M.name+'/actual-component-code-custody-index.json';p=G/name;p.write_text(json.dumps(dict(at=datetime.datetime.now().astimezone().isoformat(),role='CLOSED_COMPONENT_CODE_CUSTODY_NOT_A_RELAUNCH_OR_MAIN_AUTHORITY',source_commit='04f26c0c15a9100f5d2359fd395dc33135673b82',source_program_sha256='b125b188c6e250c9de68b35f42b4dd146cd70cad9ac4a73b220251dd9f8e0096',component_zero1_PASS_closed=True,five_arm_main_calls=0,actual_release_path=proof['release_path'],actual_release_sha256=proof['release_sha256'],original_MJB_NPZ_PNG_videos_weights_ENV_credentials_and_logs_not_in_Git=True,original_robot_engine_and_control_guards_unchanged=True,camera_ABI_and_resolution_not_final_framing_or_FPS_qualification=True,original_1280x720_frame_QA_pointer=str(M/'world0-preview-visual-QA.json'),single_local_orchestrator_gate_not_remote_GPU1_pause=True,new_J1_response_not_GPU_or_current_dataset_lease=True,checkpoint_independent_license_precondition_not_asserted_complete=True,selected_code_files={n:sha(p)for n,p in selected.items()}),ensure_ascii=False,indent=2)+'\n');paths=list(selected)+[name];git('add','--',*paths);assert set(git('diff','--cached','--name-only').splitlines())==set(paths)and all(p.startswith('data_owner/')and Path(p).suffix in('.py','.md','.json')for p in paths);git('diff','--cached','--check');git('-c','user.name=Data Team Automation','-c','user.email=data-team-automation@localhost','commit','-m','data: qualify actual V4 asset cold-runtime zero once; preserve bulk concurrency and bound J1 CPU window');commit=git('rev-parse','HEAD');git('push','origin','HEAD:data-team-development');assert git('ls-remote','origin','refs/heads/data-team-development').split()[0]==commit and not git('status','--porcelain');files={n:sha(G/n)for n in paths}
with(M/'actual-component-code-publication.json').open('x')as f:json.dump(dict(at=datetime.datetime.now().astimezone().isoformat(),commit=commit,parent=parent,files=files,GitHub_verified=True,clean=True,no_closed_program_or_H_mutation=True,logs=logs),f,indent=2);f.write('\n')
bundle=M/'actual-component-code.bundle';git('bundle','create',str(bundle),'data-team-development','^5feb26c462774552e68b15448202c206ca34b793');assert bundle.stat().st_size<5*1024**2
code=r'''
from pathlib import Path
import sys,json,base64,hashlib,subprocess
x=json.load(sys.stdin);R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114');G=R/'code/reach-ability-research';M=R/'workspace/manifests/V4-native-components-46308-20261116-v1';p=M/'actual-component-code.bundle';raw=base64.b64decode(x['bundle']);assert hashlib.sha256(raw).hexdigest()==x['bundle_sha256']
with p.open('xb')as f:f.write(raw)
logs=[]
def git(*a):
 r=subprocess.run(['git',*a],cwd=G,capture_output=True,text=True,timeout=120);logs.append(dict(args=a,exit=r.returncode,stdout=r.stdout,stderr=r.stderr));assert r.returncode==0,r.stderr;return r.stdout.strip()
assert not git('status','--porcelain')and git('rev-parse','HEAD')=='5feb26c462774552e68b15448202c206ca34b793';git('bundle','verify',str(p));git('fetch',str(p),'refs/heads/data-team-development');git('merge','--ff-only','FETCH_HEAD');assert git('rev-parse','HEAD')==x['commit']and not git('status','--porcelain')
for name,pin in x['files'].items():assert hashlib.sha256((G/name).read_bytes()).hexdigest()==pin
print(json.dumps(dict(commit=x['commit'],all_selected_SHA_match=True,clean=True,H_and_original_closed_native_program_not_written=True,logs=logs)))
'''
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],input=json.dumps(dict(bundle=base64.b64encode(bundle.read_bytes()).decode(),bundle_sha256=sha(bundle),commit=commit,files=files)),capture_output=True,text=True,timeout=220)
for suffix,text in [('stdout',r.stdout),('stderr',r.stderr),('exit',str(r.returncode)+'\n')]:
 with(M/('actual-component-code-deployment.'+suffix)).open('x')as f:f.write(text)
assert r.returncode==0,r.stderr
with(M/'actual-component-code-deployment.json').open('x')as f:json.dump(json.loads(r.stdout),f,indent=2);f.write('\n')
print(json.dumps(dict(commit=commit,selected_files=len(files),local_GitHub_remote_verified=True,no_original_closed_program_H_or_guard_mutations=True),indent=2))
