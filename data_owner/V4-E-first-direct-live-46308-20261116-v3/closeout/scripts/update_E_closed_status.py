from pathlib import Path
import json,hashlib,datetime,os,fcntl,tempfile
B=Path('/home/yuanyue/main/work/data-team');M=B/'manifests/V4-E-first-direct-live-46308-20261116-v3';D=B/'consumer-deliveries/AINAV-DATA-E-FIRST-FULL-V4-ATTEMPT-STOW-PLACEMENT-REJECTED-DIRECT-LIVE-20261116-v1';now=datetime.datetime.now().astimezone().isoformat();sha=lambda b:hashlib.sha256(b).hexdigest();proof=json.loads((M/'minimum-result-video-release-proof.json').read_bytes());assert sha((D/'release.json').read_bytes())==proof['release_sha256'];archive=M/'status-before-E-minimum-closeout';archive.mkdir()
body=f'''更新：{now}（北京时间；E首条完整V4目标真实尝试已失败收束，完整direct-live 1×原片及最少结果已正式交付，不等待完整cold）

**当前状态**
- **E结果已取得：完整任务未成功，不是资源截断。** scope `data-46308-V4-E-first-direct-live-20261116-v3`，source59 `3ab9383a…`／未改RuleBaseline43998a23…／program `f7dd66c58d98…`，own-zero1/main1均已closed。准备NAV于3018tick／15.090sim原生succeeded；首cuboid_a PUSH于3019tick／15.095sim真实started。9719tick／**48.595sim**在原`placement_handoff.py:207`保护收臂后的placement复核报`Original immutable public/native placement lost after stow`并原硬停。**PUSH无原生succeeded/failed终态回执，不能补native失败标签；后续箱子／CLIMB／高台未到达。** E规则decisions1、placed=[]、semantic_successes0，不是五组对照／高台成功，也不是旧组件改名。
- **失败定位的最少原证据：** 最后48.590sim样本为STOW_VERIFY，原PushSettled内部true且contact=true，但placement_geometry_verified=false；公开XY误差37.7186mm、signed dock gap −36.5852mm。内部NN／收臂完成不等完整PUSH placement通过；只报告此原gate，不凭异常归因Actor／新优化或宣称方法优劣。共有legacy H本次attempt1/completed1/changed1成本保留，**VLM0／WM0／fit0／新后继选择0**，不是所有旧算法0。
- **完整原片已交付：1280×720、10Hz、486帧、1×约48.6s。** 从task0直接live RGB到失败的完整事前采样grid，31 raw chunks逐SHA核、原master留远端，ffprobe实际解码486帧通过；只作原RGB编码，无状态回放／重渲染／插帧／resize／挑成功片段。原任务终态48.595sim以event/result为准，最后grid画面9700tick／48.5sim，不补造9719tick。固定广角覆盖狗／三箱／高台，狗臂相对很小，不假称近景细节。本机仅237186bytes原片小副本：`{M/'E-direct-live-1x.mp4'}`；video SHA **172e2878f349…**。正式最少交付release **{proof['release_sha256']}**：`{D/'release.json'}`；本地/远端包逐SHA一致，README有完整远端路径与时钟。
- **成本与安全收束保真：** main **9719命令／48.595task sim＋6.505aux sim／9382.502520127wall**，486机载帧，usage_known=true、resource_censored=false、close_errors=[]。own-zero另19.590225650wall／task0＋6.505auxsim；v3 zero+main总9402.092745777wall／13.010auxsim。原episode.censored=true是调用方异常截断记录，不能改成watchdog或native failed；main ledger输出68359373bytes为原账本值，不把费用未知写0、不当货币总费。Data v1 prepare授权字段错（zero0/main0）及v2 task0元数据错（17.490wall／aux6.505sim／main0）均closed历史保留，不重算成E main。
- **fresh权威及边界：** H为CLOSED_E_MAIN、PID192156已结束、镜像一致，GPU0两canonical原inode3428729629/30已释放；GPU1锁在检查时被持有，未动他组锁／进程，不谎称四锁都空。Data owned26331265536bytes／40GiB、provider quota未知。当前计划e56951c2…已消费；compute仍46308，旧46174仅按具体缺失资料只读，本次未连。E先行DEV暴露保留；不得据此调后续A—D后冒未见公平比较，不热改／重开本scope。
- **fixed24与此前af09已闭合，不自动重跑/refit：** 固定24为10链PASS／14非PASS，84 public queries、481685主世界命令，192×128原raw非HD；正式release5367a3a1…不改用途。此前af09/v2于12:11 closed，NAV成功但PUSH构造时Runtime.staircase ABI异常，正式release0a41bb54…保留；与本次E已原生started后placement失格分开，不洗掉失败或混算同环境方法收益。

**下一步**
- 最少E结果与完整原片已经先交；Data继续对closed原件只读补200Hz/FIFO/PD及journal cold与分层成本，**尚未宣称完整cold通过**，不以补报告阻原片交付。
- AINav据准确原gate与原placement合同定位收臂后placement未保住的原因；Data不改阈值、不替Reach写优化器、不把NN true补成任务成功。若需共同修复／新实验，先登记问题、版本、用途、有限次数与资源，不换ID盲重试，不恢复closed world。当前没有新main派发。
- 五组完整任务及有效方法比较尚未建立；旧critic/bulk用途不自动转V-JEPA，旧WM/Actor训练不开放。自动化／身份／他组代码进程锁均不变。

**详细入口**
- E正式最少结果／原始result/ledger／原片SHA／边界：`{D/'release.json'}`、`{D/'README_CN.md'}`；闭合只读证据与源日志：`{M/'closeout-readonly-export.json'}`；源59完整冻结及零/main/encode/close原件均在该manifest目录。
- 固定24最终原件：`{B/'consumer-deliveries/AINAV-DATA-BULK24-FIXED-COLLECTION-CLOSEOUT-NO-REFIT-20261116-v1/release.json'}`；af09正式失败：`{B/'consumer-deliveries/AINAV-DATA-PALETTE-V2-FRESH-ASSOCIATION-PASS-PUSH-RUNTIME-ABI-FAILED-20261116-v1/release.json'}`。此前Data当前段全文按原bytes封存于`{archive}`，不丢旧scope／成本／用途历史。
'''
changes=[]
def cas(p,fn,peer=False):
 raw=p.read_bytes();after=fn(raw);assert raw!=after
 with(archive/(p.name+'.before')).open('xb')as f:f.write(raw)
 dfd=os.open(p.parent,os.O_RDONLY|os.O_DIRECTORY)
 try:
  fcntl.flock(dfd,fcntl.LOCK_EX)
  with p.open('rb')as f:
   fcntl.flock(f,fcntl.LOCK_EX);st=os.fstat(f.fileno());assert f.read()==raw and p.stat().st_ino==st.st_ino;fd,tmp=tempfile.mkstemp(prefix='.Data-E-closed-',dir=p.parent)
   try:
    os.fchmod(fd,st.st_mode&0o7777)
    with os.fdopen(fd,'wb')as out:out.write(after);out.flush();os.fsync(out.fileno())
    assert p.read_bytes()==raw;os.replace(tmp,p);os.fsync(dfd)
   finally:
    if os.path.exists(tmp):os.unlink(tmp)
 finally:os.close(dfd)
 changes.append(dict(path=str(p),before_sha256=sha(raw),after_sha256=sha(after),directory_and_file_flock_SHA_CAS_atomic_replace=True,mode_preserved=True,peer_bytes_preserved=peer))
