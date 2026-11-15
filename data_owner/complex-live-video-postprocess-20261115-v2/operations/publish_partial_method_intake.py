from pathlib import Path
import os,json,hashlib,fcntl,stat,tempfile,base64,subprocess,shlex,ast,datetime
B=Path('/home/yuanyue/main/work/data-team');M=Path(__file__).resolve().parent;P=B/'manifests/g2-full2-46308-20261115-v1';S=Path('/home/yuanyue/main/汇总/各小组进展汇总.md');sha=lambda b:hashlib.sha256(b).hexdigest();remote=[];proof=[]
addition=f'''\n- **复杂方法的已到部分已实接：** Reach共享几何/greedy与multistep核心源码3a5eb184…已SHA核合，两臂共用深4/256transitions/.25s及同nominal代价/tie，不依赖critic；不是算法核心缺失。但真实AINav复杂scene/公共arc/共同终点/合法native映射与source-bound caller仍未交，core的4个抽象检查不冒场景资格/实际A-B/原片。Data接收档案`{M}/REACH_METHOD_CORE_RECEIVED_REAL_SCENE_ADAPTER_PENDING.json`，不代写答案图或selector；复杂物理/原片仍0。\n'''
def update(p,label,shared=False):
 old=p.read_bytes();s=old.decode()
 if shared:
  a=s.index('## Data组');i=s.index('\n**入口**',a);assert '复杂方法的已到部分已实接'not in s[a:];new=(s[:i]+addition+s[i:]).encode();assert new[:len(s[:a].encode())]==s[:a].encode()
 else:
  needle='可执行复杂scene/同域A-B方法尚未交';replacement='Reach共享几何/两策略核心3a5eb184…已SHA核合，但真实复杂scene/公共arc/共同终点和source-bound caller尚未交'
  if needle in s:new=s.replace(needle,replacement,1).encode()
  elif '\n**入口**'in s:
   i=s.index('\n**入口**');new=(s[:i]+addition+s[i:]).encode()
  else:return
 d=os.open(p.parent,os.O_RDONLY|os.O_DIRECTORY)
 try:
  fcntl.flock(d,fcntl.LOCK_EX)
  with p.open('rb')as f:
   fcntl.flock(f,fcntl.LOCK_EX);v=f.read();st=os.fstat(f.fileno());assert v==old and(p.stat().st_dev,p.stat().st_ino)==(st.st_dev,st.st_ino);(M/(label+'-before-partial-method-intake.md')).write_bytes(old);fd,t=tempfile.mkstemp(prefix='.'+p.name+'.core-intake-',dir=p.parent)
   try:
    with os.fdopen(fd,'wb')as o:o.write(new);o.flush();os.fchmod(o.fileno(),stat.S_IMODE(st.st_mode));os.fsync(o.fileno())
    assert p.read_bytes()==old;os.replace(t,p);os.fsync(d)
   finally:
    if os.path.exists(t):os.unlink(t)
 finally:os.close(d)
 proof.append(dict(path=str(p),before=sha(old),after=sha(new),peer_unchanged=shared))
 if p.parent==B:remote.append(dict(name=p.name,expected_sha256=sha(old),bytes=base64.b64encode(new).decode()))
update(S,'shared-Data',True)
for n in('AGENTS.md','README.md','STATUS.md'):update(B/n,n[:-3])
update(B/'manifests/new-critic-cohort-46308-20261115-v1/README.md','TRAIN-detailed')
tree=ast.parse((P/'publish_current_progress.py').read_bytes());code=next(ast.literal_eval(n.value)for n in tree.body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='code'for t in n.targets));code=code.replace('g2-full2-46308-20261115-v1','new-critic-cohort-46308-20261115-v1').replace('before-full2-live','before-partial-complex-core-intake');r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],input=json.dumps(remote),capture_output=True,text=True,timeout=90);(M/'partial-core-entry-mirror.stderr').write_text(r.stderr);(M/'partial-method-intake-CAS-peer-proof.json').write_text(json.dumps(dict(at=datetime.datetime.now().astimezone().isoformat(),local=proof,remote_exit=r.returncode,peer_text_preserved=True,H_not_written=True),indent=2)+'\n');assert r.returncode==0,r.stderr;print('Actual core intake acknowledged, unique real-scene adapter gap explicit; peer text untouched')
