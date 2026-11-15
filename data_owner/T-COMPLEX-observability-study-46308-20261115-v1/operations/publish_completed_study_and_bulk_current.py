"""Publish real completed OBS and bulk outcomes; Data-only SHA-CAS, never H."""
from pathlib import Path
import os,json,hashlib,datetime,fcntl,stat,tempfile,subprocess,shlex,base64,ast
B=Path('/home/yuanyue/main/work/data-team');M=Path(__file__).resolve().parent;K=B/'manifests/bulk24-collector-46308-20261115-v1';S=Path('/home/yuanyue/main/汇总/各小组进展汇总.md');now=datetime.datetime.now().astimezone().isoformat();sha=lambda b:hashlib.sha256(b).hexdigest()
assert sha(Path('/home/yuanyue/main/汇总/各小组下一步研究计划.md').read_bytes())=='b2fb786ec002b1e88ed4fc56a0bbfbac21d62cd788dacdda7d9fceb1a774c5a9'
h=json.loads((B/'registry/handoff_46308_current_status_20261115.json').read_bytes());q=h['active_T_COMPLEX_observation_study_scope'];co=h['bulk24_collector_v1'];bulk=h['active_bulk24_collector_scope'];d=json.loads((K/'unstarted-suffix20-driver-status.json').read_bytes());assert not q['active']and q['observation_qualification_complete']and not q['actual_task_success'];assert all(co['branches'][c]['status']=='CLOSED_ACTUAL_MAIN_PASS'for c in co['order'][:3])and co['branches'][co['order'][3]]['status']=='CLOSED_ACTUAL_MAIN_FAILED_NO_RETRY'and not co['global_stop']
release=B/'consumer-deliveries/AINAV-DATA-T-OBS-THREE-FIXED-BOUNDARIES-COMPLETE-NOT-TASK-20261115-v1/release.json';r=json.loads(release.read_bytes());assert sha(release.read_bytes())=='785bd9db046189228d72b3f607c0d1f74bae1285b4e6e120788d212d952f37ed'and r['measurement_complete']and not r['task_success'];assert d['driver_PID']and d['no_refit']and d['no_closed_scope_reopened']
main=sum(b['main_dispatch_count']for b in co['branches'].values());zero=sum(b['zero_dispatch_count']for b in co['branches'].values());remaining=sum(b['main_dispatch_count']==b['zero_dispatch_count']==0 for b in co['branches'].values());ordinal=co['order'].index(bulk['candidate_id'])+1
body=f'''## Data组

更新：{now}（北京时间；主计划14:00/b2fb786e…未变；**T固定三视角观测研究完成并关闭，bulk已4条终态：3条件PASS/1原生FF门失败；余下只对未启动suffix滚动**）

**当前状态**
- **GPU0独立观测研究已真实完成，不再是2/3或原NAV仍在途：** scope `data-46308-T-COMPLEX-observability-only-20261115-v1`，source **c3c695b5…**/program **9fdd2076…**不变；自己的zero1/main1，原capture448步后两个固定原NAV均得到字面succeeded（tick2963/5503）。3个预登记真实fresh public边界原样全部保留：初始**2.240sim aliases=[]**，left后**14.815sim aliases=['cuboid_a']**，right后**27.515sim aliases=[]**。不因left阳性取消right、不挑最好帧，不修改相机/颜色/阈值/几何/原关联门；**不是独立private-GT验证、PUSH READY/执行/成功、复杂整场成功、3有效选择或前瞻优势**。原A/B closed/stop和旧4800wall均保留，本study不是补B。
- **OBS终态/原件/原片已交付：** main result **a2252439…**，measurement_complete=true/task_success=false；**5503条200Hz命令/27.515task sim，276原RGBD+review+960×540直接raw各**。九流cold、1058行完整journal链、两原回执与三actual Observation语义SHA精确绑定过，原件前后SHA不变。scope含ownzero/双aux **40.525sim/10266.018950355ledger wall/245208182bytes高水位**，usage known、非resource censor。GPU0规范两inode fresh核自由并CAS关闭，GPU1进程未被停止。完整release **785bd9db046189228d72b3f607c0d1f74bae1285b4e6e120788d212d952f37ed**：`{release}`；3份原PNG/depth/K/T/同packet45D小副本已本机留存，远端同名delivery有**276帧/10fps/1×完整原raw编码视频**，无重渲染/插帧/裁切/后继帧冒输入。首次只读audit误查不存在相机描述文件的stderr保留，v2由冻结scene与原actual-config精确核camera，未重跑物理。
- **GPU1 bulk24新增第3条真实PASS，第4条原门失败完整留账：** 前3条ordinal01 g01-left/original、02 g01-right/+4cm、03 g02-left/−4cm各ownzero1/main1并closed、九流及exact3原NAV→PUSH→20cm CLIMB回执cold通过。第3条result **c9591b5e…**，**118.710task sim/23742命令/1188 RGBD-review-raw各**；含zero/aux131.720sim/937.219946071wall/174854738bytes。第4条g02-right/original result为**原生 `reconciled_reference_FF_intersection_empty`**，64.175task sim/12835命令/642帧，scope **77.185sim/505.588107628wall/116427432bytes**，全部usage known、非resource censor；九流cold过只代表记录完整，**不把质检PASS改写原任务失败，也不把未到的query/label补0或作CLIMB负例**。第1条正式原件release904ff608…保留，第2—4条原result/audit在`{K}/`，后续可只读并行交付、不因包装让GPU1空等。
- **并发metadata冲突已保留/解决，没重试物理：** 原余22 driver在第4条close-main时碰到OBS关闭先赢whole-H SHA-CAS而停止，原拒绝/claim/日志不覆盖；fresh只做该已终态第四支metadata收束，zero/main仍各1、原FF失败不变。**新一次性suffix20 driver PID{d['driver_PID']}只允许原预登记ordinal05—24中zero0/main0支，旧driver不重启、前4条不恢复/重派**。snapshot全批zero已派{zero}/main已派{main}/终态4（3PASS/1失败），余{remaining}条完全未启动；当前ordinal{ordinal:02d} `{bulk['scope_id']}` / **{bulk['phase']}**。单GPU1/CPU38,39逐支fresh lease/容量/ownzero/cold/main；任何admission/质检/source/resource错误即停、不retry、不refit。**不要在其phase CAS附近另写H或重复driver/main-run。**
- **原协议与范围不扩：** Reach **0f9e0e03…**/AINav **0fff23aa…**，24固定ordinal、4几何/8context×3候选、**一既有TRAIN祖先，不是4独立留出**；483成员freeze/原Actor/12N/4s/FF/QP/FIFO/CLIMB stop及每scope240sim/2400wall/1GiB不动。bulk原direct raw始终**192×128，非HD**，erratum及旧误写/失败审计均保留；不能拿bulk片替T复杂成功母版。全部raw/MJB/权重/env/视频留46308，本地/GitHub只代码、小metadata/少数原query。旧46174 UNKNOWN、原closed/T pair stop、TRAIN6/critic真实一次fit、CAL07 PASS与CAL08/09/VAL未派均不被本批重置；无WM/DINO/Actor重训/真机/第二owner/新自动化。

**下一步**
- 首优先由AINav/Reach增量消费**三边界完整原件**：left原接口接受cuboid_a只解除一个必要可观测性缺口，下一需要**两策略共用、原门下可执行的PUSH/完整决策接续新源与独立freeze/预算**；Data不拿这一观察答案回填旧A/B、不凭空手工正确路线/新目标/阈值、不以OBS当T验收。尚无该合格新包时维持现有bulk滚动及原件交付，不另起观测搜索或等重复用户指令。
- suffix20继续固定未启动支，各支真实终态→cold→关闭→fresh下一支；保完整失败/UNKNOWN/成本分母，不自动训练或把整包private/GT/未来结果送NN。按合法原PREPARE/READY/CLIMB outcome作后续用途分层，不把缺测/拒绝/censor当native负例。

**详细入口**
- OBS完整原件：`{release}`；研究/审计/metadata关闭/1×视频索引：`{M}/README.md`、`{M}/completed-study-original-release-proof.json`；第二边界partial8043053c…仍保留，不覆盖成完整结果。
- bulk当前：`{K}/README.md`、`{K}/unstarted-suffix20-driver-status.json`、`{K}/drive_unstarted_suffix20_once.py`（**已启动，不要再执行**）；旧停止证据`remaining-unstarted-driver-status.json`、第4支`close-main-control.stderr`/`CAS-close-main-metadata-reconcile-v3.json`；原相机erratum `DIRECT_RAW_RESOLUTION_AND_AUDITOR_ERRATUM.json`。
- 本地code-only：`/home/yuanyue/main/code/reach-ability-research`；分支data-team-development。旧A/B原件/同钟原片：`{B}/manifests/T-COMPLEX-01-full-program-46308-20261115-v1/closed-pair-direct-video-manifest.json`。工作目录始终`{B}`，compute仅46308；原历史/失败不覆盖。
'''
entry='## 当前最高执行入口：T三视角观测完整closed、bulk四终态3PASS/1原门失败，未启动suffix有界滚动\n'+body.split('\n',1)[1]+'\n';proof=[];remote=[]
def update(p,shared=False):
 old=p.read_bytes();s=old.decode();peer=None
 if shared:
  i=s.index('## Data组');j=s.find('\n## ',i+1);j=len(s)if j<0 else j;new=(s[:i]+body+s[j:]).encode();peer=(s[:i].encode(),s[j:].encode());assert new.startswith(peer[0])and new.endswith(peer[1])
 elif p.name=='STATUS.md':
  x='<!-- NEXT_QUESTION_SAMPLING_CURRENT_BEGIN -->';y='<!-- NEXT_QUESTION_SAMPLING_CURRENT_END -->';i=s.index(x)+len(x);j=s.index(y,i);s=s[:i]+'\n'+body.split('\n',1)[1]+'\n'+s[j:];i=s.index('更新：');j=s.index('\n',i);new=(s[:i]+'更新：'+now+'（北京时间；三视角观测已closed完成非任务；bulk3PASS/1原FF失败，suffix未启动支继续）。'+s[j:]).encode()
 else:
  i=s.index('## 当前最高执行入口');j=s.index('\n## 最新用户服务器与代码决定',i);new=(s[:i]+entry+s[j+1:]).encode()
 dfd=os.open(p.parent,os.O_RDONLY|os.O_DIRECTORY)
 try:
  fcntl.flock(dfd,fcntl.LOCK_EX)
  with p.open('rb')as f:
   fcntl.flock(f,fcntl.LOCK_EX);st=os.fstat(f.fileno());assert sha(f.read())==sha(old)and(p.stat().st_dev,p.stat().st_ino)==(st.st_dev,st.st_ino)
   with(M/(p.name+'.before-complete-OBS-four-bulk-terminal')).open('xb')as out:out.write(old)
   fd,tmp=tempfile.mkstemp(prefix='.'+p.name+'.OBS-complete-',dir=p.parent)
   try:
    with os.fdopen(fd,'wb')as out:out.write(new);out.flush();os.fchmod(out.fileno(),stat.S_IMODE(st.st_mode));os.fsync(out.fileno())
    assert p.read_bytes()==old;os.replace(tmp,p);os.fsync(dfd)
   finally:
    if os.path.exists(tmp):os.unlink(tmp)
 finally:os.close(dfd)
 if shared:assert p.read_bytes().startswith(peer[0])and p.read_bytes().endswith(peer[1])
 proof.append(dict(path=str(p),before=sha(old),after=sha(new),mode=stat.S_IMODE(st.st_mode),non_Data_peer_bytes_preserved=bool(shared)))
 if not shared:remote.append(dict(name=p.name,expected=sha(old),data=base64.b64encode(new).decode()))
