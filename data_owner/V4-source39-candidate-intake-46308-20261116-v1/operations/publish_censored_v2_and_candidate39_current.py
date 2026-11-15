"""Publish exact closed v2 wall-censor outcome and candidate39 boundary. No H/source/budget/cap changes."""
from pathlib import Path
import os,json,datetime,hashlib,fcntl,stat,tempfile,re
B=Path('/home/yuanyue/main/work/data-team');M=Path(__file__).resolve().parent;R=B/'manifests/V4-bounded-climb-nav-native-46308-20261116-v2';S=Path('/home/yuanyue/main/汇总/各小组进展汇总.md');sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();digest=lambda x:hashlib.sha256(x).hexdigest();now=datetime.datetime.now().astimezone().isoformat();assert sha(Path('/home/yuanyue/main/汇总/各小组下一步研究计划.md'))=='be3aa7e587e5aa990375d1085dde6affc497861c1d45ab01862edc2793501845'
h=json.loads((B/'registry/handoff_46308_current_status_20261115.json').read_bytes());q=h['active_V4_bounded_climb_nav_v2_scope'];assert not q['active']and q['component_zero_dispatch_count']==1 and q['task_main_dispatch_count']==0;v=json.loads((R/'actual-small/result.json').read_bytes());l=json.loads((R/'actual-small/ledger.json').read_bytes());cold=json.loads((R/'component-original-release-proof.json').read_bytes());extra=json.loads((R/'Data-budget-censor-exact-capture-and-native-boundaries.json').read_bytes());res=json.loads((R/'bounded-v2-final-authority-resource-proof.json').read_bytes());assert v['error']=='BoundedComponent1800wall cap with teardown reserve'and v['actual_task_steps']==978 and l['usage_known']and not v['close_errors']and not res['Data_runtime_worker_PIDs'];assert cold['release_sha256']=='b54503b8d19adf82980a2507425769ee70263f6c55b7382d2548a21cc46e3930';assert extra['actual_capture_commands']==448 and extra['subsequent_original_ground_NAV_preparation_commands']==530 and not extra['literal_native_terminal_receipts']
text=S.read_text();a=text.index('## Data组\n');b=text.find('\n## ',a+1);body=text[a:b if b>=0 else None];body=re.sub(r'^更新：[^\n]+',f'更新：{now}（北京时间；主计划be3aa7e5…未变；**bounded-v2已按原壁钟门resource-censor并closed：978原命令/49机载帧，未到PUSH/CLIMB接续；39源仅候选不热换、不盲重跑**）',body,count=1,flags=re.M)
new=f'''- **特定Data recorder修复v2已按原预算收束，不是native CLIMB/NAV失败：** 独立program a0e8ada0…/492成员、authority536306cb…，唯一component zero1/五main0已closed；原错误**BoundedComponent1800wall cap with teardown reserve**，实际 **1772.363236304wall /4.890任务sim /978条200Hz命令/49机载RGBD帧**，原aux6.505sim另列、4,487,295bytes、usage known/close0。原capture已真完成448步/2.240sim并同world装配，然后工程PUSH意图的**原ground NAV准备**admitted/started，实际发530步、133个原NAV Actor-forward事件；**没有NAV succeeded/failed等terminal，没有PUSH interaction/CLIMB/后继动态NAV尝试**，不造负类/失败receipt、不拿短时截断当成功成本。原resultfe3d5f6c…、正式release **b54503b8…**：`{B}/consumer-deliveries/AINAV-DATA-V4-BOUNDED-QUAL-V2-ORIGINAL-RESOURCE-AND-NATIVE-OUTCOME-20261116-v1/release.json`。492源/600原journal链、978连续命令/4步FIFO/PD raw/clip误差0、49帧clock/previous-action/storage均cold过；原状态generic failed保留，另显式resource-censor评估，不改原result。
- **边界/性能准确解释，不能拿旧owner测量或空计数造结论：** 原capture最后sample在2.240sim实际四脚≥12N/complete；闭合4.890sim的`capture.report()`是已进入NAV gait后的当前测量和历史latched完成位，3.15s不是持续四脚静止dwell，不能把其当前低脚力当2.240门被降低。原result `capture_witness_complete=false`是full-run失败分支未刷新的初始flag，以**原448步完成event＋真实witness装配**判定历史capture，不倒填原字段。壁钟吞吐极慢，06:23只读进程采样S/request_wait_answer、CPU累计约140.57s，提示文件系统等待，**未定位具体函数**；per-tick module-path/记录I/O只是候选诊断，不据此改Actor/guard或加budget。v1原错误/费用与v2分别保留，两closed root/冻结源/180sim-1800wall-1GiB cap均不复开、不追胜自动加跑。fresh 06:33 Data worker0、GPU0/1原四canonical inode均释放且H/mirror一致，owned26,134,319,616bytes/40GiB、quota未知。
'''
body,n=re.subn(r'^- \*\*只修Data recorder ABI后冻结独立v2[^\n]+\n',lambda _:new,body,count=1,flags=re.M);assert n==1
candidate=f'''- **AINav新39源修复/终点collector已收，但不倒贴给本次35源真实结果：** immutable **accbe41e…/39成员**逐SHA核同，含source自有private-catalog annotation、真实placement/CLIMB链及completed-owner high-stop/contact/.5s dwell terminal collector源码；不是完整task已可达/已native合格。当前两个Data bounded程序源仍**a703c353/35**（v2另有Data frozen adapter），未热换成39/修改owner/重渲染MJB/重写原结果。三20cm共同布局提案尚未批准/应用，原scene6394740e…/平台/Actor/原20cm门不改；static40cm、多段source/完整终点及WM bootstrap/同anchor/effects仍未通过。收件`{M}/Data-candidate39-consumed-no-hot-switch.json`。
'''
body=body.replace('\n**下一步**','\n'+candidate+'\n**下一步**',1)
body=body.replace('- 优先收束当前有限v2准确资格与原始流，任一失败保原诊断/费用，不循环追胜；AINav继续后续dynamic source/共享可行接续与完整终点，Reach完成合法bootstrap/真实causal IO/同anchor/完整cost。','- bounded-v2已按原预算收束。先对壁钟/metadata-I/O瓶颈做有界定位并保原安全语义，**不因39源到件盲重跑同样慢的整条链，不在原scope延长watchdog**；只有具体修复后的新准确完整程序才重新冻结/必要资格。AINav继续后续dynamic source/共享可行接续与完整终点，Reach完成合法bootstrap/真实causal IO/同anchor/完整cost。',1)
body=body.replace('- 当前Data bounded v1原失败/修复后v2准确程序：','- v2资源截断正式原件与精确capture/native边界：`'+str(R)+'/component-original-release-proof.json` / `'+str(R)+'/Data-budget-censor-exact-capture-and-native-boundaries.json`；39候选`'+str(M)+'/README.md`。Data bounded v1原失败/v2准确程序：',1)
proof=[]
for p in [S,B/'STATUS.md',B/'AGENTS.md',B/'README.md']:
 before=p.read_bytes();s=before.decode();mode=stat.S_IMODE(p.stat().st_mode)
 if p==S:
  a=s.index('## Data组\n');b=s.find('\n## ',a+1);b=len(s)if b<0 else b;after=(s[:a]+body.rstrip()+'\n'+s[b:]).encode();a0=before.index('## Data组\n'.encode());b0=before.find(b'\n## ',a0+1);b0=len(before)if b0<0 else b0;a1=after.index('## Data组\n'.encode());b1=after.find(b'\n## ',a1+1);b1=len(after)if b1<0 else b1;assert before[:a0]==after[:a1]and before[b0:]==after[b1:]
 elif p.name=='STATUS.md':
  begin='<!-- NEXT_QUESTION_SAMPLING_CURRENT_BEGIN -->';end='<!-- NEXT_QUESTION_SAMPLING_CURRENT_END -->';a=s.index(begin)+len(begin);b=s.index(end,a);after=(s[:a]+'\n\n'+body.split('\n\n',1)[1].rstrip()+'\n'+s[b:]).encode()
 else:
  a=s.index('## 当前最高执行入口：');b=s.index('\n## 最新用户服务器与代码决定',a);after=(s[:a]+'## 当前最高执行入口：bounded-v2原wall resource-censor已closed，先定位吞吐，不盲重跑/借39资格\n\n'+body.split('\n\n',1)[1].rstrip()+'\n'+s[b:]).encode()
 with(M/(p.name+'.before-v2-censor-closeout')).open('xb')as f:f.write(before)
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
 proof.append(dict(path=str(p),before_sha256=digest(before),after_sha256=digest(after),mode_preserved=stat.S_IMODE(p.stat().st_mode)==mode,shared_peer_bytes_preserved=p==S))
