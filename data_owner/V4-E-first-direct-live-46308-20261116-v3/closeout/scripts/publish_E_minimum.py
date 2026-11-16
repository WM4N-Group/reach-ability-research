from pathlib import Path
import json,hashlib,datetime,shutil,subprocess,base64,shlex
B=Path('/home/yuanyue/main/work/data-team');M=B/'manifests/V4-E-first-direct-live-46308-20261116-v3';X=json.loads((M/'closeout-readonly-export.json').read_bytes());name='AINAV-DATA-E-FIRST-FULL-V4-ATTEMPT-STOW-PLACEMENT-REJECTED-DIRECT-LIVE-20261116-v1';D=B/'consumer-deliveries'/name;D.mkdir();sha=lambda b:hashlib.sha256(b).hexdigest();r=json.loads((M/'original-closeout/main/result.json').read_bytes());l=json.loads((M/'original-closeout/main/ledger.json').read_bytes());z=json.loads((M/'original-closeout/zero/ledger.json').read_bytes());enc=json.loads((M/'original-closeout/main/video-encoding-result.json').read_bytes());now=datetime.datetime.now().astimezone().isoformat()
for rel in X['original_files']:
 p=D/'original'/rel;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(M/'original-closeout'/rel,p)
proof=dict(at=X['at'],H_sha256=X['H_sha256'],H_scope=X['H_scope'],video=X['video'],event_counts=X['event_counts'],selected_original_events=X['selected_original_events'],last_original_samples=X['last_original_samples'],locks=X['locks'],owned_bytes=X['owned_bytes'],owned_limit_bytes=X['owned_limit_bytes'],provider_quota_unknown=True,no_native_or_renderer_or_physics_run=True,no_full_command_PD_FIFO_cold_audit_claim_yet=True)
(D/'minimum-readonly-verification.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n')
readme=f'''# E完整V4目标首次真实尝试：失败原片先交（不等待完整cold）

发布时间：{now}。

- 真实E固定RuleBaseline；source `{r['source_commit']}`；program `{r['program_sha256']}`。独立fresh scope `{r['scope_id']}`，own-zero1/main1已closed，不重开。
- 完整任务**未成功**：准备NAV在3018tick/15.090sim原生succeeded；首cuboid_a PUSH在3019tick/15.095sim真实started。9719tick/48.595sim，原`placement_handoff.py:207`于protected stow完成后的placement复核拒绝：`{r['error']}`。后续箱子、CLIMB、高台均未到达。
- 保留PushSettled NN内部true与任务placement不合格的区别；无该PUSH的原生succeeded/failed终态回执，不补技能负标签。最后原采样48.590sim的XY误差0.0377186312m、signed dock gap -0.0365852129m、placement_geometry_verified=false，来自隔离证据，不能喂在线planner。没有单独归因某算法或几何漂移原因。
- main实际9719条200Hz命令、48.595sim、9382.502520127wall、486机载帧，resource_censored=false/usage_known=true/close_errors=[]。录制器原episode.censored=true保持，指调用方异常截断，不能覆盖为资源watchdog或native failed。own-zero额外19.590225650wall及6.505auxsim；main另有6.505auxsim。费用非货币账单；旧v1/v2前置错误成本/旧closed失败不清零。
- VLM0/WM0/fit0/新后继选择0；共有legacy H本次attempt1/completed1/changed1真实计入，不能把E说成所有算法均0，不推B/D增益。

## 完整原片

- 远端：`{enc['video_path']}`。
- 本机小副本：`{M/'E-direct-live-1x.mp4'}`（{X['video']['bytes']} bytes，非批量raw迁移）。
- SHA256 `{enc['video_sha256']}`；1280×720、10Hz、486帧、1×、MP4约48.6s。任务终态时钟48.595sim来自原event/result，不从片长推断。采样grid末帧9700tick/48.5sim，覆盖完整事前10Hz grid；未补造9719tick画面。
- 从task0直接live MuJoCo RGB保存，31个raw chunk/486帧逐SHA核，原master留远端；非状态回放、非重渲染、无resize/插帧/成功剪辑。只对已存原RGB作H264编码。母版closure中的encoded_video_created=false是编码前原记录，实际编码见独立video-encoding-result.json，不回写原件。
- ffprobe实际尺寸/FPS/解码486帧通过；解码48秒帧QA是原MP4解码，不是Runtime重渲染。固定广角覆盖狗、三箱和高台，狗臂相对很小，不能假称可看清臂细节或用裁切放大冒另一原相机。

## 完成边界与下一步

这是完整目标的真实**失败尝试及从开始至失败的原片**，不是全链成功、不是五组完成或方法排名。E先行DEV暴露保持，后续不得据此调四组又冒未见公平对照。

原件最少结果/视频已闭合；完整200Hz/FIFO/PD cold尚未完成，不能先宣称通过。AINav应依据原源码/placement合同与末段真实记录定位stow后placement不合格；Data后续只读补cold/成本，不降低阈值、不热改/重跑本scope，不替Reach写优化器。若需新共同修复/新实验，另行登记问题/版本/用途/限额，不换ID盲重试。compute仍46308；旧46174只按具体资料缺口只读，本次未连接。
'''
(D/'README_CN.md').write_text(readme)
files={str(p.relative_to(D)):sha(p.read_bytes())for p in sorted(D.rglob('*'))if p.is_file()}
release=dict(schema='Data-E-first-full-V4-goal-real-attempt-minimum-result-and-complete-direct-live-v1',at=now,scope_id=r['scope_id'],source_commit=r['source_commit'],program_sha256=r['program_sha256'],result_sha256=l['result_sha256'],full_task_success=False,task_stop_reason=r['error'],resource_censored=False,original_episode_recorder_censored=r['episode_closure']['censored'],PUSH_native_terminal_label=None,first_PUSH_started=True,PUSH_semantic_successes=0,CLIMB_invocations=0,high_platform_success=False,actual_task_commands=9719,actual_task_sim_s=r['actual_task_sim_s'],main_wall_s=l['wall_s'],technical_zero_wall_s=z['wall_s'],v3_zero_plus_main_wall_s=l['wall_s']+z['wall_s'],v3_zero_plus_main_aux_sim_s=l['actual_aux_sim_s']+z['actual_aux_sim_s'],main_output_bytes_original_ledger=l['output_bytes'],usage_known=True,close_errors=r['close_errors'],VLM_calls=0,WM_calls=0,fit_calls=0,factor_counts=r['factor_counts'],direct_video=enc,video_file_bytes=X['video']['bytes'],raw_chunks31_verified=True,raw_frames486_verified=True,full_stream_cold_audit='PENDING_NOT_A_PRECONDITION_FOR_FIRST_MINIMUM_DELIVERY',own_zero_calls=1,E_main_calls=1,automatic_retry=False,scope_closed=True,E_first_DEV_exposure=True,training_allowed=False,model_input_allowed=False,current_plan_sha256=sha(Path('/home/yuanyue/main/汇总/各小组下一步研究计划.md').read_bytes()),files=files)
(D/'release.json').write_text(json.dumps(release,ensure_ascii=False,indent=2)+'\n')
payload={str(p.relative_to(D)):base64.b64encode(p.read_bytes()).decode()for p in D.rglob('*')if p.is_file()};code=r'''
from pathlib import Path
import sys,json,base64,hashlib
x=json.load(sys.stdin);D=Path('/mnt/yuanyue/data-team/deployments/46308-20261114/workspace/consumer-deliveries')/x['name'];assert not D.exists();D.mkdir()
for rel,v in x['files'].items():
 p=D/rel;assert p.resolve().is_relative_to(D);p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb')as f:f.write(base64.b64decode(v))
r=json.loads((D/'release.json').read_bytes())
for rel,pin in r['files'].items():assert hashlib.sha256((D/rel).read_bytes()).hexdigest()==pin
print(json.dumps(dict(remote_release=str(D/'release.json'),release_sha256=hashlib.sha256((D/'release.json').read_bytes()).hexdigest(),all_files_SHA_match=True,no_runtime_source_H_or_closed_result_mutation=True)))
'''
a=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],input=json.dumps(dict(name=name,files=payload)),capture_output=True,text=True,timeout=60);assert a.returncode==0,a.stderr;receipt=json.loads(a.stdout);assert receipt['release_sha256']==sha((D/'release.json').read_bytes());(M/'minimum-result-video-release-proof.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n');print(json.dumps(dict(local_release=str(D/'release.json'),**receipt),ensure_ascii=False,indent=2))
