"""Merge closed prospective heldout extractions with the exact frozen TRAIN.

No model fitting, scoring, label inference, acquisition or native imports. This
is the missing data-assembly step before the existing evaluate_frozen entry.
Original TRAIN objects, purpose, feature ABI, protocol and all costs are kept.
"""
from copy import deepcopy
from .successor_aware_choice import need, digest
from .successor_critic import (PHASE_SPLITS, validate_dataset, _validate_finite_stage,
                               _training_rows_digest)

ROW_STATUS='NEW_PURPOSE_ROW_EXTRACTED_AWAIT_COMPLETE_TRAIN_GATE'
UNREACHED_STATUS='NO_PROTOCOL_PREPARE_DECISION_NO_SUCCESSOR_ROW'


def assemble_frozen_heldout(train_data, authorization, protocol, artifact, reports, *, phase):
    """Return data only after the entire fixed CAL/VAL phase is closed.

    The I/O caller must verify pinned extraction reports and each original source
    file before and after invoking this pure function. A report never grants fit
    permission. Failed/unreached/unknown attempts cannot disappear from the census.
    """
    need(phase in ('CALIBRATION','FULL_COHORT'),'Frozen heldout phase only, never TRAIN fitting')
    rows=validate_dataset(train_data,authorization,protocol,phase='TRAIN_ONLY')
    _validate_finite_stage(train_data,protocol,'TRAIN_ONLY')
    need(artifact.get('status')=='TRAIN_ONLY_FIT_FROZEN_HELDOUT_NOT_COLLECTED' and
         artifact.get('preregistration_sha256')==digest(protocol), 'Original frozen fit/protocol required')
    need(artifact.get('model_sha256')==digest(artifact['model']), 'Frozen model content changed')
    train_digest=_training_rows_digest(rows)
    need(artifact.get('training_rows_sha256')==train_digest,'Original TRAIN rows changed since fit')
    splits=set(PHASE_SPLITS[phase])-{'TRAIN'}
    expected={r['attempt_key']:r for r in protocol['attempt_schedule'] if r['split'] in splits}
    need(type(reports)is list and len(reports)==len(expected),
         'Complete closed heldout phase required, not a partial result or adaptive replacement')
    records=[];seen=set()
    for report in reports:
        need(report.get('role')=='NEW_PURPOSE_EXTRACTED_ATTEMPT_NOT_BATCH_FIT_PERMISSION' and
             report.get('fit_allowed')is False and report.get('actual_research_model_fits')==0 and
             report.get('new_physics_or_capture')is False, 'Original extraction only, not fitting/capture permission')
        need(report.get('collection_protocol_file_sha256')==protocol['collection_protocol_file_sha256'] and
             report.get('feature_profile_sha256')==protocol['feature_profile_sha256'] and
             report.get('feature_extractor_sha256')==protocol['feature_extractor_sha256'],
             'Same immutable collection purpose and original 48-slot ABI')
        sample=report.get('sample');unreached=report.get('unreached_decision_attempt')
        need((sample is None)!=(unreached is None),'Exactly one classified reached/unreached record; UNKNOWN is not a label')
        reached=sample is not None;record=sample if reached else unreached
        need(report.get('status')==(ROW_STATUS if reached else UNREACHED_STATUS),
             'No unclassified postdecision exception or fabricated successor label')
        key=record.get('attempt_key');need(key in expected and key not in seen,
             'Each scheduled heldout attempt once; no TRAIN/duplicate/replacement')
        seen.add(key);planned=expected[key]
        need(all(record.get(k)==planned[k] for k in ('split','source_scene_sha256','condition_binding_sha256','candidate_id')),
             'Fixed source-scene/condition/candidate split, not role relabelling')
        inventory=report.get('inventory',{})
        need(inventory.get('decision_reached')is reached and all(inventory.get(k)==record.get(k) for k in
             ('scope_id','attempt_key','split','source_scene_sha256','condition_binding_sha256','candidate_id',
              'source_result_sha256','source_journal_sha256','spent_sim_s')),
             'Extraction row and full attempt/cost inventory must agree')
        if reached and sample['outcome']=='NATIVE_GUARD_FAILURE':
            witness=report.get('label_witness')
            # Preserve literal labels too, but source-exception rows need the
            # exact separate witness accepted by the frozen extractor.
            if sample.get('native_failure_witness_kind')is not None:
                need(witness is not None and witness.get('kind')==sample['native_failure_witness_kind'] and
                     witness.get('kind') in ('SOURCE_VERIFIED_NATIVE_CLIMB_STOP_DEADLINE_EXCEPTION',
                                             'SOURCE_VERIFIED_NATIVE_CLIMB_FORBIDDEN_CONTACT_EXCEPTION') and
                     witness.get('literal_failed_terminal_receipt_synthesized')is False,
                     'Original exception source witness required; never fabricate a failed receipt')
        records.append((planned['ordinal'],reached,record))
    out=deepcopy(train_data)
    out.setdefault('unreached_decision_attempts',[])
    for _,reached,record in sorted(records):
        out['rows' if reached else 'unreached_decision_attempts'].append(deepcopy(record))
    out['closed_attempt_count']=len(out['rows'])+len(out.get('unreached_decision_attempts',[]))
    out['all_closed_attempts_accounted']=True
    final_rows=validate_dataset(out,authorization,protocol,phase=phase)
    _validate_finite_stage(out,protocol,phase)
    need(_training_rows_digest(final_rows)==train_digest,'Heldout assembly changed frozen TRAIN')
    return out
