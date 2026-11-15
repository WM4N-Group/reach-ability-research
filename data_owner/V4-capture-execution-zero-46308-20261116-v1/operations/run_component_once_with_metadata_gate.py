"""New component once; hold ONLY own local driver at a read-only boundary.
Remote GPU1 native world never receives a signal or pause. A finite watchdog
resumes the same local driver if this controller is interrupted. No source/cap
hot patch, recurring automation, old-physical replay or new owner is created.
"""
from pathlib import Path
import os,sys,json,hashlib,subprocess,shlex,base64,datetime,time,signal
M=Path(__file__).resolve().parent;B=M.parents[1];K=B/'manifests/bulk24-collector-46308-20261115-v1';H=B/'registry/handoff_46308_current_status_20261115.json';OWNER='01a1d3aa-a0d5-7de0-b886-9d92ed5f1480';sha=lambda b:hashlib.sha256(b).hexdigest();now=lambda:datetime.datetime.now().astimezone().isoformat();assert os.environ['CODEX_THREAD_ID']==os.environ['CODEX_SESSION_ID']==OWNER
C=json.loads((B/'workers'/M.name/'protocol.json').read_bytes());assert C['main_plan_sha256']==sha(Path('/home/yuanyue/main/汇总/各小组下一步研究计划.md').read_bytes());claim=json.loads((K/'unstarted-suffix20-driver-once-claim.json').read_bytes());pid=claim['driver_PID'];assert pid==2655879 and claim['owner']==OWNER
P=Path('/proc')/str(pid)
def info(p):
 rest=(p/'stat').read_text().split(') ',1)[1].split();return rest[0],rest[19]
args=[x.decode()for x in(P/'cmdline').read_bytes().split(b'\0')if x];assert Path(args[-1]).name=='drive_unstarted_suffix20_once.py'and(P/'cwd').resolve()==B and P.stat().st_uid==os.getuid();state,start=info(P);assert state not in ('T','t','Z')
def children():
 out=[]
 for child in(P/'task'/str(pid)/'children').read_text().split():
  p=Path('/proc')/child
  try:a=[x.decode()for x in(p/'cmdline').read_bytes().split(b'\0')if x]
  except OSError:continue
  out.append((int(child),a))
 return out
before=children();assert len(before)==1 and Path(before[0][1][1]).name=='control_bulk24_v2.py'and before[0][1][-1]in('main-run','fetch-main'),before
with(M/'metadata-gate-once-claim.json').open('x')as f:json.dump(dict(at=now(),local_driver_PID=pid,driver_start_ticks=start,owner=OWNER,source_cmdline=args,child_before=before,remote_native_GPU1_not_signaled=True),f,indent=2);f.write('\n')
watch=None;stopped=False;t0=time.monotonic();phases=[]
WATCH=r'''
from pathlib import Path
import os,sys,time,signal,json,datetime
pid,start,out=sys.argv[1:];p=Path('/proc')/pid;out=Path(out);time.sleep(420)
if not(out/'metadata-gate-released.json').exists()and p.exists():
 rest=(p/'stat').read_text().split(') ',1)[1].split();args=[x.decode()for x in(p/'cmdline').read_bytes().split(b'\0')if x]
 if rest[19]==start and args and Path(args[-1]).name=='drive_unstarted_suffix20_once.py':
  os.kill(int(pid),signal.SIGCONT);(out/'watchdog-resumed-local-driver.json').write_text(json.dumps(dict(at=datetime.datetime.now().astimezone().isoformat(),local_PID=int(pid),remote_native_not_signaled=True)))
'''
def remote(action):
 old=H.read_bytes();beg=time.monotonic();command='/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B /mnt/yuanyue/data-team/deployments/46308-20261114/workspace/manifests/'+M.name+'/component_control_remote.py '+action
 r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228',command],capture_output=True,text=True,timeout=300 if action=='run'else 150)
 for suffix,text in [('stdout',r.stdout),('stderr',r.stderr),('exit',str(r.returncode)+'\n')]:
  with(M/(action+'-control.'+suffix)).open('x')as f:f.write(text)
 phases.append(dict(action=action,exit_code=r.returncode,local_control_wall_s=time.monotonic()-beg,at=now()));assert r.returncode==0,r.stderr;v=json.loads(r.stdout)
 if 'after_base64'in v:
  raw=base64.b64decode(v.pop('after_base64'));assert sha(raw)==v['after_H_sha256'];sys.path.insert(0,str(B/'manifests/new-critic-cohort-46308-20261115-v1'));from mirror_H import mirror;mirror(raw,sha(old))
 if 'small_files'in v:
  D=M/'actual-small';D.mkdir()
  for name,raw in v.pop('small_files').items():assert Path(name).name==name;(D/name).write_bytes(base64.b64decode(raw))
 with(M/(action+'-control-proof.json')).open('x')as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
 return v
try:
 os.kill(pid,signal.SIGSTOP);stopped=True
 for _ in range(100):
  if info(P)[0]in('T','t'):break
  time.sleep(.01)
 assert info(P)[0]in('T','t')and info(P)[1]==start;after=children();assert not after or (len(after)==1 and Path(after[0][1][1]).name=='control_bulk24_v2.py'and after[0][1][-1]in('main-run','fetch-main')),after
 watch=subprocess.Popen([sys.executable,'-B','-c',WATCH,str(pid),start,str(M)],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 with(M/'metadata-gate-entered.json').open('x')as f:json.dump(dict(at=now(),local_PID=pid,state=info(P)[0],child_after=after,watchdog_PID=watch.pid,watchdog_max_hold_s=420,only_local_orchestration_parent_stopped_not_native_GPU1=True),f,indent=2);f.write('\n')
 remote('freeze');remote('prepare');remote('dispatch');run=remote('run');closed=remote('close')
 print(json.dumps(dict(scope_id=C['scope_id'],native_run_exit=run['exit_code'],result=closed['result'],ledger=closed['ledger'],no_E_or_A_B_C_D_main=True),ensure_ascii=False,indent=2))
finally:
 if stopped and P.exists()and info(P)[1]==start:os.kill(pid,signal.SIGCONT)
 with(M/'metadata-gate-released.json').open('x')as f:json.dump(dict(at=now(),local_driver_PID=pid,local_orchestration_hold_wall_s=time.monotonic()-t0,remote_native_GPU1_never_signaled=True,driver_source_and_old_phase_claims_not_modified=True,phases=phases),f,indent=2);f.write('\n')
 if watch is not None and watch.poll()is None:watch.terminate();watch.wait(timeout=10)
