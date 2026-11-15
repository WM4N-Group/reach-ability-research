"""Finish entry-only publication after STATUS layout mismatch, no physical retry."""
from pathlib import Path
import os,json,hashlib,datetime,fcntl,stat,tempfile,subprocess,base64,shlex
B=Path('/home/yuanyue/main/work/data-team');M=Path(__file__).resolve().parent;N=M.name;S=Path('/home/yuanyue/main/汇总/各小组进展汇总.md');sha=lambda b:hashlib.sha256(b).hexdigest();now=datetime.datetime.now().astimezone().isoformat();shared=S.read_bytes();old_shared=(M/'各小组进展汇总.md.before-component-outcome').read_bytes();a=shared.index('## Data组'.encode());assert shared[:a]==old_shared[:old_shared.index('## Data组'.encode())];body=shared[a:].decode().split('\n',1)[1];D=B/'consumer-deliveries/AINAV-DATA-T-COMPLEX-01-NATIVE-COMPONENT-FAIL-20261115-v1';assert json.loads((D/'release.json').read_bytes())['closed_no_retry'];entry='## 当前最高执行入口：T-COMPLEX组件真实编译后缺onboard camera，已closed无重试；A/B main0/videos0\n'+body+'\n';proof=[dict(path=str(S),before=sha(old_shared),after=sha(shared),all_non_Data_bytes_preserved=True)];remote=[]
for name in ['STATUS.md','AGENTS.md','README.md']:
 p=B/name;old=p.read_bytes();text=old.decode()
 if name=='STATUS.md':
  x='<!-- NEXT_QUESTION_SAMPLING_CURRENT_BEGIN -->';y='<!-- NEXT_QUESTION_SAMPLING_CURRENT_END -->';i=text.index(x)+len(x);j=text.index(y,i);new=(text[:i]+'\n'+body+'\n'+text[j:]).encode()
  s=new.decode();i=s.index('更新：');j=s.index('\n',i);new=(s[:i]+'更新：'+now+'（北京时间；复杂组件预检已closed，精确camera源故障见第1节；不恢复旧scope/不自动fit）。'+s[j:]).encode()
 else:
  i=text.index('## 当前最高执行入口');j=text.index('\n## 最新用户服务器与代码决定',i);new=(text[:i]+entry+text[j+1:]).encode()
 d=os.open(p.parent,os.O_RDONLY|os.O_DIRECTORY)
 try:
  fcntl.flock(d,fcntl.LOCK_EX)
  with p.open('rb')as f:
   fcntl.flock(f,fcntl.LOCK_EX);st=os.fstat(f.fileno());assert f.read()==old and(p.stat().st_dev,p.stat().st_ino)==(st.st_dev,st.st_ino);(M/(name+'.before-component-outcome')).write_bytes(old);fd,t=tempfile.mkstemp(prefix='.'+name+'.component-',dir=p.parent)
   try:
    with os.fdopen(fd,'wb')as out:out.write(new);out.flush();os.fchmod(out.fileno(),stat.S_IMODE(st.st_mode));os.fsync(out.fileno())
    assert p.read_bytes()==old;os.replace(t,p);os.fsync(d)
   finally:
    if os.path.exists(t):os.unlink(t)
 finally:os.close(d)
 proof.append(dict(path=str(p),before=sha(old),after=sha(new)));remote.append(dict(name=name,expected=sha(old),data=base64.b64encode(new).decode()))
code=r'''
from pathlib import Path
import os,sys,json,base64,hashlib,fcntl,stat,tempfile
B=Path('/mnt/yuanyue/data-team/deployments/46308-20261114/workspace');rows=json.load(sys.stdin);proof=[]
for row in rows:
 p=B/row['name'];assert row['name']in('STATUS.md','AGENTS.md','README.md');new=base64.b64decode(row['data']);d=os.open(p.parent,os.O_RDONLY|os.O_DIRECTORY)
 try:
  fcntl.flock(d,fcntl.LOCK_EX)
  with p.open('rb')as f:
   fcntl.flock(f,fcntl.LOCK_EX);old=f.read();st=os.fstat(f.fileno());assert hashlib.sha256(old).hexdigest()==row['expected'];assert(p.stat().st_dev,p.stat().st_ino)==(st.st_dev,st.st_ino);fd,t=tempfile.mkstemp(prefix='.'+p.name+'.component-',dir=p.parent)
   try:
    with os.fdopen(fd,'wb')as out:out.write(new);out.flush();os.fchmod(out.fileno(),stat.S_IMODE(st.st_mode));os.fsync(out.fileno())
    assert p.read_bytes()==old;os.replace(t,p);os.fsync(d)
   finally:
    if os.path.exists(t):os.unlink(t)
 finally:os.close(d)
 proof.append(dict(name=p.name,sha256=hashlib.sha256(new).hexdigest()))
print(json.dumps(proof))
'''
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],input=json.dumps(remote),text=True,capture_output=True,timeout=90)
(M/'entry-mirror.stdout').write_text(r.stdout);(M/'entry-mirror.stderr').write_text(r.stderr);(M/'publication-local-CAS-peer-proof.json').write_text(json.dumps(dict(at=now,proof=proof,entry_layout_first_failure_preserved=True,remote_exit=r.returncode,H_not_written=True),indent=2)+'\n');assert r.returncode==0,r.stderr;print('Local entries and remote mirrors published; all peer bytes unchanged, no physical dispatch')
