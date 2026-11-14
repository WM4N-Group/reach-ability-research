"""Single Isaac NAV-to-PUSH handoff diagnostic on one continuous physics scene."""

import argparse
import hashlib
import json
import math
from pathlib import Path
import runpy
import traceback

from isaaclab.app import AppLauncher


parser = argparse.ArgumentParser()
parser.add_argument("--nav-actor", type=Path, required=True)
parser.add_argument("--push-checkpoint", type=Path, required=True)
parser.add_argument("--isaac-repo", type=Path, required=True)
parser.add_argument("--output-json", type=Path, required=True)
parser.add_argument("--video-path", type=Path,
                    help="Record the rendered NAV-to-PUSH episode at half the control rate.")
parser.add_argument("--seed", type=int, default=4901)
parser.add_argument("--box-nominal-y-m", type=float, choices=(-0.12, 0.0, 0.12),
                    help="Read-only cohort layout stratum: nominal box y before the original reset jitter.")
parser.add_argument("--nav-start-x", type=float, default=-0.25)
parser.add_argument("--nav-goal-x", type=float, default=0.0)
parser.add_argument("--nav-min-translation-speed", type=float, default=0.0)
parser.add_argument("--nav-timeout-s", type=float, default=5.0)
parser.add_argument("--handoff-settle-stable-s", type=float, default=0.0,
                    help="Require this continuous stable NAV hold after arrival before PUSH.")
parser.add_argument("--handoff-settle-timeout-s", type=float, default=3.0,
                    help="Maximum additional NAV hold time after arrival.")
parser.add_argument("--handoff-settle-control", choices=("nav_zero_velocity", "default_posture", "hold_last_nav"),
                    default="nav_zero_velocity", help="Controller used during the stable handoff phase.")
parser.add_argument("--force-push-after-settle-timeout", action="store_true",
                    help="Known-state diagnostic: enter PUSH after the full NAV zero-velocity hold even if the stable gate fails.")
parser.add_argument("--nav-leg-support-until-ready", action="store_true",
                    help="Derived diagnostic: route NAV actor leg targets during PUSH safe approach until motion_ready.")
parser.add_argument("--skip-nav", action="store_true", help="Matched router baseline from a reset PUSH start.")
parser.add_argument("--nav-arm-home", action="store_true", help="Hold the initial safe arm posture with the ordinary joint actuators during NAV.")
parser.add_argument("--pre-ready-leg-action-cap", type=float, default=0.0,
                    help="Derived diagnostic: maximum absolute leg action command before motion_ready.")
parser.add_argument("--pre-ready-leg-ramp-s", type=float, default=1.0,
                    help="Derived diagnostic: time to ramp pre-ready leg commands to their capped value.")
parser.add_argument("--hold-push-arm-at-handoff", action="store_true",
                    help="Derived diagnostic: hold the measured arm joint pose from NAV handoff during PUSH.")
parser.add_argument("--hold-arm-on-support-warning", action="store_true",
                    help="Diagnostic: latch the current arm reference after five low-base/rear-unloaded steps.")
parser.add_argument("--record-push-support-trace", action="store_true",
                    help="Record read-only per-step robot COM, foot-body position, force, pose and joint telemetry.")
parser.add_argument("--record-settle-support-trace", action="store_true",
                    help="Record the same support telemetry during the NAV-to-PUSH preparation phase.")
parser.add_argument("--record-push-contact-load-trace", action="store_true",
                    help="Add four filtered ground-contact point sensors and explicit actuator torque telemetry.")
parser.add_argument("--record-leg-jacobian-trace", action="store_true",
                    help="Record read-only per-leg foot position Jacobian and joint tracking authority during PUSH.")
parser.add_argument("--record-base-contact-source", action="store_true",
                    help="Record read-only base contact force against ground and box during PUSH.")
parser.add_argument("--record-base-contact-substeps", action="store_true",
                    help="Record read-only base force and sensor history after every PUSH physics substep.")
parser.add_argument("--record-base-contact-manifold", action="store_true",
                    help="Add read-only per-point base-ground/box contact data to the substep trace.")
parser.add_argument("--record-recovery-decision-state", action="store_true",
                    help="Record read-only physical, controller and actor state at each PUSH decision step.")
parser.add_argument("--record-scene-runtime-observation", action="store_true",
                    help="Record same-run USD and PhysX observations; this is not a scene certificate.")
parser.add_argument("--record-invalid-hand-contact-detail", action="store_true",
                    help="Record read-only contact geometry when invalid_hand_contact terminates PUSH.")
parser.add_argument("--record-hand-contact-substeps", action="store_true",
                    help="Record the original hand sensor and box/hand geometry after each PUSH physics substep.")
parser.add_argument("--record-hand-contact-manifold", action="store_true",
                    help="Add read-only PhysX hand-box contact points to each hand substep sample.")
parser.add_argument("--record-push-clock-trace", action="store_true",
                    help="Record PUSH target write and post-physics joint state at every substep.")
parser.add_argument("--record-push-actuator-clock", action="store_true",
                    help="Also record per-substep leg delay and actuator torques after target write.")
parser.add_argument("--record-push-arm-clock", action="store_true",
                    help="Also record the six independent arm actuator delay buffers with the torque clock.")
parser.add_argument("--push-action-pulse-step", type=int,
                    help="PUSH control step for one paired leg-action pulse; requires clock tracing.")
parser.add_argument("--push-action-pulse-index", type=int, default=0,
                    help="Index in the 12-dimensional PUSH leg action for the pulse.")
parser.add_argument("--push-action-pulse-delta", type=float, default=0.0,
                    help="Signed actor action pulse, limited to 0.05.")
parser.add_argument("--push-arm-command-pulse-step", type=int,
                    help="PUSH control step for a one-step downstream arm joint command probe.")
parser.add_argument("--push-arm-command-pulse-joint", choices=tuple(f"joint{i}" for i in range(1, 7)),
                    default="joint3", help="Arm joint whose routed position target receives the probe.")
parser.add_argument("--push-arm-command-pulse-rad", type=float, default=0.0,
                    help="Signed one-step arm target increment in radians, limited to 0.01.")
parser.add_argument("--support-response-probe", choices=("front-up", "front-down", "rear-up", "rear-down"),
                    help="Known-state signed 3-mm foot-target pulse after the frozen support trigger.")
parser.add_argument("--record-support-response-velocity", action="store_true",
                    help="Add read-only instantaneous base velocity to a support response probe.")
parser.add_argument("--rear-support-feedback", action="store_true",
                    help="Derived known-state pilot: bounded rear-foot unloading feedback before motion_ready.")
parser.add_argument("--front-foot-probe-offset-m", type=float, choices=(-0.005, 0.0, 0.005), default=0.0,
                    help="Known-state 4.40-4.80 s front-foot vertical response probe; sign is world foot z.")
parser.add_argument("--front-foot-hold-offset-m", type=float, choices=(-0.005, 0.0), default=0.0,
                    help="Known-state 4.40-6.20 s front-foot downward hold pilot; not a feedback controller.")
parser.add_argument("--front-foot-feedback", action="store_true",
                    help="Known-state bounded front-foot response to pitch, angular velocity and rear load.")
parser.add_argument("--probe-ground-prims", action="store_true",
                    help="List collision prims below /World/ground and exit without policy rollout.")
parser.add_argument("--ground-filter-prim", default="/World/ground/terrain/GroundPlane/CollisionPlane",
                    help="Exact collision prim path for the four filtered contact sensors.")
parser.add_argument("--support-margin-pause-m", type=float, default=0.0,
                    help="Diagnostic arm-reference pause below this contact-mean geometry margin.")
parser.add_argument("--support-margin-resume-m", type=float, default=0.0,
                    help="Resume arm-reference advance above this contact-mean geometry margin.")
parser.add_argument("--safe-approach-arm-rate-scale", type=float, default=1.0,
                    help="Derived diagnostic: scale arm-reference increments before safe approach completes.")
AppLauncher.add_app_launcher_args(parser)
args = parser.parse_args()
if args.output_json.exists():
    parser.error("Output file already exists")
if args.video_path is not None:
    if args.video_path.exists():
        parser.error("Video file already exists")
    args.enable_cameras = True
if (not args.skip_nav and not -0.5 <= args.nav_start_x < -0.1) or not -0.1 <= args.nav_goal_x <= 0.0 or not 0.0 < args.nav_timeout_s <= 10.0:
    parser.error("Invalid NAV start or timeout")
if not 0.0 <= args.nav_min_translation_speed <= 0.15:
    parser.error("NAV minimum translation speed must be in [0, 0.15] m/s")
if args.skip_nav and args.nav_arm_home:
    parser.error("NAV arm hold requires a NAV phase")
if args.handoff_settle_stable_s and (args.skip_nav or not args.nav_arm_home):
    parser.error("Stable handoff requires NAV with the arm held at home")
if args.handoff_settle_control != "nav_zero_velocity" and not args.handoff_settle_stable_s:
    parser.error("Handoff settle control requires a stable handoff phase")
if args.force_push_after_settle_timeout and (not args.handoff_settle_stable_s
                                             or args.handoff_settle_control != "nav_zero_velocity"):
    parser.error("Forced timeout handoff requires staged NAV zero-velocity control")
if args.nav_leg_support_until_ready and (args.skip_nav or not args.nav_arm_home
                                         or args.pre_ready_leg_action_cap or args.hold_push_arm_at_handoff
                                         or args.support_margin_pause_m or args.safe_approach_arm_rate_scale != 1.0):
    parser.error("NAV leg support cannot be combined with other derived PUSH controls")
if not 0.0 <= args.handoff_settle_stable_s <= 2.0 or not 0.4 <= args.handoff_settle_timeout_s <= 5.0:
    parser.error("Handoff stable time must be in [0, 2] s and timeout in [0.4, 5] s")
if args.handoff_settle_stable_s > args.handoff_settle_timeout_s:
    parser.error("Handoff stable time cannot exceed its timeout")
if args.skip_nav and args.nav_min_translation_speed:
    parser.error("NAV minimum translation speed requires a NAV phase")
if args.skip_nav and args.hold_push_arm_at_handoff:
    parser.error("PUSH arm hold requires a NAV handoff")
if args.hold_arm_on_support_warning and (
        args.skip_nav or not args.nav_arm_home or not args.record_push_contact_load_trace
        or not args.record_leg_jacobian_trace or not args.record_base_contact_source
        or args.nav_leg_support_until_ready or args.pre_ready_leg_action_cap
        or args.hold_push_arm_at_handoff or args.support_margin_pause_m
        or args.safe_approach_arm_rate_scale != 1.0 or args.rear_support_feedback
        or args.support_response_probe or args.front_foot_probe_offset_m
        or args.front_foot_hold_offset_m or args.front_foot_feedback
        or args.handoff_settle_stable_s or args.record_push_clock_trace
        or args.push_action_pulse_step is not None
        or args.push_arm_command_pulse_step is not None):
    parser.error("Warning arm hold requires the unmodified immediate baseline with full support telemetry")
if not 0.0 <= args.pre_ready_leg_action_cap <= 0.2 or not 0.2 <= args.pre_ready_leg_ramp_s <= 2.0:
    parser.error("Pre-ready leg action cap must be in [0, 0.2] and ramp in [0.2, 2.0] s")
if args.record_push_contact_load_trace and not args.record_push_support_trace:
    parser.error("Contact/load tracing requires the PUSH support trace")
if args.record_leg_jacobian_trace and not args.record_push_support_trace:
    parser.error("Leg Jacobian tracing requires the PUSH support trace")
if args.record_base_contact_source and not args.record_push_contact_load_trace:
    parser.error("Base contact source tracing requires ground contact/load tracing")
if args.record_base_contact_substeps and not args.record_base_contact_source:
    parser.error("Base contact substep tracing requires base contact source tracing")
if args.record_base_contact_manifold and not args.record_base_contact_substeps:
    parser.error("Base contact manifold tracing requires base contact substep tracing")
if args.record_invalid_hand_contact_detail and not (args.record_push_support_trace
                                                    and args.record_push_contact_load_trace
                                                    and args.record_base_contact_source):
    parser.error("Invalid hand contact detail requires support and contact source telemetry")
if args.record_hand_contact_substeps and not args.record_invalid_hand_contact_detail:
    parser.error("Hand substep tracing requires terminal hand-contact detail")
if args.record_hand_contact_manifold and not args.record_hand_contact_substeps:
    parser.error("Hand contact manifold tracing requires hand substep tracing")
if args.record_push_clock_trace and not args.record_hand_contact_substeps:
    parser.error("PUSH clock tracing requires hand substep tracing")
if args.record_push_actuator_clock and not args.record_push_clock_trace:
    parser.error("Actuator clock tracing requires PUSH clock tracing")
if args.record_push_arm_clock and not args.record_push_actuator_clock:
    parser.error("Arm clock tracing requires the actuator torque clock")
if args.push_action_pulse_step is None:
    if args.push_action_pulse_delta or args.push_action_pulse_index:
        parser.error("Pulse delta and index require a pulse step")
elif (not args.record_push_clock_trace or args.push_action_pulse_step < 1
      or not 0 <= args.push_action_pulse_index < 12
      or not math.isfinite(args.push_action_pulse_delta)
      or not 0.0 < abs(args.push_action_pulse_delta) <= 0.05):
    parser.error("Pulse requires clock trace, a positive step, leg index 0-11, and nonzero delta <= 0.05")
if args.push_arm_command_pulse_step is None:
    if args.push_arm_command_pulse_rad:
        parser.error("Arm command pulse increment requires a pulse step")
