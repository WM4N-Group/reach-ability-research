"""CPU-only no-reset recovery DESIGN/admission mathematics, not a controller.

No Runtime/Machine/actor/physics import or actuator output. Reuse the original
causal initial-contact monitor, backoff measurements, and reference-rate math.
Passing any screen here does NOT authorize a physical command or dispatcher.
"""
import json
import math
from pathlib import Path

from .source_bundle import COMMIT
from initial_contact_progress_monitor import ContactProgressConfig, InitialContactProgressMonitor
from recovery_reference_intersection import axis_interval
from failure_exit_backoff_contract import MeasuredBackoff, BackoffConfig

SCHEMA = 'piper-mujoco-no-reset-recovery-design-v1'
EDGES = {
 'MONITOR_PUSH': ['SOFT_ABORT_LATCH','NATIVE_SUCCESS_SEPARATE','FAIL_CENSOR'],
 'SOFT_ABORT_LATCH': ['UNLOAD_BRAKE','FAIL_CENSOR'],
 'UNLOAD_BRAKE': ['SUPPORT_CAPTURE','FAIL_CENSOR'],
 'SUPPORT_CAPTURE': ['PLAN_STOW','FAIL_CENSOR'],
 'PLAN_STOW': ['SHORT_RETREAT','PROTECTED_STOW','FAIL_CENSOR'],
 'SHORT_RETREAT': ['RECAPTURE_REPLAN','FAIL_CENSOR'],
 'RECAPTURE_REPLAN': ['PROTECTED_STOW','FAIL_CENSOR'],
 'PROTECTED_STOW': ['STOW_VERIFY','FAIL_CENSOR'],
 'STOW_VERIFY': ['NAV_HANDOFF_WARMUP','FAIL_CENSOR'],
 'NAV_HANDOFF_WARMUP': ['NATIVE_NAV_MOVE','FAIL_CENSOR'],
 'NATIVE_NAV_MOVE': ['ARRIVAL_CAPTURE_STOW','FAIL_CENSOR'],
 'ARRIVAL_CAPTURE_STOW': ['FINAL_READY_HOLD','FAIL_CENSOR'],
 'FINAL_READY_HOLD': ['RECOVERED_NAV_READY','FAIL_CENSOR'],
 'RECOVERED_NAV_READY': [], 'NATIVE_SUCCESS_SEPARATE': [], 'FAIL_CENSOR': [],
}
INVARIANTS = {'same_task_world_and_monotonic_physics_clock','no_physical_reset_after_initial','no_qpos_qvel_object_pose_or_velocity_writes','no_actuator_queue_clear_or_delay_rewrite','preserve_failed_A_original_goal_outcome_and_history','no_native_settled_or_success_forgery','no_global_scene_alias_or_pose_exchange','all_actual_strict_limits_and_native_hard_guards_retained','no_new_or_retrained_skills','WM_training_forward_control_zero','same_control_and_RGBD_causal_stream','no_old_completed_root_or_claim_reuse'}
BOUNDARY = dict(contact_window_s=.06,minimum_progress_m=.002,unloaded_force_N=3.,
    support_capture_min_foot_N=12.,capture_hold_s=.2,body_clearance_m=.035,other_clearance_m=.002,
    arm_reference_speed_rad_s=.45,arm_reference_acceleration_rad_s2=1.,
    inner_joint_reference_margin_rad=.01,effort_prediction_reserve=.90,effort_prediction_horizon_s=.04,
    native_arm_effort_hard_ratio=.98,uncaptured_bridge_max_s=.12,unload_brake_max_s=1.,
    stow_stable_s=1.,stow_verify_s=3.,NAV_READY_hold_s=.5,minimum_real_NAV_travel_m=.1,
    minimum_registered_NAV_route_m=.25,minimum_distinct_NAV_observations=3)


def finite(x): return type(x) in (int,float) and math.isfinite(x)


def require(ok,message):
    if not ok: raise ValueError(message)


