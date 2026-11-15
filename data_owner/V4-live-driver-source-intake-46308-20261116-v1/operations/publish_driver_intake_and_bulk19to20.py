"""Consume exact new source and publish Data-only current state. No native/phase/H writes."""
from pathlib import Path
import json,hashlib,datetime,os,fcntl,stat,tempfile,re
B=Path('/home/yuanyue/main/work/data-team');M=Path(__file__).resolve().parent;K=B/'manifests/bulk24-collector-46308-20261115-v1';J=B/'manifests/V-JEPA-J1-resource-response-46308-20261116-v1';S=Path('/home/yuanyue/main/汇总/各小组进展汇总.md');sha=lambda x:hashlib.sha256(x).hexdigest();now=datetime.datetime.now().astimezone().isoformat();plan=Path('/home/yuanyue/main/汇总/各小组下一步研究计划.md');assert sha(plan.read_bytes())=='42c8a90d31e84d8d3b0c832a405b0a654ad82319f3c0b7f5da49982c1f3cfc3a'
v=json.loads((M/'source-byte-verification.json').read_bytes());assert v['source_count']==27
for name,pin in v['files_sha256'].items():assert sha((M/'source-4909180a'/name).read_bytes())==pin
record=dict(at=now,role='IMMUTABLE_LIVE_DRIVER_SOURCE_INTAKE_NOT_NEW_NATIVE_QUALIFICATION_OR_MAIN',source_commit=v['commit'],source_count=27,source_record_sha256=v['source_record_sha256'],all27_remote_and_local_exact_bytes_verified=True,default_off_live_driver_now_present=True,source_connections=['Original actual200Hz SupportedCapture loop and7 exact original writer/capture/stow/guard methods','Actual current onboard observer plus accepted RGBD resolver and frame-local aliases reset per acquisition','Shared27 public candidates/24 anchors; exact parameter membership and original selected entry judge','Original IntentExecutionCoordinator/AinavLoop and selected native factory, receipts and entered CLIMB contact authority'],no_old_ground_terminal_or_base_constructor_inherited=True,remaining_gaps=['Real post-CLIMB dynamic support/contact-owner transfer for next NAV','Static deck/.20m box-top to .60m platform .40m rise still outside selected original20cm path','Whole-task3 original placements, actual CLIMB chain, goal_deck contact plus continuous.5s stopped dwell verifier','Reach causal WM accepted200Hz owner callbacks and same96x64 anchor semantic target mapping not wired into this driver; complete common cost still absent','Whole-program exact source closure including parent scene_driver7 methods and common-source must freeze with future runner; this intake is not that qualification'],not_requesting_already_granted_box_parameters=True,no_blind_five_arm_dispatch_or_repeat_closed_zero=True,source_import_or_CPU_fixture_retest_or_native_Runtime_Actor_API_WM_forward_fit_calls=0,old_asset_program='b125b188c6e250c9de68b35f42b4dd146cd70cad9ac4a73b220251dd9f8e0096',old_capture_assembly_program='f1991adbfa9b03acb2e944fd72f8965b5fcf3f4b4aad338142ef5aba3edf49ba',both_old_component_scopes_remain_PASS_closed_no_borrowed_zero=True,current_plan_sha256=sha(plan.read_bytes()),plan_delta_only_J_group_progress_and_expired_window_status=True)
with(M/'Data-live-driver-consumption-not-native-ready.json').open('x')as f:json.dump(record,f,ensure_ascii=False,indent=2);f.write('\n')
items=json.loads((K/'closed19to20-original-release-index.json').read_bytes())['releases']
for item in items:
 D=B/'consumer-deliveries'/Path(item['release_path']).parent.name;assert sha((D/'release.json').read_bytes())==item['release_sha256'];r=json.loads((D/'release.json').read_bytes())
 for name,pin in r['files'].items():assert sha((D/name).read_bytes())==pin
 assert r['actual_summary']['all_usage_known']and not r['actual_summary']['resource_censored']
