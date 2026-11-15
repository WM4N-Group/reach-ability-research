#!/usr/bin/env python3
"""Read a successful closed bulk24 acquisition, not fit or score any model.

Accept exactly the original ordinal01 release and fixed closed ordinal02--24
release formats. Neither acceptance changes the prospective protocol or purpose.

The untouched original-cohort extractor still rejects this different release.
Reuse ONLY its public-observation 48-slot projection. Labels/clocks are derived
separately from original receipts, never supplied to that projection. Raw vectors
stay on46308; print only scalar coverage/clock facts. Failure/unreached attempts
remain in Data's denominator; this success reader must never fabricate their rows.
"""
import argparse
import datetime as dt
import hashlib
import importlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from operations.extract_new_critic_attempt import public_features_only
from research.task_conditioned_reachability.execution_preparation.public_prediction_features import physical_features
from research.task_conditioned_reachability.execution_preparation.successor_aware_choice import digest, need

PROTOCOL_SHA = '0f9e0e03a4cdf8263b1c69f69db9697968040023f42d4c1f383a320631d9e57e'
PURPOSE = 'NEW_PREREGISTERED_HIGH_LEVEL_SUCCESSOR_CRITIC'


def registration_gate(release, protocol, acquisition):
    """Pure schedule/purpose gate: does not promote this collection to fit."""
    schema = release.get('schema')
    need(schema in ('Data-bulk24-first-new-geometry-original-delivery-v1',
                    'Data-bulk24-fixed-closed-original-delivery-v2'),
         'Exact first/fixed-closed bulk24 release, not old DEV or arbitrary future schema')
    need(release.get('protocol_sha256') == acquisition.get('new_use_protocol_file_sha256') == PROTOCOL_SHA, 'Exact prospective bulk24 protocol')
    need(protocol.get('schema') == 'Reach-bulk24-prospective-new-purpose-collection-v1' and
         protocol.get('data_purpose') == acquisition.get('data_purpose') == PURPOSE, 'Prospective new-purpose acquisition')
    need(release.get('fit_allowed') is False and release.get('current_model_refit_allowed') is False
         and release.get('whole_package_model_input_allowed') is False
         and protocol.get('current_frozen_critic_refit_allowed') is False, 'No fit/whole-package permission')
    ordinal = release.get('ordinal')
    need(type(ordinal) is int and 1 <= ordinal <= len(protocol['attempt_schedule']) == 24, 'Fixed finite ordinal')
    need((schema == 'Data-bulk24-first-new-geometry-original-delivery-v1' and ordinal == 1) or
         (schema == 'Data-bulk24-fixed-closed-original-delivery-v2' and ordinal >= 2),
         'Exact original release format for this fixed ordinal')
    row = protocol['attempt_schedule'][ordinal - 1]
    for key in ('ordinal', 'attempt_key', 'split'):
        need(release.get(key) == acquisition.get(key) == row[key], 'Schedule drift: ' + key)
    for key in ('source_scene_sha256', 'condition_binding_sha256', 'scene_ancestry_key', 'preparation_payload'):
        need(acquisition.get(key) == row[key], 'New acquisition binding: ' + key)
    need(row['split'] == 'TRAIN' and protocol['scene_split_assignments'][row['source_scene_sha256']] == 'TRAIN', 'No heldout role promotion')
    need(row['scene_ancestry_key'] == '1245cf2a2c5ffa02a1cc7ae4de61fdd28f70df6eec5f0de5eb3a90a7f7f7d1a8', 'Existing full4 TRAIN ancestor, not independent family')
    return row


def semantic_success_gate(result):
    proof = result.get('exact_three_semantic_native_successes')
    need(isinstance(proof, dict) and proof.get('exact_requested_semantic_success_count') == 3 and
         proof.get('preparation_receipts_not_counted') is True, 'Structured exact three-request witness')
    requests = proof.get('requests', [])
    need(len(requests) == 3 and [r['request']['skill'] for r in requests] == ['NAV','PUSH','CLIMB'] and
         all(r['status'] == 'succeeded' for r in requests) and result.get('passed') is True and
         result.get('whole_task_success_claimed') is False, 'Successful requested chain, not whole-mission success')
    return requests


