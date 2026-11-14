"""Trace retrospective margin error cases and isolate actual-state sampling effects."""
from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path

from bind_piper_v212_registry import read,sha
from export_piper_v212_labels import load_geometry
from audit_piper_v212_phase_reference import summarize


def sampling_decomposition(dense_values,predicted_margin,stride):
    if not dense_values or stride<=0 or (len(dense_values)-1)%stride:
        raise ValueError('Window endpoints must align to both sample grids')
    dense=min(dense_values);coarse=min(dense_values[::stride]);gap=coarse-dense
    return dict(actual_dense_min_m=dense,actual_coarse_min_m=coarse,coarse_optimistic_gap_m=gap,
                prediction_error_dense_m=predicted_margin-dense,
                prediction_error_coarse_m=predicted_margin-coarse,
                decomposition_residual_m=(predicted_margin-dense)-(predicted_margin-coarse)-gap)


def audit(run,labels_path,source_root,split_path):
    status=read(run/'exit-status.json');capture=read(run/'query-errors.json');score=read(run/'score.json')
    if status['returncode'] or status['changed_sources'] or not status['official_score_rows_identical']:
        raise ValueError('Query recording did not preserve official frozen scores')
    if sha(run/'query-errors.json')!=status['query_errors_sha256'] or sha(run/'score.json')!=status['score_sha256']:
        raise ValueError('Remote recording checksum mismatch')
    plan=read(run/'plan.json');original_path=run.parent/'frozen-margin-dev-v1r1/score.json'
    if sha(original_path)!=status['original_score_sha256'] or sha(original_path)!=plan['original_score_sha256']:
        raise ValueError('Original frozen score changed')
    if read(original_path)['scores']!=score['scores']:
        raise ValueError('Error recording changed original official scoring rows')
    if sha(run/'capture_piper_v212_frozen_margin.py')!=plan['expected_files'][plan['remote_root']+'/capture_piper_v212_frozen_margin.py']:
        raise ValueError('Recording wrapper differs from executed plan')
    labels=read(labels_path);episodes={e['episode_id']:e for e in labels['episodes']};split=read(split_path)
    for ep in episodes.values():
        info=split['measured_groups'].get(ep['group_id'],{})
        if ep['owner_recorded_role']!='development_calibration' or info.get('role')!='development_calibration' or ep['episode_id'] not in info.get('episodes',[]):
            raise ValueError('Only existing development sources can be read')
    captured=defaultdict(list)
    for row in capture['predictions']:
        if row['episode_id'] not in episodes or row['group_id']!=episodes[row['episode_id']]['group_id'] or not row['observed_legal_contact']:
            raise ValueError('Captured record outside declared development support')
        captured[(row['training_schema'],row['horizon_s'],row['predictor'])].append(row)
    for metric in score['scores']:
        rows=captured[(metric['training_schema'],metric['horizon_s'],metric['predictor'])]
        grouped=summarize([(r['group_id'],r['episode_id'],r['error_m']) for r in rows])
        if grouped['query_count']!=metric['queries'] or not math.isclose(grouped['mean_group_mae_m'],metric['group_equal_mae'],abs_tol=1e-7):
            raise ValueError('Captured query errors do not reproduce official metric')
    geometry,provenance=load_geometry(source_root)
    import numpy as np
    source_states={};margins={}
    for key,ep in episodes.items():
        path=Path(ep['source_path'])
        if sha(path)!=ep['source_sha256']:raise ValueError('Actual-state source changed')
        intervals=[json.loads(line) for line in path.read_text().splitlines()]
        meta=read(path.parent/'sequence-meta.json');slots=[meta['joint_names'].index(f'joint{i}') for i in range(1,7)]
        states=[r['before'] for r in intervals]+[intervals[-1]['after']]
        source_states[key]=(states,meta)
        margins[key]=[float(geometry.clearance(np.asarray([s['joint_position_rad'][i] for i in slots])))-.035 for s in states]
    primary=[r for r in capture['predictions'] if r['training_schema']=='world-model-v212-recurrent-training-v1']
    windows={}
    for r in primary:
        ep=r['episode_id'];q=r['query_time_s'];h=r['horizon_s'];key=(ep,q,h)
        if key in windows:continue
        dt=source_states[ep][1]['control_dt_s'];start=round(q/dt);length=round(h/dt)
        values=margins[ep][start:start+length+1]
        if len(values)!=length+1:raise ValueError('Retrospective window is incomplete')
        d=sampling_decomposition(values,r['predicted_margin_m'],round(.1/dt))
        if not math.isclose(d['actual_dense_min_m'],r['target_margin_m'],abs_tol=1e-7):
            raise ValueError('Actual-state geometry differs from captured target')
        windows[key]=dict(episode_id=ep,group_id=episodes[ep]['group_id'],query_time_s=q,horizon_s=h,
            dense_dt_s=dt,coarse_dt_s=.1,actual_dense_min_m=d['actual_dense_min_m'],actual_coarse_min_m=d['actual_coarse_min_m'],
            coarse_optimistic_gap_m=d['coarse_optimistic_gap_m'],min_time_s=(start+values.index(min(values)))*dt,
            relative_times_s=[i*dt for i in range(len(values))],actual_margin_trace_m=values)
    chosen=[]
    for method,ep in (('full_history_linear_residual','p1-reset-5309'),('history_gru','p1-reset-5309'),
                      ('full_history_linear_residual','p1-reset-5310')):
        candidate=max((r for r in primary if r['horizon_s']==1. and r['predictor']==method and r['episode_id']==ep),key=lambda r:r['error_m'])
        window=windows[(ep,candidate['query_time_s'],1.)]
        start=round(candidate['query_time_s']/source_states[ep][1]['control_dt_s'])
        forecasts=[r for r in primary if r['horizon_s']==1. and r['episode_id']==ep and r['query_time_s']==candidate['query_time_s']]
        chosen.append(dict(selection=f'Retrospective maximum optimistic {method} error within {ep}',
            window=window,predictions=forecasts,
            source_trace=dict(path=episodes[ep]['source_path'],sha256=episodes[ep]['source_sha256'],
                query_step=start,minimum_step=round(window['min_time_s']/source_states[ep][1]['control_dt_s'])),
            selected_predictor=method,decomposition=sampling_decomposition(window['actual_margin_trace_m'],candidate['predicted_margin_m'],5),
            observed_controller_at_query=source_states[ep][0][start]['controller_observed']))
    temporal=[]
    for h in (.4,1.):
        rows=[w for w in windows.values() if w['horizon_s']==h]
        temporal.append(dict(horizon_s=h,**summarize([(w['group_id'],w['episode_id'],w['coarse_optimistic_gap_m']) for w in rows])))
    return dict(schema='reach-v212-retrospective-margin-cases-v1',
        run_directory=str(run.resolve()),plan=dict(path=str(run/'plan.json'),sha256=sha(run/'plan.json')),
        wrapper=dict(path=str(run/'capture_piper_v212_frozen_margin.py'),sha256=sha(run/'capture_piper_v212_frozen_margin.py')),
        original_official_score=dict(path=str(original_path),sha256=sha(original_path)),capture=dict(path=str(run/'query-errors.json'),sha256=sha(run/'query-errors.json')),
        frozen_score=dict(path=str(run/'score.json'),sha256=sha(run/'score.json')),remote_exit_status=dict(path=str(run/'exit-status.json'),sha256=sha(run/'exit-status.json')),
        development_labels=dict(path=str(labels_path),sha256=sha(labels_path)),geometry_provenance=provenance,
        official_scores_reproduced=True,captured_prediction_rows=len(capture['predictions']),
        evaluator_grid_diagnostic=temporal,cases=chosen,
        interpretation='Dense-error = same prediction minus privileged true coarse minimum + true coarse/dense sampling gap',
        cases_selected_after_observing_errors=True,neural_weights_modified=False,new_physical_episodes=0,reserved_outcomes_read=False,
        limitations=['Only retrospective examples in two exposed development groups; not online warning selection or independent validation.',
          'Actual coarse/dense future values are privileged diagnostics only, never model inputs.',
          'Grid sensitivity does not measure all joint-state/model errors or prove the cause of remaining prediction bias.',
          'Empirical maximum optimistic errors are not calibrated safety reserves.'],analysis_sha256=sha(Path(__file__)))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('run','labels','source-root','split','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():p.error('Refusing to overwrite error cases')
    result=audit(a.run,a.labels,a.source_root,a.split)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
    for c in result['cases']:
        print(c['selected_predictor'],c['window']['episode_id'],c['window']['query_time_s'],
              {k:round(v*1000,6) for k,v in c['decomposition'].items()})


if __name__=='__main__':main()
