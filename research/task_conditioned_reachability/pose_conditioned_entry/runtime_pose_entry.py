"""Pose-factor observer/selector around a byte-frozen private native FK sampler.

The sampler is deliberately E0 ONLY to construct the common uncensored cloud,
not to choose the experiment's scalar. All actual roles/criteria are logged here.
No controller, robot-state, physics clock, actor or safety threshold modifications.
"""
import json
from pathlib import Path
import time
import numpy as np
import finite_cloud_sampler_frozen as sampler
from pose_entry_selection import ARMS,ROLES,select

ARM=None;OUTPUT=None;CONTEXT=None;SEQ=0;LAST_ID=None
_CAPTURE=[]
sampler.write_record=lambda record:_CAPTURE.append(record)


def configure_study(arm,output):
    global ARM,OUTPUT,SEQ,CONTEXT,LAST_ID
    if arm not in ARMS:raise ValueError('Unregistered pose-entry arm')
    ARM=arm;OUTPUT=Path(output);SEQ=0;CONTEXT=None;LAST_ID=None
    sampler.configure_study('E0',OUTPUT)


def set_query_context(env,joint_ids,joint_names,*,evaluation_role):
    global CONTEXT,LAST_ID
    CONTEXT=None;LAST_ID=None
    if evaluation_role not in ROLES:raise ValueError('Query role must be explicit')
    sampler.set_query_context(env,joint_ids,joint_names)
    reference=None
    if evaluation_role=='planning':
        term=env.action_manager.get_term('joint_pos')
        value=getattr(term,'stance_orientation_target',None)
        if value is None:raise ValueError('Common planning input missing: existing controller orientation reference')
        reference=sampler.array(value[0]).tolist()
    CONTEXT=dict(env=env,step=int(env.episode_length_buf[0]),role=evaluation_role,reference=reference,
        reference_origin='existing action term stance_orientation_target, read before decision; production timestamp not independently recorded',
        reference_generation_step=None,reference_freshness_certified=False)


def write_record(record):
    if OUTPUT is None:raise ValueError('Unbound output')
    with (OUTPUT/'entry_geometry.jsonl').open('a') as f:f.write(json.dumps(record,allow_nan=False,separators=(',',':'))+'\n')


def required_standoff(*args,**kwargs):
    global SEQ,LAST_ID
    if ARM is None or CONTEXT is None:raise ValueError('Unbound pose-factor context')
    if int(CONTEXT['env'].episode_length_buf[0])!=CONTEXT['step']:raise ValueError('Query step changed')
    if CONTEXT['role']=='final_actual' and (kwargs.get('nominal_translation_w') is not None or kwargs.get('forecast_margin_m',0.)!=0.):
        raise ValueError('Final actual verifier forbids nominal translation/forecast margin')
    _CAPTURE.clear();SEQ+=1;LAST_ID=f'{ARM}-{CONTEXT["role"]}-q{SEQ}-step{CONTEXT["step"]}'
    started=time.perf_counter();logged=False
    try:
        base=sampler.required_standoff(*args,**kwargs)
        clouds=[r for r in _CAPTURE if r.get('event')=='finite_tip_query']
        if len(clouds)!=1:raise ValueError('Expected exactly one uncensored native cloud')
        raw=clouds[0]
        if len(raw['tip_cloud_box_m'])!=2624:raise ValueError('Native full-cloud coverage changed')
        result=select(raw,ARM,CONTEXT['role'],CONTEXT['reference'])
        record=dict(raw,**result);record.update(arm=ARM,query_id=LAST_ID,
            reference_origin=CONTEXT['reference_origin'] if CONTEXT['role']=='planning' else None,
            reference_generation_step=None,reference_freshness_certified=False,
            sampler_role='byte-frozen E0 used ONLY to construct/log full cloud; chosen scalar computed separately',
            selector_total_wall_s=time.perf_counter()-started,
            scope='Finite model preview; reference pose is NOT actual future tracking or dynamic safety')
        write_record(record);logged=True
        if not result['request_within_original40mm']:raise ValueError('Box approach needs more than40mm preparation')
        result.pop('selected_forecast_cloud_box_m');result.pop('reference_pose_cloud_box_m',None)
        return dict(base,**result,study_arm=ARM,query_id=LAST_ID)
    except Exception as error:
        if not logged:
            # Preserve the captured raw inputs/cloud even when the new selector
            # rejects them. A technical failure must not erase its witness.
            failure=dict(_CAPTURE[-1]) if _CAPTURE else {}
            failure.update(event='pose_entry_query_error',arm=ARM,query_id=LAST_ID,step=CONTEXT['step'],
                evaluation_role=CONTEXT['role'],error_type=type(error).__name__,error=str(error))
            write_record(failure)
        raise
    finally:
        if int(CONTEXT['env'].episode_length_buf[0])!=CONTEXT['step']:raise RuntimeError('Physical step advanced inside pose selector')


def record_source_hand_guard(error):
    if CONTEXT is None or LAST_ID is None:raise ValueError('No current query')
    if int(CONTEXT['env'].episode_length_buf[0])!=CONTEXT['step']:raise ValueError('Guard/query step changed')
    write_record(dict(event='source_hand_FK_guard',query_id=LAST_ID,arm=ARM,evaluation_role=CONTEXT['role'],
        step=CONTEXT['step'],time_s=CONTEXT['step']*float(CONTEXT['env'].step_dt),error_m=float(error),
        original_limit_m=.0002,passed=float(error)<=.0002))
