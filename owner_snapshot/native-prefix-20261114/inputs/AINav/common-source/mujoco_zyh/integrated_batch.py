"""Registered geometry-grouped continuous-course collection, never retries roots."""
import argparse,copy,fcntl,json,os,subprocess,time
from pathlib import Path
from .streams import sha,write_json

SCHEMA='piper-integrated-batch-case-v1'
PLAN=Path(__file__).with_name('integrated_batch_plan_v1.json')
PYTHON='/mnt/yuanyue/envs/piper-zyh-mujoco-340d7d8-v1/bin/python'
BASE=Path('/mnt/yuanyue/data/go2-piper-world-model')
BUNDLE=BASE/'zyh-mujoco-source-340d7d8-v1'

def plan():return json.loads(PLAN.read_text())
def geometry_key(case):return json.dumps({k:v for k,v in case.items() if k!='case_id'},sort_keys=True)
def case_protocol(row):
    from .integrated_course import protocol
    p=protocol(copy.deepcopy(row['geometry']))
    p.update(schema=SCHEMA,source_id='integrated-batch-20261026-v1-'+row['case_id'],
        episode_id='integrated-batch-20261026-v1-'+row['case_id']+'-episode0',
        source_group=row['geometry_group'],role=row['role'],seed=row['seed'],
        purpose='Frozen first batch of complete integrated scenarios for offline world-model training; preserve successful, failed and censored episodes.',
        integrated_batch_case=row['case_id'],batch_plan_sha256=sha(PLAN),
        training_allowed=row['role']=='train',forecast_study_training_authorized=row['role']=='train',
        collection_only_no_training_or_WM_control=True)
    return p

def validate_case(p):
    rows=[r for r in plan()['cases'] if r['case_id']==p.get('integrated_batch_case')]
    if len(rows)!=1 or p!=case_protocol(rows[0]):raise ValueError('Exact frozen batch case/split/budget required')
    return p

def root_for(row):return BASE/('integrated-batch-'+row['case_id']+'-20261026-v1')

def check_split_plan():
    d=plan();ids=set();geometries=set();groups={};counts={k:0 for k in ('train','validation','test')}
    for row in d['cases']:
        if row['case_id'] in ids:raise ValueError('Duplicate episode ID')
        key=geometry_key(row['geometry'])
        if key in geometries:raise ValueError('Duplicate geometry')
        ids.add(row['case_id']);geometries.add(key)
        group=row['geometry_group'];role=row['role']
        if group in groups and groups[group]!=role:raise ValueError('Geometry/source group crosses split')
        groups[group]=role;counts[role]+=1
        validate_case(case_protocol(row))
    if counts!={'train':4,'validation':2,'test':2}:raise ValueError('Exact registered 4/2/2 split required')
    if d['training']['test_used_for_selection'] or d['automatic_retry']:raise ValueError('No test selection or automatic retry')
    return counts

def prepare_grid(output,tests):
    from .preflight import run
    from .prepare import prepare
    output=Path(output);output.mkdir(exist_ok=False)
    check_split_plan()
    old=[]
    for directory in BASE.glob('integrated-course-full-*-20261026-v*'):
        pp=directory/'protocol.json'
        if pp.is_file():
            p=json.loads(pp.read_text());old.append((geometry_key(p['integrated_case']),str(directory)))
    rows=[]
    for row in plan()['cases']:
        exposed=[path for key,path in old if key==geometry_key(row['geometry'])]
        if exposed and row['role']!='train':raise ValueError('Holdout geometry was previously exposed: '+row['case_id'])
        p=case_protocol(row);pp=output/(row['case_id']+'-protocol.json');write_json(pp,p)
        probe=run(BUNDLE,p,BASE);zp=output/(row['case_id']+'-zero-step.json');write_json(zp,probe)
        if not probe['passed'] or probe['native_physics_steps'] or probe['actual_metric_depth_valid_fraction']<=0:raise ValueError('Real nonempty zero-step required')
        root=root_for(row);prepare(root,BUNDLE,pp,tests,zp)
        rows.append(dict(case_id=row['case_id'],role=row['role'],geometry_group=row['geometry_group'],root=str(root),
            protocol_sha256=sha(root/'protocol.json'),freeze_sha256=sha(root/'freeze.json'),zero_step_sha256=sha(zp),previous_exposure=exposed))
        print('PREPARED_BATCH_CASE',row['case_id'],flush=True)
    write_json(output/'frozen-split-plan.json',dict(schema='integrated-batch-frozen-split-plan-v1',plan=plan(),plan_sha256=sha(PLAN),
        cases=rows,physical_starts_allowed=len(rows),training_allowed=plan()['training'],automatic_retry=False))

