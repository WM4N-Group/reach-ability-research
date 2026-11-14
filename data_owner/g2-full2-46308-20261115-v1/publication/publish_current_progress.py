from pathlib import Path
import json,hashlib,datetime,os,fcntl,stat,tempfile,re,subprocess,shlex,base64
B=Path('/home/yuanyue/main/work/data-team');M=Path(__file__).resolve().parent;N=M.name;S=Path('/home/yuanyue/main/汇总/各小组进展汇总.md');now=datetime.datetime.now().astimezone().isoformat();sha=lambda b:hashlib.sha256(b).hexdigest();h=json.loads((B/'registry/handoff_46308_current_status_20261115.json').read_bytes());q=h['active_g2_full2_scope'];assert q['active'] and q['phase']=='CAS_DISPATCHED_MAIN' and q['candidate_id']=='g2_full2_native_NAV_prefix_left'
z=json.loads((M/q['candidate_id']/'zero-result.json').read_bytes());cold=json.loads((M/q['candidate_id']/'actual-zero-cold-validation.json').read_bytes());assert z['passed'] and cold['passed'];a=json.loads((M/'freeze-CAS-receipt.json').read_bytes())
body=f'''更新：{now}（北京时间；G2已按scene-disjoint新优先级切到原注册full-2，新程序真实own-zero/cold通过，left唯一main已启动；非训练cohort）

**当前状态**
- **计划与新来源已实接，避免两条gate同时烧次数。** 总计划仍53233939…；已消费Reach02时scene-disjoint政策和AINav原registered-layout有限源458ec66e…。同full-4的center/upper-entry正式固定包ce572b3b…已看到，但依新优先级仅保留派发前暂停备选，0scope/0main；不再写“未有AINav包”，也不与full-2并跑。
- **新G2实际caller已绑定full-2，而非改label。** Data自己的新build_plan直接消费AINav未改的finite builder，原protocol/HostProfile/真实Host/RequestedPlanner(max_requests=3)保留；原full-2 lane=-1.9/gap=.15/step宽1.5/bridge长3.0，PUSH目标(2.3,-1.9,0)，NAV left/right原引用/精确浮点，CLIMB .2/preparation original。原Actor/初始化函数/4301/12N/4s/guard/QP/FIFO/stop/三条matching native success门不变。这是跨登记layout资格，不冒纯prefix单因素因果或优化收益。
- **已越过纯代码阶段：** 新owned freeze489成员，left程序6ee69a5f…/right b0c2d41b…，authority1a41bdd8…；真实同一窗口owner以远端H SHA-CAS登记新G2字段，所有旧字段/次数保持。新full-2 left自身zero/cold已PASS，任务0步/clock0/queue0、aux6.505sim，model numeric93869e1a…；02:34已实际main PID8897/ledger open（不是结果或最终成本）。right尚0zero/0main。新scope每支最多zero1/main1、不自动重试，不能调用closed G1 launcher。
- **新端资源/代码保管：** fresh整个Data根19591841792bytes/40GiB，自留两scope3GiB，provider quota未知；GPU1 UUID6d66aa68… free24080MiB为快照不是lease，canonical device51/inode3428459217/3428459218。真实phase仍fresh lease/4096MiB启动门/own3GiB GPU、4GiB RSS/每支300sim/5400wall/1.5GiB。复用已成功私有Expat2.8.1单进程LD_PRELOAD，不改系统/共享env。精简代码5f16719…已GitHub push及新端code-only部署，不回传大数组/视频。

**正在做／下一项／独立备选**
- **G2当前：** 收束left唯一main，原流cold/失败与成本先交付，再按left→right各自新own-zero/唯一main。原门拒绝、直接READY、缺PREPARE、失败/故障保完整分母，不换seed/goal/scene补齐，不新增logger/训练器前置。
- **后续研究：** 原first-PREPARE真实clock/Host Observation/public原件交AINav/Reach独立做信息/scene资格评价；本gate仅DEV audit，不能fit。scene→split必须整体隔离，同scene所有prefix/arm/祖先/失败同split；尚缺第三个任务相关source-qualified scene，不能把四prefix当四scene或宣TRAIN/CAL/VAL齐。本缺口不阻本full-2最小资格。合格后才新用途cohort→G3critic/常量成功与均值耗时基线→G4同域三策略→G5长链/未见→G6，不把本批closed当总目标完成。
- **原件与边界保留：** G1 left/right两真实PASS/closed、9query完整包77748185…及有限未归并结论已交，不重跑/转fit；旧46174只一次行政UNKNOWN停止追踪，新v1 XML失败zero1/main0及15.156688wall/6831bytes/未知usage不抹。原Stage-B两PASS/一stop、科学21/3650/strict3/TEST0保持；训练0，Actor/WM/DINO/真机/第二owner不开，自动化未改。Data只采样/记录/质检/用途绑定，不代方法开发与最终评价。

**入口**：[G2实际运行/协议/源绑定]({M}/README.md) · [G2事前用途与停止规则]({M}/evaluation-inputs/G2_SCENE_GATE_PROTOCOL.json) · [当前新端权威本机镜像]({B}/registry/handoff_46308_current_status_20261115.json) · [G1完整原件]({B}/consumer-deliveries/AINAV-DATA-G1-46308-TWO-NATIVE-PREFIX-ACTUAL-20261115-v2/release.json) · [Reach优先级与隔离政策](/home/yuanyue/reach-ability-research/protocols/2026-11-15/G2-scene-disjoint-admission/PRIORITY_AND_SPLIT_POLICY_CN.md)
'''
banner=f'''## 当前最高执行入口：G2 full-2新源资格实际运行（{now}）

**当前G2 full-2 left唯一main在途，right尚未派发。** 新权威字段active_g2_full2_scope/g2_full2_cohort；同真实窗口01a1d3aa-a0d5-7de0-b886-9d92ed5f1480。新程序left自身zero/cold已PASS，main02:34实际PID8897/ledger open；不把在途算PASS或最终成本。每条件最多zero1/main1、不自动retry，全部原安全/成功门/Actor/init/4301/私有Expat配置保持。详细入口`{M}/README.md`。

Reach最新scene-disjoint政策优先原registered full-2。Data新owned caller已直接消费AINav有限源helper458ec66e…，实际protocol/runtime_config=full-2且PUSH目标(2.3,-1.9,0)；不是只换scope/label。新freeze489成员，authority1a41bdd8…，left6ee69a5f…/rightb0c2d41b…。full-4 center/upper-entry固定包已收到但仅派发前暂停备选，0scope/0main，不两条gate并跑。DEV源资格不是合格TRAIN/CAL/VAL或critic数据；尚缺第三scene，prefix/arm/seed不能冒独立scene。

当前计算仅46308独立根`/mnt/yuanyue/data-team/deployments/46308-20261114`，GPU1 UUID6d66aa68…，device51规范锁inode3428459217/3428459218；各phase fresh lease/资源门。代码5f16719…已push/部署精简仓库；大数据/视频留远端。

**G1 left/right v2均exact3 PASS/closed/九流cold，禁止再调用其physical launcher或重开旧scope。** G1完整组合77748185…/9真实query，实际电机与公开信息未完全归并，不冒稳健族/可学/方法收益，禁止DEV转fit。旧46174行政UNKNOWN只登记一次，停止重连/追锁/进程/资产；新v1 XML失败账和原Stage-B/全部旧closed历史保留。训练0，Actor/WM/DINO/真机/第二owner不开，自动化不改。以下旧条目只是历史，不覆盖本段。

'''
(M/'README.md').write_text('# G2 original registered full-2 source qualification\n\n'+body+'\n\n## 精确范围\n\n本新程序直接复用G1成功v2 runner，仅独立ID/authority/H keys/registered finite source选择和Data caller绑定；不热改旧frozen源码。源码语义检查不是native资格；目前只有left zero实际通过/main在途，right未启动。原full-2与full-4有预声明的几何多因素差，不能宣仅前缀因果。\n')
proof=[];remote=[]
def edit(p,new,label,peer=None):
 old=p.read_bytes();d=os.open(p.parent,os.O_RDONLY|os.O_DIRECTORY)
 try:
  fcntl.flock(d,fcntl.LOCK_EX)
  with p.open('rb')as f:
   fcntl.flock(f,fcntl.LOCK_EX);v=f.read();s=os.fstat(f.fileno());assert v==old and(p.stat().st_dev,p.stat().st_ino)==(s.st_dev,s.st_ino)
   (M/(label+'-before-full2-live.md')).write_bytes(old)
   fd,t=tempfile.mkstemp(prefix='.'+p.name+'.G2-full2-',dir=p.parent)
   try:
    with os.fdopen(fd,'wb')as o:o.write(new);o.flush();os.fchmod(o.fileno(),stat.S_IMODE(s.st_mode));os.fsync(o.fileno())
    assert p.read_bytes()==old;os.replace(t,p);os.fsync(d)
   finally:
    if os.path.exists(t):os.unlink(t)
 finally:os.close(d)
 proof.append(dict(path=str(p),before=sha(old),after=sha(new),peer_bytes_preserved=peer))
 if p.parent==B:remote.append(dict(name=p.name,expected_sha256=sha(old),bytes=base64.b64encode(new).decode()))
