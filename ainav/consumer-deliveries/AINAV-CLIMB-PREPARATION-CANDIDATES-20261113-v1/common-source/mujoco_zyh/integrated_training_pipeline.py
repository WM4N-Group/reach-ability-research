"""Freeze nine training sources, train while heldout physics continues, then evaluate.

No training source changes after the first optimizer step. The heldout source
plan is fixed before collection and its observations wait until checkpoint freeze.
"""
import argparse,json,time
from pathlib import Path
from .streams import sha,write_json
from .integrated_batch import plan,PLAN,BASE,root_for
from .integrated_dataset import prepare
from .integrated_world_model import train,evaluate_frozen


def wait_for(check,started):
    while not check():
        if time.monotonic()-started>21600:raise RuntimeError('Registered collection wait censored; no retry')
        time.sleep(15)


def training_audits_ready(dispatch):
    for row in plan()['cases']:
        if row['role']!='train':continue
        path=Path(dispatch)/(row['case_id']+'-independent-audit.json')
        try:json.loads(path.read_text())
        except (FileNotFoundError,json.JSONDecodeError):return False
    return True


def freeze_training_sources(batch_dispatch,output):
    summary_path=BASE/'integrated-course-five-complete-20261026-v1/five-complete-summary.json'
    if sha(summary_path)!=plan()['bootstrap_summary_sha256']:raise ValueError('Accepted bootstrap evidence changed')
    summary=json.loads(summary_path.read_text());episodes=[]
    for r in summary['rows']:
        episodes.append(dict(root=r['root'],role='train',source_group='bootstrap-'+r['case_id'],status='seen_development_bootstrap',
            task_success=True,report_sha256=r['report_sha256'],audit=r['independent_audit'],audit_sha256=r['audit_sha256']))
    heldout=[]
    for row in plan()['cases']:
        root=root_for(row)
        if row['role']!='train':
            heldout.append(dict(case_id=row['case_id'],role=row['role'],root=str(root),source_group=row['geometry_group']))
            continue  # no holdout report, pixels, proprio or audit is opened here
        ap=Path(batch_dispatch)/(row['case_id']+'-independent-audit.json');a=json.loads(ap.read_text())
        if not a['original_motor_and_visual_audit']['data_integrity_pass']:raise ValueError('Training source integrity failure')
        report=json.loads((root/'report.json').read_text())
        if sha(root/'report.json')!=a['report_sha256']:raise ValueError('Training report changed')
        episodes.append(dict(root=str(root),role='train',source_group=row['geometry_group'],status='fresh_registered_geometry',
            task_success=report['task_success'],report_sha256=a['report_sha256'],audit=str(ap),audit_sha256=sha(ap)))
    if len(episodes)!=9:raise ValueError('Exactly five seen bootstrap plus four registered fresh training sources required')
    for e in episodes:
        root=Path(e['root'])
        if sha(root/'report.json')!=e['report_sha256'] or sha(e['audit'])!=e['audit_sha256']:raise ValueError('Source acceptance changed')
        e['files_sha256']={name:sha(root/name) for name in ('protocol.json','freeze.json','episode/episode.json','episode/index.json','episode/closure.json')}
        report=json.loads((root/'report.json').read_text());e.update(frames=report['frames'],physical_steps=report['physical_steps'],terminal_error=report['error'])
    d=dict(schema='integrated-course-frozen-training-sources-v2',plan_sha256=sha(PLAN),episodes=episodes,
        reserved_heldout_sources=heldout,heldout_observations_or_outcomes_read=False,training=plan()['training'],
        bootstrap_new_training_authorization=plan()['bootstrap_new_training_authorization'],
        failed_and_censored_sources_retained=True,private_truth_allowed_as_model_input=False,
        split_unit='whole source/geometry group; no frame random split')
    write_json(output,d);return d


def execute(raw_manifest,packed,training,dispatch,tests):
    raw_manifest=Path(raw_manifest);dispatch=Path(dispatch);dispatch.mkdir(exist_ok=False)
    if not Path(tests).read_text().rstrip().endswith('OK'):raise ValueError('Passed current data/model CPU regression required')
    files=[Path(__file__),Path(__file__).with_name('integrated_dataset.py'),Path(__file__).with_name('integrated_world_model.py'),PLAN]
    sources={str(p):sha(p) for p in files};started=time.monotonic()
    write_json(dispatch/'pipeline-freeze.json',dict(schema='integrated-world-model-pipeline-v2',sources_sha256=sources,
        full_raw_manifest=str(raw_manifest),packed_training_output=str(packed),training_output=str(training),tests_sha256=sha(tests),
        configuration=plan()['training'],training_runs_allowed=1,automatic_retry=False,WM_control=False,
        training_gate='all nine immutable training sources; heldout plan pre-frozen before collection',heldout_data_gate='final checkpoint already frozen'))
    write_json(dispatch/'pipeline.claim',dict(training_runs_allowed=1,automatic_retry=False))
    wait_for(lambda:training_audits_ready(raw_manifest.parent),started)
    for file,digest in sources.items():
        if sha(file)!=digest:raise ValueError('Frozen training source changed while waiting')
    training_manifest=dispatch/'training-sources-manifest.json'
    train_raw=freeze_training_sources(raw_manifest.parent,training_manifest)
    prepare(training_manifest,packed)
    packed_manifest=Path(packed)/'packed-manifest.json'
    print('IMMUTABLE_NINE_SOURCE_TRAINING_SET_READY',str(packed_manifest),sha(packed_manifest),flush=True)
    train(packed_manifest,training,defer_evaluation=True)
    checkpoint=Path(training)/'world-model-final.pt';checkpoint_sha=sha(checkpoint)
    wait_for(lambda:raw_manifest.is_file(),started)
    raw=json.loads(raw_manifest.read_text())
    if raw['plan_sha256']!=sha(PLAN) or raw['training']!=plan()['training']:raise ValueError('Full collection/training plan mismatch')
    full_train={e['root']:e for e in raw['episodes'] if e['role']=='train'}
    if full_train!={e['root']:e for e in train_raw['episodes']}:raise ValueError('Training sources changed after first optimizer step')
    write_json(dispatch/'full-dataset-freeze.json',dict(path=str(raw_manifest),sha256=sha(raw_manifest),checkpoint_already_frozen_sha256=checkpoint_sha))
    evaluation_packed=Path(str(packed)+'-evaluation')
    prepare(raw_manifest,evaluation_packed,reuse_training_manifest=packed_manifest)
    evaluation_manifest=evaluation_packed/'packed-manifest.json'
    evaluate_frozen(checkpoint,evaluation_manifest,training)
    write_json(dispatch/'completion.json',dict(complete=True,raw_manifest_sha256=sha(raw_manifest),training_sources_manifest_sha256=sha(training_manifest),
        training_manifest_sha256=sha(packed_manifest),evaluation_manifest_sha256=sha(evaluation_manifest),checkpoint_sha256=checkpoint_sha,
        evaluation_sha256=sha(Path(training)/'evaluation.json'),training_runs=1,WM_control=False))

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('raw-manifest','packed','training','dispatch','tests'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();execute(a.raw_manifest,a.packed,a.training,a.dispatch,a.tests)
