"""Public-only 8-D input for CONTINUING one registered native PUSH task.

NOT a new relative PUSH request: the native goal was set at task reset to the
initial selected-box position plus cfg.push_distance along course +X. Reusing
that TOTAL distance at a later query must never mean "push this much farther".
The reset-to-query real observation prefix is therefore required context.

No private object registry, mass, future command, actor, simulator or optimizer
is accepted here. Pixel selection is shared with equally informed baselines.
"""
from dataclasses import dataclass
import math
import hashlib
import numpy as np
from visual_box_proposals import propose_visual_candidates,single_visible_hypothesis,visual_calibration_sha

CONTRACT_ID='public-native-PUSH-continuation-original-total-v1'
OBS_KEYS=frozenset(('rgb','depth_m','camera_K','T_base_optical','proprio','actions_previous','action_valid','timestamps_s'))
ACTION_KEYS=frozenset(('macro_intents','durations_s','anchor_times_s'))
INTENT_FIELDS=('NAV','PUSH','CLIMB','goal_body_x_m','goal_body_y_m','target_pixel_u_normalized','target_pixel_v_normalized','macro_distance_m')


@dataclass(frozen=True)
class PublicPushContinuation:
    original_total_distance_m: float=.6
    goal_reference_control_tick: int=0

    def __post_init__(self):
        if (type(self.original_total_distance_m) not in (int,float) or not math.isfinite(self.original_total_distance_m)
                or not math.isclose(self.original_total_distance_m,.6,abs_tol=1e-9)
                or type(self.goal_reference_control_tick) is not int or self.goal_reference_control_tick!=0):
            raise ValueError('This contract only continues the registered0.6m task-reset goal; no new/remaining-distance request')


def validate_snapshot(packet,query_tick):
    if not isinstance(packet,dict) or set(packet)!=OBS_KEYS or not all(isinstance(x,np.ndarray) for x in packet.values()):
        raise ValueError('Only the exact8 public acquisition arrays are allowed')
    rgb=packet['rgb']
    if rgb.dtype!=np.uint8 or rgb.ndim!=5 or rgb.shape[:2]!=(1,1) or rgb.shape[-1]!=3:
        raise ValueError('One real public RGB snapshot required')
    h,w=rgb.shape[2:4]
    shapes=dict(depth_m=(1,1,h,w,1),camera_K=(1,3,3),T_base_optical=(1,4,4),proprio=(1,1,45),actions_previous=(1,1,18),action_valid=(1,1),timestamps_s=(1,1))
    for name,shape in shapes.items():
        a=packet[name]
        if a.shape!=shape:raise ValueError('Public snapshot shape mismatch: '+name)
        if name=='action_valid':
            if a.dtype!=np.bool_:raise ValueError('Actual boolean action validity required')
        elif a.dtype.kind!='f' or (name!='depth_m' and not np.isfinite(a).all()):
            raise ValueError('Actual finite public floating data required: '+name)
    if type(query_tick) is not int or query_tick<0 or not math.isclose(float(packet['timestamps_s'][0,0]),query_tick*.02,abs_tol=1e-6):
        raise ValueError('Actual native20ms reset-to-query clock required')
    valid=bool(packet['action_valid'][0,0])
    if valid!=(query_tick>0) or (not valid and np.any(packet['actions_previous']!=0)):
        raise ValueError('Only the actual previous completed18-axis interval may be supplied')
    return h,w


def validate_macro_arrays(packet,arrays):
    if not isinstance(arrays,dict) or set(arrays)!=ACTION_KEYS:
        raise ValueError('Exact public macro arrays only; no future native PD, labels, pose or metadata input')
    for name,shape in (('macro_intents',(1,1,1,8)),('durations_s',(1,1,1)),('anchor_times_s',(1,))):
        a=arrays[name]
        if not isinstance(a,np.ndarray) or a.shape!=shape or a.dtype.kind!='f' or not np.isfinite(a).all():
            raise ValueError('Finite explicit macro array required: '+name)
    intent=arrays['macro_intents'][0,0,0]
    if (not np.array_equal(intent[:3],[0,1,0]) or np.any(intent[3:5]!=0)
            or np.any(intent[5:7]<0) or np.any(intent[5:7]>=1) or not math.isclose(float(intent[7]),.6,abs_tol=1e-6)):
        raise ValueError('PUSH continuation only; goal_xy unused/zero, current normalized uv, ORIGINAL total0.6m')
    if not any(math.isclose(float(arrays['durations_s'][0,0,0]),h,abs_tol=1e-6) for h in (.4,.8)):
        raise ValueError('Only registered0.4/0.8s prediction queries are allowed')
    if not math.isclose(float(arrays['anchor_times_s'][0]),float(packet['timestamps_s'][0,0]),abs_tol=1e-6):
        raise ValueError('Stale image/body anchor; regenerate the macro after real feedback')


