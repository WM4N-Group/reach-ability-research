from pathlib import Path
import json,datetime,hashlib,fcntl,os,stat,tempfile,re,ast,subprocess,shlex,base64
B=Path('/home/yuanyue/main/work/data-team');M=Path(__file__).resolve().parent;T=B/'manifests/new-critic-cohort-46308-20261115-v1';P=B/'manifests/g2-full2-46308-20261115-v1';S=Path('/home/yuanyue/main/汇总/各小组进展汇总.md');now=datetime.datetime.now().astimezone().isoformat();sha=lambda b:hashlib.sha256(b).hexdigest();plan=Path('/home/yuanyue/main/汇总/各小组下一步研究计划.md');assert sha(plan.read_bytes())=='b2fb786ec002b1e88ed4fc56a0bbfbac21d62cd788dacdda7d9fceb1a774c5a9';h=json.loads((B/'registry/handoff_46308_current_status_20261115.json').read_bytes());co=h['new_critic_cohort_v1'];q=h['active_new_critic_cohort_scope'];assert q['candidate_id']=='new_critic_04_full4_right_lateral_plus_0p04'and q['active']and q['phase']=='CAS_DISPATCHED_MAIN'
Ds=[B/'consumer-deliveries'/('AINAV-DATA-NEW-CRITIC-46308-ORDINAL-%02d-ACTUAL-20261115-v1'%n)for n in(1,2,3)];summaries=[]
for D in Ds:
 v=json.loads((D/'release.json').read_bytes());assert all(sha((D/n).read_bytes())==s for n,s in v['files'].items());summaries.append(v['actual_summary'])
