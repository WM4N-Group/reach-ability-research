"""Record query-level errors around the unchanged official frozen-head scorer."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('evaluator','views','labels-index','training-v1','training-v2','score-output','capture-output'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    if a.score_output.exists() or a.capture_output.exists():p.error('Refusing to overwrite case evidence')
    spec=importlib.util.spec_from_file_location('reach_official_frozen_auxiliary',a.evaluator)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    schemas=[json.loads(path.read_text())['schema'] for path in (a.training_v1,a.training_v2)]
    schedule=[(schema,h,j,name) for schema in schemas for h,j in ((.4,0),(1.,1))
              for name in ('current_margin','full_history_linear_residual','history_gru','current_state_mlp')]
    original=module.grouped_mae;calls=[];records=[]

    def record_errors(errors,data,valid):
        if len(calls)>=len(schedule):raise ValueError('Official scorer call order changed')
        schema,h,column,name=schedule[len(calls)]
        metric=original(errors,data,valid)
        calls.append(dict(training_schema=schema,horizon_s=h,predictor=name,metric=metric))
        for i in valid.nonzero().flatten().tolist():
            clock=float(data['t'][i]);query=round(clock*10)/10
            truth=float(data['margins'][i,column]);error=float(errors[i])
            records.append(dict(training_schema=schema,horizon_s=h,predictor=name,
                episode_id=data['episode_ids'][i],group_id=data['groups'][i],
                query_time_s=query,model_clock_float32_s=clock,target_margin_m=truth,
                predicted_margin_m=truth+error,error_m=error,
                current_margin_m=float(data['history'][i,-1,-1]),
                role='development_calibration',observed_legal_contact=bool(data['post'][i])))
        return metric

    module.grouped_mae=record_errors
    sys.argv=[str(a.evaluator),'--views',str(a.views),'--labels-index',str(a.labels_index),
              '--training-v1',str(a.training_v1),'--training-v2',str(a.training_v2),'--output',str(a.score_output)]
    module.main()
    score=json.loads(a.score_output.read_text())
    if len(calls)!=len(schedule) or len(score['scores'])!=len(schedule):raise ValueError('Scoring coverage changed')
    for captured,actual in zip(calls,score['scores']):
        if any(captured[k]!=actual[k] for k in ('training_schema','horizon_s','predictor')):
            raise ValueError('Cannot attribute captured errors to official metric')
        if any(captured['metric'][k]!=actual[k] for k in captured['metric']):
            raise ValueError('Recording changed official aggregate')
    result=dict(schema='reach-v212-frozen-margin-query-errors-v1',
        purpose='Retrospective development case diagnostics; no new predictive or intervention validation',
        predictions=records,official_scoring_calls=len(calls),
        official_forward_and_fitting_logic_modified=False,
        instrumentation='Wrap grouped_mae after predictions, forward identical tensors and return unchanged result',
        neural_weights_modified=False,new_physical_episodes=0,reserved_groups_read=0)
    with a.capture_output.open('x') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
    print('Captured',len(records),'supported development query errors with unchanged official aggregates')


if __name__=='__main__':main()
