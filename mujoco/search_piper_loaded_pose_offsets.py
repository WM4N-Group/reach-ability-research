"""Screen small base offsets against a recorded Isaac hand-box contact state."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import mujoco
import numpy as np
import torch
from scipy.optimize import minimize
from scipy.spatial import ConvexHull, QhullError
from scipy.spatial.transform import Rotation

from reconfigurable_navigation.piper_box_runtime import make_episode
from reconfigurable_navigation.piper_locomotion_runtime import JOINT_NAMES


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _support_geometry(model, data, base_id: int) -> tuple[float | None, list[str]]:
    floor = model.geom("floor").id
    feet = {name: model.geom(name).id for name in ("FL", "FR", "RL", "RR")}
    points = {name: [] for name in feet}
    for index in range(data.ncon):
        contact = data.contact[index]
        if contact.dist > 0.0 or floor not in (contact.geom1, contact.geom2):
            continue
        for name, geom in feet.items():
            if geom in (contact.geom1, contact.geom2):
                points[name].append(contact.pos[:2].copy())
    active = [name for name, values in points.items() if values]
    if len(active) < 3:
        return None, active
    support_points = np.array([np.mean(points[name], axis=0) for name in active])
    try:
        hull = ConvexHull(support_points)
    except QhullError:
        return None, active
    center = data.subtree_com[base_id, :2]
    return float(min(-(hull.equations[:, :2] @ center + hull.equations[:, 2]))), active


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-json", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--env", type=int, required=True)
    parser.add_argument("--trace-step", type=int, help="Use a recorded control-step trace instead of a terminal state")
    parser.add_argument("--contact-target-step", type=int, help="Use a later legal-contact trace step as a diagnostic target")
    parser.add_argument("--observed-face-target", action="store_true", help="Use the source-state hand/box nearest points as a precontact target")
    parser.add_argument("--assumed-contact-force-n", type=float, help="Box reaction magnitude for an observed-face target")
    parser.add_argument("--base-dx", type=float, nargs="+", default=(0.0,))
    parser.add_argument("--base-dy", type=float, nargs="+", default=(0.0,))
    parser.add_argument("--starts", type=int, default=2)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error(f"Refusing to overwrite {args.output_json}")
    if args.starts < 1 or not np.isfinite((*args.base_dx, *args.base_dy)).all():
        parser.error("Offsets must be finite and starts must be positive")
    if any(abs(value) > 0.06 for value in (*args.base_dx, *args.base_dy)):
        parser.error("This diagnostic is limited to +/-0.06 m base offsets")

    report = json.loads(args.input_json.read_text())
    if args.contact_target_step is not None and args.trace_step is None:
        parser.error("A contact target step requires a source trace step")
    if args.observed_face_target and (args.trace_step is None or args.contact_target_step is not None):
        parser.error("An observed-face target requires a source trace step and no later target step")
    if args.observed_face_target != (args.assumed_contact_force_n is not None):
        parser.error("An observed-face target requires an assumed contact force, and vice versa")
    if args.assumed_contact_force_n is not None and (not np.isfinite(args.assumed_contact_force_n) or args.assumed_contact_force_n <= 0):
        parser.error("Assumed contact force must be finite and positive")
    if args.trace_step is None:
        state = next((row for row in report["terminal_states"] if row["env_id"] == args.env), None)
        if state is None or not state["hand_contact_valid"] or not state["hand_contact_position_valid"]:
            raise ValueError("Selected environment needs a valid terminal hand-box contact")
        target = state
        joint_positions = state["robot_joint_position"]
        source_supporting_feet = None
    else:
        if args.trace_step < 0 or report.get("inspect_env_index") != args.env:
            raise ValueError("Trace step and inspected environment must match the report")
        trace = report.get(f"trace_env{args.env}")
        state = next((row for row in trace or [] if row["step"] == args.trace_step), None)
        target_step = args.trace_step if args.contact_target_step is None else args.contact_target_step
        target = next((row for row in trace or [] if row["step"] == target_step), None)
        if state is None or target is None or target_step < args.trace_step:
            raise ValueError("Source and target trace steps must exist in chronological order")
        if not args.observed_face_target and (not target["hand_contact"] or not target["hand_contact_position_valid"]):
            raise ValueError("Target trace step needs a valid hand-box contact")
        if args.contact_target_step is None and not args.observed_face_target and not state["hand_contact"]:
            raise ValueError("Selected source trace step needs a valid hand-box contact")
        if args.observed_face_target and state["hand_contact"]:
            raise ValueError("Observed-face target requires a contact-free source state")
        if args.observed_face_target and ("face_local" not in state or not np.isfinite(state["face_local"][0])):
            raise ValueError("Observed-face target requires a finite controller face gap")
        joint_positions = state["full_joint_position"]
        source_supporting_feet = sum(float(force) > 5.0 for force in state["foot_contact_force_z"])
    names = report["failure_history_arm_joint_names"]
    if names != [f"joint{i}" for i in range(1, 7)]:
        raise ValueError("Unexpected source arm-joint order")
    joint = dict(zip(report["joint_names"], joint_positions, strict=True))
    with patch("reconfigurable_navigation.climb_runtime.torch.jit.load", return_value=torch.nn.Identity()):
        runtime = make_episode("push", "geometry-only.pt", 1708, push_ik_mode="pose", native_collisions=True)
    model, data, arm = runtime.model, runtime.data, runtime.arm
    data.qpos[:3] = state["robot_position"]
    data.qpos[3:7] = state["robot_quaternion"]
    data.qpos[runtime.joint_qpos_adr] = [joint[name] for name in JOINT_NAMES]
    data.joint("push_box_joint").qpos[:3] = state["box_position"]
    data.joint("push_box_joint").qpos[3:7] = state["box_quaternion"]
    data.qvel[:] = 0.0
    mujoco.mj_forward(model, data)
    fk_error = float(np.linalg.norm(arm.hand_position() - state["hand_position"]))
    if fk_error >= 1e-4:
        raise ValueError(f"Isaac/MuJoCo hand FK mismatch: {fk_error} m")

    base_xy = data.qpos[:2].copy()
    initial = np.array([joint[name] for name in names])
    box_geom = arm.box_geom
    nonhand_bodies = {runtime._body_id(f"link{i}") for i in range(1, 6)}
    hand_bodies = {runtime._body_id(name) for name in ("link6", "link7", "link8", "end_effector")}
    protected_bodies = {runtime._body_id("base_link")}
    protected_bodies.update(runtime._body_id(f"{leg}_{segment}") for leg in ("FL", "FR", "RL", "RR")
                            for segment in ("hip", "thigh", "calf", "foot"))
    active = [geom for geom in range(model.ngeom) if model.geom_contype[geom] or model.geom_conaffinity[geom]]
    nonhand_geoms = [geom for geom in active if model.geom_bodyid[geom] in nonhand_bodies]
    hand_geoms = [geom for geom in active if model.geom_bodyid[geom] in hand_bodies]
    protected_arm_geoms = [geom for geom in active if model.geom_bodyid[geom] in nonhand_bodies | {runtime._body_id("link6")}]
    protected_geoms = [geom for geom in active if model.geom_bodyid[geom] in protected_bodies]
    box_front_world = data.geom_xpos[box_geom] - data.geom_xmat[box_geom].reshape(3, 3)[:, 0] * model.geom_size[box_geom, 0]
    source_heading = data.xmat[runtime.base_id].reshape(3, 3)[:, 0].copy()
    recorded_face_gap = float(state["face_local"][0]) if "face_local" in state else None
    observed_face_geometry = None
    if args.observed_face_target:
        nearest = None
        for geom in hand_geoms:
            points = np.empty(6, dtype=np.float64)
            distance = float(mujoco.mj_geomDistance(model, data, geom, box_geom, 1.0, points))
            if nearest is None or distance < nearest[0]:
                nearest = (distance, points.copy(), geom)
        if nearest is None or nearest[0] <= 0.0:
            raise ValueError("Source hand and box must be separated")
        contact = nearest[1][3:]
        box_rotation = data.geom_xmat[box_geom].reshape(3, 3)
        box_local = box_rotation.T @ (contact - data.geom_xpos[box_geom])
        half_size = np.asarray(report["actual_physics"]["box_size"], dtype=np.float64) / 2.0
        if (abs(box_local[0] + half_size[0]) > 0.005
                or abs(box_local[1]) > half_size[1] - 0.02
                or abs(box_local[2]) > half_size[2] - 0.01):
            raise ValueError(f"Nearest box point is outside the designated front face: {box_local}")
        rotation0 = data.xmat[arm.hand_body].reshape(3, 3).copy()
        local_contact = rotation0.T @ (nearest[1][:3] - data.xpos[arm.hand_body])
        external_force = box_rotation @ np.array([-args.assumed_contact_force_n, 0.0, 0.0])
        observed_face_geometry = {
            "source_hand_box_distance_m": nearest[0],
            "source_hand_geom": model.geom(nearest[2]).name,
            "target_box_local_m": box_local.tolist(),
            "source_hand_point_world_m": nearest[1][:3].tolist(),
        }
    else:
        contact = np.asarray(target["hand_contact_position"], dtype=np.float64)
    if not args.observed_face_target and target is state:
        rotation0 = data.xmat[arm.hand_body].reshape(3, 3).copy()
        local_contact = rotation0.T @ (contact - data.xpos[arm.hand_body])
    elif not args.observed_face_target:
        w, x, y, z = target["hand_quaternion"]
        rotation0 = Rotation.from_quat([x, y, z, w]).as_matrix()
        local_contact = rotation0.T @ (contact - np.asarray(target["hand_position"]))
    if not args.observed_face_target:
        external_force = np.asarray(
            target["hand_force"] if args.trace_step is None else target["hand_force_world"],
            dtype=np.float64,
        )
    dofs = np.array([model.joint(name).dofadr[0] for name in names], dtype=int)
    effort = dict(zip(report["actual_physics"]["robot_joint_names"],
                      report["actual_physics"]["robot_effort_limits"], strict=True))
    limits = np.array([effort[name] for name in names], dtype=np.float64)
    lower, upper = arm.lower.copy(), arm.upper.copy()
    lower[3] = max(lower[3], 0.8)
    jacobian = np.zeros((3, model.nv))

    def metrics(q: np.ndarray, offset: np.ndarray) -> dict[str, object]:
        data.qpos[:2] = base_xy + offset
        data.qpos[arm.arm_qpos] = q
        mujoco.mj_forward(model, data)
        rotation = data.xmat[arm.hand_body].reshape(3, 3)
        predicted = data.xpos[arm.hand_body] + rotation @ local_contact
        mujoco.mj_jac(model, data, jacobian, None, predicted, arm.hand_body)
        torque = data.qfrc_bias[dofs] - jacobian[:, dofs].T @ external_force
        support_margin, supporting_feet = _support_geometry(model, data, runtime.base_id)
        geometric_face_gap = float(data.xmat[runtime.base_id].reshape(3, 3)[:, 0] @ (box_front_world - data.xpos[runtime.base_id]))
        controller_face_gap = None if recorded_face_gap is None else float(recorded_face_gap - source_heading @ np.r_[offset, 0.0])
        return {
            "contact_error_m": float(np.linalg.norm(predicted - contact)),
            "orientation_change_rad": float(Rotation.from_matrix(rotation0.T @ rotation).magnitude()),
            "protected_clearance_m": min(float(mujoco.mj_geomDistance(model, data, geom, protected, 1.0, None))
                                          for geom in protected_arm_geoms for protected in protected_geoms),
            "nonhand_box_clearance_m": min(float(mujoco.mj_geomDistance(model, data, geom, box_geom, 1.0, None)) for geom in nonhand_geoms),
            "hand_box_signed_distance_m": min(float(mujoco.mj_geomDistance(model, data, geom, box_geom, 1.0, None)) for geom in hand_geoms),
            "static_torque_nm": torque.tolist(),
            "joint2_static_load_ratio": float(abs(torque[1]) / limits[1]),
            "max_static_load_ratio": float(max(abs(torque) / limits)),
            "geometric_face_gap_m": geometric_face_gap,
            "controller_face_gap_m": controller_face_gap,
            "controller_stop_headroom_m": None if controller_face_gap is None else controller_face_gap - 0.43,
            "support_margin_m": support_margin,
            "supporting_feet": supporting_feet,
        }

    def constraints(q: np.ndarray, offset: np.ndarray) -> np.ndarray:
        m = metrics(q, offset)
        return np.r_[
            (0.002 - m["contact_error_m"]) * 100,
            0.35 - m["orientation_change_rad"],
            (m["protected_clearance_m"] - 0.05) * 100,
            (m["nonhand_box_clearance_m"] - 0.005) * 100,
            (m["hand_box_signed_distance_m"] + 0.001) * 100,
            1.0 - np.abs(m["static_torque_nm"]) / limits,
        ]

    def loss(q: np.ndarray, offset: np.ndarray) -> float:
        m = metrics(q, offset)
        return float(
            (m["contact_error_m"] / 0.01) ** 2
            + (m["orientation_change_rad"] / 0.1) ** 2
            + (max(0.0, 0.07 - m["protected_clearance_m"]) / 0.02) ** 2
            + (max(0.0, m["joint2_static_load_ratio"] - 0.8) / 0.2) ** 2
            + (np.linalg.norm(offset) / 0.05) ** 2
        )

    baseline = metrics(initial, np.zeros(2))
    rng = np.random.default_rng(1811 + args.env)
    rows = []
    for dx in args.base_dx:
        for dy in args.base_dy:
            offset = np.array([dx, dy], dtype=np.float64)
            for start_index in range(args.starts):
                start = np.clip(initial, lower, upper) if start_index == 0 else rng.uniform(lower, upper)
                result = minimize(
                    loss, start, args=(offset,), method="SLSQP", bounds=list(zip(lower, upper)),
                    constraints={"type": "ineq", "fun": lambda q: constraints(q, offset)},
                    options={"maxiter": 120, "ftol": 1e-8},
                )
                margin = float(min(constraints(result.x, offset)))
                candidate_metrics = metrics(result.x, offset)
                numerically_feasible = margin >= -1e-5
                headroom_nonregression = (
                    candidate_metrics["controller_stop_headroom_m"] >= baseline["controller_stop_headroom_m"] - 1e-9
                    if recorded_face_gap is not None else None
                )
                rows.append({
                    "base_offset_m": offset.tolist(), "start_index": start_index,
                    "solver_success": bool(result.success), "solver_message": str(result.message),
                    "joint_solution": result.x.tolist(), "metrics": candidate_metrics,
                    "loss": loss(result.x, offset), "minimum_scaled_constraint": margin,
                    "numerically_feasible": numerically_feasible,
                    "stop_headroom_nonregression": headroom_nonregression,
                })
    feasible = [row for row in rows if row["numerically_feasible"]]
    headroom_preserving = [row for row in feasible if row["stop_headroom_nonregression"]]
    output = {
        "schema_version": 1,
        "scope": "Static finite base-offset and arm-pose screen on a recorded state; no dynamic or contact admission claim",
        "source_report": str(args.input_json.resolve()), "source_report_sha256": _sha256(args.input_json),
        "script_sha256": _sha256(Path(__file__)), "env": args.env,
        "source_step": args.trace_step,
        "contact_target_step": args.contact_target_step,
        "future_contact_target_used": target is not state,
        "observed_face_target_used": args.observed_face_target,
        "observed_face_geometry": observed_face_geometry,
        "assumed_contact_force_n": args.assumed_contact_force_n,
        "source_supporting_feet_above_5n": source_supporting_feet,
        "support_certified": False,
        "model_fk_error_m": fk_error, "external_force_world_n": external_force.tolist(),
        "external_force_source": "assumed_box_axis" if args.observed_face_target else "recorded_contact",
        "base_dx_grid_m": args.base_dx, "base_dy_grid_m": args.base_dy, "starts_per_offset": args.starts,
        "baseline": baseline, "candidates": rows,
        "selected": min(feasible, key=lambda row: row["loss"]) if feasible else None,
        "headroom_preserving_selected": min(headroom_preserving, key=lambda row: row["loss"]) if headroom_preserving else None,
        "limitations": "Base XY is hypothetically shifted with recorded leg joints and box state; no NAV transition, contact establishment, dynamics or substep safety proof. Force is recorded or assumed and held fixed. A later contact target is retrospective information unavailable to the online controller. An observed-face target uses source geometry but assumes that its hand point and box reaction are suitable. MuJoCo foot contact geometry differs from Isaac source force observations and is diagnostic only, not an optimization gate or support certificate.",
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x") as destination:
        json.dump(output, destination, indent=2, allow_nan=False)
        destination.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
