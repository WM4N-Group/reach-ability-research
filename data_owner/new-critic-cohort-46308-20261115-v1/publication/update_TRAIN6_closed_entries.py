from pathlib import Path
import json,hashlib,datetime,fcntl,os,stat,tempfile,re,ast,subprocess,shlex,base64
B=Path('/home/yuanyue/main/work/data-team');M=Path(__file__).resolve().parent;P=B/'manifests/g2-full2-46308-20261115-v1';S=Path('/home/yuanyue/main/汇总/各小组进展汇总.md');now=datetime.datetime.now().astimezone().isoformat();sha=lambda b:hashlib.sha256(b).hexdigest();h=json.loads((B/'registry/handoff_46308_current_status_20261115.json').read_bytes());co=h['new_critic_cohort_v1'];assert not h['active_new_critic_cohort_scope']['active']and co['TRAIN_native_collection_complete']and not co['TRAIN_gate_passed']and co['training_fit_manifest_sha256']is None
D=B/'consumer-deliveries/AINAV-DATA-NEW-CRITIC-46308-TRAIN6-COMPLETE-20261115-v1';v=json.loads((D/'actual-cohort-summary.json').read_bytes());assert v['requested_chain_PASS']==4 and v['requested_chain_native_error']==2 and v['main_attempts']==6;publication=json.loads((M/'TRAIN6-complete-publication-CAS.json').read_bytes());assert publication['no_owned_native_processes']and publication['CAL_VAL_counts0_preserved']
body=f'''更新：{now}（北京时间；主计划仍14:00版b2fb786e…；新用途TRAIN6已全closed/九流cold/原始完整包齐：4PASS/2原门失败，物理按协议停门；不提前激活fit或CAL/VAL）

**当前状态**
- **TRAIN6已真实完整收束，而非只跑完程序：** 01 original-left121.085sim PASS、02 original-right109.865 PASS、03plus-left118.715原CLIMB stop_deadline、04plus-right104.665原integrated_unselected_or_native_forbidden_contact:middle、05minus-left121.130 PASS、**06minus-right110.450 PASS**。06 14:29:58实际结束、14:30:03 CAS PASS closed；所有scope自身zero1/main1耗完/dispatch null、无retry/替代seed/旧根恢复，6支九流cold/原200Hz与RGBD/review全过、PD/FIFO/hardclip复现误差0。两失败有原CLIMB started/硬停止源，但缺literal failed terminal仍保缺失，非资源censor，不以cold PASS洗成native成功。
- **完整原件/边界/分母已交：** 组合release **13758867…**逐SHA引用6独立原件，06 release **c4d2f8d8…（精确以child-releases索引为准）**；保原bytes/clock/Host实际Observation/首原judgment→exact preparation binding，6个first-PREPARE、2prefix、精确原public45D状态2个（质量计数、非NN表），**27原query**。whole scene仍1个TRAIN祖先，不冒6独立scene或功效。全部是12:41事前登记之后真实新用途采集，旧5DEV不重标。Data没有代造训练行/给失败补terminal回执/nearest后READY回填/把失败elapsed当成功cost。
- **六scope真实费用/吞吐已给，不填未知峰值：** 共 **763.970sim含自身zero/12次aux、4642.471546ledger wall、1013819924bytes独立scope高水位和**，全部usage known，仅这6scope不冒全项目成本。首zero CAS→末main closed日历窗5206.804089wall，约**4.148attempt/h（其中2.766成功链/h）**；按实际native ledger口径4.653attempt/h，二者不混。实际worker RSS峰值2393833472bytes；原frozen报告没存GPU峰值/CPU time/IO带宽，明确None，不拿3GiB cap或瞬时空闲当实测峰值。
- **权威/资源已收束：** H已CAS镜像 **6a085ccf…**，active_new_critic_cohort_scope保持inactive/dispatch null，cohort明确TRAIN6_CLOSED_ORIGINALS_PUBLISHED_AWAIT_REACH_SOURCE_LABEL_FEATURE_GATE；CAL7—9/VAL10—12各zero/main0保持、TRAIN_gate_passed仍false/fit manifest None，本组native0、两GPU规范锁都空闲（不是未来lease）。整个Data根21126021632bytes/40GiB、provider quota未知。只读cold literal original误判/增量v2/未claim阶段接续原档保留，未改原program/Actor/门/次数，原所有旧scope与失败账保持。

**正在做／下一项／独立备选**
- **G2→G3交完整源门，不凭4/2数字宣布可训：** Reach可直接用6新source原query/原READY/原CLIMB事实验证48槽/age/角色/scene祖先/完整schedule及≥3成功/≥1真实决策后native失败/两状态。通过才引用原2f82530d…派生训练manifest、一次TRAIN-only fit＋常量score/均值耗时基线；失败No-Go不fit/不补样/不派heldout。当前Data未激活fit/qualified flag，**CAL/VAL不会自动派**；后续若合格需新显式gate/fit绑定准入，不热改当前冻结controller。原failed receipt缺失/UNKNOWN不能按error字符串强造负类凑门。
- **T-COMPLEX-01优先资源窗口已空，但缺可执行scene/两真实策略而非许可：** Data真实接收档案已给；当前A/B physical0/videos0，不用旧warehouse或短链/手写路线/GT正确顺序替代。不等critic/百级采齐，AINav真实场景/候选/技能映射＋Reach同信息/预算贪心与有限多步策略合格即新program/各自zero/main/lease、完整成功与失败原件；原0.2平台NAV→PUSH未解决域不能默默使用。当前已无旧TRAIN在途，不再把其全局进程扫描当实时占卡理由；但未来并发仍须逐GPU新slot准入/本program zero与GL真测。
- **可独立部分已备，不伪报实验：** GPU0 UUID297c1146…新规范inode3428729629/3428729630、binding50d6365e…/逐GPU Lease8检查与真实锁计数器probe已过，GPU1原inode3428459217/3428459218不动；还没有GPU0 native/GL资格或真实双卡吞吐。视频A/B各1×与同tick并排/结束黑屏字幕/无插值、不拉伸已用旧closed TRAIN192×128原片做工程QA并逐字节RGB校验；960×540仅software codec smoke，**复杂/HD实拍仍0**。新场景需先freeze共同相机/真实offscreen/≥10Hz负载/存储上限，不能把192放大或用QA视频冒新任务，缺原片不补跑closed。
- **后续扩量不止这6条：** 最新百级/≥10有意义组与12—24组织建议继续有效，合格组先采、不等10组全齐；Data两卡起步各1worker并测真实峰值/CPU/IO后扩，统一owner/逐slotworld/RNG/output/账本。按owned＋旧未完承诺＋新波次reserve滚动容量，保全部证据、quota未知不当无限空间；不为刷数复制同输入/改prefix label凑scene。旧5DEV/audit/GT不fit、旧46174行政UNKNOWN不追踪、XML/StageB与未知尾费另保；旧科学库存21/3650/strict3/TEST0不回写，本新cohort另列。真实fit0，WM/DINO/Actor/真机/第二owner不开、自动化未改，代码小metadata本地-GitHub-新端，dense/权重/env/视频留远端。

**入口**：[完整新用途TRAIN6原件组合]({D}/release.json) · [6attempt与literal outcome/缺失]({D}/all-six-attempts-and-literal-outcomes.json) · [完整费用/质量]({D}/actual-cohort-summary.json) · [实际吞吐/未知GPU峰值不补造]({M}/TRAIN6_OBSERVED_THROUGHPUT_NO_INVENTED_GPU_PEAK.json) · [最新权威镜像]({B}/registry/handoff_46308_current_status_20261115.json) · [复杂任务接收但未派]({B}/manifests/T-COMPLEX-01-intake-20261115-v1/OWNER_INTAKE_NOT_DISPATCH.json) · [后处理QA非复杂实测]({B}/manifests/T-COMPLEX-01-intake-20261115-v1/POSTPROCESS_QA_V2_NOT_COMPLEX_RESULT.json)
'''
# Actual child SHA is used rather than a hand-written prefix.
child6=json.loads((D/'child-releases.json').read_bytes())[-1]['release_sha256'];body=body.replace('c4d2f8d8…（精确以child-releases索引为准）',child6[:8]+'…')
banner=f'''## 当前最高执行入口：TRAIN6已全closed/原件齐4PASS＋2原门失败，按门停物理，接Reach源/特征/标签门及复杂任务（{now}）

**当前native0，两GPU规范锁空闲；TRAIN01..06各zero1/main1已耗、全部closed/dispatch null，严禁重跑。** 01/02/05/06原请求链PASS，03stop_deadline、04原forbidden_contact:middle两失败保原trace/started/terminal回执缺失，六支九流cold全过只证记录完整。完整release13758867…/27原query/6真实first-PREPARE、1TRAIN scene2prefix/2原public45D状态。原件`{D}/release.json`。

权威active_new_critic_cohort_scope inactive，new_critic_cohort_v1已完整发布待Reach门，H镜像6a085ccf…；同真实owner01a1d3aa-a0d5-7de0-b886-9d92ed5f1480。TRAIN_gate_passed=false/fit manifest None，CAL7..12 zero/main0不变；**Data不凭4/2提前宣布可训，完整48槽/原源失败监督/角色/schedule通过才一次fit，否则No-Go不补样。** 旧bad readonly auditor/错误/新增v2/明确未claim阶段接续保档，native冻结程序/Actor/原12N/4s/FF/QP/FIFO/stop及成本/次数不改。

最新主计划b2fb786e…优先T-COMPLEX-01：当前资源已空，不再说旧TRAIN占卡；可执行复杂scene/同域A-B方法尚未交，实际native/video0，不等critic或100条齐但也不虚造场景/手工路线/旧片。GPU0资源层/逐GPU最小适配已验，GPU0原生/GL尚未资格，未来新scope必须own-zero。并排后处理只做旧TRAIN低清原片QA及softwareHD codec test，不是复杂/高清实拍。百级/≥10组后续目标继续，逐GPU新slot/滚动容量，旧5DEV/旧audit/GT不fit、不恢复旧closed/旧端追查。fit0/TEST0，WM/DINO/Actor/真机/第二owner不开，自动化未改。详细`{M}/README.md`，以下仅历史。

'''
remote=[];proof=[]
def edit(p,new,label,peer=False):
 old=p.read_bytes();d=os.open(p.parent,os.O_RDONLY|os.O_DIRECTORY)
 try:
  fcntl.flock(d,fcntl.LOCK_EX)
  with p.open('rb')as f:
   fcntl.flock(f,fcntl.LOCK_EX);got=f.read();st=os.fstat(f.fileno());assert got==old and(p.stat().st_dev,p.stat().st_ino)==(st.st_dev,st.st_ino);(M/(label+'-before-TRAIN6-complete.md')).write_bytes(old);fd,t=tempfile.mkstemp(prefix='.'+p.name+'.TRAIN6-complete-',dir=p.parent)
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
p=B/'STATUS.md';s=p.read_text();a='<!-- NEXT_QUESTION_SAMPLING_CURRENT_BEGIN -->';b='<!-- NEXT_QUESTION_SAMPLING_CURRENT_END -->';i=s.index(a)+len(a);j=s.index(b,i);s=s[:i]+'\n'+body+'\n'+s[j:];s=re.sub(r'更新：[^\n]+',f'更新：{now}（北京时间；TRAIN6全closed/原件齐4PASS2原门失败，资源空闲，转完整源门/一次fit及复杂首对准入）。',s,count=1);edit(p,s.encode(),'STATUS')
edit(M/'README.md',('# Complete genuine new-purpose TRAIN6 and next prioritized complex-task admission\n\n'+body).encode(),'detailed-README')
tree=ast.parse((P/'publish_current_progress.py').read_bytes());code=next(ast.literal_eval(n.value)for n in tree.body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='code'for t in n.targets));code=code.replace('g2-full2-46308-20261115-v1','new-critic-cohort-46308-20261115-v1').replace('before-full2-live','before-TRAIN6-complete');r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],input=json.dumps(remote),capture_output=True,text=True,timeout=90)
for suf,t in [('stdout',r.stdout),('stderr',r.stderr),('exit',str(r.returncode)+'\n')]:(M/('TRAIN6-closed-entry-mirror.'+suf)).write_text(t)
(M/'TRAIN6-closed-CAS-peer-proof.json').write_text(json.dumps(dict(at=now,local=proof,remote_exit=r.returncode,other_groups_bytes_preserved=True,no_qualification_fit_or_new_physical_dispatch_by_publication=True),indent=2)+'\n');assert r.returncode==0,r.stderr;print('Complete TRAIN6/current idle/gate pending/complex priority updated without peer changes')
