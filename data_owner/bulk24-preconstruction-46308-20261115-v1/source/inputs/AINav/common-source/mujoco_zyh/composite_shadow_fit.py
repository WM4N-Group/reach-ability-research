"""Causal NAV/PUSH/CLIMB consequence dataset and bounded shadow fit."""
import argparse
import json
from pathlib import Path
import time

import numpy as np

from .composite_shadow_study import plan
from .push_forecast_data import public_features,read_episode
from .push_forecast_fit import fit,predict
from .streams import sha,write_json

HORIZONS=(.4,.8)
SKILLS=('nav','push','climb')
SPEED=np.array([30.1,30.1,15.7]*4+[3.]*6)
ALPHAS=(1e-4,1e-2,1.,100.)


def same_option(boundaries,a,b):
    """An observed boundary may finish a skill; never label its successor as continuation."""
    left=boundaries[a];right=boundaries[b]
    return (left['skill'] in SKILLS and left['skill']==right['skill'] and
            left['task_index']==right['task_index'] and
            all(row['skill']==left['skill'] and row['task_index']==left['task_index']
                for row in boundaries[a:b+1]))


def body_xy_delta(origin,future,rotation):
    return ((np.asarray(future)-np.asarray(origin))@np.asarray(rotation)[:,:2]).tolist()


def extract_episode(ep,*,include_measured_unsafe=False):
    ep=Path(ep);closure=json.loads((ep/'episode/closure.json').read_text())
    if not closure['storage_complete'] or sha(ep/'episode/private-catalog.jsonl')!=closure['private_catalog_sha256'] or sha(ep/'episode/control-boundaries.jsonl')!=closure['control_boundaries_sha256']:
        raise ValueError('Closed real stream and exact private label source required')
    meta,report,v,c,cat=read_episode(ep)
    boundary=[json.loads(line) for line in (ep/'episode/control-boundaries.jsonl').read_text().splitlines()]
    ticks=v['control_ticks'];times=v['timestamps_s']
    if not (0<=len(boundary)*4-len(c['issued'])<4) or len(cat)!=len(times) or not np.array_equal(ticks,np.arange(len(ticks))*5):
        raise ValueError('Actual 50/200/10Hz streams do not align')
    limits=np.asarray(report['joint_position_limits_rad']);q=c['q_before'];dq=c['dq_before']
    safe=(q>=limits[:,0]).all(1)&(q<=limits[:,1]).all(1)&(abs(dq)<=SPEED).all(1)
    unsafe_prefix=np.r_[0,np.cumsum(~safe)];rows={k:[] for k in ('full','kin','y','cv','clock','skill','query_time_s','unsafe_future')}
    censor={};defect=lambda name:censor.__setitem__(name,censor.get(name,0)+1)
    for i in range(7,len(times),2):
        t=float(times[i]);tick=int(ticks[i]);start=tick*4
        if start<140 or start>len(c['issued']):defect('missing_past_motor');continue
        future=[];good=True;unsafe_future=False
        for horizon in HORIZONS:
            j=i+int(round(horizon*10))
            if j>=len(times):defect('missing_future_frame');good=False;break
            end=int(ticks[j])*4
            if end>len(c['issued']) or not same_option(boundary,tick,int(ticks[j])):
                defect('skill_boundary_or_incomplete_future');good=False;break
            if unsafe_prefix[end]-unsafe_prefix[start]:
                unsafe_future=True
                if not include_measured_unsafe:defect('measured_joint_range_or_speed');good=False;break
            future.append(j)
        if not good:continue
        past=np.stack((c['issued'][start-140:start],c['delayed'][start-140:start]),axis=1)
        if past.shape!=(140,2,5,18):raise ValueError('Incomplete past issued/delayed motor stream')
        history=slice(i-7,i+1)
        f,k,cv,_=public_features(v['rgb'][history],v['depth_m'][history,...,0],v['proprio'][history],
            v['actions_previous'][history],times[history],v['camera_K'],v['T_base_optical'],past,t)
        skill=boundary[tick]['skill'];onehot=np.array([skill==name for name in SKILLS],dtype=float)
        # Public control stage is known to the executing caller at query time.
        f=np.r_[f,onehot];k=np.r_[k,onehot]
        origin=cat[i];R=origin['R_world_from_body'];root=origin['root_position_world_m'];box=origin['objects'][0]['position_world_m']
        y=[]
        for j in future:
            target=cat[j]
            y.extend(body_xy_delta(root,target['root_position_world_m'],R))
            y.extend(body_xy_delta(box,target['objects'][0]['position_world_m'],R))
        root_vel=v['proprio'][i,42:44]
        baseline=np.r_[root_vel*.4,cv[:2],root_vel*.8,cv[2:]]
        rows['full'].append(f);rows['kin'].append(k);rows['y'].append(y);rows['cv'].append(baseline)
        rows['clock'].append(t);rows['skill'].append(SKILLS.index(skill));rows['query_time_s'].append(t)
        rows['unsafe_future'].append(int(unsafe_future))
    arrays={name:np.asarray(values,dtype=np.float32 if name not in ('skill','query_time_s') else np.float64)
            for name,values in rows.items()}
    if len(arrays['y']) and arrays['y'].shape[1]!=8:raise ValueError('Two observed root/box XY horizons required')
    return arrays,dict(queries=len(arrays['y']),by_skill={name:int(np.sum(arrays['skill']==i)) for i,name in enumerate(SKILLS)},
        observed_noncompliant_windows=int(np.sum(arrays['unsafe_future'])),
        strict_window_filter_applied=not include_measured_unsafe,
        censored=censor,actual_task_success=report['task_success'],actual_outcome=report['caller_outcome'],
        source_integrity_pass=True,strict_whole_episode_certified=False)


