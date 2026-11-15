"""Current Data-only summary and exact mirrored entry updates; never dispatch."""
from pathlib import Path
import json,datetime,hashlib,os,fcntl,stat,tempfile,subprocess,base64,shlex
B=Path('/home/yuanyue/main/work/data-team');M=Path(__file__).resolve().parent;S=Path('/home/yuanyue/main/汇总/各小组进展汇总.md');O=B/'manifests/new-critic-cohort-46308-20261115-v1';sha=lambda b:hashlib.sha256(b).hexdigest();now=datetime.datetime.now().astimezone().isoformat();hr=(B/'registry/handoff_46308_current_status_20261115.json').read_bytes();h=json.loads(hr);assert not h['active_T_COMPLEX_v2_camera_component_scope']['active']and not h['active_new_critic_cohort_scope']['active'];co=h['new_critic_cohort_v1'];assert co['TRAIN_gate_passed']and co['training_fit_manifest_sha256'].startswith('3371ac20');assert all(co['branches'][c]['zero_dispatch_count']==co['branches'][c]['main_dispatch_count']==0 for c in co['order'][7:]);R=B/'consumer-deliveries/AINAV-DATA-T-COMPLEX-01-V2-COMPONENT-PASS-20261115-v1/release.json';C=B/'consumer-deliveries/AINAV-DATA-NEW-CRITIC-46308-ORDINAL-07-ACTUAL-20261115-v1/release.json';assert sha(R.read_bytes())=='d48fba0e629ce5b3859975ff16a43d3344c4c58201faa2ec128de2ec61c92ab5';assert sha(C.read_bytes())=='9249faef92810270bf192d7958b7254aabf76bff37639348931d7c2beb0884f5'
body=f'''## Data组\n\n更新：{now}（北京时间；主计划仍14:00/b2fb786e…；CAL07原件完整PASS/closed，T复杂v2修复源已真实组件准入及首张直接live HD帧，尚无A/B完整任务或视频）\n\n**当前状态**\n- **T复杂相机故障已由新源版本真实闭合，不是软件宣称修好：** 已接AINav正式immutable release **d486ec48…**，独立新v2三箱scene **578bd753…**（非按A/B输赢改场景）。本地terminal源码在发布后有drift，已拒绝采用mutable工作树，改从该commit远端immutable root取22成员逐SHA核；未改AINav源。新scope自身component-zero1/main0真实通过：新MJB **a901755c…**原robot-engine/三箱registry/原camera base_link/K/T/rotation/fovy核过，GPU0冷Runtime/原aux **6.505sim**、原onboard INPUT8/45D与**直接live960×540世界0帧1张**通过；原192×128 onboard未替换，PNG预览逐像素等于原RGB。不是上采样、旧片/状态重渲染/新任务视频。\n- **组件边界与成本：** 新程序 **c43a4471…**/原result **f956cd66…**，task steps0/task sim0、wall **17.605737142s**、RSS峰值2533969920bytes、own GPU采样峰值624951296bytes、ledger output86425276bytes，usage_known=true。scope已CAS closed/dispatch null/无retry、本组native0/两GPU规范锁释放。完整SupportedCapture witness仍未建立，**动态合法计划/真实≥3有效选择未证，A/B main0/task videos0**；该组件zero不能代替不同全程序/A/B自己的zero。旧v1缺camera失败scope仍closed/count1/main0，11.660271547wall与ledger usage_known=false/sim None原样保留，不回填洗白。\n- **CAL07已完整实际PASS，不再写在途：** 原预登记full1-left-original自身zero1/main1于15:56:45 CAS PASS closed，**119.345task sim/23869命令/1194 RGBD＋1194 review、5 query/5原native option/10literal receipts**；first-PREPARE95.250sim→原同clock query frame-000004绑定，九流cold全过、PD/FIFO/hardclip复现不改。scope含zero/两aux **132.355sim/817.287664850ledger wall/175668085bytes高水位**，全部known，原CALIBRATION role/scene祖先保持；release **9249faef…**已完整发布，不造NN表/模型评价。08/09仍zero/main0未排，VAL10—12仍0且未放行。\n- **实际fit已接收且不重训/不冒性能：** Reach原TRAIN6源门189cad1f…/实际release670d4eb5…、derived d626da89…/fit3371ac20…/model a8b1f165…已逐SHA核并CAS H gate=true/fit绑定；Data fit/refit0，weights/raw48仅远端，CAL只供同冻结model诊断，heldout成绩/校准/online部署仍未得。TRAIN6原4PASS2门失败/27query/1scene2prefix/2public状态、6个各zero1/main1closed不变；缺failed terminal仍缺，原六scope763.970sim/4642.471546ledger wall/1013819924bytes与旧UNKNOWN/DEV/组件/CAL分账保留。当前权威H **{sha(hr)[:8]}…**，旧closed/原门/所有次数不重置。\n\n**下一项／可独立推进／准确缺口**\n- **不再以缺相机或完整driver源码作阻塞：** 真实三箱资产/原语义scene-driver、共同private goal-seal/公开模型隔离和Reach四模块source-bound两策略已交；Data下一项是把完整原200Hz recorder/review/成本/直接live hooks装成新全程序，取得自己的zero及原门动态可行/SupportedCapture/有效决策原件，再同场景/信息/候选/预算做A/B各一次＋1×完整母版/同钟并排。不把组件世界0帧/CPU名义B可达或3件箱本身当任务成功/三次有效选择或本方法胜出，不使用私有正确路线喂在线方法。\n- T任务仍首资源窗口优先，不等critic/100条齐；CAL08/09按独立新fresh核滚动接续、CAL完整后冻结原同model报告再VAL，不自动下一支/重试/refit/调阈值。百级/≥10有意义组及Data唯一owner逐GPU并发目标保持，不热扩原TRAIN/刷相同输入/旧audit改fit，不连接旧46174；WM/DINO/Actor重训/真机/第二owner未开，自动化未改。新组件执行代码 **0639469…**已本地/GitHub/46308同步，后处理FFV1/pair已备但不是本task视频。\n\n**入口**\n- T复杂v2真实组件原件：`{R}`（SHA d48fba0e629ce5b3859975ff16a43d3344c4c58201faa2ec128de2ec61c92ab5）；细节`{M}/README.md`；单张原RGB无损预览`{M}/single-live-HD-world0-preview.png`（不是视频）。\n- CAL07原始完整包：`{C}`（SHA9249faef92810270bf192d7958b7254aabf76bff37639348931d7c2beb0884f5）；实际源/账本/cold在`{O}/new_critic_07_full1_left_original/`。\n- gate/fit接收与CAL独立phase：`{B}/manifests/G3-TRAIN-gate-fit-intake-46308-20261115-v1/`、`{B}/manifests/cal-after-frozen-fit-46308-20261115-v1/README.md`；旧失败/完整TRAIN6仍原路径。\n'''
(M/'README.md').write_text('# T复杂v2组件真实通过＋CAL07原件已发布\n'+body.split('\n',1)[1]);entry='## 当前最高执行入口：T复杂v2相机/Runtime/HD单帧真实通过，CAL07完整PASS closed；下一全任务程序/动态资格\n'+body.split('\n',1)[1]+'\n';proof=[];remote=[]
def update(p,shared=False):
 old=p.read_bytes();s=old.decode()
 if shared:
  i=s.index('## Data组');j=s.find('\n## ',i+1);j=len(s)if j<0 else j;new=(s[:i]+body+s[j:]).encode();assert new[:len(s[:i].encode())]==s[:i].encode()
 elif p.name=='STATUS.md':
  x='<!-- NEXT_QUESTION_SAMPLING_CURRENT_BEGIN -->';y='<!-- NEXT_QUESTION_SAMPLING_CURRENT_END -->';i=s.index(x)+len(x);j=s.index(y,i);v=s[:i]+'\n'+body.split('\n',1)[1]+'\n'+s[j:];i=v.index('更新：');j=v.index('\n',i);new=(v[:i]+'更新：'+now+'（北京时间；CAL07完整closed、T复杂v2组件及HD单帧真实过，见第1节；不是A/B或任务视频）。'+v[j:]).encode()
 else:
  i=s.index('## 当前最高执行入口');j=s.index('\n## 最新用户服务器与代码决定',i);new=(s[:i]+entry+s[j+1:]).encode()
 d=os.open(p.parent,os.O_RDONLY|os.O_DIRECTORY)
 try:
  fcntl.flock(d,fcntl.LOCK_EX)
  with p.open('rb')as f:
   fcntl.flock(f,fcntl.LOCK_EX);st=os.fstat(f.fileno());assert f.read()==old and(p.stat().st_dev,p.stat().st_ino)==(st.st_dev,st.st_ino);backup=M/(p.name+'.before-v2-CAL07');assert not backup.exists();backup.write_bytes(old);fd,t=tempfile.mkstemp(prefix='.'+p.name+'.v2-CAL07-',dir=p.parent)
   try:
    with os.fdopen(fd,'wb')as out:out.write(new);out.flush();os.fchmod(out.fileno(),stat.S_IMODE(st.st_mode));os.fsync(out.fileno())
    assert p.read_bytes()==old;os.replace(t,p);os.fsync(d)
   finally:
    if os.path.exists(t):os.unlink(t)
 finally:os.close(d)
 proof.append(dict(path=str(p),before=sha(old),after=sha(new),non_Data_peer_bytes_preserved=shared))
 if not shared:remote.append(dict(name=p.name,expected=sha(old),data=base64.b64encode(new).decode()))
