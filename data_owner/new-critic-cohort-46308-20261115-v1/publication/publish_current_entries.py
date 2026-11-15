from pathlib import Path
import json,datetime,hashlib,fcntl,os,stat,tempfile,re,ast,subprocess,shlex,base64
B=Path('/home/yuanyue/main/work/data-team');M=Path(__file__).resolve().parent;P=B/'manifests/g2-full2-46308-20261115-v1';S=Path('/home/yuanyue/main/汇总/各小组进展汇总.md');sha=lambda b:hashlib.sha256(b).hexdigest();now=datetime.datetime.now().astimezone().isoformat();h=json.loads((B/'registry/handoff_46308_current_status_20261115.json').read_bytes());q=h['active_new_critic_cohort_scope'];co=h['new_critic_cohort_v1'];assert q['candidate_id']=='new_critic_01_full4_left_original'and q['active']and q['phase']=='CAS_DISPATCHED_MAIN';v=json.loads((M/json.loads((M/'latest-observation-pointer.json').read_bytes())['file']).read_bytes());assert v['PID_exists']and v['current_PID']==18480;z=json.loads((M/q['candidate_id']/'zero-result.json').read_bytes());cold=json.loads((M/q['candidate_id']/'actual-zero-cold-validation.json').read_bytes());assert z['passed']and cold['passed'];freeze=json.loads((M/'freeze-CAS-receipt.json').read_bytes())
body=f'''更新：{now}（北京时间；主计划仍53233939…；Reach12:41新用途有限cohort已接并新freeze，TRAIN第1支自身zero/cold真实通过、13:04唯一main实际启动）

**当前状态**
- **新用途协议已到且实际推进，不再写等cohort：** 精确消费Reach finite protocol **2f82530d…**，未来新数据仅用于小型高层条件critic；full-4 TRAIN两prefix×3固定候选=6，full-1 CAL左×3=3，full-2 VAL左×3=3，总上限12、每root自身zero/main各≤1、无seed/reset重复/替代/自动扩批。whole-scene/祖先键及scene→split从原protocol/材料/初始化/构造SHA核合，不用prefix/arm/新ID伪拆scene；3scene各split1scene，历史已曝光、48槽/6TRAIN极小，只能弱探索，不冒功效/未见TEST/G4部署。
- **新Data caller真实消费每臂，不只改label：** full4/full2复用原helper458ec66e…；full1保持独立原protocol7492762c…/C质量1kg/mu.3，不放宽旧helper材料门。新plan记录同一个固定PreparationSelection，worker按plan payload交现installer/原Host/common-stow/exact3；原Actor/init4301/12N/4s/FF/QP/FIFO/stop不改。原8公共字段/原RGBD/45D/journal/录制保持，不新增NN表/logger/预算或消费回执前置。新采集manifest明示purpose/role；native result中training_allowed=false仅指本native进程不执行训练，**不回写旧physical protocol/旧结果用途**，新数据拟合仍需TRAIN gate及Reach派生manifest。
- **已进入第一条真实新数据采集：** 独立新cohort authority **88bb1827…**、完整freeze494成员，首program **b738125e…**，新端H字段active_new_critic_cohort_scope/new_critic_cohort_v1以同真实owner SHA-CAS新增，所有5旧DEV/失败/次数不变。第1支scope data-46308-new-critic-01-full4-left-original-20261115-v1，真实自身zero/cold PASS（task0/worldclock0/原INPUT8/aux6.505）；**13:04:02唯一main CAS后实际PID18480**、13:04:13 ledger open，尚不报成功/最终成本。第2—6尚未派发；7—12冻结但明确NOT_DISPATCHED_BLOCKED_TRAIN_GATE，不是已采资料。
- **固定执行与原门：** 已启动一次性有限TRAIN1—6顺序pipeline，仅复用既有prepare→zero→cold→main→cold→close；每phase fresh owner/源pin/资源/规范lease，不自动retry，不重开旧scope，异常/资源/完整性停即不派后续。原生420sim协议未改，外层更严**累计240sim（含own-zero/aux）/2400wall/1GiB，zero另180wall及原安全余量**；outer Stop保resource censor，不作native负类。fresh整个Data根20072851968bytes/40GiB，按12root×1.5GiB预留18GiB可容，provider quota未知；GPU1 UUID6d66aa68…/device51 canonical inode3428459217、3428459218，24080MiB仅freeze快照、非未来lease。ownGPU3GiB/RSS4GiB/CPU2/私有Expat2.8.1精确LD_PRELOAD不变。

**正在做／下一项／独立备选**
- **当前按固定序列采TRAIN6，不盲全12：** ordinal1原left、2原right、3plus-left、4plus-right、5minus-left、6minus-right。每新root自己zero/main/账本；原拒绝/失败/未到first-PREPARE/资源censor完整保留，不造CLIMB负标签/回执/特征或把失败elapsed当成功cost。首个CPU源检查曾将Reach未分配的scope_id=null与Data新scope直接相等，已在**未freeze/0物理**时修正只把外部null映射新ownedID，失败stdio留存，不算研究样本/新物理失败，不改Reach协议。
- **TRAIN闭合即停物理并接G3资格：** Reach按同SHA事前规则核≥2prefix组/≥2公共状态/≥3真实成功/≥1决策后native失败及48槽/源完整；不满足就No-Go、不fit、不派CAL/VAL、不换seed挖失败/补类。合格才Reach一次CPU critic+TRAIN常量score/均值耗时基线；当前控制器硬拒ordinal>6，**不会自动采CAL/VAL或训练**。CAL3/VAL3须后续引用冻结gate+真实fit，CAL仅诊断不宣校准概率、VAL不调参。后续G4三策略/G5长链另协议，非本批自动部署。
- **旧DEV与边界不动：** full-1真实PASS/closed2bae0f2a…，full2一PASS一原PUSH卸载异常9be124b3…，三源五DEV索引01e2571a…保4PREPARE/1未达；全部旧DEV/旧audit/GT不转fit。旧46174一次行政UNKNOWN停止追踪/新v1 XML失败/Stage-B两PASS一stop原账保留，center/upper-entry仍暂停。科学21/3650/strict3/TEST0、真实fit0；Actor/WM/DINO/真机/第二owner不开，自动化未改。代码137ad2a…已本地/GitHub/新端精简保管，dense数据/视频/环境/权重留远端。

**入口**：[新用途实际采集/当前]({M}/README.md) · [Reach固定研究协议](/home/yuanyue/reach-ability-research/protocols/2026-11-15/G2-new-purpose-finite-cohort-v1/FINITE_COHORT_PROTOCOL.json) · [新完整freeze]({M}/freeze-CAS-receipt.json) · [有限TRAIN6运行日志]({M}/TRAIN-pipeline.stdout) · [当前权威镜像]({B}/registry/handoff_46308_current_status_20261115.json) · [旧三源五DEV原件]({B}/consumer-deliveries/AINAV-DATA-G2-46308-REGISTERED-SCENE-SOURCE-HANDOFF-20261115-v1/release.json)
'''
banner=f'''## 当前最高执行入口：新用途TRAIN6有限采集已启动，首支真实zero/cold通过、main在途（{now}）

**新cohort协议2f82530d…已到并消费，不再等协议或重问预算。** 新权威active_new_critic_cohort_scope/new_critic_cohort_v1，authority88bb1827…/freeze494成员，同真实窗口01a1d3aa-a0d5-7de0-b886-9d92ed5f1480。首programb738125e…/scope data-46308-new-critic-01-full4-left-original-20261115-v1，自身zero/cold真实PASS，13:04:02唯一main CAS、实际PID18480/ledger open，未有最终成功/cost。

最多12全新future-purpose root：TRAIN full4 left/right×3臂=6，CAL full1-left×3，VAL full2-left×3；whole-scene split/角色/seed4301/精确请求/臂payload固定。当前一次性有限pipeline只走TRAIN1..6各自zero/main/cold/close、无retry/替代，control硬拒ordinal>6，**TRAIN6结束必须停物理等Reach gate/一次fit，CAL/VAL不会自动派发**。要求≥3成功、≥1真实决策后native失败、两prefix/公共状态/完整48槽，否则No-Go停采不挖失败。原12N/4s/FF/QP/FIFO/CLIMB stop/Actor/init不改；外层240sim含zero/aux、2400wall、1GiB，zero180wall更严，resource是censor不是负类。

新数据用途在new-purpose-acquisition-manifest/冻结protocol登记，native训练flag仍false仅说明本native进程不fit，不重写旧物理protocol或旧结果。原full4/full2 helper458ec66e…/full1独立7492762c…路径不变，既有installer真实消费plan固定候选，不能热切臂。仅46308/GPU1 UUID6d66aa68…/device51规范锁inode3428459217、3428459218，逐phase fresh lease/资源门/精确私有Expat。

**旧5DEV/所有旧scope仍closed且不转fit/不重跑。** full1 PASS2bae0f2a…/full2一PASS一前驱异常9be124b3…/三源01e2571a…全部保；full2right未达CLIMB不作负行，旧UNKNOWN/失败/费用尾部不抹、不追旧端。当前真实fit0/TEST0；WM/DINO/Actor/真机/第二owner不开，自动化不改。详细`{M}/README.md`，以下旧条目只保历史。

'''
remote=[];proof=[]
def edit(p,new,label,peer=False):
 old=p.read_bytes();d=os.open(p.parent,os.O_RDONLY|os.O_DIRECTORY)
 try:
  fcntl.flock(d,fcntl.LOCK_EX)
  with p.open('rb')as f:
   fcntl.flock(f,fcntl.LOCK_EX);got=f.read();st=os.fstat(f.fileno());assert got==old and(p.stat().st_dev,p.stat().st_ino)==(st.st_dev,st.st_ino);(M/(label+'-before-new-TRAIN-main.md')).write_bytes(old);fd,t=tempfile.mkstemp(prefix='.'+p.name+'.newTRAIN-main-',dir=p.parent)
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
p=B/'STATUS.md';s=p.read_text();a='<!-- NEXT_QUESTION_SAMPLING_CURRENT_BEGIN -->';b='<!-- NEXT_QUESTION_SAMPLING_CURRENT_END -->';i=s.index(a)+len(a);j=s.index(b,i);s=s[:i]+'\n'+body+'\n'+s[j:];s=re.sub(r'更新：[^\n]+',f'更新：{now}（北京时间；新用途finite cohort TRAIN首支真实zero/cold通过、main在途，旧5DEV闭合不转fit）。',s,count=1);edit(p,s.encode(),'STATUS')
(M/'README.md').write_text('# Prospective NEW-use conditional critic cohort, finite TRAIN6 acquisition\n\n'+body)
tree=ast.parse((P/'publish_current_progress.py').read_bytes());code=next(ast.literal_eval(n.value)for n in tree.body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='code'for t in n.targets));code=code.replace('g2-full2-46308-20261115-v1','new-critic-cohort-46308-20261115-v1').replace('before-full2-live','before-new-TRAIN-main');r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],input=json.dumps(remote),capture_output=True,text=True,timeout=90)
for suf,t in [('stdout',r.stdout),('stderr',r.stderr),('exit',str(r.returncode)+'\n')]:(M/('current-entry-mirror.'+suf)).write_text(t)
(M/'current-progress-CAS-peer-proof.json').write_text(json.dumps(dict(at=now,local=proof,remote_exit=r.returncode,other_groups_bytes_preserved=True,physical_program_or_pipeline_or_H_not_modified_by_publication=True),indent=2)+'\n');assert r.returncode==0,r.stderr;print('New-purpose TRAIN acquisition current entries published; all other groups preserved')
