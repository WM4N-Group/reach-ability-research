"""Search static native contact handoff candidates around a measured NAV state."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import mujoco
import numpy as np

from check_piper_startup import sha256
from reconfigurable_navigation.piper_locomotion_runtime import DEPLOY
from reconfigurable_navigation.reachability import PiperPositionReachabilityOracle, ReachabilityQuery
from reconfigurable_navigation.reachability.clearance import ARM_BODY_NAMES, PiperArmClearanceChecker, PiperSelfClearanceChecker
from reconfigurable_navigation.reachability.contact_geometry import PiperContactGeometryReader, native_push_orientation
from reconfigurable_navigation.reachability.scenes import make_movable_box_navigation_runtime
from reconfigurable_navigation.reachability.support import PiperQuasiStaticSupportChecker


SCRIPT = Path(__file__).resolve()


def _contact_free_designated_face_ready(geometry: dict[str, object]) -> bool:
    fingers = geometry["fingers"]
    return bool(fingers) and not geometry["contact_samples"] and all(
        finger["separated_witnesses_valid"]
        and finger.get("box_point_in_front_region", False)
        for finger in fingers
    )


def _joint2_static_load_ratio(model, data, arm_dof_adr: np.ndarray, force_world: np.ndarray) -> float:
    jacobian = np.zeros((3, model.nv), dtype=np.float64)
    mujoco.mj_jacBody(model, data, jacobian, None, model.body("end_effector").id)
    joint2_dof = int(arm_dof_adr[1])
    torque = float(data.qfrc_bias[joint2_dof] - jacobian[:, joint2_dof] @ force_world)
    limit = float(np.max(np.abs(model.actuator("link2").ctrlrange)))
    if not np.isfinite(torque) or not np.isfinite(limit) or limit <= 0.0:
        raise ValueError("Invalid joint-2 static torque estimate or actuator limit")
    return abs(torque) / limit


def _candidate_loss(row: dict[str, object], base_distance: float, headroom: float) -> float:
    clearance = min(float(row["nonhand_clearance"]), float(row["self_clearance"]))
    ratio = float(row["joint2_static_load_ratio"])
    orientation = float(row["orientation_error"])
    return float(
        (float(row["position_error"]) / 0.01) ** 2
        + (orientation / 0.1) ** 2
        + (max(0.0, 0.07 - clearance) / 0.02) ** 2
        + (max(0.0, ratio - headroom) / (1.0 - headroom)) ** 2
        + (base_distance / 0.05) ** 2
    )


def load_report(path: Path):
    with path.open() as source:
        report = json.load(source)
    for source_path, expected in report.get("source_sha256", {}).items():
        if sha256(Path(source_path)) != expected:
            raise ValueError(f"Source hash mismatch: {source_path}")
    result = report["result"]
    if not isinstance(result.get("candidate", {}).get("precontact_state"), dict):
        raise ValueError("Input must contain a NAV precontact state")
    return report, result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-json", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--target-x", type=float, nargs="+", required=True)
    parser.add_argument("--target-y", type=float, nargs="+", required=True)
    parser.add_argument("--base-dx", type=float, nargs="+", default=(0.0,))
    parser.add_argument("--base-dy", type=float, nargs="+", default=(0.0,))
    parser.add_argument("--random-starts", type=int, default=32)
    parser.add_argument("--contact-force-n", type=float, help="Assumed box reaction on the hand, along negative box-local X")
    parser.add_argument("--joint2-headroom-ratio", type=float, default=0.8)
    parser.add_argument("--provenance-source", required=True)
    parser.add_argument("--provenance-purpose", required=True)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error(f"Refusing to overwrite {args.output_json}")
    if args.random_starts < 0 or not np.isfinite((*args.target_x, *args.target_y, *args.base_dx, *args.base_dy)).all():
        parser.error("Search values must be finite and random-start count non-negative")
    if args.contact_force_n is not None and (not np.isfinite(args.contact_force_n) or args.contact_force_n <= 0.0):
        parser.error("Contact force must be finite and positive")
    if not np.isfinite(args.joint2_headroom_ratio) or not 0.0 < args.joint2_headroom_ratio < 1.0:
        parser.error("Joint-2 headroom ratio must be in (0, 1)")
    report, result = load_report(args.input_json)
    scene = result["scene"]
    runtime = make_movable_box_navigation_runtime(
        seed=int(result["seed"]),
        box_position=np.asarray(scene["requested_box_position"], dtype=np.float64),
        box_size=np.asarray(scene["box_size"], dtype=np.float64),
        box_yaw=float(scene["requested_box_yaw"]),
        box_mass=float(scene["box_mass"]),
        config_path=DEPLOY / "config_wbc.yaml",
    )
    state = result["candidate"]["precontact_state"]
    for field in ("qpos", "qvel", "ctrl"):
        getattr(runtime.data, field)[:] = np.asarray(state[field], dtype=np.float64)
    runtime.data.time = float(state["time"])
    mujoco.mj_forward(runtime.model, runtime.data)
    box = runtime.model.geom("reachability_box").id
    base_qpos = runtime.env.robot_qpos_adr
    base_rotation = runtime.data.xmat[runtime.base_id].reshape(3, 3)
    base_pose = np.array([
        runtime.data.qpos[base_qpos], runtime.data.qpos[base_qpos + 1],
        np.arctan2(base_rotation[1, 0], base_rotation[0, 0]),
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
    self_checker = PiperSelfClearanceChecker(runtime)
    support_checker = PiperQuasiStaticSupportChecker(runtime)
    center = np.asarray(result["candidate"]["joint_solution"], dtype=np.float64)
    generator = np.random.default_rng(647)
    starts = [center]
    starts.extend(
        np.clip(
            center + generator.normal(0.0, [0.35, 0.35, 0.35, 0.5, 0.5, 0.25]),
            oracle.arm_low + 0.05,
            oracle.arm_high - 0.05,
        )
        for _ in range(args.random_starts)
    )
    rows = []
    for dx in args.base_dx:
        for dy in args.base_dy:
            query_base = base_pose + np.array([dx, dy, 0.0])
            for target_x in args.target_x:
                for target_y in args.target_y:
                    target_world = runtime.data.geom_xpos[box] + box_rotation @ np.array([target_x, target_y, 0.02])
                    best = None
                    for initial in starts:
                        candidate = oracle.solve(
                            ReachabilityQuery(query_base, target_world),
                            initial_joint_positions=initial,
                            target_quaternion=native_push_orientation(box_quaternion),
                        )
                        if not candidate.kinematic_feasible:
                            continue
                        saved = oracle._save_state()
                        try:
                            oracle._set_query_state(ReachabilityQuery(query_base, target_world), candidate.joint_solution)
                            geometry = reader.read()
                            nonhand_result = nonhand.evaluate_current_configuration(required_clearance=0.0)
                            self_result = self_checker.evaluate_current_configuration(required_clearance=0.0)
                            support_result = support_checker.evaluate_configuration(query_base, candidate.joint_solution, required_margin=0.0)
                            load_ratio = (
                                _joint2_static_load_ratio(
                                    runtime.model, runtime.data, oracle.arm_dof_adr,
                                    box_rotation @ np.array([-args.contact_force_n, 0.0, 0.0]),
                                )
                                if args.contact_force_n is not None else None
                            )
                        finally:
                            oracle._restore_state(*saved)
                        contacts = geometry["contact_samples"]
                        designated_face_ready = _contact_free_designated_face_ready(geometry)
                        passed = bool(
                            designated_face_ready
                            and nonhand_result.minimum_clearance >= 0.05
                            and self_result.minimum_clearance >= 0.05
                            and support_result.support_margin is not None
                            and support_result.support_margin >= 0.02
                            and (load_ratio is None or load_ratio < 1.0)
                        )
                        row = {
                            "base_dx": float(dx), "base_dy": float(dy),
                            "target_local": [float(target_x), float(target_y), 0.02],
                            "passed": passed,
                            "designated_face_ready": designated_face_ready,
                            "contact_count": len(contacts),
                            "minimum_finger_clearance": geometry["minimum_finger_clearance"],
                            "nonhand_clearance": nonhand_result.minimum_clearance,
                            "self_clearance": self_result.minimum_clearance,
                            "support_margin": support_result.support_margin,
                            "position_error": candidate.position_error,
                            "orientation_error": candidate.orientation_error,
                            "joint_limit_margin": candidate.joint_limit_margin,
                            "joint_solution": candidate.joint_solution.tolist(),
                            "joint2_static_load_ratio": load_ratio,
                        }
                        base_distance = float(np.hypot(dx, dy))
                        row["candidate_loss"] = (
                            _candidate_loss(row, base_distance, args.joint2_headroom_ratio)
                            if load_ratio is not None else None
                        )
                        score = (
                            passed,
                            designated_face_ready,
                            -row["candidate_loss"] if load_ratio is not None else nonhand_result.minimum_clearance,
                            self_result.minimum_clearance,
                            support_result.support_margin or -1.0,
                        )
                        if best is None or score > best[0]:
                            best = (score, row)
                    if best is not None:
                        rows.append(best[1])
    output = {
        "schema_version": 1,
        "scope": "Static native contact handoff search around measured NAV state; no dynamics or execution permission",
        "contact_execution_enabled": False,
        "input_report": str(args.input_json.resolve()),
        "input_report_sha256": sha256(args.input_json),
        "provenance": {
            "source": args.provenance_source,
            "purpose": args.provenance_purpose,
            "calibration_status": "diagnostic_only",
        },
        "search": {
            "target_x": list(map(float, args.target_x)),
            "target_y": list(map(float, args.target_y)),
            "base_dx": list(map(float, args.base_dx)),
            "base_dy": list(map(float, args.base_dy)),
            "random_starts": args.random_starts,
            "assumed_contact_force_n": args.contact_force_n,
            "joint2_headroom_ratio": args.joint2_headroom_ratio if args.contact_force_n is not None else None,
            "load_model": "gravity minus end_effector_position_jacobian transpose times assumed external box reaction; static diagnostic only",
        },
        "passed_candidates": sum(row["passed"] for row in rows),
        "evaluated_queries": len(rows),
        "best_nonhand_clearance": max((row["nonhand_clearance"] for row in rows), default=None),
        "results": rows,
        "source_sha256": {str(SCRIPT): sha256(SCRIPT), str(args.input_json.resolve()): sha256(args.input_json)},
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x") as destination:
        json.dump(output, destination, indent=2, allow_nan=False, default=lambda value: value.item() if isinstance(value, np.generic) else (_ for _ in ()).throw(TypeError(type(value).__name__)))
        destination.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
