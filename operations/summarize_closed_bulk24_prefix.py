#!/usr/bin/env python3
"""Audit a fixed closed bulk24 prefix (legacy first-ten format retained), not a dataset/fit/V4 method evaluation.

Keep unreached failures in the denominator. Compare measured proprio+age equality
only; neither equal feature hashes nor independent runs imply equal full worlds.
Read actual native/source evidence, never construct Runtime/Actor/model/renderer.
"""
import argparse
import datetime as dt
import hashlib
import importlib
import json
import math
from pathlib import Path
import sys


def need(ok, message):
    if not ok:
        raise ValueError(message)


def checked_prefix_count(manifest):
    role = manifest['role']
    if role == 'FIXED_FIRST_TEN_BULK24_READ_ONLY_NOT_FIT':
        count = manifest.get('prefix_count',10)
        need(type(count) is int and count == 10, 'Legacy first-ten audit is never expanded in place')
    else:
        need(role == 'FIXED_CLOSED_BULK24_PREFIX_READ_ONLY_NOT_FIT', 'Explicit read-only prefix scope')
        count = manifest['prefix_count']
        need(type(count) is int and 10 <= count <= 24, 'Bounded prefix of the original fixed24 schedule')
    need([r['ordinal'] for r in manifest['attempts']] == list(range(1,count+1)),
         'All fixed-prefix attempts in order, never a success-only denominator')
    return count


def native_ticks(seconds):
    need(type(seconds) in (int,float) and math.isfinite(seconds) and seconds >= 0,
         'Actual finite native elapsed clock; missing/failure is not zero')
    ticks = round(seconds/.005)
    need(abs(seconds-ticks*.005) <= 1e-6, 'Native200Hz event clock, no posthoc rounding off-grid data')
    return ticks


