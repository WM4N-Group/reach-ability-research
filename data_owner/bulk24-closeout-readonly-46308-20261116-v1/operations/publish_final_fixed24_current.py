"""Data-only current state from final24 original proof and explicit source-owner policy. No H/scope/source hot edits."""
from pathlib import Path
import os,json,datetime,hashlib,fcntl,stat,tempfile,re
B=Path('/home/yuanyue/main/work/data-team');M=Path(__file__).resolve().parent;K=B/'manifests/bulk24-collector-46308-20261115-v1';J=B/'manifests/V-JEPA-J1-resource-response-46308-20261116-v1';V=B/'manifests/V4-legacy-common-policy-source-intake-46308-20261116-v1';F=B/'manifests/V4-pre-main-factor-and-bootstrap-review-46308-20261116-v1';S=Path('/home/yuanyue/main/汇总/各小组进展汇总.md');sha=lambda x:hashlib.sha256(x).hexdigest();now=datetime.datetime.now().astimezone().isoformat();assert sha(Path('/home/yuanyue/main/汇总/各小组下一步研究计划.md').read_bytes())=='42c8a90d31e84d8d3b0c832a405b0a654ad82319f3c0b7f5da49982c1f3cfc3a'
proof=json.loads((M/'fixed24-final-original-release-proof.json').read_bytes());assert proof['release_sha256']=='5367a3a1b0f68f7f623ba596e23a77a39f860905377588840f3bee76cb4eebf9';D=Path(proof['local_release_path']).parent;release=json.loads((D/'release.json').read_bytes());summary=release['summary'];assert summary['closed']==24 and summary['formal_original_public_queries']==84 and summary['conditional_original_chain_PASS']==10 and summary['closed_nonPASS']==14 and summary['closed_resource_censored']==0
for name,pin in release['files'].items():assert sha((D/name).read_bytes())==pin
resource=json.loads((M/'fixed24-final-authority-resource-proof.json').read_bytes());assert resource['all24_H_closed_zero24_main24']and not resource['Data_runtime_worker_PIDs']and resource['local_H_mirror_matches_remote'];decision=json.loads((V/'Data-resolved-legacy-common-policy-consumption.json').read_bytes());assert decision['old_pending_common_vs_treatment_classification_resolved']and decision['optional_strict_H_isolation_helper_not_adopted_and_not_pending'];d=json.loads((K/'unstarted-suffix20-driver-status.json').read_bytes());assert d['status']=='FIXED24_CLOSED_NO_REFIT'and d['closed_main']==24 and not d['global_stop']
body=f'''## Data组

更新：{now}（北京时间；主计划42c8a90d…未变；**固定bulk24已全部关闭/原件交齐：10原链PASS、14原生失败，84原public queries；V4新30源共同H政策已收，五组main仍0**）

**当前状态**
- **固定24真实采集与正式交付完成，不自动加跑/refit：** 24次自身zero＋24次独立main全部closed，最终driver `FIXED24_CLOSED_NO_REFIT`，无未启动/在途、global_stop=false。**10原NAV→PUSH→20cm CLIMB链PASS/14非PASS**；原因为FF门6、准备settle超时6、runtime `base_collision`2，resource censor0，所有scope usage known。01—24原件完整逐SHA交付，**84原public queries**、481,685实际主世界200Hz命令、24,097机载RGBD/24,097 review/24,097 direct raw帧。raw仍192×128**非HD**；4geometry/8context共享1 TRAIN祖先，不是24独立TEST/方法对照，当前critic不refit、不转VJEPA用途或改旧科学库存。
- **最终端点/成本准确保留：** 12支有真实首CLIMB PREPARE/query并原生admitted；10/21两支随后base_collision、没有原CLIMB succeeded/failed terminal，保持None，不造回执或自动critic label；其余未到CLIMB者不补负例。24个已闭scope原ledger合计含ownzero/aux **2720.665sim /19005.873282551wall**，不是整个项目端到端/货币总费；主世界原任务sum2408.425sim，失败elapsed不填成功Finish成本。各scope高水位合计3,704,710,741bytes不是当前总磁盘。完整final release **5367a3a1…**：`{D}/release.json`，固定24 source-result/audit/ledger/formal release pins、全失败/费用/用途边界齐。
- **fresh权威/设备已核，未重claim或留worker：** {resource['at']}远端H全部24closed，Data原runtime worker0，旧asset/capture/OBS/pair仍closed，本机H SHA与新端权威一致。GPU0/1 UUID297c…/6d66…、四canonical锁device51/inodes3428729629/30与3428459217/18均原inode、已释放（不是新lease），未杀/改任何其他组进程。Data owned **26,125,737,472bytes /40GiB**，provider quota未知；不迁raw/模型/env到本地或删证据腾空间。所有原cap/Actor/12N/4s/FF/effort/QP/FIFO/CLIMB stop及旧driver metadata-CAS失败历史保持，不重开/重跑成功或失败scope。
- **V4方法身份澄清已由source owner决议，不再待签：** 正式消费AINav immutable **8105e755…/30成员**（本/新端逐SHA），policy **14b77d69…**：**legacy-common旧H五组同开、全部真实成本计各arm，不归因B−A/D−C；new-successor只B/D开，A/C/E关。E=固定规则/VLM0/WM0/新后继优化0＋相同共同H，不能再声称所有底层kernel都0。** 保完整C，不采用Reach可选strict H隔离，旧待决项关闭。新source显式arm、只借原6个helper，不再setattr覆回旧installer；legacy尝试/返回/异常/path提议与new choice事件分记，缺完成未知、事件≠kernel次数/实际motor改变/任务收益。Data只消费源/政策，**未import/重复fixture/装callback或新native调用**，不把30源当native已合格；详见`{V}/Data-resolved-legacy-common-policy-consumption.json`。
- **已有V4真实资格继续保留但不借用：** 25源58b97c74…＋6依赖/475成员f1991adb…，真实SupportedCapture448条/2.240任务sim＋辅助6.505sim，原ground witness/6 placement合同/同world FIFO execution装配PASS、zero1/main0已closed；result00768cd9…/release1254bb36…，23机载帧与原FIFO/PD/clip/clock全cold，25.838781291wall/87,735,513bytes、close0。原19源b125 asset/camera资格也closed；1280×720 world0仍仅一帧，非正式片/构图/FPS。两个closed组件都不因新policy重跑/失效或借给30/full program。
- **V4剩余真实链缺口仍在，不伪报五组：** dynamic-box CLIMB→NAV support/contact-owner、static deck/.20→.60的.40m能力接续、三实际placement＋整链＋goal_deck contact/连续.5s停稳终点，合法WM bootstrap/accepted200Hz owner/同96×64 anchor关联与Reach完整名义后继cost仍未齐。SupportedCapture不是原WM已建模owner；共享公开NAV观察prelude仅提案未冻结/执行，不把首次A/B静默退成VLM-only或拿旧OBS/组件帧拼history。三箱2.4×1.4×.20m/.5kg/mu.4/.8原已匹配Reach锁，scene6394740e…无数值变动，不重复索箱体许可；DeepSeek TLS profile87d38fef…/A—D cap100、7a6远端及CPU restore1/forward0不再等迁模型/key/provider。
- **J低优先级技术窗口仍按原新slot执行：** 独立CPU40,41/2线程/nice19/idleIO/RSS4GiB/J盘3GiB、单下载≤512KiB/s/≤3600wall、CPU技术≤900wall，截止**2026-11-16 04:15北京时间**（绝对截止优先、每次fresh且三组优先可让出），GPU lease0/新cohort/真实数据fit批准0。03:39仅观察J自有root已存在，不凭目录猜下载/hash/forward/训练成功；其实际进展看原件。旧02:00 slot仍过期未使用，不自动扩窗/授卡，不改他组环境/H/锁/进程。`{J}/Data-J1-new-finite-CPU-download-window-to0415.json`。

**下一步**
- 当前固定24**不再派发**，后续若需新采集须新问题/来源/停止方案与准确用途；不按winner追胜追加、不自动refit。Data保持原件可复核，Reach独立评价已到件后果；回顾oracle/时间头结构诊断不写入在线路线，不冒模型校准或方法收益。
- 优先接V4：AINav完成真实support/contact-owner/共享可行接续与终点，Reach完成合法bootstrap/真实causal IO/同anchor/完整cost。Data以新30源政策按稳定的完整新程序冻结依赖、顺序、各自有限预算/相机/并行资源，再做必要自身zero/main；**E共同资格齐即可先于WM，仍须真实完整任务成功；A—D交完整direct-live原片，所有失败/拒绝/censor保留。** 不以本批API0采集、component或旧OBS冒五组，不新增用户签字/箱参数门、不盲派已知越原域任务。J可按有效低优先级窗口做合法权重hash/CPU技术项，未来独立新用途cohort另登记，不热换7a6/冒第六arm。

**详细入口**
- fixed24最终原件/用途/24索引：`{D}/release.json`；收束源码/源pins/最终资源/错误历史：`{M}/README.md`、`{M}/latest-snapshot-pointer.json`、`{M}/fixed24-final-original-release-proof.json`；每支原release在本组consumer-deliveries，最后24索引`{K}/closed24-original-release-index.json`。
- V4最新30源/policy：`{V}/README.md`；旧静态风险审阅`{F}/`已由新policy解决，不再等strict helper；真实capture原件`{B}/consumer-deliveries/AINAV-DATA-V4-GENUINE-CAPTURE-ORIGINAL-EXECUTION-ASSEMBLY-NOT-TASK-20261116-v1/release.json`，scope`{B}/manifests/V4-capture-execution-zero-46308-20261116-v1/`（once不再执行）；旧asset/帧QA`{B}/manifests/V4-native-components-46308-20261116-v1/`。
- compute仅46308；工作目录`{B}`不是re-nav。lean代码`/home/yuanyue/main/code/reach-ability-research`/data-team-development，本地/GitHub仅code/小metadata/少数原query，raw/MJB/模型/env/视频留远端。旧46174/全部closed根不恢复；不新建chat/agent/Goal/自动化，不产生第二物理owner。
'''
(M/'README.md').write_text(f'''# fixed24最终关闭/原件交齐，不refit（{now}）\n\n24 own-zero＋24 main全部closed，原链PASS10/非PASS14=FF6/settle6/base_collision2，resource censor0；正式24原release/84public queries，481685真实200Hz命令，24097机载RGBD/24097 review/24097 direct raw帧（192×128非HD）。12到首CLIMB PREPARE/admitted，10/21 runtime collision没有原CLIMB终端，不补label；其余未达到不造CLIMB负例。\n\n所有scope usage known；原ledger含ownzero/aux合计2720.665sim/19005.873282551wall，主世界2408.425sim，不是项目端到端/货币总费或成功条件成本。高水位合计3704710741bytes不是当前disk。4geometry/8context同1 TRAIN祖先，不独立TEST/方法对照；当前critic不refit、旧TRAIN6/模型/CAL/VAL和科学库存不改，不转J用途。\n\n最终原件release **5367a3a1b0f68f7f623ba596e23a77a39f860905377588840f3bee76cb4eebf9**：{D}/release.json；本/新端24原release SHA核同。原始partial snapshots、v1 reader KeyError与修正保留，未改原release或物理。只读tool仍可用于复核，但不得再次执行旧物理driver/once控制器；无新批登记/自动refit。\n\n03:39权威H/本机mirror相同，全24closed，Data native worker0，GPU0/1原四canonical锁inode未变并释放。owned26125737472bytes/40GiB、provider quota未知，全部raw/MJB/数组留46308。不删失败或旧CAS错误/更名重跑。\n\nV4最新8105e755/30-source policy14b77d69已明确消费：共同旧H A—E同开、真实成本各计，新后继只B/D；E是无VLM/WM/新后继优化，不冒全层kernel0，不削弱C。可选strict隔离未采用且不再待决；只source/计数澄清，原19/25组件仍closed，不新跑零步。完整owner/contact/static-deck/.40m/终点与合法WM启动/真实causal/cost还缺，五main0。见{V}/README.md。\n\nJ独立低优先级CPU/下载窗口仍至04:15，不授GPU/数据fit/新cohort；03:39仅看到其root存在，不冒模型已下载。长期Data/V4任务继续，本批结束不代表研究结束。\n''')
old=(K/'README.md').read_bytes()
with(K/'README.md.before-fixed24-final-closeout').open('xb')as f:f.write(old)
(K/'README.md').write_text(f'''# fixed24已全部closed：不得重跑任何driver/once或自动追加\n\n{now}：24 own-zero＋24 main终态齐，10原链PASS/14原生失败，resource censor0；84原query与24正式原release齐，最终5367a3a1…：{D}/release.json。Data native worker0、规范锁均释放，原费用/失败/旧whole-H CAS错误均保。后续新批要新问题/源/用途/停止方案，本批不refit、不转J、不冒V4五组。\n\n最新收束入口{M}/README.md。下列旧在途说明仅历史，不重新派发/恢复或手写phase。\n\n---\n\n'''+old.decode())
old=(F/'README.md').read_bytes()
with(F/'README.md.before-source-policy-resolved').open('xb')as f:f.write(old)
(F/'README.md').write_text(f'''# 历史待决项已由03:24源owner政策解决\n\nAINav8105e755/30-source正式保留legacy-common H五组同开，新successor仅B/D；Data已收policy14b77d69，不再等另一签字/strict隔离。准确新入口{V}/README.md。以下为03:13的原静态风险核查，保留而不继续当待决门；旧19/25组件不重跑、不失效，五main0。\n\n---\n\n'''+old.decode())
proof=[]
def update(path,transform,shared=False):
 before=path.read_bytes();after=transform(before.decode()).encode();mode=stat.S_IMODE(path.stat().st_mode);backup=M/(path.name+'.before-fixed24-final-and-policy')
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
  return s[:a]+'## 当前最高执行入口：fixed24全closed/84query原件交齐不refit；V4共同旧H政策已收，五main0\n\n'+current.rstrip()+'\n'+s[b:]
 update(B/name,f)
with(M/'Data-only-final-publication-proof.json').open('x')as f:json.dump(dict(at=now,proof=proof,no_H_worker_or_program_changes=True,all_shared_peer_bytes_preserved=True),f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps(dict(at=now,shared_Data_only_updated=True,driver_snapshot=d,released_public_queries=84),ensure_ascii=False))
