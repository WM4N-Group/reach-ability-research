from pathlib import Path
import json,hashlib,base64,subprocess,shlex,os,sys
M=Path(__file__).resolve().parent;B=M.parents[1];sys.path.insert(0,str(M));from mirror_H import mirror
sha=lambda b:hashlib.sha256(b).hexdigest();owner=os.environ['CODEX_THREAD_ID'];assert owner==os.environ['CODEX_SESSION_ID']=='01a1d3aa-a0d5-7de0-b886-9d92ed5f1480'
ops=['freeze_remote.py','phase_control_remote.py','mirror_H.py','control.py','run_prepare.py','launch_phase.py','run_cold.py','zero_cold_readonly.py','audit_main_readonly.py','adopted_optional_journal_bridge.py','JOURNAL_RECORD_BRIDGE_RELEASE_v1.json']
paths=[M/n for n in ops]+[q for q in(M/'evaluation-inputs').rglob('*')if q.is_file()]
rows=[dict(path=str(p.relative_to(B)),bytes=base64.b64encode(p.read_bytes()).decode(),sha256=sha(p.read_bytes()))for p in paths]
x=dict(owner=owner,expected_H_sha256=sha((B/'registry/handoff_46308_current_status_20261115.json').read_bytes()),files=rows,operation_names=ops)
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-o','ControlMaster=auto','-o','ControlPersist=120','-o','ControlPath=/tmp/data-team-46308-01a1d3aa-ssh','-p','46308','root@180.97.68.228','CUDA_VISIBLE_DEVICES="" MUJOCO_GL=disable OPENBLAS_NUM_THREADS=2 OMP_NUM_THREADS=2 /mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote((M/'freeze_remote.py').read_text())],input=json.dumps(x),capture_output=True,text=True,timeout=240)
for suffix,value in [('stdout',r.stdout),('stderr',r.stderr),('exit',str(r.returncode)+'\n')]:
 with(M/('freeze-transport.'+suffix)).open('x')as f:f.write(value)
assert r.returncode==0,r.stderr
v=json.loads(r.stdout);rec=v['receipt'];after=base64.b64decode(v['after_base64']);assert sha(after)==rec['after_H_sha256']
(M/'freeze-CAS-receipt.json').write_text(json.dumps(rec,ensure_ascii=False,indent=2)+'\n');(M/'H-after-cohort-freeze.json').write_bytes(after);mirror(after,rec['before_H_sha256']);print(json.dumps(rec,ensure_ascii=False,indent=2))
