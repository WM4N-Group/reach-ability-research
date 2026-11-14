"""Offline Data reader for AINav's actual intent/binding/receipt extract.

No runtime, planner, model or native execution import. This is an EVIDENCE view,
not an admission gate or public planner input. Missing evidence stays unknown.
"""
from __future__ import annotations
import copy
import hashlib
import json
import math
from pathlib import Path


def digest(value, *, native=False):
    # These are the respective serializers in AINav contracts / behavior_authority.
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=native,
        allow_nan=False, separators=(',', ':')).encode()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def params(value):
    pairs = value['parameters']
    require(isinstance(pairs, list), 'Parameters must retain original JSON pairs')
    require(all(isinstance(p, list) and len(p) == 2 and isinstance(p[0], str)
                for p in pairs), 'Malformed parameter pairs')
    keys = [p[0] for p in pairs]
    require(keys == sorted(set(keys)), 'Duplicate or unsorted parameter keys')
    require(all(type(v) in (float, int) and math.isfinite(v) for _, v in pairs),
            'Nonfinite/bool parameters are not measurements')
    return dict(pairs)


def index_extract(extract):
    """Read records, never fill a missing receipt or turn preparation into success.

    `extract` is the AINav owner's existing three-list JSON export, not a world
    snapshot. A partial extract is legal: absence of a start/terminal receipt is
    unobserved, NOT proof the native action was unexecuted or failed.
    """
    require(isinstance(extract, dict) and set(extract) == {'intents', 'bindings', 'receipts'},
            'Exact AINav three-list event extract required')
    require(all(isinstance(v, list) for v in extract.values()), 'Event lists required')
    decisions, by_intent, executions = [], {}, {}
    for selected in extract['intents']:
        require(selected.get('event') == 'skill_intent_selected', 'Selection event required')
        intent = selected['intent']
        params(intent)
        ident = digest(dict(layer='semantic_skill_intent', **intent))
        require(selected['intent_sha256'] == ident, 'Selected intent content hash mismatch')
        require(ident not in by_intent, 'Duplicate selection identity')
        row = dict(intent_sha256=ident, selected_intent=copy.deepcopy(intent),
            intent_source=selected['intent_source'],
            semantic_query_sha256=selected['semantic_query_sha256'],
            model_selection_ref=selected['model_selection_ref'], native_executions=[])
        decisions.append(row)
        by_intent[ident] = row
    for bound in extract['bindings']:
        require(bound.get('event') == 'intent_native_execution_bound', 'Binding event required')
        require(bound.get('model_input') is False, 'Private native binding must stay EVIDENCE')
        ident = bound['intent_sha256']
        require(ident in by_intent, 'Binding without its selected intent')
        selected = by_intent[ident]
        require(bound['intent'] == selected['selected_intent'] and
                digest(dict(layer='semantic_skill_intent', **bound['intent'])) == ident,
                'Selected goal changed during preparation/execution')
        require(bound['model_selection_ref'] == selected['model_selection_ref'] and
                bound['intent_source'] == selected['intent_source'], 'Selection provenance changed')
        option = bound['native_option']
        p = params(option)
        oid = digest(option, native=True)
        require(bound['native_option_sha256'] == oid, 'Native option content hash mismatch')
        require(oid not in executions, 'Duplicate bound native option')
        role = bound['execution_role']
        require(role in ('preparation', 'interaction'), 'Unknown role must get explicit adapter support')
        if role == 'interaction':
            require(option['skill'] == selected['selected_intent']['skill'],
                    'Interaction skill differs from selected intent')
            # The selected/public target_ref and private native target_ref CAN
            # differ; keep both. But public PUSH goal parameters cannot drift.
            if option['skill'] == 'PUSH':
                wanted = params(selected['selected_intent'])
                for key in ('goal_world_x_m', 'goal_world_y_m', 'push_distance_m', 'surface_height_m'):
                    if key in wanted:
                        require(p.get(key) == wanted[key], 'Native PUSH changed public goal')
        row = dict(native_option_sha256=oid, native_option=copy.deepcopy(option),
            execution_role=role, physical_decision_id=bound['physical_decision_id'],
            physical_observation_sha256=bound['physical_observation_sha256'],
            physical_query_sha256=bound['physical_query_sha256'], judgment_ref=bound['judgment_ref'],
            receipts=[], first_started_time_s=None, literal_terminal_status=None,
            literal_terminal_time_s=None, execution_evidence='UNOBSERVED',
            finish_phase=None, finish_phase_coverage='NO_COVERAGE',
            successor_ready=None, successor_ready_coverage='NO_COVERAGE')
        selected['native_executions'].append(row)
        executions[oid] = row
    known_status = {'admitted', 'running', 'started', 'budget_expired', 'hard_stop',
                    'succeeded', 'failed', 'protected_exit_complete'}
    for receipt in extract['receipts']:
        oid, status, time_s = receipt['option_sha256'], receipt['status'], receipt['time_s']
        require(oid in executions, 'Receipt without bound option')
        require(status in known_status, 'Unknown literal native status')
        require(type(time_s) in (int, float) and math.isfinite(time_s) and time_s >= 0,
                'Actual finite nonnegative receipt time required')
        require(isinstance(receipt.get('evidence_ref'), str) and receipt['evidence_ref'],
                'Receipt evidence reference required')
        command_sha = receipt.get('issued_command_sha256')
        require(isinstance(command_sha, str) and len(command_sha) == 64 and
                set(command_sha) <= set('0123456789abcdef'), 'Actual command SHA required')
        row = executions[oid]
        previous = row['receipts']
        require(not previous or time_s >= previous[-1]['time_s'], 'Reversed option receipt clock')
        require(row['literal_terminal_status'] is None, 'Receipt after terminal boundary')
        previous.append(copy.deepcopy(receipt))
        if status == 'started':
            require(row['first_started_time_s'] is None, 'Duplicate first started receipt')
            row['first_started_time_s'] = time_s
            row['execution_evidence'] = 'STARTED_RECEIPT_OBSERVED'
        if status in {'succeeded', 'failed', 'protected_exit_complete'}:
            row['literal_terminal_status'] = status
            row['literal_terminal_time_s'] = time_s
        # budget_expired and hard_stop retain their own literal namespaces;
        # neither is rewritten to a fabricated failed/terminal receipt.
    return dict(schema='Data-AINav-intent-native-evidence-index-v1',
        role='EVIDENCE_NOT_PLANNER_INPUT', decisions=decisions,
        selected_intents=len(decisions), bound_native_options=len(executions),
        literal_receipts=sum(len(r['receipts']) for r in executions.values()),
        actual_command_array_coverage='NO_COVERAGE', actual_RGBD_coverage='NO_COVERAGE',
        actual_native_distance_coverage='NO_COVERAGE',
        finish_and_successor_labels_inferred=False, task_success_inferred=False,
        new_queries_or_episodes=0, dataset_or_training_admission=False)


