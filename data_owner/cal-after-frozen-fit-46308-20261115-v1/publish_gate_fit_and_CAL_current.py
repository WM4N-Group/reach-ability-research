"""Publish new verified fit intake/CAL status, Data-only shared CAS; no dispatch."""
from pathlib import Path
import json,datetime,hashlib,os,fcntl,stat,tempfile,subprocess,base64,shlex
B=Path('/home/yuanyue/main/work/data-team');M=Path(__file__).resolve().parent;O=B/'manifests/new-critic-cohort-46308-20261115-v1';I=B/'manifests/G3-TRAIN-gate-fit-intake-46308-20261115-v1';S=Path('/home/yuanyue/main/汇总/各小组进展汇总.md');sha=lambda b:hashlib.sha256(b).hexdigest();now=datetime.datetime.now().astimezone().isoformat();hraw=(B/'registry/handoff_46308_current_status_20261115.json').read_bytes();h=json.loads(hraw);co=h['new_critic_cohort_v1'];q=h['active_new_critic_cohort_scope'];fit=co['CAL_research_gate_binding'];assert co['TRAIN_gate_passed']and co['training_fit_manifest_sha256']==fit['fit_file_sha256'];assert not h['active_T_COMPLEX_component_zero_scope']['active'];c=co['order'][6];br=co['branches'][c];assert q['candidate_id']==c;assert all(co['branches'][n]['zero_dispatch_count']==co['branches'][n]['main_dispatch_count']==0 for n in co['order'][7:]);p=O/c/'actual-zero-cold-validation.json';cold=json.loads(p.read_bytes())if p.exists()else None;mr=O/c/'main-result.json';main=json.loads(mr.read_bytes())if mr.exists()else None
if q['active']:
 state=f"CAL07 full1-left-original当前{q['phase']}，zero/main派发{q['zero_dispatch_count']}/{q['main_dispatch_count']}；终态未闭合，不报成功或heldout成绩"
else:
 state=f"CAL07已{q['phase']}，zero/main各{q['zero_dispatch_count']}/{q['main_dispatch_count']}；实际结果以原件为准，不作模型性能结论"
