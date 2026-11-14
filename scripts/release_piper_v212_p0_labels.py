"""Verify both groups' evidence and publish a P0-only label release record."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from bind_piper_v212_registry import sha, read, verify_reference


def validate_evidence(labels, binding, alignment, p0, historical, split, manifest, live_split, live_manifest):
    if (alignment.get('world_model_consumer_passed') is not True or p0.get('passed') is not True
            or historical.get('passed') is not True):
        raise ValueError('Both current-domain and historical consumer checks must pass')
    if not (labels['label_schema_version']==alignment['label_schema_version']==binding['label_schema_version']):
        raise ValueError('Label semantics differ')
    if (alignment['labels_sha256']!=binding['labels']['sha256']
            or p0['labels_sha256']!=alignment['labels_sha256']
            or p0['contract_sha256']!=labels['contract_sha256']
            or alignment['contract']['sha256']!=labels['contract_sha256']
            or historical['contract_sha256']!=labels['contract_sha256']):
        raise ValueError('Aligned source labels or contract differ')
    if not (p0['split_version']==alignment['group_split']['version']==split['version']
            ==binding['group_split_version']==live_split['version']):
        raise ValueError('Split policy differs')
    if historical.get('allowed_for_new_domain_training') is not False:
        raise ValueError('Historical diagnostic labels must remain excluded')
    by_id={e['episode_id']:e for e in manifest['physical_episodes']}
    live_by_id={e['episode_id']:e for e in live_manifest['physical_episodes']}
    aligned={e['episode_id']:e for e in p0['episodes']}
    bound={e['episode_id']:e for e in binding['episode_bindings']}
    episodes=labels['episodes'];keys={e['episode_id'] for e in episodes}
    if len(episodes)!=3 or len(keys)!=3 or keys!=set(aligned) or keys!=set(bound):
        raise ValueError('Release must match exactly the three aligned P0 episodes')
    if p0['queries']!=sum(len(e['queries']) for e in episodes):
        raise ValueError('Query count differs')
    targets=[t for e in episodes for q in e['queries'] for t in q['targets']]
    if (p0['valid_auxiliary_targets']!=sum(t['valid'] for t in targets)
            or p0['censored_auxiliary_targets']!=sum(not t['valid'] for t in targets)
            or p0['maximum_label_difference_m']>p0['geometry_numerical_tolerance_m']):
        raise ValueError('Consumer target checks differ')
    for e in episodes:
        episode=e['episode_id'];group=e['group_id']
        for registry in (split,live_split):
            info=registry['measured_groups'].get(group,{})
            if info.get('role')!='train' or episode not in info.get('episodes',[]):
                raise ValueError('Released P0 role/group is no longer train')
        for source in (by_id.get(episode,{}),live_by_id.get(episode,{})):
            if (source.get('role')!='train' or source.get('group_id')!=group
                    or source.get('sequence',{}).get('sha256')!=e['source_sha256']
                    or source.get('report',{}).get('sha256')!=e['report_sha256']):
                raise ValueError('P0 source identity or role drift')
        if (aligned[episode]['group_id']!=group or aligned[episode]['role']!='train'
                or aligned[episode]['passed'] is not True or bound[episode]['role']!='train'
                or aligned[episode]['query_count']!=len(e['queries'])):
            raise ValueError('Per-episode alignment differs')
    return sorted(keys)


def release(shared,binding_path,auditor_path):
    aggregate_path=shared/'alignment_world_model_v1.json'
    alignment=read(aggregate_path);binding=read(binding_path)
    for ref in (alignment['p0'],alignment['historical'],alignment['contract'],alignment['converter'],binding['labels']):
        verify_reference(ref)
    labels=read(binding['labels']['path']);p0=read(alignment['p0']['path']);historical=read(alignment['historical']['path'])
    if sha(auditor_path)!=p0['consumer_auditor_sha256'] or sha(auditor_path)!=historical['consumer_auditor_sha256']:
        raise ValueError('Consumer auditor code drift')
    snapshot=shared/'registry_snapshots'
    split_path=Path(alignment['group_split']['snapshot_path'])
    manifest_path=snapshot/'p0-v1-batch_manifest.json'
    ledger_path=snapshot/'p0-v1-collection_ledger.jsonl'
    if (sha(split_path)!=alignment['group_split']['sha256'] or sha(split_path)!=p0['split_sha256']
            or sha(split_path)!=binding['registry']['group_split.json']['sha256']
            or sha(manifest_path)!=binding['registry']['batch_manifest.json']['sha256']
            or sha(ledger_path)!=binding['registry']['collection_ledger.jsonl']['sha256']):
        raise ValueError('P0 registry archive differs from verified binding')
    manifest=read(manifest_path);split=read(split_path)
    if (manifest['group_split']['sha256']!=sha(split_path)
            or manifest['collection_ledger_sha256']!=sha(ledger_path)):
        raise ValueError('Archived registry cross-reference differs')
    live_split_path=shared/'group_split.json';live_manifest_path=shared/'batch_manifest.json'
    live_checksums={str(p):sha(p) for p in (live_split_path,live_manifest_path)}
    live_split=read(live_split_path);live_manifest=read(live_manifest_path)
    ids=validate_evidence(labels,binding,alignment,p0,historical,split,manifest,live_split,live_manifest)
    for e in labels['episodes']:
        if sha(e['source_path'])!=e['source_sha256']:
            raise ValueError('Released raw source drift')
    if historical['labels_sha256']==alignment['labels_sha256']:
        raise ValueError('Historical labels cannot be the P0 training file')
    if any(sha(p)!=checksum for p,checksum in live_checksums.items()):
        raise ValueError('Registry changed while checking P0 compatibility; retry')
    return dict(schema='reach-v212-p0-training-release-v1',training_released=True,
        release_scope='Only exact immutable P0 label file and these three aligned train episodes',
        label_schema_version=labels['label_schema_version'],released_episode_ids=ids,
        labels=binding['labels'],converter=alignment['converter'],contract=alignment['contract'],
        split_policy=split['version'],split_snapshot=dict(path=str(split_path),sha256=sha(split_path)),
        registry_snapshots={name:dict(path=str(path),sha256=sha(path)) for name,path in
             (('manifest',manifest_path),('ledger',ledger_path))},
        canonical_binding=dict(path=str(binding_path),sha256=sha(binding_path)),
        consumer_alignment=dict(path=str(aggregate_path),sha256=sha(aggregate_path)),
        consumer_results=dict(p0=alignment['p0'],historical=alignment['historical']),
        consumer_auditor=dict(path=str(auditor_path),sha256=sha(auditor_path)),
        counts=dict(episodes=len(ids),queries=p0['queries'],valid_targets=p0['valid_auxiliary_targets'],
                    censored_targets=p0['censored_auxiliary_targets']),
        historical_training_allowed=False,unlisted_episodes_training_allowed=False,
        source_labels_rewritten=False,new_physical_episodes=0,
        reserved_source_outcomes_read=False,implementation_sha256=sha(Path(__file__)))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--shared',type=Path,required=True)
    p.add_argument('--binding',type=Path,required=True)
    p.add_argument('--consumer-auditor',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():p.error('Refusing to overwrite release evidence')
    result=release(a.shared,a.binding,a.consumer_auditor)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x') as stream:json.dump(result,stream,indent=2);stream.write('\n')
    print('Released exactly three aligned P0 train episodes; no additional batch release')


if __name__=='__main__':main()
