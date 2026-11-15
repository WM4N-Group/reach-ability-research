"""Publish real v1 failure and separately frozen v2 status. Data-only CAS; no native phase mutation."""
from pathlib import Path
import os,json,datetime,hashlib,fcntl,stat,tempfile,re
B=Path('/home/yuanyue/main/work/data-team');M=Path(__file__).resolve().parent;P=B/'manifests/V4-bounded-climb-nav-native-46308-20261116-v1';K=B/'manifests/bulk24-collector-46308-20261115-v1';J=B/'manifests/V-JEPA-J1-resource-response-46308-20261116-v1';S=Path('/home/yuanyue/main/汇总/各小组进展汇总.md');sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();digest=lambda b:hashlib.sha256(b).hexdigest();now=datetime.datetime.now().astimezone().isoformat();plan=Path('/home/yuanyue/main/汇总/各小组下一步研究计划.md');assert sha(plan)=='be3aa7e587e5aa990375d1085dde6affc497861c1d45ab01862edc2793501845'
h=json.loads((B/'registry/handoff_46308_current_status_20261115.json').read_bytes());old=h['active_V4_bounded_climb_nav_scope'];q=h['active_V4_bounded_climb_nav_v2_scope'];assert not old['active']and old['component_zero_dispatch_count']==1 and old['actual_result_sha256']=='1469fdb251879c9b834476bc28636917b4016fe6d1dd0a794574b6e315f84525';assert q['component_zero_dispatch_count']==1 and q['task_main_dispatch_count']==0
v1=json.loads((P/'actual-small/result.json').read_bytes());assert not v1['passed']and v1['actual_task_steps']==0 and v1['error']=='Exact private catalog boundary required';proof=json.loads((P/'component-original-release-proof.json').read_bytes());v2inv=json.loads((M/'inventory-control-proof.json').read_bytes());cfg=json.loads((B/'workers'/M.name/'protocol.json').read_bytes());assert json.loads((M/'new5-private-catalog-metadata-checks.json').read_bytes())['checks_passed']==5
state='在途'if q['active']else'已关闭（结果以原result为准）'
text=S.read_text();a=text.index('## Data组\n');b=text.find('\n## ',a+1);body=text[a:b if b>=0 else None];body=re.sub(r'^更新：[^\n]+',f'更新：{now}（北京时间；新计划be3aa7e5…已读；**source35有限handoff已接，首次新资格v1在recorder门前0任务步failed/closed；特定Data ABI修复v2新程序{state}，非五组main**）',body,count=1,flags=re.M)
new=f'''- **source35已接完原先缺的有限factory/outer/public接线，并首次进入Data新准确程序资格：** immutable AINav **a703c353…/35源＋7原parent依赖**，同源30 intents（20NAV/6PUSH/4CLIMB）/27 anchors，仅新增3个box-top-centre有限NAV，scene6394740e…不改。typed-source registry lookup/selected NAV constructor/outer selected-box contact与旧private option identity在新source连上，不再写“只有inner、没有dispatcher”。这仍只单次CLIMB→NAV，非第二handoff/完整平台/五组资格；Data本次API0工程policy只选首个公开X序箱的原required PUSH→同箱20cm CLIMB→共有top-centre NAV，可有一次共有ground approach。**内部C flag只配置legacy-H ON/new-selector OFF，不是实际C或E方法，VLM/WM/新优化0、五main0**，无HD影片资格。
- **实际v1失败原件已交，不能洗成native CLIMB/NAV失败：** 程序 **788c6116…/491成员**、authorityc5bd3a6e…，新Runtime/原静态MJB后首次capture_grid到writer，因Data裸writer缺`model_input_allowed=False`显式隐私annotation而被原`Exact private catalog boundary required`拒绝；原observer已有`model_input=False`。**任务0步/0sim、capture未完成、选择/原动作controller/admission0、0归档帧**。只有原aux1world/6.505sim、24.690580467wall/12,013bytes，usage known/close0；原result1469fdb2…，正式release **{proof['release_sha256'][:12]}…**：`{B}/consumer-deliveries/AINAV-DATA-V4-BOUNDED-QUAL-RECORDER-CATALOG-FAILED-BEFORE-TASK-20261116-v1/release.json`。空流equality不是PD/视觉覆盖，不补CLIMB失败/成功或训练label；v1保持closed/zero1/main0，原worker/protocol/H账不回写。
- **只修Data recorder ABI后冻结独立v2，旧scope没有重开：** `PrivateCatalogBoundaryWriter`严格核原RegisteredObserver schema/tick/model_input=False、冲突True拒绝，只对metadata副本加原standalone caller同一annotation；packet/标定/原private payload/200Hz timing不动，原writer所有检查与Actor/NN/12N/FF/4s/FIFO/stop保持。5个新纯metadata检查过，非旧fixture重刷。v2 program **{v2inv['program_sha256'][:12]}…/{v2inv['members']}成员**，authority **{v2inv['authorization_sha256'][:12]}…**，scope`{q['scope_id']}` **{state}**；唯一component资格≤1、五组main0，180任务sim/1800wall/1GiB、GPU0 UUID297c…/own3GiB/RSS4GiB/CPU36,37，失败不另换目标/seed追胜。只读旧已核**静态MJB0b3547b0…**作输入，新Runtime/task0/empty FIFO/owner/lease，不恢复任何旧state或借旧zero、不重编旧asset；v1费用/result另计，未来不同full-program仍须自身资格。状态`{M}/latest-progress-pointer.json`与权威H `active_V4_bounded_climb_nav_v2_scope`，**不得重复once控制器**。
'''
body,n=re.subn(r'^- \*\*CLIMB→NAV已从32源必要观测推进typed inner adapter源码[^\n]+\n',lambda _:new,body,count=1,flags=re.M);assert n==1
body=body.replace('dynamic-box CLIMB→NAV support/contact-owner、static deck','single dynamic CLIMB→NAV当前仅source接通、须本必要新资格实测；后续dynamic source链/static deck',1)
body=body.replace('当前固定24**不再派发**','当前固定24**不再派发**',1)
body=body.replace('- 优先接V4：AINav完成真实support/contact-owner/共享可行接续与终点，Reach完成合法bootstrap/真实causal IO/同anchor/完整cost。','- 优先收束当前有限v2准确资格与原始流，任一失败保原诊断/费用，不循环追胜；AINav继续后续dynamic source/共享可行接续与完整终点，Reach完成合法bootstrap/真实causal IO/同anchor/完整cost。',1)
j2a=f'''- **05:34计划新增J2a可选TRAIN-only工程入口已消费，不偷偷另开采集或fit：** 原请求pin不变，single-front ground-PUSH、4—8不同execution/至少2公开goal、6D参数/存在mask、无bbox/ID特征、TRAIN-only同一祖先可用、≤25步method-check；不碰CAL/EVAL/不泛化或排序/系统结论，原2TRAIN+CAL/8段研究比较门不改。若原方案已够直接复用，不额外采第二批。当前仍无VJEPA_WM用途原release/新cohort/实际fit/GPU授予；**本次V4 component目的与原件不转J训练**，具体未来新source/停止预算由Data另冻结。收件`{J}/Data-J2a-optional-TRAIN-only-entry-received-not-dispatch.json`，不再等权重许可/额外签字。
'''
body=body.replace('\n**下一步**','\n'+j2a+'\n**下一步**',1)
body=body.replace('- V4新34源typed inner adapter：','- 当前Data bounded v1原失败/修复后v2准确程序：`'+str(P)+'/README.md` / `'+str(M)+'/README.md`；旧V4 34源typed inner adapter：',1)
proofs=[]
for p in [S,B/'STATUS.md',B/'AGENTS.md',B/'README.md']:
 before=p.read_bytes();s=before.decode();mode=stat.S_IMODE(p.stat().st_mode)
 if p==S:
  a=s.index('## Data组\n');b=s.find('\n## ',a+1);b=len(s)if b<0 else b;after=(s[:a]+body.rstrip()+'\n'+s[b:]).encode();a0=before.index('## Data组\n'.encode());b0=before.find(b'\n## ',a0+1);b0=len(before)if b0<0 else b0;a1=after.index('## Data组\n'.encode());b1=after.find(b'\n## ',a1+1);b1=len(after)if b1<0 else b1;assert before[:a0]==after[:a1]and before[b0:]==after[b1:]
 elif p.name=='STATUS.md':
  begin='<!-- NEXT_QUESTION_SAMPLING_CURRENT_BEGIN -->';end='<!-- NEXT_QUESTION_SAMPLING_CURRENT_END -->';a=s.index(begin)+len(begin);b=s.index(end,a);after=(s[:a]+'\n\n'+body.split('\n\n',1)[1].rstrip()+'\n'+s[b:]).encode()
 else:
  a=s.index('## 当前最高执行入口：');b=s.index('\n## 最新用户服务器与代码决定',a);after=(s[:a]+'## 当前最高执行入口：35源有限native资格v1 recorder failed已closed；特定Data ABI修复v2独立新程序\n\n'+body.split('\n\n',1)[1].rstrip()+'\n'+s[b:]).encode()
 with(M/(p.name+'.before-bounded-current')).open('xb')as f:f.write(before)
 dfd=os.open(p.parent,os.O_RDONLY|os.O_DIRECTORY)
 try:
  fcntl.flock(dfd,fcntl.LOCK_EX)
  with p.open('rb')as f:
   fcntl.flock(f.fileno(),fcntl.LOCK_EX);assert p.read_bytes()==before;fd,tmp=tempfile.mkstemp(prefix='.'+p.name+'.cas.',dir=p.parent)
   try:
    with os.fdopen(fd,'wb')as out:os.fchmod(out.fileno(),mode);out.write(after);out.flush();os.fsync(out.fileno())
    assert p.read_bytes()==before;os.replace(tmp,p);os.fsync(dfd)
   finally:
    if os.path.exists(tmp):os.unlink(tmp)
 finally:os.close(dfd)
 proofs.append(dict(path=str(p),before_sha256=digest(before),after_sha256=digest(after),mode_preserved=stat.S_IMODE(p.stat().st_mode)==mode,shared_peer_bytes_preserved=p==S))
with(M/'Data-only-bounded-publication-proof.json').open('x')as f:json.dump(dict(at=now,proofs=proofs,all_shared_peer_bytes_preserved=True,no_H_or_frozen_program_mutations=True),f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps(dict(at=now,v1_failed_closed_before_task=True,v2_state=state,program_sha256=v2inv['program_sha256'],members=v2inv['members'],shared_Data_only_updated=True),ensure_ascii=False))
