"""Pure SOFTWARE candidate for simultaneous recovery-reference constraints.

A sequential candidate veto is NOT proof that the feasible intersection is empty.
Compute actual scalar speed/acceleration/soft-limit/two-horizon PD intervals
first. No threshold relaxation, source reinterpretation, actuation or physics.
Geometry and real delayed/contact dynamics are NOT certified by these intervals.
"""
import math


def finite(x):return type(x) in (int,float) and math.isfinite(x)


def axis_interval(*,reference,reference_velocity,measured_q,measured_dq,kp,kd,effort_limit,
                  soft_lower,soft_upper,dt=.02,speed_limit=.45,acceleration_limit=1.,horizon=.04,reserve=.90):
    values=locals().copy()
    if not all(finite(v) for v in values.values()):raise ValueError('Finite actual scalar inputs required')
    if (min(kp,effort_limit,dt,speed_limit,acceleration_limit,horizon)<=0 or kd<0 or
            not 0<reserve<.98 or soft_lower>=soft_upper or abs(reference_velocity)>speed_limit):
        raise ValueError('Valid frozen reference/PD bounds required; never clip an invalid seed')
    vlo=max(-speed_limit,reference_velocity-acceleration_limit*dt)
    vhi=min(speed_limit,reference_velocity+acceleration_limit*dt)
    rate_lo=reference+dt*vlo;rate_hi=reference+dt*vhi
    center0=measured_q+kd/kp*measured_dq;center1=center0+horizon*measured_dq
    radius=reserve*effort_limit/kp
    effort_lo=max(center0,center1)-radius;effort_hi=min(center0,center1)+radius
    lower=max(rate_lo,effort_lo,soft_lower);upper=min(rate_hi,effort_hi,soft_upper)
    return dict(feasible=lower<=upper,lower=lower,upper=upper,signed_width_rad=upper-lower,
        rate_interval=[rate_lo,rate_hi],effort_interval=[effort_lo,effort_hi],soft_interval=[soft_lower,soft_upper],
        reference_speed_limit=speed_limit,reference_acceleration_limit=acceleration_limit,
        reserve_ratio=reserve,horizon_s=horizon,geometry_or_dynamic_safety_certified=False)


def choose_axis_reference(*,desired,**kwargs):
    if not finite(desired):raise ValueError('Finite explicitly requested goal required')
    interval=axis_interval(**kwargs)
    if not interval['feasible']:return dict(**interval,selected=None,reason='scalar_reference_constraints_have_empty_intersection')
    q=kwargs['reference'];v=kwargs['reference_velocity'];dt=kwargs.get('dt',.02)
    a=kwargs.get('acceleration_limit',1.);vmax=kwargs.get('speed_limit',.45)
    delta=desired-q
    wanted=math.copysign(min(abs(delta)/dt,vmax,math.sqrt(2*a*abs(delta))),delta)
    updated=max(-vmax,min(vmax,max(v-a*dt,min(v+a*dt,wanted))))
    nominal=q+dt*updated
    selected=max(interval['lower'],min(interval['upper'],nominal))
    return dict(**interval,selected=selected,nominal=nominal,selected_velocity=(selected-q)/dt,
        sequential_nominal_would_be_vetoed=not interval['lower']<=nominal<=interval['upper'],
        reason='scalar_intersection_candidate_only_not_geometry_or_physics_acceptance')
