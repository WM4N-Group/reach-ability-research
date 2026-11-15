#!/usr/bin/env python3
"""Extract ONE closed, prospectively registered critic acquisition on 46308.

Not a collector, fit permit or DEV-reader role override. Feature projection sees
only the original public observation and fixed public candidate. Journal/private
execution facts are read separately for clocks, literal labels and provenance.
Unknown postdecision failures remain UNKNOWN until their original witness is
qualified; no inference from result.passed=False or an exception's text alone.
"""
import argparse
import datetime as dt
import hashlib
import importlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from research.task_conditioned_reachability.execution_preparation.successor_aware_choice import digest, need, number
from research.task_conditioned_reachability.execution_preparation.public_preparation_selector import (
    PublicReference, build_problem, with_public_observation)
from research.task_conditioned_reachability.execution_preparation.public_prediction_features import physical_features
from research.task_conditioned_reachability.execution_preparation.successor_critic import PURPOSE, timestamp


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def public_features_only(observation, candidate_id, candidate_api, profile, now_s):
    """No result, judgment, private state, source config or labels in this call."""
    anchors = [a for a in observation['declared_map']['anchors']
               if a.get('target_ref') == 'cuboid-2:upper-entry']
    need(len(anchors) == 1, 'One original public registered CLIMB anchor')
    xyz = anchors[0]['position_xyz_m']
    need(len(xyz) == 3 and xyz[2] == 0., 'Original ground-source public reference only')
    problem = build_problem(PublicReference('cuboid-2:upper-entry', tuple(xyz[:2]), 0., True,
        'ORIGINAL_CAUSAL_PUBLIC_QUERY'), public_candidates=candidate_api.public_candidates)
    # ONLINE_PUBLIC means original visibility at the RECORDED causal clock, not
    # a live capture now or permission to rejuvenate old DEV. Purpose is checked
    # before this function is reached; no runtime/binding is constructed.
    problem = with_public_observation(problem, observation, now_s=now_s, source_role='ONLINE_PUBLIC')
    candidate = next(c for c in problem.domain.candidates if c.candidate_id == candidate_id)
    result = physical_features(problem, candidate)
    need(all(result.known_mask), 'Missing physical slots: keep missing, no fabricated model row')
    need(list(result.names) == profile['names'] and list(result.units) == profile['units']
         and list(result.frames) == profile['frames'], 'Exact preregistered 48-slot view')
    geometry = next(g for g in problem.geometry if g['candidate_id'] == candidate_id)
    return list(result.values), geometry


