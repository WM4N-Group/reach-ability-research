"""One metadata-only close after OBS closure won a whole-H SHA CAS race.
Preserve failed close logs and original failed native attempt, never rerun physics.
"""
from pathlib import Path
import os,json,hashlib,ast,subprocess,shlex,base64,sys
M=Path(__file__).resolve().parent; B=M.parents[1];H=B/'registry/handoff_46308_current_status_20261115.json';old=H.read_bytes();h=json.loads(old);sha=lambda b:hashlib.sha256(b).hexdigest();C=h['bulk24_collector_v1']['order'][3];q=h['active_bulk24_collector_scope'];assert C=='g2-bulk24-v1__bulk-g02_right__original'and q['candidate_id']==C and q['active'] and q['zero_dispatch_count']==q['main_dispatch_count']==1 and not h['active_T_COMPLEX_observation_study_scope']['active']
D=M/C;assert (D/'close-main-control.exit').read_text().strip()=='1'and 'AssertionError' in(D/'close-main-control.stderr').read_text();v=json.loads((D/'main-result.json').read_bytes());assert v['usage_known']and not v['passed']and v['error']=='reconciled_reference_FF_intersection_empty'
owner=os.environ['CODEX_THREAD_ID'];assert owner==os.environ['CODEX_SESSION_ID']==q['owner'];x=dict(owner=owner,arm=C,action='close-main',program=q['whole_program_freeze_sha256'],expected=sha(old))
tree=ast.parse((M/'control_bulk24_v2.py').read_text());parts={t.id:ast.literal_eval(n.value)for n in tree.body if isinstance(n,ast.Assign)for t in n.targets if isinstance(t,ast.Name)and t.id in('PRELUDE','ACTIONS')};code=parts['PRELUDE']+parts['ACTIONS']['close'].replace("D/('CAS-close-'+phase+'.json')","D/('CAS-close-'+phase+'-metadata-reconcile-v3.json')")
assert all(s not in code for s in ['Popen','full_host_worker.py','construct_cold_components','torch','mujoco'])
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],input=json.dumps(x),capture_output=True,text=True,timeout=180)
for suffix,text in [('stdout',r.stdout),('stderr',r.stderr),('exit',str(r.returncode)+'\n')]:
 with(D/('close-main-metadata-reconcile-v3.'+suffix)).open('x')as f:f.write(text)
assert r.returncode==0,r.stderr;out=json.loads(r.stdout);raw=base64.b64decode(out.pop('after_base64'));assert sha(raw)==out['after_H_sha256'];new=json.loads(raw);assert new['active_bulk24_collector_scope']['zero_dispatch_count']==new['active_bulk24_collector_scope']['main_dispatch_count']==1 and not new['active_bulk24_collector_scope']['active']and not new['bulk24_collector_v1']['global_stop']
sys.path.insert(0,str(B/'manifests/new-critic-cohort-46308-20261115-v1'));from mirror_H import mirror;mirror(raw,sha(old))
with(D/'CAS-close-main-metadata-reconcile-v3.json').open('x')as f:json.dump(out,f,indent=2);f.write('\n')
print(json.dumps(dict(**out,metadata_only_after_preserved_CAS_rejection=True,zero_main_counts_unchanged=True,native_original_failure_retained=True),indent=2))
