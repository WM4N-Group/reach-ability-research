from pathlib import Path
import time,json,subprocess,sys
M=Path(__file__).resolve().parent
with(M/'post-main-once.json').open('x')as f:json.dump(dict(no_main_or_physics_restart=True,follow_existing_main_only=True),f)
limit=time.monotonic()+36480
while not(M/'main-proof.json').exists():
 if time.monotonic()>limit:raise RuntimeError('Existing E main did not produce metadata proof by finite supervisor deadline; no retry')
 time.sleep(15)
for action in ['encode','close']:
 r=subprocess.run([sys.executable,str(M/'phase.py'),action],cwd=M.parents[1],capture_output=True,text=True,timeout=360)
 with(M/('post-'+action+'.stdout')).open('x')as f:f.write(r.stdout)
 with(M/('post-'+action+'.stderr')).open('x')as f:f.write(r.stderr)
 if r.returncode:raise RuntimeError('Post-main '+action+' failed; no native retry: '+r.stderr)
