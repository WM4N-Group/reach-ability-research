"""Document existing frozen auxiliary ridge scales without refitting any coefficient."""
import argparse
import hashlib
import json
from pathlib import Path
import torch


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('views','training','training-v2','old-score','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():p.error('Refusing to overwrite scaling provenance')
    torch.set_num_threads(2)
    from v212_learning_common import windows,fitting_weights,response_features
    import v212_learning_common
    views=json.loads(a.views.read_text());receipt=json.loads(a.training.read_text());receipt2=json.loads(a.training_v2.read_text())
    assert receipt['views_sha256']==receipt2['views_sha256']==sha(a.views)
    expected=receipt['source_hashes']['v212_learning_common.py'];assert sha(v212_learning_common.__file__)==expected
    checkpoints=[];stats=[]
    for training in (receipt,receipt2):
        record=training['models'][0];path=Path(record['path']);assert sha(path)==record['sha256']
        item=torch.load(path,map_location='cpu',weights_only=False);stats.append((item['mean'],item['std']))
        checkpoints.append(dict(path=str(path),sha256=record['sha256']))
    assert all(torch.equal(stats[0][i],stats[1][i]) for i in (0,1))
    mean,std=stats[0];data=windows(views,'train',cap=64);weights=fitting_weights(data)
    x=response_features(data,False,True,mean,std)
    raw=torch.cat((data['history'].flatten(1),data['t'][:,None]/48.,torch.ones(len(weights),1)),1)
    state_dims=len(mean);history_len=data['history'].shape[1]
    first_scale=torch.cat((std.repeat(history_len),torch.ones(2))).double()
    names=[f'history_{(k-history_len+1)*.1:.1f}s/{name}' for k in range(history_len) for name in data['names']]+['elapsed_s/48','bias']
    output=[]
    for h,j in ((.4,0),(1.,1)):
        valid=data['margin_mask'][:,j]>0;w=weights[valid].double();w=w/w.sum()
        z1=x[valid].double();raw_fit=raw[valid].double()
        center=(z1*w[:,None]).sum(0);second_std=((z1-center).square()*w[:,None]).sum(0).sqrt()
        second_scale=second_std.clamp_min(.001);second_scale[-1]=1.
        raw_center=(raw_fit*w[:,None]).sum(0);raw_std=((raw_fit-raw_center).square()*w[:,None]).sum(0).sqrt()
        raw_once=raw_std.clamp_min(.001);raw_once[-1]=1.
        effective=first_scale*second_scale;ratio=effective/raw_once
        variable=(raw_std>1e-12);variable[-2:]=False
        indices=sorted(variable.nonzero().flatten().tolist(),key=lambda k:float(ratio[k]))
        def row(k):return dict(feature=names[k],raw_training_std=float(raw_std[k]),first_state_scale=float(first_scale[k]),
            second_normalized_scale=float(second_scale[k]),old_effective_raw_scale=float(effective[k]),
            hypothetical_once_raw_scale=float(raw_once[k]),scale_ratio=float(ratio[k]))
        selected=[names.index('history_0.0s/box_angular_velocity_world_radps/1'),names.index('history_0.0s/actual_current_arm_base_clearance_margin_m')]
        output.append(dict(horizon_s=h,fit_queries=int(valid.sum()),fit_groups=len({data['groups'][i] for i in valid.nonzero().flatten().tolist()}),
            features=len(names),nonconstant_state_history_columns=int(variable.sum()),
            variable_columns_effectively_below_raw_0p001_floor=sum(float(effective[k])<.001 for k in indices),
            minimum_ratio_among_variable_columns=min((float(ratio[k]) for k in indices),default=None),
            lowest_ratio_examples=[row(k) for k in indices[:5]],declared_field_examples=[row(k) for k in selected]))
    result=dict(schema='reach-v212-frozen-margin-scaling-provenance-v1',protocol_id='v212-frozen-aux-ridge-nested-scaling-v1',
        sources=[dict(path=str(p),sha256=sha(p)) for p in (a.views,a.training,a.training_v2,a.old_score,Path(v212_learning_common.__file__))],
        checkpoint_stats_sources=checkpoints,normalizer_groups=receipt['training_groups'],auxiliary_target_groups=receipt['auxiliary_training_groups'],
        normalization_stats_equal_across_studies=True,feature_statistics=output,
        first_state_std_floor=.001,second_ridge_feature_std_floor=.001,ridge_alpha=.01,intercept_ridge=1e-8,
        effective_scale='D_i = state_scale_i * max(weighted_std_of_normalized_feature_i, .001)',
        raw_coefficient_regularizer='For non-intercept coefficients beta_i in raw coordinates, lambda * sum((D_i * beta_i)^2)',
        scope='Statistics of original training-only features; no coefficient, model, prediction, or ranking recomputed',
        old_scores_modified=False,coefficients_refit=False,development_windows_constructed=0,reserved_outcomes_read=False,
        neural_models_refit=False,physical_episodes_added=0,
        limitations=['Hypothetical single-raw-scale numbers are algebraic diagnostics, not a new fitted/evaluated predictor.',
          'A smaller effective scale is not by itself proof of actual auxiliary prediction instability.',
          'No box CV improvement or neural ranking is transferred to margin prediction.',
          'The shared numerical .001 floor spans fields with different units; it is not sensor noise or a safety reserve.'],analysis_sha256=sha(__file__))
    with a.output.open('x') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
    for r in output:print(r['horizon_s'],r['fit_queries'],r['fit_groups'],r['minimum_ratio_among_variable_columns'])


if __name__=='__main__':main()
