"""Maximin motor reserve within ORIGINAL zero-arm acceptance, not a new task.

Geometry-only reference choice; no scene IDs, future world states or rollout.
The .01 hard-interior/rate/effort/FF guards remain unchanged. Choosing a center
increases reference slack, but cannot certify coupled actor-start stability.
"""
import math


def reserve_motor_goal(nominal_goal,hard_limits):
    if len(nominal_goal)!=6 or len(hard_limits)!=6:
        raise ValueError('Six original zero-arm goals and hard limits required')
    result=[];bands=[]
    for goal,limits in zip(nominal_goal,hard_limits):
        if len(limits)!=2:raise ValueError('Original hard-limit pair required')
        g,lo,hi=map(float,(goal,*limits))
        if not all(math.isfinite(x) for x in (g,lo,hi)) or g!=0. or hi-lo<=.02:
            raise ValueError('Original finite zero-arm CLIMB domain required')
        # Original task |actual q-zero|<.08 is NOT changed. References keep
        # the same .01 inset from both hard bounds and acceptance boundaries.
        lower=max(lo+.01,g-.08+.01);upper=min(hi-.01,g+.08-.01)
        if lower>=upper:raise ValueError('No robust motor band inside original task acceptance')
        motor=(lower+upper)/2
        if abs(motor-g)>=.08 or not lo+.01<=motor<=hi-.01:
            raise ValueError('Motor reserve violates original hard-interior/task domain')
        result.append(motor);bands.append(dict(lower=lower,upper=upper,
            center=motor,maximin_reference_radius=(upper-lower)/2,
            original_task_goal=g,original_task_tolerance=.08,unchanged_hard_interior=.01))
    return result,bands


def propose_reserve_climb_arm_step(nominal_goal,reference,velocity,q,dq,kp,kd,gravity,previous_ff,effort,hard_limits):
    import numpy as np
    from .climb_arm_candidate import require_actual_hard_arm_guard,select_climb_axis
    from mujoco_zyh.recovery_design import motor_aware_axis_interval
    require_actual_hard_arm_guard(q,hard_limits)
    goals,bands=reserve_motor_goal(nominal_goal,hard_limits)
    positions=[];speeds=[];feeds=[];receipts=[]
    for j in range(6):
        row=select_climb_axis(goal=goals[j],reference=reference[j],velocity=velocity[j],q=q[j],dq=dq[j],kp=kp[j],kd=kd[j],gravity=gravity[j],previous_ff=previous_ff[j],effort=effort[j],lower_limit=hard_limits[j][0],upper_limit=hard_limits[j][1])
        interval=motor_aware_axis_interval(feedforward=row['ff'],target_velocity=0.,delay_s=.02,reference=float(reference[j]),reference_velocity=float(velocity[j]),measured_q=float(q[j]),measured_dq=float(dq[j]),kp=float(kp[j]),kd=float(kd[j]),effort_limit=float(effort[j]),soft_lower=float(hard_limits[j][0]),soft_upper=float(hard_limits[j][1]),dt=.005)
        if not interval['feasible'] or not interval['lower']-1e-10<=row['reference']<=interval['upper']+1e-10:
            raise RuntimeError('original_native_motor_interval_refused:'+str(j))
        row.update(axis=j,original_native_motor_interval=interval,motor_goal_rule='maximin_original_acceptance_intersection',motor_goal=goals[j],original_task_goal=0.,reserve_band=bands[j])
        receipts.append(row);positions.append(row['reference']);speeds.append(row['velocity']);feeds.append(row['ff'])
    return np.asarray(positions),np.asarray(speeds),np.asarray(feeds),receipts
