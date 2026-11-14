"""Export checked, versioned inputs for a prefix-free held-step continuation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import mujoco
import numpy as np

from audit_piper_held_cold_snapshot import _compiled_model_sha256, _rebuild_runtime
from check_piper_arm_precontact_motion import ArmMotionMonitor
from check_piper_startup import sha256
from reconfigurable_navigation.piper_robot_profile import PROFILE_PATH
from reconfigurable_navigation.reachability.box_state import BoxState


def _finite_vector(value, length: int, name: str) -> list[float]:
    vector = np.asarray(value, dtype=np.float64)
    if vector.shape != (length,) or not np.isfinite(vector).all():
        raise ValueError(f"Invalid {name}: expected {length} finite values")
    return vector.tolist()


def export_context(path: Path, expected_sha256: str) -> dict[str, object]:
    if sha256(path) != expected_sha256:
        raise ValueError(f"Baseline report changed: {path}")
    report = json.loads(path.read_text())
    result = report["result"]
    arguments = report["arguments"]
    event = result["motion"]["target_step_event"]
    if (report["phase"] != "baseline" or report["seed"] != arguments["seed"]
            or event is None or event["applied"]
            or event["closed_loop_state_v2"]["schema_version"] != 2
            or arguments["arm_controller"] != "unified-wbc"
            or not arguments["wbc_hold_on_gate"]):
        raise ValueError(f"Not a held WBC baseline: {path}")
    state = event["closed_loop_state_v2"]
    candidate = result["candidate"]
    solution = _finite_vector(candidate["joint_solution"], 6, "candidate joint solution")
    planned_pose = _finite_vector(result["nav"]["planned_base_pose"], 3, "planned base pose")
    arm_snapshots = [item["state"] for item in result["box_runtime"]["snapshots"]
                     if item["stage"] == "arm_target"]
    if arguments["box_mode"] == "movable" and len(arm_snapshots) != 1:
        raise ValueError("Missing unique arm-target box snapshot")
    runtime = _rebuild_runtime(arguments)
    for actual, expected, name in (
        (sha256(runtime.policy_path), result["policy_sha256"], "policy"),
        (sha256(runtime.config_path), result["config_sha256"], "config"),
        (sha256(PROFILE_PATH), result["profile_sha256"], "profile"),
    ):
        if actual != expected:
            raise ValueError(f"{name} hash mismatch")
    spec = mujoco.mjtState.mjSTATE_INTEGRATION
    vector = np.asarray(state["mujoco_integration_state"], dtype=np.float64)
    if (state["mujoco_integration_state_spec"] != int(spec)
            or vector.shape != (mujoco.mj_stateSize(runtime.model, spec),)):
        raise ValueError("MuJoCo state specification mismatch")
    mujoco.mj_setState(runtime.model, runtime.data, vector, spec)
    mujoco.mj_forward(runtime.model, runtime.data)
    restored = np.empty_like(vector)
    mujoco.mj_getState(runtime.model, runtime.data, restored, spec)
    if not np.array_equal(restored, vector):
        raise ValueError("Physical state changed during forward reconstruction")
    monitor = ArmMotionMonitor(
        runtime, target_world=np.asarray(state["target_world"], dtype=np.float64),
        required_self_clearance=arguments["required_self_clearance"],
        required_environment_clearance=arguments["required_environment_clearance"],
        required_support_margin=arguments["required_support_margin"],
        support_violation_grace_seconds=arguments["support_violation_grace_seconds"],
        require_motion_sweep_certificate=arguments["require_motion_sweep_certificate"],
        maximum_box_displacement=arguments["box_max_displacement"],
        maximum_box_linear_speed=arguments["box_max_linear_speed"],
        maximum_box_angular_speed=arguments["box_max_angular_speed"],
        hand_point=arguments["hand_point"],
        diagnose_designated_hand_approach=arguments["diagnose_designated_hand_approach"],
    )
    monitor._refresh_clearance_geometry()
    self_clearance = monitor.self_clearance.evaluate_current_configuration(required_clearance=0.0)
    environment = monitor.environment_clearance.evaluate_current_configuration(required_clearance=0.0)
    finger = (monitor.finger_environment_clearance.evaluate_current_configuration(required_clearance=0.0)
              if monitor.finger_environment_clearance is not None else None)
    nonhand = (monitor.nonhand_environment_clearance.evaluate_current_configuration(required_clearance=0.0)
               if monitor.nonhand_environment_clearance is not None else None)
    if (not np.isclose(environment.minimum_clearance, state["current_environment_clearance"], rtol=0, atol=1e-10)
            or (nonhand is not None and not np.isclose(
                nonhand.minimum_clearance, state["current_nonhand_environment_clearance"], rtol=0, atol=1e-10))):
        raise ValueError("Rebuilt clearance monitor differs from baseline snapshot")
    face_ready = None
    if monitor.contact_geometry_reader is not None:
        contact_geometry = monitor.contact_geometry_reader.read()
        face_ready = bool(contact_geometry["fingers"]) and all(
            item["separated_witnesses_valid"] and item["box_point_in_front_region"]
            for item in contact_geometry["fingers"]
        )
        if face_ready != state["current_designated_face_ready"]:
            raise ValueError("Rebuilt designated-face monitor differs from snapshot")
    observed_box = monitor.box_reader.read() if monitor.box_reader is not None else None
    if observed_box is not None:
        reference = state["box_guard_reference"]
        if reference is None or not arm_snapshots or reference != arm_snapshots[0]:
            raise ValueError("Box guard reference differs from arm-target snapshot")
        reference_state = BoxState(
            reference["time"], reference["position"], reference["quaternion"],
            reference["linear_velocity_world"], reference["angular_velocity_world"],
        )
        expected_target = reference_state.point_world(arguments["hand_target_local"])
        if not np.allclose(expected_target, state["target_world"], rtol=0, atol=1e-10):
            raise ValueError("Held target differs from arm-target box reference")
        if not np.allclose(observed_box.position, result["scene"]["box_position"], rtol=0, atol=1e-8):
            raise ValueError("Current box pose differs from report scene")
    if state["motion_step_index"] + 1 != event["control_step"]:
        raise ValueError("Held-step control index mismatch")
    return {
        "schema_version": 1,
        "scope": "Checked inputs at the held-step boundary; no prefix-free WBC suffix has run",
        "source_report": str(path),
        "source_report_sha256": expected_sha256,
        "seed": report["seed"],
        "arguments": arguments,
        "artifact_sha256": {
            "policy": result["policy_sha256"], "config": result["config_sha256"],
            "profile": result["profile_sha256"],
            "compiled_model": _compiled_model_sha256(runtime.model),
            "scene_xml": sha256(runtime.scene_path),
        },
        "closed_loop_state_v2": state,
        "candidate_joint_solution": solution,
        "planned_base_pose": planned_pose,
        "arm_target_box_snapshot": arm_snapshots[0] if arm_snapshots else None,
        "scene_box_position": result["scene"]["box_position"],
        "scene_box_yaw": result["scene"]["box_yaw"],
        "monitor_at_boundary": {
            "stage": "arm_motion",
            "self_clearance": self_clearance.minimum_clearance,
            "self_clearance_bodies": [self_clearance.arm_body, self_clearance.protected_body],
            "environment_clearance": environment.minimum_clearance,
            "environment_clearance_bodies": [environment.arm_body, environment.protected_body],
            "finger_environment_clearance": finger.minimum_clearance if finger is not None else None,
            "nonhand_environment_clearance": nonhand.minimum_clearance if nonhand is not None else None,
            "designated_face_ready": face_ready,
            "support_violation_steps": state["support_violation_steps"],
            "sweep_previous_qpos": state["sweep_previous_qpos"],
            "sweep_previous_clearances": state["sweep_previous_clearances"],
            "physics_monitor_last_time": state["physics_monitor_last_time"],
        },
        "prefix_report": {
            "nav": result["nav"],
            "candidate": candidate,
            "hold_events_before_boundary": [item for item in result["motion"]["wbc_hold_events"]
                                            if item["time"] <= event["time"]],
            "trace_before_boundary": [item for item in result["motion"]["trace"]
                                      if item["time"] < event["time"]],
        },
        "complete_prefix_accumulators_available": False,
        "cold_continuation_verified": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol-json", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    protocol = json.loads(args.protocol_json.read_text())
    if sha256(Path(__file__)) != protocol["exporter_sha256"]:
        raise ValueError("Context exporter changed")
    if args.output_dir.exists():
        parser.error("Require a new output directory")
    contexts = [export_context(Path(item["path"]), item["sha256"])
                for item in protocol["reports"]]
    args.output_dir.mkdir(parents=True)
    for context in contexts:
        output = args.output_dir / f"seed{context['seed']}-held-context-v1.json"
        with output.open("x") as destination:
            json.dump(context, destination, indent=2, allow_nan=False)
            destination.write("\n")
        print(f"{output}: {sha256(output)}")


if __name__ == "__main__":
    main()
