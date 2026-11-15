from pathlib import Path
import sys,json,base64,hashlib,os,subprocess,shlex
M=Path(__file__).parent;B=M.parents[1];sys.path.insert(0,str(M));from mirror_H import mirror
c,action=sys.argv[1:];sha=lambda b:hashlib.sha256(b).hexdigest();before=(B/'registry/handoff_46308_current_status_20261115.json').read_bytes();x=dict(candidate=c,action=action,expected_H_sha256=sha(before),owner=os.environ['CODEX_THREAD_ID'])
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-o','ControlMaster=auto','-o','ControlPersist=120','-o','ControlPath=/tmp/data-team-46308-01a1d3aa-ssh','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote((M/'phase_control_remote.py').read_text())],input=json.dumps(x),capture_output=True,text=True,timeout=150)
(M/c).mkdir(exist_ok=True);(M/c/('control-'+action+'.stderr')).write_text(r.stderr);assert r.returncode==0,r.stderr
out=json.loads(r.stdout);raw=base64.b64decode(out['after_base64']);assert sha(raw)==out['receipt']['after_H_sha256'];mirror(raw,sha(before));(M/c/('CAS-'+action+'.json')).write_text(json.dumps(out['receipt'],indent=2)+'\n');print(json.dumps(out['receipt'],indent=2))
