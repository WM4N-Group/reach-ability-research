"""Publish partial closed24 metadata and static method-risk intake; never alter H/native/optimizer."""
from pathlib import Path
import os,json,datetime,hashlib,fcntl,stat,tempfile,re
B=Path('/home/yuanyue/main/work/data-team');M=Path(__file__).resolve().parent;F=B/'manifests/V4-pre-main-factor-and-bootstrap-review-46308-20261116-v1';K=B/'manifests/bulk24-collector-46308-20261115-v1';J=B/'manifests/V-JEPA-J1-resource-response-46308-20261116-v1';S=Path('/home/yuanyue/main/汇总/各小组进展汇总.md');sha=lambda x:hashlib.sha256(x).hexdigest();now=datetime.datetime.now().astimezone().isoformat();assert sha(Path('/home/yuanyue/main/汇总/各小组下一步研究计划.md').read_bytes())=='42c8a90d31e84d8d3b0c832a405b0a654ad82319f3c0b7f5da49982c1f3cfc3a'
pointer=json.loads((M/'latest-snapshot-pointer.json').read_bytes());snapraw=(M/pointer['file']).read_bytes();assert sha(snapraw)==pointer['sha256'];snap=json.loads(snapraw);assert snap['closed']==23 and snap['conditional_original_chain_PASS']==10 and snap['closed_nonPASS']==13 and not snap['batch_physically_and_metadata_closed']and snap['formal_original_releases_count']==23 and snap['formal_original_public_queries']==82
rows=snap['rows'];assert rows[9]['CLIMB_interaction_native_admitted']is True and rows[9]['literal_CLIMB_terminal_receipts']is None and rows[20]['CLIMB_interaction_native_admitted']is True and rows[20]['literal_CLIMB_terminal_receipts']is None;assert snap['closed_ledger_usage_all_known']and snap['inflight_or_future_costs_unknown_not_zero'];assert not json.loads((F/'Data-pre-main-factor-and-bootstrap-review.json').read_bytes())['scope_decision']['optional_strict_factor_helper_not_adopted_by_Data']is False
d=json.loads((K/'unstarted-suffix20-driver-status.json').read_bytes());assert not d['global_stop'];before=S.read_text();a=before.index('## Data组\n');b=before.find('\n## ',a+1);body=before[a:b if b>=0 else None];body=re.sub(r'^更新：[^\n]+',f'更新：{now}（北京时间；主计划42c8a90d…未变；**bulk01—23原件交齐/82原queries，最后24在途；V4五组main0，未新增物理资格或改变共同底座**）',body,count=1,flags=re.M)
bulk=f'''- **bulk固定24进入最后一支，尚未全批closed：** 快照{d['at']}，zero{d['zero_dispatches']}/main{d['main_dispatches']}/closed{d['closed_main']}（{d['conditional_PASS']}原链PASS/{d['closed_native_failed']}原生失败），真正未启动{d['remaining_not_started']}；当前`{d['current_scope']}` / {d['status']}，global_stop=false。新增21 runtime `base_collision`（实际CLIMB已admitted但无succeeded/failed terminal，不补回执或自动critic label）、22原settle失败、23原FF门拒；后三支7+3=10原public queries，**01—23正式release累计82原query**，均known、非resource censor。12/14/…/22/23等未到CLIMB者不造负例，10/21两次base_collision单列。GPU1/CPU38,39原slot/ownzero/cold/main一次、240sim/2400wall/1GiB/483源不变；raw192×128非HD、四geometry同1 TRAIN祖先、critic不refit，不手写phase/H或追胜重跑。
- **只读收束工具已接实际原件，未把最后一支算完：** `{M}/run_scalar_closeout_readonly.py`只读H/原result/cold-audit/ledger/formal release，不import模型/Runtime。03:14 snapshot **23closed=10PASS/13非PASS**，原原因分为FF6/settle5/base_collision2；12支达到首CLIMB PREPARE且原生admitted，2支collision的终端仍None。23已闭scope合计含ownzero/aux **2608.510sim /18248.013831574wall**（非当前总磁盘或方法成功成本），usage全known；24剩余/尾费UNKNOWN不补0，物理闭合与24正式release完整性分别列flag。ordinal01原v1/其余v2字段差异已按原boundary读取；初次reader KeyError及本地23-wrapper拼名错误留证，均0物理/原流重试。
'''
body=re.sub(r'^- \*\*bulk新交19/20：\*\*[^\n]+\n',lambda _:bulk,body,count=1,flags=re.M)
factor=f'''- **新方法身份风险已按immutable源核，不等同已污染结果：** Reach审阅指出4909180a live driver借用的`_install_common_stow` **e658b891…**会不分arm `bind_to_host(enabled=True)`；Data独立核新端immutable原method/实际binder SHA与末尾setattr。若旧H为固定legacy-common强底座应保留且与new-successor B/D分层计数，**不为泛称优化0擅删共同项削弱C**；只有method owner明确其为本次treatment才采用可选strict helper。本回合没有采用helper/安装或删callback/改source/重跑fixture/native；原25源capture不调用此live installer、没构造选中PUSH，五main0，旧资格不因此失效。原SupportedCapture不是已建模WM owner；五组共用公开NAV观察bootstrap仍仅提案，不先偷偷执行/首次A/B退成VLM-only。正式收件`{F}/Data-pre-main-factor-and-bootstrap-review.json`，不是新增用户成本/箱参数/签字门。
'''
body=body.replace('\n**下一步**', '\n'+factor+'\n**下一步**',1)
body=body.replace('- AINav继续真实support/contact-owner/完整终点与共同技能域方案；Reach完成真实causal IO/同anchor目标/完整后继cost。','- AINav继续真实support/contact-owner/完整终点与共同技能域方案；Reach完成真实causal IO/同anchor目标/完整后继cost。首次full-program freeze前明确legacy-common与new-successor层级/实际callback和合法WM bootstrap；不要求用户重复签字、不削弱原完整C。',1)
body=body.replace('- bulk新索引closed19to20及此前', '- bulk新增closed21to22/closed23索引与只读partial收束`'+str(M)+'/latest-snapshot-pointer.json`；此前closed19to20及',1)
(M/'README.md').write_text(f'''# bulk24只读partial closeout工具（{now}）\n\n`summarize_fixed24_readonly.py`只读权威H/每支原result/cold-audit/ledger/formal release，固定24项，不动H/phase/锁/模型/Actor/原流；`run_scalar_closeout_readonly.py`可在状态有变化后重复读取，输出带SHA的时间戳snapshot。无新world、队列、source import、fit或scope重开。\n\n当前23closed=10原链PASS/13原生非PASS，FF6/settle5/base_collision2，12支到首CLIMB PREPARE/admitted；10/21碰撞均没有原CLIMB终端，不补失败label。24在途不计失败，尾费UNKNOWN，不把23已闭scope费用当完整24总成本。已闭费用含各自ownzero/aux，2608.510sim/18248.013831574wall；所有known。四geometry同1 TRAIN祖先，不独立TEST/方法对照或自动refit。\n\n正式01—23=82原queries，原件索引closed21to22/closed23（旧全部保留）；当24原closed且正式交付后再按既有工具生成final快照。`batch_physically_and_metadata_closed`仅物理H scope闭合，`all_fixed24_formal_originals_released`单列正式原件完整性，不混同。原始snapshot/初始v1字段KeyError日志与修正原件保留，不改原v1 release。\n\nV4最新27-source未变，无新native/五main；另静态消费Reach legacy-common/new-treatment风险与WM bootstrap边界：{F}/README.md，不擅改common stow/optional helper或旧资格。J新的独立低优先级CPU/下载窗口仍至04:15（GPU lease0、无数据fit/新cohort），不代起J job，不自动扩窗。\n''')
(F/'README.md').write_text('''# 首个full-program freeze前的方法身份/WM bootstrap边界核查\n\n已按AINav immutable4909180a的live_driver原字节、其原parent `_install_common_stow` exact method e658b891…与Reach v2 binder23c1d6b5…核同；AST确认constructor调用旧installer、其enabled=True无arm判断、结尾setattr可覆盖早定义override。本组未import native/重复CPU fixture/改任何owner源码或callback。初次本地checker把direct Name call和局部变量名写成错误形状的断言保留，后按实际AST核，不是source或物理失败。\n\n旧common stow若为已固定共同强底座，保留且分层计数，不为泛称优化0削弱原完整AINav C；若owner明确是本次treatment，才在task0按预定arm/flag采用可选strict helper。Data没有擅自选边/采用helper，不向用户新增许可/签字门，也不让此review复开/否定已closed25源capture/assembly。原25源组件没有构造选中PUSH或调用新live driver的installer，五组main0，不能声称已污染实验。\n\nSupportedCapture不是原WM已建模owner，帧未送WM；共享公开NAV观察prelude只是源owner/方法协议提案，尚未冻结或执行，不能把首次A/B静默退成VLM-only。未来实际source/完整程序自己的资格、真实owner/96×64同anchor/全部200Hz已发参考与source用途仍需如实接通。\n\n准确收件 Data-pre-main-factor-and-bootstrap-review.json；原Reach报告/说明与immutable method片段同时保留。\n''')
proof=[]
def update(path,transform,shared=False):
 before=path.read_bytes();after=transform(before.decode()).encode();mode=stat.S_IMODE(path.stat().st_mode);backup=M/(path.name+'.before-incremental-source-and-releases')
 with backup.open('xb')as f:f.write(before)
 dfd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY);tmp=None
 try:
  fcntl.flock(dfd,fcntl.LOCK_EX)
  with path.open('rb')as f:
   fcntl.flock(f.fileno(),fcntl.LOCK_EX);assert path.read_bytes()==before,'SHA CAS conflict'
   if shared:
    a=before.index(b'## Data\xe7\xbb\x84\n');b=before.find(b'\n## ',a+1);b=len(before)if b<0 else b
    a2=after.index(b'## Data\xe7\xbb\x84\n');b2=after.find(b'\n## ',a2+1);b2=len(after)if b2<0 else b2
    assert before[:a]==after[:a2]and before[b:]==after[b2:],'Peer bytes changed'
   fd,tmp=tempfile.mkstemp(prefix='.'+path.name+'.cas.',dir=path.parent)
   with os.fdopen(fd,'wb')as out:os.fchmod(out.fileno(),mode);out.write(after);out.flush();os.fsync(out.fileno())
   assert path.read_bytes()==before;os.replace(tmp,path);tmp=None;os.fsync(dfd)
 finally:
  if tmp:os.unlink(tmp)
  os.close(dfd)
 proof.append(dict(path=str(path),before_sha256=sha(before),after_sha256=sha(after),mode_preserved=stat.S_IMODE(path.stat().st_mode)==mode,peer_bytes_preserved=shared))
