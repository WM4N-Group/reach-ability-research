"""One bounded closed-form training pipeline + one sealed heldout evaluation.
NOT the M/RSSM architecture, not a skill policy, no physics or planner authority.
"""
import argparse,json,time
from pathlib import Path
import numpy as np
from .streams import write_json,sha

ALPHAS=(.0001,.001,.01,.1)

def metric(y,p):
    e=(p-y).reshape(-1,2,2)
    return dict(mean_abs_coordinate_m=float(abs(e).mean()),vector_RMSE_m=float(np.sqrt((e**2).sum(2).mean())),
        per_horizon_vector_RMSE_m=np.sqrt((e**2).sum(2).mean(0)).tolist(),per_coordinate_MAE_m=abs(e).mean(0).tolist())

def fit(x,y,alpha,weights=None):
    mean=x.mean(0);scale=np.maximum(x.std(0),.05);z=np.clip((x-mean)/scale,-10,10)/np.sqrt(x.shape[1])
    weights=np.ones(len(z)) if weights is None else np.asarray(weights)
    ym=np.average(y,axis=0,weights=weights);sw=np.sqrt(weights)[:,None];zw=z*sw
    dual=np.linalg.solve(zw@zw.T+alpha*len(z)*np.eye(len(z)),(y-ym)*sw);w=zw.T@dual
    return dict(mean=mean,scale=scale,w=w,ymean=ym)

def predict(m,x):return np.clip((x-m['mean'])/m['scale'],-10,10)/np.sqrt(x.shape[1])@m['w']+m['ymean']

def read_split(dataset,split):
    manifest=json.loads((dataset/'manifest.json').read_text());a={k:[] for k in ('full','kin','y','cv')};ids=[]
    for r in manifest['rows']:
        if r['split']!=split or r['path'] is None:continue
        p=dataset/r['path']
        if sha(p)!=r['sha256']:raise ValueError('Dataset chunk changed after admission')
        with np.load(p,allow_pickle=False) as z:
            for k in a:a[k].append(z[k])
            ids.extend([r['id']]*len(z['y']))
    return {k:np.concatenate(v).astype(float) for k,v in a.items()},np.array(ids)

def episode_balanced_rmse(y,p,ids):
    return float(np.mean([metric(y[ids==ep],p[ids==ep])['vector_RMSE_m'] for ep in sorted(set(ids))]))


def train(dataset,output):
    began=time.monotonic();dataset=Path(dataset);output=Path(output);output.mkdir(exist_ok=False)
    manifest=json.loads((dataset/'manifest.json').read_text())
    if not manifest['coverage_pass']:raise ValueError('Insufficient strict-valid independent episode coverage; do not train')
    # This function deliberately NEVER reads test rows/arrays.
    tr,tri=read_split(dataset,'train');va,vai=read_split(dataset,'validation');models={};selection={}
    groups,counts=np.unique(tri,return_counts=True);count=dict(zip(groups,counts));weights=np.array([len(tri)/(len(groups)*count[g]) for g in tri])
    for key in ('full','kin'):
        candidates=[]
        for alpha in ALPHAS:
            if time.monotonic()-began>300:raise TimeoutError('Frozen300wall training budget')
            model=fit(tr[key],tr['y'],alpha,weights);prediction=predict(model,va[key]);score=metric(va['y'],prediction);score['episode_balanced_vector_RMSE_m']=episode_balanced_rmse(va['y'],prediction,vai);candidates.append((score['episode_balanced_vector_RMSE_m'],alpha,model,score))
        winner=min(candidates,key=lambda x:(x[0],x[1]));models[key]=winner[2];selection[key]=dict(alpha=winner[1],validation=winner[3],candidates=[dict(alpha=a,validation=v) for _,a,_,v in candidates])
        np.savez(output/(key+'-checkpoint.npz'),**models[key])
    mean=np.average(tr['y'],axis=0,weights=weights);np.save(output/'train-only-mean.npy',mean)
    valpred=dict(zero=np.zeros_like(va['y']),train_mean=np.tile(mean,(len(va['y']),1)),public_constant_velocity=va['cv'],public_kinematics_ridge=predict(models['kin'],va['kin']))
    strongest=min(valpred,key=lambda k:episode_balanced_rmse(va['y'],valpred[k],vai))
    nonlearned=min(('zero','train_mean','public_constant_velocity'),key=lambda k:episode_balanced_rmse(va['y'],valpred[k],vai))
    best_learned=min(selection,key=lambda k:selection[k]['validation']['episode_balanced_vector_RMSE_m'])
    result=dict(schema='narrow-push-training-v1',model='public full-history ridge consequence baseline, NOT M/RSSM',
        dataset_manifest_sha256=sha(dataset/'manifest.json'),fit_calls=8,training_pipeline_runs=1,training_query_count=len(tr['y']),
        validation_query_count=len(va['y']),train_episodes=sorted(set(tri.tolist())),validation_episodes=sorted(set(vai.tolist())),
        selected=selection,strongest_baseline_selected_on_validation=strongest,
        best_learned_selected_on_validation=best_learned,strongest_nonlearned_selected_on_validation=nonlearned,
        validation_baselines={k:metric(va['y'],p) for k,p in valpred.items()},test_read_during_training=False,
        checkpoint_sha256={k:sha(output/(k+'-checkpoint.npz')) for k in models},train_mean_sha256=sha(output/'train-only-mean.npy'),wall_seconds=time.monotonic()-began,
        episode_balanced_train_weights=True,validation_selection_episode_balanced=True,optimizer_updates=0,closed_form_weight_fit=True,skill_weights_changed=False,physics_steps=0,control_authority=False)
    write_json(output/'training.json',result);print(json.dumps(result));return result


