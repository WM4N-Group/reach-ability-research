"""Reusable bounded metadata read. No deployment, H/native/model call or overwrite of original data."""
from pathlib import Path
import json,subprocess,hashlib,shlex,datetime
M=Path(__file__).resolve().parent;source=(M/'summarize_fixed24_readonly.py').read_text();stamp=datetime.datetime.now().strftime('%Y%m%dT%H%M%S');r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','taskset -c 36,37 /mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(source)],capture_output=True,text=True,timeout=90)
for suf,data in[('stdout',r.stdout),('stderr',r.stderr),('exit',str(r.returncode))]:
 with(M/(stamp+'.'+suf)).open('x')as f:f.write(data)
assert r.returncode==0,r.stderr;v=json.loads(r.stdout)
with(M/(stamp+'-fixed24-scalar-snapshot.json')).open('x')as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
(M/'latest-snapshot-pointer.json').write_text(json.dumps(dict(file=stamp+'-fixed24-scalar-snapshot.json',sha256=hashlib.sha256((M/(stamp+'-fixed24-scalar-snapshot.json')).read_bytes()).hexdigest()),indent=2)+'\n')
print(json.dumps({k:v[k]for k in['at','closed','conditional_original_chain_PASS','closed_nonPASS','not_started','dispatched_not_closed','batch_physically_and_metadata_closed','failure_class_counts','closed_ledger_usage_all_known','closed_only_scope_sim_s','closed_only_scope_wall_s']},ensure_ascii=False,indent=2))
