"""Data-only current snapshot; no H writes while finite GPU1 driver rolls."""
from pathlib import Path
import os,json,datetime,hashlib,fcntl,stat,tempfile,subprocess,shlex,base64,ast
B=Path('/home/yuanyue/main/work/data-team');M=Path(__file__).resolve().parent;D=B/'development'/M.name;K=B/'manifests/bulk24-collector-46308-20261115-v1';V=B/'manifests/V4-four-arm-intake-46308-20261115-v1';T=B/'manifests/T-COMPLEX-observability-study-46308-20261115-v1';S=Path('/home/yuanyue/main/汇总/各小组进展汇总.md');now=datetime.datetime.now().astimezone().isoformat();sha=lambda b:hashlib.sha256(b).hexdigest()
plan=sha(Path('/home/yuanyue/main/汇总/各小组下一步研究计划.md').read_bytes());assert plan=='ae2b8e6ba1681bc75af5b146033cac26d7f588f290721c593035b86dd0007f2d'
test=json.loads((M/'software-fixture-test-result.json').read_bytes());assert test['exit_code']==0 and 'Ran 9 tests' in test['stderr'] and test['synthetic_fixture_only']
for name,pin in test['source_pins'].items():assert sha((D/name).read_bytes())==pin
d=json.loads((K/'unstarted-suffix20-driver-status.json').read_bytes());assert not d['status'].startswith('STOPPED')and d['closed_main']==6 and d['conditional_PASS']==4 and d['closed_native_failed']==2
C='g2-bulk24-v1__bulk-g09_right__lateral_minus_0p04';r=json.loads((K/C/'main-result.json').read_bytes());a=json.loads((K/C/'actual-main-cold-audit-v2.json').read_bytes());assert not r['passed']and r['error'].startswith('push_start_pose_timeout:settle:')and not r['resource_censored']and r['usage_known']and a['passed']
body=f'''## Data组

更新：{now}（北京时间；22:40主计划ae2b8e6b…未变；V4四组接入准备＋四栏后处理已实现/纯软件过；bulk6条终态4PASS/2原生失败，第7在途）

**当前状态**
- **当前首优先是V4四组真实方法，不是旧API0双组：** A=VLM＋WM、B=前者＋共享后继优化、C=原AINav、D=AINav＋同一共享优化；主要B−A/D−C，保C原生VLM/技能树/重规划，不向D另加WM。现有WM推理仅本任务获准，未支持域UNKNOWN，不恢复WM/DINO/Actor重训。research只规划/汇总；AINav主责V4场景/CLIMB/support/高台终点与真实VLM/原AINav，Reach主责WM路线与B/D共享优化/评价；Data沿现runner装配稳定包、资源/生命周期/采样接线及唯一物理执行。已接收V4 scene6394740e…/research候选协议cf76b418…，但**真实V4 zero0/main0/原片0**；平台差分原9 CPU检查非native资格。尚缺实际CLIMB高台/终态接缝、真实四方法和公共API配置/预算；不拿地面XY、旧OBS/API0或手工路线冒四组成功，不猜服务endpoint或发送key到旧HTTP网关。
- **Data可独立推进的真实代码工作已完成一项：四原片＋同钟四横栏后处理。** 新`{D}/encode_four_arm_originals.py`读取现有原raw格式，逐SHA/原scope/program/camera/整数tick/采集钟绑定、流式H264编码，世界原像素不裁切/放大/插帧；96px说明头在原画面外。每组结束后黑色说明页，**不冻结或延长世界**；原task UNKNOWN不转false，phase PASS不冒整场成功。新端9项**新视频纯CPU检查**exit0/2.273s，实际ffprobe过5个微型fixture MP4及[3,2,1,3]→四栏3帧/3840×636分母，低清/相机不同/重复root/损坏/缺tick/源改动/fixture升真实均拒绝。全部SOFTWARE_FIXTURE_NO_PHYSICS，临时样例已移除，**0新世界/编译/Actor/Renderer/WM/API/实际实验影片，未重跑research原9测试或旧scope**。本机缺NumPy/ffmpeg未安装；检查只在新端现有私有环境CPU36,37/CUDA空/MUJOCO禁用。新V4采集仍优先1280×720、资源允许下至少960×540，实际采集FPS/负载待完整源冻结前实测；本后处理不签采集或方法资格、不加物理前置门。
- **GPU1 bulk已6条真实终态：4条件PASS、2原生失败，完整分母保持。** PASS为ordinal01/02/03/05（最后g09-left/+4cm：121.140task sim/24228命令/1212帧，exact3及九流cold过）；ordinal04原FF交集为空失败保留。新增ordinal06 g09-right/−4cm result **f0fec77e…**，原`push_start_pose_timeout:settle`，**99.145task sim/19829命令/992 RGBD-review-raw各**；scope含自身zero/双aux**112.155sim/775.060352648wall**，usage known、非resource censor。九流cold过仅说明记录完整，**不洗掉native失败，不把未到CLIMB的输入/label造0**；原门/阈值不改、不重试失败支。
- **固定未启动suffix持续滚动，不另开重复driver：** PID{d['driver_PID']}、snapshot `{d['at']}`，zero派{d['zero_dispatches']}/main派{d['main_dispatches']}/终态6（4PASS/2失败），余{d['remaining_not_started']}条完全未启动；当前 `{d['current_scope']}` / **{d['current_phase']}**。GPU1 UUID6d66…/CPU38,39单slot，各支fresh lease/容量/ownzero/cold/main一次；全24配方/483成员/240sim-2400wall-1GiB各scope不变，一既有TRAIN祖先、4几何/8context×3候选，不是4独立留出/方法胜率。**不要重跑driver/既耗phase或在phase CAS附近手动写H。** 原余22 driver因whole-H CAS竞态停止的日志/拒绝及第4支metadata-only收束原件均保留，不复活旧driver；现suffix仅接真正未启动ordinal05—24，前4支不重派。
- **正式原件和历史不回写：** bulk01—04 release已逐成员SHA核完；02/03首CLIMB PREPARE精确85.900/95.465sim，04没有CLIMB judgment，features/label保持None。02—04新增11实际public queries、连01共16，非16独立样本；04/06不是CLIMB负例。bulk direct raw原**192×128非HD**，原erratum/失败审计保留；不能放大作V4高清片。旧T pair closed/stop及原4800wall不改；独立OBS三边界完整closed（[]→[cuboid_a]→[]），release785bd9db…/276帧1×原片已交，只观测资格非PUSH READY/任务/前瞻收益。旧46174 UNKNOWN、TRAIN6/既有一次critic fit与CAL/VAL旧协议保持，当前bulk不refit。大raw/MJB/权重/env/视频全留46308，本地/GitHub只code、小metadata/少数原query；无第二owner/新自动化/真机。

**下一步**
- V4源/方法齐备即接现runner，结果前冻结四arm执行顺序、源/模型/初态/原门、公共VLM参数/调用预算、相机及有限watchdog；各自fresh canonical lease/ownzero后main一次，不等百级收齐、不让可选报告挡执行。方法问题由AINav/Reach owner修，Data不代造WM/优化器；0.60m高台须真实支撑停稳和原CLIMB回执，不以几何预期代动态资格。
- 后处理代码已待真实四arm，不重复跑fixture充进度、不用四条bulk重贴四方法、不因补片重跑closed。实际原件到齐后输出4份完整1×和同钟四栏；API/资源截断与native失败分开，完整任务/有效选择/机制由原实际记录解释，不预设胜出。
- GPU1继续既有固定余量，每支原终态/cold/关闭→fresh下一未启动支；原queries/费用可只读并行交付，异常或UNKNOWN保分母、不自动训练或整包fit。新计划准备与现bulk并行，不热改或取消在途程序。

**详细入口**
- 四栏工具/新软件结果：`{D}/README.md`、`{M}/software-fixture-test-result.json`；仅代码/软件资格，非实际四组影片。
- V4当前收件与职责：`{V}/README.md`、`{V}/Data-plan-2240-intake-addendum.json`。原候选source pin保留，无实际四组排队声明。
- bulk current/原结果：`{K}/unstarted-suffix20-driver-status.json`、`{K}/latest-observation-pointer.json`、各candidate子目录；**driver已启动不可重复**。01—04原件索引`{K}/closed02to04-original-release-index.json`及01独立release；06原始错误只在evidence，不用private参数喂planner。
- OBS原件：`{B}/consumer-deliveries/AINAV-DATA-T-OBS-THREE-FIXED-BOUNDARIES-COMPLETE-NOT-TASK-20261115-v1/release.json`；旧pair直接raw同钟片入口`{B}/manifests/T-COMPLEX-01-full-program-46308-20261115-v1/closed-pair-direct-video-manifest.json`。本机代码`/home/yuanyue/main/code/reach-ability-research`/data-team-development，compute仅46308，工作目录仍`{B}`。
'''
entry='## 当前最高执行入口：V4四栏后处理代码新端9软件过/真实四组未派；bulk4PASS/2原失败、第7在途\n'+body.split('\n',1)[1]+'\n';proof=[];remote=[]
old=S.read_text();i=old.index('## Data组');j=old.find('\n## ',i+1);j=len(old)if j<0 else j;peer=(old[:i].encode(),old[j:].encode())
p=B/'manifests/T-COMPLEX-01-full-program-46308-20261115-v1/publish_full_program_current.py';tree=ast.parse(p.read_text());node=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='update');fn=ast.get_source_segment(p.read_text(),node).replace('.before-full-program-A-main','.before-four-panel-code-bulk6').replace('.T-full-A-','.four-panel-bulk6-').replace('（北京时间；T完整程序A自身zero/cold通过、唯一main实派，B0/0；不是已完成对照）。','（北京时间；V4四栏后处理新端软件过，实际四组未派；bulk4PASS/2原失败、第7在途）。');exec(compile(fn,'Data-four-panel-current-publisher','exec'),globals());update(S,True);assert S.read_bytes().startswith(peer[0])and S.read_bytes().endswith(peer[1])
for name in('STATUS.md','AGENTS.md','README.md'):update(B/name)
for folder in(K,T):
 with(folder/'README.before-four-panel-code-bulk6.md').open('xb')as f:f.write((folder/'README.md').read_bytes())
 (folder/'README.md').write_text('# V4四栏后处理软件过、bulk4PASS/2失败、第7在途\n'+body.split('\n',1)[1])
code=next(ast.literal_eval(n.value)for n in tree.body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='code'for t in n.targets));r0=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],input=json.dumps(remote),capture_output=True,text=True,timeout=90)
for suffix,text in [('stdout',r0.stdout),('stderr',r0.stderr)]:
 with(M/('four-panel-current-mirror.'+suffix)).open('x')as f:f.write(text)
with(M/'four-panel-current-publication-CAS-peer-proof.json').open('x')as f:json.dump(dict(at=now,proof=proof,all_non_Data_peer_bytes_preserved=True,remote_exit=r0.returncode,H_not_written=True,native_sources_caps_counts_not_modified=True,fixtures_not_actual_experiments=True),f,indent=2);f.write('\n')
assert r0.returncode==0,r0.stderr;print('Published real postprocess implementation and original sixth native failure; peers/H/native preserved')
