"""Three registered TRAIN-only episodes isolating one native NAV parameter.

Same declared development geometry/seed/native skills; only the first NAV_STEP
world-X goal varies -2/0/+2cm. CLIMB targets, later goals, physics and hard guards
remain the registered base. Failures are data, never replaced or retried.
"""
import argparse,copy,json,subprocess
from pathlib import Path
from types import MethodType
from .streams import sha,write_json

SCHEMA='piper-integrated-nav-parameter-training-v1'
PLAN=Path(__file__).with_name('nav_parameter_training_plan_v1.json')
BASE=Path('/mnt/yuanyue/data/go2-piper-world-model')
BUNDLE=BASE/'zyh-mujoco-source-340d7d8-v1'
PYTHON='/mnt/yuanyue/envs/piper-zyh-mujoco-340d7d8-v1/bin/python'

def plan():return json.loads(PLAN.read_text())
def protocol(case):
    from .integrated_course import protocol as native_protocol,plan as native_plan
    geometry=copy.deepcopy(native_plan()['cases'][3]);p=native_protocol(geometry)
    p.update(schema=SCHEMA,source_id='nav-param-train-20261027-v1-'+case['case_id'],
        episode_id='nav-param-train-20261027-v1-'+case['case_id']+'-episode0',source_group='seen-development-native16-full4-nav-step-intervention',
        purpose='Controlled TRAIN-only first NAV_STEP X-parameter coverage, one independent continuous episode per assigned value; retain all failures.',
        role='train',training_allowed=True,forecast_study_training_authorized=True,
        seed=plan()['shared_seed'],nav_parameter_training_case=case['case_id'],nav_parameter_training=case,
        nav_parameter_training_plan_sha256=sha(PLAN),supplemental_executor_revision='native16-nav-step-intervention-v1',
        public_control_proprio_hz=50,collection_only_no_training_or_WM_control=True)
    return p

def validate(p):
    rows=[r for r in plan()['cases'] if r['case_id']==p.get('nav_parameter_training_case')]
    if len(rows)!=1 or p!=protocol(rows[0]):raise ValueError('Exact controlled NAV parameter assignment and bounded protocol required')
    return p

def install(router,p):
    validate(p);old=router.start_chunk;delta=p['nav_parameter_training']['nav_step_delta_world_x_m'];seen=[]
    def start_chunk(self,tasks,stage):
        if stage!='B_STEP_HIGH_PLATFORM':return old(tasks,stage)
        if seen:raise ValueError('First NAV_STEP intervention may be assigned exactly once')
        if len(tasks)!=5 or tasks[0]['skill']!='nav' or tasks[1]['skill']!='climb':raise ValueError('Pinned five-task B/high stage changed')
        nominal=copy.deepcopy(tasks);chosen=copy.deepcopy(tasks)
        if abs(nominal[0]['goal'][0]-.05)>1e-7:raise ValueError('Registered nominal NAV_STEP goal is not0.05m')
        chosen[0]['goal'][0]+=delta
        # No CLIMB approach/other NAV/target identity/skill order is changed.
        if chosen[1:]!=nominal[1:]:raise ValueError('Intervention escaped the single declared NAV parameter')
        seen.append(stage);self.event('registered_NAV_STEP_training_intervention',assigned_delta_world_x_m=delta,
            nominal_tasks=nominal,actual_tasks=chosen,selection_is_fixed_training_assignment=True,model_control=False)
        return old(chosen,stage)
    router.start_chunk=MethodType(start_chunk,router)
    router.wm_nav_parameter_training_receipt=dict(case_id=p['nav_parameter_training_case'],assignment=copy.deepcopy(p['nav_parameter_training']),
        source_plan_sha256=sha(PLAN),fixed_assignment_not_model_choice=True,only_first_NAV_STEP_goal_varies=True)
    return router

