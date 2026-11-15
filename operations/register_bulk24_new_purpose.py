#!/usr/bin/env python3
"""Freeze a new 24-main collection scope via source-only pure-function checks.

No dispatch, fit, Actor, Runtime, native qualification or other-owner code edits.
The source-owner test harness supplies AST-sliced original protocol/catalogue
functions on a TEMPORARY source snapshot. These are SOFTWARE checks only.
"""
import argparse,datetime as dt,hashlib,importlib.util,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from research.task_conditioned_reachability.execution_preparation.bulk_coverage_registration import build_bulk24_registration
from research.task_conditioned_reachability.execution_preparation.successor_aware_choice import need,digest


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('source-root','source-record','baseline-protocol','output','evidence-output'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--expected-source-record-sha',required=True)
    a=p.parse_args();record_bytes=a.source_record.read_bytes()
    need(hashlib.sha256(record_bytes).hexdigest()==a.expected_source_record_sha,'Exact source-owner release record')
    record=json.loads(record_bytes);own=a.source_root/'development/bulk_registered_conditions_v1'
    def source_pins():
        for name,h in record['files_sha256'].items():
            path=own/name;need(not path.is_symlink()and hashlib.sha256(path.read_bytes()).hexdigest()==h,'Source owner file drift: '+name)
    source_pins();matrix=json.loads((own/'BULK_MATRIX.json').read_bytes());base_bytes=a.baseline_protocol.read_bytes();base=json.loads(base_bytes)
    registered_at=dt.datetime.now().astimezone().isoformat()
    protocol=build_bulk24_registration(matrix,base,registered_at=registered_at,
        source_commit=record['cloud_commit'],source_files=record['files_sha256'])
    # Never imports a native constructor. The source harness itself fences numpy,
    # torch, mujoco, network/child calls and only copies small code into a tempdir.
    path=own/'tests/test_bulk_source.py'
    spec=importlib.util.spec_from_file_location('source_owner_bulk24_software_harness',path)
    harness=importlib.util.module_from_spec(spec);sys.modules[spec.name]=harness;spec.loader.exec_module(harness)
    cls=harness.BulkSourceTests;cls.setUpClass();checked=[];native_hashes={}
    try:
        helper=cls();conditions={c['condition_key']:c for c in protocol['conditions']}
        scenes={s['group_id']:s for s in protocol['scenes']}
        for row in protocol['attempt_schedule']:
            value=helper.build(row['group_id'],row['prefix_side'],row['candidate_id'])
            need(value['requested_intents']==conditions[row['condition_key']]['requested_intents']and
                 value['preparation_payload']==row['preparation_payload'],'Actual source public requests/arm differ from registration')
            native=value['original_native_protocol'];scene=scenes[row['group_id']]
            need(native['integrated_case']==scene['scene_key_canonical_payload']['integrated_case']and
                 native['registered_materials']==scene['scene_key_canonical_payload']['registered_materials'],
                 'Original source protocol differs from planned case/materials')
            need(native['training_allowed']is False and native['automatic_retry']is False and
                 value['qualified_dynamic_domain']is False and value['dispatch']is False,'No native fit/dispatch permission')
            h=digest(native);need(row['group_id']not in native_hashes or native_hashes[row['group_id']]==h,
                                 'Prefix/arm changed the shared native scene protocol')
            native_hashes[row['group_id']]=h;checked.append(row['attempt_key'])
        for scene in protocol['scenes']:
            scene['original_native_protocol_sha256_canonical']=native_hashes[scene['group_id']]
            scene['canonical_native_protocol_binding_owner']='Planned from original pure source functions, SOFTWARE only; Data must rebind exact actual protocol/fresh program/model before launch'
    finally:cls.tearDownClass()
    source_pins();need(a.baseline_protocol.read_bytes()==base_bytes,'Original baseline protocol changed')
    need(not harness.blocked,'Forbidden source-harness side effect')
    protocol['baseline_collection_lineage_sha256']=hashlib.sha256(base_bytes).hexdigest()
    protocol['source_owner_record_sha256']=a.expected_source_record_sha
    protocol['source_binding']['source_only_request_payload_checks']=len(checked)
    protocol['source_binding']['source_pure_validation_is_not_native_qualification']=True
    protocol['source_binding']['source_harness_sha256']=record['files_sha256']['tests/test_bulk_source.py']
    need(not a.output.exists()and not a.evidence_output.exists(),'Exclusive new registration and evidence; no overwrite/reregistration')
    with a.output.open('x')as f:json.dump(protocol,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
    evidence=dict(at=registered_at,role='SOURCE_PURE_FUNCTION_REGISTRATION_CHECK_NOT_NATIVE_OR_RESEARCH_SAMPLES',
        protocol_path=str(a.output.resolve()),protocol_sha256=hashlib.sha256(a.output.read_bytes()).hexdigest(),
        source_owner_record_sha256=a.expected_source_record_sha,source_owner_commit=record['cloud_commit'],
        checked_exact_source_bindings=len(checked),four_planned_native_protocol_hashes=native_hashes,
        worlds=0,physical_attempts=0,models_trained=0,source_files_modified=False,forbidden_attempts=harness.blocked)
    with a.evidence_output.open('x')as f:json.dump(evidence,f,ensure_ascii=False,indent=2);f.write('\n')
    print(json.dumps(evidence,ensure_ascii=False))
if __name__=='__main__':main()