elif (not args.record_push_arm_clock or args.push_arm_command_pulse_step < 1
      or not math.isfinite(args.push_arm_command_pulse_rad)
      or not 0.0 < abs(args.push_arm_command_pulse_rad) <= 0.01
      or args.push_action_pulse_step is not None):
    parser.error("Arm command pulse requires arm clock, positive step and nonzero increment <= 0.01 rad")
if args.record_recovery_decision_state and (
        args.skip_nav or not args.nav_arm_home or not args.record_push_support_trace
        or not args.record_push_contact_load_trace or not args.record_leg_jacobian_trace
        or not args.record_base_contact_source or args.rear_support_feedback
        or args.front_foot_probe_offset_m or args.front_foot_hold_offset_m
        or args.front_foot_feedback or args.pre_ready_leg_action_cap
        or args.nav_leg_support_until_ready or args.hold_push_arm_at_handoff
        or args.hold_arm_on_support_warning
        or args.support_margin_pause_m or args.safe_approach_arm_rate_scale != 1.0
        or args.handoff_settle_stable_s):
    parser.error("Recovery state tracing requires the unmodified immediate baseline with full telemetry")
if args.support_response_probe and (
        args.skip_nav or not args.nav_arm_home or not args.record_push_contact_load_trace
        or not args.record_leg_jacobian_trace or not args.record_base_contact_source
        or args.record_recovery_decision_state or args.rear_support_feedback
        or args.front_foot_probe_offset_m or args.front_foot_hold_offset_m
        or args.front_foot_feedback or args.pre_ready_leg_action_cap
        or args.nav_leg_support_until_ready or args.hold_push_arm_at_handoff
        or args.support_margin_pause_m or args.safe_approach_arm_rate_scale != 1.0
        or args.handoff_settle_stable_s):
    parser.error("Support response probe requires the unmodified immediate baseline with full telemetry")
if args.record_support_response_velocity and not args.support_response_probe:
    parser.error("Support response velocity requires a support response probe")
if args.rear_support_feedback and (args.skip_nav or not args.nav_arm_home
                                   or not args.record_push_contact_load_trace
                                   or not args.record_leg_jacobian_trace
                                   or args.pre_ready_leg_action_cap or args.nav_leg_support_until_ready
                                   or args.hold_push_arm_at_handoff or args.support_margin_pause_m
                                   or args.safe_approach_arm_rate_scale != 1.0
                                   or args.handoff_settle_stable_s):
    parser.error("Rear support feedback requires the unmodified immediate baseline with full telemetry")
if args.front_foot_probe_offset_m and (args.skip_nav or not args.nav_arm_home
                                       or not args.record_push_contact_load_trace
                                       or not args.record_leg_jacobian_trace
                                       or args.rear_support_feedback or args.front_foot_hold_offset_m
                                       or args.pre_ready_leg_action_cap
                                       or args.nav_leg_support_until_ready or args.hold_push_arm_at_handoff
                                       or args.support_margin_pause_m or args.safe_approach_arm_rate_scale != 1.0
                                       or args.handoff_settle_stable_s):
    parser.error("Front-foot response probe requires the unmodified immediate baseline with full telemetry")
if args.front_foot_hold_offset_m and (args.skip_nav or not args.nav_arm_home
                                      or not args.record_push_contact_load_trace
                                      or not args.record_leg_jacobian_trace or not args.record_base_contact_source
                                      or args.rear_support_feedback or args.front_foot_probe_offset_m
                                      or args.pre_ready_leg_action_cap or args.nav_leg_support_until_ready
                                      or args.hold_push_arm_at_handoff or args.support_margin_pause_m
                                      or args.safe_approach_arm_rate_scale != 1.0
                                      or args.handoff_settle_stable_s):
    parser.error("Front-foot hold pilot requires the unmodified immediate baseline with full telemetry")
if args.front_foot_feedback and (args.skip_nav or not args.nav_arm_home
                                 or not args.record_push_contact_load_trace
                                 or not args.record_leg_jacobian_trace or not args.record_base_contact_source
                                 or args.rear_support_feedback or args.front_foot_probe_offset_m
                                 or args.front_foot_hold_offset_m or args.pre_ready_leg_action_cap
                                 or args.nav_leg_support_until_ready or args.hold_push_arm_at_handoff
                                 or args.support_margin_pause_m or args.safe_approach_arm_rate_scale != 1.0
                                 or args.handoff_settle_stable_s):
    parser.error("Front-foot feedback requires the unmodified immediate baseline with full telemetry")
if args.record_settle_support_trace and (not args.handoff_settle_stable_s or not args.record_push_support_trace):
    parser.error("Preparation tracing requires a staged handoff and PUSH support tracing")
if args.support_margin_pause_m and (not args.record_push_contact_load_trace
                                    or not 0.0 < args.support_margin_pause_m < args.support_margin_resume_m < 0.25):
    parser.error("Support pause requires contact tracing and 0 < pause < resume < 0.25 m")
if not args.support_margin_pause_m and args.support_margin_resume_m:
    parser.error("Support resume margin requires a pause margin")
if args.support_margin_pause_m and args.hold_push_arm_at_handoff:
    parser.error("Support pause and fixed arm target cannot be combined")
if not 0.0 < args.safe_approach_arm_rate_scale <= 1.0:
    parser.error("Safe-approach arm rate scale must be in (0, 1]")
if args.safe_approach_arm_rate_scale < 1.0 and (args.support_margin_pause_m or args.hold_push_arm_at_handoff):
    parser.error("Arm rate scaling cannot be combined with arm pause or fixed arm target")
launcher = AppLauncher(args)

import gymnasium as gym
import torch

import isaaclab_tasks
from isaaclab.sensors import ContactSensorCfg
from isaaclab_tasks.utils import load_cfg_from_registry
from isaaclab_rl.rsl_rl import RslRlVecEnvWrapper

import LeggedManip_Lab.tasks
from LeggedManip_Lab.tasks.manager_based.leggedmanip_lab.mdp import box_push
from LeggedManip_Lab.tasks.manager_based.leggedmanip_lab.mdp.box_push_actions import BoxPushLegAction
from LeggedManip_Lab.tasks.manager_based.leggedmanip_lab.config.go2_piper import box_env_cfg as piper_box_env_cfg
from piper_scene_runtime_observation import canonical_sha256, observe


TASK = "GO2-PIPER-Box-Push-Tracking-Play"
NAV_SHA256 = "72d9f22c633081e8d4b9693e6fda54dba6cdd036a102f330c1bfe096e43b4da8"
PUSH_SHA256 = "b1ebb8abb5370dcd98debab85d70e05a004bb1e59b5b00710460f575174c7721"
CONTROL_SHA256 = {
    "box_push.py": "889a812aa2676b8c0d3d340419af407a64dee67b8d4a07812c1ce0aa74bb1d1d",
    "box_push_control.py": "92d5135c09feaff66ae848709588f1d2aa75af40e55f7e4428445fb95c0c5b3d",
    "box_push_ik.py": "6086163efb4d64b5a812cb2cbe506bc82eaafbca6b08186151fab7a1145f9370",
    "box_push_actions.py": "d92f8d006b1f5b74b7603501ec68a38fe88894e151c961fafcfb15adaf92d7c5",
}


