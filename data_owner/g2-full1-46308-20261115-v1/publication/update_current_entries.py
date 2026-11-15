from pathlib import Path
import os,json,datetime,hashlib,fcntl,tempfile,stat,re,ast,subprocess,shlex,base64
B=Path('/home/yuanyue/main/work/data-team');M=Path(__file__).resolve().parent;P=B/'manifests/g2-full2-46308-20261115-v1';S=Path('/home/yuanyue/main/汇总/各小组进展汇总.md');now=datetime.datetime.now().astimezone().isoformat();sha=lambda b:hashlib.sha256(b).hexdigest();h=json.loads((B/'registry/handoff_46308_current_status_20261115.json').read_bytes());q=h['active_g2_full1_scope'];live=json.loads((M/'left-main-live-observation.json').read_bytes());assert q['active']and q['phase']=='CAS_DISPATCHED_MAIN'and live['PID_exists'];assert live['scope']==q
C=q['candidate_id'];zero=json.loads((M/C/'zero-result.json').read_bytes());cold=json.loads((M/C/'actual-zero-cold-validation.json').read_bytes());assert zero['passed']and cold['passed'];G=B/'consumer-deliveries/AINAV-DATA-G2-46308-FULL2-TWO-PREFIX-ACTUAL-20261115-v1'
body=f'''更新：{now}（北京时间；总计划SHA仍53233939…；full-2两支已完整closed交付，full-1新独立程序自身zero/cold通过，11:52:50唯一main实际启动）

**当前状态**
- **full-2完整结果保留1PASS/1前驱异常：** left119.000sim/23800步、first CLIMB PREPARE95.605sim；right64.170sim/12834实际command步，原PUSH卸载reconciled_reference_FF_intersection_empty，只有started无terminal回执，未达CLIMB请求/首次PREPARE。两支九流cold全过只证记录完整，不将right冒native成功/CLIMB负标签，不补帧/伪造回执/重跑追胜。组合release**9be124b3…**（left3b5e9a9f…/right68339f4c…）保2attempt、7真实query及censor；总209.190sim含zero/aux、1287.339338ledger wall/290578607bytes独立scope高水位和，不冒全项目费用。
- **full-1已从源候选推进到新程序真实资格：** 单独Data owned caller选择原registered full-1，protocol7492762c…/source option350df86b…/精确原请求绑定；lane−1.8、NAV_y−1.6500000000000001、PUSH(2.3,−1.8,0)、CLIMB .2/preparation original。原C质量**1kg/mu.3**及geometry差明确，不冒geometry-only；旧full-2 helper仍原样拒绝full-1，不放宽材料门、不热改旧frozen worker。原Actor/初始化函数/4301/12N/4s/FF/stop/QP/FIFO/exact3成功门保持。
- **真正新scope/own-zero/main，不继承旧zero：** scope data-46308-G2-full1-left-PUSH-CLIMB-20261115-v1，独立freeze493成员、program**3b5e9d4d…**/authority**e0109679…**；03:36新H SHA-CAS仅新增full1字段，原G1/full2/失败账保留。自身zero真实PASS/cold，主worldclock0/command0/queue0、aux6.505sim、model numeric92f86189…（不当几何全参数证明）。本轮11:52fresh核owner/H/资源/规范锁后CAS唯一main，**实际PID14640**；11:53:34 ledger仍open，17.670含auxsim/43.166453wall仅快照，不当成功/最终成本。此前未派main，不能把03:36 freeze/zero或此前heartbeats冒作main一直在跑。当前zero1/main1已耗，禁止自动重试/重复launcher。
- **当前资源/保管：** 仅46308/GPU1 UUID6d66aa68…/device51两canonical inode3428459217、3428459218；11:52无旧owned进程/锁空闲，整个Data根19933688832bytes/40GiB、GPUfree24080MiB为启动快照不是未来lease，provider quota未知。新phase仍fresh规范lease/4096MiB启动门/每scope300sim含aux、5400wall、1.5GiB，own GPU3GiB/RSS4GiB；私有Expat2.8.1精确单进程LD_PRELOAD不改系统/env。代码c3bd7d5…已本地/GitHub/新端精简保管，大数组/视频/权重/环境留远端。

**正在做／下一项／独立备选**
- **当前G2：** 收束full-1唯一main，原流cold/实际成功或故障/first-PREPARE原query及费用公开分层交付；拒绝/失败/direct READY/缺测保分母，不换seed/scene/goal/材料凑第三scene。本新source是原不同case资格，不是修full-2异常或第二次尝试。
- **研究接续：** AINav/Reach可直接消费full-2完整负结果与未达CLIMB；full-1闭合后只增量判它的合法公共信息/原生资格，不等消费回执、不由Data代方法评价。即使full-1 PASS也不自动三scene训练资格；需新用途whole-scene split/样本功效/停止规则，G1/G2 DEV与旧audit/GT禁止fit，训练行/fit仍0。合格新cohort后G3critic/常量与均值耗时基线→G4三策略→G5多决策/未见→G6；若不合格据具体负结果有限转向，不自动v2/放宽原门/盲12或24main。
- **历史边界：** G1两closed、full-2两closed均不重跑；旧46174一次行政UNKNOWN停止追踪，新v1 XML失败/未知费用尾部与Stage-B两PASS一stop保留。center/upper-entry仍派发前暂停、不并跑。科学21/3650/strict3/TEST0不变，Actor/WM/DINO/真机/第二owner不开，自动化未改。

**入口**：[full-1新程序当前/协议]({M}/README.md) · [新事前单main范围]({M}/evaluation-inputs/G2_SCENE_GATE_PROTOCOL.json) · [真实zero/cold]({M}/{C}/actual-zero-cold-validation.json) · [full-2完整两attempt原件]({G}/release.json) · [full-2失败/未达CLIMB分母]({G}/attempts-and-unreached-censor.json) · [当前权威镜像]({B}/registry/handoff_46308_current_status_20261115.json)
'''
banner=f'''## 当前最高执行入口：G2 full-1新程序自身zero/cold通过，唯一main实际在途（{now}）

**full-1原registered单left程序3b5e9d4d…/authoritye0109679…，真实own-zero/cold通过，11:52:50才CAS派发唯一main，实际PID14640/ledger open。** 当前zero1/main1已耗、最多1main不自动retry；不要再次调用launcher。权威active_g2_full1_scope/g2_full1_cohort，同真实窗口01a1d3aa-a0d5-7de0-b886-9d92ed5f1480。主结果尚未形成，不当PASS/最终费用；此前03:36 freeze/zero不冒main。细节`{M}/README.md`。

原full-1 protocol7492762c…及它自己的PUSH(2.3,-1.8,0)/CLIMB original，明确C质量1kg/mu.3与geometry变化，不冒几何-only；Data独立caller新绑定，不改仍拒绝full-1的旧full-2 helper/任何原Actor/init4301/12N/4s/FF/stop/QP/FIFO/成功门。仅46308/GPU1 UUID6d66aa68…/device51 canonical inode3428459217、3428459218；新phase规范lease/资源门/私有Expat精确loader保持。

**full-2两支均closed：left PASS，right原PUSH卸载FF intersection异常、未达CLIMB、无terminal回执，不作CLIMB负标签/补帧，严禁重跑。** 完整9be124b3…/2attempt/7query/209.190sim/1287.339338wall原件`{G}/release.json`；G1及旧v1/旧46174一次行政UNKNOWN全部旧账保留，不连旧端。全部DEV/旧audit/GT禁止fit，第三scene/新用途cohort仍未资格，训练0；WM/DINO/Actor/真机/第二owner不开，自动化不改。以下只保历史。

'''
proof=[];remote=[]
def edit(p,new,label,peer=False):
 old=p.read_bytes();d=os.open(p.parent,os.O_RDONLY|os.O_DIRECTORY)
 try:
  fcntl.flock(d,fcntl.LOCK_EX)
  with p.open('rb')as f:
   fcntl.flock(f,fcntl.LOCK_EX);got=f.read();st=os.fstat(f.fileno());assert got==old and(p.stat().st_dev,p.stat().st_ino)==(st.st_dev,st.st_ino);(M/(label+'-before-full1-main.md')).write_bytes(old);fd,t=tempfile.mkstemp(prefix='.'+p.name+'.full1-main-',dir=p.parent)
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
p=B/'STATUS.md';s=p.read_text();a='<!-- NEXT_QUESTION_SAMPLING_CURRENT_BEGIN -->';b='<!-- NEXT_QUESTION_SAMPLING_CURRENT_END -->';i=s.index(a)+len(a);j=s.index(b,i);s=s[:i]+'\n'+body+'\n'+s[j:];s=re.sub(r'更新：[^\n]+',f'更新：{now}（北京时间；full-2两支closed原件齐，full-1新程序own-zero/cold通过，唯一main在途）。',s,count=1);edit(p,s.encode(),'STATUS')
(M/'README.md').write_text('# G2 original full-1 left single new source gate\n\n'+body)
tree=ast.parse((P/'publish_current_progress.py').read_bytes());code=next(ast.literal_eval(n.value)for n in tree.body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='code'for t in n.targets));code=code.replace('g2-full2-46308-20261115-v1','g2-full1-46308-20261115-v1').replace('before-full2-live','before-full1-main');r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],input=json.dumps(remote),capture_output=True,text=True,timeout=90)
for suf,t in [('stdout',r.stdout),('stderr',r.stderr),('exit',str(r.returncode)+'\n')]:(M/('current-entry-mirror.'+suf)).write_text(t)
(M/'current-progress-CAS-peer-proof.json').write_text(json.dumps(dict(at=now,local=proof,remote_exit=r.returncode,peer_bytes_preserved=True),indent=2)+'\n');assert r.returncode==0,r.stderr;print('Full1 actual current main and full2 failure preserved; Data-only shared update complete')