assert sum(item['summary']['public_query_count']for item in items)==7
d=json.loads((K/'unstarted-suffix20-driver-status.json').read_bytes());assert not d['global_stop'];grant=json.loads((J/'Data-J1-new-finite-CPU-download-window-to0415.json').read_bytes());assert grant['GPU_leases']==0 and grant['expires_at']=='2026-11-16T04:15:00+08:00'
body=f'''## Data组

更新：{now}（北京时间；新计划**42c8a90d…**已读，仅J进度/过期窗口口径增量，既有freeze不改；**bulk01—20原件交齐；V4新27-source live driver已收，五组task main仍0**）

**当前状态**
- **V4最新source已从helper走到live driver，未冒实际执行：** immutable AINav **4909180a…/27成员**逐SHA取回核同，`live_driver.py`实际源码接原SupportedCapture200Hz循环、current observer/accepted RGBD aliases（新帧[]清旧映射）、27公共候选/24 anchors/原selected judge及原IntentExecutionCoordinator/AinavLoop；只复用原7个逐method SHA函数，不继承旧constructor/ground终点。Data本回合没有import/重复fixture或新native调用。**还不是完整V4 main ready：** 真CLIMB→NAV动态support/contact owner、static-deck/.20→.60的.40m接续、三placement/goal_deck实际contact/连续.5s停稳终点仍缺；本driver尚未接Reach实际causal callbacks/96×64同anchor目标关联，完整共享cost仍由Reach完成。不盲派五main或以新source重跑已closed零步；精确收件`{M}/Data-live-driver-consumption-not-native-ready.json`。
- **已有真实capture/原execution资格保持PASS/closed，不借给27-source：** AINav58b97c74…/25源＋6依赖，475成员program f1991adb…，scope `data-46308-V4-capture-execution-zero-20261116-v1`，zero1/main0。真实capture448命令/2.240任务sim＋原辅助6.505sim，形成ground owner/witness后同world/FIFO装配原resolver/backend/NativeOptionExecutor/选中factory与6placement合同；装配0步/0选中技能controller。452原journal链、448原FIFO/PD raw/clip误差0、23机载192×128帧/previous-action/10Hz/close均cold过。25.838781291wall/87,735,513bytes、usage known/close errors0；result00768cd9…/release1254bb36…。不是E/技能链/五组成功或影片，NPZ/MJB/private journal远端且本包不授训练/模型输入。
- **旧资产与安全/唯一owner不变：** 原04f/19源/b125 asset-cold zero1仍原封closed；1280×720 world0仍仅一帧，非正式构图/FPS/片。未来新full program需自身zero、共同构图/负载、精确源闭包及有限预算。GPU0组件规范锁已释放；前84.644s门闩仅本地driver父进程metadata，远端GPU1 native从未暂停/信号。原Actor/12N/4s/FF/effort/QP/FIFO/CLIMB stop保持；不改旧scope/H/费用或借旧zero。
- **bulk新交19/20：** 19原链PASS/5queries，20原`reconciled_reference_FF_intersection_empty`/2queries，未到CLIMB，query/outcome保持None不补负例；两支usage known、非resource censor。**01—20正式release累计72原public queries**，不冒独立场景/TEST或方法胜率；四geometry同1 TRAIN祖先，critic不refit。driver快照{d['at']}：zero{d['zero_dispatches']}/main{d['main_dispatches']}/closed{d['closed_main']}（{d['conditional_PASS']}原链PASS/{d['closed_native_failed']}原生失败），真正未启动{d['remaining_not_started']}；当前`{d['current_scope']}` / {d['status']}，global_stop=false。GPU1/CPU38,39原单slot逐支fresh/ownzero/cold/main一次，240sim/2400wall/1GiB/483源不变；raw192×128非HD，不手写phase/CAS或复开closed。索引`{K}/closed19to20-original-release-index.json`。
- **箱参数授权/五组配置已落实：** 三箱2.4×1.4×.20m/.5kg/mu.4/.8已匹配Reach锁，scene6394740e…未改数值；不重复索箱体许可，平台/owner缺口另列。A=VLM+原7a6WM/B加共享优化，C原AINav保VLM/树/replanning/D加同一优化，E事前规则VLM/WM/优化0；B−A/D−C主比较。DeepSeek TLS profile87d38fef…/A—D cap100、7a6远端hash及ReachCPU restore1/forward0已定，不等迁模型/provider/key。Reach同anchor target8有原几何代码/synthetic CPU证据但**未接真实source/forward或完整cost**，不从组件/旧OBS拼历史。
- **J组已确认收件/旧窗未使用；本回合fresh给新的独立低优先级窗口：** 原02:00窗口保持过期，不自动延长。精确消费其readiness ack后，02:39 fresh RAM120,535,333,888bytes/盘余充足、J root未建；新窗口**现在至2026-11-16 04:15北京时间**，CPU40,41/2线程/nice19/idleIO/RSS4GiB/J盘3GiB/单job、单encoder下载≤512KiB/s且≤3600wall、CPU技术phase≤900wall，绝对截止先到先停。每次fresh RAM≥16GiB/共享盘≥30GiB/own≤3GiB、三组需要立即让出，非资源预留。**GPU lease0、cohort/数据fit批准0**，不改Data环境/他组进程/H/锁/API；具体checkpoint许可/revision前提已满足，不再等额外签字/key。Data未代建目录/起job/宣称其已下载或通知到chat。新响应`{J}/Data-J1-new-finite-CPU-download-window-to0415.json`；旧audit/critic/bulk/V4用途不转J，同祖先不拆split。

**下一步**
- AINav继续真实support/contact-owner/完整终点与共同技能域方案；Reach完成真实causal IO/同anchor目标/完整后继cost。Data按稳定的新完整程序冻结顺序、相机、预算/并行资源，必要各自own-zero后main一次。**E共同资格齐即可先于WM，目标仍必须真实完整任务成功；A—D交完整direct-live原片，失败/拒绝/censor保留。** 不以helper/小component/旧API0/OBS冒五组或已知越原域盲跑。
- GPU1接续最后真正未启动固定余量与原件cold，保全分母/费用，不refit/追胜追加；J可直接按新有效低优先级技术窗口做权重hash/CPU恢复或明确synthetic技术profile，未来独立新用途cohort/source/split/实际更小预算另行登记，不热换7a6/冒第六arm。无新chat/agent/Goal/自动化。

**详细入口**
- 最新27源及明确剩余缺口`{M}/README.md`、`{M}/Data-live-driver-consumption-not-native-ready.json`；计划SHA仅新状态，原f199冻结仍0e9f872b…不回写。
- 已过capture/assembly原件`{B}/consumer-deliveries/AINAV-DATA-V4-GENUINE-CAPTURE-ORIGINAL-EXECUTION-ASSEMBLY-NOT-TASK-20261116-v1/release.json`；`{B}/manifests/V4-capture-execution-zero-46308-20261116-v1/`（once不再执行，原decode transport错误/恢复也保留）；旧asset/帧QA`{B}/manifests/V4-native-components-46308-20261116-v1/`。
- bulk新索引closed19to20及此前closed17to18/11to16/09to10/05to08/02to04＋01原release：`{K}/`；五组/E单独交片后处理`{B}/development/V4-five-arm-video-postprocess-46308-20261115-v1/README.md`；J新窗口`{J}/README.md`。
- 工作目录`{B}`，compute仅46308；本地/GitHub只代码/小metadata/少数原query，raw/MJB/权重/env/片留远端。lean `/home/yuanyue/main/code/reach-ability-research`/data-team-development；不连旧46174/恢复closed，不动其他组/owner/自动化。
'''
(M/'README.md').write_text(f'''# 新27-source live driver已核，未当新native资格（{now}）\n\n当前计划42c8a90d…只更新J进度/过期窗口口径；原f199475-member capture/assembly程序仍按0e9f872b…冻结，原b125也不回写。新AINav4909180a3fa05ebf5a1eb1cf2847df42ee6cc1d9/27成员从immutable新端逐SHA核回，原record和源保留source-4909180a/；本回合没有source import/fixture重复或新native dispatch。\n\n原live driver/observer/selected judge/200Hz loop源码确已连，不再写“没有caller代码”；仍缺真实CLIMB→NAV support/contact owner、static deck/.40m接续、完整高台停稳终点，Reach actual96×64 anchor/200Hz causal callbacks和共享cost还未连，不能盲派五main或为相同已closed问题换ID重跑。未来full program会冻结原scene_driver7个method及完整必要依赖，不能借25源组件zero。精确边界在Data-live-driver-consumption-not-native-ready.json。\n\n同回合只读发布closed19/20：PASS1/FF失败1，7原queries，累计01—20正式72query，同1 TRAIN祖先、无refit/新用途。J原下窗ack已精确消费，fresh给新的独立低优先级CPU/下载窗口至04:15，GPU0lease/真实数据fit0、三组优先/可让出；不是延长旧过期slot，不代起其job。详见{J}/Data-J1-new-finite-CPU-download-window-to0415.json。\n''')
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
  return s[:a]+'## 当前最高执行入口：27源live driver已收但完整main待接，bulk01—20原件交齐，J新低优先级窗至04:15\n\n'+current.rstrip()+'\n'+s[b:]
 update(B/name,f)
with(M/'Data-only-publication-proof.json').open('x')as f:json.dump(dict(at=now,proof=proof,no_H_worker_or_program_changes=True,all_shared_peer_bytes_preserved=True),f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps(dict(at=now,shared_Data_only_updated=True,driver_snapshot=d,released_public_queries=72),ensure_ascii=False))