def repl_shared(s):
 a=s.index('## Data组\n');b=s.find('\n## ',a+1);b=len(s)if b<0 else b
 return s[:a]+body.rstrip()+'\n'+s[b:]
update(S,repl_shared,True)
current=body.split('\n\n',1)[1]
def st(s):
 begin='<!-- NEXT_QUESTION_SAMPLING_CURRENT_BEGIN -->';end='<!-- NEXT_QUESTION_SAMPLING_CURRENT_END -->';a=s.index(begin)+len(begin);b=s.index(end,a);s=s[:a]+'\n\n'+current.rstrip()+'\n'+s[b:]
 return re.sub(r'更新：[^\n]+',f'更新：{now}（北京时间；当前状态以第1节新入口为准）。',s,count=1)
update(B/'STATUS.md',st)
for name in ['AGENTS.md','README.md']:
 def f(s):
  a=s.index('## 当前最高执行入口：');b=s.index('\n## 最新用户服务器与代码决定',a)
  return s[:a]+'## 当前最高执行入口：bulk01—23原件已交/最后24在途；V4 common-vs-treatment源核查已收，五main0\n\n'+current.rstrip()+'\n'+s[b:]
 update(B/name,f)
with(M/'Data-only-publication-proof.json').open('x')as f:json.dump(dict(at=now,proof=proof,no_H_worker_or_program_changes=True,all_shared_peer_bytes_preserved=True),f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps(dict(at=now,shared_Data_only_updated=True,driver_snapshot=d,released_public_queries=82),ensure_ascii=False))
