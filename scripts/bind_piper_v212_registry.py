"""Bind immutable P0 labels to the world-model-owned registry, without releasing training."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def verify_reference(ref):
    if sha(ref['path']) != ref['sha256']:
        raise ValueError(f"Source checksum mismatch: {ref['path']}")


def bind(labels_path, shared):
    paths = {name: shared/name for name in ('batch_manifest.json', 'group_split.json',
                                           'collection_ledger.jsonl', 'label_contract_v1.json')}
    snapshots = {name: sha(path) for name,path in paths.items()}
    labels, manifest, split = read(labels_path), read(paths['batch_manifest.json']), read(paths['group_split.json'])
    contract = read(paths['label_contract_v1.json'])
    ledger = [json.loads(line) for line in paths['collection_ledger.jsonl'].read_text().splitlines()]
    if manifest['owner'] != 'world_model' or split['owner'] != 'world_model':
        raise ValueError('Canonical registry must remain world-model-owned')
    if (labels['label_schema_version'] != contract['label_schema_version']
            or labels['contract_sha256'] != snapshots['label_contract_v1.json']):
        raise ValueError('Label contract differs from canonical contract')
    if (manifest['group_split']['sha256'] != snapshots['group_split.json']
            or manifest['group_split']['version'] != split['version']
            or Path(manifest['group_split']['path']).resolve() != paths['group_split.json'].resolve()
            or manifest['collection_ledger_sha256'] != snapshots['collection_ledger.jsonl']):
        raise ValueError('Registry cross-references disagree')
    charged = sum(e['charged_attempt_delta'] for e in ledger)
    reserved = sum(e['reserved_attempt_delta'] for e in ledger)
    if (charged != manifest['actual_charged_attempts']
            or reserved != manifest['active_reserved_attempts']
            or charged != sum(ep['physical_episode_charge'] for ep in manifest['physical_episodes'])
            or manifest['shared_physical_episode_cap'] != contract['collection']['shared_physical_episode_cap']
            or not 0 <= charged <= charged+reserved <= manifest['shared_physical_episode_cap']
            or manifest['budget_remaining_including_reserved'] != manifest['shared_physical_episode_cap']-charged
            or manifest['budget_unreserved'] != manifest['shared_physical_episode_cap']-charged-reserved):
        raise ValueError('Registry budget accounting disagrees')
    actual = manifest['physical_episodes']
    if len({e['episode_id'] for e in actual}) != len(actual):
        raise ValueError('Duplicate physical episode in manifest')
    imported = [e['episode_id'] for e in ledger if e['event']=='import_closed_physical_attempt']
    if len(set(imported)) != len(imported) or set(imported) != {e['episode_id'] for e in actual}:
        raise ValueError('Ledger physical-episode identities disagree')
    expected_planned = {e['episode_id']:e['role'] for e in manifest['planned_episodes']}
    recorded_planned = {e['episode_id']:e['role'] for e in ledger if e['event']=='reserve_unattempted_plan'}
    split_planned = {e['episode_id']:e['role'] for e in split['planned_slots']}
    if recorded_planned != expected_planned or split_planned != expected_planned or len(expected_planned) != reserved:
        raise ValueError('Planned reservations or roles disagree')
    membership = {}
    for group, info in split['measured_groups'].items():
        if info['measured_state_fingerprint'] != group:
            raise ValueError('Group ID is not its measured fingerprint')
        for episode in info['episodes']:
            if episode in membership:
                raise ValueError('Episode occurs in more than one group')
            membership[episode] = (group, info['role'])
    labels_episodes = labels['episodes']
    if len({e['episode_id'] for e in labels_episodes}) != len(labels_episodes):
        raise ValueError('Duplicate labeled physical episode')
    by_id = {e['episode_id']:e for e in actual}
    # Decide eligibility for every label before opening any raw trajectory.
    selected = []
    for ep in labels_episodes:
        info = by_id.get(ep['episode_id'])
        if info is None:
            raise ValueError('Labeled episode is absent from canonical manifest')
        if (info['role'] != 'train' or ep['owner_recorded_role'] != 'train'
                or membership.get(ep['episode_id']) != (ep['group_id'], 'train')
                or info['group_id'] != ep['group_id']):
            raise ValueError('Label group/role differs; refuse non-training source')
        if info['status'] != 'closed' or info['recorded'] is not True:
            raise ValueError('Only completed recorded P0 sources can be bound')
        if (info['task_scope'] != ep['task_scope'] or info['skill_version'] != ep['skill_version']
                or info['sequence']['sha256'] != ep['source_sha256']
                or Path(info['sequence']['path']).resolve() != Path(ep['source_path']).resolve()
                or info['report']['sha256'] != ep['report_sha256']
                or info['query_count'] != len(ep['queries'])
                or info['outcome']['verified_task_success'] != ep['verified_task_success']
                or ep['skill_bundle_hash'] != manifest['frozen_skill_inventory']['sha256']):
            raise ValueError('Label identity/source disagrees with manifest')
        selected.append((ep,info))
    verify_reference(manifest['source_p0_ledger'])
    verify_reference(manifest['frozen_skill_inventory'])
    verify_reference(split['source_role_plan'])
    verify_reference(split['source_new_collection_plan'])
    bindings = []
    for ep,info in selected:
        for key in ('sequence','report','metadata','startup'):
            verify_reference(info[key])
        bindings.append(dict(episode_id=ep['episode_id'],group_id=ep['group_id'],
                             role='train',group_split_version=split['version'],
                             source_sha256=ep['source_sha256'],query_count=len(ep['queries'])))
    if any(sha(path) != snapshots[name] for name,path in paths.items()):
        raise ValueError('Canonical registry changed while binding; retry with one stable snapshot')
    return dict(schema='reach-v212-canonical-label-binding-v1',
                status='canonical_split_verified_consumer_alignment_pending',
                label_schema_version=labels['label_schema_version'],
                labels=dict(path=str(labels_path.resolve()),sha256=sha(labels_path)),
                registry={name:dict(path=str(path.resolve()),sha256=snapshots[name]) for name,path in paths.items()},
                group_split_version=split['version'],episode_bindings=bindings,
                budget_snapshot=dict(charged=charged,reserved_not_started=reserved,
                                     cap=manifest['shared_physical_episode_cap'],unreserved=manifest['budget_unreserved']),
                training_released=False,release_blocker='world-model consumer alignment not yet confirmed',
                source_labels_rewritten=False,owner_registry_rewritten=False,
                reserved_source_outcomes_read=False,new_physical_episodes=0,
                implementation_sha256=sha(Path(__file__)))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--labels',type=Path,required=True)
    parser.add_argument('--shared',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():
        parser.error('Refusing to overwrite a binding snapshot')
    result=bind(args.labels,args.shared)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x') as stream:
        json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
    print(f"Bound {len(result['episode_bindings'])} train episodes to {result['group_split_version']}; training release unchanged")


if __name__=='__main__':
    main()
