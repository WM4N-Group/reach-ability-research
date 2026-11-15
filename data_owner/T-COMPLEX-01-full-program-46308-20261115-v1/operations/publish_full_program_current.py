"""Publish actual assembled full program/own zero/main admission; Data-only CAS."""
from pathlib import Path
import os,json,datetime,hashlib,fcntl,stat,tempfile,subprocess,shlex,base64
B=Path('/home/yuanyue/main/work/data-team');M=Path(__file__).resolve().parent;S=Path('/home/yuanyue/main/汇总/各小组进展汇总.md');sha=lambda b:hashlib.sha256(b).hexdigest();now=datetime.datetime.now().astimezone().isoformat();hr=(B/'registry/handoff_46308_current_status_20261115.json').read_bytes();h=json.loads(hr);q=h['active_T_COMPLEX_full_program_scope'];co=h['T_COMPLEX_full_program_v1'];assert q['arm']=='A'and q['zero_dispatch_count']==q['main_dispatch_count']==1 and co['branches']['B']['zero_dispatch_count']==co['branches']['B']['main_dispatch_count']==0;z=json.loads((M/'A/zero-result.json').read_bytes());cold=json.loads((M/'A/zero-cold.json').read_bytes());assert z['passed']and cold['passed']and cold['program_sha256']==q['whole_program_freeze_sha256'];ptr=json.loads((M/'latest-observation-pointer.json').read_bytes());obs=json.loads((M/ptr['file']).read_bytes());assert obs['H_sha256']==sha(hr);cc=h['new_critic_cohort_v1'];assert all(cc['branches'][c]['zero_dispatch_count']==cc['branches'][c]['main_dispatch_count']==0 for c in cc['order'][7:])
body=f'''## Data组\n\n更新：{now}（北京时间；主计划仍14:00/b2fb786e…；完整T复杂A/B源程序已装配/freeze，A自身full-host zero/cold通过并唯一main实派，B未派；完整任务/对照视频未完成）\n\n**当前状态**\n- **已越过“只有组件/还没caller”的阶段：** 正式消费AINav最终immutable **b08f51bb…**（含真实三箱终点计数修复），selected scene仍578bd753…；Reach四模块source-bound factory/c0ecb872…两策略，原实际SupportedCapture→原语义driver→private goal seal/native executor/原终点、200Hz motor＋原INPUT8/review和直接live960×540/10Hz hooks已装入Data新全程序。A greedy程序 **626400b8…**、B multistep **0ba38395…**各自zero1/main1上限，全部496成员SHA封印，不借旧组件zero、不接私有存在性路线/critic、不改原Actor/12N/4s/FF/QP/FIFO/stop；代码 **afd6158…**已本地/GitHub/46308同步。\n- **A已自己的真实完整host zero/cold通过，不是再做组件零步：** 原result **15947a2e…**、same-model numeric **febcd592…**；35.978013324wall/原aux6.505sim，真实完整host/原onboard8字段/1×HD世界0帧/review均过、task steps0/commands0、close errors0、RSS峰值2630660096bytes/GPU采样峰值767557632bytes。只读cold禁Runtime/Actor新调用，核原私域catalog字段值/其首次canonical序列化SHA保留、原8字段/时钟/0指令/静态模型一致。发现RegisteredObserver私域标志model_input与旧原recorder的model_input_allowed命名不合，已用**双方相同、显式无损PRIVATE-only metadata alias**装配：保原catalog sidecar，仅copy加标志/time别名，绝不改INPUT8/模型输入/原Observer或源控制；5软件检查不是物理样本。\n- **唯一A main已真实CAS及启动，不能写成greedy已有结果：** 16:56:33 CAS main1，当前H **{sha(hr)[:8]}…**；{obs['at']}快照native PID{obs['PID']} alive，原ledger main尚open，task时钟约{obs['ledger_last']['sim_s']-6.505:.3f}sim、phase wall{obs['ledger_last']['wall_s']:.3f}s（含本phase初始化），仍为原cold-capture实际发命令阶段，**尚无完整capture witness/高层决策/placement或任务终态证据**。记录的是实测早期阶段，不作完整吞吐/算法评价，不因开销热改在途预算/guard或补跑。每scope625sim含zero/aux、task600sim、4800wall、3GiB；CPU2/RSS4GiB/GPU3GiB，remaining CAL/VAL预留7.5GiB＋pair6GiB已核40GiB自限内，provider quota未知。**B zero/main0，未自动派发；完整任务/有效3选择/合法动态计划与1×/同钟并排母版均未证。** 本首对明示DEV/source资格诊断，不预设B胜/不把共同域或资源错误算算法失败。\n- **既有真结果与费用不变：** d486…组件scope已closed/zero1-main0，真实camera ABI/冷Runtime/原8字段/直接HD世界0帧1过，release d48fba0e…，6.505aux sim/17.605737142wall/86425276bytes；旧缺camera失败root仍closed/11.660271547wall、ledger usage_known=false/sim None保留。CAL07 full1-original已119.345task sim PASS closed，23869命令/1194RGBD+review各/5query/九流cold过、scope132.355sim/817.287664850wall/175668085bytes，原CALIBRATION包9249faef…已发布。TRAIN6完整原件13758867…4PASS2原门失败/27query不改，实际gate=true/fit3371ac20…/model a8b1f165…冻结；Data不refit，旧费用/缺failed terminal/UNKNOWN全保。**CAL08/09和VAL10—12仍zero/main0。**\n\n**下一项／在途边界**\n- 接续同一A唯一main自然收束，保完整原命令/RGBD/review/回执/错误/真实费用与直接raw frames，结束后只读核验、CAS关闭/发布，不重启或热改该scope。若zero/完整性/共享资源门失败则停本pair；仅普通main结果才按相同冻结源/候选/门让B独立fresh准入/自身zero/main一次。不把capture预备NAV/强制终点或3箱个数冒3个有意义选择；能否满足T验收须真实决策journal/实际原终点证据。\n- T仍首优先，不等critic/百级齐；之后CAL08/09逐支新准入→同冻结model诊断/冻结CAL报告→再VAL，不refit/调阈值/自动扩量。后续≥100新尝试/≥10有意义组与Data唯一owner逐GPU并发目标保持，不刷同输入/旧audit改fit，不恢复任何old closed或旧46174；WM/DINO/Actor重训/真机/第二owner/新自动化未开。\n\n**入口**\n- 在途全程序/精确新freeze/自身zero/cold/观测：`{M}/README.md`、`{M}/A/`、`{M}/latest-observation-pointer.json`；**不要重跑main-run/zero-run或A driver**。原件及大raw/MJB全留46308，1×/pair后处理仅消费直接raw，不能重渲染/插值/旧TRAIN片代替。\n- 组件正式原件：`{B}/consumer-deliveries/AINAV-DATA-T-COMPLEX-01-V2-COMPONENT-PASS-20261115-v1/release.json`；CAL07原件：`{B}/consumer-deliveries/AINAV-DATA-NEW-CRITIC-46308-ORDINAL-07-ACTUAL-20261115-v1/release.json`。\n'''
(M/'README.md').write_text('# T复杂完整源程序：A自身zero/cold已过，唯一main实派；B未派\n'+body.split('\n',1)[1]);entry='## 当前最高执行入口：T复杂完整程序已装配/封印，A full-host zero-cold通过且main1实派；B0/0\n'+body.split('\n',1)[1]+'\n';proof=[];remote=[]
def update(p,shared=False):
 old=p.read_bytes();s=old.decode()
 if shared:
  i=s.index('## Data组');j=s.find('\n## ',i+1);j=len(s)if j<0 else j;new=(s[:i]+body+s[j:]).encode();assert new[:len(s[:i].encode())]==s[:i].encode()
 elif p.name=='STATUS.md':
  x='<!-- NEXT_QUESTION_SAMPLING_CURRENT_BEGIN -->';y='<!-- NEXT_QUESTION_SAMPLING_CURRENT_END -->';i=s.index(x)+len(x);j=s.index(y,i);v=s[:i]+'\n'+body.split('\n',1)[1]+'\n'+s[j:];i=v.index('更新：');j=v.index('\n',i);new=(v[:i]+'更新：'+now+'（北京时间；T完整程序A自身zero/cold通过、唯一main实派，B0/0；不是已完成对照）。'+v[j:]).encode()
 else:
  i=s.index('## 当前最高执行入口');j=s.index('\n## 最新用户服务器与代码决定',i);new=(s[:i]+entry+s[j+1:]).encode()
 d=os.open(p.parent,os.O_RDONLY|os.O_DIRECTORY)
 try:
  fcntl.flock(d,fcntl.LOCK_EX)
  with p.open('rb')as f:
   fcntl.flock(f,fcntl.LOCK_EX);st=os.fstat(f.fileno());assert f.read()==old and(p.stat().st_dev,p.stat().st_ino)==(st.st_dev,st.st_ino);backup=M/(p.name+'.before-full-program-A-main');assert not backup.exists();backup.write_bytes(old);fd,t=tempfile.mkstemp(prefix='.'+p.name+'.T-full-A-',dir=p.parent)
   try:
    with os.fdopen(fd,'wb')as out:out.write(new);out.flush();os.fchmod(out.fileno(),stat.S_IMODE(st.st_mode));os.fsync(out.fileno())
    assert p.read_bytes()==old;os.replace(t,p);os.fsync(d)
   finally:
    if os.path.exists(t):os.unlink(t)
 finally:os.close(d)
 proof.append(dict(path=str(p),before=sha(old),after=sha(new),non_Data_peer_bytes_preserved=shared))
 if not shared:remote.append(dict(name=p.name,expected=sha(old),data=base64.b64encode(new).decode()))
