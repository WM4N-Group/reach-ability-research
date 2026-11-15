"""Acquired-only mixed-rate first-NAV model request, shared with frozen adapters.

No native action, model training, trajectory future, pose integration or robot
state write. The provided model state/action encoders remain separately pinned.
The actual decision/dispatch gateway still owns source epoch and one-shot safety.
"""
from collections import deque
import hashlib,math
import numpy as np
from PIL import Image
from visual_push_macro_contract import validate_snapshot,OBS_KEYS
from visual_box_proposals import propose_visual_candidates
from .public_task_state import assemble_public_task_state
from .visible_surface_goal import describe_visible_goal


def finite_time(value):
    if type(value) not in (int,float) or not math.isfinite(value) or value<0:raise ValueError('Finite actual observed timestamp required')
    return float(value)

class FirstNAVBoundaryRequest:
    def __init__(self,normalizer,state_encoder,action_encoder):
        self.mean=np.asarray(normalizer['mean'],np.float32);self.scale=np.asarray(normalizer['scale'],np.float32)
        if self.mean.shape!=(45,) or self.scale.shape!=(45,) or not np.isfinite(self.mean).all() or not np.isfinite(self.scale).all() or np.any(self.scale<=0):raise ValueError('Frozen TRAIN-only45D normalizer required')
        self.state_encoder=state_encoder;self.action_encoder=action_encoder;self.frames=deque(maxlen=3);self.last_time=None
    def append_acquired(self,packet,*,declared_macro,macro_declared_at_s):
        if not isinstance(packet,dict) or set(packet)!=OBS_KEYS:raise ValueError('Only exact eight public acquisition arrays accepted')
        t=float(packet['timestamps_s'][0,0]);tick=int(round(t/.02));validate_snapshot(packet,tick)
        if self.last_time is None:
            if abs(t)>1e-7:raise ValueError('Start from real task-reset observation; no mid-episode history rebasing')
        elif abs(t-self.last_time-.1)>1e-6:raise ValueError('Missing/stale/duplicated actual10Hz image history')
        image=packet['rgb'][0,0];d=packet['depth_m'][0,0,...,0];h,w=image.shape[:2];H,W=64,96
        rgb=np.asarray(Image.fromarray(image).resize((W,H),Image.Resampling.BILINEAR)).copy()
        yy=np.minimum((np.arange(H)+.5)*h/H,h-1).astype(int);xx=np.minimum((np.arange(W)+.5)*w/W,w-1).astype(int)
        depth=d[yy][:,xx];valid=np.isfinite(depth)&(depth>=.05)&(depth<=15.)
        # Match the frozen training observation representation, not its labels.
        depth=np.where(valid,depth,0).astype(np.float16).astype(np.float32);depth=np.where(valid,depth,np.nan)
        K=packet['camera_K'][0].copy();K[0]*=W/w;K[1]*=H/h;mount=packet['T_base_optical'][0].copy();body=packet['proprio'][0,0].copy()
        state=assemble_public_task_state(rgb,depth,K,mount,body,time_s=t,declared_macro=declared_macro,macro_declared_at_s=macro_declared_at_s)['state']
        self.frames.append(dict(time_s=t,rgb=rgb,depth=depth,K=K,mount=mount,raw_state=state.copy(),observed_macro=declared_macro));self.last_time=t
    def build(self,*,decision_time_s,actual_public_body,body_observed_at_s,known_B_completion,candidate_dx_m=(-.02,0.,.02)):
        anchor=finite_time(decision_time_s);body_time=finite_time(body_observed_at_s);body=np.asarray(actual_public_body,np.float32)
        if len(self.frames)!=3:raise ValueError('Three acquired frames required; never repeat/pad a frame')
        if body.shape!=(45,) or not np.isfinite(body).all() or body_time>anchor+1e-7 or anchor-body_time>.020001:raise ValueError('Current-or-past actual45D public body observation required')
        latest=self.frames[-1]
        if latest['time_s']>anchor+1e-7 or anchor-latest['time_s']>.100001:raise ValueError('Current-or-past actual image within registered acquisition age required')
        if any(f['observed_macro']!='PUSH_B' for f in self.frames):raise ValueError('First NAV boundary must retain actually observed PUSH_B history')
        if not isinstance(known_B_completion,dict) or set(known_B_completion)!={'time','event','stage'} or known_B_completion['event']!='B_native_goal_and_original_finish_complete' or known_B_completion['stage']!='A_FAIL_RECOVER_RESELECT_B':raise ValueError('Exact already-public B-completion receipt required; no private target fields')
        event_time=finite_time(known_B_completion['time'])
        if event_time>anchor+1e-7 or anchor-event_time>.020001:raise ValueError('B completion must be currently observed before candidate planning')
        if tuple(candidate_dx_m)!=(-.02,0.,.02):raise ValueError('Only the three directly registered first-NAV parameter candidates are supported')
        proposals=propose_visual_candidates(latest['rgb'],latest['depth'],latest['K'],latest['mount'])
        choices=[r for r in proposals['candidates'] if r['appearance_family']=='green']
        if len(choices)!=1:raise ValueError('Prospective NAV target appearance is not unique in the latest actual image')
        proof=describe_visible_goal(latest['rgb'],latest['depth'],latest['K'],latest['mount'],frame_local_ref=choices[0]['frame_local_ref'],current_RGB_sha256=proposals['RGB_sha256'],standoff_m=1.05)
        plane=proof['plane'];n=plane['normal_body_xyz'];off=plane['plane_offset_body_m']
        front=np.asarray([*n,off,off/n[0],plane['p90_inlier_residual_m'],plane['inlier_fraction'],1.],np.float32)
        states=np.stack([self.state_encoder(f['raw_state'].copy(),self.mean,self.scale) for f in self.frames])
        states[-1]=self.state_encoder(latest['raw_state'].copy(),self.mean,self.scale,fresh_body=body.copy(),body_age=max(0.,anchor-body_time),rgb_age=max(0.,anchor-latest['time_s']),candidate_front=front.copy())
        if states.shape!=(3,124) or not np.isfinite(states).all():raise ValueError('Frozen124D task-model encoder schema differs')
        past=np.stack([self.action_encoder(f['observed_macro']) for f in list(self.frames)[:-1]])
        future=[];first_dt=float((math.floor(anchor*10+1e-6)+1)/10-anchor)
        if not 0<first_dt<=.100001:raise ValueError('Actual next10Hz image boundary interval unavailable')
        for delta in candidate_dx_m:
            future.append(np.stack([self.action_encoder('NAV_STEP',dx=float(delta),dt=first_dt if i==0 else .1) for i in range(20)]))
        arrays=dict(rgb_context=np.stack([f['rgb'] for f in self.frames]),state_context=states,past_declared_actions=past)
        if arrays['rgb_context'].shape!=(3,64,96,3) or past.shape!=(2,20):raise ValueError('Frozen RGB/past declared-action schema differs')
        return dict(context_arrays=arrays,candidate_declared_actions=np.stack(future),
            provenance=dict(decision_time_s=anchor,rgb_times_s=[f['time_s'] for f in self.frames],body_time_s=body_time,
                observed_macro='PUSH_B',prospective_macro='NAV_STEP',known_B_completion=dict(known_B_completion),candidate_dx_m=list(candidate_dx_m),
                first_prediction_interval_s=first_dt,candidate_geometry_from_actual_RGB_s=latest['time_s'],candidate_geometry_RGB_sha256=proof['RGB_sha256'],
                observed_phase_preserved=True,future_observations_or_motor_outputs_accepted=False,model_called=False,physical_action_dispatched=False))
