"""One preregistered tiny ridge pipeline; one fresh heldout evaluation, no control."""
import argparse,json,time
from pathlib import Path
import numpy as np
from .push_forecast_fit import fit,predict,metric
from .streams import sha,write_json

ALPHAS=(1e-4,1e-2,1.,100.)


def read(dataset,split):
    manifest=json.loads((dataset/'manifest.json').read_text());arrays={k:[] for k in ('full','kin','y','cv','clock')};ids=[]
    for r in manifest['rows']:
        if r['split']!=split or r['path'] is None:continue
        p=dataset/r['path']
        if sha(p)!=r['sha256']:raise ValueError('Dataset changed')
        with np.load(p,allow_pickle=False) as z:
            for k in arrays:arrays[k].append(z[k].copy())
            ids.extend([r['id']]*len(z['y']))
    if not ids:raise ValueError('No valid independent '+split+' data')
    return {k:np.concatenate(v).astype(float) for k,v in arrays.items()},np.array(ids)


def score(y,p,ids):
    result=metric(y[:,:4],p[:,:4]);result['failure_Brier']=float(np.mean((np.clip(p[:,4:],0.,1.)-y[:,4:])**2))
    rmses=[];briers=[]
    for ep in sorted(set(ids)):
        mask=ids==ep;rmses.append(metric(y[mask,:4],p[mask,:4])['vector_RMSE_m']);briers.append(float(np.mean((np.clip(p[mask,4:],0.,1.)-y[mask,4:])**2)))
    result['episode_equal_RMSE_m']=float(np.mean(rmses));result['episode_equal_Brier']=float(np.mean(briers));result['validation_composite']=float(np.mean(rmses)+.01*np.sqrt(np.mean(briers)))
    return result


def clock_fit(tr,weights):
    bins=np.round(tr['clock']/.1).astype(int);keys=np.unique(bins)
    return dict(bins=keys,values=np.array([np.average(tr['y'][bins==k],axis=0,weights=weights[bins==k]) for k in keys]))


def clock_predict(model,times):
    query=np.round(times/.1).astype(int)
    return np.array([model['values'][np.argmin(abs(model['bins']-key))] for key in query])


def train(dataset,output):
    dataset=Path(dataset);output=Path(output);manifest=json.loads((dataset/'manifest.json').read_text())
    if not manifest['coverage_pass']:raise ValueError('Registered train moving/failure coverage insufficient; no fit or added cases')
    output.mkdir(exist_ok=False);began=time.monotonic()
    with (output/'training.claim').open('x') as f:f.write('One pipeline; eight preregistered fits; no test loading\n')
    tr,tri=read(dataset,'train');va,vai=read(dataset,'validation')
    groups,counts=np.unique(tri,return_counts=True);lookup=dict(zip(groups,counts));weights=np.array([len(tri)/(len(groups)*lookup[ep]) for ep in tri])
    selections={};winners={}
    for key in ('full','kin'):
        candidates=[]
        for alpha in ALPHAS:
            if time.monotonic()-began>300:raise TimeoutError('Registered 300s CPU training budget')
            model=fit(tr[key],tr['y'],alpha,weights);s=score(va['y'],predict(model,va[key]),vai);candidates.append((s['validation_composite'],alpha,model,s))
        winner=min(candidates,key=lambda row:(row[0],row[1]));winners[key]=winner[2];np.savez(output/(key+'-checkpoint.npz'),**winner[2])
        selections[key]=dict(alpha=winner[1],validation=winner[3],candidates=[dict(alpha=a,validation=s) for _,a,_,s in candidates])
    clock=clock_fit(tr,weights);np.savez(output/'clock-checkpoint.npz',**clock);mean=np.average(tr['y'],axis=0,weights=weights);np.save(output/'train-only-mean.npy',mean)
    primary=min(selections,key=lambda k:(selections[k]['validation']['validation_composite'],k))
    result=dict(schema='terminated-option-small-training-v2',pipeline_runs=1,preregistered_ridge_fits=8,primary_selected_on_validation=primary,selection=selections,train_queries=len(tri),validation_queries=len(vai),train_episodes=sorted(set(tri)),validation_episodes=sorted(set(vai)),test_loaded_during_training=False,
        dataset_manifest_sha256=sha(dataset/'manifest.json'),checkpoint_sha256={name:sha(output/name) for name in ('full-checkpoint.npz','kin-checkpoint.npz','clock-checkpoint.npz','train-only-mean.npy')},wall_seconds=time.monotonic()-began,skill_weights_modified=False,physics_steps=0,WM_control=False,failure_head='clipped ridge failure score, NOT a calibrated probability',target='displacement until min(query+h,first PUSH exit), failure within h')
    write_json(output/'training.json',result);print(json.dumps(result))