def extract(release_root, expected_release_sha, source_root):
    root = Path(release_root).resolve(strict=True)
    release_file = root / 'release.json'
    need(sha(release_file) == expected_release_sha, 'Exact original Data release SHA')
    release = read(release_file)
    need(release.get('schema') == 'Data-NEW-purpose-finite-critic-acquisition-original-release-v1'
         and release.get('data_purpose') == PURPOSE and release.get('not_relabelled_historical_DEV') is True,
         'NEW-purpose acquisition only; old DEV release cannot be relabelled')
    need(release.get('fit_allowed_by_this_release') is False, 'Release alone is never a fit permit')
    pins = {str(release_file): expected_release_sha}
    for name, expected in release['files'].items():
        path = root / name
        need(not Path(name).is_absolute() and '..' not in Path(name).parts
             and not path.is_symlink() and path.resolve().is_relative_to(root), 'Regular released member only')
        need(sha(path) == expected, 'Released member drift: ' + name)
        pins[str(path)] = expected
    protocol = read(root / 'protocol/FINITE_COHORT_PROTOCOL.json')
    collection_sha = sha(root / 'protocol/FINITE_COHORT_PROTOCOL.json')
    need(collection_sha == release['collection_protocol_file_sha256'], 'Same original frozen collection protocol')
    need(protocol['data_purpose'] == PURPOSE and protocol['qualified_entry_condition_family'] is False,
         'Immutable prospective collection protocol, not a retroactive fit permit')
    acquisition = read(root / 'protocol/new-purpose-acquisition-manifest.json')
    plan = read(root / 'protocol/preconstruction-plan.json')
    freeze = read(root / 'protocol/program-freeze.json')
    need(sha(root / 'protocol/program-freeze.json') == release['program_sha256'], 'Exact new physical program')
    scheduled = protocol['attempt_schedule'][release['ordinal'] - 1]
    for key in ('attempt_key', 'ordinal', 'split', 'source_scene_sha256', 'condition_binding_sha256', 'preparation_payload'):
        need(plan[key] == acquisition[key] == scheduled[key], 'Same fixed schedule field: ' + key)
    need(plan['new_use_protocol_file_sha256'] == acquisition['new_use_protocol_file_sha256'] == collection_sha
         and plan['data_purpose'] == acquisition['data_purpose'] == PURPOSE,
         'Future acquisition purpose, not old DEV flags renamed')
    need(plan['scope_id'] == freeze['scope_id'] == release['scope_id'], 'Same fresh physical scope')
    need(protocol['scene_split_assignments'][plan['source_scene_sha256']] == plan['split'], 'Whole-scene split')
    source = Path(source_root).resolve(strict=True)
    # Check the exact actual verifier/Observation and the original candidate API,
    # not a new host adapter or all SDK/weights. No native module is imported.
    for rel in ('ainav/contracts.py', 'ainav/evidence.py'):
        path = source / rel
        need(str(path) in freeze['files'] and sha(path) == freeze['files'][str(path)], 'Exact loaded public source ' + rel)
        pins[str(path)] = sha(path)
    api_path = source.parent / 'climb_preparation_candidates.py'
    need(sha(api_path) == protocol['source_binding']['candidate_api_sha256']
         == freeze['files'][str(api_path)], 'Same original finite candidate API')
    pins[str(api_path)] = sha(api_path)
    sys.path.insert(0, str(source))
    sys.path.insert(0, str(source.parent))
    contracts = importlib.import_module('ainav.contracts')
    evidence = importlib.import_module('ainav.evidence')
    candidate_api = importlib.import_module('climb_preparation_candidates')
    for module, expected in ((contracts, source / 'ainav/contracts.py'), (evidence, source / 'ainav/evidence.py'),
                             (candidate_api, api_path)):
        need(Path(module.__file__).resolve() == expected, 'Exact source namespace, no earlier cached owner')
    extractor = Path(physical_features.__code__.co_filename).resolve()
    need(sha(extractor) == protocol['feature_extractor_sha256'], 'Existing frozen physical extractor')
    pins[str(extractor)] = sha(extractor)
    result = read(root / 'evidence/main-result.json')
    cold = read(root / 'evidence/main-cold.json')
    ledger = read(root / 'evidence/scope-ledger.json')
    need(result['program_sha256'] == release['program_sha256'] and result['scope_id'] == release['scope_id'], 'New result identity')
    need(result['new_acquisition_data_purpose'] == PURPOSE and result['new_acquisition_split'] == plan['split']
         and result['new_use_protocol_sha256'] == collection_sha, 'Native worker declares new acquisition role')
    need(cold['all_stream_checks_passed'] and all(cold['checks'].values()), 'Original cold stream/closure integrity')
    need(all(r['closed'] for r in ledger['rows']), 'Closed actual attempt, not an in-progress ledger snapshot')
    known_cost = all(r['usage_known'] for r in ledger['rows'])
    total_sim = sum(r['sim_s'] for r in ledger['rows']) if known_cost else None
    # Original paths are bound by the release's source inventory, not guessed by
    # scope name, fixed query number, latest_public or nearest acquisition time.
    originals = dict(release['source_original_file_pins'])
    # The publication deliberately indexes rather than copies the large journal.
    # Its original path/SHA are in the SHA-pinned cold report, also pinned at the
    # release top level. Do not assume every raw source is a copied member.
    for path, expected in cold['raw_source_SHA'].items():
        need(path not in originals or originals[path] == expected, 'Consistent raw source pins')
        originals[path] = expected
    result_paths = [p for p in originals if p.endswith('/main/result.json')]
    journal_paths = [p for p in originals if p.endswith('/main/events.jsonl')]
    need(len(result_paths) == len(journal_paths) == 1, 'Exact raw result and journal members')
    run = Path(result_paths[0]).parent
    for path, expected in ((result_paths[0], release['source_result_sha256']),
                           (journal_paths[0], release['source_journal_sha256'])):
        need(originals[path] == sha(path) == expected, 'Original raw execution source drift')
        pins[path] = expected
    evidence.verify(Path(journal_paths[0]))
    records = [json.loads(line) for line in Path(journal_paths[0]).read_text().splitlines()]
    by_line = {i: r for i, r in enumerate(records, 1)}
    plan_paths = [p for p in freeze['files'] if p.endswith('/preconstruction-plan.json')]
    need(len(plan_paths) == 1, 'One exact new owner plan')
    manifest_root = Path(plan_paths[0]).parent
    need(sha(plan_paths[0]) == sha(root / 'protocol/preconstruction-plan.json'), 'Original frozen owner plan bytes')
    dispatch_path, close_path = manifest_root / 'CAS-main.json', manifest_root / 'CAS-close.json'
    dispatch, close = read(dispatch_path), read(close_path)
    need(dispatch['action'] == 'main' and close['action'] == 'close' and close['active'] is False
         and dispatch['program_sha256'] == close['program_sha256'] == release['program_sha256'], 'New dispatched and CAS-closed session')
    registered, dispatched, closed = map(timestamp, (protocol['registered_at'], dispatch['at'], close['at']))
    need(registered <= dispatched <= closed <= dt.datetime.now(dt.timezone.utc), 'Fresh actual post-registration acquisition session')
    pins[str(dispatch_path)], pins[str(close_path)] = sha(dispatch_path), sha(close_path)
    common = dict(scope_id=result['scope_id'], data_purpose=PURPOSE, old_audit_ancestor=False,
        source_result_sha256=release['source_result_sha256'], source_journal_sha256=release['source_journal_sha256'],
        condition_binding_sha256=plan['condition_binding_sha256'], source_scene_sha256=plan['source_scene_sha256'],
        split=plan['split'], attempt_key=plan['attempt_key'], candidate_id=plan['preparation_payload']['candidate_id'],
        new_use_protocol_file_sha256=collection_sha,
        captured_at=dispatch['at'], capture_clock_semantics='ACTUAL_CAPTURE_SESSION_DISPATCH_UTC_NOT_FRAME_WALL_TIME',
        session_closed_at=close['at'], spent_sim_s=total_sim)
    inventory = dict(common, source_chain_passed=result['passed'], literal_status=result['status'], error=result.get('error'),
        scope_wall_s=sum(r['wall_s'] for r in ledger['rows']) if known_cost else None,
        scope_highwater_bytes=max(r['output_highwater_bytes'] for r in ledger['rows']), usage_known=known_cost,
        main_sim_s=result.get('actual_main_world_sim_s'), resource_censored=result.get('resource_censored', False))
    judgments = [(i, r) for i, r in by_line.items() if r['payload'].get('event') == 'skill_execution_judgment'
                 and r['payload'].get('spec', {}).get('skill') == 'CLIMB'
                 and r['payload'].get('spec', {}).get('target_ref') == 'cuboid-2:upper-entry']
    out = dict(at=dt.datetime.now().astimezone().isoformat(), role='NEW_PURPOSE_EXTRACTED_ATTEMPT_NOT_BATCH_FIT_PERMISSION',
        collection_protocol_file_sha256=collection_sha, source_release_sha256=expected_release_sha,
        inventory=inventory, sample=None, unreached_decision_attempt=None,
        fit_allowed=False, complete_TRAIN_gate_pending=True, independent_scene_count_added=0,
        feature_profile_sha256=protocol['feature_profile_sha256'], feature_extractor_sha256=sha(extractor),
        source_pins=pins, actual_research_model_fits=0, new_physics_or_capture=False)
    if not judgments or judgments[0][1]['payload']['status'] != 'PREPARE':
        inventory.update(decision_reached=False, physical_features=None,
            first_judgment_status=None if not judgments else judgments[0][1]['payload']['status'])
        out.update(status='NO_PROTOCOL_PREPARE_DECISION_NO_SUCCESSOR_ROW', unreached_decision_attempt=dict(common,
            decision_reached=False, physical_features=None, actual_chain_outcome=result['status']))
    else:
        ji, jr = judgments[0]
        j = jr['payload']; intent = j['intent_sha256']; time_s = j['state']['time_s']
        inventory.update(decision_reached=True, first_PREPARE_time_s=time_s)
        bindings = [(i, r) for i, r in by_line.items() if r['payload'].get('event') == 'intent_native_execution_bound'
                    and r['payload'].get('intent_sha256') == intent and r['payload'].get('execution_role') == 'preparation'
                    and r['payload'].get('judgment_ref') == str(run / 'events.jsonl') + '#' + str(ji)]
        need(len(bindings) == 1, 'Exact first judgment-to-preparation binding missing; no substitute row')
        bi, br = bindings[0]; bound = br['payload']
        need(ji < bi, 'Judgment precedes actual preparation dispatch')
        installed = [(i,r) for i,r in by_line.items() if i>bi and
                     r['payload'].get('event')=='native_option_installed' and
                     r['payload'].get('option_sha256')==bound['native_option_sha256']]
        need(len(installed)==1 and installed[0][1]['payload'].get('physical_command_already_issued') is False,
             'Original native install still precedes any selected-child physical command')
        starts = [(i,r) for i,r in by_line.items() if i>bi and
                  r['payload'].get('event')=='ainav_native_receipt' and
                  r['payload'].get('receipt',{}).get('option_sha256')==bound['native_option_sha256'] and
                  r['payload'].get('receipt',{}).get('status')=='started']
        need(not starts or starts[0][1]['payload']['receipt']['time_s']>=time_s,
             'Recorded physical candidate execution cannot precede the feature clock')
        matches = []
        for path_str, expected in originals.items():
            path = Path(path_str)
            if path.parent == run and path.name.startswith('intent-observation-'):
                need(sha(path) == expected, 'Original actual public query drift')
                value = read(path)
                if contracts.Observation.create(value).sha256 == bound['physical_observation_sha256']:
                    matches.append((path, value))
        need(len(matches) == 1, 'Unique exact original Host observation, not fixed frame or nearest')
        query_path, observation = matches[0]
        need(observation['time_s'] == time_s, 'Same actual PREPARE feature clock')
        features, geometry = public_features_only(observation, common['candidate_id'], candidate_api,
            protocol['feature_profile'], time_s)
        # Verify assigned public offsets reached BOTH the original proposal and
        # actual native child; policy booleans/labels alone are not consumption.
        proposals = [(i, r) for i, r in by_line.items() if r['payload'].get('event') ==
                     'ainav_selected_CLIMB_preparation_NAV_goal_proposed' and r['payload'].get('intent_sha256') == intent
                     and ji < i < bi]
        need(len(proposals) == 1, 'One original candidate proposal between judgment and binding')
        pi, pr = proposals[0]; proposal = pr['payload']; option = bound['native_option']; params = dict(option['parameters'])
        need(proposal['selection'] == {'candidate_id':common['candidate_id'], 'target_ref':'cuboid-2:upper-entry'}
             and proposal['original_CLIMB_approach_xy'] == geometry['original_CLIMB_reference_xy']
             and proposal['NAV_goal_xy'] == geometry['NAV_goal_xy']
             and [params['goal_world_x_m'],params['goal_world_y_m']] == geometry['NAV_goal_xy']
             and option['skill'] == 'NAV' and option['target_ref'] == 'cuboid-2:upper-entry'
             and params['surface_height_m'] == 0. and proposal['time_s'] == time_s,
             'Actual assigned preparation goal must match the same public finite candidate')
        pins[str(query_path)] = sha(query_path)
        ready = [(i, r) for i, r in judgments if i > ji and r['payload'].get('intent_sha256') == intent
                 and r['payload']['status'] == 'READY']
        ready_time, ready_sha = (None, None) if not ready else (ready[0][1]['payload']['state']['time_s'], ready[0][1]['sha256'])
        outcomes = [(i, r) for i, r in by_line.items() if r['payload'].get('event') == 'intent_actual_native_outcome'
                    and r['payload'].get('intent_sha256') == intent and i > bi]
        literal = next(((i,r) for i,r in outcomes if r['payload'].get('execution_role') == 'interaction'
                        and r['payload'].get('intent_succeeded') is True
                        and r['payload'].get('receipt',{}).get('status') == 'succeeded'), None)
        success_time = None; outcome_sha = None; native_failure_verified = False
        if literal is not None:
            oi, orow = literal; payload = orow['payload']; receipt = payload['receipt']
            final_bindings = [r for i,r in by_line.items() if i < oi and r['payload'].get('event') == 'intent_native_execution_bound'
                and r['payload'].get('intent_sha256') == intent and r['payload'].get('execution_role') == 'interaction'
                and r['payload'].get('native_option_sha256') == payload['native_option_sha256']]
            need(len(final_bindings)==1 and final_bindings[0]['payload']['native_option']['skill']=='CLIMB'
                 and final_bindings[0]['payload']['native_option']['target_ref']=='cuboid-2:upper-entry'
                 and receipt['option_sha256']==payload['native_option_sha256'] and ready_time is not None,
                 'Original READY plus exact selected CLIMB interaction outcome required')
            success_time = receipt['time_s']; outcome_sha = orow['sha256']; outcome='SUCCESS'
        elif result.get('resource_censored') is True:
            outcome='CENSORED'
        else:
            # Only literal failures of this intent's actually bound native child.
            options={r['payload']['native_option_sha256'] for i,r in by_line.items() if i>=bi and
                r['payload'].get('event')=='intent_native_execution_bound' and r['payload'].get('intent_sha256')==intent}
            failures=[r for i,r in by_line.items() if i>bi and r['payload'].get('event')=='ainav_native_receipt'
                and r['payload'].get('receipt',{}).get('option_sha256') in options
                and r['payload'].get('receipt',{}).get('status')=='failed']
            if failures:
                outcome='NATIVE_GUARD_FAILURE';native_failure_verified=True;outcome_sha=failures[0]['sha256']
            else:
                outcome=None  # Future exception-based witnesses require their actual source evidence, not guessing.
        out['causal_binding'] = dict(first_judgment_line=ji, first_judgment_record_sha256=jr['sha256'],
            proposal_line=pi, proposal_record_sha256=pr['sha256'], preparation_binding_line=bi,
            preparation_binding_record_sha256=br['sha256'], physical_observation_sha256=bound['physical_observation_sha256'],
            query_path=str(query_path), query_file_sha256=sha(query_path), feature_time_s=time_s,
            feature_age_s=features[-1], READY_record_sha256=ready_sha, outcome_record_sha256=outcome_sha,
            assigned_action_offset_xy_m=features[:2], same_public_goal_reached_native_child=True,
            native_install_record_sha256=installed[0][1]['sha256'],physical_command_already_issued_at_install=False,
            first_native_start_record_sha256=None if not starts else starts[0][1]['sha256'],
            first_native_start_time_s=None if not starts else starts[0][1]['payload']['receipt']['time_s'])
        if outcome is None:
            out['status']='POSTDECISION_FAILURE_UNCLASSIFIED_NO_FIT_NO_FABRICATED_LABEL'
        else:
            need(ready_time is None or ready_time>=time_s, 'Causal READY clock')
            need(success_time is None or success_time>=ready_time, 'Nested success clock')
            out['sample']=dict(common,sample_id=plan['attempt_key'],guard_and_stream_integrity_verified=True,
                source_feature_event_sha256=br['sha256'],physical_features=features,outcome=outcome,
                current_READY_s=None if ready_time is None else ready_time-time_s,
                full_success_s=None if success_time is None else success_time-time_s,
                READY_source_verified=ready_time is not None,successful_task_endpoint_verified=success_time is not None,
                native_guard_failure_verified=native_failure_verified)
            out['status']='NEW_PURPOSE_ROW_EXTRACTED_AWAIT_COMPLETE_TRAIN_GATE'
    for path, expected in pins.items():
        need(sha(path) == expected, 'Read sources changed during extraction')
    return out


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('release-root','expected-release-sha','source-root','output'):
        p.add_argument('--'+name,required=True)
    a=p.parse_args(); forbidden=[]
    def fence(event,args):
        if event=='import' and str(args[0]).split('.')[0] in ('torch','mujoco','onnxruntime'):
            forbidden.append(str(args[0]));raise RuntimeError('No Actor/Runtime')
        if event in ('socket.connect','socket.bind','socket.getaddrinfo','subprocess.Popen'):
            forbidden.append(event);raise RuntimeError('No network/child')
        if event=='open' and isinstance(args[0],str) and ('/query-private-' in args[0] or
                args[0].endswith(('/catalog.json','/association.json'))):
            forbidden.append('PRIVATE_INPUT');raise RuntimeError('Public features only')
    sys.addaudithook(fence)
    out=extract(a.release_root,a.expected_release_sha,a.source_root)
    need(not forbidden,'Forbidden side effects')
    out['forbidden_attempts']=forbidden
    out['reader_source_sha256']=sha(__file__)
    with Path(a.output).open('x') as stream:
        json.dump(out,stream,ensure_ascii=False,indent=2,allow_nan=False);stream.write('\n')
    sample=out['sample']
    print(json.dumps(dict(status=out['status'],scope_id=out['inventory']['scope_id'],
        outcome=None if sample is None else sample['outcome'],feature_slots=None if sample is None else len(sample['physical_features']),
        current_READY_s=None if sample is None else sample['current_READY_s'],
        full_success_s=None if sample is None else sample['full_success_s'],fit_allowed=False),ensure_ascii=False))


if __name__=='__main__':main()
