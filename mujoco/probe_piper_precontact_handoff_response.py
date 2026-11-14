"""Probe native pose-IK contact continuation from a NAV precontact state."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from types import MethodType

import mujoco
import numpy as np

from check_piper_arm_precontact_motion import (
    _base_hold_velocity, _base_pose, _candidate_end_effector_world_pose,
    _slerp_quaternion, _world_pose_to_wbc_command,
)
from check_piper_startup import sha256
from reconfigurable_navigation.piper_locomotion_runtime import DEPLOY
from reconfigurable_navigation.locomotion_runtime import POLICY_MJ_INDICES
from reconfigurable_navigation.reachability import PiperPositionReachabilityOracle, ReachabilityQuery
from reconfigurable_navigation.reachability.clearance import ARM_BODY_NAMES, PiperArmClearanceChecker, PiperSelfClearanceChecker
from reconfigurable_navigation.reachability.contact_geometry import PiperContactGeometryReader, native_push_orientation
from reconfigurable_navigation.reachability.scenes import make_movable_box_navigation_runtime
from reconfigurable_navigation.reachability.support import PiperQuasiStaticSupportChecker
from reconfigurable_navigation.reachability.contact_limits import ContactLimitProvenance


SCRIPT = Path(__file__).resolve()


class _DiagnosticStop(Exception):
    pass


def _simulate_target_with_arm_gravity(runtime, target_mj):
    for _ in range(runtime.decimation):
        joint_position = runtime.data.qpos[runtime.joint_qpos_adr]
        joint_velocity = runtime.data.qvel[runtime.joint_dof_adr]
        torque = runtime.kp * (target_mj - joint_position) - runtime.kd * joint_velocity
        torque[12:] += runtime.diagnostic_arm_gravity_scale * runtime.data.qfrc_bias[runtime.joint_dof_adr[12:]]
        runtime.data.ctrl[:] = np.clip(torque, runtime.ctrl_low, runtime.ctrl_high)
        for _ in range(runtime.physics_substeps):
            mujoco.mj_step(runtime.model, runtime.data)
            if runtime.on_physics_step is not None:
                runtime.on_physics_step()


def _simulate_target_with_arm_bias(runtime, target_mj):
    runtime.diagnostic_gravity_data.qpos[:] = runtime.data.qpos
    runtime.diagnostic_gravity_data.qvel.fill(0.0)
    mujoco.mj_forward(runtime.model, runtime.diagnostic_gravity_data)
    biased = target_mj.copy()
    offset = runtime.diagnostic_arm_bias_scale * (
        runtime.diagnostic_gravity_data.qfrc_bias[runtime.joint_dof_adr[12:]] / runtime.kp[12:]
    )
    biased[12:] = np.clip(
        target_mj[12:] + np.clip(offset, -runtime.diagnostic_arm_bias_limit, runtime.diagnostic_arm_bias_limit),
        runtime.joint_low[12:], runtime.joint_high[12:],
    )
    runtime.diagnostic_arm_target = biased[12:].copy()
    runtime.diagnostic_original_simulate_target(biased)


def _simulate_target_with_arm_ik(runtime, target_mj):
    runtime.diagnostic_gravity_data.qpos[:] = runtime.data.qpos
    runtime.diagnostic_gravity_data.qvel.fill(0.0)
    mujoco.mj_forward(runtime.model, runtime.diagnostic_gravity_data)
    reference = runtime.diagnostic_arm_start + runtime.diagnostic_arm_fraction * (
        runtime.diagnostic_arm_goal - runtime.diagnostic_arm_start
    )
    target_mj[12:] = np.clip(
        reference + runtime.diagnostic_gravity_data.qfrc_bias[runtime.joint_dof_adr[12:]] / runtime.kp[12:],
        runtime.joint_low[12:], runtime.joint_high[12:],
    )
    runtime.diagnostic_arm_target = target_mj[12:].copy()
    runtime.diagnostic_original_simulate_target(target_mj)


def _stop_reason(
    contact_samples, support, box_displacement: float, self_clearance: float,
    nonhand_clearance: float, *, observe_support_only: bool = False,
    finger_clearance: float = float("inf"),
) -> str | None:
    if contact_samples:
        return "first_box_contact"
    if box_displacement > 0.001:
        return "box_displacement_exceeded"
    if self_clearance < 0.05:
        return "self_clearance_lost"
    if nonhand_clearance < 0.05:
        return "nonhand_clearance_lost"
    if observe_support_only:
        return "baseline_finger_clearance_lost" if finger_clearance < 0.1 else None
    if len(support.supporting_feet) < 3 or support.support_margin is None or support.support_margin < 0.02:
        return "support_lost"
    return None


def _load_report(path: Path) -> tuple[dict[str, object], dict[str, object]]:
    with path.open() as source:
        report = json.load(source)
    for source_path, expected in report.get("source_sha256", {}).items():
        if sha256(Path(source_path)) != expected:
            raise ValueError(f"Source hash mismatch: {source_path}")
    result = report.get("result")
    state = result.get("candidate", {}).get("precontact_state") if isinstance(result, dict) else None
    if not isinstance(result, dict) or not isinstance(state, dict):
        raise ValueError("Input must contain a NAV precontact state")
    return report, result


def _restore(runtime, state: dict[str, object]) -> None:
    for field in ("qpos", "qvel", "ctrl"):
        values = np.asarray(state[field], dtype=np.float64)
        destination = getattr(runtime.data, field)
        if values.shape != destination.shape or not np.isfinite(values).all():
            raise ValueError(f"Invalid precontact state field: {field}")
        destination[:] = values
    runtime.data.time = float(state["time"])
    mujoco.mj_forward(runtime.model, runtime.data)


def _solve_target(runtime, result, target_local: np.ndarray, random_starts: int) -> tuple[object, np.ndarray, np.ndarray]:
    box = runtime.model.geom("reachability_box").id
    base = runtime.env.robot_qpos_adr
    rotation = runtime.data.xmat[runtime.base_id].reshape(3, 3)
    base_pose = np.array([
        runtime.data.qpos[base], runtime.data.qpos[base + 1],
        np.arctan2(rotation[1, 0], rotation[0, 0]),
    ])
    box_rotation = runtime.data.geom_xmat[box].reshape(3, 3)
    box_quaternion = np.empty(4)
    mujoco.mju_mat2Quat(box_quaternion, box_rotation.ravel())
    target_world = runtime.data.geom_xpos[box] + box_rotation @ target_local
    oracle = PiperPositionReachabilityOracle(runtime)
    center = np.asarray(result["candidate"]["joint_solution"], dtype=np.float64)
    starts = [center]
    generator = np.random.default_rng(647)
    starts.extend(
        np.clip(
            center + generator.normal(0.0, [0.35, 0.35, 0.35, 0.5, 0.5, 0.25]),
            oracle.arm_low + 0.05,
            oracle.arm_high - 0.05,
        )
        for _ in range(random_starts)
    )
    candidates = [
        oracle.solve(
            ReachabilityQuery(base_pose, target_world),
            initial_joint_positions=start,
            target_quaternion=native_push_orientation(box_quaternion),
        )
        for start in starts
    ]
    feasible = [candidate for candidate in candidates if candidate.kinematic_feasible]
    if not feasible:
        raise ValueError("No native pose-IK candidate for requested continuation target")
    candidate = min(feasible, key=lambda item: (item.position_error, item.orientation_error))
    return candidate, target_world, base_pose


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-json", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--target-local", type=float, nargs=3, default=(-0.1, 0.0, 0.02))
    parser.add_argument("--random-starts", type=int, default=64)
    parser.add_argument("--physics-substeps", type=int, choices=(1, 2, 4), default=1)
    parser.add_argument("--ramp-steps", type=int, default=80)
    parser.add_argument("--ramp-fraction-limit", type=float, default=1.0)
    parser.add_argument("--position-axis-fractions", type=float, nargs=3, default=(1.0, 1.0, 1.0))
    parser.add_argument("--orientation-fraction-limit", type=float)
    parser.add_argument("--orientation-lead-steps", type=int, default=0)
    parser.add_argument("--hold-steps", type=int, default=40)
    parser.add_argument("--observe-support-steps", type=int, default=0)
    parser.add_argument("--far-field-command-offset", type=float, nargs=3, default=(0.0, 0.0, 0.0))
    parser.add_argument("--far-field-native-orientation", action="store_true")
    parser.add_argument("--preparation-steps", type=int, default=0)
    parser.add_argument("--far-field-arm-kp-scale", type=float, default=1.0)
    parser.add_argument("--arm-gravity-compensation", action="store_true")
    parser.add_argument("--arm-gravity-compensation-scale", type=float, default=1.0)
    parser.add_argument("--arm-target-bias-scale", type=float, default=0.0)
    parser.add_argument("--arm-target-bias-limit", type=float, default=0.1)
    parser.add_argument("--arm-ik-reference", action="store_true")
    parser.add_argument("--arm-ik-pose-reference", action="store_true")
    parser.add_argument("--minimum-finger-standoff", type=float, default=0.0)
    parser.add_argument("--position-feedback-gain", type=float, default=0.0)
    parser.add_argument("--position-feedback-max-meters", type=float, default=0.04)
    parser.add_argument("--base-hold", action="store_true")
    parser.add_argument("--base-forward-offset", type=float, default=0.0)
    parser.add_argument("--diagnose-final-pose-ik", action="store_true")
    parser.add_argument("--provenance-source", required=True)
    parser.add_argument("--provenance-purpose", required=True)
    parser.add_argument("--calibration-status", choices=("diagnostic_only",), required=True)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error(f"Refusing to overwrite {args.output_json}")
    if args.random_starts < 0 or args.ramp_steps < 1 or args.hold_steps < 0 or args.orientation_lead_steps < 0:
        parser.error("Search and step counts must be non-negative; ramp must be positive")
    if not np.isfinite(args.ramp_fraction_limit) or not 0.0 < args.ramp_fraction_limit <= 1.0:
        parser.error("Ramp fraction limit must be finite and in (0, 1]")
    position_axis_fractions = np.asarray(args.position_axis_fractions, dtype=np.float64)
    if not np.isfinite(position_axis_fractions).all() or np.any(
        (position_axis_fractions < 0.0) | (position_axis_fractions > 1.0)
    ):
        parser.error("Position axis fractions must be finite and in [0, 1]")
    if args.orientation_fraction_limit is not None and (
        not np.isfinite(args.orientation_fraction_limit)
        or not 0.0 <= args.orientation_fraction_limit <= 1.0
    ):
        parser.error("Orientation fraction limit must be finite and in [0, 1]")
    if not 0 <= args.observe_support_steps <= 200 or not 0 <= args.preparation_steps <= 200:
        parser.error("Support observation and preparation must each be between 0 and 200 control steps")
    if args.observe_support_steps and args.preparation_steps:
        parser.error("Support-only observation and approach preparation are mutually exclusive")
    if args.diagnose_final_pose_ik and args.observe_support_steps:
        parser.error("Final pose IK diagnosis requires an approach trajectory")
    if args.arm_ik_reference and (args.observe_support_steps or not args.preparation_steps or args.arm_gravity_compensation):
        parser.error("Arm IK reference requires preparation and cannot combine with other arm diagnostics")
    if (not np.isfinite(args.arm_target_bias_scale) or not 0.0 <= args.arm_target_bias_scale <= 1.0
            or not np.isfinite(args.arm_target_bias_limit) or not 0.0 < args.arm_target_bias_limit <= 0.1
            or (args.arm_target_bias_scale and (not args.preparation_steps or args.arm_ik_reference
                                                or args.arm_gravity_compensation or args.observe_support_steps))):
        parser.error("Arm target bias requires preparation, scale in [0, 1], limit in (0, 0.1], and no other arm diagnostic")
    if args.arm_ik_pose_reference and not args.arm_ik_reference:
        parser.error("Arm IK pose reference requires arm IK reference")
    if (not np.isfinite(args.minimum_finger_standoff) or args.minimum_finger_standoff < 0.0
            or (args.minimum_finger_standoff and not args.arm_ik_pose_reference)):
        parser.error("Positive finger standoff requires pose IK and must be finite")
    if (not np.isfinite(args.arm_gravity_compensation_scale)
            or not 0.0 < args.arm_gravity_compensation_scale <= 1.0
            or (args.arm_gravity_compensation_scale != 1.0 and not args.arm_gravity_compensation)):
        parser.error("Arm gravity scale must be in (0, 1] and requires gravity compensation")
    if (not np.isfinite(args.far_field_arm_kp_scale) or args.far_field_arm_kp_scale <= 0.0
            or (args.far_field_arm_kp_scale != 1.0 and not args.observe_support_steps)):
        parser.error("Arm KP scaling requires fixed-pose far-field support observation and a positive finite scale")
    far_field_offset = np.asarray(args.far_field_command_offset, dtype=np.float64)
    if (not np.isfinite(far_field_offset).all() or np.linalg.norm(far_field_offset) > 0.03
            or (np.any(far_field_offset) and args.observe_support_steps != 200)):
        parser.error("Far-field offset requires 200 observation steps and a finite offset at most 30 mm")
    if args.far_field_native_orientation and args.observe_support_steps != 200:
        parser.error("Far-field native orientation requires 200 observation steps")
    if (not np.isfinite(args.position_feedback_gain) or args.position_feedback_gain < 0.0
            or not np.isfinite(args.position_feedback_max_meters) or args.position_feedback_max_meters < 0.0):
        parser.error("Position feedback gain and bound must be finite and non-negative")
    if (not np.isfinite(args.base_forward_offset) or not 0.0 <= args.base_forward_offset <= 0.03
            or (args.base_forward_offset and not args.base_hold)):
        parser.error("Base forward offset requires base hold and must be in [0, 0.03] meters")
    target_local = np.asarray(args.target_local, dtype=np.float64)
    if not np.isfinite(target_local).all():
        parser.error("Target must be finite")
    provenance = ContactLimitProvenance(
        source=args.provenance_source,
        purpose=args.provenance_purpose,
        calibration_status=args.calibration_status,
    )
    report, result = _load_report(args.input_json)
    scene = result["scene"]
    runtime = make_movable_box_navigation_runtime(
        seed=int(result["seed"]),
        box_position=np.asarray(scene["requested_box_position"], dtype=np.float64),
        box_size=np.asarray(scene["box_size"], dtype=np.float64),
        box_yaw=float(scene["requested_box_yaw"]),
        box_mass=float(scene["box_mass"]),
        config_path=DEPLOY / "config_wbc.yaml",
        physics_substeps=args.physics_substeps,
    )
    _restore(runtime, result["candidate"]["precontact_state"])
    runtime.diagnostic_arm_gravity_scale = args.arm_gravity_compensation_scale
    runtime.diagnostic_arm_bias_scale = args.arm_target_bias_scale
    runtime.diagnostic_arm_bias_limit = args.arm_target_bias_limit
    runtime.kp[12:] *= args.far_field_arm_kp_scale
    candidate, target_world, base_pose = _solve_target(runtime, result, target_local, args.random_starts)
    end_effector = runtime.model.body("end_effector").id
    start_position = runtime.data.xpos[end_effector].copy()
    start_quaternion = runtime.data.xquat[end_effector].copy()
    target_position, target_quaternion = _candidate_end_effector_world_pose(runtime, candidate.joint_solution)
    box = runtime.model.geom("reachability_box").id
    box_body = int(runtime.model.geom_bodyid[box])
    box_joint = int(runtime.model.body_jntadr[box_body])
    box_qpos = int(runtime.model.jnt_qposadr[box_joint])
    box_dof = int(runtime.model.jnt_dofadr[box_joint])
    reader = PiperContactGeometryReader(runtime)
    support_checker = PiperQuasiStaticSupportChecker(runtime)
    if (args.observe_support_steps or args.preparation_steps) and reader.read()["minimum_finger_clearance"] < 0.1:
        raise ValueError("Fixed-pose preparation requires at least 100 mm initial finger clearance")
    self_checker = PiperSelfClearanceChecker(runtime)
    nonhand_checker = PiperArmClearanceChecker(
        runtime, protected_body_names=frozenset({"reachability_box"}),
        arm_body_names=ARM_BODY_NAMES - reader.region.hand_bodies,
    )
    samples = []
    support_trace = []
    box_trace = []
    clearance_trace = []
    initial_box = runtime.data.qpos[box_qpos : box_qpos + 3].copy()
    initial_base = runtime.data.qpos[runtime.env.robot_qpos_adr : runtime.env.robot_qpos_adr + 3].copy()
    initial_base_quaternion = runtime.data.xquat[runtime.base_id].copy()
    stop_reason = None
    in_preparation = bool(args.preparation_steps)
    preparation_support = None
    preparation_base_quaternion = None
    preparation_candidate_pose = None
    hold_base_pose = None
    last_command_position = None
    far_field_settled_position = None
    maximum_feedback_correction = 0.0
    feedback_saturated_steps = 0
    maximum_arm_action = 0.0
    arm_action_clipped_steps = 0
    arm_joint_target_clipped_steps = 0
    maximum_arm_joint_tracking_error = 0.0
    final_arm_joint_tracking_error = None
    arm_torque_saturated_substeps = np.zeros(6, dtype=int)
    policy_target_trace = []
    target_data = mujoco.MjData(runtime.model)

    def record_arm_tracking():
        nonlocal maximum_arm_action, arm_action_clipped_steps
        nonlocal arm_joint_target_clipped_steps, maximum_arm_joint_tracking_error, final_arm_joint_tracking_error
        action = runtime.last_action
        maximum_arm_action = max(maximum_arm_action, float(np.max(np.abs(action[12:]))))
        arm_action_clipped_steps += int(np.any(np.abs(action[12:]) >= runtime.action_clip - 1e-6))
        raw_target = runtime.default_qpos + action[POLICY_MJ_INDICES] * runtime.action_scale
        arm_joint_target_clipped_steps += int(np.any(
            (raw_target[12:] < runtime.joint_low[12:]) | (raw_target[12:] > runtime.joint_high[12:])
        ))
        target = np.clip(raw_target, runtime.joint_low, runtime.joint_high)
        actual = runtime.data.qpos[runtime.joint_qpos_adr]
        maximum_arm_joint_tracking_error = max(
            maximum_arm_joint_tracking_error, float(np.max(np.abs(target[12:] - actual[12:])))
        )
        final_arm_joint_tracking_error = (target[12:] - actual[12:]).tolist()
        target_data.qpos[:] = runtime.data.qpos
        target_data.qpos[runtime.joint_qpos_adr[12:]] = target[12:]
        mujoco.mj_forward(runtime.model, target_data)
        policy_target_trace.append({
            "time": float(runtime.data.time),
            "policy_target_world": target_data.xpos[end_effector].tolist(),
            "actual_world": runtime.data.xpos[end_effector].tolist(),
            "command_world": last_command_position.tolist() if last_command_position is not None else None,
            "executed_arm_joint_target": (
                runtime.diagnostic_arm_target.tolist() if args.arm_ik_reference or args.arm_target_bias_scale else None
            ),
        })

    def record_executed_arm_action():
        if args.arm_ik_reference:
            runtime.last_action[12:] = (
                runtime.diagnostic_arm_target - runtime.default_qpos[12:]
            ) / runtime.action_scale[12:]
            runtime.history[-1] = runtime._single_observation()

    def wbc_command(position, quaternion):
        nonlocal last_command_position, maximum_feedback_correction, feedback_saturated_steps, stop_reason
        if args.arm_ik_pose_reference:
            solution = runtime.diagnostic_pose_oracle.solve(
                ReachabilityQuery(_base_pose(runtime, base_pose), position),
                initial_joint_positions=runtime.diagnostic_arm_goal,
                target_quaternion=quaternion,
            )
            if not solution.kinematic_feasible:
                stop_reason = "arm_ik_pose_unreachable"
                raise _DiagnosticStop
            runtime.diagnostic_arm_goal = solution.joint_solution.copy()
            runtime.diagnostic_arm_fraction = 1.0
        correction = args.position_feedback_gain * (position - runtime.data.xpos[end_effector])
        correction_norm = float(np.linalg.norm(correction))
        if correction_norm > args.position_feedback_max_meters:
            feedback_saturated_steps += 1
            correction *= args.position_feedback_max_meters / correction_norm
        maximum_feedback_correction = max(maximum_feedback_correction, float(np.linalg.norm(correction)))
        last_command_position = position + correction
        return _world_pose_to_wbc_command(runtime, position + correction, quaternion)

    def on_physics_step():
        nonlocal stop_reason
        if not in_preparation and not args.observe_support_steps:
            arm_torque_saturated_substeps[:] += (
                (runtime.data.ctrl[12:] <= runtime.ctrl_low[12:] + 1e-6)
                | (runtime.data.ctrl[12:] >= runtime.ctrl_high[12:] - 1e-6)
            )
        measurement = reader.read()
        support = support_checker.evaluate(required_margin=0.02)
        self_clearance = self_checker.evaluate_current_configuration(required_clearance=0.05).minimum_clearance
        nonhand_clearance = nonhand_checker.evaluate_current_configuration(required_clearance=0.05).minimum_clearance
        clearance_trace.append({
            "time": float(runtime.data.time),
            "self": self_clearance,
            "nonhand_box": nonhand_clearance,
            "finger_box": measurement["minimum_finger_clearance"],
            "orientation_error": measurement["native_push_orientation_error"],
            "end_effector_error_world": (
                target_world - np.asarray(measurement["end_effector_world"])
            ).tolist(),
            "base_displacement_world": (
                runtime.data.qpos[runtime.env.robot_qpos_adr : runtime.env.robot_qpos_adr + 3] - initial_base
            ).tolist(),
            "end_effector_to_target": float(np.linalg.norm(
                np.asarray(measurement["end_effector_world"]) - target_world
            )),
            "command_position_world": (
                last_command_position.tolist() if last_command_position is not None and not in_preparation else None
            ),
            "policy_end_effector_command": (
                runtime.ee_command.tolist() if last_command_position is not None and not in_preparation else None
            ),
            "end_effector_to_command": (
                float(np.linalg.norm(runtime.data.xpos[end_effector] - last_command_position))
                if last_command_position is not None and not in_preparation else None
            ),
            "base_rotation_from_initial_radians": float(2.0 * np.arccos(np.clip(
                abs(initial_base_quaternion @ runtime.data.xquat[runtime.base_id]), 0.0, 1.0,
            ))),
        })
        box_trace.append({
            "time": float(runtime.data.time),
            "position": runtime.data.qpos[box_qpos : box_qpos + 3].tolist(),
            "velocity": runtime.data.qvel[box_dof : box_dof + 6].tolist(),
        })
        support_trace.append({
            "time": float(runtime.data.time),
            "phase": "preparation" if in_preparation or args.observe_support_steps else "approach",
            "feet": list(support.supporting_feet),
            "margin": support.support_margin,
        })
        samples.extend(
            {"time": float(runtime.data.time), "sample": sample}
            for sample in measurement["contact_samples"]
        )
        stop_reason = _stop_reason(
            measurement["contact_samples"], support,
            float(np.linalg.norm(runtime.data.qpos[box_qpos : box_qpos + 3] - initial_box)),
            self_clearance, nonhand_clearance,
            observe_support_only=bool(args.observe_support_steps) or in_preparation,
            finger_clearance=measurement["minimum_finger_clearance"],
        )
        if (stop_reason is None and not in_preparation and args.minimum_finger_standoff
                and measurement["minimum_finger_clearance"] < args.minimum_finger_standoff):
            stop_reason = "finger_standoff_lost"
        if (stop_reason is None and (args.arm_gravity_compensation or args.arm_ik_reference or args.arm_target_bias_scale)
                and last_command_position is not None
                and np.linalg.norm(runtime.data.xpos[end_effector] - last_command_position) > 0.05):
            stop_reason = ("arm_ik_command_deviation" if args.arm_ik_reference else
                           "arm_bias_command_deviation" if args.arm_target_bias_scale else "arm_gravity_command_deviation")
        if stop_reason is not None:
            raise _DiagnosticStop

    runtime.on_physics_step = on_physics_step
    try:
        if args.observe_support_steps:
            for step in range(args.observe_support_steps):
                if step == 100:
                    far_field_settled_position = runtime.data.xpos[end_effector].copy()
                    if args.arm_gravity_compensation:
                        runtime._simulate_target = MethodType(_simulate_target_with_arm_gravity, runtime)
                commanded_position = start_position + (far_field_offset if step >= 100 else 0.0)
                if step >= 100:
                    last_command_position = commanded_position.copy()
                commanded_quaternion = (
                    _slerp_quaternion(start_quaternion, target_quaternion, (step - 99) / 100)
                    if args.far_field_native_orientation and step >= 100 else start_quaternion
                )
                runtime.step(np.zeros(3), _world_pose_to_wbc_command(runtime, commanded_position, commanded_quaternion))
                record_arm_tracking()
        else:
            for _ in range(args.preparation_steps):
                runtime.step(np.zeros(3), _world_pose_to_wbc_command(runtime, start_position, start_quaternion))
            if in_preparation:
                preparation_support = support_checker.evaluate(required_margin=0.02)
                in_preparation = False
                if not preparation_support.safe:
                    stop_reason = "preparation_support_lost"
                    raise _DiagnosticStop
                if args.arm_gravity_compensation:
                    runtime._simulate_target = MethodType(_simulate_target_with_arm_gravity, runtime)
                if args.arm_target_bias_scale:
                    runtime.diagnostic_gravity_data = mujoco.MjData(runtime.model)
                    runtime.diagnostic_original_simulate_target = runtime._simulate_target
                    runtime._simulate_target = MethodType(_simulate_target_with_arm_bias, runtime)
                if args.arm_ik_reference:
                    runtime.diagnostic_arm_start = runtime.data.qpos[runtime.joint_qpos_adr[12:]].copy()
                    runtime.diagnostic_arm_goal = candidate.joint_solution.copy()
                    runtime.diagnostic_arm_fraction = 0.0
                    if args.arm_ik_pose_reference:
                        runtime.diagnostic_arm_goal = runtime.diagnostic_arm_start.copy()
                        runtime.diagnostic_pose_oracle = PiperPositionReachabilityOracle(runtime)
                    runtime.diagnostic_gravity_data = mujoco.MjData(runtime.model)
                    runtime.diagnostic_original_simulate_target = runtime._simulate_target
                    runtime._simulate_target = MethodType(_simulate_target_with_arm_ik, runtime)
                preparation_base_quaternion = runtime.data.xquat[runtime.base_id].copy()
                preparation_candidate_pose, _ = _candidate_end_effector_world_pose(runtime, candidate.joint_solution)
            if args.base_hold:
                hold_base_pose = _base_pose(runtime, base_pose)
                direction = target_position[:2] - start_position[:2]
                if args.base_forward_offset:
                    if np.linalg.norm(direction) < 1e-9:
                        parser.error("Base forward offset requires a nonzero planar target displacement")
                    hold_base_pose[:2] += args.base_forward_offset * direction / np.linalg.norm(direction)

            def base_velocity():
                if hold_base_pose is None:
                    return np.zeros(3)
                return _base_hold_velocity(
                    hold_base_pose, _base_pose(runtime, base_pose),
                    position_gain=2.0, yaw_gain=2.0,
                    maximum_linear_speed=0.05, maximum_yaw_rate=0.1,
                )

            orientation_fraction_limit = (
                args.ramp_fraction_limit if args.orientation_fraction_limit is None
                else args.orientation_fraction_limit
            )
            for orientation_fraction in np.linspace(
                0.0, orientation_fraction_limit, args.orientation_lead_steps
            ):
                if args.arm_ik_reference and not args.arm_ik_pose_reference:
                    runtime.diagnostic_arm_fraction = 0.0
                quaternion = _slerp_quaternion(start_quaternion, target_quaternion, orientation_fraction)
                runtime.step(base_velocity(), wbc_command(start_position, quaternion))
                record_arm_tracking()
                record_executed_arm_action()
            for fraction, orientation_fraction in zip(
                np.linspace(0.0, args.ramp_fraction_limit, args.ramp_steps),
                np.linspace(
                    orientation_fraction_limit if args.orientation_lead_steps else 0.0,
                    orientation_fraction_limit, args.ramp_steps,
                ),
            ):
                if args.arm_ik_reference and not args.arm_ik_pose_reference:
                    runtime.diagnostic_arm_fraction = fraction
                position = start_position + fraction * position_axis_fractions * (target_position - start_position)
                quaternion = _slerp_quaternion(start_quaternion, target_quaternion, orientation_fraction)
                runtime.step(base_velocity(), wbc_command(position, quaternion))
                record_arm_tracking()
                record_executed_arm_action()
            limited_position = start_position + args.ramp_fraction_limit * position_axis_fractions * (target_position - start_position)
            limited_quaternion = _slerp_quaternion(start_quaternion, target_quaternion, orientation_fraction_limit)
            for _ in range(args.hold_steps):
                if args.arm_ik_reference and not args.arm_ik_pose_reference:
                    runtime.diagnostic_arm_fraction = args.ramp_fraction_limit
                runtime.step(base_velocity(), wbc_command(limited_position, limited_quaternion))
                record_arm_tracking()
                record_executed_arm_action()
    except _DiagnosticStop:
        pass
    finally:
        runtime.on_physics_step = None
    measured = [entry["sample"] for entry in samples]
    final_box = runtime.data.qpos[box_qpos : box_qpos + 3].copy()
    final_target_pose = None
    final_candidate_pose = None
    final_arm_gravity_torque = None
    final_arm_policy_target = None
    final_arm_actual = None
    final_policy_joint_single_substitution_displacements = None
    final_fixed_pose_error = None
    if args.observe_support_steps:
        final_fixed_pose_error = float(np.linalg.norm(runtime.data.xpos[end_effector] - start_position))
    if final_arm_joint_tracking_error is not None:
        scratch = mujoco.MjData(runtime.model)
        scratch.qpos[:] = runtime.data.qpos
        mujoco.mj_forward(runtime.model, scratch)
        final_arm_gravity_torque = scratch.qfrc_bias[runtime.joint_dof_adr[12:]].tolist()
        raw_target = runtime.default_qpos + runtime.last_action[POLICY_MJ_INDICES] * runtime.action_scale
        final_arm_policy_target = np.clip(raw_target[12:], runtime.joint_low[12:], runtime.joint_high[12:])
        final_arm_actual = runtime.data.qpos[runtime.joint_qpos_adr[12:]].copy()
        final_policy_joint_single_substitution_displacements = []
        for joint, target_value in zip(runtime.joint_qpos_adr[12:], final_arm_policy_target):
            scratch.qpos[joint] = target_value
            mujoco.mj_forward(runtime.model, scratch)
            final_policy_joint_single_substitution_displacements.append(
                (scratch.xpos[end_effector] - runtime.data.xpos[end_effector]).tolist()
            )
            scratch.qpos[joint] = runtime.data.qpos[joint]
        scratch.qpos[runtime.joint_qpos_adr[12:]] = final_arm_policy_target
        mujoco.mj_forward(runtime.model, scratch)
        final_target_pose = scratch.xpos[end_effector].tolist()
        scratch.qpos[runtime.joint_qpos_adr[12:]] = candidate.joint_solution
        mujoco.mj_forward(runtime.model, scratch)
        final_candidate_pose = scratch.xpos[end_effector].tolist()
    final_pose_ik = None
    if args.diagnose_final_pose_ik and stop_reason is None:
        reference = start_position + args.ramp_fraction_limit * position_axis_fractions * (target_position - start_position)
        orientation_limit = args.ramp_fraction_limit if args.orientation_fraction_limit is None else args.orientation_fraction_limit
        orientation = _slerp_quaternion(start_quaternion, target_quaternion, orientation_limit)
        oracle = PiperPositionReachabilityOracle(runtime)
        solution = oracle.solve(
            ReachabilityQuery(_base_pose(runtime, base_pose), reference),
            initial_joint_positions=runtime.data.qpos[runtime.joint_qpos_adr[12:]].copy(),
            target_quaternion=orientation,
        )
        final_pose_ik = {
            "kinematic_feasible": solution.kinematic_feasible,
            "position_error": solution.position_error,
            "orientation_error": solution.orientation_error,
            "joint_limit_margin": solution.joint_limit_margin,
            "joint_solution": solution.joint_solution.tolist(),
        }
    output = {
        "schema_version": 1,
        "scope": (
            "WBC fixed-pose no-contact support observation; unsupported intervals are not authorized for approach"
            if args.observe_support_steps else
            "Native pose-IK unified leg-arm WBC diagnostic continuation from NAV precontact state; no PUSH skill or contact execution permission"
        ),
        "observe_support_steps": args.observe_support_steps,
        "far_field_command_offset": far_field_offset.tolist(),
        "far_field_native_orientation": args.far_field_native_orientation,
        "far_field_settled_end_effector_world": (
            far_field_settled_position.tolist() if far_field_settled_position is not None else None
        ),
        "far_field_observed_displacement_world": (
            (runtime.data.xpos[end_effector] - far_field_settled_position).tolist()
            if far_field_settled_position is not None else None
        ),
        "far_field_final_command_error_meters": (
            float(np.linalg.norm(runtime.data.xpos[end_effector] - start_position - far_field_offset))
            if args.observe_support_steps else None
        ),
        "final_fixed_pose_error_meters": final_fixed_pose_error,
        "final_pose_ik": final_pose_ik,
        "far_field_arm_kp_scale": args.far_field_arm_kp_scale,
        "arm_gravity_compensation": args.arm_gravity_compensation,
        "arm_gravity_compensation_scale": args.arm_gravity_compensation_scale,
        "arm_target_bias_scale": args.arm_target_bias_scale,
        "arm_target_bias_limit": args.arm_target_bias_limit,
        "arm_ik_reference": args.arm_ik_reference,
        "arm_ik_pose_reference": args.arm_ik_pose_reference,
        "minimum_finger_standoff": args.minimum_finger_standoff,
        "preparation_steps": args.preparation_steps,
        "ramp_fraction_limit": args.ramp_fraction_limit,
        "position_axis_fractions": position_axis_fractions.tolist(),
        "orientation_fraction_limit": args.orientation_fraction_limit,
        "orientation_lead_steps": args.orientation_lead_steps,
        "final_limited_target_position_world": (
            start_position + args.ramp_fraction_limit * position_axis_fractions * (target_position - start_position)
        ).tolist(),
        "position_feedback_gain": args.position_feedback_gain,
        "position_feedback_max_meters": args.position_feedback_max_meters,
        "maximum_feedback_correction": maximum_feedback_correction,
        "feedback_saturated_steps": feedback_saturated_steps,
        "final_command_position_world": last_command_position.tolist() if last_command_position is not None else None,
        "arm_tracking": {
            "maximum_arm_action": maximum_arm_action,
            "arm_action_clipped_steps": arm_action_clipped_steps,
            "arm_joint_target_clipped_steps": arm_joint_target_clipped_steps,
            "maximum_arm_joint_tracking_error": maximum_arm_joint_tracking_error,
            "final_arm_joint_tracking_error": final_arm_joint_tracking_error,
            "arm_torque_saturated_substeps": arm_torque_saturated_substeps.tolist(),
            "final_arm_torque": runtime.data.ctrl[12:].tolist(),
            "arm_torque_limits": np.column_stack((runtime.ctrl_low[12:], runtime.ctrl_high[12:])).tolist(),
            "final_arm_gravity_torque_at_actual_pose": final_arm_gravity_torque,
            "final_arm_policy_joint_target": final_arm_policy_target.tolist() if final_arm_policy_target is not None else None,
            "final_arm_actual_joint_position": final_arm_actual.tolist() if final_arm_actual is not None else None,
            "final_policy_joint_single_substitution_displacements": final_policy_joint_single_substitution_displacements,
            "final_end_effector_at_policy_joint_target": final_target_pose,
            "final_policy_joint_target_end_effector_to_command": (
                float(np.linalg.norm(np.asarray(final_target_pose) - last_command_position))
                if final_target_pose is not None and last_command_position is not None else None
            ),
            "final_actual_end_effector_to_command": (
                float(np.linalg.norm(runtime.data.xpos[end_effector] - last_command_position))
                if last_command_position is not None else None
            ),
            "final_end_effector_at_candidate_joints": final_candidate_pose,
            "final_arm_joint_error_to_candidate": (
                (runtime.data.qpos[runtime.joint_qpos_adr[12:]] - candidate.joint_solution).tolist()
            ),
        },
        "base_hold": args.base_hold,
        "base_forward_offset": args.base_forward_offset,
        "base_hold_reference_pose": hold_base_pose.tolist() if hold_base_pose is not None else None,
        "preparation_end_support": (
            {"feet": list(preparation_support.supporting_feet), "margin": preparation_support.support_margin}
            if preparation_support is not None else None
        ),
        "contact_execution_enabled": False,
        "policy_executed": True,
        "push_actor_executed": False,
        "stop_reason": stop_reason,
        "completed_requested_steps": stop_reason is None,
        "input_report": str(args.input_json.resolve()),
        "input_report_sha256": sha256(args.input_json),
        "provenance": provenance.__dict__,
        "target_local": target_local.tolist(),
        "target_world": target_world.tolist(),
        "initial_candidate_end_effector_world": target_position.tolist(),
        "base_pose": base_pose.tolist(),
        "initial_base_quaternion": initial_base_quaternion.tolist(),
        "preparation_base_quaternion": preparation_base_quaternion.tolist() if preparation_base_quaternion is not None else None,
        "preparation_candidate_end_effector_world": preparation_candidate_pose.tolist() if preparation_candidate_pose is not None else None,
        "final_base_quaternion": runtime.data.xquat[runtime.base_id].tolist(),
        "candidate": {
            "position_error": candidate.position_error,
            "orientation_error": candidate.orientation_error,
            "joint_limit_margin": candidate.joint_limit_margin,
            "joint_solution": candidate.joint_solution.tolist(),
        },
        "response": {
            "contact_sample_count": len(measured),
            "region_matched_samples": sum(bool(sample["region_matched"]) for sample in measured),
            "contact_bodies": sorted({sample["body"] for sample in measured}),
            "force_and_speed_peaks": {
                "normal_force": max((sample["normal_force"] for sample in measured), default=0.0),
                "tangential_force": max((sample["tangential_force"] for sample in measured), default=0.0),
                "normal_speed_abs": max((abs(sample["normal_speed"]) for sample in measured), default=0.0),
                "tangential_speed": max((sample["tangential_speed"] for sample in measured), default=0.0),
                "orientation_error": max((sample["orientation_error"] for sample in measured), default=0.0),
            },
            "box_displacement": float(np.linalg.norm(final_box - initial_box)),
            "minimum_supporting_feet": min((len(entry["feet"]) for entry in support_trace), default=0),
            "minimum_support_margin": min((entry["margin"] for entry in support_trace if entry["margin"] is not None), default=None),
            "approach_minimum_supporting_feet": min(
                (len(entry["feet"]) for entry in support_trace if entry["phase"] == "approach"), default=None,
            ),
            "approach_minimum_support_margin": min(
                (entry["margin"] for entry in support_trace if entry["phase"] == "approach" and entry["margin"] is not None),
                default=None,
            ),
            "minimum_self_clearance": min((entry["self"] for entry in clearance_trace), default=None),
            "minimum_nonhand_box_clearance": min((entry["nonhand_box"] for entry in clearance_trace), default=None),
            "minimum_finger_box_clearance": min((entry["finger_box"] for entry in clearance_trace), default=None),
            "maximum_orientation_error": max((entry["orientation_error"] for entry in clearance_trace), default=None),
            "final_end_effector_to_target": (
                clearance_trace[-1]["end_effector_to_target"] if clearance_trace else None
            ),
        },
        "contact_samples": samples,
        "box_trace": box_trace,
        "support_trace": support_trace,
        "policy_target_trace": policy_target_trace,
        "clearance_trace": clearance_trace,
        "source_sha256": {
            str(SCRIPT): sha256(SCRIPT),
            str(args.input_json.resolve()): sha256(args.input_json),
        },
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x") as destination:
        json.dump(output, destination, indent=2, allow_nan=False)
        destination.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
