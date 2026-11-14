"""Causal planar odometry from public onboard proprioception and declared start.

This is an observation-derived estimate, not simulator base pose. It integrates
10Hz body velocity/gyro, uses projected gravity for roll/pitch, and never applies
future smoothing or privately measured pose corrections. Drift is retained.
"""
import math
import numpy as np

class PublicNavigationState:
    def __init__(self,declared_initial_xy=(-.08,0.),declared_initial_yaw=0.):
        self.xy=np.asarray(declared_initial_xy,dtype=np.float64).copy();self.yaw=float(declared_initial_yaw)
        if self.xy.shape!=(2,) or not np.isfinite(self.xy).all() or not math.isfinite(self.yaw):raise ValueError('Finite declared task-reset XY/yaw required')
        self.time=None;self.previous=None
    @staticmethod
    def orientation_terms(proprio):
        p=np.asarray(proprio,dtype=np.float64)
        if p.shape!=(45,) or not np.isfinite(p).all():raise ValueError('Exact finite45D public proprioception required')
        g=p[36:39];norm=float(np.linalg.norm(g))
        if not .9<norm<1.1:raise ValueError('Actual normalized projected-gravity observation required')
        gx,gy,gz=g/norm;pitch=math.asin(float(np.clip(gx,-1.,1.)));roll=math.atan2(-gy,-gz)
        if abs(math.cos(pitch))<.1:raise ValueError('Planar odometry unavailable near pitch singularity')
        yaw_rate=(p[40]*math.sin(roll)+p[41]*math.cos(roll))/math.cos(pitch)
        return p,roll,pitch,float(yaw_rate)
    @staticmethod
    def world_velocity(p,roll,pitch,yaw):
        cr,sr=math.cos(roll),math.sin(roll);cp,sp=math.cos(pitch),math.sin(pitch);cy,sy=math.cos(yaw),math.sin(yaw)
        R=np.array([[cy*cp,cy*sp*sr-sy*cr,cy*sp*cr+sy*sr],[sy*cp,sy*sp*sr+cy*cr,sy*sp*cr-cy*sr]])
        return R@p[42:45]
    def update(self,timestamp_s,proprio):
        t=float(timestamp_s);p,roll,pitch,rate=self.orientation_terms(proprio)
        if not math.isfinite(t) or t<0:raise ValueError('Actual finite acquisition time required')
        if self.time is None:
            if abs(t)>1e-8:raise ValueError('Declared reset pose can only initialize from actual first frame at0')
        else:
            dt=t-self.time
            if dt<=0 or dt>.100001:raise ValueError('Consecutive <=10Hz observation intervals required; no resets or future backfill')
            old_p,old_roll,old_pitch,old_rate=self.previous
            new_yaw=self.yaw+.5*(old_rate+rate)*dt
            v0=self.world_velocity(old_p,old_roll,old_pitch,self.yaw);v1=self.world_velocity(p,roll,pitch,new_yaw)
            self.xy+=.5*(v0+v1)*dt;self.yaw=new_yaw
        self.previous=(p.copy(),roll,pitch,rate);self.time=t
        return np.r_[self.xy,self.yaw].copy()
    def goal_body_xy(self,declared_world_xy):
        if self.time is None:raise ValueError('Acquire a real public frame before transforming declared task goals')
        goal=np.asarray(declared_world_xy,dtype=np.float64)
        if goal.shape!=(2,) or not np.isfinite(goal).all():raise ValueError('Finite declared static task-map goal required')
        cy,sy=math.cos(self.yaw),math.sin(self.yaw)
        return np.array([[cy,sy],[-sy,cy]])@(goal-self.xy)
