"""CAS-replace Data-only shared section and own current entrypoints; never H."""
from pathlib import Path
import os,json,datetime,hashlib,fcntl,stat,tempfile,re
B=Path('/home/yuanyue/main/work/data-team');M=Path(__file__).resolve().parent;K=B/'manifests/bulk24-collector-46308-20261115-v1';J=B/'manifests/V-JEPA-J1-resource-response-46308-20261116-v1';S=Path('/home/yuanyue/main/汇总/各小组进展汇总.md');sha=lambda x:hashlib.sha256(x).hexdigest();now=datetime.datetime.now().astimezone().isoformat()
assert sha(Path('/home/yuanyue/main/汇总/各小组下一步研究计划.md').read_bytes())=='0e9f872b16bcb376bea4bf86c4821ced26931baf90f96a1f58256a93d450b50b'
d=json.loads((K/'unstarted-suffix20-driver-status.json').read_bytes());assert not d['global_stop']and d['driver_PID']==2655879
body=f'''## Data组

更新：{now}（北京时间；最新计划0e9f872b…未变；**bulk新增11—16六支原件交付，V4已收23-source选中task factory但五组task main仍0**）

**当前状态**
- **bulk固定24继续且不手控在途phase：** driver PID2655879，快照{d['at']}：zero{d['zero_dispatches']}/main{d['main_dispatches']}/closed{d['closed_main']}（{d['conditional_PASS']}原链PASS/{d['closed_native_failed']}原生失败），真正未启动{d['remaining_not_started']}，当前`{d['current_scope']}` / {d['status']}，global_stop=false。GPU1/CPU38,39单slot逐支fresh/自身zero/cold/main/close，240sim/2400wall/1GiB cap、原483源及门不动；不重复driver、不复开closed、不在其CAS附近写H。
- **closed11—16真实原件现已完整发布：** 11/13原链PASS；12/15原FF门拒，14/16原settle失败。六支均usage known、非resource censor，19原public queries；四支上游失败没有CLIMB query或回执，保持None，不造CLIMB负例。正式01—16累计**56原queries**（不是56独立场景/TEST），query/图/标定/原journal引用/结果/成本逐SHA cold。bulk raw仍192×128**非HD**，不放大充V4原片；四geometry同一TRAIN祖先，critic不refit。索引`{K}/closed11to16-original-release-index.json`，每支原release在本组consumer-deliveries。
- **V4组件实际PASS/closed不重跑：** immutable04f/19-source＋3原构造依赖、完整466-member program b125b188…，新native资产/冷Runtimecomponent zero1 PASS，task main0。result e77fd248… / release5a0d9127…，原robot/engine/actuator/onboard INPUT8/192×128/45D、真实worldbody deck与goal_deck=.60均核过；任务0sim，辅助6.505sim、18.908145529wall，known/close errors0。GPU0组件锁已释放；此前77.056s门闩仅本地driver父进程metadata，远端GPU1 native从未暂停/信号。world0真实1280×720仅**一帧**，不是影片或E成功，原帧高台部分裁切/机器人较小，未来五组共同构图/FPS需新full-program freeze前核，不改原帧或借此zero。
- **AINav新23-source已消费，不再写“没有binder/factory源码”：** immutable eafc8c5b…的23成员本/新端逐SHA核同；destination binder接入选中CLIMB/原RegisteredTaskSessionFactory，current图/钟/world/FIFO、实际PUBLIC对象身份、原live witness与原20cm门保留，原construct/completed witness继承，旧ground-only终点hook不继承。Data本回合没有import/重复软件测试/新native调用。**尚非完整V4 task ready：** 实际selected judge/observer/driver、CLIMB→NAV动态support/contact owner链、static-deck与箱顶.20→平台.60的.40m gap、完整高台终点仍未接齐，不把23-source冒19源组件已验证。收件/精确缺口`{M}/Data-selected-task-factory-consumption.json`。
- **用户箱参数决定与五组公平性保持：** 三箱2.4×1.4×.20m/.5kg/mu.4/.8本已匹配Reach技能锁，scene6394740e…未发生数值改动；不重复索箱体许可，平台/owner接缝另列。不降12N/4s/FF/effort/QP/FIFO/CLIMB stop。A=VLM+原7a6WM，B加共享优化，C原AINav保VLM/树/replanning，D加同一优化，E事前规则且VLM/WM/优化0；B−A/D−C主比较。DeepSeek TLS profile87d38fef…/A—D cap100已定，原7a6远端已核且ReachCPU restore1/forward0，不再等迁模型/索provider或key；完整causal IO/target8和共享cost由对应源owner接续。
- **J1机器入口已明确收件，但未批准新cohort/派发：** 精确request/detail SHA已收，建议16 attempts/16 mains仅待审上界；当前无VJEPA_WM用途release，bulk同一TRAIN祖先不满足2 TRAIN+CAL+独立EVAL，不转audit/critic/V4作J训练。复用v2机载RGB/45D/K/T/原tick，J自己提取序列，不造tensor平台；PUBLIC语义ref≠自动same-anchor目标/bbox，缺关联UNKNOWN。原低优先级CPU40,41/2线程/nice19/idleIO、RSS4GiB/J盘3GiB、单下载512KiB/s及phase cap的**02:00北京时间截止不延长**；GPU lease0/数据forward-fit0，fresh RAM≥16GiB/盘≥30GiB、三组优先。许可/immutable checkpoint身份前提已由J记录满足，不等额外Data签字。Data未声称其已下载/启动/已收跨chat通知。详见`{J}/Data-J1-machine-request-received-not-cohort-approved.json`。

**下一步**
- GPU1继续真正未启动固定余量，保全部分母与费用；已closed原件只读增量发布，不因包装阻物理、不refit或追胜加跑。
- V4由AINav补完整caller/support/终点、Reach补真实方法/因果IO/完整cost，Data按稳定新程序冻结顺序、相机/并行资源与有限预算，必要各自own-zero后main一次。**E共同资格齐即可先于WM，必须真实完整任务成功；A—D交完整direct-live原片，失败/拒绝/censor保留。** 不以组件/软件/旧API0/OBS冒五组，不复开closed。J未来cohort/source/split/实际更小预算另行登记，不阻五组，不热换7a6或冒第六arm。

**详细入口**
- 新原件索引：`{K}/closed11to16-original-release-index.json`；bulk状态`{K}/unstarted-suffix20-driver-status.json`。
- V4已过组件原件：`{B}/consumer-deliveries/AINAV-DATA-V4-NATIVE-ASSET-COLD-COMPONENT-PASS-NOT-TASK-20261116-v1/release.json`；原一帧QA与closed证据`{B}/manifests/V4-native-components-46308-20261116-v1/`（once控制器不再执行）。23-source intake`{M}/README.md`。
- 五组视频后处理/E单独交片：`{B}/development/V4-five-arm-video-postprocess-46308-20261115-v1/README.md`（11软件检查，非影片）；箱锁/profile`{B}/manifests/V4-box-skill-lock-consumption-46308-20261115-v1/README.md`；J响应`{J}/README.md`。
- 计算仅46308；本地/GitHub仅code/小metadata/少数原query，MJB/权重/env/raw/影片留新端。本窗口owner不变；不连旧46174，不改旧scope/根/分母，不创建chat/agent/Goal/自动化。lean仓库`/home/yuanyue/main/code/reach-ability-research`/data-team-development。
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
  return s[:a]+'## 当前最高执行入口：bulk11—16原件已交，V4新23-source已收但完整task尚未ready\n\n'+current.rstrip()+'\n'+s[b:]
 update(B/name,f)
with(M/'Data-only-publication-proof.json').open('x')as f:json.dump(dict(at=now,proof=proof,no_H_worker_or_program_changes=True,all_shared_peer_bytes_preserved=True),f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps(dict(at=now,shared_Data_only_updated=True,driver_snapshot=d,released_public_queries=56),ensure_ascii=False))