def read_pinned(path, expected_sha256, *, max_bytes=2*1024*1024):
    path = Path(path)
    require(path.is_absolute() and not path.is_symlink(), 'Explicit nonsymlink source path required')
    require(path.stat().st_size <= max_bytes, 'Bounded source input required')
    raw = path.read_bytes()
    require(len(raw) <= max_bytes and hashlib.sha256(raw).hexdigest() == expected_sha256,
            'Input file SHA mismatch')
    return json.loads(raw)


def inspect_historical_package(inputs):
    """Join ONE archived source package; historical acceptance is not deployment."""
    require(set(inputs) == {'extract', 'summary', 'report', 'freeze'}, 'Four exact source refs required')
    data = {k: read_pinned(v['path'], v['sha256']) for k, v in inputs.items()}
    summary, report, freeze = data['summary'], data['report'], data['freeze']
    require(summary['source_report_sha256'] == inputs['report']['sha256'], 'Summary/report byte mismatch')
    source = summary['source_manifest_sha256']
    require(report['source_manifest_sha256'] == source == freeze['source_manifest_sha256'],
            'Mixed source manifests are not one host')
    result = index_extract(data['extract'])
    # This is a consistency check against the owner's archived intervals, not a
    # substitute for reading the raw 200Hz commands/physical success audit.
    intervals = summary['actual_execution_intervals_detail']
    by_option = {r['native_option_sha256']: (d, r) for d in result['decisions']
                 for r in d['native_executions']}
    require(len(intervals) == len(by_option) and len({i['native_option_sha256'] for i in intervals}) == len(intervals),
            'Historical interval inventory mismatch')
    for interval in intervals:
        require(interval['native_option_sha256'] in by_option, 'Unknown historical interval')
        d, r = by_option[interval['native_option_sha256']]
        require(interval['intent_skill'] == d['selected_intent']['skill'] and
                interval['intent_target'] == d['selected_intent']['target_ref'] and
                interval['execution_role'] == r['execution_role'] and
                interval['native_skill'] == r['native_option']['skill'], 'Interval binding mismatch')
        require(r['first_started_time_s'] == interval['actual_first_motor_time_s'] and
                r['literal_terminal_status'] == 'succeeded' and
                r['literal_terminal_time_s'] == interval['actual_success_time_s'],
                'Interval/receipt boundary mismatch')
    result.update(source_inputs=copy.deepcopy(inputs), historical_source_manifest_sha256=source,
        historical_root=summary['root'], historical_owner_task_success_claim=summary['original_full_task_passed'],
        source_full_bytes_reverified=False, source_owner_baseline_selection='PENDING_AINAV_PUBLICATION',
        current_host_runtime_or_zero_qualified=False, physical_dispatch_authorized=False,
        historical_VLM_calls_not_new_API_calls=summary['API_calls'])
    return result