def validate_design(p):
    require(p.get('schema')==SCHEMA and p.get('status')=='DESIGN_CPU_SCREEN_ONLY_NOT_DISPATCHABLE', 'Design schema/status required')
    for name in ('dispatchable','controller_implemented','physical_dispatch_started','training_authorized'):
        require(p.get(name) is False,'No design-to-execution flag flip: '+name)
    require(p['upstream_commit']==COMMIT,'Pinned native MuJoCo source required')
    require(p['boundaries']==BOUNDARY,'New boundary choices require a separate protocol; never relax frozen margins')
    require(p['state_edges']==EDGES,'Illegal recovery shortcut or success/failure relabel')
    require(set(p['invariants'])==INVARIANTS and all(v is True for v in p['invariants'].values()),'Every no-reset/identity/history invariant is required')
    require(p['current_attempt_failure_only'] is True and p['global_immovability_claim'] is False,'Only this PUSH attempt may be labelled failed')
    require(set(p['states'])==set(EDGES),'Every recovery state must be explicitly specified')
    require(set(p['completion_status'])=={'physics_admission','strict_limit_admission','live_binding','selected_B_authorized'} and all(v is False for v in p['completion_status'].values()),'Design cannot certify live/research/strict admission')
    require(p['new_physics_starts']==0 and p['WM_forwards']==0 and p['WM_control_calls']==0 and p['training_runs']==0,'Design must not consume physical/training budget')
    b=p['proposed_budget_NOT_DISPATCHED']
    require(b==dict(episodes=1,max_sim_seconds=180,max_wall_seconds=900,grace_seconds=10,
        auxiliary_calibration_worlds=1,auxiliary_max_sim_seconds=10.5,max_payload_bytes=128*1024*1024,max_recovery_private_log_bytes=32*1024*1024,max_total_episode_bytes=192*1024*1024,
        reset_after_initial_main_allowed=0,automatic_retry=False,training_runs=0), 'Independent proposed budget required, not old-root reuse')
    return dict(schema=SCHEMA,design_consistent=True,dispatchable=False,actuator_command_authorized=False,
        physics_or_live_measurement_provenance_validated=False)


def new_initial_contact_monitor():
    # Explicit new60ms config, never edits the inherited default80ms or old logs.
    return InitialContactProgressMonitor(ContactProgressConfig(window_s=.06,minimum_forward_progress_m=.002))


def new_backoff_measurement_monitor():
    # Original measured geometry envelope only; not a negative-PUSH-gait policy.
    return MeasuredBackoff(BackoffConfig())


def unchanged_attempt(goal_before,goal_now,episode_before,episode_now,attempt_before,attempt_now):
    require(len(goal_before)==len(goal_now)==3 and all(finite(v) for v in (*goal_before,*goal_now)), 'Actual finite original goal required')
    require(all(isinstance(v,str) and v for v in (episode_before,episode_now,attempt_before,attempt_now)), 'Actual nonempty episode/attempt identities required')
    require(tuple(goal_before)==tuple(goal_now),'Never change A goal to current box pose')
    require(episode_before==episode_now and attempt_before==attempt_now,'No reset/new-attempt/history relabel inside recovery')
    return True


def entry_screen(*,hard_flags,strict_limits_ok,strict_speed_ok,substep_guard_coverage,
        measured_reference_epoch,committed_queue_screen_pass,foot_normal_N):
    checks=(strict_limits_ok,strict_speed_ok,substep_guard_coverage,measured_reference_epoch,committed_queue_screen_pass)
    require(all(type(v) is bool for v in checks),'Explicit measured admission booleans required')
    require(isinstance(hard_flags,(tuple,list)) and all(isinstance(x,str) and x for x in hard_flags),'Exact native hard flags required')
    require(len(foot_normal_N)==4 and all(finite(v) for v in foot_normal_N),'Four actual normal loads required')
    ok=not hard_flags and all(checks) and min(foot_normal_N)>0.
    return dict(screen_pass=ok,intent='future_bounded_unload_adapter_only' if ok else 'STOP_AND_CENSOR',
        retraction_authorized=False,NAV_authorized=False,actuator_command_authorized=False,
        actual_supported_capture_pass=min(foot_normal_N)>=12.,
        actual_motor_or_contact_dynamics_validated=False)


def supported_unloaded_screen(*,legal_hand_contact,selected_hand_force_N,all_candidate_hand_force_N,
        box_linear_speed,box_angular_speed,base_linear_speed,base_angular_speed,tilt_rad,
        foot_normal_N,contact_point_slip_m_s,strict_limits_ok,strict_speed_ok,native_all_candidate_contact_ok):
    require(type(legal_hand_contact) is bool and type(strict_limits_ok) is bool and type(strict_speed_ok) is bool and type(native_all_candidate_contact_ok) is bool,'Explicit real gates required')
    values=(selected_hand_force_N,all_candidate_hand_force_N,box_linear_speed,box_angular_speed,
        base_linear_speed,base_angular_speed,tilt_rad,*foot_normal_N,*contact_point_slip_m_s)
    require(len(foot_normal_N)==len(contact_point_slip_m_s)==4 and all(finite(v) and v>=0 for v in values),'Finite actual nonnegative force/speed fields required')
    return (not legal_hand_contact and selected_hand_force_N<3. and all_candidate_hand_force_N<3.
        and box_linear_speed<.02 and box_angular_speed<.1 and base_linear_speed<.02
        and base_angular_speed<.1 and tilt_rad<.1 and min(foot_normal_N)>=12.
        and max(contact_point_slip_m_s)<.03 and strict_limits_ok and strict_speed_ok and native_all_candidate_contact_ok)