for folder in(M,K):
 p=folder/'README.md'
 with(folder/'README.before-complete-OBS-four-bulk-terminal.md').open('xb')as f:f.write(p.read_bytes())
 p.write_text('# 当前：T观测完整非任务、bulk3PASS/1失败、未启动suffix滚动\n'+body.split('\n',1)[1])
update(S,True)
for name in('STATUS.md','AGENTS.md','README.md'):update(B/name)
tree=ast.parse((B/'manifests/T-COMPLEX-01-full-program-46308-20261115-v1/publish_full_program_current.py').read_text());code=next(ast.literal_eval(n.value)for n in tree.body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='code'for t in n.targets))
rp=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],input=json.dumps(remote),capture_output=True,text=True,timeout=90)
for suffix,text in [('stdout',rp.stdout),('stderr',rp.stderr)]:
 with(M/('complete-study-entry-mirror.'+suffix)).open('x')as f:f.write(text)
with(M/'complete-study-publication-CAS-peer-proof.json').open('x')as f:json.dump(dict(at=now,proof=proof,remote_exit=rp.returncode,H_not_written=True,old_physical_and_failure_CAS_logs_not_changed=True),f,indent=2);f.write('\n')
assert rp.returncode==0,rp.stderr;print('Published complete OBS and four terminal bulk outcomes; Data-only peers preserved; H untouched')