def build(study,output):
    study=Path(study);output=Path(output);collection=json.loads((study/'collection.json').read_text())
    if not collection['complete'] or len(collection['rows'])!=len(plan()['cases']):raise ValueError('Exact fresh collection required')
    output.mkdir(exist_ok=False);rows=[]
    for case in plan()['cases']:
        ep=study/'episodes'/case['case_id'];arrays,summary=extract_episode(ep)
        path=output/(case['case_id']+'.npz')
        np.savez_compressed(path,**arrays)
        rows.append(dict(case_id=case['case_id'],role=case['role'],path=path.name,sha256=sha(path),**summary))
    train=[r for r in rows if r['role']=='train']
    coverage=all(r['queries']>0 for r in train) and sum(r['by_skill']['push']>0 for r in train)>=2
    write_json(output/'manifest.json',dict(schema='composite-shadow-dataset-v1',source_study_freeze_sha256=sha(study/'study-freeze.json'),
        collection_sha256=sha(study/'collection.json'),rows=rows,coverage_pass=coverage,
        public_inputs_only=True,private_catalog_labels_only=True,complete_past_motor_steps=140,
        no_cross_skill_or_unsafe_future_labels=True,old_engineering_review_excluded=True,
        scope='Short-horizon within-skill NAV/PUSH/CLIMB consequences in native1kg/20cm scene; no A/B/C, long macro planning or safety certification'))
    print(json.dumps(dict(episodes=len(rows),queries=sum(r['queries'] for r in rows),coverage_pass=coverage)))


def read(dataset,role):
    manifest=json.loads((dataset/'manifest.json').read_text());data={k:[] for k in ('full','kin','y','cv','clock','skill')};ids=[]
    for row in manifest['rows']:
        if row['role']!=role:continue
        path=dataset/row['path']
        if sha(path)!=row['sha256']:raise ValueError('Dataset changed: '+row['case_id'])
        with np.load(path,allow_pickle=False) as z:
            for key in data:data[key].append(z[key].copy())
            ids.extend([row['case_id']]*len(z['y']))
    if not ids:raise ValueError('No complete '+role+' queries')
    return {k:np.concatenate(v).astype(float) for k,v in data.items()},np.asarray(ids)


def clock_fit(data,weights):
    keys=np.column_stack((data['skill'].astype(int),np.round(data['clock']*2).astype(int)))
    unique=np.unique(keys,axis=0)
    values=np.stack([np.average(data['y'][np.all(keys==key,axis=1)],axis=0,
        weights=weights[np.all(keys==key,axis=1)]) for key in unique])
    return dict(keys=unique,values=values)


