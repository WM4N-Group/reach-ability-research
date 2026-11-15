"""Bumpless arm hold during moving-base braking, before gravity unloading.

Retains the original0.45rad/s,1rad/s2,1cm soft margin and90% effort envelope
at current/20ms delayed/60ms constant-velocity forecasts. Feedforward is selected
inside those constraints, closest to its ACTUALLY issued previous value. The
stationary protected-stow gravity reconciliation starts only after capture.
"""
import math
import numpy as np
from .recovery_design import motor_aware_axis_interval


def brake_arm_hold(desired,reference,velocity,q,dq,kp,kd,previous_ff,effort,limits,dt=.005):
    vectors=(desired,reference,velocity,q,dq,kp,kd,previous_ff,effort)
    if (dt!=.005 or any(np.shape(x)!=(6,) or not np.isfinite(x).all() for x in vectors)
            or np.shape(limits)!=(6,2) or np.max(abs(velocity))>.45 or np.any(kp<=0)):
        raise ValueError('Actual six-axis issued reference/state and original5ms clock required')
    selected=[];speeds=[];feeds=[];receipts=[]
    vmax=.4499;amax=.999
    for j in range(6):
        r,v,x,w,K,D,F,E=map(float,(reference[j],velocity[j],q[j],dq[j],kp[j],kd[j],previous_ff[j],effort[j]))
        lo,hi=map(float,limits[j]);delta=float(desired[j])-r
        wanted=math.copysign(min(abs(delta)/dt,vmax,math.sqrt(2*amax*abs(delta))),delta)
        vn=max(-vmax,min(vmax,max(v-amax*dt,min(v+amax*dt,wanted))))
        rate_lo=r+dt*max(-vmax,v-amax*dt);rate_hi=r+dt*min(vmax,v+amax*dt)
        reserve=.90*E-1e-6
        # Additional per-command slew is tighter than the effort-only envelope.
        ff_lo,ff_hi=F-.05*E,F+.05*E
        centers=[x+h*w for h in (0.,.02,.06)]
        lower=max(rate_lo,lo+.01,max(c+(D*w-ff_hi-reserve)/K for c in centers))
        upper=min(rate_hi,hi-.01,min(c+(D*w-ff_lo+reserve)/K for c in centers))
        if lower>upper:
            raise RuntimeError('moving_brake_hold_position_FF_intersection_empty:'+str(j))
        candidate=max(lower,min(upper,r+dt*vn));speed=(candidate-r)/dt
        f_low=max(ff_lo,max(-reserve-K*(candidate-c)+D*w for c in centers))
        f_high=min(ff_hi,min(reserve-K*(candidate-c)+D*w for c in centers))
        if f_low>f_high:
            raise RuntimeError('moving_brake_hold_FF_interval_empty:'+str(j))
        ff=max(f_low,min(f_high,F))
        check=motor_aware_axis_interval(feedforward=ff,target_velocity=0.,delay_s=.02,
            reference=r,reference_velocity=v,measured_q=x,measured_dq=w,kp=K,kd=D,
            effort_limit=E,soft_lower=lo,soft_upper=hi,dt=dt)
        if not check['feasible'] or not check['lower']-1e-10<=candidate<=check['upper']+1e-10:
            raise RuntimeError('moving_brake_original_motor_envelope_refused:'+str(j))
        raw=[K*(candidate-c)-D*w+ff for c in centers]
        if max(map(abs,raw))>.9*E or abs(ff-F)>.05*E+1e-10:
            raise RuntimeError('moving_brake_original_effort_or_FF_slew_refused:'+str(j))
        selected.append(candidate);speeds.append(speed);feeds.append(ff)
        receipts.append(dict(axis=j,reference=candidate,velocity=speed,ff=ff,
            ff_interval=[f_low,f_high],raw_torque_0_20_60ms=raw,effort_limit=E,
            original_axis_interval=check))
    return np.asarray(selected),np.asarray(speeds),np.asarray(feeds),receipts
