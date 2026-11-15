"""Decode the already-successful original export response locally; no remote call or native retry."""
from pathlib import Path
import json,hashlib,base64,datetime
B=Path('/home/yuanyue/main/work/data-team');M=Path(__file__).resolve().parent;v=json.loads((M/'original-export.stdout').read_bytes());D=B/'consumer-deliveries'/Path(v['release_path']).parent.name;failed=[p for p in D.rglob('*')if p.is_file()];assert len(failed)==1 and failed[0].stat().st_size==0 and str(failed[0].relative_to(D))in v['small_files'];backup=M/'publication-transport-before-decode-fix';backup.mkdir();failed_name=failed[0].name;failed[0].rename(backup/(failed_name+'.empty-from-failed-local-transport'))
for name,data in v.pop('small_files').items():
 p=Path(name);assert not p.is_absolute()and'..'not in p.parts;p=D/p;p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb')as f:f.write(base64.b64decode(data))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();assert sha(D/'release.json')==v['release_sha256'];release=json.loads((D/'release.json').read_bytes())
for name,pin in release['files'].items():assert sha(D/name)==pin
with(M/'component-original-release-proof.json').open('x')as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
with(M/'local-publication-transport-decode-erratum.json').open('x')as f:json.dump(dict(at=datetime.datetime.now().astimezone().isoformat(),error='Local wrapper used b64encode(str) where b64decode was intended; TypeError before first payload write',first_recovery_assertion_incorrectly_expected_result_filename_instead_of_actual_ledger_no_data_changed=True,empty_local_transport_file_archived=str(backup/(failed_name+'.empty-from-failed-local-transport')),remote_export_already_succeeded_once=True,recovered_only_from_original_saved_stdout=True,all_original_release_SHA_verified=True,remote_export_or_native_reruns=0,original_source_result_and_streams_not_changed=True),f,indent=2);f.write('\n')
print(json.dumps(dict(release_sha256=v['release_sha256'],audit=v['audit']),ensure_ascii=False,indent=2))
