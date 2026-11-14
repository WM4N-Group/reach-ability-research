"""Independent zero-velocity PUSH-leg stop, seeded only after actual issuance.

The retired controller, goal, IK history and incoming motor FIFO are untouched.
The frozen original leg actor sees its original observation layout. Only its
requested body-velocity term becomes zero; measured motion/contact stay real.
"""
from copy import deepcopy
import numpy as np


class IssuedPushObservation:
    def __init__(self,view):
        self.proposal=None;self.committed=None;self.view=view
        observation=view.observation;set_action=view.set_action
        def observed():
            value=observation()
            self.proposal=dict(time_s=float(view.data.time),observation=value.copy(),
                history=[x.copy() for x in view.history])
            return value
        def applied(leg,arm):
            value=set_action(leg,arm)
            if self.proposal is not None:
                self.proposal.update(raw_leg=np.asarray(leg).copy(),applied=view.applied_commands.copy(),targets=view.targets.copy())
            return value
        view.observation=observed;view.set_action=applied

    def after_actual_issuance(self,command):
        p=self.proposal
        if (p is None or 'raw_leg' not in p or float(self.view.data.time)<=p['time_s']
                or not np.array_equal(command.position,p['targets'])):
            return  # preparation/blend or a proposal which never reached motors
        if self.committed is not None and self.committed['time_s']==p['time_s']:return
        self.committed=deepcopy(p)
        self.committed['first_actual_issued_time_s']=float(self.view.data.time)

    def seed(self):
        if self.committed is None:raise RuntimeError('PUSH stop needs an actually issued native observation')
        return deepcopy(self.committed)


def leg_scale_from_issued(seed,slots):
    raw=np.asarray(seed['raw_leg']);applied=np.asarray(seed['applied'])[slots]
    if raw.shape!=(12,) or applied.shape!=(12,) or not np.isfinite(np.r_[raw,applied]).all():
        raise ValueError('Original leg action layout required')
    norm=float(raw@raw)
    if norm<1e-8:raise ValueError('Cannot identify actual native leg release scale')
    scale=float(raw@applied/norm)
    if not -1e-6<=scale<=1+1e-6 or not np.allclose(raw*scale,applied,atol=2e-6,rtol=1e-6):
        raise ValueError('Unrecognized actual native leg postprocessing')
    return float(np.clip(scale,0,1))


def advance_stop_history(history,terms):
    expected=(3,3,18,18,18,3,7)
    if len(history)!=7 or len(terms)!=7:raise ValueError('Original seven observation terms required')
    out=[]
    for old,current,n in zip(history,terms,expected):
        if np.shape(old)!=(3,n) or np.shape(current)!=(n,) or not np.isfinite(current).all():
            raise ValueError('Original actual native observation shape required')
        out.append(np.vstack((old[1:],np.asarray(current)[None])))
    return out


def nn_landing_capture(m):
    return bool(m['base_linear_speed']<.08 and m['base_angular_speed']<.15
        and m['tilt_rad']<.1 and min(m['foot_normal_N'])>=12
        and m['max_foot_speed']<.08 and m['arm_speed']<.5)


def nn_wbc_handoff_capture(m):
    # Original WBC explicitly lands feet. Requiring the locomotion NN itself
    # to stop all four feet prevented the v4 transfer while it kept trotting.
    return bool(m['base_linear_speed']<.15 and m['base_angular_speed']<.15
        and m['tilt_rad']<.1 and m['arm_speed']<.3
        and sum(x>=12 for x in m['foot_normal_N'])>=2
        and m['brake_loaded_feet_max_speed']<.03
        and m['brake_loaded_feet_span_body_x_m']>.2
        and m['brake_loaded_feet_span_body_y_m']>.15)


class NativePushLegStop:
    def __init__(self,runtime,seed):
        from runtime import infer
        self.infer=infer;self.r=runtime;self.s=runtime.sim;self.pm=runtime.push['model']
        self.history=[x.copy() for x in seed['history']]
        self.ee=self.history[6][-1].copy();self.slots=np.asarray(self.s.controller.leg_slots,dtype=int)
        if not np.array_equal(np.sort(self.slots),np.arange(12)):
            raise ValueError('Native PUSH leg mapping must cover actual twelve leg motors')
        self.scale=leg_scale_from_issued(seed,self.slots)
        self.seed_time=float(seed['time_s']);self.seed_issued_time=float(seed['first_actual_issued_time_s'])
        if not self.seed_time<self.seed_issued_time<=float(self.s.data.time):
            raise ValueError('Stop seed must precede real issuance and current query')
        self.targets=runtime.last.position[:12].copy();self.last_policy_time=-np.inf;self.forwards=0

    def command_legs(self):
        s=self.s;now=float(s.data.time)
        if now-self.last_policy_time>=.02-1e-8:
            import torch
            b=self.r.push['bridge'].box_push;robot=s.robot.data
            actual=(self.r.last.position-self.pm.REFERENCE)/.25
            terms=[robot.root_ang_vel_b[0].numpy()*.2,robot.projected_gravity_b[0].numpy(),
                s.data.qpos[s.qids]-self.pm.REFERENCE,s.data.qvel[s.dids]*.05,actual,np.zeros(3),self.ee]
            self.history=advance_stop_history(self.history,terms)
            extra=torch.cat((b.box_observation(s),s.box_push_pose_override_active[:,None].float(),
                b.hand_contact(s,s.hand_cfg)[:,None].float()),dim=1)[0].numpy()
            obs=np.r_[np.concatenate([h.ravel() for h in self.history]),extra].astype(np.float32)
            if obs.shape!=(226,) or not np.isfinite(obs).all():raise ValueError('Original PUSH actor observation226 required')
            raw=self.infer(self.r.push_actors[0],obs,self.r.device)
            action=np.zeros(18);action[self.slots]=np.asarray(raw)*self.scale
            self.targets=(self.pm.REFERENCE+.25*np.clip(action,-10,10))[:12]
            self.last_policy_time=now;self.forwards+=1
        return self.targets.copy()
