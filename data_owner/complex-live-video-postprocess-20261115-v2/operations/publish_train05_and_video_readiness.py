from pathlib import Path
import json,hashlib,datetime,fcntl,os,stat,tempfile,re,ast,subprocess,shlex,base64
B=Path('/home/yuanyue/main/work/data-team');M=Path(__file__).resolve().parent;T=B/'manifests/new-critic-cohort-46308-20261115-v1';P=B/'manifests/g2-full2-46308-20261115-v1';S=Path('/home/yuanyue/main/汇总/各小组进展汇总.md');now=datetime.datetime.now().astimezone().isoformat();sha=lambda b:hashlib.sha256(b).hexdigest();plan=Path('/home/yuanyue/main/汇总/各小组下一步研究计划.md');assert sha(plan.read_bytes())=='b2fb786ec002b1e88ed4fc56a0bbfbac21d62cd788dacdda7d9fceb1a774c5a9';h=json.loads((B/'registry/handoff_46308_current_status_20261115.json').read_bytes());q=h['active_new_critic_cohort_scope'];assert q['candidate_id']=='new_critic_06_full4_right_lateral_minus_0p04'and q['active'];cursor=json.loads((T/'TRAIN01_TO05_CLOSED_RELEASE_CURSOR_NOT_FIT.json').read_bytes());assert cursor['closed_and_originals_published']==5;qa=json.loads((M/'POSTPROCESS_QA_V2_NOT_COMPLEX_RESULT.json').read_bytes());assert qa['pair']['exact_RGB_codec_roundtrip_verified']and qa['task_T_COMPLEX_actual_videos_still0']
body=f'''更新：{now}（北京时间；主计划仍14:00版b2fb786e…；新用途TRAIN已发布01—05：3PASS/2决策后原门失败，06执行中，完整六支gate/真实fit尚未开放；复杂首对优先任务原片后处理已备但实测0）

**当前状态**
- **真实新数据已闭合/独立发布5支，不等整批：** 01原left121.085sim/24217步PASS，02原right109.865sim/21973步PASS；03plus-left118.715sim/23743command步原CLIMB **stop_deadline**；04plus-right104.665sim/20933command步原 **integrated_unselected_or_native_forbidden_contact:middle**；05minus-left121.130sim/24226步PASS。04 release **1ff9998a…**，05 **3906bdfb…**，前三原件f253b6af…/daa22f04…/6f662bb4…保留。全部自身zero/main各一次、closed/九流cold全过，PD/FIFO/hardclip误差0；cold PASS不把两原生失败洗成成功，也不补literal failed terminal回执或成功成本。
- **失败的时点/分母与费用：** 04首CLIMB PREPARE86.580sim→准备NAV succeeded100.005→CLIMB started100.010→104.665原contact guard触发；03同样是PREPARE之后CLIMB原stop失败，不是上游未达或资源censor。Data保原trace/started回执及terminal缺失，具体训练标签由Reach按冻结协议原源验证，不由Data造NN表或降门。当前只核五closed scope：**640.510sim含自身zero/aux、3915.810332ledger wall、850534544bytes独立scope高水位和**；不是六支/全项目最终费用，第06尚未闭合不补0。
- **当前06继续，绝不提前fit/跨heldout：** 05于14:17:14 CAS PASS closed，06新program ad3ae291…自身zero/新只读候选审计接续，最新权威已main1/zero1，实际PID34325在途；14:19:58 ledger open/26.320含auxsim/95.009631wall仅快照。剩余一支结束后物理停在原TRAIN6门；即使目前3成功/2失败也必须完整schedule/source/两prefix与两公共状态/48槽全齐，由Reach派生一次fit或No-Go，CAL7—9/VAL10—12仍阻。原声明6/3/3、Actor/init4301/12N/4s/FF/QP/FIFO/stop、240sim含zero/aux/2400wall/1GiB/zero180wall与所有旧scope不改，资源/完整性错停新增，不换seed挖失败。
- **之前plus的纯读审计错误不冒物理失败/重跑：** old zero-cold literal original断言保留原代码/stdio；只加v2按精确frozen payload核candidate、保INPUT8/world0/model等原检查。03zero没重跑，原pipeline一启动标记与停止档案保留；显式continuation只执行03尚未claim的main/04—06原未派阶段，现每支仍zero≤1/main≤1，无旧根恢复或热改原frozen程序。

**正在做／下一项／独立备选**
- **T-COMPLEX-01已接收、资源优先，场景/策略未交则不假排队。** 主目标为同信息/技能/候选/成功门/合理预算的局部贪心vs有限多步前瞻，同场景/初态、各1新main/各自own-zero，完整成功能力优先，不预设输赢；不少于2环境重构/3有效决策、不等critic或100条采齐。Data原接收档案已给，当前真实复杂scene/A-B包仍缺，**实际复杂native/视频均0**；当前TRAIN6冻结生命周期先完整收束，首个安全合格资源窗口优先本对比，批量长期目标继续。
- **视频交付工具已做实际工程QA，不冒复杂结果/HD实拍：** 复用原direct-live raw_frames/FFV1，新增同physical tick并排、短臂结束后黑屏＋原终止时间/状态、字幕只在源像素外，保完整frame↔tick/time映射、不拉伸/插值/重放。用已closed TRAIN01/02的原192×128母版，只读验证A/B各1×无损RGB与并排1211帧RGB解码逐字节一致；这只是后处理QA，**不是新复杂实验或高清片**。旧1-slice FFV1在384×160并排被真实codec拒绝，保错误/partial，增量4-slice修正后过；960×540仅1张明确SOFTWARE codec smoke通过，不是GL/实时高清资格。新场景仍须共同冻结相机覆盖/实际offscreen/≥10Hz负载及空间预算，不能把192放大冒960；缺原片任务视频部分不完成，不补跑closed arm。全部QA视频留新端，未回传大媒体。
- **双GPU与后续批次资源准备仍有效、未冒已并发native：** GPU0 UUID297c1146…新规范inode3428729629/3428729630、binding50d6365e…、逐GPU资源适配8软件检查/实际锁计数器probe过；原GPU1 UUID6d66aa68…/inode3428459217、3428459218与当前lease不动。现冻结TRAIN6仍全局Data进程扫描串行，不能另开世界触发它/绕锁热改；后续新批按同owner每GPU起步1worker、新slot/program/output/RNG/账本/自身zero/GL/实测峰值后扩。32核/122406567936byte cgroup内存已读核，不改配额；provider存储quota仍未知。按旧剩余承诺＋owned＋新2slot滚动容量可容，不一次承诺12/24root、不删必要原证据。复杂首对合格后，再按AINav矩阵/Reach新用途split与预定重复/去冗余/停止推进百级/≥10有意义组，不把目标数当已采成果或独立功效。
- **旧边界保持：** 5个旧DEV/旧audit/GT不转fit、full2right未达CLIMB不造负行；旧UNKNOWN/XML/StageB失败账与原科学库存21/3650/strict3/TEST0不回写，本新cohort另列。实际fit0，WM/DINO/Actor/真机/第二owner不开，自动化未改；代码/小metadata本地-GitHub-新端保管，dense/环境/权重/视频留46308。

**入口**：[TRAIN01—05已闭合原件索引，非fit许可]({T}/TRAIN01_TO05_CLOSED_RELEASE_CURSOR_NOT_FIT.json) · [04原contact负结果]({B}/consumer-deliveries/AINAV-DATA-NEW-CRITIC-46308-ORDINAL-04-ACTUAL-20261115-v1/release.json) · [05实际PASS]({B}/consumer-deliveries/AINAV-DATA-NEW-CRITIC-46308-ORDINAL-05-ACTUAL-20261115-v1/release.json) · [当前接续日志]({T}/TRAIN03_06-reviewed-continuation.stdout) · [复杂任务接收/未派发]({M}/OWNER_INTAKE_NOT_DISPATCH.json) · [后处理QA明确非复杂实测]({M}/POSTPROCESS_QA_V2_NOT_COMPLEX_RESULT.json) · [双GPU准备]({B}/manifests/bulk-dual-gpu-preparation-46308-20261115-v1/BULK_NEXT_BATCH_INTAKE_NO_DISPATCH.json)
'''
banner=f'''## 当前最高执行入口：新用途TRAIN01—05原件齐（3PASS/2原门失败），06执行中；复杂首对/双GPU资源与原片后处理准备（{now}）

**当前原2f82530d…TRAIN6不热扩，01/02/05 PASS，03原CLIMB stop_deadline，04原integrated_unselected_or_native_forbidden_contact:middle均closed/九流cold/独立原件齐。** 无literal failed terminal回执不补；两失败均在first PREPARE之后，资源censor=false，但训练标签/48槽/全schedule门仍由Reach原源核。当前06 programad3ae291…自身zero/main各1已派，PID34325main在途，不能提前fit或派CAL/VAL。五closed原件索引`{T}/TRAIN01_TO05_CLOSED_RELEASE_CURSOR_NOT_FIT.json`，不是fit许可。

原plus只读zero auditor literal original误报已按精确frozen plan用新增v2修正，原reader/错误/停止文件不改，03zero不重跑、显式continuation只派未claim阶段。原Actor/init4301/12N/4s/FF/QP/FIFO/stop/SDK/Expat与240sim/2400wall等限制保持；同真实owner01a1d3aa-a0d5-7de0-b886-9d92ed5f1480，权威active_new_critic_cohort_scope/new_critic_cohort_v1。

最新主计划b2fb786e…优先T-COMPLEX-01复杂A/B和完整live母版，不等critic/百级采齐。Data已真实接收，但场景/同域两真实策略未交，native/视频0不冒已排队。已复用/验证A/B1×及同tick并排CPU编码、短臂结束黑屏/原clock/不拉伸；仅用closed TRAIN低清片做QA、960×540仅software codec smoke，不冒复杂或HD原片，原任务仍0。GPU0 UUID297c1146…/新inode3428729629、3428729630资源适配和probe已备，GPU1原锁不动；当前冻结TRAIN全局串行保护不绕过，新包才逐GPU新资格，一卡一worker起测峰值后扩。滚动容量、不删原证据、百级/≥10组是后续目标非现成果。

旧5DEV/旧audit/GT不fit，旧closed/UNKNOWN/失败/费用均保、不连旧端；fit0/TEST0，WM/DINO/Actor/真机/第二owner不开，自动化不改。当前详细`{T}/README.md`；以下仅历史。

'''
remote=[];proof=[]
def edit(p,new,label,peer=False):
 old=p.read_bytes();d=os.open(p.parent,os.O_RDONLY|os.O_DIRECTORY)
 try:
  fcntl.flock(d,fcntl.LOCK_EX)
  with p.open('rb')as f:
   fcntl.flock(f,fcntl.LOCK_EX);got=f.read();st=os.fstat(f.fileno());assert got==old and(p.stat().st_dev,p.stat().st_ino)==(st.st_dev,st.st_ino);(M/(label+'-before-TRAIN05-video-ready.md')).write_bytes(old);fd,t=tempfile.mkstemp(prefix='.'+p.name+'.TRAIN05-video-',dir=p.parent)
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
p=B/'STATUS.md';s=p.read_text();a='<!-- NEXT_QUESTION_SAMPLING_CURRENT_BEGIN -->';b='<!-- NEXT_QUESTION_SAMPLING_CURRENT_END -->';i=s.index(a)+len(a);j=s.index(b,i);s=s[:i]+'\n'+body+'\n'+s[j:];s=re.sub(r'更新：[^\n]+',f'更新：{now}（北京时间；TRAIN01—05原件齐3PASS/2原门失败、06执行；复杂任务仍未派，原片后处理工程QA已备）。',s,count=1);edit(p,s.encode(),'STATUS')
edit(T/'README.md',('# Fixed TRAIN6 partial original releases and complex live-video preparation\n\n'+body).encode(),'TRAIN-detailed-README')
tree=ast.parse((P/'publish_current_progress.py').read_bytes());code=next(ast.literal_eval(n.value)for n in tree.body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='code'for t in n.targets));code=code.replace('g2-full2-46308-20261115-v1','new-critic-cohort-46308-20261115-v1').replace('before-full2-live','before-TRAIN05-video-ready');r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],input=json.dumps(remote),capture_output=True,text=True,timeout=90)
for suf,t in [('stdout',r.stdout),('stderr',r.stderr),('exit',str(r.returncode)+'\n')]:(M/('TRAIN05-video-entry-mirror.'+suf)).write_text(t)
(M/'TRAIN05-video-readiness-CAS-peer-proof.json').write_text(json.dumps(dict(at=now,local=proof,remote_exit=r.returncode,other_groups_exact_bytes_preserved=True,H_and_native_program_not_modified=True),indent=2)+'\n');assert r.returncode==0,r.stderr;print('TRAIN5 closed records and complex postprocess readiness published; no complex experiment claimed')
