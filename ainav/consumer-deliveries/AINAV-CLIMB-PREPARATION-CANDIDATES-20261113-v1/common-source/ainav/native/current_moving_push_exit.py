"""Native WBC moving-PUSH brake before the original stationary protected stow.

The failed v1 attempted stationary stow at0.366m/s with two feet unloaded. This
adds the native Finish leg landing/braking portion first, while retaining actual
arm unloading, original target/history, immutable delay queue and hard guards.
It never calls Finish's goal-success path or changes a goal to current position.
"""
from collections import deque
from dataclasses import replace
import numpy as np
from .stall_stow import ProtectedStow, unload_reference, history_sha
from .recovery_design import committed_queue_screen

MODE = 'native-WBC-moving-brake-before-protected-stow-v1'


def stationary_brake_capture(metrics):
    return bool(metrics['base_linear_speed'] < .02 and metrics['base_angular_speed'] < .1
        and metrics['tilt_rad'] < .1 and min(metrics['foot_normal_N']) >= 12
        and metrics['max_foot_speed'] < .03 and metrics['hand_force_N'] < 3
        and not metrics['legal_hand_contact'] and metrics['arm_speed'] < .12)


def native_brake_leg_mix(old, q, dq, torque, cfg, takeover):
    """Native Finish takeover, generalized to the ACTUALLY issued old gains/FF."""
    if not 0<=takeover<=1 or any(np.shape(v)!=(12,) or not np.isfinite(v).all() for v in (q,dq,torque)):
        raise ValueError('Finite actual leg state and native WBC torque required')
    kp=(1-takeover)*old.kp[:12]+takeover*cfg.motor_kp
    kd=(1-takeover)*old.kd[:12]+takeover*cfg.motor_kd
    ff=(1-takeover)*(old.kp[:12]*(old.position[:12]-q)+old.kd[:12]*old.velocity[:12]+old.feedforward[:12])+takeover*(torque+cfg.motor_kd*dq)
    return kp,kd,ff


