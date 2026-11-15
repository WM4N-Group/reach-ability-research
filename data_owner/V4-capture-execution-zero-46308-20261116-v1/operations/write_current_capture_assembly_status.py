"""Publish the real capture/assembly zero result; Data-only shared CAS, no H writes."""
from pathlib import Path
import os,json,datetime,hashlib,fcntl,stat,tempfile,re
B=Path('/home/yuanyue/main/work/data-team');M=Path(__file__).resolve().parent;K=B/'manifests/bulk24-collector-46308-20261115-v1';J=B/'manifests/V-JEPA-J1-resource-response-46308-20261116-v1';S=Path('/home/yuanyue/main/汇总/各小组进展汇总.md');sha=lambda x:hashlib.sha256(x).hexdigest();now=datetime.datetime.now().astimezone().isoformat()
assert sha(Path('/home/yuanyue/main/汇总/各小组下一步研究计划.md').read_bytes())=='0e9f872b16bcb376bea4bf86c4821ced26931baf90f96a1f58256a93d450b50b'
proof=json.loads((M/'component-original-release-proof.json').read_bytes());assert proof['release_sha256']=='1254bb36b3b073533d9974d5c6849c0bef390be7fca9a054fcf782366ccc51fd';r=json.loads((M/'actual-small/result.json').read_bytes());l=json.loads((M/'actual-small/ledger.json').read_bytes());assert r['passed']and r['capture_witness_complete']and r['actual_execution_assembly_verified']and r['actual_task_steps']==448 and not r['close_errors']and l['usage_known'];h=json.loads((B/'registry/handoff_46308_current_status_20261115.json').read_bytes());q=h['active_V4_capture_execution_scope'];assert not q['active']and q['component_zero_dispatch_count']==1 and q['task_main_dispatch_count']==0
assert not h['active_V4_native_component_scope']['active'];gate=json.loads((M/'metadata-gate-released.json').read_bytes());assert gate['remote_native_GPU1_never_signaled'];d=json.loads((K/'unstarted-suffix20-driver-status.json').read_bytes());assert not d['global_stop']
D=B/'consumer-deliveries/AINAV-DATA-V4-GENUINE-CAPTURE-ORIGINAL-EXECUTION-ASSEMBLY-NOT-TASK-20261116-v1'
body=f'''## Data组

更新：{now}（北京时间；新计划0e9f872b…未变；**V4已取得真实SupportedCapture＋原execution装配zero1 PASS/closed，五组task main仍0；bulk原件已交01—18**）

**当前状态**
- **V4不再停在cold Runtime：** immutable AINav **58b97c74…/25源＋6精确原构造依赖**，新scope `data-46308-V4-capture-execution-zero-20261116-v1`，475成员freeze **f1991adb…**、authority **ecff7d5b…**，真正自身zero1 **PASS并closed**。原SupportedCapture实际发出并核448条200Hz命令/**2.240任务sim**，形成真实ground owner/witness，然后原resolver/backend/RegisteredPushAPI/NativeOptionExecutor＋选中V4TaskFactory/destination adapter在**同world/FIFO**装配通过，6条公开不可变placement合同齐。装配本身0步，未选择/构造NAV/PUSH/CLIMB controller。原completed witness不是软件complete标志，也未复用旧closed world。
- **原流/cost已cold并正式交付：** actual result **00768cd9…**，release **1254bb36…**：`{D}/release.json`。475源逐SHA，452原journal链、448连续命令/原4步FIFO/PD raw与硬clip重现误差0、**23原机载192×128 RGBD**/previous-action/10Hz原格/close均过。辅助1world/6.505sim另列，worker **25.838781291wall/87,735,513bytes**、usage known、close errors0，GPU峰663,748,608bytes/RSS2,520,928,256bytes，原有限cap内。NPZ/MJB/private journal留46308，本机仅小JSON；本包不能进模型/训练或转J用途。
- **这是capture→execution接缝资格，不是E/五组成功或CLIMB动态资格：** 没有技能main、placement、CLIMB→NAV完整owner/contact链、static-deck/.20→.60的.40m接续或完整终点。当前scope已耗尽，不再执行once controller。旧04f/19源asset/cold组件program b125b188…仍原封closed；新475程序不借旧zero，也不能给未来不同完整程序借zero。此前1280×720 world0原件仍只是一帧，非影片；高台裁切/机器人小的共同构图与FPS负载要在新full-program freeze前核。
- **双卡/唯一owner与保护门不变：** 本窗口真实owner保持，fresh GPU0 UUID297c…/canonical device51/inode3428729629/30与容量核后新lease，结束已释放；GPU1原bulk native并存且从未被暂停/信号。whole-H CAS仅新scope键，84.644s有限门闩只停本地driver父进程metadata，watchdog/finally已恢复；不手改bulk phase、不热补source/cap、不复开closed。原Actor/12N/4s/FF/effort/QP/FIFO/CLIMB stop均保留。
- **bulk固定24继续及新原件：** 快照{d['at']}，zero{d['zero_dispatches']}/main{d['main_dispatches']}/closed{d['closed_main']}（{d['conditional_PASS']}原链PASS/{d['closed_native_failed']}原生失败），真正未启动{d['remaining_not_started']}；`{d['current_scope']}` / {d['status']}，global_stop=false。新增17/18均原链PASS，9原public queries；**01—18正式release累计65原query**，不是65独立场景/TEST。11—16的2PASS/4原生失败仍保，FF/settle未到CLIMB不补负例；10的base_collision没有terminal不造回执。GPU1/CPU38,39逐支原ownzero/cold/main一次、240sim/2400wall/1GiB与原483源不变；raw192×128非HD，四geometry同一TRAIN祖先，critic不refit。
- **用户箱锁与方法配置已定，不重复索许可：** 三箱2.4×1.4×.20m/.5kg/mu.4/.8已匹配Reach锁，scene6394740e…无数值改动；平台/owner缺口与箱参数许可分开。A=VLM+7a6WM，B加共享优化，C原AINav保VLM/树/replanning，D加同一优化，E事前规则VLM/WM/优化0；B−A/D−C主比较。DeepSeek TLS profile87d38fef…/A—D cap100已定；7a6已在新端核过、ReachCPU restore1/forward0，不再等迁模型/key/provider。Reach完整causal query/target8/名义cost仍按真实源接，Data不代写优化器/补None为0。
- **J1机器请求已收但未来cohort未批准：** 本用途release0、建议16 attempts/16 mains只是待审上界；bulk同一TRAIN祖先不满足2 TRAIN+CAL+独立EVAL，不转旧audit/critic/V4训练。原低优先级无GPU CPU/下载窗口已于**2026-11-16 02:00北京时间到期**，不自动延长/新增资源或数据fit许可、不改他组进程；未来窗口按fresh余量协调，checkpoint许可前提已满足，不重复签字/key门。详见`{J}/Data-J1-prior-window-expired-at0200.json`。不声称J已下载/已收跨chat通知。

**下一步**
- AINav把已实际装配过的execution接到真正selected caller/observer/judge、CLIMB→NAV support/contact owner与完整终点；Reach接真实causal IO/共享后继cost。Data据稳定新full program冻结顺序、相机、各自有限预算/并行资源后做必要自身zero及main一次。**E共同资格齐即可先于WM，必须真实完整任务成功；A—D交完整direct-live原片，全部失败/拒绝/censor保留。** 不以本capture资格代五组结果、不开已知越原域假对照。
- GPU1继续真正未启动固定余量与cold原件发布，保全分母/成本，不追胜重跑/refit。J未来新用途source/split/实际更小预算另行登记，不阻五组或热换7a6/冒第六arm。无新chat/agent/Goal/自动化。

**详细入口**
- 本次capture/assembly原件：`{D}/release.json`；新scope/cold/账与门闩`{M}/README.md`、`{M}/component-original-release-proof.json`及`{M}/actual-small/`（zero已耗尽）。本地小包decode TypeError及一次恢复断言原记录保留，最终仅从已成功原export响应恢复，物理/export均未重跑。
- bulk新原件索引`{K}/closed17to18-original-release-index.json`；此前closed11to16/09to10/05to08/02to04＋01 release均保留，状态`{K}/unstarted-suffix20-driver-status.json`。
- 五组原片后处理`{B}/development/V4-five-arm-video-postprocess-46308-20261115-v1/README.md`；旧组件/一帧QA`{B}/manifests/V4-native-components-46308-20261116-v1/`；箱锁/profile`{B}/manifests/V4-box-skill-lock-consumption-46308-20261115-v1/README.md`；J响应`{J}/README.md`。
- 工作目录`{B}`，计算仅46308；本地/GitHub仅code/小metadata/少数原query，raw/MJB/权重/env/影片留新端。lean仓库`/home/yuanyue/main/code/reach-ability-research`/data-team-development；旧46174及所有closed根不恢复。
'''
proof=[]
def update(path,transform,shared=False):
 before=path.read_bytes();after=transform(before.decode()).encode();mode=stat.S_IMODE(path.stat().st_mode);backup=M/(path.name+'.before-incremental-source-and-releases')
 with backup.open('xb')as f:f.write(before)
 dfd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY);tmp=None
 try:
  fcntl.flock(dfd,fcntl.LOCK_EX)
  with path.open('rb')as f:
   fcntl.flock(f.fileno(),fcntl.LOCK_EX);assert path.read_bytes()==before,'SHA CAS conflict'
   if shared:
    a=before.index(b'## Data\xe7\xbb\x84\n');b=before.find(b'\n## ',a+1);b=len(before)if b<0 else b
    a2=after.index(b'## Data\xe7\xbb\x84\n');b2=after.find(b'\n## ',a2+1);b2=len(after)if b2<0 else b2
    assert before[:a]==after[:a2]and before[b:]==after[b2:],'Peer bytes changed'
   fd,tmp=tempfile.mkstemp(prefix='.'+path.name+'.cas.',dir=path.parent)
   with os.fdopen(fd,'wb')as out:os.fchmod(out.fileno(),mode);out.write(after);out.flush();os.fsync(out.fileno())
   assert path.read_bytes()==before;os.replace(tmp,path);tmp=None;os.fsync(dfd)
 finally:
  if tmp:os.unlink(tmp)
  os.close(dfd)
 proof.append(dict(path=str(path),before_sha256=sha(before),after_sha256=sha(after),mode_preserved=stat.S_IMODE(path.stat().st_mode)==mode,peer_bytes_preserved=shared))