def run_batch(preparation,dispatch):
    from .audit_integrated_course import audit
    preparation=Path(preparation);dispatch=Path(dispatch);dispatch.mkdir(exist_ok=False)
    frozen=json.loads((preparation/'frozen-split-plan.json').read_text())
    if frozen['plan_sha256']!=sha(PLAN) or frozen['plan']!=plan():raise ValueError('Frozen split plan changed')
    write_json(dispatch/'batch.claim',dict(max_starts=8,automatic_retry=False,plan_sha256=sha(PLAN)))
    rows=[];started=time.monotonic()
    for row in frozen['cases']:
        root=Path(row['root'])
        if sha(root/'freeze.json')!=row['freeze_sha256'] or sha(root/'protocol.json')!=row['protocol_sha256']:raise ValueError('Prepared root changed')
        with (root/'run.log').open('x') as log:
            rc=subprocess.run([str(root/'launch_once.sh')],stdout=log,stderr=subprocess.STDOUT,timeout=2420).returncode
        write_json(root/'dispatch-exit.json',dict(returncode=rc,automatic_retry=False))
        report=json.loads((root/'report.json').read_text());ap=dispatch/(row['case_id']+'-independent-audit.json')
        a=audit(root,ap)
        record=dict(**row,returncode=rc,task_success=report['task_success'],independent_full_task_pass=a['passed'],
            data_integrity_pass=a['original_motor_and_visual_audit']['data_integrity_pass'],errors=a['errors'],
            report_sha256=sha(root/'report.json'),audit=str(ap),audit_sha256=sha(ap),
            sim_seconds=report['sim_seconds'],frames=report['frames'],physical_steps=report['physical_steps'],error=report['error'])
        rows.append(record)
        # The progress pointer is mutable; source reports, freezes and audits are immutable.
        (dispatch/'progress.json').write_text(json.dumps(dict(completed=len(rows),total=8,rows=rows),indent=2))
        print('CLOSED_DISTINCT_BATCH_EPISODE',json.dumps(record),flush=True)
        if not record['data_integrity_pass']:raise ValueError('Stop batch on infrastructure/data-integrity failure')
    write_json(dispatch/'collection.json',dict(schema='integrated-batch-collection-v1',complete=True,rows=rows,
        physical_starts=len(rows),wall_seconds=time.monotonic()-started,automatic_retry=False,training_runs=0,WM_control=False))
    freeze_dataset(preparation,dispatch)

def freeze_dataset(preparation,dispatch):
    dispatch=Path(dispatch);frozen=json.loads((Path(preparation)/'frozen-split-plan.json').read_text())
    collected=json.loads((dispatch/'collection.json').read_text())
    if not collected['complete'] or len(collected['rows'])!=8:raise ValueError('Complete registered batch required')
    summary_path=BASE/'integrated-course-five-complete-20261026-v1/five-complete-summary.json'
    if sha(summary_path)!=plan()['bootstrap_summary_sha256']:raise ValueError('Bootstrap acceptance changed')
    summary=json.loads(summary_path.read_text());episodes=[]
    for r in summary['rows']:
        episodes.append(dict(root=r['root'],role='train',source_group='bootstrap-'+r['case_id'],
            status='seen_development_bootstrap',task_success=True,report_sha256=r['report_sha256'],audit=r['independent_audit'],audit_sha256=r['audit_sha256']))
    for r in collected['rows']:
        if not r['data_integrity_pass']:raise ValueError('No silent exclusion of corrupted sources')
        episodes.append(dict(root=r['root'],role=r['role'],source_group=r['geometry_group'],status='fresh_registered_geometry',
            task_success=r['task_success'],report_sha256=r['report_sha256'],audit=r['audit'],audit_sha256=r['audit_sha256']))
    for e in episodes:
        root=Path(e['root'])
        if sha(root/'report.json')!=e['report_sha256'] or sha(e['audit'])!=e['audit_sha256']:raise ValueError('Closed source changed')
        e['files_sha256']={name:sha(root/name) for name in ('protocol.json','freeze.json','episode/episode.json','episode/index.json','episode/closure.json')}
        report=json.loads((root/'report.json').read_text());e.update(frames=report['frames'],physical_steps=report['physical_steps'],terminal_error=report['error'])
    write_json(dispatch/'dataset-manifest.json',dict(schema='integrated-course-world-model-dataset-v1',plan_sha256=sha(PLAN),
        frozen_split_sha256=sha(Path(preparation)/'frozen-split-plan.json'),episodes=episodes,
        training=plan()['training'],collection=plan()['collection'],
        bootstrap_original_metadata_unchanged=True,bootstrap_new_training_authorization=plan()['bootstrap_new_training_authorization'],
        split_unit='whole source/geometry group; no frame random split',test_used_for_training_or_selection=False,
        failed_and_censored_sources_retained=True,private_truth_allowed_as_model_input=False,
        input_contract='Actual RGBD/proprio history and ALL ordered intervening issued 200Hz PD/FF commands; future recorded commands only in explicitly conditional offline prediction, no planning efficacy claim.'))
    print('FROZEN_DATASET_MANIFEST',str(dispatch/'dataset-manifest.json'),sha(dispatch/'dataset-manifest.json'),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='command',required=True)
    a=sub.add_parser('prepare');a.add_argument('--output',type=Path,required=True);a.add_argument('--tests',type=Path,required=True)
    a=sub.add_parser('run');a.add_argument('--preparation',type=Path,required=True);a.add_argument('--dispatch',type=Path,required=True)
    a=p.parse_args()
    if a.command=='prepare':prepare_grid(a.output,a.tests)
    else:run_batch(a.preparation,a.dispatch)
