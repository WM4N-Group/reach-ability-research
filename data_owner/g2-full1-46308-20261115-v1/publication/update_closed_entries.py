from pathlib import Path
import os,json,datetime,hashlib,fcntl,tempfile,stat,re,ast,subprocess,shlex,base64
B=Path('/home/yuanyue/main/work/data-team');M=Path(__file__).resolve().parent;S=Path('/home/yuanyue/main/汇总/各小组进展汇总.md');P=B/'manifests/g2-full2-46308-20261115-v1';now=datetime.datetime.now().astimezone().isoformat();sha=lambda b:hashlib.sha256(b).hexdigest();h=json.loads((B/'registry/handoff_46308_current_status_20261115.json').read_bytes());q=h['active_g2_full1_scope'];assert not q['active']and q['zero_dispatch_program_sha256']is None and q['main_dispatch_program_sha256']is None
D=B/'consumer-deliveries/AINAV-DATA-G2-46308-FULL1-LEFT-ACTUAL-20261115-v1';T=B/'consumer-deliveries/AINAV-DATA-G2-46308-REGISTERED-SCENE-SOURCE-HANDOFF-20261115-v1';v=json.loads((D/'actual-summary.json').read_bytes());assert v['source_result_passed']and all(v['nine_stream_checks'].values());proof=json.loads((M/'closed-publication-and-source-handoff-CAS.json').read_bytes());owned=proof['owned_allocated_bytes'];reserve=1610612736;capacity=(42949672960-owned)//reserve
body=f'''更新：{now}（北京时间；主计划仍53233939…；full-1真实exact3 PASS/closed/九流cold，5原query齐；三registered source/五DEV attempt索引已交，接G2新用途cohort协议而非结束总任务）

**当前状态**
- **新增full-1真实完整请求链PASS：** NAV left→PUSH(2.3,−1.8,0)→CLIMB .2/original，**119.345sim / 23869步 / 1194 RGBD及review帧**，5native options/10literal回执；首次真实CLIMB PREPARE **95.250sim/frame-000004**。同自身zero/main model92f86189…，九流cold全过、FIFO/PD/hardclip复现误差0、teardown无错。原full-1 C质量1kg/mu.3及geometry变化明确，非几何-only/单prefix因果，也不是far-bank整任务或优化收益。
- **完整原件可直接消费：** release **2bae0f2a…**，约1.11MB必要public/metadata，5原Host query与base/calibration/RGB/depth原字节/clock/semantic SHA/record-chain保留，first PREPARE按真实proposal+binding定位，不用固定query/旧95.605/后READY回填。原实际config由冻结device-only plan加原SDK bundle绝对路径组成；首版只读发布器误把bundle字段当drift而断言失败，stdio保留；修正仅核精确frozen plan＋同SHA SDK，未改native结果/程序/门/账本，无物理重跑。protocol/evidence与public分层，整包DEV不fit。
- **费用与权威已收束：** 本full-1含自身zero/两次aux **132.355sim / 814.418296ledger wall / 175664393bytes highwater**，不拿进行中stdout成本冒final，也不等全项目费用。新scope自身zero1/main1均耗、PASS closed/dispatch null，原main11:52:50才派不冒整夜运行；远端H SHA **bf035ddb…**已CAS镜像，current scope原封inactive，旧G1/full2/失败次数不变。当前本组native0/规范锁释放，不占未来lease；整个Data根20067454976bytes/40GiB、provider quota未知。
- **三源／完整分母已交，不再泛写“缺第三source”：** 新source handoff release **01e2571a…**逐SHA引用full-4 left/right、full-2 left/right、full-1 left **5个closed DEV main／3个原registered scene来源**：4链PASS/1前驱异常、4个first-PREPARE/1未达，原query合21（不增加科学库存21来源/3650query）。full-2 right仍原PUSH卸载FF交集空/无terminal回执/未请求CLIMB，不作CLIMB负标签或补第四格。5scope含zero/aux598.515sim/3722.513041ledger wall/highwater和805949466bytes，仅这5scope费用，旧未知/infra失败另列。来源数不是独立群体/稳健族/三split资格，Data未代公开信息或方法最终评价。

**正在做／下一项／独立备选**
- **G2下一具体外部交付只有新用途finite cohort协议，不再等待模型或再次经济许可。** Reach据这三原source和不完整prefix域固定：预测时点/horizon、合法scene/prefix/arm、whole-scene/祖先split、新真实采样量及功效/弱原型依据、停止/未达/资源censor；AINav沿已有有限候选/精确caller绑定。**现有5支DEV全部不得转TRAIN/CAL/VAL或fit**，不能按prefix/arm/frame/reset凑scene、自动套旧8组/24main；即使full-1单PASS也不自动放行训练。Data已给可消费源/attempt/角色清单和唯一缺项，不新增logger/NN表/经济/消费回执签字门。
- **Data独立准备与容量：** 复用已合格runner/8公共字段/原journal/SDK/私有Expat2.8.1，收到具体新协议即可新purpose/IDs/完整freeze/各自own-zero/fresh lease并容量分批。按当次整个Data根与1.5GiB/scope保守预留，纯容量可留至多{capacity}个新root；这只是预算算术，**未分配{capacity}scope/未预约卡/未授权任何12/24main**，provider quota仍未知，实际每phase fresh门。代码/小元数据本地+GitHub+新端保管，dense数组/视频/环境/权重留远端；不为迁移重复复制历史。
- **继续G2→G3→G4→G5→G6：** 新用途合格cohort首足够批次闭合才critic与常量成功/均值耗时基线，继而同域三策略、长链/未见及结论；当前fit0而不是假训练。若三源/信息仍不够，需具体有限修正问题，不自动再扫side/seed/material/新label追胜。本批closed不是长期完成，也不是等用户逐run再授权。
- **旧边界保持：** G1/full2/full1全部closed不重开；full2一PASS一PUSH异常完整原件9be124b3…；旧46174一次行政UNKNOWN停止追踪、新v1 XML失败/未知尾费/Stage-B两PASS一stop保留。center/upper-entry仍暂停不并跑，科学21/3650/strict3/TEST0、训练0；Actor/WM/DINO/真机/第二owner不开、自动化未改。

**入口**：[full-1完整原件]({D}/release.json) · [实际结果/费用/first-PREPARE]({D}/actual-summary.json) · [三源五attempt给新用途协议]({T}/release.json) · [下一具体协议缺项，不派发]({T}/prospective-new-use-admission-gap.json) · [完整失败/角色政策]({T}/source-clock-and-role-policy.json) · [当前权威镜像]({B}/registry/handoff_46308_current_status_20261115.json) · [本批详细]({M}/README.md)
'''
banner=f'''## 当前最高执行入口：full-1真实PASS/closed原件齐，三原source五DEV attempt交新用途cohort准入（{now}）

**当前native0/规范锁已释放，full-1 zero1/main1均耗、PASS closed/dispatch null，严禁重跑。** 主119.345sim/23869步/1194帧，5原query，first CLIMB PREPARE95.250sim/frame-000004，九流cold全过；release2bae0f2a…原件`{D}/release.json`。原full-1 C质量1kg/mu.3与几何变化显式，不冒geometry-only/优化收益。原Actor/init4301/12N/4s/FF/stop/QP/FIFO/成功门/私有Expat精确loader未改；03:36freeze/zero不冒main，11:52:50唯一派发后现已收束。

真实owner01a1d3aa-a0d5-7de0-b886-9d92ed5f1480；新端H active_g2_full1_scope/g2_full1_cohort已closed，镜像bf035ddb…；所有G1/full2/旧失败/次数原样保。仅46308/GPU1 UUID6d66aa68…/device51两规范锁inode3428459217、3428459218，新phase仍新qualified用途/完整freeze/自身zero/fresh lease。

**下一不是缺第三source或等用户预算：** 三源handoff01e2571a…交3原registered scene、5完整DEV main（4链PASS/1PUSH前驱异常、4PREPARE/1未达），`{T}/release.json`。目前唯一外部新训练前置是Reach-owned事前新用途finite cohort协议：具体允许scene/prefix/arm、whole-scene/祖先split、样本依据/停止/未达/资源censor，沿AINav现成源；不新增reader/logger/经济回执门。不将本DEV/旧audit/GT转fit，不以scope/prefix/seed拆scene，不盲套8组/24main。Data继续已有采样/容量准备，合格新cohort后G3—G6，不以本批closed收工。

full2 right原PUSH FF intersection异常/无terminal回执/未达CLIMB保原分母，不作CLIMB负标签；full2原件9be124b3…、G1两closed/新v1失败/旧46174一次行政UNKNOWN全部旧账不抹、不重开、不再连旧端。训练0、TEST0；WM/DINO/Actor/真机/第二owner不开，自动化未改。以下仅历史。

'''
remote=[];proofs=[]
def edit(p,new,label,peer=False):
 old=p.read_bytes();d=os.open(p.parent,os.O_RDONLY|os.O_DIRECTORY)
 try:
  fcntl.flock(d,fcntl.LOCK_EX)
  with p.open('rb')as f:
   fcntl.flock(f,fcntl.LOCK_EX);got=f.read();st=os.fstat(f.fileno());assert got==old and(p.stat().st_dev,p.stat().st_ino)==(st.st_dev,st.st_ino);(M/(label+'-before-full1-closed.md')).write_bytes(old);fd,t=tempfile.mkstemp(prefix='.'+p.name+'.full1-closed-',dir=p.parent)
   try:
    with os.fdopen(fd,'wb')as o:o.write(new);o.flush();os.fchmod(o.fileno(),stat.S_IMODE(st.st_mode));os.fsync(o.fileno())
    assert p.read_bytes()==old;os.replace(t,p);os.fsync(d)
   finally:
    if os.path.exists(t):os.unlink(t)
 finally:os.close(d)
 proofs.append(dict(path=str(p),before=sha(old),after=sha(new),peer_bytes_exact=peer))
 if p.parent==B:remote.append(dict(name=p.name,expected_sha256=sha(old),bytes=base64.b64encode(new).decode()))
