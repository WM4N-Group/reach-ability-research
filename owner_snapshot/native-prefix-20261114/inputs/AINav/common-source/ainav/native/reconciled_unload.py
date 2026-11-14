"""Candidate reference/FF selector with the EXISTING native safety bounds.

Generalizes the original brake_arm_hold feasible-set algebra. Reference moves
toward the fixed measured unload posture; FF is selected independently within
the same 0.05E slew/0.90E effort bounds, nearest the gravity-debiased spring
objective. It does not force the original unload controller's FF/progress line.
Not yet deployed or a trajectory/stability proof. No actor/world-model/physics.
"""
import math


def select_axis(*,goal,reference,velocity,q,dq,kp,kd,gravity,previous_ff,effort,lower_limit,upper_limit,dt=.005):
    values=(goal,reference,velocity,q,dq,kp,kd,gravity,previous_ff,effort,lower_limit,upper_limit)
    if dt!=.005 or not all(math.isfinite(float(x)) for x in values) or kp<=0 or kd<0 or effort<=0 or upper_limit-lower_limit<=.02 or abs(velocity)>.45:
        raise ValueError('Original finite 5ms motor/reference domain required')
    r,v,x,w,K,D,F,E=map(float,(reference,velocity,q,dq,kp,kd,previous_ff,effort))
    vmax=.4499;amax=.999;delta=float(goal)-r
    wanted=math.copysign(min(abs(delta)/dt,vmax,math.sqrt(2*amax*abs(delta))),delta)
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
    # Same Kp/Kd; this soft objective represents gravity-supported ORIGINAL PD
    # at the fixed unload goal. It is clipped only inside the admitted interval,
    # never by changing or bypassing a safety threshold.
    wanted_ff=float(gravity)+K*(float(goal)-candidate)
    ff=max(f_low,min(f_high,wanted_ff))
    raw=[K*(candidate-c)-D*w+ff for c in centers]
    if max(map(abs,raw))>.9*E or abs(ff-F)>.05*E+1e-10:raise RuntimeError('original_effort_or_FF_slew_refused')
    return dict(reference=candidate,velocity=speed,ff=ff,ff_objective=wanted_ff,
        reference_interval=[lower,upper],FF_interval=[f_low,f_high],
        rate_interval=[rate_lo,rate_hi],raw_torque_0_20_60ms=raw,
        effort_limit=E,unchanged_effort_reserve=.9,unchanged_FF_slew_fraction=.05,
        unchanged_speed_limit=.45,unchanged_acceleration_limit=1.,unchanged_inner_margin=.01)


def reconciled_unload_reference(goal,reference,velocity,q,dq,kp,kd,gravity,previous_ff,effort,limits):
    import numpy as np
    from mujoco_zyh.recovery_design import motor_aware_axis_interval
    vectors=(goal,reference,velocity,q,dq,kp,kd,gravity,previous_ff,effort)
    if any(np.shape(v)!=(6,) or not np.isfinite(v).all() for v in vectors) or np.shape(limits)!=(6,2):
        raise ValueError('Actual six-axis native reference/state/limits required')
    positions=[];speeds=[];feeds=[];receipts=[]
    for j in range(6):
        row=select_axis(goal=goal[j],reference=reference[j],velocity=velocity[j],q=q[j],dq=dq[j],kp=kp[j],kd=kd[j],
            gravity=gravity[j],previous_ff=previous_ff[j],effort=effort[j],lower_limit=limits[j,0],upper_limit=limits[j,1])
        check=motor_aware_axis_interval(feedforward=row['ff'],target_velocity=0.,delay_s=.02,
            reference=float(reference[j]),reference_velocity=float(velocity[j]),measured_q=float(q[j]),measured_dq=float(dq[j]),
            kp=float(kp[j]),kd=float(kd[j]),effort_limit=float(effort[j]),soft_lower=float(limits[j,0]),soft_upper=float(limits[j,1]),dt=.005)
        if not check['feasible'] or not check['lower']-1e-10<=row['reference']<=check['upper']+1e-10:
            raise RuntimeError('original_native_motor_envelope_refused:'+str(j))
        row.update(axis=j,original_native_motor_interval=check)
        positions.append(row['reference']);speeds.append(row['velocity']);feeds.append(row['ff']);receipts.append(row)
    return np.asarray(positions),np.asarray(speeds),np.asarray(feeds),receipts
