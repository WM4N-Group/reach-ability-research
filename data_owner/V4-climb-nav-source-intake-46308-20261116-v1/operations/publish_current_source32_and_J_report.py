"""Replace Data-only current source/resource status. No native/optimizer/H writes."""
from pathlib import Path
import os,json,datetime,hashlib,fcntl,stat,tempfile,re
B=Path('/home/yuanyue/main/work/data-team');M=Path(__file__).resolve().parent;K=B/'manifests/bulk24-collector-46308-20261115-v1';J=B/'manifests/V-JEPA-J1-resource-response-46308-20261116-v1';S=Path('/home/yuanyue/main/汇总/各小组进展汇总.md');sha=lambda x:hashlib.sha256(x).hexdigest();now=datetime.datetime.now().astimezone().isoformat();assert sha(Path('/home/yuanyue/main/汇总/各小组下一步研究计划.md').read_bytes())=='22f570c1d74340287088f34eeaf5bce694d53317876bb826956f71321d6c0b65';d=json.loads((K/'unstarted-suffix20-driver-status.json').read_bytes());assert d['status']=='FIXED24_CLOSED_NO_REFIT'and d['closed_main']==24
c=json.loads((M/'Data-climb-nav-source32-consumption-not-handoff.json').read_bytes());assert c['all32_remote_local_exact_bytes_verified']and c['actual_observer_or_CLIMB_NAV_native_calls_by_Data']==0;j=json.loads((J/'Data-J1-download-completion-report-consumed.json').read_bytes());assert j['report_matches_preverified_official_pin']and j['Data_model_weight_download_rehash_restore_forward_fit_calls']==0
text=S.read_text();a=text.index('## Data组\n');b=text.find('\n## ',a+1);body=text[a:b if b>=0 else None];body=re.sub(r'^更新：[^\n]+',f'更新：{now}（北京时间；04:12新计划22f570c1…已读（仅J真实技术进度增量，旧freeze不回写）；**fixed24全closed/84query不变，V4新32源必要source观测已收但非active NAV handoff；J完整技术报告已收，不冒真实数据训练**）',body,count=1,flags=re.M)
source=f'''- **CLIMB→NAV必要source观测新入口已到件，不再写“没有contact/history reader”：** immutable AINav **f7da873c…/32成员**逐SHA从新端核回，`read_actual_climb_nav_source`只接当前entered/succeeded原session/RegisteredClimbMachine/witness，核原选中option/opaque/body、root/selected model-data-FIFO、原executor session/200Hz时钟及2条实发global18参考；原collision guard/soft-hard限位保留。实际所选箱四脚contact normal各≥12N，不从总足力或高度猜支撑。私有唯一SurfaceSpec不写registry/PUBLIC目录、下一物理步过期，**不是Capture/Arrival/Stow或NAV active owner/constructor准入**；next-source不足不改原CLIMB成功。Data没有import/重fixture/实际调用reader或新native、没有load/replay closed bulk/组件；typed active NAV owner/constructor与外层contact transfer仍缺，不借旧zero。收件`{M}/Data-climb-nav-source32-consumption-not-handoff.json`。
'''
body=body.replace('- **V4方法身份澄清已由source owner决议',source+'- **V4方法身份澄清已由source owner决议',1)
state='已到期'if now>='2026-11-16T04:15:00+08:00'else'仍按原截止生效'
replacement=f'''- **J技术slot已完成并提前让出，数据研究尚未开始：** Data消费04:12新计划22f570c1…及J完整milestone/完成ack，对**7份本机原件metadata和5份远端metadata SHA**逐一核同，未重复权重/model工作。J原件：1,303,947,864bytes/SHA25466aef…匹配官方pin，strict CPU restore2、预训练encoder合成forward2、自有随机未训练head1；**真实录制forward/fit/EVAL/GPU/物理0**。首轮processor形状门失败及一次有限修正保留，不是训练/排序/系统收益。全部job04:02:26结束并主动让出，CPU技术总315.303s<900、峰RSS2,077,630,464bytes<4GiB、盘1,368,431,413bytes<3GiB。原slot04:15绝对截止（{state}），不自动扩窗/授GPU/批cohort；不再等未下载/权重许可加签，不重复下载/restore或合成forward充数。Data仅核元数据/原报告SHA，未hash权重/restore/forward或改他组环境/H/锁/进程；原03:56下载report的restore0仅历史，不再当当前。收件`{J}/Data-J1-completed-CPU-technical-window-consumed.json`。
'''

body=re.sub(r'^- \*\*J低优先级技术窗口仍按原新slot执行：\*\*[^\n]+\n',lambda _:replacement,body,count=1,flags=re.M)
body=body.replace('Data以新30源政策按稳定的完整新程序','Data沿已定共同H政策，以稳定的完整新程序',1)
body=body.replace('- V4最新30源/policy：','- V4新32源必要source reader：`'+str(M)+'/README.md`；已定30源/policy：',1)
body=body.replace('J可按有效低优先级窗口做合法权重hash/CPU技术项，未来独立新用途cohort另登记','J当前下载/CPU技术问题已完成并提前让出，不再重复下载/restore/合成forward；未来独立新用途cohort及实际计算安排另登记',1)
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
  return s[:a]+'## 当前最高执行入口：fixed24已closed，32源必要contact/history reader已收但非handoff，J下载报告已收\n\n'+current.rstrip()+'\n'+s[b:]
 update(B/name,f)
with(M/'Data-only-publication-proof.json').open('x')as f:json.dump(dict(at=now,proof=proof,no_H_worker_or_program_changes=True,all_shared_peer_bytes_preserved=True),f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps(dict(at=now,shared_Data_only_updated=True,driver_snapshot=d,released_public_queries=84),ensure_ascii=False))