class NavPushAction(BoxPushLegAction):
    """Route 18 NAV actions directly and 12 PUSH actions through original IK."""

    def __init__(self, cfg, env):
        super().__init__(cfg, env)
        self.phase = "nav"
        self.nav_arm_command = None
        self.nav_support_command = None
        self.nav_leg_support_steps = 0
        self.pre_ready_leg_steps = 0
        self.arm_command_pulse_count = 0
        self.held_push_arm_command = None
        self.warning_arm_hold_reference = None
        self.warning_arm_hold_steps = 0
        self.support_pause_active = False
        self.support_pause_steps = 0
        self.support_margin_m = None
        self.slowed_approach_steps = 0
        self.rear_support_feedback_pending = False
        self.rear_support_feedback_applied = False
        self.rear_support_feedback_steps = 0
        self.rear_support_feedback_max_target_delta_rad = 0.0
        self.rear_support_feedback_config = None
        self.rear_support_feedback_previous_targets = None
        self.front_foot_probe_config = None
        self.front_foot_probe_previous_targets = None
        self.front_foot_probe_applied = False
        self.front_foot_probe_steps = 0
        self.front_foot_probe_max_target_delta_rad = 0.0
        self.front_foot_hold_applied = False
        self.front_foot_hold_steps = 0
        self.front_foot_feedback_steps = 0
        self.front_foot_feedback_offset_m = 0.0
        self.front_foot_feedback_max_target_delta_rad = 0.0
        self.front_foot_feedback_snapshot = None
        self.front_foot_feedback_foot_ids = None
        self.support_probe_config = None
        self.support_probe_previous_targets = None
        self.support_probe_pending = False
        self.support_probe_active_steps = 0
        self.support_probe_applied = False
        self.support_probe_steps = 0
        self.support_probe_max_target_delta_rad = 0.0

    @property
    def action_dim(self):
        return 18

    def process_actions(self, actions):
        if actions.shape[1] != 18:
            raise ValueError("NAV/PUSH router requires 18 action slots")
        if self.phase == "nav":
            if self.nav_arm_command is not None:
                actions = actions.clone()
                actions[:, self.controller.action_slots] = self.nav_arm_command
            self.joint_commands[:] = actions
            self._raw[:] = actions[:, self.controller.leg_slots]
            self.delegate.process_actions(actions)
        elif self.phase == "push":
            self.rear_support_feedback_applied = False
            self.front_foot_probe_applied = False
            self.front_foot_hold_applied = False
            self.front_foot_feedback_snapshot = None
            self.support_probe_applied = False
            previous_reference = (
                self.controller.reference.clone()
                if args.support_margin_pause_m or args.safe_approach_arm_rate_scale < 1.0 else None
            )
            super().process_actions(actions[:, :12])
            self.pre_ready_leg_steps += 1
            modified = False
            if self.nav_support_command is not None and not bool(self.controller.motion_ready[0]):
                self.joint_commands[:, self.controller.leg_slots] = self.nav_support_command
                self.nav_leg_support_steps += 1
                modified = True
            if (args.safe_approach_arm_rate_scale < 1.0
                    and not bool(self.controller.safe_approach_complete[0])):
                arm = self.controller
                arm.reference = previous_reference + args.safe_approach_arm_rate_scale * (
                    arm.reference - previous_reference
                )
                robot = arm.robot
                gravity = robot.root_physx_view.get_gravity_compensation_forces()
                columns = arm.joint_ids if gravity.shape[1] == robot.num_joints else arm.jacobian_columns
                compensated = arm.reference + gravity[:, columns] / arm.stiffness
                self.joint_commands[:, arm.action_slots] = (
                    compensated - robot.data.default_joint_pos[:, arm.joint_ids]
                ) / arm.scale
                self.slowed_approach_steps += 1
                modified = True
            if args.support_margin_pause_m:
                self.support_margin_m = contact_mean_support_margin(self.controller.env)
                if (self.pre_ready_leg_steps * self.controller.env.step_dt >= 1.0
                        and not bool(self.controller.safe_approach_complete[0])):
                    if self.support_pause_active:
                        self.support_pause_active = (self.support_margin_m is None
                                                     or self.support_margin_m < args.support_margin_resume_m)
                    else:
                        self.support_pause_active = (self.support_margin_m is None
                                                     or self.support_margin_m < args.support_margin_pause_m)
                else:
                    self.support_pause_active = False
                if self.support_pause_active:
                    arm = self.controller
                    arm.reference = previous_reference
                    robot = arm.robot
                    gravity = robot.root_physx_view.get_gravity_compensation_forces()
                    columns = arm.joint_ids if gravity.shape[1] == robot.num_joints else arm.jacobian_columns
                    compensated = arm.reference + gravity[:, columns] / arm.stiffness
                    self.joint_commands[:, arm.action_slots] = (
                        compensated - robot.data.default_joint_pos[:, arm.joint_ids]
                    ) / arm.scale
                    self.support_pause_steps += 1
                    modified = True
            if args.pre_ready_leg_action_cap:
                ramp = min(self.pre_ready_leg_steps * self.controller.env.step_dt / args.pre_ready_leg_ramp_s, 1.0)
                capped = actions[:, :12].clamp(
                    -args.pre_ready_leg_action_cap, args.pre_ready_leg_action_cap
                ) * ramp
                slots = self.controller.leg_slots
                self.joint_commands[:, slots] = torch.where(
                    self.controller.motion_ready[:, None], self.joint_commands[:, slots], capped
                )
                modified = True
            if self.rear_support_feedback_pending and not bool(self.controller.motion_ready[0]):
                self.apply_rear_support_feedback()
                self.rear_support_feedback_applied = True
                self.rear_support_feedback_steps += 1
                modified = True
            elapsed = self.pre_ready_leg_steps * self.controller.env.step_dt
            if (args.front_foot_probe_offset_m and 4.40 <= elapsed <= 4.80
                    and not bool(self.controller.motion_ready[0])):
                envelope = max(0.0, 1.0 - abs(2.0 * (elapsed - 4.40) / 0.40 - 1.0))
                self.apply_front_foot_offset(args.front_foot_probe_offset_m * envelope)
                self.front_foot_probe_applied = True
                self.front_foot_probe_steps += 1
                modified = True
            if (args.front_foot_hold_offset_m and 4.40 <= elapsed <= 6.20
                    and not bool(self.controller.motion_ready[0])):
                envelope = min((elapsed - 4.40) / 0.20, 1.0, (6.20 - elapsed) / 0.20)
                self.apply_front_foot_offset(args.front_foot_hold_offset_m * max(0.0, envelope))
                self.front_foot_hold_applied = True
                self.front_foot_hold_steps += 1
                modified = True
            if (args.front_foot_feedback and 4.40 <= elapsed <= 6.20
                    and not bool(self.controller.motion_ready[0])):
                self.apply_front_foot_feedback(elapsed)
                modified = True
            if (args.support_response_probe and self.support_probe_pending
                    and self.support_probe_active_steps < 20
                    and not bool(self.controller.motion_ready[0])):
                self.support_probe_active_steps += 1
                pulse_s = self.support_probe_active_steps * self.controller.env.step_dt
                envelope = max(0.0, 1.0 - abs(pulse_s - 0.20) / 0.20)
                signed_offset = 0.003 if args.support_response_probe.endswith("up") else -0.003
                self.apply_support_response_offset(signed_offset * envelope)
                self.support_probe_applied = True
                self.support_probe_steps += 1
                modified = True
            if self.held_push_arm_command is not None:
                self.joint_commands[:, self.controller.action_slots] = self.held_push_arm_command
                modified = True
            if self.warning_arm_hold_reference is not None:
                arm = self.controller
                arm.reference = self.warning_arm_hold_reference.clone()
                robot = arm.robot
                gravity = robot.root_physx_view.get_gravity_compensation_forces()
                columns = arm.joint_ids if gravity.shape[1] == robot.num_joints else arm.jacobian_columns
                compensated = arm.reference + gravity[:, columns] / arm.stiffness
                self.joint_commands[:, arm.action_slots] = (
                    compensated - robot.data.default_joint_pos[:, arm.joint_ids]
                ) / arm.scale
                self.joint_commands[:, arm.leg_slots] = 0.0
                self.warning_arm_hold_steps += 1
                modified = True
            if args.push_arm_command_pulse_step == self.pre_ready_leg_steps:
                robot = self.controller.robot
                names = [robot.joint_names[joint_id] for joint_id in self.controller.joint_ids]
                joint_index = names.index(args.push_arm_command_pulse_joint)
                action_slot = self.controller.action_slots[joint_index]
                self.joint_commands[0, action_slot] += args.push_arm_command_pulse_rad / self.controller.scale
                self.arm_command_pulse_count += 1
                modified = True
            if modified:
                self.delegate.process_actions(self.joint_commands)
        else:
            raise RuntimeError(f"Unknown phase: {self.phase}")

    def apply_front_foot_offset(self, offset_m):
        robot = self.controller.robot
        jacobians = robot.root_physx_view.get_jacobians()
        offset = 0 if robot.is_fixed_base else 6
        if self.front_foot_probe_config is None:
            raise RuntimeError("Front-foot probe was not configured")
        if self.front_foot_probe_previous_targets is None:
            self.front_foot_probe_previous_targets = {
                name: robot.data.default_joint_pos[0, joint_ids].clone()
                for name, _body_id, joint_ids, _slots in self.front_foot_probe_config
            }
        for name, body_id, joint_ids, slots in self.front_foot_probe_config:
            columns = [joint_id + offset for joint_id in joint_ids]
            vertical_jacobian = jacobians[0, body_id, 2, columns]
            if not bool(torch.isfinite(vertical_jacobian).all()):
                raise RuntimeError(f"Invalid front-foot Jacobian: {name}")
            delta = offset_m * vertical_jacobian / (
                torch.dot(vertical_jacobian, vertical_jacobian) + 0.05 ** 2
            )
            default = robot.data.default_joint_pos[0, joint_ids]
            target = default + delta.clamp(-0.04, 0.04)
            previous = self.front_foot_probe_previous_targets[name]
            target = torch.maximum(torch.minimum(target, previous + 0.02), previous - 0.02)
            limits = robot.data.soft_joint_pos_limits[0, joint_ids]
            target = torch.maximum(torch.minimum(target, limits[:, 1]), limits[:, 0])
            self.front_foot_probe_previous_targets[name] = target.clone()
            self.front_foot_probe_max_target_delta_rad = max(
                self.front_foot_probe_max_target_delta_rad, float((target - default).abs().amax())
            )
            self.joint_commands[0, slots] = (target - default) / self.controller.scale

    def apply_front_foot_feedback(self, elapsed):
        robot = self.controller.robot
        q = robot.data.root_quat_w[0]
        pitch = float(torch.asin((2.0 * (q[0] * q[2] - q[3] * q[1])).clamp(-1.0, 1.0)))
        omega_y = float(robot.data.root_ang_vel_w[0, 1])
        forces = self.controller.env.scene["contact_forces"].data.net_forces_w[0,
                                                                                  self.front_foot_feedback_foot_ids, 2]
        if not bool(torch.isfinite(forces).all()) or not math.isfinite(pitch) or not math.isfinite(omega_y):
            raise RuntimeError("Invalid front-foot feedback state")
        positive_forces = forces.clamp(min=0.0)
        total_force = float(positive_forces.sum())
        qualified = total_force >= 20.0
        rear_share = float(positive_forces[2:].sum()) / total_force if qualified else None
        risk = max(
            min(max((pitch - 0.06) / 0.10, 0.0), 1.0),
            min(max((omega_y - 0.02) / 0.20, 0.0), 1.0),
            min(max((0.30 - rear_share) / 0.20, 0.0), 1.0),
        ) if qualified else 0.0
        exit_envelope = min(max((6.20 - elapsed) / 0.20, 0.0), 1.0)
        desired_offset = -0.005 * risk * exit_envelope
        previous = self.front_foot_feedback_offset_m
        applied_offset = min(max(desired_offset, previous - 0.0005), previous + 0.0005)
        self.front_foot_feedback_offset_m = applied_offset
        self.apply_front_foot_offset(applied_offset)
        self.front_foot_feedback_max_target_delta_rad = max(
            self.front_foot_feedback_max_target_delta_rad, self.front_foot_probe_max_target_delta_rad
        )
        self.front_foot_feedback_steps += 1
        self.front_foot_feedback_snapshot = {
            "base_pitch_rad_before_action": pitch,
            "world_y_angular_velocity_rad_s_before_action": omega_y,
            "total_foot_normal_force_n_before_action": total_force,
            "rear_normal_force_fraction_before_action": rear_share,
            "support_input_qualified": qualified,
            "risk_demand": risk,
            "applied_world_foot_z_target_offset_m": applied_offset,
        }

    def apply_support_response_offset(self, offset_m):
        robot = self.controller.robot
        if self.support_probe_config is None:
            raise RuntimeError("Support response probe was not configured")
        jacobians = robot.root_physx_view.get_jacobians()
        base_columns = 0 if robot.is_fixed_base else 6
        if self.support_probe_previous_targets is None:
            self.support_probe_previous_targets = {
                name: robot.data.default_joint_pos[0, joint_ids].clone()
                for name, _body_id, joint_ids, _slots in self.support_probe_config
            }
        for name, body_id, joint_ids, slots in self.support_probe_config:
            columns = [joint_id + base_columns for joint_id in joint_ids]
            vertical_jacobian = jacobians[0, body_id, 2, columns]
            if not bool(torch.isfinite(vertical_jacobian).all()):
                raise RuntimeError(f"Invalid support probe Jacobian: {name}")
            delta = offset_m * vertical_jacobian / (
                torch.dot(vertical_jacobian, vertical_jacobian) + 0.05 ** 2
            )
            default = robot.data.default_joint_pos[0, joint_ids]
            target = default + delta.clamp(-0.04, 0.04)
            previous = self.support_probe_previous_targets[name]
            target = torch.maximum(torch.minimum(target, previous + 0.02), previous - 0.02)
            limits = robot.data.soft_joint_pos_limits[0, joint_ids]
            target = torch.maximum(torch.minimum(target, limits[:, 1]), limits[:, 0])
            self.support_probe_previous_targets[name] = target.clone()
            self.support_probe_max_target_delta_rad = max(
                self.support_probe_max_target_delta_rad, float((target - default).abs().amax())
            )
            self.joint_commands[0, slots] = (target - default) / self.controller.scale

    def apply_rear_support_feedback(self):
        robot = self.controller.robot
        jacobians = robot.root_physx_view.get_jacobians()
        sensor = self.controller.env.scene["contact_forces"]
        offset = 0 if robot.is_fixed_base else 6
        if self.rear_support_feedback_config is None:
            raise RuntimeError("Rear support feedback was not configured")
        if self.rear_support_feedback_previous_targets is None:
            self.rear_support_feedback_previous_targets = {
                name: robot.data.default_joint_pos[0, joint_ids].clone()
                for name, _sensor_id, _body_id, joint_ids, _slots in self.rear_support_feedback_config
            }
        for name, sensor_id, body_id, joint_ids, slots in self.rear_support_feedback_config:
            force = sensor.data.net_forces_w[0, sensor_id, 2]
            columns = [joint_id + offset for joint_id in joint_ids]
            vertical_jacobian = jacobians[0, body_id, 2, columns]
            if not bool(torch.isfinite(force) and torch.isfinite(vertical_jacobian).all()):
                raise RuntimeError(f"Invalid rear support feedback input: {name}")
            deficit = ((5.0 - force) / 5.0).clamp(0.0, 1.0)
            delta = (-0.01 * deficit) * vertical_jacobian / (
                torch.dot(vertical_jacobian, vertical_jacobian) + 0.05 ** 2
            )
            default = robot.data.default_joint_pos[0, joint_ids]
            target = default + delta.clamp(-0.08, 0.08)
            previous = self.rear_support_feedback_previous_targets[name]
            target = torch.maximum(torch.minimum(target, previous + 0.03), previous - 0.03)
            limits = robot.data.soft_joint_pos_limits[0, joint_ids]
            target = torch.maximum(torch.minimum(target, limits[:, 1]), limits[:, 0])
            self.rear_support_feedback_previous_targets[name] = target.clone()
            self.rear_support_feedback_max_target_delta_rad = max(
                self.rear_support_feedback_max_target_delta_rad, float((target - default).abs().amax())
            )
            self.joint_commands[0, slots] = (target - default) / self.controller.scale

    def reset(self, env_ids=None):
        self.pre_ready_leg_steps = 0
        self.nav_support_command = None
        self.nav_leg_support_steps = 0
        self.held_push_arm_command = None
        self.warning_arm_hold_reference = None
        self.warning_arm_hold_steps = 0
        self.support_pause_active = False
        self.support_pause_steps = 0
        self.support_margin_m = None
        self.slowed_approach_steps = 0
        self.rear_support_feedback_pending = False
        self.rear_support_feedback_applied = False
        self.rear_support_feedback_steps = 0
        self.rear_support_feedback_max_target_delta_rad = 0.0
        self.rear_support_feedback_previous_targets = None
        self.front_foot_probe_previous_targets = None
        self.front_foot_probe_applied = False
        self.front_foot_probe_steps = 0
        self.front_foot_probe_max_target_delta_rad = 0.0
        self.front_foot_hold_applied = False
        self.front_foot_hold_steps = 0
        self.front_foot_feedback_steps = 0
        self.front_foot_feedback_offset_m = 0.0
        self.front_foot_feedback_max_target_delta_rad = 0.0
        self.front_foot_feedback_snapshot = None
        self.support_probe_previous_targets = None
        self.support_probe_pending = False
        self.support_probe_active_steps = 0
        self.support_probe_applied = False
        self.support_probe_steps = 0
        self.support_probe_max_target_delta_rad = 0.0
        super().reset(env_ids)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def contact_mean_support_margin(base):
    from analyze_piper_isaac_support_dynamics import signed_margin

    robot = base.scene["robot"]
    masses = robot.root_physx_view.get_masses()[0].to(robot.data.body_com_pos_w.device)
    center = (robot.data.body_com_pos_w[0] * masses[:, None]).sum(dim=0) / masses.sum()
    points = []
    for foot in ("fl", "fr", "rl", "rr"):
        sensor = base.scene[f"diagnostic_{foot}_ground"]
        if float(sensor.data.force_matrix_w[0, 0, 0, 2]) > 2.0:
            point = sensor.data.contact_pos_w[0, 0, 0]
            if not bool(torch.isfinite(point).all()):
                return None
            points.append(point[:2].tolist())
    return signed_margin(points, center[:2].tolist())


def robot_state(base):
    robot = base.scene["robot"]
    box = base.scene["box"]
    origin = base.scene.env_origins[0]
    return {
        "base_pos": (robot.data.root_pos_w[0] - origin).tolist(),
        "base_quat": robot.data.root_quat_w[0].tolist(),
        "base_vel": robot.data.root_lin_vel_w[0].tolist(),
        "base_omega": robot.data.root_ang_vel_w[0].tolist(),
        "joint_pos": robot.data.joint_pos[0].tolist(),
        "joint_vel": robot.data.joint_vel[0].tolist(),
        "box_pos": (box.data.root_pos_w[0] - origin).tolist(),
        "box_quat": box.data.root_quat_w[0].tolist(),
        "box_vel": box.data.root_lin_vel_w[0].tolist(),
        "box_omega": box.data.root_ang_vel_w[0].tolist(),
    }


def controller_state(controller):
    return {
        "reference": controller.reference[0].tolist(),
        "safe_approach_index": int(controller.safe_approach_index[0]),
        "safe_approach_complete": bool(controller.safe_approach_complete[0]),
        "precontact_stage": int(controller.precontact_stage[0]),
        "motion_ready": bool(controller.motion_ready[0]),
        "contact_memory_left": float(controller.contact_memory_left[0]),
        "leg_release_elapsed": float(controller.leg_release_elapsed[0]),
        "leg_release_blend": float(controller.leg_release_blend[0]),
        "goal_hold_active": bool(controller.goal_hold_active[0]),
        "velocity_integral": controller.velocity_integral[0].tolist(),
    }


