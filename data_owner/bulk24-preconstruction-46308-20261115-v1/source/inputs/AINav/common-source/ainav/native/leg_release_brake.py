"""Explicit reverse native leg-release envelope after genuine NN confirmation.

This changes only action postprocessing, not actor weights/input/history or the
original landing/dwell/WBC/stow/geometry gates. It cannot confer stable ownership.
The .7s timing and clamp law come from the selected original SDK, not a scene
route, box ID, absolute trigger time or parameter search.
"""
import hashlib
import inspect
import math
from types import MethodType


def reverse_release_scale(seed_scale,*,now,confirmed_at,ramp_s):
    values=(seed_scale,now,ramp_s) if confirmed_at is None else (seed_scale,now,confirmed_at,ramp_s)
    if not all(math.isfinite(float(x)) for x in values) or not 0<=seed_scale<=1 or ramp_s<=0:
        raise ValueError('Finite native scale/time and positive original ramp required')
    if confirmed_at is None:return float(seed_scale)
    if now<confirmed_at-1e-9:raise ValueError('Genuine confirmation cannot be in future')
    return float(seed_scale)*(1.-min(1.,max(0.,(float(now)-float(confirmed_at))/float(ramp_s))))


class NativeLegReleaseBrake:
    def __init__(self,stop,*,native_blend,ramp_s,native_confirmation,journal):
        from mujoco_zyh.native_push_stop import NativePushLegStop
        if stop.command_legs.__func__ is not NativePushLegStop.command_legs:
            raise ValueError('Original native stop-leg method required')
        if not callable(native_blend) or not callable(native_confirmation) or not callable(journal):raise ValueError('Original blend, genuine confirmation and private journal required')
        self.stop=stop;self.original_command=stop.command_legs
        self.native_blend=native_blend;self.ramp_s=float(ramp_s)
        self.seed_scale=float(stop.scale);self.last_scale=self.seed_scale
        reverse_release_scale(self.seed_scale,now=float(stop.s.data.time),confirmed_at=None,ramp_s=self.ramp_s)
        self.native_confirmation=native_confirmation;self.journal=journal;self.confirmed_at=None;self.policy_proposals=0
        self.original_function=stop.command_legs.__func__
        self.original_source_sha256=hashlib.sha256(inspect.getsource(self.original_function).encode()).hexdigest()
        self.blend_source_sha256=hashlib.sha256(inspect.getsource(native_blend).encode()).hexdigest()
        def command(this):
            self.assert_immutable();now=float(this.s.data.time)
            if now-this.last_policy_time>=.02-1e-8:
                this.scale=self.scale_at(now);self.last_scale=float(this.scale);self.policy_proposals+=1
            return self.original_command()
        self.bound_command=MethodType(command,stop);stop.command_legs=self.bound_command
    def assert_immutable(self):
        if (self.stop.command_legs is not self.bound_command or self.stop.scale!=self.last_scale
                or float(self.stop.s.cfg.push_leg_release_ramp_s)!=self.ramp_s):
            raise RuntimeError('Declared native reverse-release binding changed')
    def confirm(self):
        self.assert_immutable()
        if not self.native_confirmation():raise RuntimeError('Leg release cannot precede genuine native settled confirmation')
        now=float(self.stop.s.data.time)
        if self.confirmed_at is not None:return False
        self.confirmed_at=now
        self.journal(dict(event='original_leg_release_reverse_confirmed',time_s=now,
            seed_scale=self.seed_scale,original_ramp_s=self.ramp_s,model_input=False,
            no_owner_or_task_success_declared=True))
        return True
    def scale_at(self,now):
        expected=reverse_release_scale(self.seed_scale,now=now,confirmed_at=self.confirmed_at,ramp_s=self.ramp_s)
        if self.confirmed_at is None:return expected
        import torch
        age=torch.tensor(max(0.,float(now)-self.confirmed_at),dtype=torch.float64)
        original=self.seed_scale*(1.-float(self.native_blend(age,hold_time=0.,ramp_time=self.ramp_s)))
        if abs(original-expected)>1e-12 or original>self.last_scale+1e-12:
            raise RuntimeError('Original reverse release must match clamp law and never re-release')
        return original
    def receipt(self):
        return dict(schema='ainav-native-reverse-leg-release-v1',seed_scale=self.seed_scale,current_scale=self.last_scale,
            original_ramp_s=self.ramp_s,confirmed_at_s=self.confirmed_at,policy_proposals=self.policy_proposals,
            original_stop_command_source_sha256=self.original_source_sha256,original_blend_source_sha256=self.blend_source_sha256,
            original_actor_input_history_and_native_action_mapping_retained=True,
            original_landing_dwell_WBC_stow_or_safety_gates_changed=False,
            private_only=True,model_input_allowed=False,stable_owner_or_task_success_claimed=False)
