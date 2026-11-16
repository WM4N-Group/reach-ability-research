from pathlib import Path
import json,hashlib,datetime,os,fcntl,tempfile
B=Path('/home/yuanyue/main/work/data-team');M=Path(__file__).resolve().parent;D=B/'consumer-deliveries/AINAV-DATA-E59-CLOSED-STREAM-COLD-PASS-NNSTOP-FIRST-PLACEMENT-LOSS-20261116-v1';sha=lambda b:hashlib.sha256(b).hexdigest();a=json.loads((M/'cold-audit-v1.json').read_bytes());p=json.loads((M/'cold-addendum-publication-proof.json').read_bytes());assert sha((D/'release.json').read_bytes())==p['release_sha256'];assert any(v['sequence']==3137 and v['event']=='V4_legacy_common_H_kernel_attempt'for v in a['original_milestone_events']);now=datetime.datetime.now().astimezone().isoformat()
cold=f'- **完整closed数据流cold已通过，但任务失败标签不变（{now}）：** Data独立逐SHA核515 frozen成员及4711行journal，9719条200Hz命令／原4步FIFO精确通过，PD raw与effort硬clip重现最大误差均0；486机载帧的previous action与时钟、31 raw chunks／486个1280×720原RGB像素SHA及10Hz grid全部通过。CPU/NumPy只读audit13.980s，原scope全文件及H前后SHA相同，未导入Runtime/Actor/MuJoCo/Renderer、未派物理／回放。原NN true、录制完整、cold通过均不等PUSH或任务成功，原PUSH terminal=None、CLIMB0保持。新增不可变补充release **{p["release_sha256"]}**：`{D/"release.json"}`；原最少结果／视频release13082992…不回写。\n'
timeline='- **首次失格已准确前移到NN_STOP，不误归因H／收臂：** 原sequence2500／26.570sim首次placement合格，XY8.8551mm／signed dock gap +3.4623mm；sequence2503／26.590进入NN_STOP_MOVING_PUSH仍合格，**sequence2507／26.630sim首次再次失格，之后未恢复**（XY14.6202mm／gap −13.7201mm）。27.210原NN内部true仍失格；29.390 BRAKE、30.210 UNLOAD_CAPTURE已失格，32.910才进PROTECTED_STOW，H首attempt sequence3137亦在首次失格之后。48.595sim的`lost after stow`是最终复核报错位置，不是首次越界时点；不能倒归因后面的H路径选择，也未据此断言唯一动力学／接触原因。末48.590sim XY37.7186mm／gap −36.5852mm保持。\n'
oldnext='- 最少E结果与完整原片已经先交；Data继续对closed原件只读补200Hz/FIFO/PD及journal cold与分层成本，**尚未宣称完整cold通过**，不以补报告阻原片交付。'
newnext='- 最少E结果与完整原片已先交，完整200Hz/FIFO/PD／journal／RGB cold现已补齐；下一项聚焦原arrival→NN_STOP的实际命令/FIFO/卸载接触定位。AINav新性能helper／E20场景只是后续候选，提速或降高本身不修复此次PUSH失格，不把新源发布当新main准入。'
archive=M/'status-before-E-cold-addendum';archive.mkdir();changes=[]
def transform(raw):
 s=raw.decode();assert '**完整closed数据流cold已通过'not in s
 lines=s.splitlines(keepends=True)
 for i,l in enumerate(lines):
  if l.startswith('更新：'):lines[i]='更新：'+now+'（北京时间；E原件完整cold通过，任务失败不变；首次placement失格定位NN_STOP/26.630sim，早于H）\n';break
 s=''.join(lines);assert '**当前状态**\n'in s;s=s.replace('**当前状态**\n','**当前状态**\n'+cold,1)
 lines=s.splitlines(keepends=True);seen=0
 for i,l in enumerate(lines):
  if l.startswith('- **失败定位的最少原证据：**'):lines[i]=timeline;seen+=1;break
 assert seen==1;s=''.join(lines);assert oldnext in s;s=s.replace(oldnext,newnext,1)
 if '## 当前最高执行入口：E真实失败与完整direct-live原片已交，补closed原件cold'in s:s=s.replace('## 当前最高执行入口：E真实失败与完整direct-live原片已交，补closed原件cold','## 当前最高执行入口：E失败原片与完整cold已交，定位NN_STOP首次失格',1)
 return s.encode()
def cas(path,fn,peer=False):
 raw=path.read_bytes();after=fn(raw);assert raw!=after
 with(archive/(path.name+'.before')).open('xb')as f:f.write(raw)
 dfd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
 try:
  fcntl.flock(dfd,fcntl.LOCK_EX)
  with path.open('rb')as f:
   fcntl.flock(f,fcntl.LOCK_EX);st=os.fstat(f.fileno());assert f.read()==raw and path.stat().st_ino==st.st_ino;fd,tmp=tempfile.mkstemp(prefix='.Data-E-cold-',dir=path.parent)
   try:
    os.fchmod(fd,st.st_mode&0o7777)
    with os.fdopen(fd,'wb')as out:out.write(after);out.flush();os.fsync(out.fileno())
    assert path.read_bytes()==raw;os.replace(tmp,path);os.fsync(dfd)
   finally:
    if os.path.exists(tmp):os.unlink(tmp)
 finally:os.close(dfd)
 changes.append(dict(path=str(path),before_sha256=sha(raw),after_sha256=sha(after),directory_file_flock_SHA_CAS_atomic_replace=True,mode_preserved=True,peer_bytes_preserved=peer))
def shared(raw):
 a=raw.index('## Data组\n'.encode());b=raw.index(b'\n## ',a+1);out=raw[:a]+transform(raw[a:b])+raw[b:];assert out[:a]==raw[:a]and out.endswith(raw[b:]);return out
cas(Path('/home/yuanyue/main/汇总/各小组进展汇总.md'),shared,True)
for name in ['STATUS.md','AGENTS.md']:cas(B/name,transform)
(M/'E-cold-addendum-Data-only-update-proof.json').write_text(json.dumps(dict(at=now,release_sha256=p['release_sha256'],changes=changes,no_new_physics_no_old_root_retry=True),ensure_ascii=False,indent=2)+'\n');print(json.dumps(dict(at=now,updated=[v['path']for v in changes],release=p['release_sha256']),ensure_ascii=False))
