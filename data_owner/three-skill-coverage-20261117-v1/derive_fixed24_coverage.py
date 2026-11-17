"""Default-OFF, metadata-only retrospective three-skill denominator reader.

Only existing fixed24 release/result/cold-audit metadata; no journal replay,
arrays, video, source execution, simulator, credentials, API or remote access.
Historical labels/purposes stay immutable; not a new L0/L1/L2 screening cohort.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

SKILLS = ('NAV', 'PUSH', 'CLIMB')
PARENT = 'AINAV-DATA-BULK24-FIXED-COLLECTION-CLOSEOUT-NO-REFIT-20261116-v1'
PARENT_SHA = '5367a3a1b0f68f7f623ba596e23a77a39f860905377588840f3bee76cb4eebf9'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def derive(deliveries=None, *, enabled=False):
    if enabled is not True:
        return None
    root = Path(deliveries).resolve(strict=True)
    inputs = {}
    def read(path, expected=None):
        if path.is_symlink():
            raise ValueError('No substituted source metadata')
        raw = path.read_bytes()
        sha = digest(raw)
        if expected is not None and sha != expected:
            raise ValueError('Original release/member SHA drift: '+str(path))
        inputs[str(path)] = sha
        return json.loads(raw)
    parent = read(root/PARENT/'release.json', PARENT_SHA)
    snapshot = read(root/PARENT/'fixed24-final-scalar-snapshot.json', parent['files']['fixed24-final-scalar-snapshot.json'])
    if snapshot['fixed_registered_attempts'] != 24 or snapshot['closed'] != 24 or not snapshot['batch_physically_and_metadata_closed']:
        raise ValueError('Exact historical fixed24 closed denominator only')
    summaries = {s: Counter() for s in SKILLS}
    rows = []
    seen = set()
    for source in snapshot['rows']:
        ordinal = source['ordinal']
        scope = source['scope_id']
        if scope in seen or source['zero_dispatch_count'] != 1 or source['main_dispatch_count'] != 1 or not source['closed']:
            raise ValueError('Unique original scope, both original attempts preserved')
        seen.add(scope)
        directory = root/f'AINAV-DATA-BULK24-ORDINAL-{ordinal:02d}-ORIGINAL-ACTUAL-20261115-v1'
        release = read(directory/'release.json', source['formal_release_sha256'])
        result = read(directory/'evidence/main-result.json', release['files']['evidence/main-result.json'])
        audit = read(directory/'evidence/actual-main-cold-audit-v2.json', release['files']['evidence/actual-main-cold-audit-v2.json'])
        if result['program_sha256'] != source['program_sha256'] or inputs[str(directory/'evidence/main-result.json')] != source['actual_result_sha256']:
            raise ValueError('Historical snapshot program/result identity disagrees')
        if result['scope_id'] != scope or audit['source_result_sha256'] != inputs[str(directory/'evidence/main-result.json')] or not audit['passed']:
            raise ValueError('Real result and existing cold audit must bind this exact scope')
        if not result['CLIMB_requested'] or source['resource_censored'] is not False:
            raise ValueError('Historical planned CLIMB and resource classification changed')
        intents = {x['intent_sha256']: x['intent']['skill'] for x in audit['actual_semantic_intent_selections']}
        admissions = {x['receipt']['option_sha256']: x for x in audit['actual_native_admissions']}
        if len(intents) != len(audit['actual_semantic_intent_selections']) or len(admissions) != len(audit['actual_native_admissions']):
            raise ValueError('Ambiguous duplicate binding; never silently deduplicate')
        if any(s not in SKILLS for s in intents.values()) or any(x['option']['skill'] not in SKILLS for x in admissions.values()):
            raise ValueError('Unexpected semantic skill')
        option_terminals = {}
        for event in audit['actual_native_terminal_receipts']:
            terminal = event['receipt']
            key = terminal['option_sha256']
            if key not in admissions or key in option_terminals:
                raise ValueError('Missing/duplicate option-terminal identity')
            option_terminals[key] = terminal
        semantic_terminals = {}
        for event in audit['actual_intent_native_outcomes']:
            if event['execution_role'] not in ('preparation', 'interaction'):
                raise ValueError('Unreviewed actual execution role')
            if event['execution_role'] != 'interaction':
                continue  # NAV preparation receipt is NOT a failed PUSH intent.
            key = event['intent_sha256']
            if key not in intents or key in semantic_terminals or event['native_option_sha256'] not in admissions:
                raise ValueError('Unbound/duplicate actual semantic interaction')
            terminal = event['receipt']
            if terminal != option_terminals[event['native_option_sha256']]:
                raise ValueError('Semantic/native receipt disagreement')
            if event['intent_succeeded'] != (terminal['status'] == 'succeeded'):
                raise ValueError('Never substitute a preparation/installation success')
            semantic_terminals[key] = terminal
        per_skill = {}
        for skill in SKILLS:
            selected = [key for key, s in intents.items() if s == skill]
            admitted = [key for key, x in admissions.items() if x['option']['skill'] == skill]
            semantic_status = Counter(semantic_terminals[key]['status'] for key in selected if key in semantic_terminals)
            native_status = Counter(option_terminals[key]['status'] for key in admitted if key in option_terminals)
            values = dict(planned_chain_opportunities=1, semantic_selections=len(selected),
                native_option_admissions=len(admitted), semantic_terminal_succeeded=semantic_status['succeeded'],
                native_terminal_succeeded=native_status['succeeded'],
                semantic_terminal_failed=semantic_status['failed'], native_terminal_failed=native_status['failed'],
                selected_without_semantic_terminal=len(selected)-sum(semantic_status.values()),
                admitted_without_native_terminal=len(admitted)-sum(native_status.values()),
                predecessor_blocked_before_selection=int(not selected))
            if set(semantic_status)-{'succeeded','failed'} or set(native_status)-{'succeeded','failed'}:
                raise ValueError('New terminal status requires explicit review, not masking')
            summaries[skill].update(values)
            per_skill[skill] = dict(**values, body_Actor_activation_denominator=None,
                body_Actor_failure_count=None, L0_L1_L2_training_domain_qualification='NOT_REVIEWED_NOT_PREREGISTERED')
        error = result.get('error')
        if error is None:
            category = 'CHAIN_PASS_NOT_GENERAL_TASK_OR_ROBUSTNESS_SUCCESS'
        elif error.startswith('push_start_pose_timeout:settle'):
            category = 'PUSH_ENTRY_SETTLE_GATE_STOP_NO_ACTOR_FAILURE_INFERRED'
        elif error == 'reconciled_reference_FF_intersection_empty':
            category = 'PUSH_REFERENCE_UNLOAD_EXIT_GATE_STOP_NO_QP_SOLVER_OR_ACTOR_FAILURE_INFERRED'
        elif error == 'base_collision':
            category = 'RUNTIME_COLLISION_AFTER_CLIMB_ADMISSION_NO_CLIMB_TERMINAL'
            if per_skill['CLIMB']['native_option_admissions'] != 1 or per_skill['CLIMB']['native_terminal_succeeded']:
                raise ValueError('Collision stage evidence differs from declared summary')
        else:
            raise ValueError('Unreviewed historical failure, keep UNKNOWN: '+str(error))
        # Establish only timestamp ordering of observed same-run receipts, not a
        # trained-domain, hidden-state, reset-free or Actor-activation guarantee.
        predecessor = {}
        for previous, successor in [('NAV', 'PUSH'), ('PUSH', 'CLIMB')]:
            earlier = [semantic_terminals[key]['time_s'] for key in intents if intents[key] == previous and key in semantic_terminals]
            later = [x['receipt']['time_s'] for x in admissions.values() if x['option']['skill'] == successor]
            predecessor[successor] = bool(earlier and later and max(earlier) <= min(later))
        rows.append(dict(ordinal=ordinal, scope_id=scope, candidate_id=source['candidate_id'], source_program_sha256=source['program_sha256'],
            original_source_result_sha256=source['actual_result_sha256'], source_failure_category=category, per_skill=per_skill,
            predecessor_receipt_before_successor_admission=predecessor,
            literal_NAV_actor_named_events=audit['literal_NAV_actor_forward_event_count'],
            named_Actor_event_is_not_semantic_NAV_activation_denominator=True))
    if len(rows) != 24 or set(r['ordinal'] for r in rows) != set(range(1,25)):
        raise ValueError('No selective historical subset')
    stage_directory = root/'AINAV-DATA-CLIMB-PREPARATION-THREE-BRANCH-ACTUAL-20261114-v1'
    stage_release = read(stage_directory/'release.json', '4de5ca665d950c7d7663c722518675ab7c35c3a487140c8f3571261912fb45ce')
    stage = read(stage_directory/'actual-all-three-comparison.json', stage_release['files']['actual-all-three-comparison.json'])
    stage_rows = []
    for row in stage['rows']:
        known = row.get('failure_known_stages') or {}
        stage_rows.append(dict(candidate_id=row['candidate_id'], scope_id=row['scope_id'],
            collector_passed=row['literal_collector_passed'], original_error=row['original_error'],
            decision_to_READY_s=row['current_decision_to_READY_s'],
            decision_to_CLIMB_terminal_s=row['decision_to_CLIMB_receipt_s'],
            original_final_CLIMB_native_receipt_on_failure=known.get('original_final_CLIMB_native_receipt'),
            exact_Actor_activation_or_body_contact_cause=known.get('exact_Actor_activation_or_body_contact_cause')))
    return dict(schema='Data-retrospective-fixed24-three-skill-denominators-not-new-robustness-cohort-v1',
        historical_closed_main_scopes=24, original_own_zero_attempts=24,
        original_cohort_accounting=dict(main_task_sim_s=snapshot['closed_actual_main_commands']*.005,
            scope_sim_including_zero_and_aux_s=snapshot['closed_only_scope_sim_s'],
            scope_ledger_wall_s=snapshot['closed_only_scope_wall_s'],
            resource_censored_scopes=snapshot['closed_resource_censored'],
            all_usage_known=snapshot['closed_ledger_usage_all_known'],
            per_skill_exclusive_wall_or_Actor_cost=None, failed_elapsed_not_success_conditioned_cost=True,
            task_sim_from_original_command_count_times_original_005dt=True,
            not_pooled_with_StageB_D3_or_other_scopes=True),
        summaries={s:dict(summaries[s]) for s in SKILLS},
        source_failure_categories=dict(Counter(r['source_failure_category'] for r in rows)),
        predecessor_receipt_before_successor_admission_scopes={s:sum(r['predecessor_receipt_before_successor_admission'][s] for r in rows) for s in ('PUSH','CLIMB')},
        scopes_with_positive_literal_NAV_actor_named_event=sum(r['literal_NAV_actor_named_events']>0 for r in rows),
        zero_named_event_is_not_no_Actor_execution_proof=True,
        actual_body_Actor_activation_denominators={s:None for s in SKILLS},
        retrospective_level_candidates=dict(L0='UNKNOWN_ORIGINAL_TRAINING_ENTRY_NOT_CHECKED', L1='PUSH_AFTER_NAV_AND_CLIMB_AFTER_PUSH_CHAIN_RECORDS_NOT_QUALIFIED_SCREENING', L2='ORIGINAL_GEOMETRY_CONTEXT_PREPARATION_VARIATIONS_NOT_NEW_L2_PREREGISTRATION'),
        new_L0_L1_L2_screening=dict(registered_frozen_cases=0, zero_dispatches=0, main_dispatches=0, body_Actor_denominator=None, ninety_case_draft_not_dispatch_authority=True),
        independent_seen_DEV_preparation_reference_not_pooled=dict(scopes=3, observed_successes=stage['success_count'],
            observed_stop_deadline_without_CLIMB_terminal=stage['failure_or_non_success_count'], rows=stage_rows,
            retrospective_L2_like_offsets_not_new_qualified_L2=True, formal_skill_robustness_rate_claimed=False),
        one_original_TRAIN_ancestor_not_independent_validation=True, no_success_rate_or_retraining_decision_inferred=True,
        immutable_historical_purposes_labels_and_costs_preserved=True, model_input_fit_or_label_reassignment_allowed=False,
        no_new_Runtime_GPU_NVML_Actor_Renderer_physics_API_or_H_mutation=True, source_metadata_SHA256=inputs, rows=rows)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--enabled', action='store_true')
    parser.add_argument('--deliveries')
    parser.add_argument('--out')
    args = parser.parse_args()
    if args.enabled:
        value = derive(args.deliveries, enabled=True)
        with Path(args.out).open('x', encoding='utf-8') as out:
            json.dump(value, out, ensure_ascii=False, indent=2, allow_nan=False)
            out.write('\n')
