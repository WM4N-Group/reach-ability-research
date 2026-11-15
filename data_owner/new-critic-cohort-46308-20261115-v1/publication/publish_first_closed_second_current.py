from pathlib import Path
import json,datetime,hashlib,fcntl,os,stat,tempfile,re,ast,subprocess,shlex,base64
B=Path('/home/yuanyue/main/work/data-team');M=Path(__file__).resolve().parent;P=B/'manifests/g2-full2-46308-20261115-v1';S=Path('/home/yuanyue/main/汇总/各小组进展汇总.md');now=datetime.datetime.now().astimezone().isoformat();sha=lambda b:hashlib.sha256(b).hexdigest();h=json.loads((B/'registry/handoff_46308_current_status_20261115.json').read_bytes());co=h['new_critic_cohort_v1'];q=h['active_new_critic_cohort_scope'];assert q['candidate_id']=='new_critic_02_full4_right_original'and q['active']and q['phase']=='CAS_DISPATCHED_MAIN';assert co['branches']['new_critic_01_full4_left_original']['status']=='CLOSED_ACTUAL_MAIN_PASS'
D=B/'consumer-deliveries/AINAV-DATA-NEW-CRITIC-46308-ORDINAL-01-ACTUAL-20261115-v1';release=json.loads((D/'release.json').read_bytes());assert sha((D/'release.json').read_bytes())=='f253b6afc8fa58a75f0ef961d6ed03ecef7a1bc44a16b3d1cfc9c55e46186a0c';assert all(sha((D/n).read_bytes())==s for n,s in release['files'].items());summary=release['actual_summary'];assert summary['source_result_passed']and all(summary['nine_stream_checks'].values())
body=f'''更新：{now}（北京时间；主计划仍53233939…；新用途TRAIN01真实PASS/closed/九流cold，原件已交；TRAIN02自身zero/cold通过、唯一main在途，继续固定TRAIN6后停门）

**当前状态**
- **首条真正新用途TRAIN采集已闭合，非旧DEV重标：** ordinal01 full4-left-original新program b738125e…/新scope在13:04:02唯一派发、13:17:30 CAS closed，原NAV→PUSH→CLIMB exact3 PASS，**121.085sim/24217步/1211 RGBD与review帧、5native options/10literal回执**。同本scope新zero/main model7b9ed33e…、九流cold全过，FIFO/PD/hardclip误差0/teardown无误。相同原init/4301有相同任务结果不等复用旧世界/zero/数据；scene/祖先仍同TRAIN组，不增加独立scene数或统计功效。
- **可消费原始新用途数据已发布：** ordinal01 release **f253b6af…**，约1.16MB必要public/metadata、5真实Host query。首次原CLIMB PREPARE **97.285sim/frame-000004**，由first literal skill_execution_judgment→exact preparation binding→actual Observation语义SHA定位，不以proposal/固定编号/nearest/后READY替代；保原source bytes/clock/record-chain。新增acquisition manifest/protocol2f82530d…明示NEW purpose/TRAIN角色；native训练flag仍false仅说明native进程不训练，不改旧physical protocol或旧结果。public/evidence分层，私有config/pose/force/未来图不入48槽；whole package不可喂模型，**这一子包不是fit许可**，Reach按既有新用途提取器做原READY/原CLIMB终态监督，不由Data产NN表/替它拟合。
- **真实费用与下一在途：** ordinal01 scope含自身zero/两次aux **134.095sim / 832.970434ledger wall / 177094914bytes highwater**，不是全batch最终费用/方法收益。ordinal02 full4-right-original programdc58bd6c…自身zero/cold通过，13:18:37唯一main CAS、实际PID21808；13:22:14 ledger仍open（50.120含auxsim/216.705904wall只是快照），未报PASS/最终cost。第3—6 zero/main均0，第7—12仍NOT_DISPATCHED_BLOCKED_TRAIN_GATE；独立有限pipeline继续原顺序，不重复启动/无替代重试。发布只读已closed01，未读在途02为模型输入、未写H干扰pipeline CAS。
- **协议/安全/容量保持：** 固定Reach2f82530d… 6/3/3未来新scope，TRAIN full4两prefix×original/±.04，CAL full1左3，VAL full2左3，whole-scene/祖先不拆臂/ID/reset；full1 C质量1kg/mu.3和独立原protocol显式，旧helper458ec66e…材料guard不改。Data plan payload真交原installer/同Host/common-stow，Actor/init4301/12N/4s/FF/QP/FIFO/stop不变；外层累计240sim含zero/aux、2400wall、1GiB，zero180wall，资源失败是censor、完整性/共享资源问题停后续。仅46308 GPU1 UUID6d66aa68…/device51规范inode3428459217、3428459218/私有Expat精确loader；每phase fresh lease，40GiB自限/12root×1.5GiB容量预留不冒provider quota或未来lease。

**正在做／下一项／独立备选**
- **先完整TRAIN6再判，不因当前1条提前fit或No-Go：** 现1closed PASS/1main在途/4TRAIN未派；按预登记1原left→2原right→3plus-left→4plus-right→5minus-left→6minus-right，每root自己zero/main/cold/close。对后续failure/未达/censor原分母、无terminal回执/未知成功cost保None，不补帧/造CLIMB负行/换seed挖类。
- **闭合TRAIN才G3单次fit或有限No-Go：** 要求≥2 reached prefix/≥2公共proprio状态/≥3成功/≥1**真实决策后native失败**且source/48槽完整；不满足就停采不fit、不派CAL/VAL、不补样。Reach已解除原fit要求三split齐的时序阻塞，TRAIN-only→frozen CAL/VAL只评价入口已实际软件核/部署，不再让Data等模型或新接口。当前controller硬拒ordinal>6，6结束停物理，不能热改已freeze control；后续CAL/VAL须原协议SHA+真实gate/单次fit的新派生准入，不自动跨门，G4/G5另协议。
- **旧域/边界不动：** 原5DEV仍closed且禁fit，full2right原PUSH卸载异常/未到CLIMB保历史；full1原PASS2bae0f2a…/full2完整9be124b3…/三源01e2571a…原字节不变。旧46174一次行政UNKNOWN停止追踪、新v1 XML/StageB账与未知尾费保留，center/upper-entry暂停。科学21/3650/strict3/TEST0，真实fit0；WM/DINO/Actor/真机/第二owner不开，自动化未改；代码和小必要原件本地/GitHub，dense数组/环境/权重/视频留远端。

**入口**：[首新用途TRAIN01完整原件]({D}/release.json) · [真实结果/费用/first-PREPARE]({D}/actual-summary.json) · [新用途与标签/输入边界]({D}/source-clock-and-role-policy.json) · [有限TRAIN6运行日志]({M}/TRAIN-pipeline.stdout) · [当前权威镜像]({B}/registry/handoff_46308_current_status_20261115.json) · [本批详细/协议]({M}/README.md)
'''
banner=f'''## 当前最高执行入口：新用途TRAIN01真实PASS/closed已交，TRAIN02 main在途，固定TRAIN6后必须停门（{now}）

**ordinal01 programb738125e…/zero1/main1已耗，13:17:30 PASS closed/九流cold；121.085sim/24217步/1211帧、5原query，releasef253b6af…已交。** 原first CLIMB PREPARE97.285/frame-000004按原judgment/ref/Host Observation匹配；新用途manifest明确TRAIN，不是旧DEV重标。原件`{D}/release.json`。ordinal02 programdc58bd6c…自身zero/cold PASS，13:18:37唯一main CAS，实际PID21808在途，尚无最终结果。不要重启pipeline/任何已耗launcher。

当前authority88bb1827…/cohort2f82530d…，H active_new_critic_cohort_scope/new_critic_cohort_v1，同真实窗口01a1d3aa-a0d5-7de0-b886-9d92ed5f1480。TRAIN1..6固定原左右→plus左右→minus左右各自zero/main/cold/close；CAL7..9/VAL10..12未派且硬阻。TRAIN6全闭合才按两prefix/两公共状态/≥3成功/≥1决策后native失败/完整48槽判gate，失败No-Go不fit/不补类；通过才Reach派生一次fit。**当前1条不足以fit，不能因部分结果提前判断或自动跨CAL/VAL。** 不热改frozen controller/原门。

原Actor/init4301/12N/4s/FF/QP/FIFO/stop/SDK/私有Expat不改，外层240sim含own-zero/aux、2400wall、1GiB、zero180wall更严，资源是censor；仅46308 GPU1 UUID6d66aa68…/device51规范inode3428459217、3428459218，每phase fresh lease。原5DEV不重跑/不转fit，旧full2right未达CLIMB不造负行，所有旧UNKNOWN/失败/费用不洗、不连旧端。训练0/TEST0、WM/DINO/Actor/真机/第二owner不开，自动化未改。详细`{M}/README.md`；以下仅历史。

'''
remote=[];proof=[]
def edit(p,new,label,peer=False):
 old=p.read_bytes();d=os.open(p.parent,os.O_RDONLY|os.O_DIRECTORY)
 try:
  fcntl.flock(d,fcntl.LOCK_EX)
  with p.open('rb')as f:
   fcntl.flock(f,fcntl.LOCK_EX);got=f.read();st=os.fstat(f.fileno());assert got==old and(p.stat().st_dev,p.stat().st_ino)==(st.st_dev,st.st_ino);(M/(label+'-before-TRAIN01-release.md')).write_bytes(old);fd,t=tempfile.mkstemp(prefix='.'+p.name+'.TRAIN01-release-',dir=p.parent)
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
p=B/'STATUS.md';s=p.read_text();a='<!-- NEXT_QUESTION_SAMPLING_CURRENT_BEGIN -->';b='<!-- NEXT_QUESTION_SAMPLING_CURRENT_END -->';i=s.index(a)+len(a);j=s.index(b,i);s=s[:i]+'\n'+body+'\n'+s[j:];s=re.sub(r'更新：[^\n]+',f'更新：{now}（北京时间；新用途TRAIN01真实PASS/closed/九流cold及原件齐，TRAIN02 main在途，固定六支后停门）。',s,count=1);edit(p,s.encode(),'STATUS')
edit(M/'README.md',('# NEW-purpose finite conditional critic acquisition: first closed release, TRAIN6 in progress\n\n'+body).encode(),'detailed-README')
tree=ast.parse((P/'publish_current_progress.py').read_bytes());code=next(ast.literal_eval(n.value)for n in tree.body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='code'for t in n.targets));code=code.replace('g2-full2-46308-20261115-v1','new-critic-cohort-46308-20261115-v1').replace('before-full2-live','before-TRAIN01-release');r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],input=json.dumps(remote),capture_output=True,text=True,timeout=90)
for suf,t in [('stdout',r.stdout),('stderr',r.stderr),('exit',str(r.returncode)+'\n')]:(M/('TRAIN01-entry-mirror.'+suf)).write_text(t)
(M/'TRAIN01-publication-CAS-peer-proof.json').write_text(json.dumps(dict(at=now,local=proof,remote_exit=r.returncode,other_groups_bytes_preserved=True,H_and_frozen_pipeline_not_modified=True),indent=2)+'\n');assert r.returncode==0,r.stderr;print('New TRAIN01 original release/current TRAIN02 published; peer text and active pipeline untouched')
