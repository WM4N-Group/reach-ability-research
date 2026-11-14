"""Replay a measured PIPER precontact terminal state through read-only handoff checks."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import mujoco
import numpy as np

from check_piper_arm_precontact_motion import _base_pose, _hand_position, sha256
from reconfigurable_navigation.reachability.box_state import BoxSnapshotGuard, BoxStateReader
from reconfigurable_navigation.reachability.clearance import ARM_BODY_NAMES
from reconfigurable_navigation.reachability.contact_geometry import PiperContactGeometryReader
from reconfigurable_navigation.reachability.contact_limits import (
    ContactHandoffGuard, ContactLimitDeclaration, ContactLimitProvenance,
    ContactLimits,
)
from reconfigurable_navigation.reachability.scenes import STATIC_BOX_BODY, make_movable_box_navigation_runtime
from reconfigurable_navigation.reachability.clearance import (
    PiperArmClearanceChecker, PiperSelfClearanceChecker,
)
from reconfigurable_navigation.piper_locomotion_runtime import DEPLOY
from reconfigurable_navigation.reachability.support import PiperQuasiStaticSupportChecker


def _load_report(path: Path) -> dict[str, object]:
    with path.open() as source:
        report = json.load(source)
    for source_path, expected in report.get("source_sha256", {}).items():
        actual = sha256(Path(source_path))
        if actual != expected:
            raise ValueError(f"Source hash mismatch: {source_path}")
    result = report.get("result")
    if not isinstance(result, dict) or not result.get("passed"):
        raise ValueError("Replay requires a successful precontact report")
    if result.get("safety", {}).get("first_box_contact") is not None:
        raise ValueError("Replay refuses a report with robot-box contact")
    state = result.get("motion", {}).get("final_state")
    if not isinstance(state, dict) or not all(field in state for field in ("qpos", "qvel", "ctrl", "time")):
        raise ValueError("Replay requires a complete terminal state")
    return report


def _restore(runtime, state: dict[str, object]) -> None:
    for field in ("qpos", "qvel", "ctrl"):
        values = np.asarray(state[field], dtype=np.float64)
        destination = getattr(runtime.data, field)
        if values.shape != destination.shape or not np.isfinite(values).all():
            raise ValueError(f"Invalid terminal state field: {field}")
        destination[:] = values
    time = float(state["time"])
    if not np.isfinite(time):
        raise ValueError("Invalid terminal state time")
    runtime.data.time = time
    mujoco.mj_forward(runtime.model, runtime.data)


def _handoff_conditions(
    reader_result: dict[str, object], *, snapshot_valid: bool,
    support_valid: bool, nonhand_clearance_valid: bool,
    native_orientation_valid: bool, contact_free: bool,
) -> dict[str, bool]:
    designated_face_ready = bool(all(
        finger["separated_witnesses_valid"]
        and finger.get("box_point_in_front_region", False)
        for finger in reader_result["fingers"]
    ))
    return {
        "snapshot_valid": bool(snapshot_valid),
        "support_valid": bool(support_valid),
        "nonhand_clearance_valid": bool(nonhand_clearance_valid),
        "designated_face_ready": designated_face_ready,
        "native_orientation_valid": bool(native_orientation_valid),
        "contact_free": bool(contact_free),
    }


def _failure_replay(
    conditions: dict[str, bool],
    declaration: ContactLimits | ContactLimitDeclaration,
    *,
    time: float,
) -> dict[str, object]:
    baseline = None
    injected = {}
    for name in conditions:
        guard = ContactHandoffGuard(declaration)
        current_baseline = guard.check_precontact(time=time, **conditions)
        if current_baseline["state"] != "ready_for_contact":
            raise ValueError(f"Baseline handoff is not ready: {current_baseline}")
        if baseline is None:
            baseline = current_baseline
        failed = dict(conditions)
        failed[name] = False
        stopped = guard.check_precontact(time=time + 0.1, **failed)
        after_failure = guard.check_precontact(time=time + 0.2, **conditions)
        try:
            guard.reset_after_reobservation(time=time + 0.3, **conditions)
        except ValueError as error:
            raise ValueError(
                f"Recovery failed after {name}: {error}; "
                f"snapshot_valid={conditions['snapshot_valid']}, "
                f"reset_time={time + 0.3}, last_time={guard.monitor.last_time}"
            ) from error
        recovered = guard.check_precontact(time=time + 0.4, **conditions)
        injected[name] = {
            "stop": stopped,
            "latched_after_valid_read": after_failure,
            "recovered": recovered,
        }
    contact_guard = ContactHandoffGuard(declaration)
    contact_guard.check_precontact(time=time, **conditions)
    declared_limits = (
        declaration.limits
        if isinstance(declaration, ContactLimitDeclaration)
        else declaration
    )
    sample = {
        "measurement_valid": True,
        "region_matched": True,
        "normal_force": declared_limits.maximum_normal_force + 1.0,
        "tangential_force": 0.0,
        "normal_speed": 0.0,
        "tangential_speed": 0.0,
        "orientation_error": 0.0,
        "tip_distance": 0.0,
    }
    contact_stop = contact_guard.observe_contact(
        [sample], time=time + 0.1, snapshot_valid=True,
        support_valid=True, nonhand_clearance_valid=True,
    )
    contact_after = contact_guard.observe_contact(
        [], time=time + 0.2, snapshot_valid=True,
        support_valid=True, nonhand_clearance_valid=True,
    )
    return {
        "baseline": baseline,
        "precondition_failures": injected,
        "contact_limit_failure": {
            "stop": contact_stop,
            "latched_after_empty_read": contact_after,
        },
    }


def replay(
    report_path: Path, output_path: Path, declaration: ContactLimitDeclaration,
) -> dict[str, object]:
    report = _load_report(report_path)
    result = report["result"]
    scene = result["scene"]
    runtime = make_movable_box_navigation_runtime(
        seed=int(result["seed"]),
        box_position=np.asarray(scene["requested_box_position"], dtype=np.float64),
        box_size=np.asarray(scene["box_size"], dtype=np.float64),
        box_yaw=float(scene["requested_box_yaw"]),
        config_path=DEPLOY / "config_wbc.yaml",
        physics_substeps=int(result["simulation"]["physics_substeps"]),
        box_mass=float(scene["box_mass"]),
    )
    _restore(runtime, result["motion"]["final_state"])
    box_reader = BoxStateReader(runtime)
    box_state = box_reader.read()
    snapshot_valid = BoxSnapshotGuard(
        box_state, geometry_radius=box_reader.radius
    ).evaluate(box_state)["valid"]
    arm = np.asarray(result["motion"]["final_joint_position"], dtype=np.float64)
    planned_pose = np.asarray(result["nav"]["planned_base_pose"], dtype=np.float64)
    base_pose = _base_pose(runtime, planned_pose)
    contact_reader = PiperContactGeometryReader(runtime)
    self_checker = PiperSelfClearanceChecker(runtime)
    nonhand_checker = PiperArmClearanceChecker(
        runtime,
        protected_body_names=frozenset({STATIC_BOX_BODY}),
        arm_body_names=ARM_BODY_NAMES - contact_reader.region.hand_bodies,
    )
    support = PiperQuasiStaticSupportChecker(runtime).evaluate(
        required_margin=float(result["thresholds"]["quasistatic_support_margin"])
    )
    nonhand = nonhand_checker.evaluate_current_configuration(
        required_clearance=float(result["thresholds"]["environment_clearance"])
    )
    self_clearance = self_checker.evaluate_current_configuration(
        required_clearance=float(result["thresholds"]["self_clearance"])
    )
    geometry_result = contact_reader.read()
    native_orientation_valid = bool(
        geometry_result["native_push_orientation_error"]
        <= float(result["thresholds"]["orientation_tracking_tolerance"])
    )
    reader_guard = ContactHandoffGuard(declaration)
    reader_result = contact_reader.read(
        handoff_guard=reader_guard,
        snapshot_valid=snapshot_valid,
        support_valid=support.safe,
        nonhand_clearance_valid=nonhand.safe,
        native_orientation_valid=native_orientation_valid,
    )
    conditions = _handoff_conditions(
        reader_result,
        snapshot_valid=snapshot_valid,
        support_valid=support.safe,
        nonhand_clearance_valid=nonhand.safe,
        native_orientation_valid=native_orientation_valid,
        contact_free=not reader_result["contact_samples"],
    )
    handoff = _failure_replay(
        conditions, declaration, time=float(box_state.time)
    )
    output = {
        "schema_version": 1,
        "scope": "Read-only measured terminal-state contact handoff replay; no contact execution",
        "contact_execution_enabled": False,
        "source_sha256": {str(Path(__file__).resolve()): sha256(Path(__file__))},
        "input_report": str(report_path.resolve()),
        "input_report_sha256": sha256(report_path),
        "terminal_time": float(box_state.time),
        "base_pose": base_pose.tolist(),
        "final_hand_position": _hand_position(runtime, "piper").tolist(),
        "geometry": reader_result,
        "safety": {
            "snapshot_valid": bool(snapshot_valid),
            "support_valid": support.safe,
            "supporting_feet": list(support.supporting_feet),
            "support_margin": support.support_margin,
            "self_clearance": self_clearance.minimum_clearance,
            "nonhand_clearance": nonhand.minimum_clearance,
            "native_orientation_valid": native_orientation_valid,
            "contact_free": not reader_result["contact_samples"],
        },
        "declared_limits": declaration.limits.__dict__,
        "limits_provenance": declaration.provenance.__dict__,
        "handoff_replay": handoff,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("x") as destination:
        json.dump(output, destination, indent=2, allow_nan=False)
        destination.write("\n")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-json", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--limits-source", required=True)
    parser.add_argument("--limits-purpose", required=True)
    parser.add_argument(
        "--limits-calibration-status",
        choices=("diagnostic_only", "simulation_calibrated", "hardware_calibrated"),
        required=True,
    )
    for name in (
        "maximum-normal-force", "maximum-tangential-force",
        "maximum-normal-speed", "maximum-tangential-speed",
        "maximum-orientation-error", "maximum-tip-distance",
    ):
        parser.add_argument(f"--{name}", type=float, required=True)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error(f"Refusing to overwrite {args.output_json}")
    values = [
        args.maximum_normal_force, args.maximum_tangential_force,
        args.maximum_normal_speed, args.maximum_tangential_speed,
        args.maximum_orientation_error, args.maximum_tip_distance,
    ]
    if not np.isfinite(values).all() or min(values) < 0.0:
        parser.error("Declared contact limits must be finite and non-negative")
    declaration = ContactLimitDeclaration(
        limits=ContactLimits(*values),
        provenance=ContactLimitProvenance(
            source=args.limits_source,
            purpose=args.limits_purpose,
            calibration_status=args.limits_calibration_status,
        ),
    )
    replay(args.input_json, args.output_json, declaration)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