def shared(raw):
 a=raw.index('## Data组\n'.encode());b=raw.index(b'\n## ',a+1);out=raw[:a]+('## Data组\n\n'+body.rstrip()+'\n').encode()+raw[b:];assert out[:a]==raw[:a]and out.endswith(raw[b:]);return out
cas(Path('/home/yuanyue/main/汇总/各小组进展汇总.md'),shared,True)
def status(raw):
 a=raw.index(b'<!-- NEXT_QUESTION_SAMPLING_CURRENT_BEGIN -->');b=raw.index(b'<!-- NEXT_QUESTION_SAMPLING_CURRENT_END -->',a);s=(raw[:a]+('<!-- NEXT_QUESTION_SAMPLING_CURRENT_BEGIN -->\n'+body).encode()+raw[b:]).decode();lines=s.splitlines(keepends=True)
 for i,l in enumerate(lines):
  if l.startswith('更新：'):lines[i]='更新：'+now+'（北京时间；E真实失败收束，完整direct-live原片与最少结果已正式交付）\n';break
 return ''.join(lines).encode()
cas(B/'STATUS.md',status)
def agents(raw):
 a=raw.index('## 当前最高执行入口'.encode());b=raw.index('## 最新用户服务器'.encode(),a);return raw[:a]+('## 当前最高执行入口：E真实失败与完整direct-live原片已交，补closed原件cold\n\n'+body+'\n').encode()+raw[b:]
cas(B/'AGENTS.md',agents)
(M/'E-minimum-closeout-Data-only-publication-proof.json').write_text(json.dumps(dict(at=now,release_sha256=proof['release_sha256'],changes=changes,no_new_physics_or_runtime_mutation=True),ensure_ascii=False,indent=2)+'\n');print(json.dumps(dict(at=now,updated=[v['path']for v in changes],release=proof['release_sha256']),ensure_ascii=False))