assert[s['source_result_passed']for s in summaries]==[True,True,False]and summaries[-1]['error']=='stop_deadline'and not summaries[-1]['resource_censored'];sum_sim=sum(s['scope_including_own_zero_and_aux_sim_s']for s in summaries);sum_wall=sum(s['scope_ledger_wall_s']for s in summaries);sum_bytes=sum(s['scope_output_highwater_bytes']for s in summaries)
body=f'''更新：{now}（北京时间；已接最新“14:00版”复杂成功能力/临时T-COMPLEX-01优先计划b2fb786e…（含13:30批量双卡授权）；当前冻结TRAIN保持原六支：01/02 PASS、03原CLIMB deadline失败均closed/原件齐，04 main在途；并行准备后续双卡批次）

**当前状态**
- **临时优先任务T-COMPLEX-01已由Data真实接收但未假排队。** 已完整读任务书a3ade42a…/task registry22256a6b…，登记`/home/yuanyue/main/work/data-team/manifests/T-COMPLEX-01-intake-20261115-v1/OWNER_INTAKE_NOT_DISPATCH.json`。目标是双通路多箱/≥2环境重构/≥3有效决策、局部贪心vs有限多步前瞻各1新main与各自own-zero、原生成功能力优先，不预设赢家；不等critic/百级采齐。当前可执行scene/A-B方法包未交，Data只确认接收/资源准备，实际queue/native/video均0，不拿旧warehouse或短链顶替。当前TRAIN6继续不热改，首个安全合格资源窗口优先该任务；批量长期目标不取消。
- **最新授权已落实到接续，不热扩当前批次。** 用户新授权目标≥100事前登记新用途attempt/≥10有意义组，后续首批约12—24、合格组先采、计划性重复须有目的/随机化/祖先/停止，不拿完全相同输入或prefix改名凑场景。当前2f82530d…/6TRAIN＋3CAL＋3VAL冻结范围、TRAIN gate/每root一次/原失败与closed根不改；不是把六支当全项目总上限，也不重问经济许可/另等全部10组齐。
- **新用途当前3个真实闭合结果：** 01原left **121.085sim/24217步/1211帧 PASS**，releasef253b6af…；02原right **109.865sim/21973步/1099帧 PASS**，release**daa22f04…**；03 plus-left **118.715sim/23743实际command步/1188帧 FAILED_NO_RETRY stop_deadline**，release**6f662bb4…**。03 first CLIMB PREPARE97.285sim→准备NAV succeeded110.720→CLIMB started110.725→原stop_deadline终止；是决策后的原生CLIMB失败、不是资源censor，但无literal failed terminal回执仍保缺失，不把失败elapsed当成功cost。三支九流cold全过/PD/FIFO/hardclip误差0只证记录完整，不能把03洗成PASS。合3scope含zero/aux **{sum_sim:.3f}sim/{sum_wall:.6f}ledger wall/{sum_bytes}bytes高水位和**，14原query，不是全项目总费或独立14场景。
- **只读审计错误已正确解决，物理未retry：** 03实际zero已PASS，旧cold reader硬编码candidate==original使plus误断言，13:31纯读阶段停住、main0。原错误stdio/原frozen reader与pipeline字节不动；新增只读v2按精确frozen plan核实际候选并保原INPUT8/world0/model/流全部检查，zero不重跑。核清后显式continuation只派03尚未claim的main及04—06原未执行阶段；03 13:50:16 closed后04自身zero/coldv2通过，**13:51:26唯一main CAS**，当前main在途。05/06未派，CAL/VAL仍硬阻，未启动训练。
- **第二张GPU只做资源准备，不冒双卡native已跑：** fresh GPU0 UUID **297c1146…**（4090，24080MiB空闲快照）新canonical device51/inode **3428729629/3428729630**、binding **50d6365e…**已建立，独立争用阻断/释放核过；GPU1 UUID6d66aa68…/原inode3428459217/3428459218/绑定SHAada256e7…字节与在途lease不动。同一Data owner的最小PerGpuLease适配保ownGPU3GiB/共享1GiB余量、CUDA初始化后PID观测缺失fail-closed，8软件检查和真实GPU0“锁＋计数器”probe过，**无Actor/GL/Runtime/world/own-zero**，GPU0 native资格/真实双卡吞吐尚未取得。

**正在做／下一项／独立备选**
- **当前TRAIN6继续并保门：** 04→05→06逐scope独立zero/main/cold/close、失败不补样/不换seed。六支闭合后Reach核≥2prefix/≥2公共状态/≥3成功/≥1真实决策后native失败及48槽/source；当前2成功＋1失败不提前fit或放CAL/VAL。原Actor/init4301/12N/4s/FF/QP/FIFO/stop及外层240sim含zero/aux、2400wall、1GiB/zero180wall均保持；无热改frozen control/worker/限制。
- **复杂首对优先、后续首批12—24及双卡资源并行准备：** 起步每卡1worker，同一owner、每slot独立world/output/RNG/账本/phase权威，新program freeze/各自own-zero/GL与真实峰值验证后再增并发。当前冻结TRAIN6控制器仍“扫描所有Data worker”的串行保护，**不能另开GPU0世界导致它下个phase误停，更不能绕/删原锁或热改**；新批才采用逐GPU slot准入。不是为未来训练预留空卡，真实原因是当前冻结生命周期/新批准入尚未结束；未来训练未起时两卡可采，Reach训练须统一资源协调。
- **容量按滚动波次，不伪称能一次预留24root：** 13:45整个Data根20551849984bytes/40GiB，仍保旧10个未闭合承诺root各1.5GiB保守预留，再加新2slot×1.5GiB，合39879202816bytes可容；一次再预留新12/24root则不满足当前cap。新批按每波fresh owned＋所有旧剩余承诺＋新slot预留核验，容量/渲染/OOM风险停新增、保全部失败/原始证据，不删必要数据/不挪出owned口径/不把provider quota未知当无限空间。共享静态review-model cache去重仅已识别的后续方案，原实现有并发创建race，使用前需单独cache锁；**尚未实施/未声称已释放空间**。
- **复杂任务与新批当前具体方法输入：** 复杂任务先接AINav真实场景/公开候选/技能映射与Reach同信息同目标两真实策略/共同预算；Data负责装配、A/B各一次freeze/zero/lease/live原片，不代造算法。视频需新场景共同相机优先960×540/≥10Hz，先验实际offscreen/负载/储存并freeze；当前192×128原片不能放大冒HD，失败也交完整母版、1×同钟并排/结束标记，不重渲染/插帧/补跑closed。随后批量接AINav矩阵及Reach新用途/whole-scene祖先split、预定重复/去冗余/失败与未达/停止；资源侧入口已交，不新增logger/预算/消费签字门，也不等待所有10组或100条才首训。有包即新批freeze/资源/真实资格后接续，不代两组编算法或自行凑scene。旧5DEV/旧audit/GT不fit，full2right原前驱异常不作CLIMB负行；旧UNKNOWN/XML/StageB等账和旧科学库存21/3650/strict3/TEST0保留，另列本新cohort，真实fit0，WM/DINO/Actor/真机/第二owner不开、自动化不改。代码已本地/GitHub/新端同步，dense/视频/环境/权重留远端。

**入口**：[当前TRAIN采集/审核修正]({T}/README.md) · [02完整原件]({Ds[1]}/release.json) · [03原生deadline负结果]({Ds[2]}/release.json) · [只读修正来源]({T}/READONLY_ZERO_CANDIDATE_AUDITOR_CORRECTION_v2.json) · [明确未执行phase接续日志]({T}/TRAIN03_06-reviewed-continuation.stdout) · [双卡资源/滚动容量准备]({M}/BULK_NEXT_BATCH_INTAKE_NO_DISPATCH.json) · [GPU0实际资源probe，非native]({M}/GPU0-adapter-actual-resource-probe.json) · [当前权威镜像]({B}/registry/handoff_46308_current_status_20261115.json)
'''
banner=f'''## 当前最高执行入口：已接最新复杂任务优先版及批量双卡授权，当前TRAIN3closed（2PASS/1原CLIMB deadline）、04 main在途（{now}）

**主计划现b2fb786e…（文档标“14:00版”），临时T-COMPLEX-01复杂A/B及原片优先、不等critic/100条；原大批量/场景覆盖/双GPU仍授权，同一Data owner，当前TRAIN6不热扩。Data已读task并登记接收；可执行scene/两真实策略未交，实际排队/物理/视频0，不冒已跑对比。** 01/02真PASS，03 plus-left在原CLIMB stop_deadline失败，三支均closed/九流cold/原件齐；03 first PREPARE97.285→NAV成功110.720→CLIMB started110.725、118.715sim终止，无literal failed terminal回执不补。02release daa22f04…/03release6f662bb4…。当前04自身zero/cold通过、13:51:26唯一main在途；05/06未派，六支完整gate前不fit/CAL/VAL。

03之前只读zero auditor的literal original断言已用新增v2按精确frozen candidate修正；原bad reader/错误stdio/物理程序/原pipeline字节保留，03 zero不重跑，显式continuation只跑尚未claim的03main及04—06阶段。无旧scope恢复/失败换ID追跑。当前权威仍active_new_critic_cohort_scope/new_critic_cohort_v1、同真实窗口01a1d3aa-a0d5-7de0-b886-9d92ed5f1480。

**双卡新批资源层已准备，未冒native并发：** 新GPU0 UUID297c1146…/device51新规范inode3428729629、3428729630/binding50d6365e…真实资源锁probe过；原GPU1 UUID6d66aa68…/inode3428459217、3428459218不动。最小逐GPU Lease8软件检查过，但无GPU0 Actor/GL/world/native资格，未开新bulk scope。当前冻结TRAIN6仍全局进程扫描串行，不绕锁/热改；后续首批12—24起步一卡一worker，新freeze/自身zero/峰值后再扩，容量按2slot滚动、不一次承诺24root、不删原证据。详`{M}/BULK_NEXT_BATCH_INTAKE_NO_DISPATCH.json`。

原Actor/init4301/12N/4s/FF/QP/FIFO/stop/Expat/当前240sim与2400wall等门不改，原5DEV/旧audit/GT不fit；旧UNKNOWN/失败/费用/closed根保持、不连旧端。复杂任务要求同场景/同初态/同候选/观测/公平预算两算法，各1新main及完整原live母版；旧192×128/warehouse/回放不顶替，失败不补跑。目标≥100新用途attempt/≥10有意义组仍是长期接续目标，非已有资格或已大量运行。真实fit0/TEST0，WM/DINO/Actor/真机/第二owner不开，自动化不改。当前详细`{T}/README.md`，以下仅历史。

'''
remote=[];proof=[]
def edit(p,new,label,peer=False):
 old=p.read_bytes();d=os.open(p.parent,os.O_RDONLY|os.O_DIRECTORY)
 try:
  fcntl.flock(d,fcntl.LOCK_EX)
  with p.open('rb')as f:
   fcntl.flock(f,fcntl.LOCK_EX);got=f.read();st=os.fstat(f.fileno());assert got==old and(p.stat().st_dev,p.stat().st_ino)==(st.st_dev,st.st_ino);(M/(label+'-before-bulk-plan-adoption.md')).write_bytes(old);fd,t=tempfile.mkstemp(prefix='.'+p.name+'.bulk-next-',dir=p.parent)
   try:
    with os.fdopen(fd,'wb')as o:o.write(new);o.flush();os.fchmod(o.fileno(),stat.S_IMODE(st.st_mode));os.fsync(o.fileno())
    assert p.read_bytes()==old;os.replace(t,p);os.fsync(d)
   finally:
    if os.path.exists(t):os.unlink(t)
 finally:os.close(d)
 proof.append(dict(path=str(p),before=sha(old),after=sha(new),peer_bytes_exact=peer))
 if p.parent==B:remote.append(dict(name=p.name,expected_sha256=sha(old),bytes=base64.b64encode(new).decode()))