def correlate_semantic_successes(records, requests, journal_path):
    """Original helper's binding_ref is a JUDGE reference, not a bound row."""
    rows = {i:r['payload'] for i,r in enumerate(records,1)}
    for request in requests:
        ref_path, ref_line = request['binding_ref'].rsplit('#',1)
        need(ref_path == journal_path and int(ref_line) in rows, 'Original requested-skill judgment path')
        judge = rows[int(ref_line)]
        need(judge.get('intent_sha256') == request['intent_sha256'] and
             (judge.get('event') == 'skill_execution_judge_ready' or
              judge.get('event') == 'skill_execution_judgment' and judge.get('status') == 'READY'),
             'Actual original READY judgment, not a private pose fallback')
        bindings = [(i,r) for i,r in rows.items() if i > int(ref_line) and
            r.get('event') == 'intent_native_execution_bound' and r.get('execution_role') == 'interaction' and
            r.get('intent_sha256') == request['intent_sha256'] and r.get('native_option_sha256') == request['native_option_sha256']]
        need(len(bindings) == 1, 'Original requested-skill unique actual binding')
        bi,bound = bindings[0]
        need(bound.get('judgment_ref') == request['binding_ref'] and
             bound['native_option']['skill'] == request['request']['skill'], 'Original requested-skill native binding')
        terminals = [r for i,r in rows.items() if i > bi and r.get('event') == 'intent_actual_native_outcome' and
            r.get('execution_role') == 'interaction' and r.get('intent_sha256') == request['intent_sha256'] and
            r.get('native_option_sha256') == request['native_option_sha256']]
        need(len(terminals) == 1 and terminals[0]['intent_succeeded'] is True and
             terminals[0]['receipt']['status'] == 'succeeded' and
             terminals[0]['receipt']['option_sha256'] == request['native_option_sha256'], 'Literal requested-skill terminal receipt')



