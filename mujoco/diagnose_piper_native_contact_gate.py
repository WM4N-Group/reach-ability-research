"""Diagnose native PIPER end-effector gate versus designated-finger geometry."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import mujoco
import numpy as np

from check_piper_startup import sha256
from reconfigurable_navigation.box_push_runtime import CONTROL, batch
from reconfigurable_navigation.piper_locomotion_runtime import DEPLOY
from reconfigurable_navigation.reachability import PiperPositionReachabilityOracle, ReachabilityQuery
from reconfigurable_navigation.reachability.clearance import PiperArmClearanceChecker, ARM_BODY_NAMES
from reconfigurable_navigation.reachability.contact_geometry import PiperContactGeometryReader, native_push_orientation
from reconfigurable_navigation.reachability.scenes import make_movable_box_navigation_runtime


SCRIPT = Path(__file__).resolve()


def _json_default(value):
    if isinstance(value, np.generic):
        return value.item()
    raise TypeError(f"Unsupported JSON value: {type(value).__name__}")


def load_report(path: Path) -> tuple[dict[str, object], dict[str, object]]:
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-json", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--target-x", type=float, nargs="+", required=True)
    parser.add_argument("--provenance-source", required=True)
    parser.add_argument("--provenance-purpose", required=True)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error(f"Refusing to overwrite {args.output_json}")
    if not np.isfinite(args.target_x).all():
        parser.error("Target x values must be finite")
    report, result = load_report(args.input_json)
    scene = result["scene"]
    runtime = make_movable_box_navigation_runtime(
        seed=int(result["seed"]),
        box_position=np.asarray(scene["requested_box_position"], dtype=np.float64),
        box_size=np.asarray(scene["box_size"], dtype=np.float64),
        box_yaw=float(scene["requested_box_yaw"]),
        box_mass=float(scene["box_mass"]),
        config_path=DEPLOY / "config_wbc.yaml",
        physics_substeps=1,
    )
    state = result["candidate"]["precontact_state"]
    for field in ("qpos", "qvel", "ctrl"):
        getattr(runtime.data, field)[:] = np.asarray(state[field], dtype=np.float64)
    runtime.data.time = float(state["time"])
    mujoco.mj_forward(runtime.model, runtime.data)
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
    oracle = PiperPositionReachabilityOracle(runtime)
    reader = PiperContactGeometryReader(runtime)
    nonhand = PiperArmClearanceChecker(
        runtime,
        protected_body_names=frozenset({"reachability_box"}),
        arm_body_names=ARM_BODY_NAMES - reader.region.hand_bodies,
    )
    initial = np.asarray(result["candidate"]["joint_solution"], dtype=np.float64)
    rows = []
    for target_x in args.target_x:
        target_world = runtime.data.geom_xpos[box] + box_rotation @ np.array([target_x, 0.0, 0.02])
        candidate = oracle.solve(
            ReachabilityQuery(base_pose, target_world),
            initial_joint_positions=initial,
            target_quaternion=native_push_orientation(box_quaternion),
        )
        if not candidate.kinematic_feasible:
            rows.append({"target_local_x": float(target_x), "ik_feasible": False, "position_error": float(candidate.position_error), "orientation_error": float(candidate.orientation_error) if candidate.orientation_error is not None else None})
            continue
        runtime.data.qpos[runtime.joint_qpos_adr[12:]] = candidate.joint_solution
        runtime.data.qvel.fill(0.0)
        mujoco.mj_forward(runtime.model, runtime.data)
        hand_body = runtime.model.body("end_effector").id
        hand_local = box_rotation.T @ (runtime.data.xpos[hand_body] - runtime.data.geom_xpos[box])
        geometry = reader.read()
        finger_clearance = min(finger["clearance"] for finger in geometry["fingers"])
        face_ready = bool(all(
            finger["separated_witnesses_valid"] and finger.get("box_point_in_front_region", False)
            for finger in geometry["fingers"]
        ))
        gate = bool(
            CONTROL["side_approach_ready"](
                batch(hand_local), scene["box_size"][0] / 2.0, result["thresholds"]["push_approach_distance"]
            )[0]
        ) and abs(hand_local[2]) < 0.06
        rows.append({
            "target_local_x": float(target_x),
            "ik_feasible": True,
            "position_error": float(candidate.position_error),
            "orientation_error": float(candidate.orientation_error) if candidate.orientation_error is not None else None,
            "hand_local": hand_local.tolist(),
            "hand_gate": gate,
            "finger_clearance": finger_clearance,
            "designated_face_ready": bool(face_ready),
            "contact_samples": len(geometry["contact_samples"]),
            "nonhand_clearance": nonhand.evaluate_current_configuration(required_clearance=0.0).minimum_clearance,
        })
    output = {
        "schema_version": 1,
        "scope": "Static native hand-gate versus designated-finger geometry diagnosis; no dynamics or execution",
        "contact_execution_enabled": False,
        "input_report": str(args.input_json.resolve()),
        "input_report_sha256": sha256(args.input_json),
        "provenance": {
            "source": args.provenance_source,
            "purpose": args.provenance_purpose,
            "calibration_status": "diagnostic_only",
        },
        "gate_definition": {
            "approach_distance": result["thresholds"]["push_approach_distance"],
            "box_half_length": scene["box_size"][0] / 2.0,
            "end_effector_local_x_range": [
                -scene["box_size"][0] / 2.0 - result["thresholds"]["push_approach_distance"] - 0.06,
                -scene["box_size"][0] / 2.0 - 0.03,
            ],
        },
        "results": rows,
        "source_sha256": {
            str(SCRIPT): sha256(SCRIPT),
            str(args.input_json.resolve()): sha256(args.input_json),
        },
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x") as destination:
        json.dump(output, destination, indent=2, allow_nan=False, default=_json_default)
        destination.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
