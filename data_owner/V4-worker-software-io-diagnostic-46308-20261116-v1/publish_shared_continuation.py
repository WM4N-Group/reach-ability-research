"""Complete only the pending shared Data CAS after recorded delimiter TypeError.
Do not rerun the first publisher or previous physical/controller operations.
"""
from pathlib import Path
import os,json,hashlib,fcntl,tempfile
M=Path(__file__).resolve().parent;B=M.parent.parent
sha=lambda b:hashlib.sha256(b).hexdigest()
a=json.loads((M/'Data-software-io-assessment.json').read_text());now=a['at'];D=B/'consumer-deliveries/AINAV-DATA-V4-WORKER-SOFTWARE-IO-DIAGNOSIS-20261116-v1'
first=[]
for name in ('STATUS.md','README.md','AGENTS.md'):
 raw=(B/name).read_bytes();text=raw.decode();paragraph=next(x for x in text.splitlines(keepends=True) if x.startswith('- **Data实际worker的软件/I/O切片已测，未冒已修复：**'))
 assert text.count(paragraph)==1 and '更新：'+now in text
 first.append(dict(path=str(B/name),after_sha256=sha(raw),postread_verified=True,original_prewrite_SHA_not_persisted_after_later_shared_delimiter_error=True))
path=Path('/home/yuanyue/main/汇总/各小组进展汇总.md');before=path.read_bytes();pin=sha(before);i=before.index('## Data组\n'.encode());j=before.index(b'\n## ',i+1);prefix,suffix=before[:i],before[j:];chunk=before[i:j].decode()
assert paragraph not in chunk and '先对壁钟/metadata-I/O瓶颈做有界定位并保原安全语义，' in chunk
chunk=chunk.replace('\n**下一步**\n','\n'+paragraph+'\n**下一步**\n',1).replace('先对壁钟/metadata-I/O瓶颈做有界定位并保原安全语义，','Data文件访问分段已完成并与AINav热点观测交叉界定；接续需具体保语义的源码/运行条件改进，而非再重复同一probe。',1).replace('更新：2026-11-16T06:38:49.995685+08:00','更新：'+now,1)
out=prefix+chunk.encode()+suffix;dfd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY);ffd=None
try:
 fcntl.flock(dfd,fcntl.LOCK_EX);ffd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW);fcntl.flock(ffd,fcntl.LOCK_EX);assert sha(path.read_bytes())==pin,'Shared CAS conflict; preserve peer changes'
 mode=os.fstat(ffd).st_mode&0o7777;fd,tmp=tempfile.mkstemp(prefix='.'+path.name+'.Data-cas-',dir=path.parent)
 try:
  os.fchmod(fd,mode)
  with os.fdopen(fd,'wb')as f:f.write(out);f.flush();os.fsync(f.fileno())
  os.replace(tmp,path);os.fsync(dfd)
 finally:
  if os.path.exists(tmp):os.unlink(tmp)
 assert path.read_bytes()==out and out[:i]==prefix and out[-len(suffix):]==suffix and path.stat().st_mode&0o7777==mode
finally:
 if ffd is not None:os.close(ffd)
 os.close(dfd)
proof=dict(at=now,release=str(D/'release.json'),release_sha256=sha((D/'release.json').read_bytes()),first_metadata_publisher_partial_error_preserved='publication-first-error.txt',first_three_after_states=first,shared=dict(path=str(path),before_sha256=pin,after_sha256=sha(out),directory_file_flock_SHA_CAS_atomic_preserve_mode=True,mode=mode,peer_bytes_preserved=True,only_Data_section=True),no_H_or_physical_scope_mutation=True)
with (M/'publication-proof.json').open('x')as f:json.dump(proof,f,indent=2,ensure_ascii=False);f.write('\n')
print(json.dumps(proof,ensure_ascii=False,indent=2))
