"""Publish additive evidence only; never mutate old release, H, frozen code or runtime."""
from pathlib import Path
import json,hashlib,datetime,base64,subprocess,shlex
B=Path('/home/yuanyue/main/work/data-team');M=Path(__file__).resolve().parent;A=M/'cold-audit-v1.json';a=json.loads(A.read_bytes());assert all(a['cold_checks'].values())and not a['original_task_passed'];sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();D=B/'consumer-deliveries/AINAV-DATA-E59-CLOSED-STREAM-COLD-PASS-NNSTOP-FIRST-PLACEMENT-LOSS-20261116-v1';D.mkdir();(D/'original-stream-cold-audit.json').write_bytes(A.read_bytes())
prior=B/'consumer-deliveries/AINAV-DATA-E-FIRST-FULL-V4-ATTEMPT-STOW-PLACEMENT-REJECTED-DIRECT-LIVE-20261116-v1/release.json';assert sha(prior)=='13082992532fe8b8ae537671129121d7558312d7d715a6a7a4f9257864d9269a'
text=f'''# 原E59 closed只读完整数据流cold补充：通过不改任务失败

原最少结果与完整1×视频早先已交，release `{sha(prior)}` 不回写。此补充不增加物理次数，不恢复world。

## 完整性

515 frozen source/asset成员逐SHA核；4711行原journal完整序列/哈希链；9719条200Hz命令/原4步FIFO完全一致；原PD raw和硬effort clip最大重现误差均0；486机载RGBD帧前一动作/时间grid通过。31个1280×720 raw chunk/486帧解压核像素SHA、dtype/shape、实际tick/时间，10Hz完整事前grid通过。所有原scope文件及H在只读audit前后SHA相同，close_errors0。audit本身为CPU/NumPy只读{a['CPU_readonly_audit_wall_s']:.6f}s，不计新task或免费抹去其开销；不导入Runtime/Actor/MuJoCo/Renderer/WM。

## 准确首次失格，不误归因收臂/H

- sequence2500，26.570sim：placement首次合格，XY误差8.8551mm、signed dock gap +3.4623mm。
- sequence2503，26.590sim：进入NN_STOP_MOVING_PUSH时仍合格。
- **sequence2507，26.630sim：NN_STOP_MOVING_PUSH内首次再次失格**，距首次合格仅60ms；XY14.6202mm、signed gap −13.7201mm。之后原测量未恢复合格。
- 原NN在27.210sim内部确认，不等task placement合格。29.390 BRAKE_MOVING_PUSH及30.210 UNLOAD_CAPTURE已在失格状态；32.910才进入PROTECTED_STOW，早于它的legacy H首attempt为sequence3137；44.610进入STOW_VERIFY。
- **48.595sim**才在原placement_handoff.py:207于保护收臂完成后的复核抛异常。`lost after stow`是原报错位置，不是首次越界发生时刻；不能把已有失格倒归因于后面的H路径选择。末48.590sim XY37.7186mm、signed gap −36.5852mm；具体动态/接触原因尚未仅凭此timeline确定。

## 标签与后续

任务仍未成功，原PUSH terminal=None、CLIMB0；NN true/数据流通过都不补完整PUSH成功/failed标签或成功cost。resource_censored=false与原recorder.censored=true分别保持。原E DEV暴露/用途、旧v1/v2元数据错误、原费用、其它closed失败全部保留；无V-JEPA/WM训练准入。

下一项由AINav定位arrival→NN_STOP的原动作/FIFO/卸载接触；Data维护这份真实证据和下一版完整同门计时，不降低成功/安全门、不单纯降高或提速后换ID盲试、不重跑本scope。最少视频和正式补充均可先独立消费，不待A—D/WM/VLM/J。
'''
(D/'README_CN.md').write_text(text);files={str(p.relative_to(D)):sha(p)for p in D.iterdir()if p.is_file()};release=dict(schema='Data-E59-closed-original-cold-PASS-task-failure-unchanged-placement-loss-timeline-v1',at=datetime.datetime.now().astimezone().isoformat(),scope_id=a['scope_id'],source_commit=a['source_commit'],program_sha256=a['program_sha256'],original_result_sha256=a['original_result_sha256'],prior_minimum_release_sha256=sha(prior),full_task_success=False,native_PUSH_terminal_label=None,resource_censored=False,recorder_censored_original=True,cold_checks=a['cold_checks'],all_frozen_members=515,journal_rows=4711,commands=9719,onboard_frames=486,raw_frames=486,max_raw_PD_error=0,max_clip_error=0,first_placement_pass=a['first_placement_pass'],first_loss_after_pass=a['first_loss_after_pass'],loss_precedes_legacy_H_selection=True,physical_zero_count_unchanged=1,physical_main_count_unchanged=1,no_simulation_replay_recovery_or_automatic_retry=True,all_original_bytes_and_H_unchanged=True,training_allowed=False,model_input_allowed=False,files=files);(D/'release.json').write_text(json.dumps(release,ensure_ascii=False,indent=2)+'\n')
code=r'''
from pathlib import Path
import json,sys,base64,hashlib
x=json.load(sys.stdin);D=Path('/mnt/yuanyue/data-team/deployments/46308-20261114/workspace/consumer-deliveries')/x['name'];assert not D.exists();D.mkdir()
for rel,v in x['files'].items():
 p=D/rel;assert p.resolve().is_relative_to(D);p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb')as f:f.write(base64.b64decode(v))
r=json.loads((D/'release.json').read_bytes())
for rel,pin in r['files'].items():assert hashlib.sha256((D/rel).read_bytes()).hexdigest()==pin
print(json.dumps(dict(remote_release=str(D/'release.json'),release_sha256=hashlib.sha256((D/'release.json').read_bytes()).hexdigest(),all_files_SHA_match=True,no_closed_runtime_source_H_or_old_release_mutation=True)))
'''
x=dict(name=D.name,files={str(p.relative_to(D)):base64.b64encode(p.read_bytes()).decode()for p in D.iterdir()if p.is_file()});r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],input=json.dumps(x),capture_output=True,text=True,timeout=60);assert r.returncode==0,r.stderr;p=json.loads(r.stdout);assert p['release_sha256']==sha(D/'release.json');(M/'cold-addendum-publication-proof.json').write_text(json.dumps(p,ensure_ascii=False,indent=2)+'\n');print(json.dumps(dict(local_release=str(D/'release.json'),**p),ensure_ascii=False,indent=2))
