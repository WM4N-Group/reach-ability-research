"""Data-only original delivery pointers; no H or physical/native changes."""
from pathlib import Path
import os,json,datetime,hashlib,fcntl,stat,tempfile,subprocess,shlex,base64,ast,re
B=Path('/home/yuanyue/main/work/data-team');M=Path(__file__).resolve().parent;T=B/'manifests/T-COMPLEX-observability-study-46308-20261115-v1';S=Path('/home/yuanyue/main/汇总/各小组进展汇总.md');now=datetime.datetime.now().astimezone().isoformat();sha=lambda b:hashlib.sha256(b).hexdigest()
assert sha(Path('/home/yuanyue/main/汇总/各小组下一步研究计划.md').read_bytes())=='ad0b589ba1aaf46a0de5faaf1002bc690f2df2c727195297460b30e291385dca'
idx=json.loads((M/'closed02to04-original-release-index.json').read_bytes());assert len(idx['releases'])==3
releases=[]
for ordinal,row in zip((2,3,4),idx['releases']):
 p=B/'consumer-deliveries'/Path(row['release_path']).parent.name/'release.json';r=json.loads(p.read_bytes());assert r['ordinal']==ordinal and sha(p.read_bytes())==row['release_sha256']
 for name,pin in r['files'].items():assert sha((p.parent/name).read_bytes())==pin
 releases.append((p,r,row['release_sha256']))
assert [r['actual_summary']['source_result_passed']for p,r,pin in releases]==[True,True,False]
f=releases[2][1]['actual_summary'];assert f['source_error']=='reconciled_reference_FF_intersection_empty'and f['first_CLIMB_boundary']['status']=='NO_CLIMB_JUDGMENT_RECORDED'and f['missing_CLIMB_query_features']is None and f['missing_CLIMB_outcome_label']is None
s=S.read_text();i=s.index('## Data组');j=s.find('\n## ',i+1);j=len(s)if j<0 else j;body=s[i:j];peer=(s[:i].encode(),s[j:].encode());driver=json.loads((M/'unstarted-suffix20-driver-status.json').read_bytes());assert not driver['status'].startswith('STOPPED') and not driver['global_stop']
parts=[]
for p,r,pin in releases:
 summary=r['actual_summary'];b=summary['first_CLIMB_boundary'];parts.append(f"ordinal{r['ordinal']:02d} release **{pin[:12]}…**（{summary['public_query_count']}个实际原public queries；首CLIMB PREPARE="+(f"{b['first_PREPARE_time_s']:.3f}sim"if b['actual_physical_observation_sha256']else'None/未到CLIMB judgment')+'）')
new=f'''- **原件交付补齐（{now}，仅只读复制，不重跑）：** '''+'；'.join(parts)+f'''。02/03按原intent-observation语义SHA＋原journal精确绑定首PREPARE，非最近grid/后继帧；04完整保原FF失败、2个实际query及已发生NAV成功回执，**缺失CLIMB输入/features/label仍None，不能因尝试失败造CLIMB负例**。3份release/所有小成员逐SHA核过、完整journal链再核过，三原branch前后不变；raw/MJB/数组/模型/视频留远端，未写权威H、未创建新world/query或训练/派发。完整入口 `{M}/closed02to04-original-release-index.json`（本机共11个原public query；含第1条累计16个，不等16独立场景/决策）。未来48slots/标签仍由原用途协议与精确PREPARE/READY/outcome分层，本交付不授权当前critic refit或整包fit。\n'''
anchor='- **并发metadata冲突';pos=body.index(anchor);body=body[:pos]+new+body[pos:]
body=body.replace('第1条正式原件release904ff608…保留，第2—4条原result/audit在','第1条正式原件release904ff608…及新增02—04正式原件均可消费；第2—4条原result/audit在')
# Fresh local finite-driver snapshot, no remote H mutation or phase replay.
body=re.sub(r'snapshot全批zero已派.*?。单GPU1/',f"snapshot（{driver['at']}）全批zero已派{driver['zero_dispatches']}/main已派{driver['main_dispatches']}/终态{driver['closed_main']}（{driver['conditional_PASS']}PASS/{driver['closed_native_failed']}失败），余{driver['remaining_not_started']}条完全未启动；当前 `{driver['current_scope']}` / **{driver['current_phase']}**。单GPU1/",body,count=1)
body=re.sub(r'bulk已4条终态：3条件PASS/1原生FF门失败',f"bulk已{driver['closed_main']}条终态：{driver['conditional_PASS']}条件PASS/{driver['closed_native_failed']}原生门失败；02—04正式原件补齐",body,count=1)
# Do not turn a completed pre-CLIMB/native gate failure into a method failure or zero label.
body=body.replace('更新：2026-11-15T22:24:26.891487+08:00', '更新：'+now,1)

