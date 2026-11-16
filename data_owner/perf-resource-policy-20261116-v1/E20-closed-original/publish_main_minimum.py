from pathlib import Path
import json,hashlib,datetime,subprocess,shlex,base64
B=Path('/home/yuanyue/main/work/data-team');M=Path(__file__).resolve().parent;X=json.loads((M/'closed-main-minimum-export.json').read_bytes());O=M/'original-main-closeout';r=json.loads((O/'main/result.json').read_bytes());l=json.loads((O/'main/ledger.json').read_bytes());enc=json.loads((O/'main/video-encoding-result.json').read_bytes());sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();D=B/'consumer-deliveries/AINAV-DATA-E20-40MM-ACTUAL-ENTRY-NATIVE-CONFIRMATION-LOST-COMPLETE-VIDEO-20261116-v1';D.mkdir()
for rel in X['original_files']:
 p=D/'original'/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((O/rel).read_bytes())
summary={k:v for k,v in X.items()if k!='original_files'};(D/'minimum-readonly-verification.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n');(D/'README_CN.md').write_text(f'''# E20/40mm唯一动态main失败与完整1×原片：先交最少结果

scope {r['scope_id']}；source04a9c0fe…/program39ef86d5…/asseted6267bb…。own-zero1/main1已closed，原准入/相机/NN/安全门不热改、不重跑。此为三箱+C箱顶20cm的DEV，不是原.60m高台成功或五组胜出。

原NAV15.090 succeeded、首PUSH15.095 started。**26.470sim真实触发单点40mm提前原brake**（gap34.992mm），geometry仍false，未伪标到位。27.190sim原内部NN clock确认true/0.5s，但placement仍false（XY31.810mm/gap−30.993mm）；**27.410sim/5482tick原confirmation丢失硬停**：`{r['error']}`。PUSH无复合succeeded/failed终态回执，保持None，CLIMB/后箱0、共有H attempt0；不由异常补技能负类，也不宣称更早触发已修复问题。40mm dynamic family main合计1，不扫margin/换seed追胜。

完整现场原片：`{enc['video_path']}`；本机仅196166bytes副本`{M/'E20-direct-live-1x.mp4'}`。SHA {enc['video_sha256']}，1280×720/10Hz/275帧/1×约27.5s；18 raw chunks逐SHA、ffprobe实际解码275帧通过。原母版保留，非状态回放/重渲染/插帧/成功剪辑。最后grid画面5480tick/27.400sim，真实终态27.410来自原result/event，不从片长推任务时间。完整FIFO/PD冷审尚未补，不冒已全流通过。

main原成本5482命令/27.410task+6.505aux sim/**3522.131102207wall**，usage_known=true、resource_censored=false、close0、峰值RSS2286088192bytes/GPU810549248bytes。own-zero另18.663792928wall+6.505auxsim；新静态资产编译11.758566817wall，旧5a静态失败10.479544644wall、Data v2漏privacy-helper的zero授权1/Runtime0/main0及未知wall/RSS全部保留，不合成免费0/项目总费。原episode.censored=true为异常截断，不改成资源watchdog。

原loaded路径/目录策略未动：15926002次路径出现请求、10968 path pass，resolve2121.001589334s（非内核I/O次数）；Data guard1163.920884856s含size281.162020663s，原driver3432.376559024s，这些包含/重叠不能相加。新19:35计划02dc65ed…已接：下一项先改静态/资源审计热循环，只做新源/离线资格后独立性能验证，不再新增E/五组/bulk先排、不热改此closed run。
''');files={str(p.relative_to(D)):sha(p)for p in D.rglob('*')if p.is_file()};rel=dict(schema='Data-E20-40mm-actual-entry-confirmation-lost-minimum-closeout-and-complete-video-v1',at=datetime.datetime.now().astimezone().isoformat(),scope_id=r['scope_id'],source_commit=r['source_commit'],program_sha256=r['program_sha256'],result_sha256=l['result_sha256'],full_task_success=False,error=r['error'],resource_censored=False,native_PUSH_terminal_label=None,actual_early_brake_entry_sim_s=26.47,original_NN_true_sim_s=27.19,actual_stop_sim_s=r['actual_task_sim_s'],actual_commands=r['actual_task_steps'],main_wall_s=r['wall_s'],own_zero_calls=1,main_calls=1,total40mm_dynamic_main_calls=1,automatic_retry=False,scope_closed=True,video=enc,raw_chunks18_SHA_verified=True,ffprobe275_frames_passed=True,full_command_FIFO_PD_cold='PENDING_NOT_A_FIRST_DELIVERY_GATE',training_allowed=False,model_input_allowed=False,files=files);(D/'release.json').write_text(json.dumps(rel,ensure_ascii=False,indent=2)+'\n')
code=r'''
from pathlib import Path
import sys,json,base64,hashlib
x=json.load(sys.stdin);D=Path('/mnt/yuanyue/data-team/deployments/46308-20261114/workspace/consumer-deliveries')/x['name'];assert not D.exists();D.mkdir()
for rel,v in x['files'].items():
 p=D/rel;assert p.resolve().is_relative_to(D);p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb')as f:f.write(base64.b64decode(v))
r=json.loads((D/'release.json').read_bytes())
for rel,pin in r['files'].items():assert hashlib.sha256((D/rel).read_bytes()).hexdigest()==pin
print(json.dumps(dict(remote_release=str(D/'release.json'),release_sha256=hashlib.sha256((D/'release.json').read_bytes()).hexdigest(),all_files_SHA_match=True,no_frozen_or_closed_runtime_or_H_mutation=True)))
''';payload=dict(name=D.name,files={str(p.relative_to(D)):base64.b64encode(p.read_bytes()).decode()for p in D.rglob('*')if p.is_file()});p=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],input=json.dumps(payload),capture_output=True,text=True,timeout=60);assert p.returncode==0,p.stderr;x=json.loads(p.stdout);assert x['release_sha256']==sha(D/'release.json');(M/'main-minimum-publication-proof.json').write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n');print(json.dumps(dict(local_release=str(D/'release.json'),**x),ensure_ascii=False))