def arm_approach_state(controller, robot):
    position = robot.data.joint_pos[0, controller.joint_ids]
    velocity = robot.data.joint_vel[0, controller.joint_ids]
    waypoints = controller.safe_approach_waypoints
    index = int(controller.safe_approach_index[0])
    return {
        "index": index,
        "joint_position": position.tolist(),
        "joint_velocity_max_abs": float(velocity.abs().amax()),
        "waypoint_joint_distance_max_abs":
            (position[None, :] - waypoints).abs().amax(dim=1).tolist(),
        "active_waypoint_distance_max_abs":
            float((position - waypoints[index]).abs().amax()) if index < len(waypoints) else None,
    }


def yaw_from_quat(quat):
    w, x, y, z = quat
    return math.atan2(2.0 * (w * z + x * y), 1.0 - 2.0 * (y * y + z * z))


def nav_command(state, goal_x, minimum_translation_speed):
    x, y = state["base_pos"][:2]
    yaw = yaw_from_quat(state["base_quat"])
    error_x, error_y = goal_x - x, -y
    body_x = math.cos(yaw) * error_x + math.sin(yaw) * error_y
    body_y = -math.sin(yaw) * error_x + math.cos(yaw) * error_y
    yaw_error = math.atan2(math.sin(-yaw), math.cos(-yaw))
    velocity = [
        max(-0.45, min(0.45, 0.8 * body_x)),
        max(-0.25, min(0.25, 0.8 * body_y)),
        max(-0.70, min(0.70, 1.2 * yaw_error)),
    ]
    distance = math.hypot(error_x, error_y)
    if distance < 0.05:
        velocity[:2] = [0.0, 0.0]
    else:
        translation_speed = math.hypot(*velocity[:2])
        if 0.0 < translation_speed < minimum_translation_speed:
            velocity[:2] = [value * minimum_translation_speed / translation_speed for value in velocity[:2]]
    return velocity, distance, abs(yaw_error)


