from pathlib import Path
import json,hashlib,datetime,base64,subprocess,shlex
B=Path('/home/yuanyue/main/work/data-team');M=Path(__file__).resolve().parent;C=B/'development/perf-resource-policy-20261116-v1';D=B/'consumer-deliveries/AINAV-DATA-PERF-CONTROLLED-IO-PERIODIC-GUARD-CPU-QUALIFIED-NOT-NATIVE-20261116-v1';D.mkdir();sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
for p in C.iterdir():
 if p.is_file()and p.suffix in('.py','.json','.md'):
  q=D/'code'/p.name;q.parent.mkdir(exist_ok=True);q.write_bytes(p.read_bytes())
for name in ['remote-CPU-tests.json','remote-additional-tests-and-FUSE-benchmark.json','remote-shutdown-safety-test.json','local-final-tests.stderr','local-same-tree-benchmark.json','exact-current-parallel8-comparison.json','primary-performance-assessment.json','new-plan-acceptance-and-safety-boundaries.json','closed-tree-sizes-only.json']:
 p=D/'evidence'/name;p.parent.mkdir(exist_ok=True);p.write_bytes((M/name).read_bytes())
a=json.loads((M/'primary-performance-assessment.json').read_bytes());files={str(p.relative_to(D)):sha(p)for p in D.rglob('*')if p.is_file()};r=dict(schema='Data-future-resource-IO-policy-CPU-qualification-primary-matched-benchmark-v1',at=datetime.datetime.now().astimezone().isoformat(),plan_sha256='02dc65edff1a562a4e1d47b6f24ebd8b169d99d780bd69c8c6a9063cb1a73064',role='CPU_CANDIDATE_NOT_NATIVE_OR_METHOD_RESULT',CPU_tests_local=30,CPU_tests_target=30,target_tests_split=[26,3,1],original_recorder_fixture_commands40_byte_identical=True,original_Journal_fixture100_rows_byte_identical=True,original_module_monkeypatch=False,primary_baseline='exact deployed parallel8 source052747ca…',target_filesystem='fuseblk',tree_files=93,logical_tree_bytes=38388712,hot_calls_per_round=1000,rounds=3,directory_scans_old_new=[1000,101],median_paired_directory_component_ratio=a['median_paired_component_ratio'],hot_guard_median_microseconds=a['median_hot_guard_microseconds_per_call'],static_and_resource_detection_schedule_intentionally_changed=True,poll_s=1.,stale_s=2.,native_guards_unchanged_required=True,no_current_or_closed_run_hotpatch=True,native_ready=False,end_to_end_5x_measured=False,real_static_audit_share_below10percent_measured=False,Runtime_Actor_restore_forward_renderer_physics_GPU_training_calls=0,missing_native_wiring=json.loads((C/'IO_COVERAGE.json').read_bytes())['categories'],files=files);(D/'release.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
code=r'''
from pathlib import Path
import json,sys,base64,hashlib
x=json.load(sys.stdin);B=Path('/mnt/yuanyue/data-team/deployments/46308-20261114/workspace');D=B/'consumer-deliveries'/x['name'];assert not D.exists();D.mkdir()
for rel,v in x['files'].items():
 p=D/rel;assert p.resolve().is_relative_to(D);p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb')as f:f.write(base64.b64decode(v))
r=json.loads((D/'release.json').read_bytes())
for rel,pin in r['files'].items():assert hashlib.sha256((D/rel).read_bytes()).hexdigest()==pin
# Future-only development copies, never old frozen workers/control/registry.
T=B/'development/perf-resource-policy-20261116-v1'
for p in(D/'code').iterdir():
 q=T/p.name
 if q.exists()and q.suffix=='.py':assert q.read_bytes()==p.read_bytes(),'Tested source drift'
 else:q.write_bytes(p.read_bytes())
print(json.dumps(dict(remote_release=str(D/'release.json'),release_sha256=hashlib.sha256((D/'release.json').read_bytes()).hexdigest(),all_files_SHA_match=True,no_frozen_worker_H_or_runtime_mutation=True)))
''';payload=dict(name=D.name,files={str(p.relative_to(D)):base64.b64encode(p.read_bytes()).decode()for p in D.rglob('*')if p.is_file()});p=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],input=json.dumps(payload),capture_output=True,text=True,timeout=60);assert p.returncode==0,p.stderr;x=json.loads(p.stdout);assert x['release_sha256']==sha(D/'release.json');(M/'CPU-candidate-publication-proof.json').write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n');print(json.dumps(dict(local_release=str(D/'release.json'),**x),ensure_ascii=False))
