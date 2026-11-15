from pathlib import Path
import os,hashlib,json,fcntl,stat,tempfile
B=Path('/home/yuanyue/main/work/data-team');H=B/'registry/handoff_46308_current_status_20261115.json'
def mirror(raw,expected):
 sha=lambda b:hashlib.sha256(b).hexdigest();d=os.open(H.parent,os.O_RDONLY|os.O_DIRECTORY)
 try:
  fcntl.flock(d,fcntl.LOCK_EX|fcntl.LOCK_NB)
  with H.open('rb') as f:
   fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);old=f.read();st=os.fstat(f.fileno());assert sha(old)==expected and (H.stat().st_dev,H.stat().st_ino)==(st.st_dev,st.st_ino)
   fd,tmp=tempfile.mkstemp(prefix='.handoff_stageB_',dir=H.parent)
   try:
    with os.fdopen(fd,'wb') as out:out.write(raw);out.flush();os.fchmod(out.fileno(),stat.S_IMODE(st.st_mode));os.fsync(out.fileno())
    assert H.read_bytes()==old;os.replace(tmp,H);os.fsync(d)
   finally:
    if os.path.exists(tmp):os.unlink(tmp)
 finally:os.close(d)
if __name__=='__main__':
 M=Path(__file__).parent;r=json.loads((M/'freeze-CAS-receipt.json').read_bytes());mirror((M/'H-after-cohort-freeze.json').read_bytes(),r['before_H_sha256']);print('local H mirror CAS synchronized')
