"""OFFLINE candidate: zero-goal CLIMB arm reference governor, NOT deployed.

The original task goal/success predicates remain zero; only the motor reference
heads to the nearest .01rad hard-interior point (within original .08 tolerance).
Native actual hard-limit guard stays enabled. First-step command feasibility is
NOT trajectory safety. Future QPs must consume the same governed arm command;
post-QP replacement alone is explicitly NOT an authorized integration design.
"""
import math


def interior_motor_goal(nominal_goal,hard_limits):
    if len(nominal_goal)!=6 or len(hard_limits)!=6 or any(len(v)!=2 for v in hard_limits):raise ValueError('Six original arm goals/limits required')
    if any(float(g)!=0. for g in nominal_goal):raise ValueError('This candidate is only for original zero-arm CLIMB')
    result=[]
    for g,(lo,hi) in zip(nominal_goal,hard_limits):
        if not all(math.isfinite(float(v)) for v in (g,lo,hi)) or hi-lo<=.02:raise ValueError('Original finite hard limits with interior required')
        value=max(float(lo)+.01,min(float(hi)-.01,float(g)))
        if abs(value-float(g))>=.08:raise ValueError('Motor interior would not satisfy original zero-goal tolerance')
        result.append(value)
    return result


def require_actual_hard_arm_guard(q,hard_limits):
    if len(q)!=6 or len(hard_limits)!=6:raise ValueError('Six actual arm positions/limits required')
    for value,(lo,hi) in zip(q,hard_limits):
        if not all(math.isfinite(float(v)) for v in (value,lo,hi)):raise ValueError('Finite actual joint state required')
        if value<lo-.001 or value>hi+.001:raise RuntimeError('original_actual_arm_joint_limit_refused_no_recovery')


def discrete_braking_speed_bound(distance,*,acceleration=.999,dt=.005,max_speed=.4499):
    """Maximum next reference speed with an admitted discrete stop remaining.

    For n=ceil(v/(a*dt)), exact future displacement including this command is
    dt*(n*v-a*dt*n*(n-1)/2). This is reference kinematics, NOT robot prediction.
    Binary search keeps the lower admitted bound, without relaxing a/dt/v.
    """
    if not all(math.isfinite(float(x)) for x in (distance,acceleration,dt,max_speed)) or distance<0 or acceleration<=0 or dt!=.005 or max_speed<=0:
        raise ValueError('Original finite reference distance/rate domain required')
    low,high=0.,float(max_speed);step=acceleration*dt
    for _ in range(55):
        speed=(low+high)/2;n=max(1,math.ceil(speed/step))
        travel=dt*(n*speed-step*n*(n-1)/2)
        if travel<=distance:low=speed
        else:high=speed
    # Tighten (never widen) the bound against accumulated binary rounding
    # when the motor goal coincides with the hard-interior boundary.
    return max(0.,low-1e-10)


def select_climb_axis(*,goal,reference,velocity,q,dq,kp,kd,gravity,previous_ff,effort,lower_limit,upper_limit,dt=.005):
    values=(goal,reference,velocity,q,dq,kp,kd,gravity,previous_ff,effort,lower_limit,upper_limit)
    if dt!=.005 or not all(math.isfinite(float(x)) for x in values) or kp<=0 or kd<0 or effort<=0 or upper_limit-lower_limit<=.02 or abs(velocity)>.45:
        raise ValueError('Original finite 5ms motor/reference domain required')
    r,v,x,w,K,D,F,E=map(float,(reference,velocity,q,dq,kp,kd,previous_ff,effort))
    vmax=.4499;amax=.999;delta=float(goal)-r
    wanted=math.copysign(min(abs(delta)/dt,vmax,discrete_braking_speed_bound(abs(delta),acceleration=amax,dt=dt,max_speed=vmax)),delta)
    vn=max(-vmax,min(vmax,max(v-amax*dt,min(v+amax*dt,wanted))))
    rate_lo=r+dt*max(-vmax,v-amax*dt);rate_hi=r+dt*min(vmax,v+amax*dt)
    reserve=.90*E-1e-6;ff_lo,ff_hi=F-.05*E,F+.05*E
    centers=[x+h*w for h in (0.,.02,.06)]
    lower=max(rate_lo,float(lower_limit)+.01,max(c+(D*w-ff_hi-reserve)/K for c in centers))
    upper=min(rate_hi,float(upper_limit)-.01,min(c+(D*w-ff_lo+reserve)/K for c in centers))
    if lower>upper:raise RuntimeError('reconciled_reference_FF_intersection_empty')
    candidate=max(lower,min(upper,r+dt*vn));speed=(candidate-r)/dt
    f_low=max(ff_lo,max(-reserve-K*(candidate-c)+D*w for c in centers))
    f_high=min(ff_hi,min(reserve-K*(candidate-c)+D*w for c in centers))
    if f_low>f_high:raise RuntimeError('reconciled_FF_interval_empty')
    # IMPORTANT: FF tracks only original gravity. Adding K*(goal-reference)
    # would cancel the reference-rate governor and command the distant goal
    # through FF immediately. Nominal task arm goal remains native zero.
    wanted_ff=float(gravity)
    ff=max(f_low,min(f_high,wanted_ff))
    raw=[K*(candidate-c)-D*w+ff for c in centers]
    if max(map(abs,raw))>.9*E or abs(ff-F)>.05*E+1e-10:raise RuntimeError('original_effort_or_FF_slew_refused')
    return dict(reference=candidate,velocity=speed,ff=ff,ff_objective=wanted_ff,
        reference_interval=[lower,upper],FF_interval=[f_low,f_high],
        rate_interval=[rate_lo,rate_hi],raw_torque_0_20_60ms=raw,
        effort_limit=E,unchanged_effort_reserve=.9,unchanged_FF_slew_fraction=.05,
        unchanged_speed_limit=.45,unchanged_acceleration_limit=1.,unchanged_inner_margin=.01)



def propose_climb_arm_step(nominal_goal,reference,velocity,q,dq,kp,kd,gravity,previous_ff,effort,hard_limits):
    import numpy as np
    from mujoco_zyh.recovery_design import motor_aware_axis_interval
    require_actual_hard_arm_guard(q,hard_limits)
    goal=interior_motor_goal(nominal_goal,hard_limits);positions=[];speeds=[];feeds=[];receipts=[]
    for j in range(6):
        row=select_climb_axis(goal=goal[j],reference=reference[j],velocity=velocity[j],q=q[j],dq=dq[j],kp=kp[j],kd=kd[j],gravity=gravity[j],previous_ff=previous_ff[j],effort=effort[j],lower_limit=hard_limits[j][0],upper_limit=hard_limits[j][1])
        check=motor_aware_axis_interval(feedforward=row['ff'],target_velocity=0.,delay_s=.02,reference=float(reference[j]),reference_velocity=float(velocity[j]),measured_q=float(q[j]),measured_dq=float(dq[j]),kp=float(kp[j]),kd=float(kd[j]),effort_limit=float(effort[j]),soft_lower=float(hard_limits[j][0]),soft_upper=float(hard_limits[j][1]),dt=.005)
        if not check['feasible'] or not check['lower']-1e-10<=row['reference']<=check['upper']+1e-10:raise RuntimeError('original_native_motor_interval_refused:'+str(j))
        row.update(axis=j,original_native_motor_interval=check);receipts.append(row);positions.append(row['reference']);speeds.append(row['velocity']);feeds.append(row['ff'])
    return np.asarray(positions),np.asarray(speeds),np.asarray(feeds),receipts