def requested_climb_endpoint(rows, intent, journal_path, result, *, allow_native_hard_stop=False):
    """Audit-only exact READY -> requested CLIMB terminal, never impute success cost.

    An uncaught native hard stop may have no failed receipt. Retain that literal
    fact rather than creating one or relabelling failure duration as success time.
    Private failure-event metrics are not read; only outcome error/clock binds.
    """
    ready = [(i,r) for i,r in rows.items() if r['payload'].get('event') == 'skill_execution_judgment'
        and r['payload'].get('intent_sha256') == intent and r['payload'].get('status') == 'READY'
        and r['payload'].get('spec',{}).get('skill') == 'CLIMB'
        and r['payload']['spec'].get('target_ref') == 'cuboid-2:upper-entry']
    need(len(ready) == 1, 'Exact same-intent CLIMB READY, never preparation receipt as READY')
    ri, rr = ready[0]
    climbs = [(i,r) for i,r in rows.items() if i > ri
        and r['payload'].get('event') == 'intent_native_execution_bound'
        and r['payload'].get('intent_sha256') == intent and r['payload'].get('execution_role') == 'interaction'
        and r['payload'].get('native_option',{}).get('skill') == 'CLIMB'
        and r['payload'].get('judgment_ref') == journal_path+'#'+str(ri)]
    need(len(climbs) == 1, 'Exact requested CLIMB bound to that READY judgment')
    bi, br = climbs[0]; native = br['payload']['native_option_sha256']
    need(br['payload']['native_option'].get('target_ref') == rr['payload']['spec']['target_ref'],
         'Same exact requested target across READY and native binding')
    outcomes = [(i,r) for i,r in rows.items() if i > bi
        and r['payload'].get('event') == 'intent_actual_native_outcome'
        and r['payload'].get('intent_sha256') == intent and r['payload'].get('execution_role') == 'interaction'
        and r['payload'].get('native_option_sha256') == native]
    ready_time = rr['payload']['state']['time_s']
    from research.task_conditioned_reachability.execution_preparation.successor_aware_choice import number
    need(number(ready_time) and ready_time >= 0, 'Actual finite READY clock')
    if result.get('passed') is True:
        need(len(outcomes) == 1, 'Literal single requested interaction terminal')
        oi, outcome = outcomes[0]; payload = outcome['payload']; receipt = payload['receipt']
        need(payload.get('intent_succeeded') is True and receipt.get('status') == 'succeeded'
             and receipt.get('option_sha256') == native, 'Original succeeded receipt for exact requested CLIMB')
        end = receipt['time_s']
        witness = dict(endpoint_kind='LITERAL_REQUESTED_CLIMB_SUCCEEDED', native_receipt_status='succeeded',
            outcome_sha256=outcome['sha256'], native_hard_stop_sha256=None, failure_clock_sha256=None,
            native_start_sha256=None, source_error=None)
    else:
        need(allow_native_hard_stop is True and result.get('passed') is False
             and result.get('error_class') == 'RuntimeError' and not outcomes,
             'Failure requires explicit original native hard-stop route, not timeout/absent terminal as failed receipt')
        error = result.get('error')
        need(type(error) is str and error and result.get('whole_task_success_claimed') is False,
             'Literal closed native failure, never whole-task success')
        starts = [(i,r) for i,r in rows.items() if i > bi and r['payload'].get('event') == 'ainav_native_receipt'
            and r['payload'].get('receipt',{}).get('option_sha256') == native
            and r['payload']['receipt'].get('status') == 'started']
        stops = [(i,r) for i,r in rows.items() if i > bi and r['payload'].get('event') == 'ainav_chain_hard_stop'
            and r['payload'].get('error') == error and r['payload'].get('native_safety_handling_required') is True
            and r['payload'].get('automatic_retry') is False]
        failures = [(i,r) for i,r in rows.items() if i > bi and r['payload'].get('event') == 'private_terminal_controller_failure'
            and r['payload'].get('error') == error and r['payload'].get('model_input') is False
            and r['payload'].get('live_state_written') is False]
        need(len(starts) == len(stops) == len(failures) == 1, 'Exact original started CLIMB/hard-stop/failure-clock witnesses')
        si, sr = starts[0]; hi, hr = stops[0]; fi, fr = failures[0]
        need(bi < si < hi < fi, 'Original native started before hard stop and failure clock')
        intervening = [r for i,r in rows.items() if si < i < hi and r['payload'].get('event') == 'native_option_installed']
        need(not intervening, 'No later native owner installed between CLIMB start and hard stop')
        end = fr['payload']['time_s']
        need(number(end) and end == result.get('actual_main_world_sim_s'), 'Original closed result clock equals literal failure clock')
        need(number(sr['payload']['receipt'].get('time_s')) and
             ready_time <= sr['payload']['receipt']['time_s'] <= end, 'Finite causal started receipt clock')
        witness = dict(endpoint_kind='LITERAL_CHAIN_HARD_STOP_DURING_STARTED_CLIMB_NO_TERMINAL_RECEIPT',
            native_receipt_status=None, outcome_sha256=None, native_hard_stop_sha256=hr['sha256'],
            failure_clock_sha256=fr['sha256'], native_start_sha256=sr['sha256'], source_error=error)
    need(number(end) and ready_time <= end, 'Nested actual endpoint clocks')
    return dict(witness, ready_time_s=ready_time, end_time_s=end, READY_sha256=rr['sha256'],
                binding_sha256=br['sha256'], READY_line=ri, CLIMB_binding_line=bi,
                native_option_sha256=native)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('release-root', 'expected-release-sha', 'source-root', 'TRAIN-root', 'expected-TRAIN-release-sha', 'output'):
        p.add_argument('--' + name, required=True)
    p.add_argument('--include-native-hard-stop', action='store_true',
                   help='Audit exact failed started-CLIMB hard stop; no success-cost imputation')
    a = p.parse_args(); pins = {}
    sha = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
    def read(path, expected=None):
        path = Path(path)
        need(path.is_file() and not path.is_symlink(), 'Explicit regular input')
        value = sha(path)
        need(expected is None or value == expected, 'SHA mismatch: ' + str(path))
        need(str(path) not in pins or pins[str(path)] == value, 'Input drift')
        pins[str(path)] = value
        return json.loads(path.read_bytes())
    root = Path(a.release_root).resolve(strict=True)
    release = read(root / 'release.json', a.expected_release_sha)
    for rel, expected in release['files'].items():
        path = root / rel
        need(not Path(rel).is_absolute() and '..' not in Path(rel).parts and
             not path.is_symlink() and path.resolve().is_relative_to(root), 'Regular released member')
        need(sha(path) == expected, 'Released member SHA: ' + rel); pins[str(path)] = expected
    protocol = read(root / 'protocol/BULK24_COLLECTION_PROTOCOL.json', PROTOCOL_SHA)
    acquisition = read(root / 'protocol/new-purpose-acquisition-manifest.json')
    scheduled = registration_gate(release, protocol, acquisition)
    freeze = read(root / 'protocol/program-freeze.json', release['program_sha256'])
    result = read(root / 'evidence/main-result.json', release['actual_summary']['source_result_sha256'])
    ledger = read(root / 'evidence/ledger.json'); cold = read(root / 'evidence/actual-main-cold-audit-v2.json')
    need(freeze['scope_id'] == result['scope_id'] == ledger['scope_id'] == release['scope_id'] and
         ledger['program_sha256'] == release['program_sha256'] and all(r['closed'] and r['usage_known'] for r in ledger['rows']), 'Closed exact physical program')
    need(len(ledger['rows']) == 2 and ledger['rows'][1]['report_sha256'] == release['actual_summary']['source_result_sha256'], 'One zero/main; closed ledger result')
    need(result['new_use_protocol_sha256'] == PROTOCOL_SHA and result['source_scene_sha256'] == scheduled['source_scene_sha256'], 'Actual new-use native source')
    passed = result.get('passed') is True
    need(passed or a.include_native_hard_stop and result.get('passed') is False,
         'Default reader still requires original success; native hard-stop analysis is explicit')
    semantic_requests = semantic_success_gate(result) if passed else None
    need(cold['passed'] is True and cold['source_result_sha256'] == release['actual_summary']['source_result_sha256']
         and all(cold['checks'].values()), 'Data cold checks consumed, not re-run')
    need(dt.datetime.fromisoformat(protocol['registered_at']) <= dt.datetime.fromisoformat(freeze['at']) <
         dt.datetime.fromisoformat(release['at']), 'Protocol frozen before actual program publication')
    source = Path(a.source_root).resolve(strict=True)
    api = source.parent / 'climb_preparation_candidates.py'
    for path in (source / 'ainav/contracts.py', source / 'ainav/evidence.py', api):
        need(sha(path) == freeze['files'][str(path)], 'Exact original public contract/API'); pins[str(path)] = sha(path)
    need(sha(api) == protocol['source_binding']['candidate_api_sha256'], 'Same finite candidate API')
    feature_source = Path(physical_features.__code__.co_filename).resolve()
    need(sha(feature_source) == protocol['feature_extractor_sha256'], 'Unchanged prospective 48-slot projection'); pins[str(feature_source)] = sha(feature_source)
    pins[str(Path(public_features_only.__code__.co_filename).resolve())] = sha(public_features_only.__code__.co_filename)
    sys.path[:0] = [str(source), str(source.parent)]
    contracts = importlib.import_module('ainav.contracts'); evidence = importlib.import_module('ainav.evidence')
    candidates = importlib.import_module('climb_preparation_candidates')
    need(Path(contracts.__file__).resolve() == source / 'ainav/contracts.py' and
         Path(evidence.__file__).resolve() == source / 'ainav/evidence.py' and
         Path(candidates.__file__).resolve() == api, 'Exact source namespace')
    ref = read(root / 'original-journal-remote-reference.json'); journal = Path(ref['path'])
    need(sha(journal) == ref['sha256'], 'Original complete journal SHA'); pins[str(journal)] = ref['sha256']
    chain = evidence.verify(journal); need(chain == cold['journal_chain'] == ref['verified_chain'], 'Independent complete original journal chain')
    records = [json.loads(line) for line in journal.read_text().splitlines()]
    rows = {i:r for i,r in enumerate(records, 1)}
    if passed: correlate_semantic_successes(records, semantic_requests, str(journal))
    else: need(cold.get('source_resource_censored') is False and cold.get('source_result_passed') is False,
               'Original native failure, not resource censor relabelled as negative successor')
    judgments = [(i,r) for i,r in rows.items() if r['payload'].get('event') == 'skill_execution_judgment'
        and r['payload'].get('spec',{}).get('skill') == 'CLIMB' and r['payload'].get('spec',{}).get('target_ref') == 'cuboid-2:upper-entry']
    need(judgments and judgments[0][1]['payload']['status'] == 'PREPARE', 'Actual first PREPARE, no nearest/READY substitution')
    ji,jr = judgments[0]; intent = jr['payload']['intent_sha256']; clock = jr['payload']['state']['time_s']
    bindings = [(i,r) for i,r in rows.items() if i > ji and r['payload'].get('event') == 'intent_native_execution_bound'
        and r['payload'].get('intent_sha256') == intent and r['payload'].get('execution_role') == 'preparation'
        and r['payload']['judgment_ref'] == str(journal)+'#'+str(ji)]
    need(len(bindings) == 1, 'Exact first PREPARE preparation binding'); bi,br = bindings[0]; bound = br['payload']
    matches = []
    for path in (root/'public').glob('intent-observation-*.json'):
        obs = read(path)
        if contracts.Observation.create(obs).sha256 == bound['physical_observation_sha256']: matches.append((path,obs))
    need(len(matches) == 1 and matches[0][1]['time_s'] == clock, 'Unique original causal public query')
    query,observation = matches[0]
    features,geometry = public_features_only(observation, scheduled['candidate_id'], candidates, protocol['feature_profile'], clock)
    proposals = [(i,r) for i,r in rows.items() if ji < i < bi and r['payload'].get('event') == 'ainav_selected_CLIMB_preparation_NAV_goal_proposed' and r['payload'].get('intent_sha256') == intent]
    need(len(proposals) == 1, 'Original proposal before original native binding'); pi,pr = proposals[0]; proposed = pr['payload']; option = bound['native_option']; params = dict(option['parameters'])
    need(proposed['selection']['candidate_id'] == scheduled['candidate_id'] and proposed['original_CLIMB_approach_xy'] == geometry['original_CLIMB_reference_xy']
         and proposed['NAV_goal_xy'] == geometry['NAV_goal_xy'] == [params['goal_world_x_m'],params['goal_world_y_m']]
         and option['skill'] == 'NAV' and option['target_ref'] == 'cuboid-2:upper-entry' and params['surface_height_m'] == 0., 'Assigned public candidate actually consumed')
    installed = [r for i,r in rows.items() if i > bi and r['payload'].get('event') == 'native_option_installed' and r['payload'].get('option_sha256') == bound['native_option_sha256']]
    need(len(installed) == 1 and installed[0]['payload']['physical_command_already_issued'] is False, 'Install-before-command causal boundary')
    starts = [r for i,r in rows.items() if i > bi and r['payload'].get('event') == 'ainav_native_receipt'
        and r['payload'].get('receipt',{}).get('option_sha256') == bound['native_option_sha256'] and r['payload']['receipt']['status'] == 'started']
    need(len(starts) == 1 and starts[0]['payload']['receipt']['time_s'] >= clock, 'Actual candidate start follows feature clock')
    endpoint = requested_climb_endpoint(rows, intent, str(journal), result,
        allow_native_hard_stop=a.include_native_hard_stop)
    ready_time = endpoint['ready_time_s']; end = endpoint['end_time_s']
    need(clock <= ready_time <= end, 'Causal nested endpoint clocks')
    train_root = Path(a.TRAIN_root); train_release = read(train_root/'TRAIN_GATE_AND_FIT_RELEASE.json', a.expected_TRAIN_release_sha)
    train = read(train_root/'CLOSED_TRAIN_ONLY_DATASET.json', train_release['files']['CLOSED_TRAIN_ONLY_DATASET.json'])
    need(len(train['rows']) == 6 and train['feature_profile_sha256'] == protocol['feature_profile_sha256'] and
         train['feature_extractor_sha256'] == protocol['feature_extractor_sha256'], 'Same frozen feature view, original TRAIN six only, no heldout read')
    feature_hash = digest(features); state_hash = digest(features[2:])
    duplicates = [r['sample_id'] for r in train['rows'] if digest(r['physical_features']) == feature_hash]
    state_duplicates = [r['sample_id'] for r in train['rows'] if digest(r['physical_features'][2:]) == state_hash]
    for path,h in pins.items(): need(sha(path) == h, 'Input drift after read')
    scalar = dict(status='ACTUAL_BULK24_PUBLIC_BOUNDARY_MEASURED_NOT_FIT',ordinal=scheduled['ordinal'],attempt_key=scheduled['attempt_key'],
        group_id=scheduled['group_id'],prefix_side=scheduled['prefix_side'],candidate_id=scheduled['candidate_id'],split='TRAIN',
        new_geometry_definition_sha256=scheduled['source_scene_sha256'],existing_TRAIN_ancestor=scheduled['scene_ancestry_key'],
        first_PREPARE_time_s=clock,current_READY_s=ready_time-clock,
        full_requested_CLIMB_success_s=end-clock if passed else None,
        decision_to_native_hard_stop_s=None if passed else end-clock,
        READY_to_native_hard_stop_s=None if passed else end-ready_time,
        source_result_passed=passed,literal_endpoint=endpoint['endpoint_kind'],
        literal_CLIMB_terminal_receipt_status=endpoint['native_receipt_status'],
        task_sim_s=result['actual_main_world_sim_s'],feature_slots=len(features),feature_age_s=features[-1],
        full48_feature_sha256=feature_hash,state46_sha256=state_hash,exact_full48_matches_in_frozen_TRAIN=len(duplicates),
        exact_state46_matches_in_frozen_TRAIN=len(state_duplicates),journal_chain=chain,
        scope_including_zero_aux_sim_s=sum(r['sim_s'] for r in ledger['rows']),scope_ledger_wall_s=sum(r['wall_s'] for r in ledger['rows']),
        scope_output_highwater_bytes=max(r['output_highwater_bytes'] for r in ledger['rows']),direct_raw_resolution_px=cold['direct_raw_resolution_px'],
        not_HD=True,fit_or_current_model_refit_allowed=False,model_scored_or_calibrated=False,new_independent_heldout_families=0,
        three_candidates_measured_for_this_context=False,task_or_method_gain_claimed=False)
    report = dict(at=dt.datetime.now().astimezone().isoformat(),role='NEW_PREREGISTERED_BULK24_MEASUREMENT_NOT_TRAINING_DATASET_OR_FIT',
        reader_sha256=sha(__file__),scalar=scalar,physical_features=features,geometry_from_original_public_anchor=geometry,
        causal_binding=dict(judgment_line=ji,judgment_sha256=jr['sha256'],proposal_sha256=pr['sha256'],binding_sha256=br['sha256'],
            physical_observation_sha256=bound['physical_observation_sha256'],query_file=str(query),
            native_install_sha256=installed[0]['sha256'],native_start_sha256=starts[0]['sha256'],native_start_time_s=starts[0]['payload']['receipt']['time_s'],READY_sha256=endpoint['READY_sha256'],outcome_sha256=endpoint['outcome_sha256'],
            requested_CLIMB_endpoint=endpoint),
        source_pins=pins,baseline_exact_feature_match_sample_ids=duplicates,baseline_exact_state_match_sample_ids=state_duplicates,
        novelty_does_not_establish_learnability_or_independent_scene=True,new_physics_Actor_Renderer_fit_or_critic_predictions=0)
    with Path(a.output).open('x') as f: json.dump(report,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
    print(json.dumps(scalar,ensure_ascii=False,indent=2))


if __name__ == '__main__':
    def fence(event, args):
        if event == 'import' and str(args[0]).split('.')[0] in ('torch','mujoco','onnxruntime'):
            raise RuntimeError('No native/Actor imports')
        if event in ('subprocess.Popen','socket.connect','socket.bind','socket.getaddrinfo'):
            raise RuntimeError('No child process or network')
    sys.addaudithook(fence)
    main()