def evaluate(dataset,output):
    dataset=Path(dataset);output=Path(output);trained=json.loads((output/'training.json').read_text())
    if sha(dataset/'manifest.json')!=trained['dataset_manifest_sha256']:raise ValueError('Dataset changed before sealed test')
    for n,h in trained['checkpoint_sha256'].items():
        if sha(output/n)!=h:raise ValueError('Model/preprocessing changed before heldout')
    with (output/'heldout-evaluation.claim').open('x') as f:f.write('Unique evaluation of new test; no model selection or refit\n')
    models={}
    for key in ('full','kin','clock'):
        with np.load(output/(key+'-checkpoint.npz'),allow_pickle=False) as z:models[key]={n:z[n].copy() for n in z.files}
    test,ids=read(dataset,'test');mean=np.load(output/'train-only-mean.npy',allow_pickle=False);preds={}
    preds['zero']=np.tile(np.r_[np.zeros(4),mean[4:]],(len(ids),1));preds['train_mean']=np.tile(mean,(len(ids),1));preds['public_CV']=np.c_[test['cv'],np.tile(mean[4:],(len(ids),1))]
    preds['train_only_clock']=clock_predict(models['clock'],test['clock'])
    for k in ('full','kin'):preds[k]=predict(models[k],test[k])
    metrics={k:score(test['y'],p,ids) for k,p in preds.items()};per={ep:{k:score(test['y'][ids==ep],p[ids==ep],ids[ids==ep]) for k,p in preds.items()} for ep in sorted(set(ids))}
    primary=trained['primary_selected_on_validation'];delta=np.array([per[e][primary]['episode_equal_RMSE_m']-per[e]['train_only_clock']['episode_equal_RMSE_m'] for e in per]);rng=np.random.default_rng(20261025);boot=np.array([delta[rng.integers(0,len(delta),len(delta))].mean() for _ in range(2000)])
    result=dict(schema='terminated-option-fresh-heldout-v2',test_episode_ids=sorted(set(ids)),test_queries=len(ids),primary_selected_without_test=primary,metrics=metrics,per_episode=per,primary_minus_clock_episode_RMSE_m=float(delta.mean()),episode_bootstrap95_RMSE_difference_m=np.quantile(boot,[.025,.975]).tolist(),
        outperforms_clock_point_estimate=metrics[primary]['episode_equal_RMSE_m']<metrics['train_only_clock']['episode_equal_RMSE_m'],failure_score_better_than_clock=metrics[primary]['episode_equal_Brier']<metrics['train_only_clock']['episode_equal_Brier'],
        independent_test_episodes_only=len(per),general_world_model_effectiveness_validated=False,warning='Three heldout episodes are an engineering pilot, not broad statistical/safety or closed-loop planning certification. No post-exit recovery motion is a continued-PUSH label.',
        old_heldout_data_reused=False,heldout_model_selection=False,physics_steps=0,WM_control=False)
    write_json(output/'heldout-results.json',result);np.savez_compressed(output/'heldout-predictions.npz',truth=test['y'],episode_ids=ids,**preds);print(json.dumps(result))

if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('mode',choices=('train','evaluate'));a.add_argument('--dataset',type=Path,required=True);a.add_argument('--output',type=Path,required=True);p=a.parse_args();(train if p.mode=='train' else evaluate)(p.dataset,p.output)