zero='尚未消费完整自身zero/cold原件'
if cold and cold['passed']:zero='自身zero真实通过＋候选精确v2只读cold通过，原INPUT8/aux/model/clock已核，非新训练样本'
body=f'''## Data组\n\n更新：{now}（北京时间；主计划仍14:00/b2fb786e…；已独立核实Reach真实TRAIN源门及一次冻结fit，CAL仅推进原预登记07，不扩TRAIN/不派VAL）\n\n**当前状态**\n- **不是继续等已完成的TRAIN门：** 46308实际release **670d4eb5…**、源/48槽/标签gate **189cad1f…**、derived manifest **d626da89…**、dataset **cb2cae69…**、fit文件 **3371ac20…**及原6 extracted source pins已逐SHA核到。Reach15:04:11已真实CPU fit一次，6分类/6READY/4成功耗时、TRAIN4正2原生负/2prefix/2公开45D状态但仍1scene；固定model **a8b1f165…**/TRAIN rows **882ca00b…**。Data未fit/refit，raw48/权重留远端；**heldout指标未有、score未校准、online deployment=false**，不把训练完成当泛化或完整任务能力。\n- **已真实接续CAL而非只写接收：** {state}；{zero}。独立新CAL phase-admission freeze **19e7bde7…**绑定同一实际gate/fit，只准原已预登记7—9，保原每root自身zero1/main1/240sim/2400wall/1GiB/CPU2/RSS4GiB/GPU3GiB/原规范GPU1 lease；原TRAIN controller/全12 native冻结字节均未热改。原07先前zero/main0，非恢复旧closed。**08/09仍0未排，VAL10—12仍0且本阶段不放行**；单root driver结束即停，不自动下一支/重试/替代/调阈值。H当前 **{sha(hraw)[:8]}…**，TRAIN_gate_passed已据实际原件CAS true/fit3371ac20…，所有旧closed/费用保持。\n- **复杂任务首优先仍保留：** 上次GPU0新组件zero真实编译通过原robot-engine/两轻箱registry，offscreen960×540，但camera列表空/缺wm_onboard_rgbd，在Runtime/Actor/GL前已closed/no retry（result9bcc0242…、11.660271547wall，原usage_known=false/sim None不洗）。完整A/B main0/高清帧0/videos0，GPU0 Actor/GL仍未资格。AINav新修源/semantic driver在开发，不把mutable源码或软件检查当已接收可运行新版本；已给精确camera ABI修复定位，Data不擅改他组源/重开旧root。Reach已有两策略及公共模型/intent seam，真实公共arc/caller/≥3有效选择/共同动态合法计划和完整原终点仍须源资格。\n- **原TRAIN分母/成本不变：** 01/02/05/06PASS、03stop_deadline/04forbidden_contact:middle，全部各zero1/main1 closed/27query/6first-PREPARE、九流cold过；缺failed literal terminal仍缺，原始完整release13758867…保留。六scope763.970sim含zero/aux、4642.471546ledger wall、1013819924bytes高水位和，CAL与复杂组件另账，不冒全项目成本或独立scene。\n\n**下一项／独立推进／边界**\n- 收束本支CAL07原流/实际成本/九流cold与原件发布；08/09逐支新fresh核并让合格T复杂A/B优先，不用旧TRAIN低清QA/softwareHD替代直接live完整母版。CAL完整后交Reach仅评价同一冻结model/原TRAIN基线；冻结CAL报告前不派VAL、不refit，不在T场景调用局部CLIMB critic冒完整任务后果。\n- 后续新批12—24滚动向≥100新尝试/≥10有意义组、Data唯一owner逐GPU并发目标保持；不热扩原TRAIN/刷同输入/旧audit改fit，旧46174不再连接，WM/DINO/Actor重训/真机/第二owner不开，自动化未改。代码本地/GitHub/46308 phase snapshot04ab8c3…；原native执行冻结程序未改。\n\n**入口**\n- 真实gate/fit SHA接收：`{I}/actual-release-and-hash-verification.json`、`actual-gate-fit-summary-no-weights.json`；CAL新独立控制与当前原件`{M}/README.md`、`{O/c}/`。\n- 复杂组件真实负结果/源修复：`{B}/manifests/T-COMPLEX-01-native-components-46308-20261115-v1/README.md`、`SOURCE_OWNER_CAMERA_ABI_REPAIR_REQUIRED.json`；原件`{B}/consumer-deliveries/AINAV-DATA-T-COMPLEX-01-NATIVE-COMPONENT-FAIL-20261115-v1/release.json`（c9eaabe4…）。\n- TRAIN6完整源：`{B}/consumer-deliveries/AINAV-DATA-NEW-CRITIC-46308-TRAIN6-COMPLETE-20261115-v1/release.json`。\n'''
(M/'README.md').write_text('# CAL新阶段：真实TRAIN源门/一次冻结fit已接收；原07单支推进\n\n'+body.split('\n',1)[1]);entry='## 当前最高执行入口：TRAIN源门/一次冻结fit已核，原CAL07单支推进；T复杂组件旧root已closed待新源\n'+body.split('\n',1)[1]+'\n';proof=[];remote=[]
def update(p,shared=False):
 old=p.read_bytes();s=old.decode()
 if shared:
  i=s.index('## Data组');j=s.find('\n## ',i+1);j=len(s)if j<0 else j;new=(s[:i]+body+s[j:]).encode();assert new[:len(s[:i].encode())]==s[:i].encode()
 elif p.name=='STATUS.md':
  x='<!-- NEXT_QUESTION_SAMPLING_CURRENT_BEGIN -->';y='<!-- NEXT_QUESTION_SAMPLING_CURRENT_END -->';i=s.index(x)+len(x);j=s.index(y,i);v=s[:i]+'\n'+body.split('\n',1)[1]+'\n'+s[j:];i=v.index('更新：');j=v.index('\n',i);new=(v[:i]+'更新：'+now+'（北京时间；真实TRAIN源门/一次fit已核，CAL07接续见第1节；旧closed不重开）。'+v[j:]).encode()
 else:
  i=s.index('## 当前最高执行入口');j=s.index('\n## 最新用户服务器与代码决定',i);new=(s[:i]+entry+s[j+1:]).encode()
 d=os.open(p.parent,os.O_RDONLY|os.O_DIRECTORY)
 try:
  fcntl.flock(d,fcntl.LOCK_EX)
  with p.open('rb')as f:
   fcntl.flock(f,fcntl.LOCK_EX);st=os.fstat(f.fileno());assert f.read()==old and(p.stat().st_dev,p.stat().st_ino)==(st.st_dev,st.st_ino);backup=M/(p.name+'.before-gate-fit-CAL');assert not backup.exists();backup.write_bytes(old);fd,t=tempfile.mkstemp(prefix='.'+p.name+'.CAL-fit-',dir=p.parent)
   try:
    with os.fdopen(fd,'wb')as out:out.write(new);out.flush();os.fchmod(out.fileno(),stat.S_IMODE(st.st_mode));os.fsync(out.fileno())
    assert p.read_bytes()==old;os.replace(t,p);os.fsync(d)
   finally:
    if os.path.exists(t):os.unlink(t)
 finally:os.close(d)
 proof.append(dict(path=str(p),before=sha(old),after=sha(new),non_Data_peer_bytes_preserved=shared))
 if not shared:remote.append(dict(name=p.name,expected=sha(old),data=base64.b64encode(new).decode()))
