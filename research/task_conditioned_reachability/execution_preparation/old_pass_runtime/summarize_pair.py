"""Read-only matched-pair summary of OWN reports; never launch/repair/retry.

Missing/unstarted/censored results stay null, and safety is separate from task
success. Physical logs are outcomes, NOT fitted error bounds or planner inputs.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import time

REPORT_FIELDS = (
    'caller_outcome', 'task_success', 'full_integrated_task_success', 'error',
    'sim_seconds', 'wall_seconds', 'physical_steps', 'frames', 'WM_forwards',
    'WM_control', 'strict_safety_certified', 'auxiliary_calibration',
    'high_level_planner', 'stall_stow_recovery', 'native_events',
    'native_results', 'peak_joint_speed_rad_s', 'speed_exceeded_physics_steps',
    'angle_violation_rad', 'torque_saturation_physics_steps',
)


def load_optional(path):
    return json.loads(path.read_text()) if path.is_file() else None


def file_receipt(path):
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return {'name': path.name, 'bytes': path.stat().st_size, 'sha256': digest.hexdigest()}


def phase_spans(path):
    """Observed transition intervals; never pad the censored final interval."""
    spans = []
    if not path.is_file():
        return None
    with path.open() as stream:
        for line in stream:
            row = json.loads(line)
            t, phase = row['time_s'], row['phase']
            if not spans or spans[-1]['phase'] != phase:
                if spans:
                    spans[-1].update(next_phase_first_time_s=t,
                                     transition_duration_s=t-spans[-1]['first_sample_time_s'],
                                     right_censored=False)
                spans.append(dict(phase=phase, first_sample_time_s=t,
                                  last_sample_time_s=t, samples=0,
                                  reference_first=row.get('arm_reference'),
                                  reference_last=row.get('arm_reference'),
                                  right_censored=True, transition_duration_s=None))
            spans[-1].update(last_sample_time_s=t, reference_last=row.get('arm_reference'))
            spans[-1]['samples'] += 1
    return spans


def finite_delta(a, b):
    if type(a) not in (int, float) or type(b) not in (int, float):
        return None
    return b-a if math.isfinite(a) and math.isfinite(b) else None


def paired_prefix(roots, decisions):
    """Compare actual state prefix BEFORE B's intervention, no fitted tolerance."""
    if not decisions:
        return None
    boundary = decisions[0].get('actual_unload_boundary_time_s')
    if boundary is None:
        return None
    paths = [roots[arm]/'stow-actual-200hz.jsonl' for arm in ('A', 'B')]
    if not all(p.is_file() for p in paths):
        return None
    prefixes = []
    for path in paths:
        rows = []
        with path.open() as stream:
            for line in stream:
                row = json.loads(line)
                if row['time_s'] >= boundary:
                    break
                rows.append(row)
        prefixes.append(rows)
    a, b = prefixes
    aligned = len(a) == len(b) and all(x['time_s'] == y['time_s'] for x, y in zip(a, b))
    maxima = {}
    if aligned and a:
        for field in ('q', 'dq', 'arm_reference', 'arm_reference_velocity'):
            maxima[field] = max(abs(u-v) for x, y in zip(a, b) for u, v in zip(x[field], y[field]))
    return dict(before_B_boundary_time_s=boundary, strict_time_less_than_boundary=True,
                A_samples=len(a), B_samples=len(b), exact_timestamp_alignment=aligned,
                all_JSON_rows_exactly_equal=(a == b) if aligned and a else None,
                maximum_absolute_field_difference=maxima or None,
                tolerance_not_fit_from_results=True)


def summarize(release):
    pair = load_optional(release / 'actual-pair-report.json')
    rows = {}
    roots = {}
    for arm in ('A', 'B'):
        admission = json.loads((release / arm / 'main-admission.json').read_text())
        root = Path(admission['new_physical_root'])
        roots[arm] = root
        report = load_optional(root / 'report.json')
        wrapper = load_optional(root / 'wrapper-report.json')
        hookfile = root / 'PHE-actual-decisions.jsonl'
        decisions = [json.loads(line) for line in hookfile.read_text().splitlines()] if hookfile.is_file() else None
        rows[arm] = dict(root=str(root), attempt_started=(root/'attempt.claim').exists(),
                         report_present=report is not None,
                         outcome={k: report.get(k) for k in REPORT_FIELDS} if report is not None else None,
                         wrapper=wrapper, phe_decisions=decisions,
                         actual_stow_phase_spans=phase_spans(root/'stow-actual-200hz.jsonl'),
                         native_video_provenance=load_optional(root/'native-camera-provenance.json'),
                         receipts=[x for n in ('report.json', 'wrapper-report.json', 'PHE-actual-decisions.jsonl',
                                               'stow-actual-200hz.jsonl', 'native-camera-1x.mp4',
                                               'native-camera-provenance.json', 'native-camera-times.jsonl')
                                   if (x := file_receipt(root/n)) is not None])
    deltas = {}
    for field in ('sim_seconds', 'wall_seconds', 'frames', 'WM_forwards', 'WM_control'):
        a, b = (rows[arm]['outcome'] for arm in ('A', 'B'))
        deltas[field + '_B_minus_A'] = finite_delta(a.get(field) if a else None, b.get(field) if b else None)
    launcher = {row['arm']: row.get('full_arm_launcher_wall_s') for row in pair.get('rows', [])} if pair else {}
    deltas['full_arm_launcher_wall_s_B_minus_A'] = finite_delta(launcher.get('A'), launcher.get('B'))
    both_complete = all(rows[arm]['outcome'] is not None and
                        rows[arm]['outcome'].get('full_integrated_task_success') is True
                        for arm in ('A', 'B'))
    efficiency = dict(comparable_completed_tasks=both_complete,
                      reason='both original complete endpoints passed' if both_complete else
                             'at least one task incomplete; shorter censored duration is NOT an efficiency gain',
                      sim_seconds_B_minus_A=deltas['sim_seconds_B_minus_A'] if both_complete else None,
                      full_arm_launcher_wall_s_B_minus_A=deltas['full_arm_launcher_wall_s_B_minus_A'] if both_complete else None)
    return dict(schema='reach-own-old-pass-H-only-pair-outcome-v2',
                pair_report=pair, arms=rows, raw_elapsed_differences_NOT_efficiency=deltas,
                matched_completion_efficiency=efficiency,
                actual_preintervention_prefix=paired_prefix(roots, rows['B']['phe_decisions']),
                scope='one seen-development matched seed; H-only, NOT full F7',
                unstarted_missing_and_censored_results_never_imputed=True,
                statistical_success_rate_or_general_efficiency_effect_established=False,
                task_success_is_not_dynamic_safety=True,
                outcome_logs_not_used_to_fit_bounds_or_select_seeds=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--release', type=Path, required=True)
    parser.add_argument('--wait-seconds', type=float, default=0)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    deadline = time.monotonic() + args.wait_seconds
    while not (args.release/'actual-pair-report.json').exists() and time.monotonic() < deadline:
        time.sleep(min(10, max(0, deadline-time.monotonic())))
    # Summarize only a closed pair when --wait is used. A timeout is not an outcome.
    if args.wait_seconds and not (args.release/'actual-pair-report.json').exists():
        print('READ_ONLY_WATCH_TIMEOUT; no imputation, restart or new task')
        return
    result = summarize(args.release)
    encoded = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    if args.output:
        with args.output.open('x') as stream:
            stream.write(encoded)
    print(encoded)


if __name__ == '__main__':
    main()
