from pathlib import Path
import subprocess,shlex,json
M=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import json,hashlib
import numpy as np
R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114');B=R/'workspace';W=B/'workers/T-COMPLEX-01-full-program-46308-20261115-v1';M=B/'manifests/T-COMPLEX-01-full-program-46308-20261115-v1';protocol=json.loads((W/'protocol.json').read_bytes());roots={a:R/'runtime/workers'/p['scope_id']/'zero'for a,p in protocol['arms'].items()};sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();packets={};states={};frames={};pins={}
for a,root in roots.items():
 r=json.loads((root/'result.json').read_bytes());assert r['passed']and r['task_physics_steps']==0;idx=json.loads((root/'episode/index.json').read_bytes());p=root/'episode'/idx['visual'][0]['path'];assert sha(p)==idx['visual'][0]['sha256']
 with np.load(p,allow_pickle=False)as n:packets[a]={k:n[k].copy()for k in n.files if k!='control_ticks'}
 rc=json.loads((root/'review-state/closure.json').read_bytes());p=root/'review-state'/rc['chunks'][0]['path'];assert sha(p)==rc['chunks'][0]['sha256']
 with np.load(p,allow_pickle=False)as n:states[a]=n['full_state'].copy()
 vc=r['raw_third_view_closure'];p=root/'raw-third-view'/vc['chunks'][0]['path'];assert sha(p)==vc['chunks'][0]['sha256']
 with np.load(p,allow_pickle=False)as n:frames[a]=n['rgb'].copy()
 pins[a]=dict(zero_result_sha256=sha(root/'result.json'),numeric_model_sha256=r['actual_model_numeric_sha256'])
checks=dict(same_numeric_model=pins['A']['numeric_model_sha256']==pins['B']['numeric_model_sha256'],exact_full_integration_state_equal=np.array_equal(states['A'],states['B'],equal_nan=True),exact_original_INPUT8_fields_equal={k:np.array_equal(v,packets['B'][k],equal_nan=True)for k,v in packets['A'].items()},exact_direct_HD_frame_equal=np.array_equal(frames['A'],frames['B']));passed=checks['same_numeric_model']and checks['exact_full_integration_state_equal']and all(checks['exact_original_INPUT8_fields_equal'].values())and checks['exact_direct_HD_frame_equal'];v=dict(passed=passed,checks=checks,source_pins=pins,actual_recorded_world0_only=True,no_state_copy_or_restore_or_new_capture=True,no_new_Runtime_Actor_Renderer_model_or_physics=True,not_full_dynamical_trajectory_equivalence_or_task_success=True)
with(M/'actual-AB-zero-condition-equality.json').open('x')as f:json.dump(v,f,indent=2);f.write('\n')
print(json.dumps(v))
'''
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],capture_output=True,text=True,timeout=60);assert r.returncode==0,r.stderr;v=json.loads(r.stdout);(M/'actual-AB-zero-condition-equality.json').write_text(json.dumps(v,indent=2)+'\n');print(json.dumps(v,indent=2));assert v['passed'],'Do not dispatch main on non-identical initial recorded state'
