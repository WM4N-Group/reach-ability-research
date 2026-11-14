"""Export explicitly selected closed train or development episodes with separated purposes."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

from bind_piper_v212_registry import sha, read, verify_reference
from export_piper_shared_label_examples import label
from export_piper_v212_labels import load_geometry, normalize, auxiliary_queries


def select_closed_role(manifest, split, episode_ids, role):
    if role not in ('train', 'development_calibration'):
        raise ValueError('Only train or development roles are supported; reserved sources stay unread')
    if not episode_ids or len(set(episode_ids))!=len(episode_ids):
        raise ValueError('Explicit distinct episode IDs required')
    by_id={e['episode_id']:e for e in manifest['physical_episodes']}
    selected=[]
    for episode in episode_ids:
        item=by_id.get(episode,{})
        if item.get('role')!=role:
            raise ValueError('Requested role differs from explicitly registered episode role')
        group=split['measured_groups'].get(item.get('group_id'),{})
        if group.get('role')!=role or episode not in group.get('episodes',[]):
            raise ValueError('Measured split does not confirm requested role membership')
        if item.get('status')!='closed' or item.get('recorded') is not True:
            raise ValueError('Running, planned or unrecorded episodes cannot be exported')
        if item.get('skill_version')!='push-direct-approach-v212' or item.get('task_scope')!='original_reset_independent_push':
            raise ValueError('Unexpected task or skill domain')
        selected.append(item)
    return selected


def export(shared,source_root,world_scripts,episode_ids,role):
    registry_paths={name:shared/name for name in ('batch_manifest.json','group_split.json','label_contract_v1.json')}
    payloads={name:p.read_bytes() for name,p in registry_paths.items()}
    checksums={name:hashlib.sha256(raw).hexdigest() for name,raw in payloads.items()}
    manifest,split,contract=(json.loads(payloads[name]) for name in registry_paths)
    if manifest['owner']!='world_model' or split['owner']!='world_model':
        raise ValueError('Invalid registry owner')
    if manifest['group_split']['sha256']!=checksums['group_split.json'] or manifest['group_split']['version']!=split['version']:
        raise ValueError('Registry split drift')
    if contract['label_schema_version']!='reach-wm-v212-v1':
        raise ValueError('Label contract changed')
    selected=select_closed_role(manifest,split,episode_ids,role) # All roles checked before any raw reads.
    geometry,provenance=load_geometry(source_root)
    verify_reference(manifest['frozen_skill_inventory'])
    if manifest['frozen_skill_inventory']['sha256']!=provenance['manifest_sha256']:
        raise ValueError('Runtime differs from registered v212 inventory')
    sys.path.insert(0,str(world_scripts))
    from build_v212_sequences import build
    episodes=[]
    for item in selected:
        for key in ('report','sequence','metadata','startup'):verify_reference(item[key])
        root=Path(item['source_root']);built=build(root,role)
        if built['source_sequence_sha256']!=item['sequence']['sha256'] or built['source_report_sha256']!=item['report']['sha256']:
            raise ValueError('Source root differs from registered sequence or report')
        if built['group_id']!=item['group_id'] or len(built['times_s'])!=item['query_count']:
            raise ValueError('Actual source fingerprint or query count differs')
        meta=read(item['metadata']['path']);report=read(item['report']['path'])
        if meta['recorder_sha256']!=sha(world_scripts/'v212_sequence_recording.py'):
            raise ValueError('Recorder drift; update field mapping explicitly')
        if meta['evaluator_sha256']!=sha(source_root/'push-direct-approach-v212/train/scripts/evaluate_residual_push.py'):
            raise ValueError('Frozen evaluator drift')
        intervals=[json.loads(line) for line in Path(item['sequence']['path']).read_text().splitlines()]
        states,rows=normalize(intervals,meta,geometry)
        flags=intervals[-1]['termination_flags'];end=rows[-1]['time_s']
        success=flags.get('box_settled') is True and not any(v for k,v in flags.items() if k not in ('box_settled','time_out'))
        if success!=built['terminal_label']['success'] or success!=item['outcome']['verified_task_success']:
            raise ValueError('Terminal labels disagree')
        contact=next((r['time_s'] for r,s in zip(rows,states) if s['legal_hand_contact']
                      and not s['invalid_hand_contact'] and not s['forbidden_box_contact']),None)
        approach=next((r['time_s'] for r,s in zip(rows,states)
                       if s['controller_observed']['safe_approach_complete'] is True),None)
        not_entered=label(None,'not_entered_in_independent_push_task',end)
        queries=auxiliary_queries(states,rows,meta['control_dt_s'])
        if [q['query_time_s'] for q in queries]!=built['times_s']:
            raise ValueError('Query time differs from owner model sequence')
        episodes.append(dict(episode_id=item['episode_id'],skill_version=item['skill_version'],task_scope=item['task_scope'],
            source_path=item['sequence']['path'],source_sha256=item['sequence']['sha256'],report_sha256=item['report']['sha256'],
            skill_bundle_hash=provenance['manifest_sha256'],group_id=item['group_id'],group_split_version=split['version'],
            owner_recorded_role=role,execution_status='normal_completion' if success else
                 'normal_timeout' if flags.get('time_out') else 'native_termination',verified_task_success=success,
            actual_sample_period_s=meta['control_dt_s'],last_valid_observation_time_s=end,native_flags=flags,
            first_recorded_legal_contact_s=contact,first_recorded_safe_approach_complete_s=approach,
            sampled_actual_clearance_range_m=[min(r['clearance_m'] for r in rows),max(r['clearance_m'] for r in rows)],
            stages=dict(transition_complete=label(None,'no_nav_transition_in_independent_push',end),
                contact_established=label(contact is not None,None,contact if contact is not None else end,'observed_legal_contact'),
                push_complete=label(success,None,end,'native_terminal'),
                whole_task_complete=label(success,None,end,'native_terminal_independent_push_scope'),
                exit_complete=not_entered,next_skill_complete=not_entered),queries=queries))
    # Registry can append other episodes during offline geometry; selected sources must stay compatible.
    live_manifest=read(shared/'batch_manifest.json');live_split=read(shared/'group_split.json')
    current=select_closed_role(live_manifest,live_split,episode_ids,role)
    if current!=selected or live_split['version']!=split['version']:
        raise ValueError('Selected sources or policy changed while exporting')
    return dict(label_schema_version=contract['label_schema_version'],adapter_version='v212-registered-role-labels-v3',
        exporter_sha256=sha(Path(__file__)),field_mapping_kernel=dict(path=str(Path(__file__).with_name('export_piper_v212_labels.py')),
          sha256=sha(Path(__file__).with_name('export_piper_v212_labels.py'))),
        contract_sha256=checksums['label_contract_v1.json'],geometry_provenance=provenance,
        canonical_registry_snapshot_checksums=checksums,
        registry_snapshot_inputs={name:dict(path=str(registry_paths[name]),original_utf8=raw.decode('utf-8'))
                                  for name,raw in payloads.items()},
        group_split_version=split['version'],episodes=episodes,
        episode_count=len(episodes),new_physical_episodes=0,reserved_source_outcomes_read=False,
        dataset_role=role,allowed_purpose='weight_fitting_after_release' if role=='train' else 'development_evaluation_only_after_release',
        cross_group_alignment='new_increment_pending_consumer_check',training_released=False,evaluation_released=False,
        unsupported_sources='Planned, incomplete, exception or missing-record episodes remain in owner denominator; no labels invented')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('shared','source-root','world-scripts','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--episode-id',action='append',required=True)
    p.add_argument('--role',choices=('train','development_calibration'),required=True)
    a=p.parse_args()
    if a.output.exists():p.error('Refusing to overwrite label increment')
    result=export(a.shared,a.source_root,a.world_scripts,a.episode_id,a.role)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x') as stream:json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
    print('Exported explicit registered '+a.role+' increment; purpose-specific release remains pending')


if __name__=='__main__':main()
