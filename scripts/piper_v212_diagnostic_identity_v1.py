"""Post-outcome identity-only adapter; original diagnostic kernels stay immutable.

The sole exception is the pinned original-5301 audit receipt, never a model sample.
Each original module is loaded into a private namespace; only its registry/protocol
hooks are substituted. Numeric conversion, masks, release and frozen code checks
are unchanged. No mutation of sys.modules, owner registries or original modules.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

import piper_v212_diagnostic_contract as original
from bind_piper_v212_registry import read, sha, verify_reference

VERSION = 'reach-v212-diagnostic-identity-adapter-v1'
ADDENDUM_SCHEMA = 'reach-v212-diagnostic-identity-addendum-v1'
ALIAS = 'p0-01-original-5301'
PEER = 'p0-02-recorded-5301'
GROUP = 'a26af970b1274f97f51a0549b982b7c91939985bd29ccf7c651ae8bc1645bf84'
ASSOCIATION = 'Recorded/original full report SHA identical; not an independent group'
DECISION_SHA = '98f9ad3f5bfeb6641c9802889a3c1ca5e75d2c7508ce7c52e70a6a47c4573f32'
REPORT_SHA = '11c6b0c37a71f6eac558563e365404f0b9745d88c9ab921f0df677bb5a987e30'
UNCHANGED = ('model_weights', 'normalizers', 'references', 'scoring_mathematics',
             'label_semantics', 'thresholds', 'physical_conditions', 'roles', 'budget')
require = original.require


def private_module(filename):
    path = Path(__file__).with_name(filename)
    spec = importlib.util.spec_from_file_location('_identity_private_' + path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def select_reserved(manifest, split, episode_ids):
    """Validate every identity first, then verify the two known report bytes.

    The only role projection exists in a temporary validation view, after exact
    alias checks; the canonical registry, returned episode records, receipt role,
    physical count and selected source roles are never changed.
    """
    items = manifest['physical_episodes']
    by_id = {e['episode_id']: e for e in items}
    require(len(by_id) == len(items), 'Duplicate manifest episode')
    alias = by_id.get(ALIAS)
    require(alias is not None, 'Pinned receipt alias may not be deleted')
    peer = by_id.get(PEER, {})
    group = split['measured_groups'].get(GROUP, {})
    require(alias.get('recorded') is False and alias.get('sequence') is None and
            alias.get('role') == 'receipt_baseline_only' and alias.get('status') == 'closed' and
            alias.get('physical_episode_charge') == 1 and alias.get('group_id') == GROUP and
            alias.get('group_association') == ASSOCIATION,
            'Pinned receipt alias identity differs')
    require(peer.get('recorded') is True and peer.get('role') == 'train' and peer.get('status') == 'closed' and
            peer.get('group_id') == GROUP and peer.get('sequence') and
            group.get('role') == 'train' and group.get('measured_state_fingerprint') == GROUP and
            sorted(group.get('episodes', [])) == sorted([ALIAS, PEER]), 'Pinned receipt peer/group differs')
    require(alias.get('report', {}).get('sha256') == peer.get('report', {}).get('sha256') == REPORT_SHA,
            'Pinned receipt/peer report SHA differs')
    require(all(e['episode_id'] == ALIAS or e.get('role') != 'receipt_baseline_only' for e in items),
            'No other receipt alias exception allowed')
    # This view cannot select the alias: original selector still requires reserved.
    view = dict(manifest, physical_episodes=[dict(e, role='train') if e['episode_id'] == ALIAS else e for e in items])
    selected = original.select_reserved(view, split, episode_ids)
    for ref in (alias['report'], peer['report']):
        verify_reference(ref)
    verify_reference(peer['sequence'])
    return selected


def registry(shared, episode_ids):
    module = private_module('piper_v212_diagnostic_contract.py')
    module.select_reserved = select_reserved
    return module.registry(shared, episode_ids)


def validate_addendum(path, protocol_path, episode_ids, split_version, contract_sha):
    a = read(path)
    require(a.get('schema') == ADDENDUM_SCHEMA and a.get('identity_only') is True and
            a.get('after_reserved_outcome_read') is True, 'Explicit post-outcome identity-only addendum required')
    require(a.get('unchanged') == {name: True for name in UNCHANGED}, 'Identity scope must preserve all frozen semantics')
    verify_reference(a['original_protocol'])
    require(a['original_protocol']['sha256'] == sha(protocol_path), 'Original protocol addendum binding differs')
    # Old protocol keeps verifying all original Reach kernels and original owner
    # auditor source files. New auditor versions are explicitly separate refs.
    frozen = original.protocol(protocol_path, episode_ids, split_version, contract_sha)
    require(a['original_scoring_lock'] == frozen['owner_evaluation_lock'], 'Original scoring lock binding differs')
    verify_reference(a['original_scoring_lock'])
    require(a['reach_adapter']['sha256'] == sha(__file__), 'Identity adapter source drift')
    verify_reference(a['reach_adapter'])
    for name in ('consumer_auditor', 'observation_auditor', 'owner_identity_addendum', 'main_decision'):
        verify_reference(a[name])
    require(a['main_decision']['sha256'] == DECISION_SHA, 'Main decision evidence drift')
    owner = read(a['owner_identity_addendum']['path'])
    require(owner.get('schema') == 'world-model-v212-receipt-identity-addendum-v1' and
            owner.get('scope') == 'exact_legacy_receipt_identity_only' and
            owner.get('after_known_5311_physical_failure') is True and
            owner.get('scoring_mathematics_changed') is False and
            owner.get('models_normalizers_references_changed') is False and
            owner.get('raw_registry_roles_changed') is False and
            owner.get('original_owner_lock') == a['original_scoring_lock'] and
            owner.get('original_evaluation_protocol') == a['original_protocol'], 'Owner identity scope/bindings differ')
    owner_root = Path(frozen['consumer_auditor']['path']).parent
    for name, digest in owner['owner_adapter_code_sha256'].items():
        require(Path(name).name == name and sha(owner_root / name) == digest, 'Owner identity adapter source drift')
    decision = read(a['main_decision']['path'])
    exact = decision['exact_alias']
    require(decision.get('schema') == 'main-receipt-identity-decision-evidence-v1' and
            (exact['episode_id'], exact['peer_episode_id'], exact['group_id'], exact['report_sha256']) ==
            (ALIAS, PEER, GROUP, REPORT_SHA), 'Main decision must authorize only the pinned receipt')
    require(a['consumer_auditor']['sha256'] not in original.code_hashes().values() and
            a['consumer_auditor']['sha256'] != sha(__file__), 'Independent consumer required')
    effective = dict(frozen, consumer_auditor=a['consumer_auditor'], observation_auditor=a['observation_auditor'])
    return effective


def adapted_kernel(filename, addendum_path, protocol_path):
    """Dependency injection in a fresh namespace, with original code SHA checks."""
    module = private_module(filename)
    module.registry = registry
    module.protocol = lambda path, ids, split, contract: validate_addendum(
        addendum_path, path, ids, split, contract)
    return module


def addendum_reference(path):
    return dict(path=str(Path(path).resolve()), sha256=sha(path))


def export(shared, source_root, protocol_path, episode_ids, identity_addendum):
    before = sha(identity_addendum)
    module = adapted_kernel('export_piper_v212_diagnostic.py', identity_addendum, protocol_path)
    labels = module.export(shared, source_root, protocol_path, episode_ids)
    require(sha(identity_addendum) == before, 'Identity addendum changed during export')
    labels.update(identity_adapter_version=VERSION, identity_addendum=addendum_reference(identity_addendum),
                  post_outcome_identity_adaptation=True)
    return labels


def release(labels_path, alignment_path, shared, protocol_path, identity_addendum, consumer_execution=None):
    before = sha(identity_addendum)
    labels = read(labels_path)
    require(labels.get('identity_adapter_version') == VERSION and labels.get('post_outcome_identity_adaptation') is True and
            labels.get('identity_addendum') == addendum_reference(identity_addendum), 'Label identity addendum differs')
    alignment = read(alignment_path)
    if alignment.get('identity_addendum_sha256') != before:
        require(consumer_execution is not None, 'Independent consumer must confirm the identity addendum')
        execution = read(consumer_execution)
        a = read(identity_addendum)
        require(execution.get('schema') == 'world-model-v212-identity-adapted-execution-v1' and
                execution.get('mode') == 'consumer' and
                execution.get('identity_addendum') == a['owner_identity_addendum'] and
                execution.get('original_evaluation_protocol') == a['original_protocol'] and
                execution.get('original_scoring_lock') == a['original_scoring_lock'] and
                execution.get('output', {}).get('sha256') == sha(alignment_path) and
                execution.get('scoring_mathematics_changed') is False and
                execution.get('models_normalizers_references_changed') is False and
                execution.get('raw_roles_changed') is False, 'Consumer execution receipt binding differs')
        verify_reference(execution['output'])
        execution_ref = addendum_reference(consumer_execution)
    else:
        execution_ref = None
    module = adapted_kernel('release_piper_v212_diagnostic.py', identity_addendum, protocol_path)
    receipt = module.release(labels_path, alignment_path, shared, protocol_path)
    require(sha(identity_addendum) == before, 'Identity addendum changed during release')
    receipt.update(identity_adapter_version=VERSION, identity_addendum=addendum_reference(identity_addendum),
                   post_outcome_identity_adaptation=True, consumer_identity_execution=execution_ref)
    return receipt


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('operation', choices=('export', 'release'))
    for name in ('shared', 'protocol', 'identity-addendum', 'output'):
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--source-root', type=Path)
    p.add_argument('--episode-id', action='append')
    p.add_argument('--labels', type=Path)
    p.add_argument('--alignment', type=Path)
    p.add_argument('--consumer-execution', type=Path)
    a = p.parse_args()
    if a.output.exists():
        p.error('Refusing to overwrite an identity-adapted artifact')
    if a.operation == 'export':
        if a.source_root is None or not a.episode_id:
            p.error('export requires --source-root and explicit --episode-id')
        result = export(a.shared, a.source_root, a.protocol, a.episode_id, a.identity_addendum)
    else:
        if a.labels is None or a.alignment is None:
            p.error('release requires --labels and --alignment')
        result = release(a.labels, a.alignment, a.shared, a.protocol, a.identity_addendum, a.consumer_execution)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False); stream.write('\n')
    print('Identity-only ' + a.operation + ' completed; original protocol/physics unchanged')


if __name__ == '__main__':
    main()
