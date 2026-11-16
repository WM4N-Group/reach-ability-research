from pathlib import Path
import json,hashlib,datetime,os,fcntl,tempfile
B=Path('/home/yuanyue/main/work/data-team');M=Path(__file__).resolve().parent;D=B/'consumer-deliveries/AINAV-DATA-OLD46174-LEFT-RECOVERED-ORIGINAL-METADATA-PASS-NOT-NEW-RUN-20261116-v1';p=json.loads((M/'recovered-metadata-publication-proof.json').read_bytes());sha=lambda b:hashlib.sha256(b).hexdigest();assert sha((D/'release.json').read_bytes())==p['release_sha256'];now=datetime.datetime.now().astimezone().isoformat();assert(M/'current-H-recovery-note-CAS-proof.json').exists()
bullet=f'''- **历史缺项恢复只读闭合，不是新E或新样本（{now}）：** 按14:08计划e56951c2授权，为失联旧left的具体result/ledger缺口仅一次只读访问46174，取约101KB原元数据，无旧计算／旧H／锁／进程／账本写入。旧scope `data-native-prefix-left-PUSH-CLIMB-20261114-v1`原program5472a8bb…/auth c9787048…三方一致，原result **9a879643…**与最终账本main行report SHA一致：**原报告REQUESTED_API0_PASS，所请求NAV→PUSH→20cm CLIMB三语义成功（含准备共5原option完成）**，24217任务步／121.085sim、1211机载帧、close_errors=[]；本回合未重新冷审raw/journal，不冒新V4/E20/whole-task成功。zero/main行closed=true，但旧账本顶层stopped=false、旧H仍active/CAS_DISPATCHED_MAIN且SHA仍e3baa660…，原样保留、不作为当前权威/lease，也不续派旧right。失联时UNKNOWN原件a312c3e5…不改，另附恢复证据，旧zero1/main1不增、新端配对/祖先血缘/用途/库存不改。
- **旧费用从原件补明，口径差异保留：** main原result wall909.799338533s，最终main ledger909.890570222s，zero42.510913883s；原账本zero+main合计**952.401484105wall／134.095sim（含两aux13.010sim）**。main最终高水位177089038bytes，result记176989422bytes，差99616bytes等于原result大小；不猜全部wall差原因、不填货币成本或新方法成功cost。正式恢复release **{p['release_sha256']}**：`{D/'release.json'}`。当前46308 H仅CAS追加恢复元数据索引，旧UNKNOWN字段/全部旧scope字段不变、镜像一致；**计算仍仅46308，当前E20静态geom lookup硬阻塞未解除**，无新具体缺项不再轮询旧端。
'''
changes=[]
def transform(raw):
 s=raw.decode();assert '**历史缺项恢复只读闭合'not in s;assert '**当前状态**\n'in s;s=s.replace('**当前状态**\n','**当前状态**\n'+bullet,1);s=s.replace('旧46174仅按具体缺失资料只读，本次未连。','旧46174仅按具体缺失资料只读，18:10已按此范围核回旧left元数据（见本节恢复证据）；旧H非当前权威。',1);lines=s.splitlines(keepends=True)
 for i,l in enumerate(lines):
  if l.startswith('更新：'):lines[i]='更新：'+now+'（北京时间；按需只读恢复旧46174 left原结果/账本；当前E20静态lookup阻塞不变，无新物理）\n';break
 return ''.join(lines).encode()
def cas(path,fn,peer=False):
 old=path.read_bytes();new=fn(old);dfd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
 try:
  fcntl.flock(dfd,fcntl.LOCK_EX)
  with path.open('rb')as f:
   fcntl.flock(f,fcntl.LOCK_EX);st=os.fstat(f.fileno());assert f.read()==old and path.stat().st_ino==st.st_ino;fd,tmp=tempfile.mkstemp(prefix='.Data-old-recovery-',dir=path.parent)
   try:
    os.fchmod(fd,st.st_mode&0o7777)
    with os.fdopen(fd,'wb')as out:out.write(new);out.flush();os.fsync(out.fileno())
    assert path.read_bytes()==old;os.replace(tmp,path);os.fsync(dfd)
   finally:
    if os.path.exists(tmp):os.unlink(tmp)
 finally:os.close(dfd)
 changes.append(dict(path=str(path),before_sha256=sha(old),after_sha256=sha(new),directory_file_flock_SHA_CAS_atomic_replace=True,mode_preserved=True,peer_bytes_preserved=peer))
def shared(raw):
 a=raw.index('## Data组\n'.encode());b=raw.index(b'\n## ',a+1);out=raw[:a]+transform(raw[a:b])+raw[b:];assert out[:a]==raw[:a]and out.endswith(raw[b:]);return out
cas(Path('/home/yuanyue/main/汇总/各小组进展汇总.md'),shared,True)
for name in ['STATUS.md','AGENTS.md']:cas(B/name,transform)
(M/'recovery-Data-only-status-proof.json').write_text(json.dumps(dict(at=now,release_sha256=p['release_sha256'],changes=changes,no_new_physics_no_old_scope_changes=True),ensure_ascii=False,indent=2)+'\n');print(json.dumps(dict(updated=[v['path']for v in changes],release=p['release_sha256']),ensure_ascii=False))
