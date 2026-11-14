from pathlib import Path
import os,datetime,json,hashlib,fcntl,stat,tempfile,re,ast,subprocess,shlex,base64
B=Path('/home/yuanyue/main/work/data-team');M=Path(__file__).resolve().parent;S=Path('/home/yuanyue/main/汇总/各小组进展汇总.md');now=datetime.datetime.now().astimezone().isoformat();sha=lambda b:hashlib.sha256(b).hexdigest();h=json.loads((B/'registry/handoff_46308_current_status_20261115.json').read_bytes());q=h['active_g2_full2_scope'];assert q['active']and q['candidate_id']=='g2_full2_native_NAV_prefix_right'and q['phase']=='CAS_DISPATCHED_MAIN'
D=B/'consumer-deliveries/AINAV-DATA-G2-46308-FULL2-LEFT-ACTUAL-20261115-v1';release=json.loads((D/'release.json').read_bytes());v=release['actual_summary'];assert v['source_result_passed']and v['task_physics_steps']==23800 and all(v['nine_stream_checks'].values());live=json.loads((M/'right-main-live-observation.json').read_bytes());assert live['PID_exists']and live['ledger']['rows'][-1]['PID']==12229
body=f'''更新：{now}（北京时间；G2原full-2 left真实exact3 PASS/closed/九流cold，5原query已交付；right自身zero/cold通过、唯一main在途）

**当前状态**
- **新增真实结果，不再只报source/zero：** full-2 left原NAV→PUSH(2.3,-1.9,0)→CLIMB .2三语义PASS，主118.995～119.000sim的原浮点终值按原件为118.99999999996426，23800任务步、1191 RGBD/review帧，5 native options/10 literal回执；九流cold全过，FIFO/PD/hardclip复现误差0，同自身zero/main numeric93869e1a…、无teardown错误。不是完整far-bank导航/优化器或跨布局性能收益。
- **原件已经完整可消费：** left release **3b5e9a9f…**，约1.10MB必要原始public/metadata；5实际Host public query，首次CLIMB PREPARE **95.605sim/frame-000004**，依原proposal与matching preparation binding/Host语义SHA定位，不套旧clock/编号、不抽10Hz/nearest/插值或后READY倒灌。protocol含原full-2实际config/新freeze/精确请求，evidence含实际结果/成本/模型身份/九流质检（可含私有后果，绝不送模型）。源bytes/clock/SHA保持；Data未代做45D/视觉/信息研究评价。
- **left真实费用及right当前：** left scope含自身zero/两次aux共132.010sim、**836.637653ledger wall**、输出highwater **174466192bytes**；不是全项目费用，也不拿raw stdout进行中836.490788作final。left已CAS closed、zero1/main1已耗。right新程序b0c2d41b…自身zero/cold真实PASS、主world0/同numeric93869e1a…，02:54后唯一main已CAS并实际PID12229运行；02:55:38 ledger仍open，18.730含auxsim/48.497748wall只是快照，**未报right PASS/最终费用**。right各次数1已耗，不允许重派/自动retry。
- **优先级/源与保管不变：** 总计划仍53233939…，Reach scene-disjoint优先full-2；AINav已独立核Data实际finite builder458ec66e…/selected caller/config/公开目标，center/upper-entry仅派发前暂停备选，0scope/0main，不两gate并跑。GPU1 UUID6d66aa68…/device51两canonical inode3428459217/3428459218、原私有Expat2.8.1 loader、每scope300sim/5400wall/1.5GiB/自身3GiB GPU与4GiB RSS/原Actor/init/4301/12N/4s/stop/QP/FIFO/exact3门保持。fresh整个Data根19767707136bytes/40GiB、provider quota未知，后续phase仍fresh lease。代码本地/GitHub/新端精简保存，大数组/视频留远端。

**正在做／下一项／独立备选**
- **G2当前：** 收束right唯一main，按原流cold/实际结果与费用发布第二支和完整pair索引；失败/拒绝/direct READY/缺PREPARE均保分母，不补帧/换seed/goal追胜。left先发布无需等right或消费回执；原件入口已写远端权威，CAS未改当前right phase、旧cohort/次数。
- **接续：** AINav/Reach按既定四格full-4/full-2×left/right及各自first-PREPARE独立判断公开信息/scene资格。full-2有效也仅第二任务scene，尚缺第三任务相关source-qualified scene及新用途/功效/停止规则，不能按prefix/arm/frame/reset凑TRAIN/CAL/VAL，不能拿本DEV fit。本缺口不否定已做sourcegate；有明确新源则最小新资格，不重跑本四格/盲开12或24main；新用途cohort后接G3critic与简单基线→G4三策略→G5长链/未见→G6，不以本批closed收工。
- **旧边界保持：** G1两closed/9query完整包77748185…不重跑、不转fit；旧46174行政UNKNOWN一次登记停止追踪，新v1 XML失败zero1/main0、15.156688wall/6831bytes/usage未知保留。原Stage-B两PASS/一stop、21来源3650query/strict3/TEST0、训练0保持；Actor/WM/DINO/真机/第二owner不开，自动化未改，不代方法开发/最终研究评价。

**入口**：[full-2 left完整原件]({D}/release.json) · [实际结果/费用/first-PREPARE]({D}/actual-summary.json) · [原query与binding索引]({D}/observation-index.json) · [G2当前运行与协议]({M}/README.md) · [当前权威镜像]({B}/registry/handoff_46308_current_status_20261115.json) · [G1完整旧DEV原件]({B}/consumer-deliveries/AINAV-DATA-G1-46308-TWO-NATIVE-PREFIX-ACTUAL-20261115-v2/release.json)
'''
body=body.replace('主118.995～119.000sim的原浮点终值按原件为118.99999999996426','主119.000sim（原终值118.99999999996426）')
banner=f'''## 当前最高执行入口：G2 full-2 left已closed交原件，right唯一main在途（{now}）

**left原三意图exact3真实PASS/closed/九流cold；主119.000sim/23800步/1191帧、5原query已交，release3b5e9a9f…；首次CLIMB PREPARE95.605sim/frame-000004。right自身zero/cold已PASS，唯一main实际PID12229在途，未报成功/最终费用。** 两支zero/main各1已耗，禁止再派/自动retry；当前新端权威字段active_g2_full2_scope/g2_full2_cohort，同真实窗口01a1d3aa-a0d5-7de0-b886-9d92ed5f1480。细节`{M}/README.md`；left原件`{D}/release.json`。

原registered full-2及它自己的PUSH(2.3,-1.9,0)，AINav finite source458ec66e…已由Data实际caller消费且两开发组独立核过。center/upper-entry已收到但按scene-disjoint政策派发前暂停，0scope/0main，不并跑。原Actor/init/4301/私有Expat2.8.1单进程loader与全部安全/成功门不改。仅46308/GPU1 UUID6d66aa68…/device51规范锁inode3428459217、3428459218；每phase新lease/资源门，代码精简保管，大数组留远端。

**G1两closed、旧新v1失败/旧46174行政UNKNOWN全部保留，不重开旧launcher/账本，不连旧端追查。** 全部G1/G2 gate仍DEV audit-only，public/evidence隔离，禁止fit；两prefix不是两scene，第三任务相关scene/正式训练cohort尚未合格。训练0，Actor/WM/DINO/真机/第二owner不开，自动化不改。以下旧条目只保历史。

'''
remote=[];proof=[]
def edit(p,new,label,peer=False):
 old=p.read_bytes();d=os.open(p.parent,os.O_RDONLY|os.O_DIRECTORY)
 try:
  fcntl.flock(d,fcntl.LOCK_EX)
  with p.open('rb')as f:
   fcntl.flock(f,fcntl.LOCK_EX);got=f.read();st=os.fstat(f.fileno());assert got==old and(p.stat().st_dev,p.stat().st_ino)==(st.st_dev,st.st_ino);(M/(label+'-before-left-closed-right-main.md')).write_bytes(old);fd,t=tempfile.mkstemp(prefix='.'+p.name+'.G2-left-release-',dir=p.parent)
   try:
    with os.fdopen(fd,'wb')as o:o.write(new);o.flush();os.fchmod(o.fileno(),stat.S_IMODE(st.st_mode));os.fsync(o.fileno())
    assert p.read_bytes()==old;os.replace(t,p);os.fsync(d)
   finally:
    if os.path.exists(t):os.unlink(t)
 finally:os.close(d)
 proof.append(dict(path=str(p),before=sha(old),after=sha(new),peer_bytes_exact=peer))
 if p.parent==B:remote.append(dict(name=p.name,expected_sha256=sha(old),bytes=base64.b64encode(new).decode()))