def clock_predict(model,data):
    keys=np.column_stack((data['skill'].astype(int),np.round(data['clock']*2).astype(int)))
    prediction=[]
    for skill,t in keys:
        eligible=np.flatnonzero(model['keys'][:,0]==skill)
        if not len(eligible):raise ValueError('Train-only clock lacks an observed skill')
        index=eligible[np.argmin(abs(model['keys'][eligible,1]-t))]
        prediction.append(model['values'][index])
    return np.asarray(prediction)


def score(y,p,ids):
    error=(np.asarray(p)-np.asarray(y)).reshape(-1,2,2,2)
    per={ep:float(np.sqrt(np.mean(np.sum(error[ids==ep]**2,axis=-1)))) for ep in sorted(set(ids))}
    return dict(episode_equal_vector_RMSE_m=float(np.mean(list(per.values()))),per_episode_RMSE_m=per,
        overall_vector_RMSE_m=float(np.sqrt(np.mean(np.sum(error**2,axis=-1)))))


def train(dataset,output):
    dataset=Path(dataset);output=Path(output);manifest=json.loads((dataset/'manifest.json').read_text())
    if not manifest['coverage_pass']:raise ValueError('Train coverage insufficient; never include validation/test in fit')
    output.mkdir(exist_ok=False);started=time.monotonic()
    with (output/'training.claim').open('x') as f:f.write('One bounded shadow training; sealed test not read\n')
    tr,tri=read(dataset,'train');va,vai=read(dataset,'validation')
    groups,counts=np.unique(tri,return_counts=True);count=dict(zip(groups,counts));weights=np.asarray([len(tri)/(len(groups)*count[g]) for g in tri])
    selected={};models={}
    for key in ('full','kin'):
        candidates=[]
        for alpha in ALPHAS:
            if time.monotonic()-started>300:raise TimeoutError('Bounded 300s CPU training budget')
            model=fit(tr[key],tr['y'],alpha,weights);metrics=score(va['y'],predict(model,va[key]),vai)
            candidates.append((metrics['episode_equal_vector_RMSE_m'],alpha,model,metrics))
        winner=min(candidates,key=lambda x:(x[0],x[1]));models[key]=winner[2]
        np.savez(output/(key+'-checkpoint.npz'),**winner[2])
        selected[key]=dict(alpha=winner[1],validation=winner[3],candidates=[dict(alpha=a,validation=m) for _,a,_,m in candidates])
    primary=min(selected,key=lambda key:(selected[key]['validation']['episode_equal_vector_RMSE_m'],key))
    baseline=score(va['y'],va['cv'],vai)
    clock=clock_fit(tr,weights);clock_baseline=score(va['y'],clock_predict(clock,va),vai)
    np.savez(output/'clock-checkpoint.npz',**clock)
    result=dict(schema='composite-shadow-training-v1',training_runs=1,closed_form_fits=8,
        selected_on_validation=primary,selection=selected,constant_velocity_validation=baseline,
        train_only_phase_clock_validation=clock_baseline,
        train_episodes=sorted(set(tri)),validation_episodes=sorted(set(vai)),test_loaded_during_training=False,
        dataset_manifest_sha256=sha(dataset/'manifest.json'),checkpoint_sha256={k:sha(output/(k+'-checkpoint.npz')) for k in (*models,'clock')},
        wall_seconds=time.monotonic()-started,model='causal public RGBD/proprio/past-motor ridge consequence baseline',
        scope='Short-horizon within-skill development model; no macro world model or control authority',WM_control=False,physics_steps=0)
    write_json(output/'training.json',result);print(json.dumps(dict(selected=primary,validation=selected[primary]['validation'],constant_velocity=baseline,clock=clock_baseline,training_runs=1)))


def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=('build','train'));p.add_argument('--study',type=Path);p.add_argument('--dataset',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.mode=='build':build(a.study,a.output)
    else:train(a.dataset,a.output)


if __name__=='__main__':main()
