"""Audit the isolated remote supplementary evaluation of already-frozen margin heads."""
import argparse
import json
import math
from pathlib import Path

from bind_piper_v212_registry import read,sha
from audit_piper_v212_model_development import verify_metric


def verify_exit_status(status):
    if status['returncode']!=0 or not status['all_expected_sources_unchanged'] or status['changed_sources']:
        raise ValueError('Evaluation did not complete with frozen sources')


def audit(run,release_path,reference_path,model_root,split_path):
    status=read(run/'exit-status.json');plan=read(run/'plan.json');score=read(run/'score.json');release=read(release_path)
    verify_exit_status(status)
    launch=read(run/'launch.json');transport=read(run/'labels-index-transport.json')
    if sha(run/'plan.json')!=launch['plan_sha256']:
        raise ValueError('Executed plan differs from recorded launch')
    if not (transport['transport_source_index_sha256']==score['labels_index_sha256']==plan['source_index_sha256']):
        raise ValueError('Consumer source-index snapshot differs')
    if sha(run/'development-release.json')!=sha(release_path):
        raise ValueError('Transport release differs from canonical evaluation permission')
    if sha(run/'score.json')!=status['score_sha256']:
        raise ValueError('Remote score checksum mismatch')
    if not release['development_evaluation_released'] or release['training_released']:
        raise ValueError('Development labels must be evaluation-only')
    if (score['neural_weights_modified'] or score['new_labels_used_for_neural_fitting']
            or score['reserved_groups_read'] or score['physical_episodes_added']):
        raise ValueError('Unexpected training, reserved exposure or physical activity')
    if sha(run/'evaluate_v212_auxiliary_frozen.py')!=score['evaluator_sha256']:
        raise ValueError('Scoring code mismatch')
    if score['original_views_sha256']!=sha(model_root/'fitting-views-v2.json'):
        raise ValueError('Frozen fitting view changed')
    if [e['sha256'] for e in score['released_development_labels']]!=[release['labels']['sha256']]:
        raise ValueError('Scored labels differ from released development sources')
    if sha(run/'development-labels.json')!=release['labels']['sha256']:
        raise ValueError('Transport development labels changed')
    for item in score['training_receipts']:
        local=model_root/Path(item['path']).parent.name/Path(item['path']).name
        if sha(local)!=item['sha256']:
            raise ValueError('Neural training receipt changed')
    split=read(split_path);roles={ep:(info['role'],g) for g,info in split['measured_groups'].items() for ep in info['episodes']}
    reference=read(reference_path)['roles']['development_calibration']['metrics'];groups={}
    for metric in score['scores']:
        verify_metric(metric,roles,'development_calibration')
        h=metric['horizon_s'];key=(metric['training_schema'],h)
        groups.setdefault(key,{})[metric['predictor']]=metric
    results=[]
    for (study,h),metrics in groups.items():
        supports=[{ep:v['queries'] for ep,v in m['per_episode'].items()} for m in metrics.values()]
        if any(s!=supports[0] for s in supports):raise ValueError('Predictors have different query support')
        current=metrics['current_margin'];linear=metrics['full_history_linear_residual']
        original=next(m for m in reference if m['horizon_s']==h)['phases']['legal_contact_seen']
        if current['queries']!=original['query_count'] or not math.isclose(current['group_equal_mae'],original['mean_group_mae_m'],abs_tol=1e-7):
            raise ValueError('Current-value reference differs from original label-side diagnostic')
        results.append(dict(study=study,horizon_s=h,queries=current['queries'],groups=current['groups'],
             predictors=metrics,linear_improvement_over_current_m=current['group_equal_mae']-linear['group_equal_mae'],
             gru_better_than_linear=metrics['history_gru']['group_equal_mae']<linear['group_equal_mae'],
             mlp_better_than_linear=metrics['current_state_mlp']['group_equal_mae']<linear['group_equal_mae']))
    return dict(schema='reach-v212-frozen-margin-evaluation-audit-v1',
        run_directory=str(run.resolve()),remote_directory=plan['remote_root'],
        files={n:dict(path=str((run/n).resolve()),sha256=sha(run/n)) for n in
            ('plan.json','launch.json','exit-status.json','score.json','run.log','evaluate_v212_auxiliary_frozen.py','labels-index-transport.json','development-release.json')},
        development_release=dict(path=str(release_path),sha256=sha(release_path)),
        original_reference=dict(path=str(reference_path),sha256=sha(reference_path)),
        grouped_metric_rows_checked=len(score['scores']),metric_rows=results,
        first_attempt=dict(path=str((run.parent/'frozen-margin-dev-v1/exit-status.json').resolve()),
            sha256=sha(run.parent/'frozen-margin-dev-v1/exit-status.json'),
            outcome='launch cwd could not resolve relative checkpoint paths; no score or model change'),
        neural_training_runs_added=0,linear_reference='Fit only original P0 auxiliary labels, unchanged alpha .01; dev labels used only to score',
        physical_episodes_added=0,reserved_outcomes_read=False,
        limitations=['Supplementary evaluation on two previously used development groups, not independent test or calibration.',
            'All trajectories succeed and do not identify failure recall or intervention benefit.',
            'Observed maximum optimism is not a calibrated uncertainty bound or a deployable safety margin.',
            'Neural weights and prior box-displacement scores remain frozen.'],analysis_sha256=sha(Path(__file__)))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('run','release','reference','model-root','split','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():p.error('Refusing to overwrite frozen-evaluation audit')
    result=audit(a.run,a.release,a.reference,a.model_root,a.split)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
    print('Verified',result['grouped_metric_rows_checked'],'frozen-head development metrics; no neural retraining')


if __name__=='__main__':main()