update(S,True)
for name in ['STATUS.md','AGENTS.md','README.md']:update(B/name)
code=r'''
from pathlib import Path
import os,sys,json,base64,hashlib,fcntl,stat,tempfile
B=Path('/mnt/yuanyue/data-team/deployments/46308-20261114/workspace');rows=json.load(sys.stdin)
for row in rows:
 p=B/row['name'];assert p.name in('STATUS.md','AGENTS.md','README.md');new=base64.b64decode(row['data']);d=os.open(p.parent,os.O_RDONLY|os.O_DIRECTORY)
 try:
  fcntl.flock(d,fcntl.LOCK_EX)
  with p.open('rb')as f:
   fcntl.flock(f,fcntl.LOCK_EX);old=f.read();st=os.fstat(f.fileno());assert hashlib.sha256(old).hexdigest()==row['expected']and(p.stat().st_dev,p.stat().st_ino)==(st.st_dev,st.st_ino);fd,t=tempfile.mkstemp(prefix='.'+p.name+'.CAL-fit-',dir=p.parent)
   try:
    with os.fdopen(fd,'wb')as out:out.write(new);out.flush();os.fchmod(out.fileno(),stat.S_IMODE(st.st_mode));os.fsync(out.fileno())
    assert p.read_bytes()==old;os.replace(t,p);os.fsync(d)
   finally:
    if os.path.exists(t):os.unlink(t)
 finally:os.close(d)
print('Mirrored current entries only; no H/process/native writes')
'''
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],input=json.dumps(remote),capture_output=True,text=True,timeout=90)
(M/'entry-mirror.stdout').write_text(r.stdout);(M/'entry-mirror.stderr').write_text(r.stderr);(M/'gate-fit-CAL-publication-CAS-peer-proof.json').write_text(json.dumps(dict(at=now,proof=proof,remote_exit=r.returncode,H_not_written=True),indent=2)+'\n');assert r.returncode==0,r.stderr;print('Actual gate/fit and CAL current published, peer bytes preserved')