def validate_public_continuation(packet,query):
    """Provenance check in addition to raw tensor shape/time validation."""
    if query.get('contract_id')!=CONTRACT_ID:raise ValueError('Wrong macro semantic contract')
    proof=query['public_provenance'];h,w=validate_snapshot(packet,proof['query_tick'])
    rgb_sha=hashlib.sha256(packet['rgb'][0,0].tobytes()).hexdigest()
    calibration=visual_calibration_sha(packet['camera_K'][0],packet['T_base_optical'][0])
    if rgb_sha!=proof['RGB_sha256'] or calibration!=proof['calibration_sha256']:
        raise ValueError('Stale RGB/calibration even at the same timestamp; regenerate public target')
    prefix=query['required_history'];tick=proof['query_tick']
    if prefix['first_control_tick']!=0 or prefix['last_control_tick']!=tick or prefix['consecutive_frames']!=tick+1:
        raise ValueError('Do not clip the task-reset reference out of continuation context')
    validate_macro_arrays(packet,query['model_macro_arrays'])
    result=query['public_proposals']
    if result['calibration_sha256']!=calibration:raise ValueError('Stale proposal calibration')
    p=single_visible_hypothesis(result,query['selected_frame_local_ref'],current_RGB_sha256=rgb_sha)
    if not np.allclose(query['model_macro_arrays']['macro_intents'][0,0,0,5:7],np.asarray(p['pixel_centroid_uv'])/[w,h],rtol=0,atol=1e-6):
        raise ValueError('Macro target does not correspond to its current public proposal')


def build_public_continuation(packet,*,query_tick,click_uv,duration_s,command=PublicPushContinuation()):
    h,w=validate_snapshot(packet,query_tick)
    if not isinstance(command,PublicPushContinuation):raise ValueError('Explicit typed native continuation command required')
    click=np.asarray(click_uv)
    if click.shape!=(2,) or click.dtype.kind not in 'fi' or not np.isfinite(click).all() or np.any(click<0) or np.any(click>=1):
        raise ValueError('Current normalized public image point required, not an engine object key')
    if type(duration_s) not in (int,float) or duration_s not in (.4,.8):raise ValueError('Registered public prediction interval required')
    proposals=propose_visual_candidates(packet['rgb'][0,0],packet['depth_m'][0,0],packet['camera_K'][0],packet['T_base_optical'][0])
    x,y=click[0]*w,click[1]*h
    matches=[p for p in proposals['candidates'] if p['pixel_bbox_xyxy'][0]<=x<p['pixel_bbox_xyxy'][2] and p['pixel_bbox_xyxy'][1]<=y<p['pixel_bbox_xyxy'][3]]
    if len(matches)!=1:raise ValueError('Public point has no unique visible proposal; never fall back to a private/nearest box')
    proposal=single_visible_hypothesis(proposals,matches[0]['frame_local_ref'],current_RGB_sha256=proposals['RGB_sha256'])
    u,v=proposal['pixel_centroid_uv']
    arrays=dict(macro_intents=np.asarray([[[[0.,1.,0.,0.,0.,u/w,v/h,command.original_total_distance_m]]]],dtype=np.float32),
                durations_s=np.asarray([[[duration_s]]],dtype=np.float32),anchor_times_s=packet['timestamps_s'][0].astype(np.float64,copy=True))
    validate_macro_arrays(packet,arrays)
    query=dict(contract_id=CONTRACT_ID,model_macro_arrays=arrays,public_proposals=proposals,selected_frame_local_ref=proposal['frame_local_ref'],
        public_provenance=dict(query_tick=query_tick,RGB_sha256=proposals['RGB_sha256'],calibration_sha256=proposals['calibration_sha256']),
        required_history=dict(first_control_tick=0,last_control_tick=query_tick,consecutive_frames=query_tick+1,
            retain_reset_goal_context=True,trailing_window_alone_not_certified=True,streaming_recurrence_permitted=True,
            reset_recurrent_state_per_episode=True,source_group_is_not_a_recurrent_cache_key=True),
        semantics=dict(command='continue same original registered native PUSH goal',distance='ORIGINAL TOTAL FROM TASK RESET, NOT additional/remaining distance',
            goal_body_xy='unused reserved zeros for this PUSH-only subtype, NOT an estimated remaining goal',target_uv='descriptor centroid in latest REAL image',
            no_new_goal_retarget_or_new_candidate_execution_certified=True),
        training_authorized=False,model_forwards=0,App_starts=0)
    validate_public_continuation(packet,query)
    return query
