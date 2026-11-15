#!/usr/bin/env python3
"""Activate derived TRAIN-only files ONLY after all fixed six NEW attempts close.

Leaves original collection protocol/roles untouched. No fit, physics, GPU,
Data authority edits or heldout acquisition. Invoke the existing train-only CLI
once after this source/feature/label gate succeeds; weights/data stay on46308.
"""
import argparse,copy,datetime as dt,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from research.task_conditioned_reachability.execution_preparation.successor_aware_choice import need,digest
from research.task_conditioned_reachability.execution_preparation.successor_critic import PURPOSE,validate_dataset,_validate_finite_stage,attempt_spending

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('collection-protocol','authorization','output-root'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--attempt',type=Path,action='append',required=True)
    a=p.parse_args();collection=json.loads(a.collection_protocol.read_bytes());base_sha=sha(a.collection_protocol)
    need(collection['qualified_entry_condition_family'] is False and collection['data_purpose']==PURPOSE,'Immutable NEW collection purpose')
    need(sha(a.authorization)==collection['authorization_sha256'],'Exact original user training grant')
    expected={r['attempt_key']:r for r in collection['attempt_schedule'] if r['split']=='TRAIN'}
    need(len(a.attempt)==len(expected)==6,'Complete fixed TRAIN6, not an early subset or replacement')
    reports=[];pins={str(a.collection_protocol.resolve()):base_sha,str(a.authorization.resolve()):sha(a.authorization)}
    for path in a.attempt:
        need(not path.is_symlink(),'Regular explicit NEW extraction report')
        r=json.loads(path.read_bytes());sample=r.get('sample')
        need(r.get('collection_protocol_file_sha256')==base_sha and r.get('fit_allowed')is False,
             'Extraction never supplies standalone fit permission')
        need(r.get('status')=='NEW_PURPOSE_ROW_EXTRACTED_AWAIT_COMPLETE_TRAIN_GATE' and sample is not None,
             'Missing/unreached/unclassified attempt: report No-Go, do not drop it or invent a row')
        need(sample['attempt_key'] in expected and sample['split']=='TRAIN','Only six frozen TRAIN keys')
        if sample['outcome']=='NATIVE_GUARD_FAILURE':
            witness=r.get('label_witness')
            need(witness is not None and witness.get('kind') in (
                'SOURCE_VERIFIED_NATIVE_CLIMB_STOP_DEADLINE_EXCEPTION',
                'SOURCE_VERIFIED_NATIVE_CLIMB_FORBIDDEN_CONTACT_EXCEPTION')
                and witness.get('literal_failed_terminal_receipt_synthesized') is False,
                'Native failures require their original source witness, never error-text relabelling')
        for source,h in r['source_pins'].items():need(sha(source)==h,'Actual closed source changed: '+source)
        reports.append((path,r));pins[str(path.resolve())]=sha(path)
    need(len({r['sample']['attempt_key'] for _,r in reports})==6,'No repeated extraction of one acquisition')
    reports.sort(key=lambda item:expected[item[1]['sample']['attempt_key']]['ordinal'])
    derived=copy.deepcopy(collection)
    derived.update(qualified_entry_condition_family=True,collection_protocol_file_sha256=base_sha,
        derived_training_gate_at=dt.datetime.now().astimezone().isoformat(),
        qualification_scope='ONLY_THIS_SIX_TRAIN_EXPLORATORY_CONDITIONAL_FAMILY_NOT_DEPLOYMENT_OR_G5',
        training_gate_source_reports={str(path.resolve()):sha(path) for path,_ in reports})
    data=dict(purpose=PURPOSE,origin='FUTURE_NEW_CAPTURE',training_allowed=True,
        authorization_sha256=collection['authorization_sha256'],preregistration_sha256=digest(derived),
        collection_protocol_file_sha256=base_sha,preregistered_at=collection['registered_at'],
        feature_profile_sha256=collection['feature_profile_sha256'],feature_extractor_sha256=collection['feature_extractor_sha256'],
        all_closed_attempts_accounted=True,closed_attempt_count=6,unreached_decision_attempts=[],
        rows=[r['sample']for _,r in reports])
    # Temporary true flag is NOT written until both the original and exact-stage
    # gates pass; all original hyperparameters/splits/features stay byte-equivalent.
    rows=validate_dataset(data,json.loads(a.authorization.read_bytes()),derived,phase='TRAIN_ONLY')
    _validate_finite_stage(data,derived,'TRAIN_ONLY')
    gate=dict(status='CLOSED_TRAIN_SOURCE_FEATURE_LABEL_GATE_PASS_NOT_FIT_OR_DISPATCH',
        at=dt.datetime.now().astimezone().isoformat(),collection_protocol_file_sha256=base_sha,
        closed_attempts=6,new_purpose_rows=len(rows),success_rows=sum(r['outcome']=='SUCCESS'for r in rows),
        native_failure_rows=sum(r['outcome']=='NATIVE_GUARD_FAILURE'for r in rows),
        source_scene_groups=len({r['source_scene_sha256']for r in rows}),
        condition_groups=len({r['condition_binding_sha256']for r in rows}),
        distinct_public_proprio_states=len({tuple(round(v,6)for v in r['physical_features'][2:47])for r in rows}),
        spending=attempt_spending(data),source_pins=pins,old_DEV_fit=False,physical_dispatch=False,
        original_collection_flag_or_Data_authority_modified=False,statistical_or_execution_qualification=False)
    need(not a.output_root.exists(),'Fresh derived output directory, never overwrite an old fit')
    a.output_root.mkdir()
    for name,obj in (('DERIVED_TRAINING_PROTOCOL.json',derived),('CLOSED_TRAIN_ONLY_DATASET.json',data),('TRAIN_SOURCE_FEATURE_LABEL_GATE.json',gate)):
        with (a.output_root/name).open('x')as f:json.dump(obj,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
    print(json.dumps({k:v for k,v in gate.items()if k not in ('source_pins','spending')}))
if __name__=='__main__':main()