s=S.read_bytes();i=s.index('## Data组'.encode());j=s.find(b'\n## ',i+1);j=len(s)if j<0 else j;new=s[:i]+('## Data组\n\n'+body).encode()+s[j:];assert new[:i]==s[:i];edit(S,new,'shared-Data',True)
for name in('AGENTS.md','README.md'):
 p=B/name;s=p.read_text();i=s.index('## 当前最高执行入口');j=s.index('## 最新用户服务器',i);edit(p,(s[:i]+banner+s[j:]).encode(),name[:-3])
p=B/'STATUS.md';s=p.read_text();a='<!-- NEXT_QUESTION_SAMPLING_CURRENT_BEGIN -->';b='<!-- NEXT_QUESTION_SAMPLING_CURRENT_END -->';i=s.index(a)+len(a);j=s.index(b,i);s=s[:i]+'\n'+body+'\n'+s[j:];s=re.sub(r'更新：[^\n]+',f'更新：{now}（北京时间；已接最新复杂首对优先＋批量双GPU授权；TRAIN3closed/04main，后续滚动双卡资源已备但未native派发）。',s,count=1);edit(p,s.encode(),'STATUS')
edit(T/'README.md',('# Current fixed TRAIN6 and 13:30 successor bulk preparation\n\n'+body).encode(),'TRAIN-detailed-README')
tree=ast.parse((P/'publish_current_progress.py').read_bytes());code=next(ast.literal_eval(n.value)for n in tree.body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='code'for t in n.targets));code=code.replace('g2-full2-46308-20261115-v1','new-critic-cohort-46308-20261115-v1').replace('before-full2-live','before-bulk-plan-adoption');r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],input=json.dumps(remote),capture_output=True,text=True,timeout=90)
for suf,t in [('stdout',r.stdout),('stderr',r.stderr),('exit',str(r.returncode)+'\n')]:(M/('current-entry-mirror.'+suf)).write_text(t)
(M/'bulk-plan-adoption-CAS-peer-proof.json').write_text(json.dumps(dict(at=now,latest_main_plan_sha256=sha(plan.read_bytes()),local=proof,remote_exit=r.returncode,other_groups_bytes_preserved=True,frozen_programs_H_and_phase_counts_not_changed_by_publication=True),indent=2)+'\n');assert r.returncode==0,r.stderr;print('Latest bulk plan, actual TRAIN02/03 closure and readonly resource preparation published; peer sections untouched')