V=B/'manifests/V4-four-arm-intake-46308-20261115-v1';intake=json.loads((V/'Data-readonly-intake.json').read_bytes());assert intake['main_plan_sha256']=='ad0b589ba1aaf46a0de5faaf1002bc690f2df2c727195297460b30e291385dca' and intake['new_V4_main_dispatches']==0
v4=f"- **22:36新计划已切换：V4＋四组真实方法，覆盖旧API0双组定义。** A=VLM＋WM，B=前者＋共享后继优化，C=原AINav，D=AINav＋同一共享优化；主要B−A、D−C，保C原生VLM/技能树/重规划，不向D另加WM。既有WM推理仅本对照获准，未支持Finish/CLIMB/整链保持UNKNOWN，不恢复WM/Actor训练。Data已逐SHA保存research原协议cf76b418…、V4 scene6394740e…与平台fresh-spec源差分；原9软件测试不重复、0新compile/Runtime/Actor/Renderer/API/WM forward，**V4 zero0/main0/视频0、未持新lease或宣称入队**。缺实际V4 CLIMB/support transition/高台停稳终点、真实两backbone及B/D共享优化、准确provider endpoint/model/安全注入与共同预算；齐备后在结果前冻结四arm独立顺序/有限cap并各自zero/lease/main一次。高台0.60m必须实际支撑停稳，不能拿地面XY或几何预期代动态成功；不猜endpoint、不把key发旧HTTP网关。**现bulk不热改，旧pair/OBS不改名四组、不复开。** 接续入口 `{V}/README.md`、`{V}/Data-readonly-intake.json`。\n"
body=body.replace('**当前状态**\n','**当前状态**\n'+v4,1).replace('主计划14:00/b2fb786e…未变','新主计划22:36/ad0b589b…已读，V4四组接入准备',1)
start=body.index('- 首优先由AINav/Reach');end=body.index('\n- suffix20',start)
body=body[:start]+f"- **首优先改为V4四组准确接入。** Data按research已给的协议/平台差分准备新隔离装配，不以旧API0 greedy/multistep或脚本观测冒真实VLM＋WM/AINav；原技能/门/观测域/候选/公共VLM版本与预定预算统一，真实WM调用和共享优化选项须有原native消费记录。先接准确CLIMB高台与backbone源，再独立freeze/ownzero/main、四份完整live原片和同钟四栏，全部失败/API与资源截断保留，不按结果重试。现唯一计算工作仍bulk固定未启动suffix；源/接口缺口具体见`{V}/README.md`，不重复索实验许可或新增wrapper。OBS三边界只作旧DEV原件，不将left旧阳性缓存给V4下一PUSH。"+body[end:]

entry=f"## 当前最高执行入口：V4四组已接收未派、T观测closed非任务、bulk{driver['conditional_PASS']}PASS/{driver['closed_native_failed']}原门失败，02—04原件补齐、未启动suffix滚动\n"+body.split('\n',1)[1]+'\n';proof=[];remote=[]
oldmod=B/'manifests/T-COMPLEX-01-full-program-46308-20261115-v1/publish_full_program_current.py';tree=ast.parse(oldmod.read_text());node=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='update');src=ast.get_source_segment(oldmod.read_text(),node);src=src.replace('.before-full-program-A-main','.before-bulk02to04-original-release').replace('.T-full-A-','.bulk02to04-release-').replace('（北京时间；T完整程序A自身zero/cold通过、唯一main实派，B0/0；不是已完成对照）。','（北京时间；V4四组新计划已接收未派、bulk原件02—04补齐，未启动suffix滚动；旧closed/原门不改）。');exec(compile(src,'Data-only-original-release-publisher','exec'),globals())
update(S,True);assert S.read_bytes().startswith(peer[0])and S.read_bytes().endswith(peer[1])
for name in('STATUS.md','AGENTS.md','README.md'):update(B/name)
for folder in(M,T):
 p=folder/'README.md'
 with(folder/'README.before-bulk02to04-original-release.md').open('xb')as f:f.write(p.read_bytes())
 p.write_text('# T观测closed、bulk原件02—04补齐、仅未启动suffix滚动\n'+body.split('\n',1)[1])
code=next(ast.literal_eval(n.value)for n in tree.body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='code'for t in n.targets));rp=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],input=json.dumps(remote),capture_output=True,text=True,timeout=90)
for suffix,text in [('stdout',rp.stdout),('stderr',rp.stderr)]:
 with(M/('closed02to04-entry-mirror.'+suffix)).open('x')as f:f.write(text)
with(M/'closed02to04-publication-CAS-peer-proof.json').open('x')as f:json.dump(dict(at=now,proof=proof,all_non_Data_peer_bytes_preserved=True,remote_exit=rp.returncode,H_not_written=True,no_native_source_scope_cap_or_count_change=True),f,indent=2);f.write('\n')
assert rp.returncode==0,rp.stderr;print('Published original02..04 deliveries; peers preserved, H/native unchanged')
