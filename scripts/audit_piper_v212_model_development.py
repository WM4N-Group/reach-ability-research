"""Read-only provenance, grouped-metric and label-coverage audit of published model scores."""
from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path

from bind_piper_v212_registry import read,sha


def verify_metric(metric,role_by_episode,expected_role):
    grouped=defaultdict(list);queries=0
    for episode,value in metric['per_episode'].items():
        if role_by_episode.get(episode)!=(expected_role,value['group_id']):
            raise ValueError('Scored episode role/group differs from canonical split')
        if type(value['queries']) is not int or value['queries']<=0:
            raise ValueError('Invalid supported query count')
        if not math.isfinite(value['mae']) or value['mae']<0:
            raise ValueError('Invalid episode MAE')
        queries+=value['queries'];grouped[value['group_id']].append(value['mae'])
    expected=(sum(sum(v)/len(v) for v in grouped.values())/len(grouped)) if grouped else None
    if metric['queries']!=queries or metric['episodes']!=len(metric['per_episode']) or metric['groups']!=len(grouped):
        raise ValueError('Reported query/episode/group denominator differs')
    actual=metric['group_equal_mae']
    if (expected is None and actual is not None) or (expected is not None and
            (actual is None or not math.isclose(actual,expected,abs_tol=1e-10,rel_tol=0))):
        raise ValueError('Group-equal MAE not reproducible; empty support must stay unknown')
    return abs(actual-expected) if expected is not None else 0.


def compare_primary(metrics):
    by_name={m['predictor']:m for m in metrics}
    required=('history_gru','current_state_mlp','full_linear_history')
    if any(name not in by_name for name in required):
        raise ValueError('Primary comparison is missing a strong reference or neural model')
    supports=[{ep:v['queries'] for ep,v in by_name[name]['per_episode'].items()} for name in required]
    if supports[1:]!=[supports[0],supports[0]]:
        raise ValueError('Predictors do not share the same episode/query support')
    errors={name:by_name[name]['group_equal_mae'] for name in required}
    return dict(mae_m=errors,gru_better_than_linear=errors['history_gru']<errors['full_linear_history'],
                mlp_better_than_linear=errors['current_state_mlp']<errors['full_linear_history'])