update(S,True)
for n in['STATUS.md','AGENTS.md','README.md']:update(B/n)
code=r'''
from pathlib import Path
import os,sys,json,base64,hashlib,fcntl,stat,tempfile
B=Path('/mnt/yuanyue/data-team/deployments/46308-20261114/workspace')
for row in json.load(sys.stdin):
 p=B/row['name'];assert p.name in('STATUS.md','AGENTS.md','README.md');new=base64.b64decode(row['data']);d=os.open(p.parent,os.O_RDONLY|os.O_DIRECTORY)
 try:
  fcntl.flock(d,fcntl.LOCK_EX)
  with p.open('rb')as f:
   fcntl.flock(f,fcntl.LOCK_EX);old=f.read();st=os.fstat(f.fileno());assert hashlib.sha256(old).hexdigest()==row['expected']and(p.stat().st_dev,p.stat().st_ino)==(st.st_dev,st.st_ino);fd,t=tempfile.mkstemp(prefix='.'+p.name+'.T-full-A-',dir=p.parent)
   try:
    with os.fdopen(fd,'wb')as out:out.write(new);out.flush();os.fchmod(out.fileno(),stat.S_IMODE(st.st_mode));os.fsync(out.fileno())
    assert p.read_bytes()==old;os.replace(t,p);os.fsync(d)
   finally:
    if os.path.exists(t):os.unlink(t)
 finally:os.close(d)
print('Mirrored current Data entries only, no H or in-flight source change')
'''
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],input=json.dumps(remote),text=True,capture_output=True,timeout=90);(M/'entry-mirror.stdout').write_text(r.stdout);(M/'entry-mirror.stderr').write_text(r.stderr);(M/'full-A-main-publication-CAS-peer-proof.json').write_text(json.dumps(dict(at=now,proof=proof,remote_exit=r.returncode,H_not_written=True,inflight_program_source_unchanged=True),indent=2)+'\n');assert r.returncode==0,r.stderr;print('Actual full program own-zero and main admission published; peer bytes unchanged')
