"""Pure point-cloud planning factors and one arm-independent measured verifier.

References are available controller inputs, NOT promises of future tracking.
No FK, actors, environment state writes, admission authority or learned bounds.
"""
import numpy as np

ARMS=('P0','P1','P2','P3')
ROLES=('planning','final_actual')


def vector(value,n,name):
    result=np.asarray(value,dtype=float)
    if result.shape!=(n,) or not np.isfinite(result).all():raise ValueError('Invalid '+name)
    return result.copy()


def rotation(quaternion,*,normalize=False):
    q=vector(quaternion,4,'wxyz quaternion');norm=np.linalg.norm(q)
    if abs(norm-1)>1e-5:raise ValueError('Quaternion outside registered near-unit domain')
    if normalize:q=q/norm # private FK uses a unit root rotation; never write measured q.
    w,x,y,z=q
    return np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],
                     [2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],
                     [2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])


def reference_pose_cloud(raw_cloud,root_position,root_quaternion,box_position,box_quaternion,translation,reference_quaternion):
    points=np.asarray(raw_cloud,dtype=float)
    if points.ndim!=2 or points.shape[1]!=3 or not len(points) or not np.isfinite(points).all():raise ValueError('Invalid finite cloud')
    root=vector(root_position,3,'root position');box=vector(box_position,3,'box position')
    delta=np.zeros(3) if translation is None else vector(translation,3,'nominal translation')
    rb=rotation(box_quaternion);rr=rotation(root_quaternion,normalize=True);ref=rotation(reference_quaternion,normalize=True)
    # The native sampler stores R_box.T @ (p_world + delta - box). Invert its
    # exact floating transform instead of silently normalizing the box frame.
    world=points@np.linalg.inv(rb.T).T+box
    root_local=(world-root-delta)@rr
    return (root_local@ref.T+root+delta-box)@rb


def scalar_request(points,phase_ids,half,axis,inflation,*,endpoint,swept):
    points=np.asarray(points,dtype=float);ids=np.asarray(phase_ids)
    half=vector(half,3,'box half size');axis=vector(axis,3,'world-x in box')
    if points.ndim!=2 or points.shape[1]!=3 or not len(points) or not np.isfinite(points).all():raise ValueError('Invalid finite cloud')
    if ids.shape!=(len(points),) or not np.isfinite(ids).all() or not np.equal(ids,np.floor(ids)).all() or np.any(ids<0) or np.any(ids>40):raise ValueError('Invalid nominal phase identities')
    if any(half<=0) or axis[0]<.95 or not np.isfinite(inflation) or inflation<0:raise ValueError('Outside native request domain')
    expansion=.04*np.abs(axis[1:]) if swept else np.zeros(2)
    valid=(np.abs(points[:,1:])<=half[1:]+inflation+expansion).all(1)
    if endpoint:valid&=ids==40
    selected=np.flatnonzero(valid);maximum=None if not len(selected) else float(points[selected,0].max())
    needed=0. if maximum is None else float(max(0.,(maximum+half[0]+inflation)/axis[0]))
    return dict(minimum_shift_m=needed,maximum_box_local_x=maximum,samples_in_expanded_yz=int(len(selected)),
                request_within_original40mm=needed<=.04)


def select(raw,arm,role,reference_quaternion=None):
    if arm not in ARMS or role not in ROLES:raise ValueError('Unregistered arm or query role')
    points=np.asarray(raw['tip_cloud_box_m'],dtype=float);half=np.asarray(raw['box_size_m'],dtype=float)/2
    common=(raw['nominal_indices'],half,raw['world_x_in_box'],.015+raw['forecast_margin_m'])
    if role=='final_actual':
        if raw['nominal_translation_w'] is not None or raw['forecast_margin_m']!=0.:
            raise ValueError('Final actual verifier forbids nominal translation/forecast margin')
        # Identical actual FULL cloud + ORIGINAL fixed-yz rule for every arm.
        result=scalar_request(points,*common,endpoint=False,swept=False)
        return dict(result,evaluation_role=role,criterion='COMMON_original_full_cloud_fixed_yz',
                    predicted_pose_mode='actual_measured_pose',reference_quaternion_wxyz=None,
                    all_planning_requests=None,selected_forecast_cloud_box_m=points.tolist())
    if reference_quaternion is None:raise ValueError('Common planning input missing: existing controller orientation reference')
    # All arms construct and observe both clouds/four scalar calculations. Only
    # the selected scalar changes the existing minimum_shift_m interface.
    predicted=reference_pose_cloud(points,raw['root_position_w'],raw['root_quaternion_wxyz'],raw['box_position_w'],
        raw['box_quaternion_wxyz'],raw['nominal_translation_w'],reference_quaternion)
    values={}
    for name in ARMS:
        cloud=predicted if name in ('P1','P3') else points
        values[name]=scalar_request(cloud,*common,endpoint=name in ('P0','P1'),swept=True)
    return dict(values[arm],evaluation_role=role,criterion='factorial_planner_COMMON_swept_yz',
        predicted_pose_mode='existing_reference' if arm in ('P1','P3') else 'translation_only',
        reference_quaternion_wxyz=vector(reference_quaternion,4,'reference').tolist(),
        all_planning_requests=values,selected_forecast_cloud_box_m=(predicted if arm in ('P1','P3') else points).tolist(),
        reference_pose_cloud_box_m=predicted.tolist(),prospective_pose_error_bound=None,
        pose_error_bound_status='UNKNOWN_not_inferred_from_observed_outcomes')