def main():
    if not args.probe_ground_prims and (sha256(args.nav_actor) != NAV_SHA256 or sha256(args.push_checkpoint) != PUSH_SHA256):
        raise RuntimeError("NAV or PUSH policy hash differs from the handoff")
    mdp_dir = Path(box_push.__file__).resolve().parent
    actual_control_hashes = {name: sha256(mdp_dir / name) for name in CONTROL_SHA256}
    if actual_control_hashes != CONTROL_SHA256:
        raise RuntimeError("PUSH control source differs from the handoff")

    config = load_cfg_from_registry(TASK, "env_cfg_entry_point")
    config.scene.num_envs = 1
    config.seed = args.seed
    config.sim.device = args.device
    config.observations.policy.enable_corruption = False
    config.episode_length_s = 30.0
    config.scene.robot.init_state.pos = (args.nav_start_x, *config.scene.robot.init_state.pos[1:])
    if args.box_nominal_y_m is not None:
        box_position = config.scene.box.init_state.pos
        config.scene.box.init_state.pos = (box_position[0], args.box_nominal_y_m, box_position[2])
    config.push_ik_clearance_minimum = 0.10
    config.push_ik_orientation_weight = 0.5
    config.push_ik_joint_limit_solve = True
    config.push_goal_hold_pose = True
    config.push_press_on_legal_contact = True
    config.push_stop_distance = 0.11
    config.push_contact_memory_s = 0.10
    config.push_leg_release_ramp_s = 0.7
    config.push_leg_contact_ramp_s = 0.2
    config.push_forward_command_gain = 2.0
    config.push_contact_gap_slowdown_start = 0.0
    config.push_press_depth = 0.10
    config.push_hand_height_offset = 0.03
    if hasattr(config, "push_contact_height_offset"):
        config.push_contact_height_offset = 0.03
    config.actions.joint_pos.hand_pitch = 0.6
    config.actions.joint_pos.class_type = NavPushAction
    if args.record_push_contact_load_trace:
        for foot in ("FL", "FR", "RL", "RR"):
            setattr(config.scene, f"diagnostic_{foot.lower()}_ground", ContactSensorCfg(
                prim_path=f"{{ENV_REGEX_NS}}/Robot/{foot}_foot",
                filter_prim_paths_expr=[args.ground_filter_prim],
                track_contact_points=True,
                track_friction_forces=True,
                max_contact_data_count_per_prim=8,
                update_period=config.sim.dt,
            ))
    if args.record_base_contact_source:
        for target, prim_path in (("ground", args.ground_filter_prim), ("box", "{ENV_REGEX_NS}/Box")):
            setattr(config.scene, f"diagnostic_base_{target}", ContactSensorCfg(
                prim_path="{ENV_REGEX_NS}/Robot/base",
                filter_prim_paths_expr=[prim_path],
                track_contact_points=True,
                max_contact_data_count_per_prim=8,
                update_period=config.sim.dt,
            ))

    agent_config = load_cfg_from_registry(TASK, "rsl_rl_cfg_entry_point")
    agent_config.device = args.device
    agent_config.seed = args.seed
    env = RslRlVecEnvWrapper(
        gym.make(TASK, cfg=config, render_mode="rgb_array" if args.video_path else None),
        clip_actions=agent_config.clip_actions,
    )
    video = None
    try:
        base = env.unwrapped
        if args.video_path is not None:
            import imageio.v2 as imageio

            args.video_path.parent.mkdir(parents=True, exist_ok=True)
            video = imageio.get_writer(str(args.video_path), fps=round(1.0 / (2 * base.step_dt)), codec="libx264")
            origin = base.scene.env_origins[0].cpu().numpy()
            base.sim.set_camera_view(eye=origin + [0.7, 3.2, 1.5],
                                     target=origin + [0.9, 0.0, 0.3])
        if args.probe_ground_prims:
            import omni.usd
            from pxr import UsdPhysics

            stage = omni.usd.get_context().get_stage()
            ground = stage.GetPrimAtPath("/World/ground")
            collision_prims = [
                {"path": str(prim.GetPath()), "type": prim.GetTypeName()}
                for prim in stage.Traverse()
                if str(prim.GetPath()).startswith("/World/ground") and prim.HasAPI(UsdPhysics.CollisionAPI)
            ]
            if not ground.IsValid() or not collision_prims:
                raise RuntimeError("No ground collision prim found in the active USD stage")
            args.output_json.parent.mkdir(parents=True, exist_ok=True)
            with args.output_json.open("x", encoding="utf-8") as stream:
                json.dump({"ground_collision_prims": collision_prims}, stream, indent=2)
            print("GROUND_PRIMS=" + str(args.output_json), flush=True)
            return
        action_term = base.action_manager.get_term("joint_pos")
        robot = base.scene["robot"]
        if args.nav_arm_home:
            arm = action_term.controller
            home = arm.safe_approach_waypoints[0]
            initial = robot.data.joint_pos[0, arm.joint_ids]
            if float((initial - home).abs().amax()) > 0.05:
                raise RuntimeError("NAV arm hold requires the arm to start near the safe home posture")
            default = robot.data.default_joint_pos[0, arm.joint_ids]
            action_term.nav_arm_command = (home - default) / arm.scale
        foot_sensor = base.scene["contact_forces"]
        foot_ids, foot_names = foot_sensor.find_bodies(".*_foot")
        leg_jacobian_ids = {}
        if args.record_leg_jacobian_trace:
            for name in foot_names:
                leg = name.split("_", 1)[0]
                leg_jacobian_ids[name] = [robot.joint_names.index(f"{leg}_{joint}_joint")
                                          for joint in ("hip", "thigh", "calf")]
        rear_foot_indices = [foot_names.index(name) for name in ("RL_foot", "RR_foot")]
        if args.rear_support_feedback:
            action_joint_ids = robot.find_joints(config.actions.joint_pos.joint_names, preserve_order=True)[0]
            if len(action_joint_ids) != 18 or set(action_term.controller.leg_slots) != set(range(12)):
                raise RuntimeError("Rear support feedback requires the frozen 12-leg/6-arm action layout")
            action_term.rear_support_feedback_config = [
                (name, int(foot_ids[foot_names.index(name)]), robot.body_names.index(name),
                 leg_jacobian_ids[name], [action_joint_ids.index(joint_id) for joint_id in leg_jacobian_ids[name]])
                for name in ("RL_foot", "RR_foot")
            ]
            for name, _sensor_id, body_id, joint_ids, slots in action_term.rear_support_feedback_config:
                if (body_id >= robot.root_physx_view.get_jacobians().shape[1]
                        or len(slots) != 3 or not set(slots).issubset(action_term.controller.leg_slots)
                        or [action_joint_ids[slot] for slot in slots] != joint_ids):
                    raise RuntimeError(f"Invalid rear support joint mapping: {name}")
        if args.front_foot_probe_offset_m or args.front_foot_hold_offset_m or args.front_foot_feedback:
            action_joint_ids = robot.find_joints(config.actions.joint_pos.joint_names, preserve_order=True)[0]
            action_term.front_foot_probe_config = [
                (name, robot.body_names.index(name), leg_jacobian_ids[name],
                 [action_joint_ids.index(joint_id) for joint_id in leg_jacobian_ids[name]])
                for name in ("FL_foot", "FR_foot")
            ]
            for name, body_id, joint_ids, slots in action_term.front_foot_probe_config:
                if (body_id >= robot.root_physx_view.get_jacobians().shape[1]
                        or len(slots) != 3 or not set(slots).issubset(action_term.controller.leg_slots)
                        or [action_joint_ids[slot] for slot in slots] != joint_ids):
                    raise RuntimeError(f"Invalid front-foot probe joint mapping: {name}")
            if args.front_foot_feedback:
                action_term.front_foot_feedback_foot_ids = [
                    int(foot_ids[foot_names.index(name)])
                    for name in ("FL_foot", "FR_foot", "RL_foot", "RR_foot")
                ]
        if args.support_response_probe:
            selected = ("FL_foot", "FR_foot") if args.support_response_probe.startswith("front") else (
                "RL_foot", "RR_foot"
            )
            action_joint_ids = robot.find_joints(config.actions.joint_pos.joint_names, preserve_order=True)[0]
            action_term.support_probe_config = [
                (name, robot.body_names.index(name), leg_jacobian_ids[name],
                 [action_joint_ids.index(joint_id) for joint_id in leg_jacobian_ids[name]])
                for name in selected
            ]
            for name, body_id, joint_ids, slots in action_term.support_probe_config:
                if (body_id >= robot.root_physx_view.get_jacobians().shape[1]
                        or len(slots) != 3 or not set(slots).issubset(action_term.controller.leg_slots)
                        or [action_joint_ids[slot] for slot in slots] != joint_ids):
                    raise RuntimeError(f"Invalid support probe joint mapping: {name}")
        settled_term = base.termination_manager.get_term_cfg("box_settled").func
        if args.record_push_support_trace:
            robot_foot_ids = [robot.body_names.index(name) for name in foot_names]
            body_masses = robot.root_physx_view.get_masses()[0].to(robot.data.joint_pos.device)
            if body_masses.shape != (robot.data.body_com_pos_w.shape[1],) or not bool((body_masses > 0).all()):
                raise RuntimeError("Robot body masses do not match COM bodies")
        if args.record_push_contact_load_trace:
            ground_sensors = {
                f"{foot}_foot": base.scene[f"diagnostic_{foot.lower()}_ground"]
                for foot in ("FL", "FR", "RL", "RR")
            }
            for name, sensor in ground_sensors.items():
                if sensor.data.contact_pos_w is None or sensor.data.contact_pos_w.shape != (1, 1, 1, 3):
                    raise RuntimeError(f"No single-body ground contact point channel for {name}")
        if args.record_base_contact_source:
            base_sensor_id = foot_sensor.find_bodies("base")[0]
            if len(base_sensor_id) != 1:
                raise RuntimeError("Expected one base body in the original contact sensor")
            base_source_sensors = {
                name: base.scene[f"diagnostic_base_{name}"] for name in ("ground", "box")
            }
            for name, sensor in base_source_sensors.items():
                if (sensor.data.contact_pos_w is None
                        or sensor.data.contact_pos_w.shape != (1, 1, 1, 3)
                        or sensor.data.force_matrix_w.shape != (1, 1, 1, 3)):
                    raise RuntimeError(f"Unexpected base-{name} contact channel layout")
        if args.record_hand_contact_substeps:
            from isaaclab.utils.math import quat_apply_inverse

            hand_sensor = base.scene.sensors["box_contact_hand"]
            if (hand_sensor.data.contact_pos_w is None
                    or hand_sensor.data.contact_pos_w.shape != (1, 1, 1, 3)
                    or hand_sensor.data.force_matrix_w.shape != (1, 1, 1, 3)):
                raise RuntimeError("Unexpected original hand-box contact channel layout")
            hand_ids, hand_names = robot.find_bodies("^end_effector$")
            if len(hand_ids) != 1 or hand_names != ["end_effector"]:
                raise RuntimeError("Expected one end_effector body")
            box_for_hand_trace = base.scene["box"]

        def contact_load_snapshot():
            contacts = {}
            for name, sensor in ground_sensors.items():
                point = sensor.data.contact_pos_w[0, 0, 0]
                contacts[name] = {
                    "ground_contact_pos": (point - base.scene.env_origins[0]).tolist()
                    if bool(torch.isfinite(point).all()) else None,
                    "ground_normal_force": sensor.data.force_matrix_w[0, 0, 0].tolist(),
                    "ground_friction_force": sensor.data.friction_forces_w[0, 0, 0].tolist(),
                }
            return {
                "ground_contacts": contacts,
                "joint_pos_target": robot.data.joint_pos_target[0].tolist(),
                "computed_torque": robot.data.computed_torque[0].tolist(),
                "applied_torque": robot.data.applied_torque[0].tolist(),
            }

        def support_snapshot():
            body_com = robot.data.body_com_pos_w[0]
            origin = base.scene.env_origins[0]
            robot_com = (body_com * body_masses[:, None]).sum(dim=0) / body_masses.sum()
            forces = foot_sensor.data.net_forces_w[0, foot_ids, 2]
            snapshot = {
                "robot_com_pos": (robot_com - origin).tolist(),
                "foot_body_pos": (robot.data.body_pos_w[0, robot_foot_ids] - origin).tolist(),
                "foot_normal_forces_n": forces.tolist(),
                "supported_feet_gt_2n": int((forces > 2.0).sum()),
                "base_pos": (robot.data.root_pos_w[0] - origin).tolist(),
                "base_quat": robot.data.root_quat_w[0].tolist(),
                "joint_pos": robot.data.joint_pos[0].tolist(),
                "joint_vel": robot.data.joint_vel[0].tolist(),
                "arm_approach_index": int(action_term.controller.safe_approach_index[0]),
                "arm_reference": action_term.controller.reference[0].tolist(),
                "motion_ready": bool(action_term.controller.motion_ready[0]),
                "support_pause_active": action_term.support_pause_active,
                "support_margin_m_before_action": action_term.support_margin_m,
            }
            if args.hold_arm_on_support_warning:
                snapshot["warning_arm_hold_steps"] = action_term.warning_arm_hold_steps
            if args.record_push_contact_load_trace:
                snapshot.update(contact_load_snapshot())
            if args.record_base_contact_source:
                base_force = foot_sensor.data.net_forces_w[0, base_sensor_id[0]]
                sources = {}
                for name, sensor in base_source_sensors.items():
                    point = sensor.data.contact_pos_w[0, 0, 0]
                    sources[name] = {
                        "force_w": sensor.data.force_matrix_w[0, 0, 0].tolist(),
                        "contact_pos": (point - origin).tolist() if bool(torch.isfinite(point).all()) else None,
                    }
                snapshot["base_contact_source"] = {
                    "net_force_w": base_force.tolist(),
                    "net_force_history_w": foot_sensor.data.net_forces_w_history[0, :, base_sensor_id[0]].tolist(),
                    "filtered": sources,
                }
            if args.record_recovery_decision_state:
                physical = robot_state(base)
                snapshot["recovery_decision_state"] = {
                    "base_vel_w": physical["base_vel"],
                    "base_omega_w": physical["base_omega"],
                    "box_pos": physical["box_pos"],
                    "box_quat": physical["box_quat"],
                    "box_vel_w": physical["box_vel"],
                    "box_omega_w": physical["box_omega"],
                    "arm_controller": controller_state(action_term.controller),
                    "settled_duration_s": float(settled_term.duration[0]),
                    "settled_contact_seen": bool(settled_term.contact_seen[0]),
                }
            if args.rear_support_feedback:
                snapshot["rear_support_feedback_applied"] = action_term.rear_support_feedback_applied
                snapshot["rear_support_feedback_leg_actions"] = {
                    name: action_term.joint_commands[0, slots].tolist()
                    for name, _sensor_id, _body_id, _joint_ids, slots in action_term.rear_support_feedback_config
                }
            if args.front_foot_probe_offset_m:
                snapshot["front_foot_probe_applied"] = action_term.front_foot_probe_applied
                snapshot["front_foot_probe_leg_actions"] = {
                    name: action_term.joint_commands[0, slots].tolist()
                    for name, _body_id, _joint_ids, slots in action_term.front_foot_probe_config
                }
            if args.front_foot_hold_offset_m:
                snapshot["front_foot_hold_applied"] = action_term.front_foot_hold_applied
                snapshot["front_foot_hold_leg_actions"] = {
                    name: action_term.joint_commands[0, slots].tolist()
                    for name, _body_id, _joint_ids, slots in action_term.front_foot_probe_config
                }
            if args.front_foot_feedback:
                snapshot["front_foot_feedback"] = action_term.front_foot_feedback_snapshot
                snapshot["front_foot_feedback_leg_actions"] = {
                    name: action_term.joint_commands[0, slots].tolist()
                    for name, _body_id, _joint_ids, slots in action_term.front_foot_probe_config
                }
            if args.support_response_probe:
                snapshot["support_probe_applied"] = action_term.support_probe_applied
                snapshot["support_probe_leg_actions"] = {
                    name: action_term.joint_commands[0, slots].tolist()
                    for name, _body_id, _joint_ids, slots in action_term.support_probe_config
                }
                if args.record_support_response_velocity:
                    snapshot["support_probe_dynamics"] = {
                        "base_vel_w": robot.data.root_lin_vel_w[0].tolist(),
                        "base_omega_w": robot.data.root_ang_vel_w[0].tolist(),
                    }
            return snapshot

        def leg_jacobian_snapshot():
            jacobians = robot.root_physx_view.get_jacobians()
            offset = 0 if robot.is_fixed_base else 6
            if jacobians.ndim != 4 or jacobians.shape[0] != 1 or jacobians.shape[2] != 6:
                raise RuntimeError("Unexpected foot Jacobian layout")
            snapshot = {}
            for name, joint_ids in leg_jacobian_ids.items():
                body_id = robot.body_names.index(name)
                columns = [joint_id + offset for joint_id in joint_ids]
                if body_id >= jacobians.shape[1] or max(columns) >= jacobians.shape[3]:
                    raise RuntimeError(f"Foot Jacobian indices out of bounds: {name}")
                foot_jacobian = jacobians[0, body_id, :3][:, columns]
                singular_values = torch.linalg.svdvals(foot_jacobian)
                position = robot.data.joint_pos[0, joint_ids]
                limits = robot.data.soft_joint_pos_limits[0, joint_ids]
                limit_margin = torch.minimum(position - limits[:, 0], limits[:, 1] - position)
                target_error = (robot.data.joint_pos_target[0, joint_ids] - position).abs()
                if not bool(torch.isfinite(singular_values).all()
                            and torch.isfinite(limit_margin).all()
                            and torch.isfinite(target_error).all()):
                    raise RuntimeError(f"Non-finite leg control authority: {name}")
                snapshot[name] = {
                    "foot_position_jacobian_singular_values": singular_values.tolist(),
                    "minimum_soft_joint_limit_margin_rad": float(limit_margin.min()),
                    "maximum_joint_target_error_rad": float(target_error.max()),
                }
            return snapshot

        def read_only_telemetry():
            forces = foot_sensor.data.net_forces_w[0, foot_ids, 2]
            return {
                "arm_approach": arm_approach_state(action_term.controller, robot),
                "foot_normal_forces_n": forces.tolist(),
                "supported_feet_gt_2n": int((forces > 2.0).sum()),
                "settled_duration_s": float(settled_term.duration[0]),
                "settled_contact_seen": bool(settled_term.contact_seen[0]),
            }

        def invalid_hand_contact_detail():
            from isaaclab.utils.math import quat_apply, quat_apply_inverse

            sensor = base.scene.sensors["box_contact_hand"]
            box = base.scene["box"]
            hand_ids, hand_names = robot.find_bodies("^end_effector$")
            if len(hand_ids) != 1 or hand_names != ["end_effector"]:
                raise RuntimeError("Expected one end_effector body for hand contact detail")
            force = sensor.data.force_matrix_w.sum(dim=(1, 2))[0]
            contact = sensor.data.contact_pos_w[0, 0, 0]
            hand = robot.data.body_pos_w[0, hand_ids[0]]
            finite = bool(torch.isfinite(contact).all())
            axis = torch.zeros_like(force)
            axis[0] = 1.0
            axis = quat_apply(box.data.root_quat_w[0], axis)
            local = quat_apply_inverse(
                box.data.root_quat_w[0], contact - box.data.root_pos_w[0]
            ) if finite else None
            strength = float(torch.linalg.vector_norm(force))
            resisting = float(-torch.dot(force, axis))
            return {
                "force_w_n": force.tolist(),
                "force_norm_n": strength,
                "resisting_force_n": resisting,
                "resisting_fraction": resisting / strength if strength > 0.0 else None,
                "contact_pos_w_m": contact.tolist() if finite else None,
                "contact_pos_box_m": local.tolist() if local is not None else None,
                "hand_pos_w_m": hand.tolist(),
                "contact_to_hand_m": float(torch.linalg.vector_norm(contact - hand)) if finite else None,
                "box_pos_w_m": box.data.root_pos_w[0].tolist(),
                "box_quat_w": box.data.root_quat_w[0].tolist(),
                "box_size_m": list(config.box_size),
                "tip_radius_limit_m": float(getattr(config, "push_contact_tip_radius", 0.07)),
                "height_margin_m": float(getattr(config, "push_contact_height_margin", 0.01)),
            }

        observation = env.get_observations()
        if observation["policy"].shape != (1, 210) or observation["box"].shape != (1, 16):
            raise RuntimeError("Unexpected PUSH observation layout")
        if action_term.action_dim != 18 or action_term.joint_commands.shape != (1, 18):
            raise RuntimeError("Action router layout is incorrect")
        nav_actor = torch.jit.load(str(args.nav_actor), map_location=args.device).eval()
        checkpoint = torch.load(args.push_checkpoint, map_location=args.device, weights_only=False)
        actor_loader = runpy.run_path(str(args.isaac_repo / "scripts/rsl_rl/initialization.py"))["actor_from_state_dict"]
        push_actor = actor_loader(checkpoint["actor_state_dict"], device=args.device)
        push_groups = agent_config.obs_groups["actor"]
        nav_velocity_history = torch.zeros((3, 3), device=args.device)
        nav_pose = torch.tensor([0.5, 0.0, 0.4, 1.0, 0.0, 0.0, 0.0], device=args.device)
        nav_pose_history = nav_pose.repeat(3)
        terminal = {}
        original_pre_reset = base.recorder_manager.record_pre_reset

        def record_pre_reset(env_ids, *callback_args, **callback_kwargs):
            if 0 in env_ids.tolist():
                terminal.update(
                    phase=action_term.phase,
                    step=int(base.episode_length_buf[0]),
                    state=robot_state(base),
                    reasons={name: bool(base.termination_manager.get_term(name)[0])
                             for name in base.termination_manager.active_terms},
                    telemetry=read_only_telemetry(),
                    slowed_approach_steps=action_term.slowed_approach_steps,
                    nav_leg_support_steps=action_term.nav_leg_support_steps,
                )
                if args.rear_support_feedback:
                    terminal["rear_support_feedback_steps"] = action_term.rear_support_feedback_steps
                    terminal["rear_support_feedback_max_target_delta_rad"] = (
                        action_term.rear_support_feedback_max_target_delta_rad
                    )
                if args.front_foot_probe_offset_m:
                    terminal["front_foot_probe_steps"] = action_term.front_foot_probe_steps
                    terminal["front_foot_probe_max_target_delta_rad"] = (
                        action_term.front_foot_probe_max_target_delta_rad
                    )
                if args.front_foot_hold_offset_m:
                    terminal["front_foot_hold_steps"] = action_term.front_foot_hold_steps
                    terminal["front_foot_hold_max_target_delta_rad"] = (
                        action_term.front_foot_probe_max_target_delta_rad
                    )
                if args.front_foot_feedback:
                    terminal["front_foot_feedback_steps"] = action_term.front_foot_feedback_steps
                    terminal["front_foot_feedback_max_target_delta_rad"] = (
                        action_term.front_foot_feedback_max_target_delta_rad
                    )
                if args.support_response_probe:
                    terminal["support_probe_steps"] = action_term.support_probe_steps
                    terminal["support_probe_max_target_delta_rad"] = (
                        action_term.support_probe_max_target_delta_rad
                    )
                if args.hold_arm_on_support_warning:
                    terminal["warning_arm_hold_steps"] = action_term.warning_arm_hold_steps
                if args.record_push_support_trace:
                    terminal["support_snapshot"] = support_snapshot()
                if args.record_leg_jacobian_trace:
                    terminal["leg_jacobians"] = leg_jacobian_snapshot()
                if (args.record_invalid_hand_contact_detail
                        and terminal["reasons"].get("invalid_hand_contact")):
                    terminal["invalid_hand_contact_detail"] = invalid_hand_contact_detail()
            return original_pre_reset(env_ids, *callback_args, **callback_kwargs)

        base.recorder_manager.record_pre_reset = record_pre_reset
        report = {
            "schema_version": 30 if args.hold_arm_on_support_warning
            else 29 if args.record_push_arm_clock
            else 28 if args.record_push_actuator_clock
            else 27 if args.record_push_clock_trace
            else 26 if args.record_hand_contact_manifold
            else 25 if args.record_hand_contact_substeps
            else 24 if args.record_invalid_hand_contact_detail
            else 23 if args.record_scene_runtime_observation
            else 22 if args.record_base_contact_manifold
            else 21 if args.record_base_contact_substeps
            else 20 if args.record_support_response_velocity
            else 19 if args.support_response_probe
            else 18 if args.record_recovery_decision_state
            else 17 if args.front_foot_feedback else 16 if args.front_foot_hold_offset_m
            else 15 if args.front_foot_probe_offset_m
            else 14 if args.record_base_contact_source
            else 13 if args.rear_support_feedback
            else 12 if args.record_leg_jacobian_trace else 11,
            "purpose": "Derived single-scene NAV actor to current PUSH handoff diagnostic",
            "seed": args.seed,
            "task": TASK,
            "nav_actor_sha256": NAV_SHA256,
            "push_checkpoint_sha256": PUSH_SHA256,
            "video_path": str(args.video_path) if args.video_path else None,
            "control_sha256": actual_control_hashes,
            "nav_start_x_m": args.nav_start_x,
            "box_nominal_y_m": float(config.scene.box.init_state.pos[1]),
            "skip_nav": args.skip_nav,
            "nav_arm_home": args.nav_arm_home,
            "nav_arm_home_command": action_term.nav_arm_command.tolist() if args.nav_arm_home else None,
            "nav_goal_xyyaw": [args.nav_goal_x, 0.0, 0.0],
            "nav_min_translation_speed_m_s": args.nav_min_translation_speed,
            "nav_timeout_s": args.nav_timeout_s,
            "handoff_settle_stable_s": args.handoff_settle_stable_s,
            "handoff_settle_timeout_s": args.handoff_settle_timeout_s,
            "handoff_settle_control": args.handoff_settle_control,
            "force_push_after_settle_timeout": args.force_push_after_settle_timeout,
            "nav_leg_support_until_ready": args.nav_leg_support_until_ready,
            "pre_ready_leg_action_cap": args.pre_ready_leg_action_cap,
            "pre_ready_leg_ramp_s": args.pre_ready_leg_ramp_s,
            "hold_push_arm_at_handoff": args.hold_push_arm_at_handoff,
            "hold_arm_on_support_warning": args.hold_arm_on_support_warning,
            "record_push_support_trace": args.record_push_support_trace,
            "record_settle_support_trace": args.record_settle_support_trace,
            "record_push_contact_load_trace": args.record_push_contact_load_trace,
            "record_leg_jacobian_trace": args.record_leg_jacobian_trace,
            "record_base_contact_source": args.record_base_contact_source,
            "record_base_contact_substeps": args.record_base_contact_substeps,
            "record_base_contact_manifold": args.record_base_contact_manifold,
            "record_push_clock_trace": args.record_push_clock_trace,
            "record_push_actuator_clock": args.record_push_actuator_clock,
            **({"record_push_arm_clock": True} if args.record_push_arm_clock else {}),
            "push_action_pulse": ({
                "control_step": args.push_action_pulse_step,
                "actor_index": args.push_action_pulse_index,
                "delta": args.push_action_pulse_delta,
            } if args.push_action_pulse_step is not None else None),
            **({"push_arm_command_pulse": ({
                "control_step": args.push_arm_command_pulse_step,
                "joint": args.push_arm_command_pulse_joint,
                "target_delta_rad": args.push_arm_command_pulse_rad,
            } if args.push_arm_command_pulse_step is not None else None)} if args.record_push_arm_clock else {}),
            "record_recovery_decision_state": args.record_recovery_decision_state,
            "support_response_probe": args.support_response_probe,
            "front_foot_probe_offset_m": args.front_foot_probe_offset_m,
            "front_foot_hold_offset_m": args.front_foot_hold_offset_m,
            "front_foot_feedback": args.front_foot_feedback,
            "ground_filter_prim": args.ground_filter_prim if args.record_push_contact_load_trace else None,
            "support_margin_pause_m": args.support_margin_pause_m,
            "support_margin_resume_m": args.support_margin_resume_m,
            "safe_approach_arm_rate_scale": args.safe_approach_arm_rate_scale,
            "push_budget_s": 12.0,
            "scene_episode_length_s": 30.0,
            "step_dt": float(base.step_dt),
            "joint_names": list(robot.joint_names),
            "action_joint_names": [robot.joint_names[j] for j in robot.find_joints(config.actions.joint_pos.joint_names, preserve_order=True)[0]],
            "initial_state": robot_state(base),
            "trace": [],
            "approach_transitions": [],
            "max_settled_duration_s": 0.0,
            "max_push_leg_action_abs": 0.0,
            "max_applied_leg_command_abs_before_ready": 0.0,
            "support_pause_steps": 0,
            "slowed_approach_steps": 0,
            "nav_leg_support_steps": 0,
            "nav_leg_support_max_abs": 0.0,
        }
        if args.record_invalid_hand_contact_detail:
            report["record_invalid_hand_contact_detail"] = True
        if args.record_hand_contact_substeps:
            report["record_hand_contact_substeps"] = True
        if args.record_hand_contact_manifold:
            report["record_hand_contact_manifold"] = True
        if args.record_scene_runtime_observation:
            import omni.usd

            stage = omni.usd.get_context().get_stage()
            source_root = Path(box_push.__file__).resolve().parents[1]
            source_paths = {
                "diagnostic": Path(__file__),
                "scene_observer": Path(observe.__code__.co_filename),
                "piper_box_env_cfg": source_root / "config/go2_piper/box_env_cfg.py",
                "arx5_box_push_env_cfg": source_root / "config/go2_arx5/box_push_env_cfg.py",
                "flat_env_cfg": source_root / "config/go2_arx5/flat_env_cfg.py",
                "parent_env_cfg": source_root / "leggedmanip_lab_env_cfg.py",
                "box_push_reset": Path(box_push.__file__),
                "safe_approach_resource": piper_box_env_cfg.PIPER_SAFE_APPROACH_PATH,
            }
            report["scene_runtime_observation"] = observe(
                stage, config, base, args.seed, args.ground_filter_prim, source_paths
            )
            report["scene_runtime_observation_sha256"] = canonical_sha256(
                report["scene_runtime_observation"]
            )
        if args.rear_support_feedback:
            report.update(rear_support_feedback=True,
                          rear_support_feedback_parameters={
                              "base_height_below_m": 0.27,
                              "rear_foot_force_below_n": 2.0,
                              "trigger_consecutive_steps": 5,
                              "target_rear_force_n": 5.0,
                              "maximum_foot_downward_offset_m": 0.01,
                              "jacobian_damping_m_per_rad": 0.05,
                              "maximum_joint_offset_rad": 0.08,
                              "maximum_joint_target_change_per_step_rad": 0.03,
                          },
                          rear_support_feedback_steps=0,
                          rear_support_feedback_max_target_delta_rad=0.0)
        if args.front_foot_probe_offset_m:
            report.update(front_foot_probe_parameters={
                "start_push_s": 4.40,
                "end_push_s": 4.80,
                "pulse_shape": "symmetric triangle with peak at 4.60 s",
                "peak_world_foot_z_offset_m": args.front_foot_probe_offset_m,
                "jacobian_damping_m_per_rad": 0.05,
                "maximum_joint_offset_rad": 0.04,
                "maximum_joint_target_change_per_step_rad": 0.02,
            }, front_foot_probe_steps=0, front_foot_probe_max_target_delta_rad=0.0)
        if args.front_foot_hold_offset_m:
            report.update(front_foot_hold_parameters={
                "start_push_s": 4.40,
                "ramp_down_end_push_s": 4.60,
                "hold_end_push_s": 6.00,
                "ramp_out_end_push_s": 6.20,
                "peak_world_foot_z_offset_m": args.front_foot_hold_offset_m,
                "jacobian_damping_m_per_rad": 0.05,
                "maximum_joint_offset_rad": 0.04,
                "maximum_joint_target_change_per_step_rad": 0.02,
            }, front_foot_hold_steps=0, front_foot_hold_max_target_delta_rad=0.0)
        if args.front_foot_feedback:
            report.update(front_foot_feedback_parameters={
                "start_push_s": 4.40,
                "exit_ramp_start_push_s": 6.00,
                "end_push_s": 6.20,
                "maximum_world_foot_z_target_offset_m": 0.005,
                "pitch_risk_start_rad": 0.06,
                "pitch_risk_full_rad": 0.16,
                "world_y_angular_velocity_risk_start_rad_s": 0.02,
                "world_y_angular_velocity_risk_full_rad_s": 0.22,
                "rear_normal_force_share_risk_start": 0.30,
                "rear_normal_force_share_risk_full": 0.10,
                "maximum_offset_advance_per_step_m": 0.0005,
                "maximum_offset_release_per_step_m": 0.0005,
                "minimum_total_foot_normal_force_n": 20.0,
                "maximum_joint_offset_rad": 0.04,
                "maximum_joint_target_change_per_step_rad": 0.02,
            }, front_foot_feedback_steps=0, front_foot_feedback_max_target_delta_rad=0.0)
        if args.support_response_probe:
            report.update(support_probe_parameters={
                "trigger": "Five consecutive PUSH steps before motion_ready with base height below 0.27 m and RL or RR force below 2 N",
                "offset_world_foot_z_m": 0.003 if args.support_response_probe.endswith("up") else -0.003,
                "pulse_duration_s": 0.40,
                "pulse_peak_s": 0.20,
                "maximum_joint_offset_rad": 0.04,
                "maximum_joint_target_change_per_step_rad": 0.02,
            }, support_probe_trigger_s=None, support_probe_steps=0,
                support_probe_max_target_delta_rad=0.0)
        if args.hold_arm_on_support_warning:
            report.update(warning_arm_hold_trigger_s=None,
                          warning_arm_hold_steps=0,
                          warning_arm_hold_reference=None)
        if args.record_support_response_velocity:
            report["record_support_response_velocity"] = True
        if args.record_push_support_trace:
            report["support_trace"] = []
            report["support_foot_body_names"] = foot_names
            report["robot_body_mass_kg"] = body_masses.tolist()
        if args.record_settle_support_trace:
            report["settle_support_trace"] = []
        if args.record_push_contact_load_trace:
            report["joint_effort_limits"] = robot.data.joint_effort_limits[0].tolist()
        if args.record_base_contact_substeps:
            report["base_contact_substeps"] = []
            report["base_contact_substep_contract"] = {
                "physics_dt_s": float(base.physics_dt),
                "control_decimation": int(config.decimation),
                "sensor_history_length": int(foot_sensor.cfg.history_length),
                "sensor_update_period_s": float(foot_sensor.cfg.update_period),
                "threshold_n": float(config.terminations.base_contact.params["threshold"]),
            }
        if args.record_hand_contact_substeps:
            report["hand_contact_substeps"] = []
            report["hand_contact_substep_contract"] = {
                "physics_dt_s": float(base.physics_dt),
                "control_decimation": int(config.decimation),
                "sensor": "box_contact_hand",
                "sample_phase": "after_scene_update_before_control_step_termination",
            }
        if args.record_push_clock_trace:
            report["push_clock_trace"] = []
            report["push_clock_actions"] = []
            report["push_clock_contract"] = {
                "physics_dt_s": float(base.physics_dt),
                "control_decimation": int(config.decimation),
                "target_phase": "after_scene_write_data_to_sim_before_sim_step",
                "state_phase": "after_scene_update_before_control_step_termination",
                "joint_order": list(robot.joint_names),
            }
        if args.record_push_actuator_clock:
            leg_actuator = robot.actuators["base_legs"]
            if (leg_actuator.cfg.min_delay != 0 or leg_actuator.cfg.max_delay != 4
                    or leg_actuator.positions_delay_buffer.time_lags.shape != (1,)):
                raise RuntimeError("Unexpected GO2 leg actuator delay contract")
            report["push_actuator_clock_contract"] = {
                "actuator": "base_legs",
                "configured_min_delay_substeps": leg_actuator.cfg.min_delay,
                "configured_max_delay_substeps": leg_actuator.cfg.max_delay,
                "torque_phase": "after_scene_write_data_to_sim_before_sim_step",
            }
        if args.record_push_arm_clock:
            arm_actuators = {f"joint{i}": robot.actuators[f"joint{i}"] for i in range(1, 7)}
            if any(actuator.cfg.min_delay != 0 or actuator.cfg.max_delay != 4
                   or actuator.positions_delay_buffer.time_lags.shape != (1,)
                   for actuator in arm_actuators.values()):
                raise RuntimeError("Unexpected GO2 arm actuator delay contract")
            report["push_arm_clock_contract"] = {
                "actuators": list(arm_actuators),
                "configured_delay_range_substeps": [0, 4],
                "pulse_location": "after_PushArmIK_apply_before_delegate_process_actions",
            }
        if args.record_hand_contact_manifold:
            report["hand_contact_manifold_contract"] = {
                "prim_paths": list(hand_sensor.body_physx_view.prim_paths),
                "filter_prim_paths_expr": list(hand_sensor.cfg.filter_prim_paths_expr),
                "capacity_per_pair": int(hand_sensor.cfg.max_contact_data_count_per_prim),
                "source": "box_contact_hand.contact_physx_view.get_contact_data",
            }
        if args.record_base_contact_manifold:
            base_view = base_source_sensors["ground"].body_physx_view
            if list(base_view.prim_paths) != ["/World/envs/env_0/Robot/base"]:
                raise RuntimeError("Contact manifold view must contain only the base body")
            contact_offsets = base_view.get_contact_offsets()
            rest_offsets = base_view.get_rest_offsets()
            if contact_offsets.shape != (1, 1) or rest_offsets.shape != (1, 1):
                raise RuntimeError("Expected one base collision shape in the PhysX view")
            report["base_physx_contact_offset_m"] = float(contact_offsets[0, 0])
            report["base_physx_rest_offset_m"] = float(rest_offsets[0, 0])
            report["base_contact_manifold_capacity_per_pair"] = {
                name: sensor.cfg.max_contact_data_count_per_prim
                for name, sensor in base_source_sensors.items()
            }
        nav_hold_steps = 0
        settle_start_step = None
        settle_stable_steps = 0
        settle_initial_action = None
        last_nav_action = None
        last_nav_actor_input = None
        last_nav_actor_step = None
        last_nav_actor_action_replaced_by_settle_control = None
        nav_limit = math.ceil(args.nav_timeout_s / base.step_dt)
        settle_limit = math.ceil(args.handoff_settle_timeout_s / base.step_dt)
        phase = "nav"
        push_start_step = None
        push_steps = 0
        rear_support_condition_steps = 0
        support_probe_condition_steps = 0
        warning_arm_hold_condition_steps = 0
        if args.record_base_contact_substeps or args.record_hand_contact_substeps:
            original_scene_update = base.scene.update

            if args.record_push_clock_trace:
                original_scene_write = base.scene.write_data_to_sim

                def record_scene_write():
                    original_scene_write()
                    if phase == "push":
                        clock_row = {
                            "push_control_step": push_steps + 1,
                            "physics_substep": len(report["push_clock_trace"]) % config.decimation + 1,
                            "joint_target_before_sim": robot.data.joint_pos_target[0].tolist(),
                            "joint_pos_before_sim": robot.data.joint_pos[0].tolist(),
                        }
                        if args.record_push_actuator_clock:
                            clock_row.update(
                                leg_delay_substeps=int(leg_actuator.positions_delay_buffer.time_lags[0]),
                                computed_torque_before_sim=robot.data.computed_torque[0].tolist(),
                                applied_torque_before_sim=robot.data.applied_torque[0].tolist(),
                            )
                        if args.record_push_arm_clock:
                            clock_row["arm_delay_substeps"] = {
                                name: int(actuator.positions_delay_buffer.time_lags[0])
                                for name, actuator in arm_actuators.items()
                            }
                        report["push_clock_trace"].append(clock_row)

                base.scene.write_data_to_sim = record_scene_write

            def contact_manifold(sensor):
                forces, points, normals, separations, counts, starts = (
                    sensor.contact_physx_view.get_contact_data(dt=base.physics_dt)
                )
                if counts.shape != (1, 1) or starts.shape != (1, 1):
                    raise RuntimeError("Expected one body/filter contact pair")
                count, start = int(counts[0, 0]), int(starts[0, 0])
                if count < 0 or start < 0 or start + count > len(forces):
                    raise RuntimeError("Invalid PhysX contact buffer bounds")
                contacts = []
                for index in range(start, start + count):
                    if not (bool(torch.isfinite(forces[index]).all())
                            and bool(torch.isfinite(points[index]).all())
                            and bool(torch.isfinite(normals[index]).all())
                            and bool(torch.isfinite(separations[index]).all())):
                        raise RuntimeError("Non-finite PhysX contact data")
                    contacts.append({
                        "normal_force_n": float(forces[index, 0]),
                        "point_w": (points[index] - base.scene.env_origins[0]).tolist(),
                        "normal_w": normals[index].tolist(),
                        "separation_m": float(separations[index, 0]),
                    })
                return contacts

            def record_scene_update(dt):
                original_scene_update(dt)
                if phase != "push":
                    return
                if args.record_push_clock_trace:
                    if len(report["push_clock_trace"]) != len(report["hand_contact_substeps"]) + 1:
                        raise RuntimeError("PUSH target write and physics update clocks differ")
                    report["push_clock_trace"][-1]["joint_pos_after_update"] = (
                        robot.data.joint_pos[0].tolist()
                    )
                if args.record_base_contact_substeps:
                    contact_data = foot_sensor.data
                    source_forces = {
                        name: sensor.data.force_matrix_w[0, 0, 0].tolist()
                        for name, sensor in base_source_sensors.items()
                    }
                    row = {
                        "push_control_step": push_steps + 1,
                        "physics_substep": len(report["base_contact_substeps"]) % config.decimation + 1,
                        "net_force_w": contact_data.net_forces_w[0, base_sensor_id[0]].tolist(),
                        "net_force_history_w": (
                            contact_data.net_forces_w_history[0, :, base_sensor_id[0]].tolist()
                        ),
                        "filtered_force_w": source_forces,
                        "base_pos": (robot.data.root_pos_w[0] - base.scene.env_origins[0]).tolist(),
                        "base_quat": robot.data.root_quat_w[0].tolist(),
                    }
                    if args.record_base_contact_manifold:
                        row["contact_manifold"] = {
                            name: contact_manifold(sensor) for name, sensor in base_source_sensors.items()
                        }
                    report["base_contact_substeps"].append(row)
                if args.record_hand_contact_substeps:
                    hand_origin_box = quat_apply_inverse(
                        box_for_hand_trace.data.root_quat_w[0],
                        robot.data.body_pos_w[0, hand_ids[0]] - box_for_hand_trace.data.root_pos_w[0],
                    )
                    hand_row = {
                        "push_control_step": push_steps + 1,
                        "physics_substep": len(report["hand_contact_substeps"]) % config.decimation + 1,
                        "arm_approach_index": int(action_term.controller.safe_approach_index[0]),
                        "motion_ready": bool(action_term.controller.motion_ready[0]),
                        "foot_normal_forces_n": foot_sensor.data.net_forces_w[0, foot_ids, 2].tolist(),
                        "base_pos_w_m": robot.data.root_pos_w[0].tolist(),
                        "base_quat_w": robot.data.root_quat_w[0].tolist(),
                        "hand_body_origin_box_m": hand_origin_box.tolist(),
                        "hand_contact": invalid_hand_contact_detail(),
                    }
                    if args.record_hand_contact_manifold:
                        hand_row["contact_manifold"] = contact_manifold(hand_sensor)
                    report["hand_contact_substeps"].append(hand_row)

            base.scene.update = record_scene_update
        with torch.inference_mode():
            if args.skip_nav:
                action_term.controller.reset(None)
                action_term.phase = "push"
                phase = "push"
                push_start_step = int(base.episode_length_buf[0])
                report["handoff"] = {
                    "nav_steps": 0,
                    "nav_elapsed_s": 0.0,
                    "state": robot_state(base),
                    "controller": controller_state(action_term.controller),
                    "push_observation_shape": list(torch.cat([observation[name] for name in push_groups], dim=-1).shape),
                    "push_action_history": observation["policy"][0, 126:180].tolist(),
                    "last_nav_actor_input": None,
                    "last_nav_actor_step": None,
                    "last_nav_actor_action_replaced_by_settle_control": None,
                    "telemetry": read_only_telemetry(),
                }
            for step in range(nav_limit + settle_limit + math.ceil(12.0 / base.step_dt)):
                if video is not None and step % 2 == 0:
                    video.append_data(base.render())
                state = robot_state(base)
                if phase == "nav":
                    velocity, distance, yaw_error = nav_command(state, args.nav_goal_x, args.nav_min_translation_speed)
                    speed = math.hypot(*state["base_vel"][:2])
                    if settle_start_step is None:
                        nav_hold_steps = nav_hold_steps + 1 if distance < 0.05 and yaw_error < 0.10 and speed < 0.12 else 0
                        if nav_hold_steps * base.step_dt >= 0.4 and args.handoff_settle_stable_s:
                            settle_start_step = step
                            settle_initial_action = last_nav_action.clone()
                            report["nav_arrival"] = {
                                "elapsed_s": step * base.step_dt,
                                "state": state,
                                "telemetry": read_only_telemetry(),
                                "last_nav_leg_action": settle_initial_action[0, :12].tolist(),
                            }
                    readiness = None
                    if settle_start_step is not None:
                        velocity = [0.0, 0.0, 0.0]
                        arm = action_term.controller
                        arm_velocity = float(robot.data.joint_vel[0, arm.joint_ids].abs().amax())
                        arm_home_error = float((robot.data.joint_pos[0, arm.joint_ids]
                                                - arm.safe_approach_waypoints[0]).abs().amax())
                        angular_speed = math.sqrt(sum(value * value for value in state["base_omega"]))
                        supported_feet = int((foot_sensor.data.net_forces_w[0, foot_ids, 2] > 2.0).sum())
                        stable = (distance < 0.05 and yaw_error < 0.10 and speed < 0.06
                                  and angular_speed < 0.15 and arm_velocity < 0.12
                                  and arm_home_error < 0.15 and supported_feet == 4)
                        settle_stable_steps = settle_stable_steps + 1 if stable else 0
                        readiness = {
                            "distance_m": distance,
                            "yaw_error_rad": yaw_error,
                            "planar_speed_m_s": speed,
                            "angular_speed_rad_s": angular_speed,
                            "arm_speed_max_rad_s": arm_velocity,
                            "arm_home_error_max_rad": arm_home_error,
                            "supported_feet_gt_2n": supported_feet,
                            "consecutive_stable_s": settle_stable_steps * base.step_dt,
                        }
                    stable_gate_satisfied = (
                        settle_stable_steps * base.step_dt >= args.handoff_settle_stable_s
                        if settle_start_step is not None else nav_hold_steps * base.step_dt >= 0.4
                    )
                    ready_to_push = (
                        step - settle_start_step >= settle_limit
                        if settle_start_step is not None and args.force_push_after_settle_timeout
                        else stable_gate_satisfied
                    )
                    if ready_to_push:
                        before = robot_state(base)
                        action_term.controller.reset(None)
                        after = robot_state(base)
                        if before != after:
                            raise RuntimeError("Controller reset changed the physical scene")
                        if action_term.controller.contact_memory_left[0] != 0:
                            raise RuntimeError("Contact memory is nonzero at NAV handoff")
                        action_term.phase = "push"
                        action_term.pre_ready_leg_steps = 0
                        if args.hold_push_arm_at_handoff:
                            arm = action_term.controller
                            action_term.held_push_arm_command = (
                                (robot.data.joint_pos[:, arm.joint_ids] - robot.data.default_joint_pos[:, arm.joint_ids])
                                / arm.scale
                            ).clone()
                        phase = "push"
                        push_start_step = int(base.episode_length_buf[0])
                        report["handoff"] = {
                            "nav_steps": push_start_step,
                            "nav_elapsed_s": push_start_step * base.step_dt,
                            "settle_elapsed_s": (step - settle_start_step) * base.step_dt
                            if settle_start_step is not None else 0.0,
                            "readiness": readiness,
                            "stable_gate_satisfied": stable_gate_satisfied,
                            "forced_after_settle_timeout": args.force_push_after_settle_timeout,
                            "state": before,
                            "controller": controller_state(action_term.controller),
                            "push_observation_shape": list(torch.cat([observation[name] for name in push_groups], dim=-1).shape),
                            "push_action_history": observation["policy"][0, 126:180].tolist(),
                            "last_nav_actor_input": last_nav_actor_input,
                            "last_nav_actor_step": last_nav_actor_step,
                            "last_nav_actor_action_replaced_by_settle_control": last_nav_actor_action_replaced_by_settle_control,
                            "held_push_arm_command": action_term.held_push_arm_command.tolist()
                            if action_term.held_push_arm_command is not None else None,
                            "telemetry": read_only_telemetry(),
                        }
                    else:
                        actor_input = observation["policy"].clone()
                        actor_input[:, 180:189] = nav_velocity_history.flatten()
                        actor_input[:, 189:210] = nav_pose_history
                        if not torch.isfinite(actor_input).all():
                            raise RuntimeError("Non-finite NAV observation")
                        last_nav_actor_input = actor_input[0].tolist()
                        last_nav_actor_step = int(base.episode_length_buf[0])
                        nav_action = nav_actor(actor_input)
                        if nav_action.shape != (1, 18):
                            raise RuntimeError("Unexpected NAV actor output")
                        if settle_start_step is not None and args.handoff_settle_control == "default_posture":
                            ramp = max(0.0, 1.0 - (step - settle_start_step) * base.step_dt / 0.6)
                            nav_action = settle_initial_action * ramp
                        elif settle_start_step is not None and args.handoff_settle_control == "hold_last_nav":
                            nav_action = settle_initial_action.clone()
                        last_nav_actor_action_replaced_by_settle_control = (
                            settle_start_step is not None
                            and args.handoff_settle_control in ("default_posture", "hold_last_nav")
                        )
                        observation, _reward, done, _extras = env.step(nav_action)
                        if settle_start_step is not None and args.record_settle_support_trace:
                            post_state = terminal["state"] if bool(done[0]) else robot_state(base)
                            support = terminal["support_snapshot"] if bool(done[0]) else support_snapshot()
                            report["settle_support_trace"].append({
                                "settle_elapsed_s": (step + 1 - settle_start_step) * base.step_dt,
                                "nav_leg_action": nav_action[0, :12].tolist(),
                                "base_vel": post_state["base_vel"],
                                "base_omega": post_state["base_omega"],
                                **support,
                            })
                        if settle_start_step is None:
                            last_nav_action = nav_action.clone()
                        nav_velocity_history = torch.roll(nav_velocity_history, shifts=-1, dims=0)
                        nav_velocity_history[-1] = torch.tensor(velocity, device=args.device)
                        if step % 25 == 0:
                            report["trace"].append({"phase": "settle" if settle_start_step is not None else "nav",
                                                    "step": step, "distance": distance,
                                                    "yaw_error": yaw_error, "speed": speed,
                                                    "velocity_command": velocity,
                                                    "base_pos": state["base_pos"], "readiness": readiness})
                        if bool(done[0]):
                            report["outcome"] = "handoff_settle_terminated" if settle_start_step is not None else "nav_terminated"
                            break
                        if (settle_start_step is not None and step + 1 - settle_start_step >= settle_limit
                                and not args.force_push_after_settle_timeout):
                            report["outcome"] = "handoff_settle_timeout"
                            report["handoff_settle_readiness"] = readiness
                            break
                        if settle_start_step is None and step + 1 >= nav_limit:
                            report["outcome"] = "nav_timeout"
                            report["nav_terminal_command"] = velocity
                            break
                        continue
                if phase == "push":
                    actor_input = torch.cat([observation[name] for name in push_groups], dim=-1)
                    if actor_input.shape != (1, 226) or not torch.isfinite(actor_input).all():
                        raise RuntimeError("Invalid PUSH actor input at handoff")
                    if push_steps == 0:
                        if int(base.episode_length_buf[0]) != push_start_step:
                            raise RuntimeError("PUSH first input is not at the handoff step")
                        report["handoff"]["first_push_actor_input"] = actor_input[0].tolist()
                        report["handoff"]["first_push_actor_step"] = push_start_step
                        report["handoff"]["push_actor_input_groups"] = list(push_groups)
                        if args.record_leg_jacobian_trace:
                            report["handoff"]["leg_jacobians"] = leg_jacobian_snapshot()
                    push_action = push_actor(actor_input)
                    if push_action.shape != (1, 12):
                        raise RuntimeError("Unexpected PUSH actor output")
                    if args.record_push_clock_trace:
                        unmodified_action = push_action[0].tolist()
                        if args.push_action_pulse_step == push_steps + 1:
                            push_action = push_action.clone()
                            push_action[0, args.push_action_pulse_index] += args.push_action_pulse_delta
                        report["push_clock_actions"].append({
                            "push_control_step": push_steps + 1,
                            "actor_action": unmodified_action,
                            "routed_leg_action": push_action[0].tolist(),
                        })
                    nav_support_command_abs = 0.0
                    if args.nav_leg_support_until_ready:
                        nav_input = observation["policy"].clone()
                        nav_input[:, 180:189] = nav_velocity_history.flatten()
                        nav_input[:, 189:210] = nav_pose_history
                        if nav_input.shape != (1, 210) or not torch.isfinite(nav_input).all():
                            raise RuntimeError("Invalid NAV support actor input")
                        nav_support_action = nav_actor(nav_input)
                        if nav_support_action.shape != (1, 18) or not torch.isfinite(nav_support_action).all():
                            raise RuntimeError("Invalid NAV support actor output")
                        nav_support_command = nav_support_action[:, :12]
                        if agent_config.clip_actions is not None:
                            nav_support_command = nav_support_command.clamp(
                                -agent_config.clip_actions, agent_config.clip_actions
                            )
                        action_term.nav_support_command = nav_support_command.clone()
                        nav_support_command_abs = float(action_term.nav_support_command.abs().amax())
                    routed_action = torch.cat([push_action, torch.zeros((1, 6), device=args.device)], dim=1)
                    previous_approach_index = int(action_term.controller.safe_approach_index[0])
                    observation, _reward, done, _extras = env.step(routed_action)
                    push_steps += 1
                    controller = action_term.controller
                    if args.record_push_support_trace:
                        support_record = {
                            "push_elapsed_s": push_steps * base.step_dt,
                            **(terminal["support_snapshot"] if bool(done[0]) else support_snapshot()),
                        }
                        if args.record_recovery_decision_state:
                            next_actor_input = None
                            if not bool(done[0]):
                                next_input = torch.cat([observation[name] for name in push_groups], dim=-1)
                                if next_input.shape != (1, 226) or not bool(torch.isfinite(next_input).all()):
                                    raise RuntimeError("Invalid next PUSH actor input")
                                next_actor_input = next_input[0].tolist()
                            support_record["recovery_decision_state"].update(
                                actor_input_before_action=actor_input[0].tolist(),
                                actor_action_before_step=push_action[0].tolist(),
                                next_actor_input=next_actor_input,
                            )
                        if args.record_leg_jacobian_trace:
                            support_record["leg_jacobians"] = (
                                terminal["leg_jacobians"] if bool(done[0]) else leg_jacobian_snapshot()
                            )
                        report["support_trace"].append(support_record)
                        if args.rear_support_feedback:
                            forces = support_record["foot_normal_forces_n"]
                            active_condition = (
                                not support_record["motion_ready"]
                                and support_record["base_pos"][2] < 0.27
                                and any(forces[index] < 2.0 for index in rear_foot_indices)
                            )
                            rear_support_condition_steps = rear_support_condition_steps + 1 if active_condition else 0
                            if rear_support_condition_steps == 5 and not action_term.rear_support_feedback_pending:
                                action_term.rear_support_feedback_pending = True
                                report["rear_support_feedback_trigger_s"] = push_steps * base.step_dt
                            report["rear_support_feedback_steps"] = (
                                terminal["rear_support_feedback_steps"] if bool(done[0])
                                else action_term.rear_support_feedback_steps
                            )
                            report["rear_support_feedback_max_target_delta_rad"] = (
                                terminal["rear_support_feedback_max_target_delta_rad"] if bool(done[0])
                                else action_term.rear_support_feedback_max_target_delta_rad
                            )
                        if args.front_foot_probe_offset_m:
                            report["front_foot_probe_steps"] = (
                                terminal["front_foot_probe_steps"] if bool(done[0])
                                else action_term.front_foot_probe_steps
                            )
                            report["front_foot_probe_max_target_delta_rad"] = (
                                terminal["front_foot_probe_max_target_delta_rad"] if bool(done[0])
                                else action_term.front_foot_probe_max_target_delta_rad
                            )
                        if args.front_foot_hold_offset_m:
                            report["front_foot_hold_steps"] = (
                                terminal["front_foot_hold_steps"] if bool(done[0])
                                else action_term.front_foot_hold_steps
                            )
                            report["front_foot_hold_max_target_delta_rad"] = (
                                terminal["front_foot_hold_max_target_delta_rad"] if bool(done[0])
                                else action_term.front_foot_probe_max_target_delta_rad
                            )
                        if args.front_foot_feedback:
                            report["front_foot_feedback_steps"] = (
                                terminal["front_foot_feedback_steps"] if bool(done[0])
                                else action_term.front_foot_feedback_steps
                            )
                            report["front_foot_feedback_max_target_delta_rad"] = (
                                terminal["front_foot_feedback_max_target_delta_rad"] if bool(done[0])
                                else action_term.front_foot_feedback_max_target_delta_rad
                            )
                        if args.support_response_probe:
                            forces = support_record["foot_normal_forces_n"]
                            trigger_active = (
                                not support_record["motion_ready"]
                                and support_record["base_pos"][2] < 0.27
                                and any(forces[index] < 2.0 for index in rear_foot_indices)
                            )
                            support_probe_condition_steps = (
                                support_probe_condition_steps + 1 if trigger_active else 0
                            )
                            if (support_probe_condition_steps == 5 and not bool(done[0])
                                    and not action_term.support_probe_pending):
                                action_term.support_probe_pending = True
                                report["support_probe_trigger_s"] = push_steps * base.step_dt
                            report["support_probe_steps"] = (
                                terminal["support_probe_steps"] if bool(done[0])
                                else action_term.support_probe_steps
                            )
                            report["support_probe_max_target_delta_rad"] = (
                                terminal["support_probe_max_target_delta_rad"] if bool(done[0])
                                else action_term.support_probe_max_target_delta_rad
                            )
                        if args.hold_arm_on_support_warning:
                            forces = support_record["foot_normal_forces_n"]
                            warning_active = (
                                not support_record["motion_ready"]
                                and support_record["base_pos"][2] < 0.27
                                and any(forces[index] < 2.0 for index in rear_foot_indices)
                            )
                            warning_arm_hold_condition_steps = (
                                warning_arm_hold_condition_steps + 1 if warning_active else 0
                            )
                            if (warning_arm_hold_condition_steps == 5 and not bool(done[0])
                                    and action_term.warning_arm_hold_reference is None):
                                action_term.warning_arm_hold_reference = controller.reference.clone()
                                report["warning_arm_hold_trigger_s"] = push_steps * base.step_dt
                                report["warning_arm_hold_reference"] = (
                                    action_term.warning_arm_hold_reference[0].tolist()
                                )
                            report["warning_arm_hold_steps"] = (
                                terminal["warning_arm_hold_steps"] if bool(done[0])
                                else action_term.warning_arm_hold_steps
                            )
                        if support_record["support_pause_active"]:
                            report["support_pause_steps"] += 1
                            report.setdefault("first_support_pause_s", push_steps * base.step_dt)
                    report["slowed_approach_steps"] = (
                        terminal["slowed_approach_steps"] if bool(done[0])
                        else action_term.slowed_approach_steps
                    )
                    if args.nav_leg_support_until_ready:
                        report["nav_leg_support_steps"] = (
                            terminal["nav_leg_support_steps"] if bool(done[0])
                            else action_term.nav_leg_support_steps
                        )
                        report["nav_leg_support_max_abs"] = max(
                            report["nav_leg_support_max_abs"], nav_support_command_abs,
                        )
                        nav_velocity_history = torch.roll(nav_velocity_history, shifts=-1, dims=0)
                        nav_velocity_history[-1] = 0.0
                    telemetry = terminal.get("telemetry") if bool(done[0]) else read_only_telemetry()
                    push_leg_action_abs = float(push_action.abs().amax())
                    applied_leg_command_abs = float(action_term.joint_commands[0, controller.leg_slots].abs().amax())
                    report["max_push_leg_action_abs"] = max(report["max_push_leg_action_abs"], push_leg_action_abs)
                    if not bool(controller.motion_ready[0]):
                        report["max_applied_leg_command_abs_before_ready"] = max(
                            report["max_applied_leg_command_abs_before_ready"], applied_leg_command_abs
                        )
                    report["max_settled_duration_s"] = max(
                        report["max_settled_duration_s"], telemetry["settled_duration_s"]
                    )
                    if telemetry["arm_approach"]["index"] != previous_approach_index:
                        report["approach_transitions"].append({
                            "push_elapsed_s": push_steps * base.step_dt,
                            "from_index": previous_approach_index,
                            "to_index": telemetry["arm_approach"]["index"],
                            "telemetry": telemetry,
                        })
                    for key, observed in (
                        ("safe_approach_complete_s", bool(controller.safe_approach_complete[0])),
                        ("motion_ready_s", bool(controller.motion_ready[0])),
                        ("drive_contact_s", bool(controller.drive_contact[0])),
                    ):
                        if observed and key not in report:
                            report[key] = push_steps * base.step_dt
                    if step % 25 == 0 or push_steps == 1:
                        report["trace"].append({"phase": "push", "step": step,
                                                "push_elapsed_s": push_steps * base.step_dt,
                                                "base_pos": state["base_pos"],
                                                "base_quat": state["base_quat"],
                                                "box_pos": state["box_pos"],
                                                "controller": controller_state(action_term.controller),
                                                "push_leg_action_max_abs": push_leg_action_abs,
                                                "applied_leg_command_max_abs": applied_leg_command_abs,
                                                "telemetry": telemetry})
                    if bool(done[0]):
                        report["outcome"] = "push_terminated"
                        break
                    if push_steps * base.step_dt >= 12.0:
                        report["outcome"] = "push_budget_exhausted"
                        break
            else:
                report["outcome"] = "loop_limit"
        report["terminal"] = terminal or {"state": robot_state(base), "step": int(base.episode_length_buf[0])}
        report["push_executed_steps"] = push_steps
        report["push_elapsed_s"] = push_steps * base.step_dt
        if args.record_scene_runtime_observation and "handoff" in report:
            entry = report["handoff"]
            report["handoff_entry_observation"] = {
                key: entry[key] for key in (
                    "nav_steps", "state", "controller", "push_action_history",
                    "last_nav_actor_input", "last_nav_actor_step"
                )
            }
            report["handoff_entry_observation_sha256"] = canonical_sha256(
                report["handoff_entry_observation"]
            )
        if args.record_base_contact_substeps and len(report["base_contact_substeps"]) != push_steps * config.decimation:
            raise RuntimeError("Missing or duplicate PUSH physics-substep records")
        if args.record_push_clock_trace and (
                len(report["push_clock_trace"]) != push_steps * config.decimation
                or len(report["push_clock_actions"]) != push_steps
                or any("joint_pos_after_update" not in row for row in report["push_clock_trace"])):
            raise RuntimeError("Incomplete PUSH action/target/physics clock trace")
        if args.record_push_arm_clock:
            if action_term.arm_command_pulse_count != int(args.push_arm_command_pulse_step is not None):
                raise RuntimeError("Arm command pulse did not execute exactly once")
            report["push_arm_command_pulse_count"] = action_term.arm_command_pulse_count
        report["terminal_telemetry"] = terminal.get("telemetry") if terminal else read_only_telemetry()
        if not terminal:
            box = base.scene["box"]
            goal = box_push.push_target(base)
            report["terminal"].update(
                box_goal_error_m=float(torch.linalg.vector_norm(goal[0, :2] - box.data.root_pos_w[0, :2])),
                box_speed_m_s=float(torch.linalg.vector_norm(box.data.root_lin_vel_w[0])),
            )
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        with args.output_json.open("x", encoding="utf-8") as stream:
            json.dump(report, stream, indent=2, allow_nan=False)
        print("NAV_PUSH_HANDOFF_DIAGNOSTIC=" + str(args.output_json), flush=True)
    finally:
        if video is not None:
            video.close()
        env.close()


try:
    main()
except BaseException:
    traceback.print_exc()
    raise
finally:
    launcher.app.close()