s=S.read_bytes();start=s.index(b'## Data\xe7\xbb\x84');old=s[start:];rest=old.find(b'\n## ',1);end=len(s)if rest<0 else start+rest
new=s[:start]+('## Data组\n\n'+body).encode()+s[end:];assert new[:start]==s[:start] and new[start+len(('## Data组\n\n'+body).encode()):]==s[end:];edit(S,new,'shared-Data',True)
for name in ('AGENTS.md','README.md'):
 p=B/name;s=p.read_text();i=s.index('## 当前最高执行入口');j=s.index('## 最新用户服务器',i);edit(p,(s[:i]+banner+s[j:]).encode(),name[:-3])
p=B/'STATUS.md';s=p.read_text();a='<!-- NEXT_QUESTION_SAMPLING_CURRENT_BEGIN -->';b='<!-- NEXT_QUESTION_SAMPLING_CURRENT_END -->';i=s.index(a)+len(a);j=s.index(b,i);s=s[:i]+'\n'+body+'\n'+s[j:];s=re.sub(r'更新：[^\n]+',f'更新：{now}（北京时间；G2 full-2 left真实zero/cold通过，唯一main在途；G1closed不重跑）。',s,count=1);edit(p,s.encode(),'STATUS')
code='''from pathlib import Path
import json,sys,hashlib,base64,fcntl,os,stat,tempfile
x=json.load(sys.stdin);B=Path('/mnt/yuanyue/data-team/deployments/46308-20261114/workspace');proof=[]
for row in x:
 p=B/row['name'];raw=base64.b64decode(row['bytes']);d=os.open(p.parent,os.O_RDONLY|os.O_DIRECTORY)
 try:
  fcntl.flock(d,fcntl.LOCK_EX)
  with p.open('rb')as f:
   fcntl.flock(f,fcntl.LOCK_EX);old=f.read();s=os.fstat(f.fileno());assert hashlib.sha256(old).hexdigest()==row['expected_sha256'] and(p.stat().st_dev,p.stat().st_ino)==(s.st_dev,s.st_ino)
   arc=B/'manifests/g2-full2-46308-20261115-v1'/(p.name+'.before-full2-live')
   with arc.open('xb')as z:z.write(old)
   fd,t=tempfile.mkstemp(prefix='.'+p.name+'.G2-',dir=p.parent)
   try:
    with os.fdopen(fd,'wb')as o:o.write(raw);o.flush();os.fchmod(o.fileno(),stat.S_IMODE(s.st_mode));os.fsync(o.fileno())
    assert p.read_bytes()==old;os.replace(t,p);os.fsync(d)
   finally:
    if os.path.exists(t):os.unlink(t)
 finally:os.close(d)
 proof.append(dict(path=str(p),before=hashlib.sha256(old).hexdigest(),after=hashlib.sha256(raw).hexdigest()))
print(json.dumps(proof))
'''
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],input=json.dumps(remote),capture_output=True,text=True,timeout=90)
(M/'current-entry-mirror.stdout').write_text(r.stdout);(M/'current-entry-mirror.stderr').write_text(r.stderr);(M/'current-entry-mirror.exit').write_text(str(r.returncode)+'\n');(M/'current-progress-CAS-proof.json').write_text(json.dumps(dict(at=now,local=proof,remote_exit=r.returncode,other_groups_exactly_preserved=True,physical_dispatch_not_by_publication=True),indent=2)+'\n');assert r.returncode==0,r.stderr
print('G2 source priority/current actual main published; peer bytes preserved; own docs mirrored')
