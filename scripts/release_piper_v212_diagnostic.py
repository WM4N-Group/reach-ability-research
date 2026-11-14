"""Release exact reserved files for frozen diagnosis only, after owner alignment.

This does not modify labels, the owner split, the shared index, old releases or
any model. Consumers must check this per-file receipt, never index-level ready.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

from bind_piper_v212_registry import read, sha, verify_reference
from piper_v212_diagnostic_contract import (
    SCHEMA, ROLE, require, registry, protocol, observation_audit, source_bindings,
    purpose_permissions, code_hashes,
)


def aligned_equal(left, right):
    """Full mask/time/stage identity, with only 1e-7 numerical audit tolerance."""
    if type(left) in (int, float) and type(right) in (int, float):
        return math.isfinite(left) and math.isfinite(right) and abs(left - right) <= 1e-7
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(aligned_equal(v, right[k]) for k, v in left.items())
    if isinstance(left, list):
        return len(left) == len(right) and all(aligned_equal(x, y) for x, y in zip(left, right))
    return left == right


def release(labels_path, alignment_path, shared, protocol_path):
    label_sha, alignment_sha, protocol_sha = sha(labels_path), sha(alignment_path), sha(protocol_path)
    labels, alignment = read(labels_path), read(alignment_path)
    require(labels.get('schema') == SCHEMA and labels.get('dataset_role') == ROLE, 'Not reserved labels v1')
    require(all(labels.get(k) is v for k, v in purpose_permissions().items()) and
            labels['permissions'] == purpose_permissions() and labels['training_released'] is False and
            labels['development_evaluation_released'] is False and labels['diagnostic_evaluation_released'] is False,
            'Unreleased purpose isolation mismatch')
    require(labels['reach_code_sha256'] == code_hashes(), 'Exporter/kernel/release code drift')
    episodes = labels['episodes']
    ids = [e['episode_id'] for e in episodes]
    require(episodes and len(ids) == len(set(ids)) and all(e['owner_recorded_role'] == ROLE for e in episodes),
            'Empty, duplicate or mixed-role label file')
    _, split, selected, snapshots = registry(shared, ids)
    require(labels['group_split_version'] == split['version'] and
            labels['contract_sha256'] == snapshots['label_contract_v1.json']['sha256'], 'Current split/contract drift')
    require(labels['evaluation_protocol']['sha256'] == sha(protocol_path), 'Frozen evaluation protocol drift')
    frozen = protocol(protocol_path, ids, split['version'], labels['contract_sha256'])
    for name, snap in labels['registry_snapshots'].items():
        require(hashlib.sha256(snap['original_utf8'].encode()).hexdigest() == snap['sha256'],
                'Corrupt embedded registry snapshot')
    for ep, item in zip(episodes, selected):
        require(ep['group_id'] == item['group_id'] and ep['sources'] == source_bindings(item) and
                ep['observation_audit'] == item['diagnostic_observation_audit'], 'Current source/group binding drift')
        audit = observation_audit(item, sha(protocol_path))
        require(audit['auditor'] == frozen['observation_auditor'], 'Observation auditor drift')
        require(ep['execution_status'] == audit['execution_status'] and
                ep['verified_task_success'] is audit['verified_task_success'], 'Execution disposition drift')
    require(alignment.get('schema') == 'reach-v212-diagnostic-consumer-alignment-v1' and
            alignment.get('passed') is True and alignment.get('independently_recomputed') is True,
            'Independent consumer alignment required')
    require(alignment['labels_sha256'] == sha(labels_path) and
            alignment['evaluation_protocol_sha256'] == sha(protocol_path) and
            alignment['contract_sha256'] == labels['contract_sha256'] and
            alignment['split_version'] == split['version'], 'Consumer file/protocol/contract mismatch')
    require(alignment['auditor'] == frozen['consumer_auditor'], 'Consumer auditor not frozen')
    verify_reference(alignment['auditor'])
    require(aligned_equal(episodes, alignment['episodes']), 'Consumer role/group/query/mask/value alignment differs')
    targets = [t for e in episodes for q in e['queries'] for t in q['targets']]
    require(labels['episode_count'] == len(episodes) and labels['independent_group_count'] == len({e['group_id'] for e in episodes}),
            'Episode/group denominator differs')
    # Recheck current registry and all selected files after verification, before receipt.
    _, current_split, current, live_snapshots = registry(shared, ids)
    require(current == selected and current_split['version'] == split['version'] and
            live_snapshots['label_contract_v1.json']['sha256'] == labels['contract_sha256'],
            'Registry changed during release')
    for item in selected:
        observation_audit(item, sha(protocol_path))
    require((label_sha, alignment_sha, protocol_sha) == (sha(labels_path), sha(alignment_path), sha(protocol_path)),
            'Labels/alignment/protocol changed during release')
    return dict(schema='reach-v212-diagnostic-label-release-v1',
                **purpose_permissions(True), permissions=purpose_permissions(True),
                training_released=False, development_evaluation_released=False, diagnostic_evaluation_released=True,
                labels=dict(path=str(Path(labels_path).resolve()), sha256=sha(labels_path)),
                alignment=dict(path=str(Path(alignment_path).resolve()), sha256=sha(alignment_path)),
                evaluation_protocol=dict(path=str(Path(protocol_path).resolve()), sha256=sha(protocol_path)),
                released_episode_ids=ids, episode_bindings=[dict(episode_id=e['episode_id'], group_id=e['group_id'],
                    role=ROLE, sources=e['sources'], observation_audit=e['observation_audit']) for e in episodes],
                split_version=split['version'], contract_sha256=labels['contract_sha256'],
                attempt_count=len(episodes), independent_group_count=labels['independent_group_count'],
                zero_query_episode_ids=[e['episode_id'] for e in episodes if not e['queries']],
                valid_auxiliary_targets=sum(t['valid'] for t in targets),
                censored_auxiliary_targets=sum(not t['valid'] for t in targets),
                scope='Only this labels SHA and frozen protocol; no fitting/calibration/selection/threshold changes',
                original_files_rewritten=False, new_physical_episodes=0, reach_code_sha256=code_hashes())


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('labels', 'alignment', 'shared', 'protocol', 'output'):
        p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args()
    if a.output.exists():
        p.error('Refusing to overwrite diagnostic release')
    result = release(a.labels, a.alignment, a.shared, a.protocol)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False); stream.write('\n')
    print('Released exact file for diagnostic evaluation only; training/development remain forbidden')


if __name__ == '__main__':
    main()