def prepare(output,tests):
    from .preflight import run
    from .prepare import prepare as prepare_root
    output=Path(output);output.mkdir(exist_ok=False);rows=[]
    for row in plan()['cases']:
        p=protocol(row);pp=output/(row['case_id']+'-protocol.json');write_json(pp,p)
        probe=run(BUNDLE,p,BASE);zp=output/(row['case_id']+'-zero-step.json');write_json(zp,probe)
        if not probe['passed'] or probe['native_physics_steps'] or probe['actual_metric_depth_valid_fraction']<=0:raise ValueError('Real nonempty current-source zero-step preflight required')
        root=BASE/('nav-parameter-train-'+row['case_id']+'-20261027-v1');prepare_root(root,BUNDLE,pp,tests,zp)
        rows.append(dict(case_id=row['case_id'],root=str(root),protocol_sha256=sha(root/'protocol.json'),freeze_sha256=sha(root/'freeze.json'),assigned_parameter=row))
        print('PARAMETER_TRAINING_PREPARED',row['case_id'],flush=True)
    write_json(output/'frozen-intervention-plan.json',dict(schema='controlled-nav-training-freeze-v1',source_plan=plan(),source_plan_sha256=sha(PLAN),
        cases=rows,physical_starts_allowed=3,automatic_retry=False,all_sources_train_only=True,old_manifest_or_roles_modified=False))

def dispatch(preparation,output):
    from .audit_integrated_course import audit
    preparation=Path(preparation);output=Path(output);output.mkdir(exist_ok=False)
    frozen=json.loads((preparation/'frozen-intervention-plan.json').read_text())
    if frozen['source_plan_sha256']!=sha(PLAN) or frozen['source_plan']!=plan():raise ValueError('Frozen intervention assignment changed')
    write_json(output/'batch.claim',dict(physical_starts_allowed=3,automatic_retry=False,source_plan_sha256=sha(PLAN)))
    rows=[]
    for row in frozen['cases']:
        root=Path(row['root'])
        if sha(root/'freeze.json')!=row['freeze_sha256'] or sha(root/'protocol.json')!=row['protocol_sha256']:raise ValueError('Frozen root changed')
        with (root/'run.log').open('x') as log:rc=subprocess.run([str(root/'launch_once.sh')],stdout=log,stderr=subprocess.STDOUT,timeout=2420).returncode
        write_json(root/'dispatch-exit.json',dict(returncode=rc,automatic_retry=False))
        ap=output/(row['case_id']+'-audit.json');a=audit(root,ap);r=json.loads((root/'report.json').read_text())
        public_rows=[json.loads(line) for line in (root/'episode/control-boundaries.jsonl').open()]
        for sample in public_rows:
            body=sample.get('public_body_proprio')
            if not isinstance(body,list) or len(body)!=9:raise ValueError('Registered50Hz public body stream missing')
        result=dict(**row,returncode=rc,task_success=r['task_success'],complete_task_audit_pass=a['passed'],data_integrity_pass=a['original_motor_and_visual_audit']['data_integrity_pass'],
            error=r['error'],sim_seconds=r['sim_seconds'],frames=r['frames'],physical_steps=r['physical_steps'],
            public_body_samples=len(public_rows),audit=str(ap),audit_sha256=sha(ap),report_sha256=sha(root/'report.json'))
        rows.append(result);(output/'progress.json').write_text(json.dumps(dict(completed=len(rows),total=3,rows=rows),indent=2))
        print('CONTROLLED_TRAIN_SOURCE_CLOSED',json.dumps(result),flush=True)
        if not result['data_integrity_pass']:raise ValueError('Stop controlled data collection on storage/infrastructure integrity error')
    write_json(output/'collection.json',dict(schema='controlled-nav-parameter-training-collection-v1',complete=True,rows=rows,
        sources_train_only=True,all_failures_retained=True,original13_source_roles_unchanged=True,automatic_retry=False,model_updates=0,WM_control=False))
    print('CONTROLLED_NAV_TRAINING_COLLECTION_COMPLETE',str(output/'collection.json'),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='command',required=True)
    a=sub.add_parser('prepare');a.add_argument('--output',type=Path,required=True);a.add_argument('--tests',type=Path,required=True)
    a=sub.add_parser('run');a.add_argument('--preparation',type=Path,required=True);a.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.command=='prepare':prepare(a.output,a.tests)
    else:dispatch(a.preparation,a.output)
