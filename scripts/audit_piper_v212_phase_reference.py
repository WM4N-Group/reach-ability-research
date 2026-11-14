"""Diagnose phase mixing in the fixed current-clearance reference, using P0 train data."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path

from audit_piper_source_transition_trace import sha256


PHASES = ('all', 'before_approach_complete',
          'approach_complete_before_legal_contact', 'legal_contact_seen')


def causal_phases(intervals):
    """The current phase depends only on this before-state and prior intervals."""
    contact_seen = approach_seen = False
    result = []
    for row in intervals:
        state = row['before']
        contact_seen |= (state['legal_hand_contact'] is True
                         and state['invalid_hand_contact'] is False
                         and state['forbidden_box_contact'] is False)
        approach_seen |= state['controller_observed']['safe_approach_complete'] is True
        phase = ('legal_contact_seen' if contact_seen else
                 'approach_complete_before_legal_contact' if approach_seen else
                 'before_approach_complete')
        result.append((phase, contact_seen))
    return result


def summarize(items):
    """Average queries within episodes, then episodes within measured groups."""
    episodes = defaultdict(list)
    for group_id, episode_id, error in items:
        if not math.isfinite(error):
            raise ValueError('Nonfinite scoring error')
        episodes[(group_id, episode_id)].append(error)
    groups = defaultdict(list)
    detail = []
    for (group, episode), errors in sorted(episodes.items()):
        mae = sum(abs(e) for e in errors) / len(errors)
        optimistic = sum(max(e, 0.) for e in errors) / len(errors)
        groups[group].append((mae, optimistic))
        detail.append(dict(episode_id=episode, group_id=group, queries=len(errors),
                           mae_m=mae, mean_optimistic_error_m=optimistic,
                           max_optimistic_error_m=max(max(e, 0.) for e in errors)))
    group_metrics = [dict(group_id=g, episodes=len(values),
                         mae_m=sum(v[0] for v in values)/len(values),
                         mean_optimistic_error_m=sum(v[1] for v in values)/len(values))
                     for g, values in sorted(groups.items())]
    return dict(query_count=len(items), episode_count=len(episodes),
                measured_groups=len(groups),
                mean_group_mae_m=(sum(g['mae_m'] for g in group_metrics)/len(groups)
                                  if groups else None),
                max_optimistic_error_m=max((max(e, 0.) for _, _, e in items), default=None),
                groups=group_metrics, episodes=detail)


def audit(labels_path):
    labels = json.loads(labels_path.read_text())
    if labels.get('adapter_version') != 'v212-recorded-p0-labels-v1r1':
        raise ValueError('This diagnostic binds the existing P0 v1r1 labels')
    scores = {(h, phase): [] for h in (.4, 1.) for phase in PHASES}
    exclusions = defaultdict(lambda: dict(no_history=0, incomplete_horizon=0))
    episodes = labels['episodes']
    if len({e['episode_id'] for e in episodes}) != len(episodes):
        raise ValueError('Duplicate physical episode')
    # Check every role before opening any raw source, including later entries.
    if any(e.get('owner_recorded_role') != 'train' for e in episodes):
        raise ValueError('P0 training diagnostic must not read reserved/development sources')
    pass_count = query_count = 0
    margins = []
    future_breach = defaultdict(int)
    for ep in episodes:
        source = Path(ep['source_path'])
        if sha256(source) != ep['source_sha256']:
            raise ValueError('Raw sequence checksum differs from frozen labels')
        intervals = [json.loads(s) for s in source.read_text().splitlines()]
        phases = causal_phases(intervals)
        dt = ep['actual_sample_period_s']
        for q in ep['queries']:
            step = round(q['query_time_s']/dt)
            if (not 0 <= step < len(intervals)
                    or not math.isclose(intervals[step]['interval_start_s'],
                                        q['query_time_s'], abs_tol=1e-8)):
                raise ValueError('Query does not map to recorded before-state')
            phase, contact_seen = phases[step]
            if q['inputs']['legal_contact_seen'] != contact_seen:
                raise ValueError('Query contact history differs from causal raw prefix')
            margin = q['inputs']['actual_clearance_m'] - .035
            query_count += 1
            pass_count += int(margin >= 0.)
            margins.append(margin)
            for t in q['targets']:
                h = t['requested_horizon_s']
                if h not in (.4, 1.):
                    raise ValueError('Unexpected horizon')
                if not q['history_0p4s_available']:
                    exclusions[h]['no_history'] += 1
                    continue
                if not t['valid']:
                    if t['value'] is not None:
                        raise ValueError('Censored target must not contain a regression value')
                    exclusions[h]['incomplete_horizon'] += 1
                    continue
                if not t['horizon_complete']:
                    raise ValueError('Valid target lacks full horizon')
                if not math.isclose(t['constant_reference_m'], margin, abs_tol=1e-10):
                    raise ValueError('Reference differs from current actual geometry')
                if t['value'] > margin + 1e-8:
                    raise ValueError('Inclusive minimum exceeds query clearance')
                error = margin - t['value']
                item = (ep['group_id'], ep['episode_id'], error)
                scores[(h, 'all')].append(item)
                scores[(h, phase)].append(item)
                future_breach[h] += int(t['value'] < 0.)
    result = []
    for h in (.4, 1.):
        complete = summarize(scores[(h, 'all')])
        phases = {phase: summarize(scores[(h, phase)]) for phase in PHASES[1:]}
        assert sum(v['query_count'] for v in phases.values()) == complete['query_count']
        result.append(dict(horizon_s=h, eligibility='0.4s history and observed full horizon',
                           excluded=dict(exclusions[h]), pooled=complete, phases=phases,
                           future_recorded_clearance_breach_count=future_breach[h]))
    return dict(schema='reach-v212-p0-phase-reference-v1',
                label_schema_version=labels['label_schema_version'],
                labels_path=str(labels_path), labels_sha256=sha256(labels_path),
                analysis_sha256=sha256(Path(__file__)), reference='current_actual_clearance_minus_35mm',
                aggregation='query -> physical episode -> measured initial-state group',
                rule_diagnostic=dict(current_clearance_pass=pass_count,queries=query_count,
                    minimum_query_margin_m=min(margins), verified_success_episodes=sum(
                        ep['verified_task_success'] is True for ep in episodes),
                    failure_episodes=sum(ep['verified_task_success'] is False for ep in episodes),
                    false_rejection_rate=None, safety_failure_recall=None,
                    reason='All exposed P0 episodes succeed; no reject-execute counterfactuals or failures'),
                results=result, new_physical_episodes=0,
                limitations=['P0 training groups only; no model fitting, threshold selection or holdout score.',
                    'Origin phase uses recorded current/past events; future crossing does not reclassify a query.',
                    'Complete-window eligibility is retrospective evaluation support, not an online input.',
                    'Current geometry is only one necessary rule; passage is not future execution safety.',
                    'The inclusive minimum makes optimism nonnegative by definition; not predictive evidence.'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--labels', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Refusing to overwrite frozen diagnostic')
    result = audit(args.labels)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    for result in result['results']:
        print(result['horizon_s'], 'pooled_MAE_mm', result['pooled']['mean_group_mae_m']*1000,
              'post_contact_MAE_mm', result['phases']['legal_contact_seen']['mean_group_mae_m']*1000)


if __name__ == '__main__':
    main()
