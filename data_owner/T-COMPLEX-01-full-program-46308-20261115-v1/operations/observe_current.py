from pathlib import Path
import subprocess,shlex,json,datetime
M=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import json,hashlib,datetime
R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114');B=R/'workspace';H=B/'registry/handoff_current_status_20261115.json';raw=H.read_bytes();h=json.loads(raw);q=h['active_T_COMPLEX_full_program_scope'];S=R/'runtime/workers'/q['scope_id'];L=S/'accounting/ledger.json';ledger=json.loads(L.read_bytes())if L.exists()else None;phase='main'if q['main_dispatch_count']else'zero';D=S/phase;result=D/'result.json';result=json.loads(result.read_bytes())if result.exists()else None;events=[];capture=[];p=D/'events.jsonl'
if p.exists():
 for line in p.read_text().splitlines():
  try:v=json.loads(line)['payload']
  except(json.JSONDecodeError,KeyError):continue
  if v.get('event')=='complex_actual_cold_capture_completed':capture.append({k:v.get(k)for k in('event','time_s','actual_steps','witness')})
  events.append(v.get('event'))
pid=ledger['rows'][-1]['PID']if ledger and ledger['rows']else None
print(json.dumps(dict(at=datetime.datetime.now().astimezone().isoformat(),H_sha256=hashlib.sha256(raw).hexdigest(),scope=q,pair_status=h['T_COMPLEX_full_program_v1']['status'],global_stop=h['T_COMPLEX_full_program_v1']['global_stop'],branches=h['T_COMPLEX_full_program_v1']['branches'],PID=pid,PID_exists=bool(pid and Path('/proc/'+str(pid)).exists()),ledger_last=ledger['rows'][-1]if ledger and ledger['rows']else None,result_status=result['status']if result else None,result_error=result.get('error')if result else None,result_passed=result['passed']if result else None,capture_witness_events=capture,last_events=events[-12:]),ensure_ascii=False))
'''
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],text=True,capture_output=True,timeout=60);assert r.returncode==0,r.stderr;v=json.loads(r.stdout);p=M/('current-remote-observation-'+datetime.datetime.now().strftime('%Y%m%dT%H%M%S')+'.json');p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n');(M/'latest-observation-pointer.json').write_text(json.dumps(dict(file=p.name),indent=2)+'\n');print(json.dumps(v,ensure_ascii=False,indent=2))