class MovingPushExit:
    def __init__(self, runtime, last_two, *, compact_goal, hold_issued_arm=False, leg_stop_seed=None, nn_handoff=False, nn_handoff_dwell_s=.1, retirement_reason='voluntary_early_exit'):
        if retirement_reason not in ('voluntary_early_exit','native_contact_progress_failure'):
            raise ValueError('Explicit actual PUSH retirement reason required')
        self.retirement_reason=retirement_reason
        self.nn_handoff=nn_handoff
        self.nn_handoff_dwell_s=nn_handoff_dwell_s
        self.hold_issued_arm=hold_issued_arm
        self.r, self.s = runtime, runtime.sim
        self.pm = runtime.push['model']
        self.compact_goal = np.array(compact_goal, copy=True)
        if self.compact_goal.shape!=(6,) or not np.isfinite(self.compact_goal).all():
            raise ValueError('Explicit finite original compact target required')
        self.old = runtime.last
        self.exit_origin = self.s.data.qpos[:3].copy()
        self.leg_stop = None
        self.leg_landed_since = None
        self.leg_stop_completed = False
        self.wbc_started = None
        if leg_stop_seed is not None:
            from .native_push_stop import NativePushLegStop
            self.leg_stop = NativePushLegStop(runtime, leg_stop_seed)
        s = self.s
        self.seed = committed_queue_screen(queue=[x.tolist() for x in s.queue],delay_steps=[int(x) for x in s.delays],
            q=s.data.qpos[s.qids].tolist(),dq=s.data.qvel[s.dids].tolist(),effort=self.pm.EFFORT.tolist())
        if not self.seed['screen_pass']:
            raise RuntimeError('moving_exit_immutable_pending_queue_refused')
        self.original_goal = s.box_push_target.numpy().copy()
        self.retired_history_sha = history_sha(s)
        finish = runtime.push['finish']
        # Original landing/braking QP config, with no goal-success or arm-retract path.
        self.native = finish.FinishController(s,replace(finish.FinishConfig(),arm_pose=tuple(self.compact_goal),deadline=60.))
        self.native.entry_position = self.old.position[:12].copy()
        self.reference_start = self.old.position[12:].copy()
        self.reference = self.reference_start.copy()
        self.velocity = (last_two[-1][12:]-last_two[-2][12:])/.005
        if np.max(abs(self.velocity)) > .45:
            raise RuntimeError('moving_exit_actual_reference_seed_too_fast')
        self.unload_target = s.data.qpos[s.qids[12:]].copy()
        self.limits = np.column_stack((np.maximum(s.model.jnt_range[s.jids[12:],0],s.soft_limits[12:,0]),
                                      np.minimum(s.model.jnt_range[s.jids[12:],1],s.soft_limits[12:,1])))
        self.last_two = deque([x.copy() for x in last_two],maxlen=2)
        self.started = float(s.data.time)
        self.captured_since = None
        self.last_command_time = -np.inf
        self.stow = None
        self.metrics = self.measure()
        self.initial_metrics = dict(self.metrics)
        self.events = [dict(time=self.started,event='actual_moving_PUSH_retired_native_brake_started',metrics=self.metrics)]

    @property
    def phase(self):
        return self.stow.phase if self.stow is not None else ('NN_STOP_MOVING_PUSH' if self.leg_stop and not self.leg_stop_completed else 'BRAKE_MOVING_PUSH')

    @property
    def complete(self):
        return self.stow is not None and self.stow.complete

    def measure(self):
        metrics=ProtectedStow.measure(self)
        metrics.update(base_retreat_m=float(self.exit_origin[0]-self.s.data.qpos[0]),
            base_horizontal_displacement_m=float(np.linalg.norm(self.s.data.qpos[:2]-self.exit_origin[:2])))
        if self.nn_handoff:
            import mujoco
            s=self.s;loaded=np.asarray(metrics['foot_normal_N'])>=12
            points=(s.data.xpos[s.feet_ids]-s.data.qpos[:3])@s.data.xmat[s.base_id].reshape(3,3)
            speeds=[]
            for bid,active in zip(s.feet_ids,loaded):
                if not active:continue
                jac=np.zeros((3,s.model.nv));mujoco.mj_jacBody(s.model,s.data,jac,None,int(bid))
                speeds.append(float(np.linalg.norm((jac@s.data.qvel)[:2])))
            spans=np.ptp(points[loaded,:2],axis=0) if loaded.sum()>=2 else np.zeros(2)
            metrics.update(brake_loaded_feet_max_speed=max(speeds,default=1e9),
                brake_loaded_feet_span_body_x_m=float(spans[0]),brake_loaded_feet_span_body_y_m=float(spans[1]))
        return metrics

    def update(self):
        if self.stow is not None:
            self.stow.update()
            if np.linalg.norm(self.s.data.qpos[:2]-self.exit_origin[:2])>.18:
                raise RuntimeError('moving_exit_original_total_displacement_envelope_exceeded')
            return
        s = self.s;now = float(s.data.time)
        if history_sha(s) != self.retired_history_sha or not np.array_equal(s.box_push_target.numpy(),self.original_goal):
            raise RuntimeError('moving_exit_original_goal_or_retired_history_changed')
        if now-self.started > 10.:
            raise RuntimeError('moving_exit_native_brake_timeout')
        self.metrics = self.measure()
        if self.metrics['base_horizontal_displacement_m'] > .18:
            raise RuntimeError('moving_exit_original_displacement_envelope_exceeded')
        reason = self.native.guard.check(s.data.qpos[s.qids[12:]],allow_hand_contact=True,record=True)
        if reason:
            raise RuntimeError('moving_exit_native_actual_collision:' + reason)
        if self.leg_stop is not None and not self.leg_stop_completed:
            from .native_push_stop import nn_landing_capture,nn_wbc_handoff_capture
            landed=(nn_wbc_handoff_capture if self.nn_handoff else nn_landing_capture)(self.metrics)
            self.leg_landed_since=(self.leg_landed_since if self.leg_landed_since is not None else now) if landed else None
            if self.leg_landed_since is not None and now-self.leg_landed_since>=(self.nn_handoff_dwell_s if self.nn_handoff else .1)-1e-8:
                self.leg_stop_completed=True;self.wbc_started=now;self.old=self.r.last
                finish=self.r.push['finish']
                self.native=finish.FinishController(s,replace(finish.FinishConfig(),arm_pose=tuple(self.compact_goal),deadline=60.))
                self.native.entry_position=self.old.position[:12].copy()
                self.events.append(dict(time=now,event='actual_original_PUSH_zero_command_slow_supported_WBC_landing_started' if self.nn_handoff else 'actual_original_PUSH_zero_command_landed_before_WBC',metrics=self.metrics,
                    seed_observation_time_s=self.leg_stop.seed_time,seed_actual_issue_time_s=self.leg_stop.seed_issued_time,
                    stop_actor_forwards=self.leg_stop.forwards,actual_native_release_scale_held=self.leg_stop.scale))
            else:return
        stable = stationary_brake_capture(self.metrics)
        self.captured_since = (self.captured_since if self.captured_since is not None else now) if stable else None
        if now-self.started >= .5 and self.captured_since is not None and now-self.captured_since >= .1-1e-8:
            self.events.append(dict(time=now,event='actual_loaded_stationary_brake_capture',metrics=self.metrics))
            # The original .15m/s stationary-stow envelope remains unchanged.
            self.stow = ProtectedStow(self.r,list(self.last_two),compact_goal=self.compact_goal,
                                     unload_initial_ff=self.r.last.feedforward[12:].copy())

    def command(self):
        if self.stow is not None:
            return self.stow.command()
        self.update()
        if self.stow is not None:
            return self.stow.command()
        s = self.s;n = self.native;cfg=n.config;now=float(s.data.time);age=now-self.started
        gravity=s.robot.get_gravity_compensation_forces().numpy()[0]
        gravity=gravity[[s.robot.joint_names.index(f'joint{i}') for i in range(1,7)]]
        if now-self.last_command_time >= .005-1e-8:
            self.last_command_time = now
            if self.hold_issued_arm:
                from .moving_arm_reference import brake_arm_hold
                self.reference,self.velocity,self.ff,receipts=brake_arm_hold(self.reference_start,
                    self.reference,self.velocity,s.data.qpos[s.qids[12:]],s.data.qvel[s.dids[12:]],
                    self.pm.KP[12:],self.pm.KD[12:],self.r.last.feedforward[12:],self.pm.EFFORT[12:],self.limits)
                self.last_arm_receipts=receipts
            else:
                self.reference,self.velocity,self.ff,_ = unload_reference(self.unload_target,self.reference_start,
                    self.reference,self.velocity,s.data.qpos[s.qids[12:]],s.data.qvel[s.dids[12:]],
                    self.pm.KP[12:],self.pm.KD[12:],gravity,self.pm.EFFORT[12:],self.limits,age,
                    start_ff=self.old.feedforward[12:].copy())
        reason=n.guard.check(self.reference,allow_hand_contact=True)
        if reason:
            raise RuntimeError('moving_exit_unload_reference_collision:' + reason)
        warning=n.guard.check(s.data.qpos[s.qids[12:]]+.1*s.data.qvel[s.dids[12:]],allow_hand_contact=True,joint_limits=False)
        if warning:
            raise RuntimeError('moving_exit_actual_velocity_geometry_forecast:' + warning)
        if self.leg_stop is not None and not self.leg_stop_completed:
            return self.r.Command(np.r_[self.leg_stop.command_legs(),self.reference],np.zeros(18),
                self.pm.KP.copy(),self.pm.KD.copy(),np.r_[np.zeros(12),self.ff])
        if self.wbc_started is not None:age=now-self.wbc_started
        # Exact native Finish stance interpolation and all-four-feet landing QP.
        fraction=np.clip((age-cfg.stance_delay)/cfg.stance_seconds,0.,1.)
        blend=fraction*fraction*(3.-2.*fraction)
        posture=(1-blend)*n.entry_posture+blend*n.stand_posture
        com=(1-blend)*n.entry_com+blend*n.stand_com
        command=self.r.Command(np.r_[posture,self.reference],np.zeros(18),self.pm.KP.copy(),self.pm.KD.copy(),np.r_[np.zeros(12),self.ff])
        torque,*_=n.qp.solve(np.ones(4,dtype=bool),n.anchors,np.zeros((4,3)),np.zeros((4,3)),com,n.yaw,posture,command)
        takeover=np.clip(age/cfg.blend_seconds,0.,1.);takeover=takeover*takeover*(3.-2.*takeover)
        q=s.data.qpos[s.qids[:12]];dq=s.data.qvel[s.dids[:12]]
        command.position[:12]=q
        command.kp[:12],command.kd[:12],command.feedforward[:12]=native_brake_leg_mix(self.old,q,dq,torque,cfg,takeover)
        return command

    def after_step(self):
        self.last_two.append(self.r.last.position.copy())
        if self.stow is not None:
            self.stow.after_step()
            if np.linalg.norm(self.s.data.qpos[:2]-self.exit_origin[:2])>.18:
                raise RuntimeError('moving_exit_original_total_displacement_envelope_exceeded')
        else:
            self.update()

    def report(self):
        stow = self.stow.report() if self.stow is not None else None
        if stow is not None:
            stow=dict(stow,native_PUSH_attempt_failed=self.retirement_reason=='native_contact_progress_failure',retirement_reason=self.retirement_reason)
        return dict(mode=(('native-PUSH-leg-zero-command-WBC-capture-v6' if self.nn_handoff_dwell_s==0 else 'native-PUSH-leg-zero-command-WBC-landing-v5') if self.nn_handoff else 'native-PUSH-leg-zero-command-stop-v4') if self.leg_stop else MODE,phase=self.phase,
            independent_stop_observation_history=self.leg_stop is not None,pre_WBC_handoff_dwell_s=self.nn_handoff_dwell_s if self.nn_handoff else .1,stop_actor_forwards=self.leg_stop.forwards if self.leg_stop else 0,
            zero_requested_velocity_only=True if self.leg_stop else None,hold_actual_issued_arm_until_stationary=self.hold_issued_arm,stow_verified=self.complete,brake_events=self.events,
            initial_metrics=self.initial_metrics,metrics=self.stow.metrics if self.stow is not None else self.metrics,protected_stow=stow,
            original_goal_preserved=np.array_equal(self.s.box_push_target.numpy(),self.original_goal),
            retired_PUSH_history_preserved=history_sha(self.s)==self.retired_history_sha,
            original_stationary_stow_speed_limit_m_s=.15,moving_brake_timeout_s=10.,
            measured_foot_load_gate_N=12.,native_QP_residual=self.native.qp.maximum_residual,
            original_PUSH_goal_success_inferred=False,retirement_reason=self.retirement_reason,
            total_displacement_from_exit_origin_m=float(np.linalg.norm(self.s.data.qpos[:2]-self.exit_origin[:2])),
            voluntary_exit_is_not_a_stall_diagnosis=self.retirement_reason=='voluntary_early_exit')
