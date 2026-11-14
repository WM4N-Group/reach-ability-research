"""Test a frozen empirical WBC endpoint envelope on disjoint seeds.

This is a finite-sample mechanism diagnostic, not statistical calibration.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path

import mujoco
import numpy as np

from check_piper_startup import sha256
from reconfigurable_navigation.piper_locomotion_runtime import DEPLOY
from reconfigurable_navigation.piper_robot_profile import PROFILE_PATH
from reconfigurable_navigation.reachability.clearance import (
    ARM_BODY_NAMES, PiperArmClearanceChecker, PiperSelfClearanceChecker,
)
from reconfigurable_navigation.reachability.scenes import (
    STATIC_BOX_BODY, make_movable_box_navigation_runtime,
)
from reconfigurable_navigation.reachability.tracking_clearance import PiperTrackingClearance
from reconfigurable_navigation.reachability.geometry_residual import (
    anchored_geometry_displacement_bounds, anchored_clearance_lower_bound,
)


def _load(path):
    report = json.loads(path.read_text())
    if not report.get("source_sha256"):
        raise ValueError(f"Missing source hashes: {path}")
    for source, expected in report["source_sha256"].items():
        if sha256(Path(source)) != expected:
            raise ValueError(f"Input source hash mismatch: {source}")
    if not report["result"]["passed"]:
        raise ValueError("Endpoint-only study requires completed rollouts; failures need a separate analysis")
    return report


def _rotation_distance(first, second):
    for quaternion in (first, second):
        if not np.isclose(np.linalg.norm(quaternion), 1, rtol=0, atol=1e-10):
            raise ValueError("Quaternion must be normalized")
    delta = np.empty(3)
    mujoco.mju_subQuat(delta, second, first)
    return float(np.linalg.norm(delta))


def _residual(reference, actual, runtime):
    base = runtime.env.robot_qpos_adr
    body = runtime.model.body(STATIC_BOX_BODY).id
    joint = int(runtime.model.body_jntadr[body])
    box = int(runtime.model.jnt_qposadr[joint])
    geometry = runtime.model.geom(STATIC_BOX_BODY).id
    box_radius = float(runtime.model.geom_rbound[geometry] + np.linalg.norm(runtime.model.geom_pos[geometry]))
    box_rotation = _rotation_distance(reference[box + 3:box + 7], actual[box + 3:box + 7])
    return {
        "joint_error_radii": np.abs(actual[runtime.joint_qpos_adr] - reference[runtime.joint_qpos_adr]).tolist(),
        "base_translation_radius": float(np.linalg.norm(actual[base:base + 3] - reference[base:base + 3])),
        "base_rotation_radius": _rotation_distance(reference[base + 3:base + 7], actual[base + 3:base + 7]),
        "external_point_error_radius": float(np.linalg.norm(actual[box:box + 3] - reference[box:box + 3])
                                             + 2 * box_radius * np.sin(box_rotation / 2)),
    }


def _maximum_envelope(residuals):
    return {key: np.max([item[key] for item in residuals], axis=0).tolist()
            for key in residuals[0]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--calibration-json", type=Path, nargs="+", required=True)
    parser.add_argument("--test-json", type=Path, nargs="+", required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error("Output already exists")
    paths = args.calibration_json + args.test_json
    if len({p.resolve() for p in paths}) != len(paths):
        parser.error("Calibration and test inputs must be distinct")
    reports = [_load(path) for path in paths]
    reference_report = reports[0]
    contract = {k: v for k, v in reference_report["arguments"].items() if k not in ("seed", "output_json")}
    seeds = [r["result"]["seed"] for r in reports]
    if len(set(seeds)) != len(seeds):
        parser.error("Calibration and test seeds must be disjoint and unique")
    for report in reports:
        if {k: v for k, v in report["arguments"].items() if k not in ("seed", "output_json")} != contract:
            parser.error("All inputs must share the same controller/scene arguments")
    scene = reference_report["result"]["scene"]
    if scene["box_mode"] != "movable" or contract["locomotion_policy"] != "wbc":
        parser.error("Study expects a movable-box WBC contract")
    runtime = make_movable_box_navigation_runtime(
        seed=seeds[0], box_position=np.asarray(scene["requested_box_position"]),
        box_size=np.asarray(scene["box_size"]), box_yaw=scene["requested_box_yaw"],
        box_mass=scene["box_mass"], config_path=DEPLOY / "config_wbc.yaml",
        physics_substeps=contract["physics_substeps"],
    )
    for report in reports:
        for key, path in (("policy_sha256", runtime.policy_path), ("config_sha256", runtime.config_path),
                          ("profile_sha256", PROFILE_PATH)):
            if report["result"][key] != sha256(path):
                raise ValueError(f"Runtime asset mismatch: {key}")
    states = [np.asarray(r["result"]["motion"]["final_state"]["qpos"], dtype=float) for r in reports]
    if any(q.shape != (runtime.model.nq,) or not np.isfinite(q).all() for q in states):
        parser.error("Invalid endpoint state")
    reference = states[0]
    count = len(args.calibration_json)
    # Freeze reference and budgets using only the declared calibration partition.
    envelope = _maximum_envelope([_residual(reference, q, runtime) for q in states[:count]])
    checkers = {
        "self": PiperSelfClearanceChecker(runtime),
        "nonhand_environment": PiperArmClearanceChecker(runtime,
            protected_body_names=frozenset({STATIC_BOX_BODY}),
            arm_body_names=ARM_BODY_NAMES - frozenset({"link7", "link8"})),
        "finger_environment": PiperArmClearanceChecker(runtime,
            protected_body_names=frozenset({STATIC_BOX_BODY}), arm_body_names=frozenset({"link7", "link8"})),
    }
    certificates = {}
    bounds = {}
    for name, checker in checkers.items():
        bound = PiperTrackingClearance(checker, moving_body_names=frozenset({STATIC_BOX_BODY}))
        bounds[name] = bound
        budgets = dict(envelope)
        if name == "self":
            budgets["external_point_error_radius"] = 0.0
        result = bound.evaluate(reference, **budgets, required_joint_margin=0.05,
                                required_clearance=0.02 if name == "finger_environment" else 0.05)
        certificates[name] = {**asdict(result), "conditional_clearance_safe": result.conditional_clearance_safe}
    # Each geometry retains the net result of coordinated whole-body motion.
    # The object anchor cancels one common SE(3), including its own motion.
    anchor = runtime.model.geom(STATIC_BOX_BODY).id
    geometries = sorted({g for bound in bounds.values() for pair in bound.pairs for g in pair})
    endpoint_data = []
    for state in states:
        data = mujoco.MjData(runtime.model)
        data.qpos[:] = state
        mujoco.mj_forward(runtime.model, data)
        endpoint_data.append(data)
    geometry_residuals = [anchored_geometry_displacement_bounds(
        runtime.model, endpoint_data[0], data, geometry_ids=geometries,
        anchor_geometry=anchor) for data in endpoint_data]
    geometry_envelope = {g: max(item[g] for item in geometry_residuals[:count]) for g in geometries}
    geometry_certificates = {}
    for name, bound in bounds.items():
        required = 0.02 if name == "finger_environment" else 0.05
        lower = anchored_clearance_lower_bound(runtime.model, endpoint_data[0],
                                               bound.pairs, geometry_envelope)
        geometry_certificates[name] = {
            "clearance_lower_bound": lower, "required_clearance": required,
            "conditional_clearance_safe": lower >= required,
            "joint_limits_and_support_checked": False,
        }
    tests = []
    for path, report, actual, geometric in zip(paths[count:], reports[count:], states[count:],
                                               geometry_residuals[count:]):
        residual = _residual(reference, actual, runtime)
        exceeded = []
        for key, values in residual.items():
            excess = np.asarray(values) - np.asarray(envelope[key])
            if np.any(excess > 1e-12):
                exceeded.append({"coordinate": key, "maximum_excess": float(np.max(excess)),
                                 "joint_indices": np.flatnonzero(excess > 1e-12).tolist()
                                 if key == "joint_error_radii" else None})
        actual_clearance = {}
        for name, bound in bounds.items():
            measured = bound.evaluate(actual, joint_error_radii=np.zeros(18),
                required_clearance=0.02 if name == "finger_environment" else 0.05, required_joint_margin=0.05)
            actual_clearance[name] = measured.nominal_clearance
        tests.append({
            "input": str(path.resolve()), "input_sha256": sha256(path), "seed": report["result"]["seed"],
            "measured_residuals": residual, "outside_empirical_envelope": bool(exceeded),
            "exceeded_budgets": exceeded, "actual_endpoint_clearances": actual_clearance,
            "actual_endpoint_hand_position_error": report["result"]["motion"]["final_hand_position_error"],
            "input_rollout_passed_its_own_criteria": report["result"]["passed"],
            "geometry_residuals": geometric,
            "outside_geometry_envelope": any(geometric[g] > geometry_envelope[g] + 1e-12
                                              for g in geometries),
            "exceeded_geometry_budgets": [{"geometry_id": g,
                "geometry_name": runtime.model.geom(g).name,
                "body_name": runtime.model.body(int(runtime.model.geom_bodyid[g])).name,
                "excess": geometric[g] - geometry_envelope[g]}
                for g in geometries if geometric[g] > geometry_envelope[g] + 1e-12],
            "geometry_membership_by_constraint": {name: all(
                geometric[g] <= geometry_envelope[g] + 1e-12
                for pair in bound.pairs for g in pair) for name, bound in bounds.items()},
            "execution_certified": False,
        })
    root = Path(__file__).resolve().parent
    sources = [Path(__file__).resolve(), root / "check_piper_startup.py", PROFILE_PATH,
               runtime.policy_path, runtime.config_path]
    sources.extend(root / "reconfigurable_navigation" / name for name in (
        "reachability/tracking_clearance.py", "reachability/geometry_residual.py",
        "reachability/sweep.py", "reachability/clearance.py",
        "reachability/scenes.py", "piper_locomotion_runtime.py", "piper_robot_profile.py", "locomotion_runtime.py"))
    sources.extend(p for p in (root / "robots/go2_piper").rglob("*") if p.is_file())
    output = {
        "schema_version": 2,
        "scope": "empirical WBC endpoint envelope; no confidence coverage, trajectory or stability guarantee",
        "controller_scene_contract": contract,
        "reference_seed": seeds[0], "reference_qpos": reference.tolist(),
        "calibration_inputs": [{"path": str(p.resolve()), "sha256": sha256(p), "seed": s}
                               for p, s in zip(paths[:count], seeds[:count])],
        "joint_order": [runtime.model.joint(int(j)).name
                        for j in runtime.model.dof_jntid[runtime.joint_dof_adr]],
        "frozen_empirical_envelope": envelope,
        "conditional_endpoint_certificates": certificates,
        "geometry_envelope": {
            "anchor_geometry_id": anchor, "anchor_geometry_name": STATIC_BOX_BODY,
            "geometry_names": {g: runtime.model.geom(g).name for g in geometries},
            "frozen_point_displacement_radii": geometry_envelope,
            "conditional_endpoint_certificates": geometry_certificates,
            "scope": "selected clearance only; no joint-limit, task or support guarantee",
        },
        "source_assets_sha256": {str(p.resolve()): sha256(p) for p in sources},
        "backend": {"mujoco": mujoco.__version__, "numpy": np.__version__},
        "tests": tests,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x") as destination:
        json.dump(output, destination, indent=2, allow_nan=False)
    print(json.dumps({"calibration_seeds": seeds[:count],
        "conditional_endpoint_certificates": certificates,
        "geometry_certificates": geometry_certificates,
        "tests": [{k: t[k] for k in ("seed", "outside_empirical_envelope", "outside_geometry_envelope",
            "exceeded_geometry_budgets", "actual_endpoint_clearances", "execution_certified")}
            for t in tests]}, indent=2))


if __name__ == "__main__":
    main()
