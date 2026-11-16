from pathlib import Path
import json,hashlib,datetime,base64,subprocess,shlex
B=Path('/home/yuanyue/main/work/data-team');M=Path(__file__).resolve().parent;P=M/'arrival-NNSTOP-original-command-window.json';x=json.loads(P.read_bytes());assert x['window_command_rows']==25 and x['FIFO_within_window_exact'];sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();D=B/'consumer-deliveries/AINAV-DATA-E59-ARRIVAL-NNSTOP-BOUNDED-COMMAND-EVIDENCE-20261116-v1';D.mkdir();(D/'original-window.json').write_bytes(P.read_bytes());(D/'README_CN.md').write_text('''# E59原arrival→NN_STOP有限实际命令窗口

原cold release d7bd4be9…已核所有流；此补充只为AINav定位同一已closed失败，物理次数不增。

原主世界tick5308—5332（26.540—26.660sim）共25条command：每行有原NPZ位置、dtype/shape、完整issued/delayed/q_before/dq_before/raw_torque/torque byte SHA。五个landmark ticks5314/5315/5319/5322/5326另含精确原6字段值，未重算或改动原数组。父NPZ仍在远端，SHA及原index entry齐；本机只86.8KB小证据，不迁批量NPZ/图像。

原5314tick/26.570sim测量首次合格；其后第一条issued5315依原4步FIFO在5319实际应用。首次失格测量5326/26.630sim处的delayed来自issued5322，不是同tick requested。这只是精确队列关联，不能仅凭命令差值认定controller归属或唯一动力学/接触原因。

helper仅CPU/NumPy只读一小段，父NPZ与H前后不改，无Runtime/Actor/MuJoCo/Renderer、无回放/新world/模型调用/训练。此证据为PRIVATE_EVIDENCE，禁止送在线planner或fit；任务失败/PUSH terminal=None/旧成本和原片标签保持。下一原arrival/NN_STOP根因修复由AINav负责，不把提速/E20降高当PUSH修复，不降低门或重跑closed。
''')
r=dict(schema='Data-E59-arrival-NNSTOP-original-bounded-command-evidence-v1',at=datetime.datetime.now().astimezone().isoformat(),scope_id=x['scope_id'],program_sha256=x['program_sha256'],original_result_sha256=x['result_sha256'],original_journal_sha256=x['original_journal_sha256'],prior_cold_release_sha256='d7bd4be94aeab1662c0b973ec358971aefee7b422abd01711ae2a8268d38faba',ticks_inclusive=x['physical_tick_window_inclusive'],rows=25,exact_landmark_ticks=x['exact_original_landmark_ticks'],FIFO_exact=True,no_unique_root_cause_claim=True,no_physics_replay_or_retry=True,training_allowed=False,model_input_allowed=False,files={p.name:sha(p)for p in D.iterdir()if p.is_file()});(D/'release.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
code=r'''
from pathlib import Path
import json,base64,hashlib,sys
x=json.load(sys.stdin);D=Path('/mnt/yuanyue/data-team/deployments/46308-20261114/workspace/consumer-deliveries')/x['name'];assert not D.exists();D.mkdir()
for name,v in x['files'].items():
 p=D/name;assert p.resolve().is_relative_to(D)
 with p.open('xb')as f:f.write(base64.b64decode(v))
r=json.loads((D/'release.json').read_bytes())
for name,pin in r['files'].items():assert hashlib.sha256((D/name).read_bytes()).hexdigest()==pin
print(json.dumps(dict(remote_release=str(D/'release.json'),release_sha256=hashlib.sha256((D/'release.json').read_bytes()).hexdigest(),all_files_SHA_match=True,no_runtime_or_H_mutation=True)))
'''
y=dict(name=D.name,files={p.name:base64.b64encode(p.read_bytes()).decode()for p in D.iterdir()if p.is_file()});a=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],input=json.dumps(y),capture_output=True,text=True,timeout=60);assert a.returncode==0,a.stderr;receipt=json.loads(a.stdout);assert receipt['release_sha256']==sha(D/'release.json');(M/'command-window-publication-proof.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n');print(json.dumps(dict(local_release=str(D/'release.json'),**receipt),ensure_ascii=False))
