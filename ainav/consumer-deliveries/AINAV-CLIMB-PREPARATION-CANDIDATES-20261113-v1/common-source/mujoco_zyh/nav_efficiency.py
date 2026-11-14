"""Opt-in engineering NAV adapter; frozen WBC actors/native arrival gates unchanged.

This is NOT source-native high-level navigation. It uses supported body vx/vy
commands to traverse the same map waypoints without facing each segment. Motor
state, delay queue and actor history are never reset. One wrist damping change
is explicit, private telemetry reports every native stability gate at 200Hz.
"""
import math
import numpy as np

MODE='postpush_body_xy_native_minimums_wrist_damping_v2'
# Body command envelope is no larger than the native skills NAV profile.
SPEED_LIMITS=np.array([.5,.4,.9])
MIN_SPEEDS=np.array([.4,.4,.8])


class EfficientNav:
    def __init__(self,native):
        self.native=native;self.config=native.config
        self.command=np.zeros(3);self.last_time=None
        self.position_latched=False;self.yaw_latched=False
        self.gate_failures={};self.observe_count=0;self.last_checks={}
        self.reacquisitions=0;self.last_state=None

    @property
    def arrived(self):return self.native.arrived
    @property
    def distance(self):return self.native.distance
    @property
    def yaw_error(self):return self.native.yaw_error

    def update(self,state):
        if not np.isfinite(np.r_[state.time,state.xy,state.yaw,state.velocity,state.arm_q,state.arm_qd,state.tilt]).all():
            raise ValueError('NAV actual state nonfinite')
        dt=.02 if self.last_time is None else state.time-self.last_time
        if self.last_time is not None and abs(dt-.02)>1e-6:
            raise ValueError('NAV control clock gap; no replay or fabricated warmup')
        self.last_time=state.time
        if state.time>getattr(self,'maximum_seconds',15.):
            raise RuntimeError(f"nav_efficiency_{getattr(self,'maximum_seconds',15.):g}s_censor:"+str(self.last_checks))
        cfg=self.config;delta=self.native.goal-state.xy
        distance=float(np.linalg.norm(delta));yaw_error=(self.native.goal_yaw-state.yaw+math.pi)%(2*math.pi)-math.pi
        if distance>cfg.position_tolerance:
            if self.position_latched:self.reacquisitions+=1
            self.position_latched=False
        elif distance<=cfg.position_tolerance*cfg.position_stop_ratio:self.position_latched=True
        if self.reacquisitions>getattr(self,'maximum_reacquisitions',2):raise RuntimeError('nav_repeated_goal_reacquisition_censor')
        if abs(yaw_error)>cfg.yaw_tolerance:self.yaw_latched=False
        elif abs(yaw_error)<=cfg.yaw_tolerance*cfg.yaw_stop_ratio:self.yaw_latched=True
        desired=np.zeros(3)
        if state.time>=cfg.warmup_seconds:
            c,s=math.cos(state.yaw),math.sin(state.yaw)
            body_delta=np.array([c*delta[0]+s*delta[1],-s*delta[0]+c*delta[1]])
            if not self.position_latched:
                # v1 measured .2-.3m/s requests did not move this frozen WBC
                # reliably. Keep the source-tested nonzero command floor.
                for axis in (0,1):
                    if abs(body_delta[axis])>cfg.position_command_deadband:
                        desired[axis]=math.copysign(max(MIN_SPEEDS[axis],2.*abs(body_delta[axis])),body_delta[axis])
            if not self.yaw_latched:
                desired[2]=math.copysign(max(MIN_SPEEDS[2],2.*abs(yaw_error)),yaw_error)
        desired=np.clip(desired,-SPEED_LIMITS,SPEED_LIMITS)
        # The source skills profile has command_slew=False and brakes by an
        # immediate ZERO REQUEST (never by changing actual velocity/state).
        self.command=desired.copy()
        self.native.position_reached=self.position_latched;self.native.yaw_reached=self.yaw_latched
        self.native.phase='settle' if self.position_latched and self.yaw_latched and np.all(self.command==0.) else 'drive'
        self.last_state=state;self.observe(state)
        return self.command.copy()

    def observe(self,state):
        # Original predicate and original 1s continuously checked hold, at every
        # native physics step. Never infer arrival just from position or timeout.
        self.native.observe(state)
        checks=self.native.stability_checks(state)
        for name,ok in checks.items():self.gate_failures[name]=self.gate_failures.get(name,0)+int(not ok)
        self.observe_count+=1;self.last_checks=checks

    def diagnostics(self):
        return dict(method=MODE,internal_phase=self.native.phase,goal_xy=self.native.goal.tolist(),
            goal_yaw_rad=self.native.goal_yaw,requested_body_velocity=self.command.tolist(),
            distance_m=self.distance,yaw_error_rad=self.yaw_error,
            actual_hold_s=self.native.hold_elapsed,last_checks=self.last_checks.copy(),
            gate_fail_observations=self.gate_failures.copy(),observe_count=self.observe_count,
            position_reacquisitions=self.reacquisitions)


def install(runtime,tasks,config):
    mode=config.get('nav_efficiency_mode')
    if mode is None:return tasks
    if mode!=MODE:raise ValueError('Unregistered NAV adaptation')
    # This first engineering admission keeps scene/path geometry unchanged.
    if config['scenario']!='nav-push-climb' or config['scene_recipe']!='zyh_native_single_box':
        raise ValueError('NAV adapter not admitted to research/failure recovery')
    tasks=[dict(t) for t in tasks]
    expected=[[-.02,-2.],[-.4,-2.],[-.4,0.],[-.08,0.]]
    if [t['goal'] for t in tasks if t['skill']=='nav']!=expected:
        raise ValueError('Native map route changed since admission')
    for t in tasks:
        if t['skill']=='nav':t['yaw']=0.  # change task orientation, NOT a safety tolerance
    original_make=runtime.make_nav
    runtime.wm_efficient_nav_active=False
    def make(item):
        native=original_make(item)
        runtime.wm_efficient_nav_active=item['goal']!=[-.02,-2.]
        return EfficientNav(native) if runtime.wm_efficient_nav_active else native
    runtime.make_nav=make
    original_command=runtime.nav_command
    def command():
        native=original_command()
        kd=native.kd.copy()
        if runtime.wm_efficient_nav_active:kd[16]=2.5  # joint5: native isaac-profile damping, not new weight/force limit
        return runtime.Command(native.position.copy(),native.velocity.copy(),native.kp.copy(),kd,native.feedforward.copy())
    runtime.nav_command=command
    runtime.wm_nav_efficiency=dict(method=MODE,source_native_high_level_or_NAV_motor_gains=False,
        actors_modified=False,source_bundle_modified=False,physical_state_or_queue_reset=False,
        route_geometry_changed=False,all_NAV_goals_final_yaw_zero=True,
        original_arrival_predicates_and_1s_hold_unchanged=True,
        body_velocity_limits=SPEED_LIMITS.tolist(),nonzero_command_minimums=MIN_SPEEDS.tolist(),
        native_command_slew_false_and_zero_request_braking=True,
        original_initial_NAV_and_PUSH_prefix_unmodified=True,
        only_postpush_NAV_arm_joint5_kd_old=1.,only_postpush_NAV_arm_joint5_kd_new=2.5,
        native_NAV_other_gains_unchanged=True,native_PUSH_CLIMB_and_collision_guards_unchanged=True,
        max_single_NAV_s=15.,max_position_reacquisitions=2,
        warning='Command-envelope compliance/CPU tests do not certify frozen actor performance or strict physical safety')
    return tasks