def complete_candidate_tables(measurements):
    """Hindsight ONLY: actual R/C labels, not predictions or a deployable baseline.

    Group by declared geometry/prefix, retaining failed complete cost=None. Exact
    public45+age equality is reported but is NOT equal RGBD/hidden-world proof.
    """
    candidates = ('original','lateral_plus_0p04','lateral_minus_0p04')
    groups = {}
    for ordinal,report in measurements.items():
        scalar = report['scalar']; candidate = scalar['candidate_id']
        need(candidate in candidates and scalar['ordinal'] == ordinal, 'Exact registered candidate/ordinal')
        need(len(report['physical_features']) == 48, 'Actual existing public48 feature projection')
        key = (scalar['group_id'],scalar['prefix_side'],scalar['new_geometry_definition_sha256'])
        group = groups.setdefault(key,{})
        need(candidate not in group, 'No repeated candidate/seed replaces a missing member')
        group[candidate] = report
    tables = []
    for (group_id,side,scene_sha),group in sorted(groups.items()):
        if set(group) != set(candidates): continue
        items = []
        for candidate in candidates:
            report = group[candidate];scalar = report['scalar']
            r = native_ticks(scalar['current_READY_s']);c = scalar['full_requested_CLIMB_success_s']
            ct = None if c is None else native_ticks(c)
            need(ct is None or ct >= r, 'Complete requested success cannot predate READY')
            passed = scalar.get('source_result_passed',c is not None)
            need(type(passed) is bool and passed == (c is not None), 'Failure/censor cost stays None')
            items.append(dict(candidate_id=candidate,ordinal=scalar['ordinal'],
                actual_current_READY_s=scalar['current_READY_s'],actual_current_READY_ticks=r,
                actual_full_CLIMB_success_s=c,actual_full_CLIMB_success_ticks=ct,
                actual_READY_to_CLIMB_success_ticks=None if ct is None else ct-r,
                source_result_passed=passed))
        local_min = min(row['actual_current_READY_ticks'] for row in items)
        succeeded = [row for row in items if row['actual_full_CLIMB_success_ticks'] is not None]
        full_min = None if not succeeded else min(row['actual_full_CLIMB_success_ticks'] for row in succeeded)
        local = [row for row in items if row['actual_current_READY_ticks'] == local_min]
        full = [row for row in succeeded if row['actual_full_CLIMB_success_ticks'] == full_min]
        feature_states = [group[c]['physical_features'][2:] for c in candidates]
        clocks = [group[c]['scalar']['first_PREPARE_time_s'] for c in candidates]
        same_states = all(value == feature_states[0] for value in feature_states)
        tables.append(dict(group_id=group_id,prefix_side=side,declared_scene_sha256=scene_sha,rows=items,
            all_three_candidates_measured=True,actual_public45_plus_age_exactly_equal=same_states,
            first_PREPARE_clocks_equal=all(value == clocks[0] for value in clocks),
            same_RGBD_or_hidden_world_or_causal_effect_claimed=False,
            hindsight_local_READY_minimizers=[row['candidate_id'] for row in local],
            hindsight_full_success_minimizers=[row['candidate_id'] for row in full],
            local_and_full_best_disjoint=bool(full) and not bool({r['candidate_id'] for r in local}&{r['candidate_id'] for r in full}),
            at_least_one_local_minimizer_failed=any(not row['source_result_passed'] for row in local),
            local_advantage_over_full_best_ticks=None if not full else min(row['actual_current_READY_ticks'] for row in full)-local_min,
            observed_full_cost_gap_for_local_minimizers_ticks={row['candidate_id']:(None if row['actual_full_CLIMB_success_ticks'] is None or full_min is None
                else row['actual_full_CLIMB_success_ticks']-full_min) for row in local},
            not_online_predictions_or_trained_policy_or_method_gain=True))
    return tables


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--expected-manifest-sha', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args(); pins = {}

    def read(path, expected=None):
        path = Path(path)
        need(path.is_file() and not path.is_symlink(), 'Regular exact input only')
        raw = path.read_bytes(); sha = hashlib.sha256(raw).hexdigest()
        need(expected is None or expected == sha, 'Input SHA: '+str(path))
        need(str(path) not in pins or pins[str(path)] == sha, 'Input changed during audit')
        pins[str(path)] = sha
        return json.loads(raw)

    manifest = read(args.manifest, args.expected_manifest_sha)
    prefix_count = checked_prefix_count(manifest)
    source = Path(manifest['original_public_source_root'])
    for rel, sha in manifest['original_public_source_pins'].items():
        need(rel in ('ainav/contracts.py','ainav/evidence.py'), 'Only original public contracts/evidence imports')
        path = source / rel
        need(path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == sha, 'Original public verification source')
        pins[str(path)] = sha
    need(len(manifest['original_public_source_pins']) == 2, 'Exact public verification closure')
    sys.path.insert(0, str(source))
    evidence = importlib.import_module('ainav.evidence')
    need(Path(evidence.__file__).resolve() == (source/'ainav/evidence.py').resolve(), 'No foreign evidence module')
    from measure_bulk24_public_boundary import requested_climb_endpoint,registration_gate,PROTOCOL_SHA
    endpoint_reader = Path(sys.modules[requested_climb_endpoint.__module__].__file__)
    pins[str(endpoint_reader)] = hashlib.sha256(endpoint_reader.read_bytes()).hexdigest()
    rows = []; measurements = {}
    for registered in manifest['attempts']:
        release_path = Path(registered['release_path']); root = release_path.parent
        release = read(release_path, registered['release_sha256'])
        need(release['ordinal'] == registered['ordinal'] and release['fit_allowed'] is False and
             release['current_model_refit_allowed'] is False and release['whole_package_model_input_allowed'] is False,
             'No data purpose/ordinal/fit promotion')
        for rel, expected in release['files'].items():
            path = root/rel
            need(not Path(rel).is_absolute() and '..' not in Path(rel).parts and not path.is_symlink()
                 and path.resolve().is_relative_to(root) and path.is_file(), 'Released member stays in source package')
            need(hashlib.sha256(path.read_bytes()).hexdigest() == expected, 'Released member SHA: '+rel)
            pins[str(path)] = expected
        protocol = read(root/'protocol/BULK24_COLLECTION_PROTOCOL.json',PROTOCOL_SHA)
        acquisition = read(root/'protocol/new-purpose-acquisition-manifest.json')
        scheduled = registration_gate(release,protocol,acquisition)
        ledger = read(root/'evidence/ledger.json')
        need(ledger['scope_id'] == release['scope_id'] and ledger['program_sha256'] == release['program_sha256']
             and len(ledger['rows']) == 2 and all(row['closed'] and row['usage_known'] for row in ledger['rows']),
             'Original closed zero/main ledger for every prefix attempt, including unreached failures')
        result = read(root/'evidence/main-result.json',release['actual_summary']['source_result_sha256'])
        need(type(result['passed']) is bool, 'Literal original result')
        ref = read(root/'original-journal-remote-reference.json')
        journal = Path(ref['path']); raw = journal.read_bytes()
        need(hashlib.sha256(raw).hexdigest() == ref['sha256'], 'Original full journal SHA')
        pins[str(journal)] = ref['sha256']
        chain = evidence.verify(journal); need(chain == ref['verified_chain'], 'Original full chain')
        prepares = [(i,json.loads(line)) for i,line in enumerate(raw.splitlines(),1)
            if (lambda p: p.get('event') == 'skill_execution_judgment' and p.get('status') == 'PREPARE'
                and p.get('spec',{}).get('skill') == 'CLIMB')(json.loads(line)['payload'])]
        row = dict(ordinal=registered['ordinal'], scope_id=release['scope_id'],
            release_sha256=registered['release_sha256'], source_result_sha256=release['actual_summary']['source_result_sha256'],
            source_result_passed=result['passed'],
            source_error_classification=None if result.get('error') is None else result['error'].split('{',1)[0].rstrip(':'),
            source_literal_error_sha256=None if result.get('error') is None else hashlib.sha256(result['error'].encode()).hexdigest(),
            group_id=scheduled['group_id'],prefix_side=scheduled['prefix_side'],candidate_id=scheduled['candidate_id'],
            first_CLIMB_PREPARE_reached=bool(prepares),
            first_CLIMB_PREPARE_s=None if not prepares else prepares[0][1]['payload']['state']['time_s'],
            first_CLIMB_PREPARE_line=None if not prepares else prepares[0][0],
            original_journal_sha256=ref['sha256'], original_journal_chain=chain,
            current_READY_s=None, full_requested_CLIMB_success_s=None,
            physical_features_measured=False, predictor_success_cost_label_created=False)
        measurement = registered.get('measurement')
        if measurement:
            report = read(measurement['path'], measurement['sha256']); scalar = report['scalar']
            need(report['source_pins'].get(str(release_path)) == registered['release_sha256']
                and scalar['ordinal'] == row['ordinal'] and prepares
                and scalar['first_PREPARE_time_s'] == row['first_CLIMB_PREPARE_s'], 'Measurement exact first-decision binding')
            need(scalar['fit_or_current_model_refit_allowed'] is False and scalar['model_scored_or_calibrated'] is False,
                 'Not a fit, evaluation or calibration run')
            need((scalar['full_requested_CLIMB_success_s'] is not None) == result['passed'],
                 'Failure/censor elapsed cannot be successful-Finish cost')
            endpoint = requested_climb_endpoint(
                {i:json.loads(line) for i,line in enumerate(raw.splitlines(),1)},
                prepares[0][1]['payload']['intent_sha256'], str(journal), result, allow_native_hard_stop=True)
            need(abs((endpoint['ready_time_s']-row['first_CLIMB_PREPARE_s'])-scalar['current_READY_s']) <= 1e-9,
                 'Independent exact READY clock agrees with measured scalar')
            row['literal_endpoint'] = endpoint
            row.update(measurement_path=measurement['path'], measurement_sha256=measurement['sha256'],
                measured=scalar, current_READY_s=scalar['current_READY_s'],
                full_requested_CLIMB_success_s=scalar['full_requested_CLIMB_success_s'], physical_features_measured=True)
            measurements[row['ordinal']] = report
        else:
            need(not prepares and result['passed'] is False, 'Every reached decision accounted, no dropped failed decision')
        rows.append(row)
    comparisons = []
    for a,b in ((1,9),(2,10)):
        left,right = measurements[a],measurements[b]; x,y = left['scalar'],right['scalar']
        need(all(x[k] == y[k] for k in ('group_id','prefix_side','new_geometry_definition_sha256','first_PREPARE_time_s')),
             'Only same declared context/clock contrasts')
        equal = left['physical_features'][2:] == right['physical_features'][2:]
        need(equal == (x['state46_sha256'] == y['state46_sha256']), 'Actual 45D+age bytes, not metadata shortcut')
        comparisons.append(dict(ordinals=[a,b], same_declared_context=True,
            actual_public45_plus_age_exactly_equal=equal, same_full_observation_or_hidden_world_claimed=False,
            local_READY_delta_b_minus_a_s=y['current_READY_s']-x['current_READY_s'],
            complete_success_delta_b_minus_a_s=(None if x['full_requested_CLIMB_success_s'] is None or
                y['full_requested_CLIMB_success_s'] is None else y['full_requested_CLIMB_success_s']-x['full_requested_CLIMB_success_s']),
            causal_or_method_gain_claimed=False))
    for path,sha in pins.items():
        need(hashlib.sha256(Path(path).read_bytes()).hexdigest() == sha, 'Input changed after read')
    output = dict(schema='Reach-bulk24-closed-prefix-endpoint-audit-v2',
        at=dt.datetime.now().astimezone().isoformat(), role='RETROSPECTIVE_BULK24_PREPARATION_ENDPOINTS_NOT_FIT_OR_V4_RESULT',
        reader_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), rows=rows, comparisons=comparisons,
        actual_attempts=prefix_count, original_source_passes=sum(r['source_result_passed'] for r in rows),
        original_source_failures=sum(not r['source_result_passed'] for r in rows),
        reached_CLIMB_decisions=len(measurements), unreached_CLIMB_attempts=prefix_count-len(measurements),
        complete_three_candidate_tables=complete_candidate_tables(measurements),
        measured_full48_vectors=len(measurements),
        distinct_full48=sum(1 for _ in {r['scalar']['full48_feature_sha256'] for r in measurements.values()}),
        distinct_public45_plus_age=sum(1 for _ in {r['scalar']['state46_sha256'] for r in measurements.values()}),
        original_independent_scene_ancestors=1, new_fit_or_refit_or_scoring_or_V4_physics_or_WM_calls=0,
        frozen_model_changed=False, optimizer_gain_or_complete_V4_qualification_claimed=False,
        physical_arrays_frames_weights_videos_stay_remote=True, source_pins=pins)
    with Path(args.output).open('x') as f:
        json.dump(output,f,ensure_ascii=False,indent=2,allow_nan=False); f.write('\n')
    print(json.dumps({k:v for k,v in output.items() if k not in ('rows','source_pins')},indent=2))


if __name__ == '__main__':
    def fence(event,args):
        if event == 'import' and str(args[0]).split('.')[0] in ('torch','mujoco','onnxruntime'):
            raise RuntimeError('No native or model imports')
        if event in ('subprocess.Popen','socket.connect','socket.bind','socket.getaddrinfo'):
            raise RuntimeError('No child process or network')
    sys.addaudithook(fence)
    main()