def motor_aware_axis_interval(*,feedforward,target_velocity,delay_s,**actual):
    """Fold-only reference candidate: original rate/accel + actual motor semantics.

    Native tau=Kp*(target-q)+Kd*(target_velocity-dq)+feedforward. Keep actual q/dq
    unchanged; shift ONLY the algebraic effort interval. Forecast includes delay
    and the original40ms horizon. Constant measured velocity is a screening
    assumption, NOT proof of contact/geometry/dynamic safety.
    """
    require(all(finite(v) for v in (feedforward,target_velocity,delay_s)) and 0<=delay_s<=.0200001,'Actual native FF/velocity/latency required')
    required={'reference','reference_velocity','measured_q','measured_dq','kp','kd','effort_limit','soft_lower','soft_upper','dt'}
    require(set(actual)==required and all(finite(v) for v in actual.values()),'Exact finite actual reference/measurement/gain fields required')
    require('soft_lower' in actual and 'soft_upper' in actual and actual['soft_upper']-actual['soft_lower']>.02,'Nonempty original inner joint domain required')
    require(finite(actual['dt']) and .0049999<=actual['dt']<=.020001,'Actual5ms or20ms reference interval required')
    require(abs(actual['reference_velocity'])<=.45,'Do not zero/clip actual issued derivative into the fold domain')
    kwargs=dict(actual,soft_lower=actual['soft_lower']+.01,soft_upper=actual['soft_upper']-.01,
        speed_limit=.45,acceleration_limit=1.,horizon=.04+delay_s,reserve=.90)
    old=axis_interval(**kwargs)
    shift=-(actual['kd']*target_velocity+feedforward)/actual['kp']
    force=[v+shift for v in old['effort_interval']]
    lower=max(old['rate_interval'][0],force[0],old['soft_interval'][0])
    upper=min(old['rate_interval'][1],force[1],old['soft_interval'][1])
    actual_inside=actual['soft_lower']<=actual['measured_q']<=actual['soft_upper']
    forecast_q=actual['measured_q']+(.04+delay_s)*actual['measured_dq']
    forecast_inside=actual['soft_lower']<=forecast_q<=actual['soft_upper']
    return dict(feasible=bool(actual_inside and forecast_inside and lower<=upper),lower=lower,upper=upper,
        effort_interval=force,rate_interval=old['rate_interval'],inner_reference_interval=old['soft_interval'],
        feedforward_and_target_velocity_accounted=True,actual_q_dq_not_modified=True,
        geometry_contact_queue_or_physics_certified=False,actuator_command_authorized=False)


def committed_queue_screen(*,queue,delay_steps,q,dq,effort,physics_dt=.005):
    """Read only all already-committed native5x18 commands. Never clear the lag.

    Future new command cannot affect the existing prefix. For each joint j with
    lag L, the next L effective commands are queue[-L:] along that axis.
    """
    require(physics_dt==.005 and len(queue)==5 and len(delay_steps)==len(q)==len(dq)==len(effort)==18,'Exact actual native5-command/18-axis queue required')
    require(all(type(v) is int and 0<=v<=4 for v in delay_steps),'Actual per-axis delay0..4 required')
    require(all(finite(v) for v in (*q,*dq,*effort)) and min(effort)>0,'Actual finite measured state/limits required')
    for command in queue:
        require(len(command)==5 and all(len(row)==18 and all(finite(v) for v in row) for row in command),'Finite position/velocity/Kp/Kd/FF queue required')
        require(all(v>=0 for row in command[2:4] for v in row),'Invalid actual motor gains')
    failures=[];checked=0
    for j,lag in enumerate(delay_steps):
        for k in range(lag):
            cmd=queue[len(queue)-lag+k];predicted_q=q[j]+dq[j]*k*physics_dt
            raw=cmd[2][j]*(cmd[0][j]-predicted_q)+cmd[3][j]*(cmd[1][j]-dq[j])+cmd[4][j]
            checked+=1
            if abs(raw)>.90*effort[j]:failures.append(dict(joint_slot=j,prefix_step=k,raw_torque=raw,effort_limit=effort[j]))
    return dict(screen_pass=not failures,failures=failures,immutable_prefix_axis_samples=checked,
        queue_or_delay_modified=False,constant_velocity_screen_only=True,actual_dynamic_safety_certified=False,
        actuator_command_authorized=False)


def main():
    p=json.loads(Path(__file__).with_name('no_reset_recovery_protocol_v1.json').read_text())
    print(json.dumps(validate_design(p),indent=2))


if __name__=='__main__':main()
