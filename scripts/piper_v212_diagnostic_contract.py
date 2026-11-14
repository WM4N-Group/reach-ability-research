"""Versioned, fail-closed contracts for reserved evaluation, never for fitting.

No raw-source discovery or model loading. Owner supplies the final protocol and
observation audit only after its collection/identity checks. Existing v3 train/dev
adapters and releases intentionally remain unchanged.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from bind_piper_v212_registry import read, sha, verify_reference

ROLE = 'diagnostic_reserved'
SCHEMA = 'reach-v212-diagnostic-labels-v1'
PROTOCOL_SCHEMA = 'reach-v212-diagnostic-protocol-v1'
AUDIT_SCHEMA = 'reach-v212-diagnostic-observation-audit-v1'
SOURCE_KEYS = ('sequence', 'report', 'metadata', 'startup')
STATUSES = ('normal_completion', 'normal_timeout', 'native_termination',
            'runtime_error', 'missing_log')
CODE_FILES = ('piper_v212_diagnostic_contract.py', 'export_piper_v212_diagnostic.py',
              'release_piper_v212_diagnostic.py', 'export_piper_v212_labels.py',
              'export_piper_shared_label_examples.py', 'bind_piper_v212_registry.py')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def purpose_permissions(released=False):
    return dict(allowed_for_new_v212_training=False,
                allowed_for_development_evaluation=False,
                allowed_for_diagnostic_evaluation=released,
                allowed_for_calibration=False, allowed_for_seed_selection=False,
                allowed_for_candidate_selection=False, allowed_for_threshold_adjustment=False,
                model_action_authority=False)


def code_hashes():
    return {name: sha(Path(__file__).with_name(name)) for name in CODE_FILES}


def select_reserved(manifest, split, episode_ids):
    """Check every requested identity before *any* raw/receipt/geometry reads."""
    require(manifest.get('owner') == split.get('owner') == 'world_model', 'Registry owner mismatch')
    require(episode_ids and len(set(episode_ids)) == len(episode_ids), 'Explicit distinct episode IDs required')
    all_items = manifest['physical_episodes']
    by_id = {e['episode_id']: e for e in all_items}
    require(len(by_id) == len(all_items), 'Duplicate manifest episode')
    membership = {}
    for gid, group in split['measured_groups'].items():
        require(group.get('measured_state_fingerprint') == gid, 'Invalid measured fingerprint')
        for eid in group['episodes']:
            require(eid not in membership, 'Duplicate split membership')
            membership[eid] = (gid, group['role'])
    # A different-role sibling sharing a reset must never be hidden by selecting one ID.
    for item in all_items:
        gid = item.get('group_id')
        if gid in split['measured_groups']:
            require(membership.get(item['episode_id']) == (gid, item['role']),
                    'Cross-role group collision or inconsistent membership')
    selected = []
    for eid in episode_ids:
        item = by_id.get(eid, {})
        require(item.get('role') == ROLE and membership.get(eid) == (item.get('group_id'), ROLE),
                'Owner reserved role/group mismatch')
        require(item.get('status') == 'closed', 'Only owner-closed attempts can be read')
        require(item.get('skill_version') == 'push-direct-approach-v212' and
                item.get('task_scope') == 'original_reset_independent_push' and
                item.get('model_action_authority') is False, 'Unexpected skill/task/authority')
        require(isinstance(item.get('recorded'), bool), 'Explicit recorded state required')
        selected.append(item)
    return selected


def registry(shared, episode_ids):
    paths = {n: Path(shared) / n for n in ('batch_manifest.json', 'group_split.json', 'label_contract_v1.json')}
    raw = {n: p.read_bytes().decode('utf-8') for n, p in paths.items()}
    hashes = {n: hashlib.sha256(text.encode('utf-8')).hexdigest() for n, text in raw.items()}
    manifest, split, contract = (json.loads(raw[n]) for n in paths)
    require(manifest['group_split']['sha256'] == hashes['group_split.json'] and
            manifest['group_split']['version'] == split['version'], 'Registry split drift')
    target = contract['auxiliary_target']
    require(contract['label_schema_version'] == 'reach-wm-v212-v1' and target['threshold_m'] == .035 and
            target['horizons_s'] == [.4, 1.] and target['current_evaluator_declared_control_period_s'] == .02,
            'Label contract drift')
    selected = select_reserved(manifest, split, episode_ids)
    return manifest, split, selected, {n: dict(path=str(paths[n].resolve()), sha256=hashes[n],
                                             original_utf8=raw[n]) for n in paths}


def protocol(path, ids, split_version, contract_sha):
    p = read(path)
    require(p.get('schema') == PROTOCOL_SCHEMA and p.get('owner') == 'world_model' and
            p.get('frozen_before_collection') is True, 'Final owner-frozen protocol required; preparation is not permission')
    require(p.get('purpose') == 'diagnostic_evaluation_only' and
            p.get('permissions') == purpose_permissions(True), 'Frozen purpose isolation mismatch')
    allowed = p['episode_ids']
    require(allowed and len(set(allowed)) == len(allowed) and set(ids) <= set(allowed),
            'Episode outside frozen protocol')
    require(p['split_version'] == split_version and p['label_contract_sha256'] == contract_sha,
            'Frozen split/contract mismatch')
    require(p['reach_code_sha256'] == code_hashes(), 'Frozen Reach code drift')
    # Owner final scoring lock binds models, normalizers, references, primary/secondary
    # metrics and scorer. Reach hashes this opaque lock, not models or reserved outcomes.
    verify_reference(p['owner_evaluation_lock'])
    lock = read(p['owner_evaluation_lock']['path'])
    require(lock.get('frozen') is True and lock.get('read_only_scoring') is True and
            lock.get('allow_fitting') is False and
            lock.get('schema') != 'world-model-v212-reserved-diagnostic-preparation-v1',
            'Owner scoring lock must be final/read-only; preparation cannot be wrapped as a freeze')
    verify_reference(p['consumer_auditor'])
    verify_reference(p['observation_auditor'])
    require(p['consumer_auditor']['sha256'] not in code_hashes().values(),
            'Consumer alignment must be independent of the Reach exporter')
    return p


def source_bindings(item):
    return {k: item.get(k) for k in SOURCE_KEYS}


def observation_audit(item, protocol_sha):
    ref = item['diagnostic_observation_audit']
    verify_reference(ref)
    a = read(ref['path'])
    require(a.get('schema') == AUDIT_SCHEMA and a.get('owner') == 'world_model' and a.get('passed') is True,
            'Owner observation audit required')
    require(a['episode_id'] == item['episode_id'] and a['group_id'] == item['group_id'] and a['role'] == ROLE,
            'Observation audit identity mismatch')
    require(a['evaluation_protocol_sha256'] == protocol_sha and a['collection_started_after_freeze'] is True,
            'Collection not bound to frozen protocol')
    require(a['sources'] == source_bindings(item), 'Observation audit source bindings differ')
    require(a['execution_status'] in STATUSES, 'Unsupported execution status')
    require(type(a['valid_interval_count']) is int and 0 <= a['valid_interval_count'] <= 2400 and
            type(a['final_after_available']) is bool, 'Invalid prefix length/after disposition')
    require(a['no_cross_reset'] is True and a['source_integrity_passed'] is True,
            'Source continuity/reset audit failed')
    # The audit implementation is owned/frozen with the final scoring lock.
    verify_reference(a['auditor'])
    for ref in a['sources'].values():
        if ref is not None:
            verify_reference(ref)
    require((item.get('sequence') is not None) == item['recorded'], 'Recorded flag differs from source availability')
    return a
