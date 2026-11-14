"""E0-E3 finite-cloud shadow requests for the existing v317 scalar interface.

Not a controller, SDK hook, fresh-data certificate, state write, or RUN permit.
The old robot-only snapshot is deliberately NOT enough: never invent box pose
or excluded tip samples from recorded maxima/default reset geometry.
"""
import math

from tip_envelope_standoff import preview_tip_retreat, finite, vec3

PLAN_SHA='4753fa761aea0054cf98d6d720afcf553bb825b71a972a55d6d12084bce0b9e1'
PATH_SHA='9c6db3af65afe62ace57f5d85f3a773666074b381383d037db4fa3df62162cbc'
ARMS=('E0','E1','E2','E3')


def evaluate_native_shadow(packet,arm):
    if arm not in ARMS:raise ValueError('Unknown native ablation arm')
    out=dict(schema='native-v317-tip-ablation-shadow-result-v1',arm=arm,status='not_ready',
             execution_authorized=False,actual_freshness_certified=False,actual_navigation_success=None)
    required=['v317_plan_sha256','frozen_waypoints_sha256','query_step','query_time_s',
              'root_pose_world','box_pose_world','named_joint_state','tip_cloud_box','world_x_in_box',
              'nominal_translation_w','source_hand_FK_error_m']
    missing=[k for k in required if k not in packet or (packet[k] is None and k!='nominal_translation_w')]
    if missing:return dict(out,missing=missing,reason='No source/default/geometry imputation')
    if packet['v317_plan_sha256']!=PLAN_SHA or packet['frozen_waypoints_sha256']!=PATH_SHA:
        raise ValueError('Wrong frozen native caller or two-point path; no latest16-point substitution')
    step=packet['query_step'];time=finite(packet['query_time_s'])
    if type(step) is not int or step<0 or time<0:raise ValueError('Invalid native query clock')
    for key in ['root_pose_world','box_pose_world','named_joint_state','tip_cloud_box']:
        part=packet[key]
        if part.get('step')!=step or part.get('time_s')!=time:
            raise ValueError('Mixed declared query clocks; stamps alone still do NOT certify actual freshness')
    for key in ['root_pose_world','box_pose_world']:
        vec3(packet[key]['position_m'])
        quat=packet[key]['quaternion_wxyz']
        if len(quat)!=4 or abs(sum(finite(q)**2 for q in quat)-1)>1e-5:
            raise ValueError('Invalid declared world quaternion')
    # Geometry must refer to the recorded box frame, not an unrelated valid axis.
    quat=packet['box_pose_world']['quaternion_wxyz']
    norm=math.sqrt(sum(q*q for q in quat))
    w,x,y,z=[q/norm for q in quat]  # derived frame only; raw recorded quaternion is preserved
    expected_axis=(1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w))
    axis=vec3(packet['world_x_in_box'])
    if max(abs(a-b) for a,b in zip(axis,expected_axis))>1e-6:
        raise ValueError('Box quaternion and world-x projection frame mismatch')
    joint=packet['named_joint_state']
    names=joint['joint_names']
    expected={f'{leg}_{j}_joint' for leg in ['FR','FL','RR','RL'] for j in ['hip','thigh','calf']}|{f'joint{i}' for i in range(1,7)}
    if len(names)!=18 or set(names)!=expected or len(joint['q_rad'])!=18 or len(joint['dq_rad_s'])!=18:
        raise ValueError('Need actual named18-axis state, not an FL/FR array guess')
    tuple(finite(x) for x in joint['q_rad']+joint['dq_rad_s'])
    cloud=packet['tip_cloud_box']
    if cloud.get('frame')!='box_local' or cloud.get('censored_by_yz_gate') is not False:
        raise ValueError('Need uncensored full finite tip cloud in explicit box frame')
    samples=cloud['samples']
    ids=[(r['nominal_index'],r['residual_corner_index']) for r in samples]
    if len(ids)!=2624 or set(ids)!={(i,j) for i in range(41) for j in range(64)}:
        raise ValueError('Frozen two-point path needs all41x64 samples, not extrema imputation')
    for r in samples:vec3(r['point_box_m'])
    fk_error=finite(packet['source_hand_FK_error_m'])
    if not 0<=fk_error<=.0002:raise ValueError('Outside original source-hand FK agreement guard')
    translation=packet['nominal_translation_w']
    forecast=0.
    if translation is not None:
        translation=vec3(translation)
        if math.sqrt(sum(v*v for v in translation))>.09:raise ValueError('Outside original nominal translation domain')
        forecast=.005
    points=[r['point_box_m'] for r in samples if arm!='E1' or r['nominal_index']==40]
    if arm=='E0':
        return dict(out,status='shadow_request_only',minimum_shift_m=0.,source_role=packet.get('data_role'),
                    caller_required='original support-only selection and all native/final READY gates remain')
    request=preview_tip_retreat(points,[.6,.6,.1],packet['world_x_in_box'],forecast_margin_m=forecast,
                                lateral_membership='swept' if arm=='E3' else 'fixed')
    return dict(out,status='shadow_request_only' if request['request_within_original_domain'] else 'unknown_no_sufficient_request_within_original_cap',
                minimum_shift_m=request['minimum_front_plane_request_m'] if request['request_within_original_domain'] else None,
                geometry_preview=request,source_role=packet.get('data_role'),
                caller_required='existing prospective_support(minimum_shift_m), grid/reserve and measured final recheck; no direct base command')


def map_historical_robot_query(observation):
    """Map the bound v317 observation, preserving actual q/pose and missing box/cloud.

    Source IDs come from the verified binding, not guessed physical defaults.
    A later PUSH box sample or stance yaw MUST NOT become query-time box pose.
    """
    if observation.get('schema')!='actual-historical-navigation-entry-observation-v1':
        raise ValueError('Expected the source-bound historical entry observation')
    state=observation['measured_state'];step=observation['step'];time=observation['time_s']
    return dict(schema='native-v317-tip-cloud-query-robot-part-only-v2',
        v317_plan_sha256=PLAN_SHA,frozen_waypoints_sha256=PATH_SHA,
        query_step=step,query_time_s=time,
        root_pose_world=dict(step=step,time_s=time,position_m=list(state['root_position']),
                             quaternion_wxyz=list(state['root_quaternion'])),
        named_joint_state=dict(step=step,time_s=time,joint_names=list(observation['joint_names']),
                               q_rad=list(state['q']),dq_rad_s=list(state['dq'])),
        source_report_sha256=observation['source_report_sha256'],
        source_control_sha256=observation['source_control_sha256'],
        data_role='historical_exposed_robot_state_only_NOT_complete_geometry_or_unseen',
        box_pose_world=None,tip_cloud_box=None,world_x_in_box=None,source_hand_FK_error_m=None,
        not_imputed=['box from later PUSH sample','box quaternion from stance yaw','missing finite samples','actual-q clipping'],
        execution_authorized=False)