s=S.read_bytes();i=s.index('## Data组'.encode());j=s.find(b'\n## ',i+1);j=len(s)if j<0 else j;new=s[:i]+('## Data组\n\n'+body).encode()+s[j:];assert new[:i]==s[:i];edit(S,new,'shared-Data',True)
for name in('AGENTS.md','README.md'):
 p=B/name;s=p.read_text();i=s.index('## 当前最高执行入口');j=s.index('## 最新用户服务器',i);edit(p,(s[:i]+banner+s[j:]).encode(),name[:-3])
p=B/'STATUS.md';s=p.read_text();a='<!-- NEXT_QUESTION_SAMPLING_CURRENT_BEGIN -->';b='<!-- NEXT_QUESTION_SAMPLING_CURRENT_END -->';i=s.index(a)+len(a);j=s.index(b,i);s=s[:i]+'\n'+body+'\n'+s[j:];s=re.sub(r'更新：[^\n]+',f'更新：{now}（北京时间；full-1真实PASS/closed/九流cold与原件齐，三源五DEV attempt接G2新用途cohort协议）。',s,count=1);edit(p,s.encode(),'STATUS')
edit(M/'README.md',('# G2 original full-1 left closed DEV source gate and prospective NEW-use handoff\n\n'+body).encode(),'detailed-README')
tree=ast.parse((P/'publish_current_progress.py').read_bytes());code=next(ast.literal_eval(n.value)for n in tree.body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='code'for t in n.targets));code=code.replace('g2-full2-46308-20261115-v1','g2-full1-46308-20261115-v1').replace('before-full2-live','before-full1-closed');r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],input=json.dumps(remote),capture_output=True,text=True,timeout=90)
for suf,t in [('stdout',r.stdout),('stderr',r.stderr),('exit',str(r.returncode)+'\n')]:(M/('closed-entry-mirror.'+suf)).write_text(t)
(M/'closed-progress-CAS-peer-proof.json').write_text(json.dumps(dict(at=now,local=proofs,remote_exit=r.returncode,peer_bytes_preserved=True,pure_capacity_root_count_not_dispatch=capacity),indent=2)+'\n');assert r.returncode==0,r.stderr;print('Full1 closed/source handoff/new-purpose protocol gap published; no peer text changed')