update(S,True)
for n in ['STATUS.md','AGENTS.md','README.md']:update(B/n)
code=r'''
from pathlib import Path
import os,sys,json,base64,hashlib,fcntl,stat,tempfile
B=Path('/mnt/yuanyue/data-team/deployments/46308-20261114/workspace')
for row in json.load(sys.stdin):
 p=B/row['name'];assert p.name in('STATUS.md','AGENTS.md','README.md');new=base64.b64decode(row['data']);d=os.open(p.parent,os.O_RDONLY|os.O_DIRECTORY)
 try:
  fcntl.flock(d,fcntl.LOCK_EX)
  with p.open('rb')as f:
   fcntl.flock(f,fcntl.LOCK_EX);old=f.read();st=os.fstat(f.fileno());assert hashlib.sha256(old).hexdigest()==row['expected']and(p.stat().st_dev,p.stat().st_ino)==(st.st_dev,st.st_ino);fd,t=tempfile.mkstemp(prefix='.'+p.name+'.v2-CAL07-',dir=p.parent)
   try:
    with os.fdopen(fd,'wb')as out:out.write(new);out.flush();os.fchmod(out.fileno(),stat.S_IMODE(st.st_mode));os.fsync(out.fileno())
    assert p.read_bytes()==old;os.replace(t,p);os.fsync(d)
   finally:
    if os.path.exists(t):os.unlink(t)
 finally:os.close(d)
print('Current entries mirrored; no H/physical writes')
'''
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],input=json.dumps(remote),capture_output=True,text=True,timeout=90);(M/'entry-mirror.stdout').write_text(r.stdout);(M/'entry-mirror.stderr').write_text(r.stderr);(M/'v2-CAL07-publication-CAS-peer-proof.json').write_text(json.dumps(dict(at=now,proof=proof,remote_exit=r.returncode,H_not_written=True),indent=2)+'\n');assert r.returncode==0,r.stderr;print('Component/CAL07 current entries updated, all non-Data shared bytes preserved')
