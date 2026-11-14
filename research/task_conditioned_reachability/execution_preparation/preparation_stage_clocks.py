"""Future, pinned original-journal clock reader; audit-only, never planner input.

No log replays, Runtime, simulator, model, inferred Actor activation, nearest-event
joins or task-success relabelling. CPU fixtures test source-schema interpretation;
actual new envelopes and complete task endpoint still belong to Data.
"""
import hashlib
import json
from .successor_aware_choice import need, pin, number


def _sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
        separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def read_preparation_clocks(raw, *, expected_sha256, journal_ref, intent_sha256, payload):
    """Read bytes already captured by owner, verify the entire original hash chain.

    The interaction's exact judgment_ref binds the READY row; exact intent and
    native_option_sha256 bind its outcome. First proposal is the predeclared
    decision origin, including ALL repeated preparations (not the shortest one).
    Raw success receipt is a stage witness, NOT sufficient whole-task evidence.
    """
    need(type(raw) is bytes and pin(expected_sha256) and
         hashlib.sha256(raw).hexdigest() == expected_sha256, 'Original full journal SHA')
    need(type(journal_ref) is str and journal_ref.startswith('/') and '#' not in journal_ref,
         'Exact original absolute journal reference')
    need(pin(intent_sha256), 'Exact selected CLIMB intent identity')
    need(type(payload) is dict and set(payload) == {'schema','target_ref','candidate_id'} and
         payload['schema'] == 'AINav-finite-CLIMB-preparation-selection-v1' and
         payload['candidate_id'] in ('original','lateral_plus_0p04','lateral_minus_0p04'),
         'Exact finite owner payload')
    rows=[]; previous='0'*64
    for line in raw.splitlines():
        row=json.loads(line)
        need(type(row) is dict and set(row)=={'sequence','previous_sha256','payload','sha256'}, 'Original journal envelope')
        need(type(row['sequence']) is int and row['sequence']==len(rows) and
             row['previous_sha256']==previous and row['sha256']==_sha({k:v for k,v in row.items() if k!='sha256'}),
             'Original journal hash chain changed/reordered')
        need(type(row['payload']) is dict, 'Typed original event payload')
        previous=row['sha256'];rows.append(row)
    result=dict(schema='Reach-source-bound-preparation-clocks-v1', role='AUDIT_ONLY_NOT_PLANNER_OR_FIT',
        journal_sha256=expected_sha256, intent_sha256=intent_sha256, candidate_id=payload['candidate_id'],
        status='UNKNOWN_MISSING_OR_AMBIGUOUS_EXACT_EVENTS', witnesses={},
        preparation_attempts=None, current_to_READY_s=None, READY_to_CLIMB_receipt_s=None,
        decision_to_CLIMB_receipt_s=None, literal_CLIMB_receipt_status=None,
        complete_two_request_task_outcome='UNKNOWN_REQUIRES_OWNER_TASK_ENDPOINT',
        actual_motor_difference_proven=False, inferred_Actor_activation=False,
        original_native_outcome_relabelled=False, execution_authorized=False)
    def events(name):
        return [r for r in rows if r['payload'].get('event')==name and
                r['payload'].get('intent_sha256')==intent_sha256]
    proposals=events('ainav_selected_CLIMB_preparation_NAV_goal_proposed')
    if not proposals:
        result['status']='NO_RECORDED_PREPARATION_INTERVENTION_NOT_A_FAILURE';return result
    owner_selection={k:v for k,v in payload.items() if k!='schema'}  # original asdict(PreparationSelection)
    if any(r['payload'].get('selection')!=owner_selection for r in proposals):
        result['status']='MISMATCHED_IMMUTABLE_PREPARATION_PAYLOAD';return result
    bound=[r for r in events('intent_native_execution_bound') if
           r['payload'].get('execution_role')=='interaction' and
           r['payload'].get('intent',{}).get('skill')=='CLIMB' and
           r['payload'].get('intent',{}).get('target_ref')==payload['target_ref']]
    if len(bound)!=1:return result
    bound=bound[0];b=bound['payload']
    if not pin(b.get('native_option_sha256')):return result
    ready=[r for r in events('skill_execution_judgment') if
           b.get('judgment_ref')==journal_ref+'#'+str(r['sequence']+1) and
           r['payload'].get('status')=='READY' and
           r['payload'].get('spec',{}).get('skill')=='CLIMB' and
           r['payload'].get('spec',{}).get('target_ref')==payload['target_ref']]
    if len(ready)!=1:return result
    ready=ready[0]
    receipt=[r for r in events('intent_actual_native_outcome') if
             r['payload'].get('execution_role')=='interaction' and
             r['payload'].get('native_option_sha256')==b.get('native_option_sha256') and
             r['payload'].get('receipt',{}).get('option_sha256')==b.get('native_option_sha256')]
    if len(receipt)!=1:return result
    receipt=receipt[0]
    if not (max(r['sequence'] for r in proposals)<ready['sequence']<bound['sequence']<receipt['sequence']):return result
    decision=proposals[0]
    clocks=(decision['payload'].get('time_s'),ready['payload'].get('state',{}).get('time_s'),
            receipt['payload'].get('receipt',{}).get('time_s'))
    result['literal_CLIMB_receipt_status']=receipt['payload']['receipt'].get('status')
    if not all(number(t) and t>=0 for t in clocks) or not clocks[0]<=clocks[1]<=clocks[2]:return result
    def witness(row, clock_pointer, time):
        return dict(source_journal_sha256=expected_sha256,
            original_hash_chain_record_sha256=row['sha256'], source_pointer_within_JSONL_record='/payload',
            journal_line_1based=row['sequence']+1, evidence_ref=journal_ref+'#'+str(row['sequence']+1),
            clock_pointer_within_event=clock_pointer, actual_sim_time_s=time,
            journal_file_sha256=expected_sha256,
            directly_compatible_with_Data_single_JSON_envelope_reader=False)
    result['witnesses']={name:witness(row,clock,t) for name,row,clock,t in (
        ('preparation_decision',decision,'/time_s',clocks[0]),
        ('successor_entry_READY',ready,'/state/time_s',clocks[1]),
        ('successor_native_receipt',receipt,'/receipt/time_s',clocks[2]))}
    result.update(status='EXACT_SOURCE_BOUND_STAGE_CLOCKS_NOT_WHOLE_TASK_SUCCESS',
        preparation_attempts=len(proposals),current_to_READY_s=clocks[1]-clocks[0],
        READY_to_CLIMB_receipt_s=clocks[2]-clocks[1],decision_to_CLIMB_receipt_s=clocks[2]-clocks[0])
    return result