def repl_shared(s):
 a=s.index('## Data组\n');b=s.find('\n## ',a+1);b=len(s)if b<0 else b
 return s[:a]+body.rstrip()+'\n'+s[b:]
update(S,repl_shared,True)
current=body.split('\n\n',1)[1]
def st(s):
 begin='<!-- NEXT_QUESTION_SAMPLING_CURRENT_BEGIN -->';end='<!-- NEXT_QUESTION_SAMPLING_CURRENT_END -->';a=s.index(begin)+len(begin);b=s.index(end,a);s=s[:a]+'\n\n'+current.rstrip()+'\n'+s[b:]
 return re.sub(r'更新：[^\n]+',f'更新：{now}（北京时间；当前状态以第1节新入口为准）。',s,count=1)
update(B/'STATUS.md',st)
for name in ['AGENTS.md','README.md']:
 def f(s):
  a=s.index('## 当前最高执行入口：');b=s.index('\n## 最新用户服务器与代码决定',a)
  return s[:a]+'## 当前最高执行入口：V4真实SupportedCapture/原execution装配已PASS并closed；五组task main0，bulk继续\n\n'+current.rstrip()+'\n'+s[b:]
 update(B/name,f)
with(M/'Data-only-publication-proof.json').open('x')as f:json.dump(dict(at=now,proof=proof,no_H_worker_or_program_changes=True,all_shared_peer_bytes_preserved=True),f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps(dict(at=now,shared_Data_only_updated=True,driver_snapshot=d,released_public_queries=65),ensure_ascii=False))
