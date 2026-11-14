"""Create a source-exact, role-specific release after independent consumer alignment."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from bind_piper_v212_registry import sha, read
from export_piper_v212_registered_roles import select_closed_role


def permissions(labels,alignment):
    if alignment.get('passed') is not True:
        raise ValueError('Independent consumer alignment has not passed')
    roles={e['owner_recorded_role'] for e in labels['episodes']}
    if len(roles)!=1 or not roles <= {'train','development_calibration'}:
        raise ValueError('Release must have one non-reserved role')
    role=next(iter(roles));episodes=labels['episodes']
    aligned={e['episode_id']:e for e in alignment['episodes']}
    if len(aligned)!=len(alignment['episodes']) or set(aligned)!={e['episode_id'] for e in episodes}:
        raise ValueError('Alignment episode set differs')
    if alignment['contract_sha256']!=labels['contract_sha256'] or alignment['split_version']!=labels['group_split_version']:
        raise ValueError('Aligned contract or policy differs')
    targets=[t for e in episodes for q in e['queries'] for t in q['targets']]
    if (alignment['valid_auxiliary_targets']!=sum(t['valid'] for t in targets)
            or alignment['censored_auxiliary_targets']!=sum(not t['valid'] for t in targets)
            or not 0 <= alignment['maximum_label_difference_m'] <= 1e-7):
        raise ValueError('Alignment target counts or geometry difference invalid')
    for e in episodes:
        a=aligned[e['episode_id']]
        if a['group_id']!=e['group_id'] or a['role']!=role or a['queries']!=len(e['queries']):
            raise ValueError('Aligned role, group or queries differ')
    return dict(role=role,weight_fitting=role=='train',development_evaluation=role=='development_calibration',
                unlisted_sources=False,historical_sources=False)


def release(labels_path,alignment_path,shared,exporter_path,consumer_path):
    labels=read(labels_path);alignment=read(alignment_path)
    if alignment['labels_sha256']!=sha(labels_path):
        raise ValueError('Consumer confirmed a different label file')
    if sha(exporter_path)!=labels['exporter_sha256']:
        raise ValueError('Label exporter source mismatch')
    if sha(consumer_path)!=alignment.get('auditor_sha256',alignment.get('consumer_auditor_sha256')):
        raise ValueError('Consumer auditor source mismatch')
    scope=permissions(labels,alignment)
    contract=shared/'label_contract_v1.json'
    if sha(contract)!=labels['contract_sha256']:
        raise ValueError('Canonical contract drift')
    for name,snap in labels['registry_snapshot_inputs'].items():
        import hashlib
        if hashlib.sha256(snap['original_utf8'].encode()).hexdigest()!=labels['canonical_registry_snapshot_checksums'][name]:
            raise ValueError('Embedded registry snapshot corrupted')
    manifest=read(shared/'batch_manifest.json');split=read(shared/'group_split.json')
    ids=[e['episode_id'] for e in labels['episodes']]
    selected=select_closed_role(manifest,split,ids,scope['role'])
    if split['version']!=labels['group_split_version']:
        raise ValueError('Current canonical policy differs')
    for e,item in zip(labels['episodes'],selected):
        if (e['group_id']!=item['group_id'] or e['source_sha256']!=item['sequence']['sha256']
                or sha(e['source_path'])!=e['source_sha256'] or e['report_sha256']!=item['report']['sha256']):
            raise ValueError('Current source role/identity differs from checked increment')
    return dict(schema='reach-v212-role-specific-label-release-v1r1',
                training_released=scope['weight_fitting'],
                development_evaluation_released=scope['development_evaluation'],
                label_schema_version=labels['label_schema_version'],permissions=scope,released_episode_ids=ids,
                labels=dict(path=str(labels_path.resolve()),sha256=sha(labels_path)),
                alignment=dict(path=str(alignment_path.resolve()),sha256=sha(alignment_path)),
                exporter=dict(path=str(exporter_path.resolve()),sha256=sha(exporter_path)),
                consumer_auditor=dict(path=str(consumer_path.resolve()),sha256=sha(consumer_path)),
                split_policy=labels['group_split_version'],
                original_role_snapshot='Embedded in immutable labels; current selected role and identity also checked',
                original_labels_rewritten=False,new_physical_episodes=0,reserved_source_outcomes_read=False,
                implementation_sha256=sha(Path(__file__)))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('labels','alignment','shared','exporter','consumer-auditor','output'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():p.error('Refusing to overwrite release record')
    result=release(a.labels,a.alignment,a.shared,a.exporter,a.consumer_auditor)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print('Released exact increment for '+result['permissions']['role']+' only')


if __name__=='__main__':main()