s=S.read_bytes();i=s.index('## Data组'.encode());end=s.find(b'\n## ',i+1);end=len(s)if end<0 else end;new=s[:i]+('## Data组\n\n'+body).encode()+s[end:];assert new[:i]==s[:i];edit(S,new,'shared-Data',True)
for name in('AGENTS.md','README.md'):
 p=B/name;s=p.read_text();i=s.index('## 当前最高执行入口');j=s.index('## 最新用户服务器',i);edit(p,(s[:i]+banner+s[j:]).encode(),name[:-3])
p=B/'STATUS.md';s=p.read_text();a='<!-- NEXT_QUESTION_SAMPLING_CURRENT_BEGIN -->';b='<!-- NEXT_QUESTION_SAMPLING_CURRENT_END -->';i=s.index(a)+len(a);j=s.index(b,i);s=s[:i]+'\n'+body+'\n'+s[j:];s=re.sub(r'更新：[^\n]+',f'更新：{now}（北京时间；G2 full-2 left真实PASS/closed/原件齐，right main在途）。',s,count=1);edit(p,s.encode(),'STATUS')
edit(M/'README.md',('# G2 original registered full-2 source qualification\n\n'+body).encode(),'detailed-README')
tree=ast.parse((M/'publish_current_progress.py').read_bytes());code=next(ast.literal_eval(n.value)for n in tree.body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='code'for t in n.targets));code=code.replace('before-full2-live','before-full2-left-closed-right-main');r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],input=json.dumps(remote),capture_output=True,text=True,timeout=90)
for suffix,text in [('stdout',r.stdout),('stderr',r.stderr),('exit',str(r.returncode)+'\n')]:(M/('left-closed-entry-mirror.'+suffix)).write_text(text)
(M/'left-closed-right-main-CAS-peer-proof.json').write_text(json.dumps(dict(at=now,local=proof,remote_exit=r.returncode,all_peer_bytes_preserved=True),indent=2)+'\n');assert r.returncode==0,r.stderr
print('Data current and peer-safe shared summary updated; left release linked; right main not misreported')