def audit(root,split_path,world_scripts):
    lock=read(root/'study-lock-v1.json');inventory=read(root/'download-inventory.json')
    split=read(split_path);role_by_episode={}
    for group,info in split['measured_groups'].items():
        for ep in info['episodes']:role_by_episode[ep]=(info['role'],group)
    for item in inventory:
        path=root/item['path']
        if not path.resolve().is_relative_to(root.resolve()) or sha(path)!=item['sha256']:
            raise ValueError('Transport inventory mismatch')
    for name,expected in lock['files'].items():
        if sha(root/name)!=expected:raise ValueError('Locked study artifact changed')
    for item in lock['models']:
        local=root/item['study']/Path(item['path']).name
        if sha(local)!=item['sha256']:raise ValueError('Frozen model checkpoint mismatch')
    for name,expected in lock['scorers'].items():
        if sha(world_scripts/name)!=expected:raise ValueError('Locked scoring code changed')
    views=read(root/'fitting-views-v2.json');views_sha=sha(root/'fitting-views-v2.json')
    support=[]
    for ep in views['episodes']:
        if ep['role'] not in ('train','development_calibration') or role_by_episode.get(ep['episode_id'])!=(ep['role'],ep['group_id']):
            raise ValueError('Fitting view has unsupported or mismatched role')
        support.append(dict(episode_id=ep['episode_id'],role=ep['role'],group_id=ep['group_id'],
            auxiliary_observed_targets=sum(value is not None for pair in ep['auxiliary_margin_targets'] for value in pair)))
    studies=[];verified_metrics=0;max_diff=0.
    for directory,score_name,scorer in (
            ('fit','development-score-v1.json','evaluate_v212_recurrent.py'),
            ('fit-feedback-v2','development-score-feedback-v2.json','evaluate_v212_feedback_v2.py')):
        training=read(root/directory/'training.json');score=read(root/score_name)
        if training['views_sha256']!=views_sha or score['views_sha256']!=views_sha or score['training_sha256']!=sha(root/directory/'training.json'):
            raise ValueError('Study and score use different views/training files')
        if score['evaluator_sha256']!=lock['scorers'][scorer]:raise ValueError('Scorer identity mismatch')
        if training['held_out_groups_used_for_training']!=0 or training['model_action_authority'] or score['reserved_groups_read']!=0:
            raise ValueError('Unexpected study authority or reserved exposure')
        for name,expected in training['source_hashes'].items():
            if sha(world_scripts/name)!=expected:raise ValueError('Training source identity mismatch')
        for role in score['results']:
            if role['role'] not in ('train','development_calibration'):raise ValueError('Unexpected scored role')
            for key in ('scores','secondary_state_scores','auxiliary_scores','completion_time_scores'):
                for metric in role[key]:
                    max_diff=max(max_diff,verify_metric(metric,role_by_episode,role['role']));verified_metrics+=1
        dev=next(v for v in score['results'] if v['role']=='development_calibration')
        primary={}
        for mode in ('free_rollout','real_feedback_at_0.4_then_recursive'):
            values=[s for s in dev['scores'] if s['mode']==mode and s['horizon_s']==1. and s['phase']=='legal_contact_observed']
            if {s['queries'] for s in values}!={20} or {s['groups'] for s in values}!={2}:
                raise ValueError('Primary comparison does not have matched support')
            primary[mode]=[{k:s[k] for k in ('predictor','group_equal_mae','queries','groups','per_episode')} for s in values]
        aux=dev['auxiliary_scores']
        studies.append(dict(study=directory,score_file=dict(path=str(root/score_name),sha256=sha(root/score_name)),
            primary=primary,auxiliary_development_supported_queries=sum(s['queries'] for s in aux),
            auxiliary_development_scores_available=any(s['group_equal_mae'] is not None for s in aux),
            primary_comparisons={mode:compare_primary(metrics) for mode,metrics in primary.items()},
            auxiliary_training_groups=training['auxiliary_training_groups'],
            interpretation='Development iteration, not an independent diagnostic test'))
    return dict(schema='reach-v212-world-model-development-audit-v1',
        scope='Artifact identity, grouped-score arithmetic and label coverage; network inference was not rerun',
        source_root=str(root.resolve()),study_lock=dict(path=str(root/'study-lock-v1.json'),sha256=sha(root/'study-lock-v1.json')),
        split=dict(path=str(split_path),sha256=sha(split_path),policy=split['version']),
        transport_files_verified=len(inventory),locked_model_files_verified=len(lock['models']),
        metric_rows_verified=verified_metrics,max_group_aggregation_error=max_diff,
        view_auxiliary_support=support,studies=studies,new_physical_episodes=0,new_training_runs=0,
        reserved_source_outcomes_read=False,analysis_sha256=sha(Path(__file__)),
        any_neural_better_than_full_linear=any(
            c['gru_better_than_linear'] or c['mlp_better_than_linear']
            for study in studies for c in study['primary_comparisons'].values()),
        auxiliary_development_available=any(study['auxiliary_development_scores_available'] for study in studies),
        limitations=['Only two development groups and 20 primary windows; no independent test result.',
          'A missing auxiliary development target produces unavailable MAE, never zero error.',
          'Later label releases do not retroactively change these frozen views or fitted models.',
          'No probability calibration, safety or online decision benefit inferred.'])


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('root','split','world-scripts','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():p.error('Refusing to overwrite audit')
    result=audit(a.root,a.split,a.world_scripts)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
    print('Verified',result['metric_rows_verified'],'metric rows; no inference/training or reserved outcomes read')


if __name__=='__main__':main()
