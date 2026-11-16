"""Follow exactly the pre-dispatched current main; never another dispatch/zero/world."""
from pathlib import Path
import os,sys,json,subprocess,time
M=Path(__file__).resolve().parent
assert (M/'dispatch-main-proof.json').exists()and(M/'qualify-zero-1-proof.json').exists()
with(M/'main-supervisor-once.json').open('x')as f:json.dump(dict(owner=os.environ['CODEX_THREAD_ID'],actions=['main','encode','close'],no_dispatch_or_retry=True),f)
for action in ['main','encode','close']:
 cap=36200 if action=='main'else 440
 p=subprocess.run([sys.executable,str(M/'phase.py'),action],cwd=M.parents[1],capture_output=True,text=True,timeout=cap)
 with(M/('supervised-'+action+'.stdout')).open('x')as f:f.write(p.stdout)
 with(M/('supervised-'+action+'.stderr')).open('x')as f:f.write(p.stderr)
 if p.returncode:raise RuntimeError('Metadata lifecycle '+action+' failed; no physics retry: '+p.stderr)
 if action=='main':
  x=json.loads((M/'main-proof.json').read_bytes());assert x.get('result')is not None,'Main worker has no original result; inspect only, never rerun'
