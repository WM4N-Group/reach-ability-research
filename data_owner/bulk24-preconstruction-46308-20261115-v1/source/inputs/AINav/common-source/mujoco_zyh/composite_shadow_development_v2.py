"""Train-only exploratory view of the fresh composite streams, with unsafe rows marked.

This analysis was registered after the five v1 collections closed. It does not
alter their freeze or roles, read validation/test, or certify physical safety.
"""
import argparse
import json
from pathlib import Path
import time

import numpy as np

from .composite_shadow_fit import extract_episode,score
from .composite_shadow_study import plan
from .push_forecast_fit import fit,predict
from .streams import sha,write_json

ALPHA=.01


def build(study,output):
    study=Path(study);output=Path(output);collection=json.loads((study/'collection.json').read_text())
    if not collection['complete'] or len(collection['rows'])!=5:raise ValueError('All five frozen physical starts must close first')
    cases=[c for c in plan()['cases'] if c['role']=='train']
    if len(cases)!=3:raise ValueError('Exactly three original train roles required')
    output.mkdir(exist_ok=False);rows=[];command_identities=set()
    for case in cases:
        ep=study/'episodes'/case['case_id']
        if not json.loads((ep/'data-audit.json').read_text())['errors']==[]:raise ValueError('Actual stream audit failed')
        index=json.loads((ep/'episode/index.json').read_text())
        identity=tuple(item['sha256'] for item in index['commands'])
        if identity in command_identities:raise ValueError('Duplicate train motor trajectory')
        command_identities.add(identity)
        arrays,summary=extract_episode(ep,include_measured_unsafe=True)
        if not summary['queries']:raise ValueError('Train episode has no observed within-skill future')
        path=output/(case['case_id']+'.npz');np.savez_compressed(path,**arrays)
        rows.append(dict(case_id=case['case_id'],role='train',path=path.name,sha256=sha(path),
            motor_chunk_sha256s=list(identity),**summary))
    coverage=all(sum(r['by_skill'][skill]>0 for r in rows)>=2 for skill in ('nav','push')) and any(r['by_skill']['climb']>0 for r in rows)
    write_json(output/'manifest.json',dict(schema='composite-shadow-exploratory-train-only-v2',
        raw_study_freeze_sha256=sha(study/'study-freeze.json'),raw_collection_sha256=sha(study/'collection.json'),
        rows=rows,coverage_pass=coverage,validation_and_test_files_read=False,
        unsafe_future_rows_retained_and_flagged=True,strict_safety_certified=False,
        failed_episodes_retained=True,no_cross_skill_or_unobserved_future_labels=True,
        private_catalog_labels_only=True,public_RGBD_proprio_complete_past_motor_inputs_only=True,
        exploratory_change_after_collection=True,
        interpretation='Fit observed actual short-horizon dynamics including measured noncompliant states; never use this model for safety or control. No independent model selection.'))
    print(json.dumps(dict(train_sources=len(rows),rows=sum(r['queries'] for r in rows),
        unsafe_rows=sum(r['observed_noncompliant_windows'] for r in rows),coverage_pass=coverage)))


def train(dataset,output):
    dataset=Path(dataset);output=Path(output);manifest=json.loads((dataset/'manifest.json').read_text())
    if not manifest['coverage_pass'] or len(manifest['rows'])!=3:raise ValueError('Train-only stage coverage missing')
    output.mkdir(exist_ok=False);started=time.monotonic()
    with (output/'training.claim').open('x') as f:f.write('One fixed-alpha exploratory training; validation and test sealed\n')
    arrays={k:[] for k in ('full','kin','y','skill','unsafe_future')};ids=[]
    for row in manifest['rows']:
        if row['role']!='train' or sha(dataset/row['path'])!=row['sha256']:raise ValueError('Train-only frozen chunk required')
        with np.load(dataset/row['path'],allow_pickle=False) as z:
            for key in arrays:arrays[key].append(z[key].copy())
            ids.extend([row['case_id']]*len(z['y']))
    data={k:np.concatenate(v).astype(float) for k,v in arrays.items()};ids=np.asarray(ids)
    groups,counts=np.unique(ids,return_counts=True);lookup=dict(zip(groups,counts))
    weights=np.asarray([len(ids)/(len(groups)*lookup[g]) for g in ids])
    model=fit(data['full'],data['y'],ALPHA,weights)
    checkpoint=output/'shadow-ridge.npz';np.savez(checkpoint,**model)
    predictions=predict(model,data['full']);metrics=score(data['y'],predictions,ids)
    per_skill={skill:score(data['y'][data['skill']==i],predictions[data['skill']==i],ids[data['skill']==i])
        for i,skill in enumerate(('nav','push','climb')) if np.any(data['skill']==i)}
    result=dict(schema='composite-shadow-exploratory-fit-v2',training_runs=1,alpha_fixed_before_fit=ALPHA,
        train_sources=sorted(set(ids)),train_queries=len(ids),measured_noncompliant_train_queries=int(data['unsafe_future'].sum()),
        training_fit_diagnostics=metrics,by_skill_training_fit_diagnostics=per_skill,
        validation_or_test_loaded=False,model_selected_on_validation=False,
        dataset_manifest_sha256=sha(dataset/'manifest.json'),model_sha256=sha(checkpoint),
        wall_seconds=time.monotonic()-started,actor_weights_modified=False,WM_control=False,physics_steps=0,
        safety_certified=False,generalization_or_world_model_planning_benefit_validated=False,
        scope='Observed within-skill root/box XY at 0.4/0.8s; not multi-step task imagination. Includes measured out-of-range/speed rows as explicit exploratory data.')
    write_json(output/'training.json',result)
    print(json.dumps(dict(train_queries=len(ids),model_sha256=result['model_sha256'],
        training_RMSE_m=metrics['episode_equal_vector_RMSE_m'],validation_or_test_loaded=False)))


def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=('build','train'));p.add_argument('--study',type=Path)
    p.add_argument('--dataset',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.mode=='build':build(a.study,a.output)
    else:train(a.dataset,a.output)


if __name__=='__main__':main()