with(M/'Data-only-v2-censor-publication-proof.json').open('x')as f:json.dump(dict(at=now,proof=proof,all_shared_peer_bytes_preserved=True,no_H_original_result_or_frozen_source_changes=True),f,ensure_ascii=False,indent=2);f.write('\n')
old=(R/'README.md').read_bytes();(R/'README.md.before-resource-censor-closeout').write_bytes(old);(R/'README.md').write_text(f'''# v2原wall门resource-censor已closed，不重跑/延budget\n\n{now}：programa0e8ada0/492、authority536306cb，source35＋Data metadata adapter不变，原wall guard停止，实际1772.363236304wall/4.890task sim/978命令/49机载帧；aux6.505sim另列、4487295bytes、known/close0。capture448步/2.240sim真完成，随后ground NAV准备530步/133原Actor forward，仍未完成NAV/进入PUSH interaction或CLIMB/动态handoff。资源截断不是native负类/失败回执。\n\n原resultfe3d5f6c…/releaseb54503b8d19adf82980a2507425769ee70263f6c55b7382d2548a21cc46e3930已本/新端交付，源码492/原journal600行/978 FIFO-PD-clip/49帧clock等cold过，原generic状态不改。闭合后native worker0/规范锁释放。capture.report晚时刻是NAV gait当前测量＋历史complete，不能当2.240完成边界/3.15s持续静止；capture_witness_complete初始flag未刷新的原字段也保留，精确原event解释在Data-budget-censor-exact-capture-and-native-boundaries.json。\n\nwall吞吐慢、只读wchan request_wait_answer提示FS等待，尚未定位到具体函数。先做有界性能定位并保安全语义，不盲跑新39源/不改本budget/不热修本程序。当前两个bounded scope均closed且已耗唯一资格，不再执行任何once。source39只候选、三20cm布局未应用，不把原35-source结果记成39合格。v1原recorder失败/费用和5项纯metadata修复证据全部留存。以下在途记录是历史。\n\n---\n\n'''+old.decode())
print(json.dumps(dict(at=now,v2_closed_resource_censor=True,native_terminals=0,commands=978,frames=49,candidate39_not_live_or_qualified=True,shared_Data_only_updated=True),ensure_ascii=False))