def evaluate(dataset,model_root):
    dataset=Path(dataset);model_root=Path(model_root)
    with (model_root/'heldout-evaluation.claim').open('x') as f:f.write('One test evaluation, never model selection\n')
    train_result=json.loads((model_root/'training.json').read_text())
    if sha(dataset/'manifest.json')!=train_result['dataset_manifest_sha256']:raise ValueError('Dataset changed')
    models={}
    for key in ('full','kin'):
        p=model_root/(key+'-checkpoint.npz')
        if sha(p)!=train_result['checkpoint_sha256'][key]:raise ValueError('Checkpoint changed before heldout')
        with np.load(p,allow_pickle=False) as z:models[key]={k:z[k].copy() for k in z.files}
    test,ids=read_split(dataset,'test');mean=np.load(model_root/'train-only-mean.npy',allow_pickle=False)
    if sha(model_root/'train-only-mean.npy')!=train_result['train_mean_sha256']:raise ValueError('Train mean changed')
    preds=dict(zero=np.zeros_like(test['y']),train_mean=np.tile(mean,(len(test['y']),1)),public_constant_velocity=test['cv'],public_kinematics_ridge=predict(models['kin'],test['kin']),learned_full_history=predict(models['full'],test['full']))
    metrics={k:metric(test['y'],p) for k,p in preds.items()};baseline=train_result['strongest_baseline_selected_on_validation'];per_episode={}
    for ep in sorted(set(ids)):
        mask=ids==ep;per_episode[ep]={k:metric(test['y'][mask],p[mask]) for k,p in preds.items()}
    # Episode-balanced bootstrap, never pretend overlapping query frames are independent.
    epnames=sorted(per_episode);delta=np.array([per_episode[e]['learned_full_history']['vector_RMSE_m']-per_episode[e][baseline]['vector_RMSE_m'] for e in epnames]);rng=np.random.default_rng(971)
    boot=np.array([delta[rng.integers(0,len(delta),len(delta))].mean() for _ in range(2000)]);ci=np.quantile(boot,[.025,.975])
    best_key='learned_full_history' if train_result['best_learned_selected_on_validation']=='full' else 'public_kinematics_ridge'
    rule=train_result['strongest_nonlearned_selected_on_validation']
    learned_delta=np.array([per_episode[e][best_key]['vector_RMSE_m']-per_episode[e][rule]['vector_RMSE_m'] for e in epnames])
    learned_boot=np.array([learned_delta[rng.integers(0,len(learned_delta),len(learned_delta))].mean() for _ in range(2000)]);learned_ci=np.quantile(learned_boot,[.025,.975])
    result=dict(schema='narrow-push-heldout-v1',test_queries=len(test['y']),test_episode_groups=epnames,metrics=metrics,per_episode=per_episode,
        best_learned_selected_without_test=best_key,strongest_nonlearned_selected_without_test=rule,
        best_learned_minus_nonlearned_episode_RMSE_m=float(learned_delta.mean()),
        best_learned_minus_nonlearned_episode_bootstrap95_m=learned_ci.tolist(),
        exploratory_learning_value_supported=bool(learned_ci[1]<0),
        baseline_selected_without_test=baseline,episode_balanced_RMSE_difference_model_minus_baseline_m=float(delta.mean()),
        episode_cluster_bootstrap95_RMSE_difference_m=ci.tolist(),outperforms_selected_baseline_point_estimate=bool(delta.mean()<0),
        robust_superiority_in_this_small_pilot=bool(ci[1]<0),test_used_for_hyperparameter_selection=False,
        moving_query_count=int((np.linalg.norm(test['y'][:,2:4],axis=1)>.01).sum()),
        moving_subset_metrics={k:metric(test['y'][np.linalg.norm(test['y'][:,2:4],axis=1)>.01],p[np.linalg.norm(test['y'][:,2:4],axis=1)>.01]) for k,p in preds.items()} if (np.linalg.norm(test['y'][:,2:4],axis=1)>.01).any() else None,
        stationary_subset_metrics={k:metric(test['y'][np.linalg.norm(test['y'][:,2:4],axis=1)<=.01],p[np.linalg.norm(test['y'][:,2:4],axis=1)<=.01]) for k,p in preds.items()} if (np.linalg.norm(test['y'][:,2:4],axis=1)<=.01).any() else None,
        full_RSSM_or_closed_loop_planning_validated=False,strict_physics_safety_certified=False,
        forward_model_scope='Only one fixed native PUSH continuation; no alternate action or closed-loop replanning efficacy claim')
    write_json(model_root/'heldout-results.json',result);np.savez_compressed(model_root/'heldout-predictions.npz',truth=test['y'],episode_ids=ids,**preds);print(json.dumps(result));return result


def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['train','evaluate']);p.add_argument('--dataset',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    (train if a.mode=='train' else evaluate)(a.dataset,a.output)
if __name__=='__main__':main()
