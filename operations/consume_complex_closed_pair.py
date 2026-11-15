#!/usr/bin/env python3
"""Read the frozen first T DEV pair after closure; never launch a native task.

Execute on46308. Hash released small members, verify original journal chains,
link the earlier actual-prefix proof, and distinguish installation/started from
terminal receipts. Stream/PD/RGB-pixel checks are CONSUMED from Data cold audits,
not independently recomputed here. No raw arrays or Actor observations exported.
"""
import argparse
import datetime as dt
import hashlib
import json
import math
import sys
from pathlib import Path


def need(condition, message):
    if not condition:
        raise ValueError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical_sha(value):
    return digest(json.dumps(value, sort_keys=True, ensure_ascii=False,
                             allow_nan=False, separators=(',', ':')).encode())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('protocol', 'expected-protocol-sha', 'a-release', 'a-release-sha',
                 'b-release', 'b-release-sha', 'prefix-report', 'prefix-report-sha', 'output'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
    pins = {}

    def read(path, expected=None):
        path = Path(path)
        need(path.is_file() and not path.is_symlink(), 'Explicit regular input: ' + str(path))
        raw = path.read_bytes()
        need(len(raw) < 16 * 1024**2, 'Small metadata or original journal only')
        value = digest(raw)
        need(expected is None or value == expected, 'SHA mismatch: ' + str(path))
        need(str(path) not in pins or pins[str(path)] == value, 'Input changed during read')
        pins[str(path)] = value
        return raw

    protocol = json.loads(read(args.protocol, args.expected_protocol_sha))
    need(protocol['schema'] == 'Data-T-COMPLEX-first-native-DEV-source-method-pair-v1', 'Exact pair protocol')
    prefix = json.loads(read(args.prefix_report, args.prefix_report_sha))
    need(prefix['protocol_sha256'] == args.expected_protocol_sha and
         prefix['predecision_capture_steps'] == 448 and
         prefix['first_public_observations_equal_except_storage_path'] is True and
         all(all(v.values()) for v in prefix['actual_capture_channel_checks'].values()), 'Prior actual prefix proof')
    expected_programs = {
        'A': '626400b87c001800da53c7bf6f4050e7421a2a86dcecbd9a8f2bce61f8f231df',
        'B': '0ba3839592bc733162a4d913dfff12de4e21147a6d1be0d4e2ca99b21cb34589',
    }
    arms = {}
    for arm in ('A', 'B'):
        release_path = Path(getattr(args, arm.lower() + '_release'))
        release = json.loads(read(release_path, getattr(args, arm.lower() + '_release_sha')))
        root = release_path.parent
        for rel, expected in release['files'].items():
            member = root / rel
            need(member.resolve().is_relative_to(root.resolve()), 'No member path escape')
            read(member, expected)
        result = json.loads(read(root / 'main/result.json', release['source_result_sha256']))
        ledger = json.loads(read(root / 'ledger.json'))
        cold = json.loads(read(root / 'actual-main-cold-audit.json'))
        expected_arm = protocol['arms'][arm]
        need(result['scope_id'] == ledger['scope_id'] == release['scope_id'] == expected_arm['scope_id'], 'Scope identity')
        need(result['program_sha256'] == ledger['program_sha256'] == release['program_sha256'] ==
             expected_programs[arm], 'Exact first DEV program identity')
        need(result['source_owner_commit'] == protocol['source_owner_commit'] and
             result['source_scene_sha256'] == protocol['scene_sha256'], 'Frozen source/scene identity')
        need(result['method'] == release['method'] == expected_arm['method'] and result['arm'] == arm, 'Method identity')
        need(result['phase'] == 'main' and result['status'] == 'FAILED_NO_RETRY' and
             result['passed'] is False and result['task_success'] is False and
             result['automatic_retry'] is False and result['training_allowed'] is False, 'Exact failed DEV pair; not a future trial reader')
        rows = ledger['rows']
        need(ledger['stopped'] is True and len(rows) == 2 and
             [r['phase'] for r in rows] == ['zero', 'main'] and
             all(r['closed'] is True and r['usage_known'] is True for r in rows), 'Closed original scope accounting')
        need(rows[1]['report_sha256'] == release['source_result_sha256'], 'Main ledger/result binding')
        read(root / 'zero/result.json', rows[0]['report_sha256'])
        need(cold['passed'] is True and cold['source_result_sha256'] == release['source_result_sha256'] and
             all(v is True for v in cold['checks'].values()), 'Data cold audit consumed, not re-executed')
        if arm == 'B':
            reference = json.loads(read(root / 'original-journal-remote-reference.json'))
            journal_path = Path(reference['path'])
            need(str(journal_path) == prefix['B_journal_prefix_not_terminal']['original_journal_path'], 'Original B path')
            raw = read(journal_path, reference['sha256'])
            need(len(raw) == reference['bytes'], 'Original journal byte count')
            old = prefix['B_journal_prefix_not_terminal']
            need(digest(raw[:old['prefix_bytes']]) == old['prefix_sha256'], 'Earlier B prefix retained verbatim')
        else:
            raw = read(root / 'main/events.jsonl')
        need(raw.endswith(b'\n'), 'Closed journal has no partial tail')
        previous = '0' * 64
        events = []
        for index, line in enumerate(raw.splitlines()):
            row = json.loads(line)
            claim = row.pop('sha256')
            need(row['sequence'] == index and row['previous_sha256'] == previous and
                 canonical_sha(row) == claim, 'Original journal chain')
            previous = claim
            events.append(row['payload'])
        journal = dict(rows=len(events), last_sha256=previous, valid=True)
        need(journal == cold['journal_chain'], 'Independent full-chain matches Data report')
        named = lambda name: [e for e in events if e.get('event') == name]
        decisions = named('reach_complex_public_decision')
        selected = named('reach_complex_semantic_intent_selected')
        installed = named('native_option_installed')
        terminal = [e for e in named('ainav_native_receipt')
                    if e['receipt']['status'] in ('succeeded', 'failed', 'hard_stop', 'budget_expired')]
        completed = named('completed_placement_boundary_latched')
        forwards = len(named('registered_NAV_actual_actor_forward'))
        need(len(decisions) == len(selected) == 1 and not terminal and not completed, 'Only one decision, no native terminal/reconstruction')
        if arm == 'B':
            bound = named('intent_native_execution_bound')
            need(len(bound) == len(installed) == 1 and
                 bound[0]['intent_sha256'] == selected[0]['intent_sha256'] and
                 bound[0]['native_option_sha256'] == installed[0]['option_sha256'] == prefix['B_original_native_option_sha256'], 'Actual native consumer binding')
            need(result['resource_censored'] is True and
                 result['error'] == 'Full-task owned wall watchdog, no retry' and
                 forwards == cold['actual_NAV_actor_forward_count'] == release['actual_NAV_actor_forward_count'], 'Actual B resource stop, not a skill terminal')
        else:
            need(not installed and result['resource_censored'] is False and
                 result['error'].startswith('ORIGINAL_INTENT_REJECTION:'), 'Actual A source refusal')
        total_sim = sum(r['sim_s'] for r in rows)
        wall = sum(r['wall_s'] for r in rows)
        highwater = max(r['output_highwater_bytes'] for r in rows)
        need(math.isclose(rows[1]['sim_s'], result['actual_main_world_sim_s'] +
                          result['actual_auxiliary_calibration']['sim_seconds'], abs_tol=1e-8), 'Task vs aux accounting')
        need(math.isclose(total_sim, release['actual_scope_including_zero_aux_sim_s'], abs_tol=1e-8) and
             wall == release['actual_scope_ledger_wall_s'] and highwater == release['actual_scope_output_highwater_bytes'], 'Released full cost')
        arms[arm] = dict(result_sha256=release['source_result_sha256'], status=result['status'],
            error=result['error'], resource_censored=result['resource_censored'], task_success=False,
            task_sim_s=result['actual_main_world_sim_s'], actual_command_steps=result['task_physics_steps'],
            scope_including_zero_aux_sim_s=total_sim, scope_ledger_wall_s=wall, scope_output_highwater_bytes=highwater,
            journal_chain=journal, algorithm_decisions=len(decisions), original_native_installs=len(installed),
            NAV_Actor_forward_events=forwards, native_terminal_receipts=terminal, task_reconstructions=len(completed),
            actual_first_decision=decisions[0], actual_first_selected_intent=selected[0],
            direct_HD_frames=release['direct_HD_raw_frames'], Data_nine_stream_audit_consumed=True,
            independent_NPZ_PD_RGB_recomputation=False)
    video = json.loads(read(Path(args.b_release).parent / 'closed-pair-direct-video-manifest.json'))
    need(video['pair_same_actual_sim_clock'] is True and
         video['no_new_model_Actor_Renderer_or_physics_calls'] is True and
         video['post_end_panel_is_black_explanatory_slate_not_frozen_or_fabricated_world'] is True, 'Video interpretation')
    for row in video['outputs'].values():
        read(row['path'], row['sha256'])
    for path, expected in pins.items():
        need(digest(Path(path).read_bytes()) == expected, 'Input changed before publication')
    report = dict(schema='Reach-independent-closed-T-first-DEV-pair-consumption-v1',
        at=dt.datetime.now().astimezone().isoformat(), reader_source_sha256=digest(Path(__file__).read_bytes()),
        protocol_sha256=args.expected_protocol_sha, arms=arms, source_pins=pins,
        independent_closed_journal_chains_verified=True, prior_actual_448step_prefix_proof_retained=True,
        direct_video_outputs_remote=video['outputs'], video_bytes_verified_not_decoded_by_Reach=True,
        video_role='COMPLETE_AVAILABLE_FAILED_CENSORED_EPISODES_NOT_FULL_TASK_SUCCESS',
        three_effective_choices_or_full_task_or_method_advantage_established=False,
        A_observability_confound_preserved=True, B_resource_censor_is_not_native_skill_or_search_budget_failure=True,
        source_throughput_cause_not_established=True, new_physics_Actor_Renderer_fit_dispatch=0,
        original_records_or_closed_caps_modified=False)
    with Path(args.output).open('x') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({k: {n: v[n] for n in ('status', 'resource_censored', 'task_sim_s', 'journal_chain',
        'algorithm_decisions', 'original_native_installs', 'native_terminal_receipts')} for k, v in arms.items()}))


if __name__ == '__main__':
    def fence(event, args):
        if event == 'import' and str(args[0]).split('.')[0] in ('torch', 'mujoco', 'onnxruntime', 'numpy'):
            raise RuntimeError('Metadata/journal-only consumption: no native/arrays')
        if event in ('subprocess.Popen', 'socket.connect', 'socket.bind', 'socket.getaddrinfo'):
            raise RuntimeError('No child process or network')
    sys.addaudithook(fence)
    main()
