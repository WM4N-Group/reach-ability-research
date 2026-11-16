from pathlib import Path
import json,base64,hashlib,subprocess,shlex,datetime,ast
M=Path(__file__).resolve().parent;B=M.parents[1];W=B/'workers'/M.name;A=Path('/home/yuanyue/main/work/ainav/consumer-deliveries/AINAV-V4-FIVE-ARM-ASSET-E-RULE-AND-CLIMB-GAP-20261115-v1');req=json.loads((A/'E_ONLY_ENTRY59_AND_COLD_TERRAIN_REPAIR_NOT_NATIVE_OR_VIDEO_QUALIFIED.json').read_bytes());sha=lambda b:hashlib.sha256(b).hexdigest();assert req['cloud_commit']=='3ab9383a02bd5eeb1179cb3b273427744c3cb325';raw=(A/'E_ONLY_ENTRY59_AND_COLD_TERRAIN_REPAIR_NOT_NATIVE_OR_VIDEO_QUALIFIED.json').read_bytes();(M/'source59.original.json').write_bytes(raw)
code=r'''
from pathlib import Path
import sys,json,hashlib,base64,shutil,datetime
x=json.load(sys.stdin);R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114');B=R/'workspace';N='V4-E-first-direct-live-46308-20261116-v1';W=B/'workers'/N;M=B/'manifests'/N;assert not W.exists()and not M.exists();W.mkdir();M.mkdir();V=Path(x['request']['remote_owned_root'])/'ainav/development/complex_v4_four_arm_v1';parent=V.parent/'complex_dual_route_v1';files={}
for folder,names in [(V,x['request']['source_files_sha256']),(parent,{n:hashlib.sha256((parent/n).read_bytes()).hexdigest()for n in ['native_construction.py','complex_scene.py','camera_abi.py','semantic_factory.py','multi_goal_factory.py','terminal_stop.py','scene_driver.py']})]:
 for name,pin in names.items():
  p=folder/name;raw=p.read_bytes();assert not p.is_symlink()and hashlib.sha256(raw).hexdigest()==pin;dest=W/'inputs/ainav/development'/folder.name/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw);files[str(dest.relative_to(W))]=base64.b64encode(raw).decode()
print(json.dumps(dict(files=files,ffmpeg_sha256=hashlib.sha256(Path('/usr/bin/ffmpeg').read_bytes()).hexdigest(),source59_SHA_verified=True,no_H_or_native_call=True)))
'''
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],input=json.dumps(dict(request=req)),capture_output=True,text=True,timeout=90);assert r.returncode==0,r.stderr;v=json.loads(r.stdout)
for name,b64 in v.pop('files').items():
 p=W/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(base64.b64decode(b64))
C=dict(schema='Data-E-first-original-rule-full-V4-goal-and-direct-live-v1',scope_id='data-46308-V4-E-first-direct-live-20261116-v1',source_commit=req['cloud_commit'],source_record_sha256=sha(raw),plan_sha256=sha(Path('/home/yuanyue/main/汇总/各小组下一步研究计划.md').read_bytes()),scene_sha256='6394740eb54b99ec0e0b4b35b0f804e7875dfc29255d9f897ba57b1ac0b48d20',model_path='/mnt/yuanyue/data-team/deployments/46308-20261114/runtime/workers/data-46308-V4-common-palette-bounded-native-20261116-v2/complex-static-new-palette.mjb',model_sha256='a89119217e1aa18ec344ce63f55fceb69806a07c47cf56c2ac79a9f6d7959e87',GPU_UUID='GPU-297c1146-bcec-a8ee-8437-d9603392a2e1',own_GPU_cap_bytes=3*1024**3,own_RSS_cap_bytes=4*1024**3,output_cap_bytes=1024**3,zero_wall_cap_s=300,main_wall_cap_s=36000,main_task_sim_cap_s=600,main_task_step_cap=120000,own_zero_max=1,main_max=1,E_selection_max64=True,VLM_WM_fit_calls_allowed=0,known_original_policy_refusal_at_rise040_not_blind_CLIMB_call=True,no_layout_height_or_skill_guard_change=True,no_prior_complete_E_success_required=True,no_component_as_E_main=True,ffmpeg_path='/usr/bin/ffmpeg',ffmpeg_sha256=v['ffmpeg_sha256'],camera_candidates=[dict(kind='fixed_free',width=1280,height=720,stride_physics_ticks=20,chunk_frames=16,max_bytes=512*1024**2,lookat=look,distance=dist,azimuth=110.,elevation=-58.)for look,dist in [([6.5,0.,.2],18.),([7.5,0.,.4],20.)]],camera_choice_in_required_task0_zero_only=True,frame_private_evidence_not_model_input=True,known_actual_prefix_cost_basis='closed af09:2151.132wall/2570 native preparation commands; cap is finite not completion promise; fresh scandir I/O guard preserves every-call sums, no cached budget',no_other_arm_WM_J_or_extra_component_wait=True)
assert C['plan_sha256']=='7559f685a72fbbfb3dae6d95c5cb35660116670f2c8bb1c523c0690c69f9bbec';(W/'protocol.json').write_text(json.dumps(C,ensure_ascii=False,indent=2)+'\n')
files={str(p.relative_to(W)):base64.b64encode(p.read_bytes()).decode()for p in W.glob('*')if p.is_file()}
code=r'''
from pathlib import Path
import sys,json,base64
W=Path('/mnt/yuanyue/data-team/deployments/46308-20261114/workspace/workers/V4-E-first-direct-live-46308-20261116-v1')
for n,b64 in json.load(sys.stdin).items():
 raw=base64.b64decode(b64)
 with(W/n).open('xb')as f:f.write(raw)
 if n.endswith('.py'):compile(raw,str(W/n),'exec')
print('staged')
'''
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],input=json.dumps(files),capture_output=True,text=True,timeout=60);assert r.returncode==0,r.stderr
C.update(own_zero_required=True,allowed_zero1_main1=True,zero_wall_cap_s=300.,main_wall_cap_s=36000.,main_task_sim_cap_s=600.,main_task_step_cap=120000,output_cap_bytes=1024**3,ffmpeg_path='/usr/bin/ffmpeg',ffmpeg_sha256=v['ffmpeg_sha256'],cameras=[dict(kind='fixed_free',width=1280,height=720,stride_physics_ticks=20,chunk_frames=16,max_bytes=512*1024**2,lookat=[6.5,0.,.2],distance=18.,azimuth=110.,elevation=-58.),dict(kind='fixed_free',width=1280,height=720,stride_physics_ticks=20,chunk_frames=16,max_bytes=512*1024**2,lookat=[7.5,0.,.4],distance=20.,azimuth=110.,elevation=-58.)],fixed_E_rule_sha256=req['real_unchanged_E_rule_sha256'],E_max_selections=64,known_040rise_original_rule_may_refuse_before_unsupported_call=True,no_world_replay_or_layout_lowering_or_NN_gate_change=True)
(W/'protocol.json').write_text(json.dumps(C,ensure_ascii=False,indent=2)+'\n')
with(M/'source-staging-proof.json').open('x')as f:json.dump(v,f,indent=2);f.write('\n')
print(json.dumps(dict(source59_staged=True,Data_files=len(files),no_H_or_native=True)))
