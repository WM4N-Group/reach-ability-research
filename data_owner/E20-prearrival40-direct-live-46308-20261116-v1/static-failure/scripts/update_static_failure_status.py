from pathlib import Path
import json,hashlib,os,fcntl,tempfile,datetime
B=Path('/home/yuanyue/main/work/data-team');M=Path(__file__).resolve().parent;D=B/'consumer-deliveries/AINAV-DATA-E20-PREARRIVAL40-STATIC-ASSET-GEOM-LOOKUP-FAILED-NO-ZERO-MAIN-20261116-v1';sha=lambda b:hashlib.sha256(b).hexdigest();p=json.loads((M/'static-failure-publication-proof.json').read_bytes());assert p['release_sha256']==sha((D/'release.json').read_bytes());now=datetime.datetime.now().astimezone().isoformat()
bullet=f'''- **新E20／40mm候选已真实接入，但阻在静态资产构造，未进zero/main（{now}）：** 已核用户环境参数适配授权及AINav prereg source **5a1a92b1…**（固定规则43998a23…、新C20cm目标/scene08a260a4…、单点40mm提前进入同原brake＋两完整I/O helper，非旧.60m成功/未见对照）。Data新scope `data-46308-E20-prearrival40-direct-live-20261116-v1`在485成员静态子程序freeze **c3e14456…**及fresh GPU0原锁/容量/权威CAS后，静态构造唯一1次于`complex_e_skill20_arrival_v3/v4_native_asset.py:97`的`sim.spec.geom(...).rgba`报 **NoneType has no attribute rgba**。父base源码虽有带名add_geom，wrapper按名取回None；具体spec引用/lookup接缝需AINav修，不猜唯一缓存原因。新复杂场景`spec.compile()`尚未到，**新MJB0、task Runtime0、任务步0、Actor forward0、own-zero0/main0**；40mm动态效果未测试，不冒E20 main/PUSH/CLIMB失败或新截图/视频。
- **新静态失败已安全关闭／费用保留：** 原构造10.479544644wall、峰值RSS1336918016bytes、aux0、close_errors=[]；GPU own/peak=None且CUDA_UNINITIALIZED_NO_PID_ROW，保None不伪0。H为CLOSED_STATIC_ASSET_FAILED_NO_ZERO_MAIN、PID243226结束、GPU0两原canonical inode释放、H镜像一致、485冻源/SDK关闭后全SHA同。原失败spec丢弃不续编，main完整freeze未生成，旧E59/main/费用/原片/cold不变。正式失败release **{p['release_sha256']}**：`{D/'release.json'}`，本地／远端逐SHA同；本地未冻结路径/生成器错误另有记录，未动旧源或已关闭scope。AINav17:35已发布40836ff0…窗口精确消费回执（25行/5landmark/字段SHA/FIFO），但尚不声称其已消费本新静态失败。
'''
nextline='- E59原片／完整cold／25条实际命令证据均已交，当前唯一执行硬阻塞是AINav新E20资产构造的spec/新增geom lookup。需其修准确对象引用／SDK调用接缝并给明确新source/技术问题版本；Data不跳染色、塞None dummy、借旧.60 MJB或在本closed scope重编/重跑，不放宽原安全成功门，不扫margin或换seed。修复代码发布不自动等native准入，之后再按独立有限程序/自身zero/lease推进；不等WM/VLM/全部方法，也不重复经济审批。\n'
def transform(raw):
 s=raw.decode();assert '新E20／40mm候选已真实接入'not in s;assert '**当前状态**\n'in s;s=s.replace('**当前状态**\n','**当前状态**\n'+bullet,1);lines=s.splitlines(keepends=True)
 for i,l in enumerate(lines):
  if l.startswith('更新：'):lines[i]='更新：'+now+'（北京时间；新E20/40mm静态构造lookup失败已closed，zero0/main0；原E59失败原片/cold保持）\n';break
 for i,l in enumerate(lines):
  if l.startswith('- 最少E结果与完整原片已先交，'):lines[i]=nextline;break
 s=''.join(lines);s=s.replace('## 当前最高执行入口：E失败原片与完整cold已交，定位NN_STOP首次失格','## 当前最高执行入口：E20新静态资产lookup失败closed，原E59证据保留',1);return s.encode()
changes=[]
def cas(path,fn,peer=False):
 old=path.read_bytes();new=fn(old);dfd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
 try:
  fcntl.flock(dfd,fcntl.LOCK_EX)
  with path.open('rb')as f:
   fcntl.flock(f,fcntl.LOCK_EX);st=os.fstat(f.fileno());assert f.read()==old and path.stat().st_ino==st.st_ino;fd,tmp=tempfile.mkstemp(prefix='.Data-E20-static-',dir=path.parent)
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
(M/'static-failure-Data-only-status-proof.json').write_text(json.dumps(dict(at=now,release_sha256=p['release_sha256'],changes=changes,no_old_scope_resume_or_new_main=True),ensure_ascii=False,indent=2)+'\n');print(json.dumps(dict(updated=[v['path']for v in changes],release=p['release_sha256']),ensure_ascii=False))
