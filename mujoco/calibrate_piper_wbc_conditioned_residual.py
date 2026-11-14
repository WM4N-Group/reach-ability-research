"""Calibrate a whole-run WBC geometry residual threshold on disjoint seeds."""

from __future__ import annotations

import argparse
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
from reconfigurable_navigation.reachability.geometry_residual import conditioned_geometry_poses
from reconfigurable_navigation.reachability.scenes import STATIC_BOX_BODY, make_movable_box_navigation_runtime


def _read_trace(path, runtime, contract, count):
    report = json.loads(path.read_text())
    if {key: value for key, value in report["arguments"].items()
            if key not in ("seed", "output_json")} != contract:
        raise ValueError(f"Controller or scene contract mismatch: {path}")
    if not report["replay_comparison"]["same_result"]:
        raise ValueError(f"Replay did not reproduce original result: {path}")
    for source, expected in report["source_sha256"].items():
        if sha256(Path(source)) != expected:
            raise ValueError(f"Source hash mismatch: {source}")
    for key, asset in (("policy_sha256", runtime.policy_path),
                       ("config_sha256", runtime.config_path),
                       ("profile_sha256", PROFILE_PATH)):
        if report["result"][key] != sha256(asset):
            raise ValueError(f"Runtime asset mismatch: {key}")
    trace = report["trace"]
    if sha256(Path(trace["path"])) != trace["sha256"]:
        raise ValueError(f"Trace hash mismatch: {path}")
    with np.load(trace["path"], allow_pickle=False) as payload:
        qpos = payload["qpos"]
        times = payload["time"]
    if (len(times) < 1 or qpos.shape != (len(times), runtime.model.nq)
            or not np.isfinite(qpos).all() or not np.isfinite(times).all()
            or not np.allclose(np.diff(times), runtime.sim_dt, rtol=0, atol=1e-10)
            or not trace["first_sample_is_motion_start"]):
        raise ValueError(f"Invalid physics trace: {path}")
    return report, qpos[:count], len(times) >= count


def _measure(runtime, reference, observed, geometries, anchor, groups, radius):
    model = runtime.model
    initial_reference = mujoco.MjData(model)
    initial_observed = mujoco.MjData(model)
    current_reference = mujoco.MjData(model)
    current_observed = mujoco.MjData(model)
    predicted_data = mujoco.MjData(model)
    initial_reference.qpos[:] = reference[0]
    initial_observed.qpos[:] = observed[0]
    mujoco.mj_kinematics(model, initial_reference)
    mujoco.mj_kinematics(model, initial_observed)
    score = 0.0
    conditions = {name: {"minimum_conditional_lower_bound": float("inf"),
                         "minimum_observed_residual_lower_bound": float("inf"),
                         "minimum_actual_sampled_clearance": float("inf"),
                         "samples_meeting_conditional_bound": 0,
                         "samples_meeting_observed_bound": 0}
                  for name in groups} if radius is not None else None
    for step in range(len(observed)):
        current_reference.qpos[:] = reference[step]
        current_observed.qpos[:] = observed[step]
        mujoco.mj_kinematics(model, current_reference)
        mujoco.mj_kinematics(model, current_observed)
        prediction, residuals = conditioned_geometry_poses(
            model, initial_reference, current_reference,
            initial_observed, current_observed,
            geometry_ids=geometries, anchor_geometry=anchor)
        score = max(score, max(residuals.values()))
        if radius is None:
            continue
        for geometry, (position, rotation) in prediction.items():
            predicted_data.geom_xpos[geometry] = position
            predicted_data.geom_xmat[geometry] = rotation.ravel()
        for name, (pairs, threshold) in groups.items():
            lower = min(mujoco.mj_geomDistance(model, predicted_data, a, b,
                         float("inf"), None)
                        - radius * (int(a != anchor) + int(b != anchor))
                        for a, b in pairs)
            observed_lower = min(mujoco.mj_geomDistance(model, predicted_data, a, b,
                                 float("inf"), None) - residuals[a] - residuals[b]
                                 for a, b in pairs)
            actual = min(mujoco.mj_geomDistance(model, current_observed, a, b,
                         float("inf"), None) for a, b in pairs)
            item = conditions[name]
            item["minimum_conditional_lower_bound"] = min(
                item["minimum_conditional_lower_bound"], lower)
            item["minimum_observed_residual_lower_bound"] = min(
                item["minimum_observed_residual_lower_bound"], observed_lower)
            item["minimum_actual_sampled_clearance"] = min(
                item["minimum_actual_sampled_clearance"], actual)
            item["samples_meeting_conditional_bound"] += int(lower >= threshold)
            item["samples_meeting_observed_bound"] += int(observed_lower >= threshold)
    return score, conditions


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference-json", type=Path, required=True)
    parser.add_argument("--calibration-json", type=Path, nargs="+", required=True)
    parser.add_argument("--test-json", type=Path, nargs="*", default=[])
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    paths = [args.reference_json, *args.calibration_json, *args.test_json]
    if args.output_json.exists() or len({path.resolve() for path in paths}) != len(paths):
        parser.error("Require distinct inputs and a new output")
    reference_report = json.loads(args.reference_json.read_text())
    contract = {key: value for key, value in reference_report["arguments"].items()
                if key not in ("seed", "output_json")}
    if contract["box_mode"] != "movable" or contract["arm_controller"] != "unified-wbc":
        parser.error("Expected movable-box unified WBC contract")
    runtime = make_movable_box_navigation_runtime(
        seed=reference_report["result"]["seed"],
        box_position=np.asarray(contract["static_box_position"]),
        box_size=np.asarray(contract["static_box_size"]),
        box_yaw=contract["static_box_yaw"], box_mass=contract["box_mass"],
        config_path=DEPLOY / "config_wbc.yaml",
        physics_substeps=contract["physics_substeps"],
    )
    horizon = float(contract["wbc_command_ramp_seconds"])
    steps = int(round(horizon / runtime.sim_dt))
    if steps < 1 or not np.isclose(steps * runtime.sim_dt, horizon, rtol=0, atol=1e-10):
        parser.error("Window must be a positive integer number of physics steps")
    count = steps + 1
    entries = [_read_trace(path, runtime, contract, count) for path in paths]
    seeds = [entry[0]["result"]["seed"] for entry in entries]
    if len(set(seeds)) != len(seeds):
        parser.error("Reference, calibration and test seeds must be unique")
    if not entries[0][2]:
        parser.error("Reference lacks a full window")
    reference = entries[0][1]
    checkers = {
        "self": PiperSelfClearanceChecker(runtime),
        "nonhand_environment": PiperArmClearanceChecker(runtime,
            protected_body_names=frozenset({STATIC_BOX_BODY}),
            arm_body_names=ARM_BODY_NAMES - frozenset({"link7", "link8"})),
        "finger_environment": PiperArmClearanceChecker(runtime,
            protected_body_names=frozenset({STATIC_BOX_BODY}),
            arm_body_names=frozenset({"link7", "link8"})),
    }
    groups = {name: ([(a, b) for a in checker.arm_geometries
                      for b in checker.protected_geometries],
                     0.02 if name == "finger_environment" else 0.05)
              for name, checker in checkers.items()}
    geometries = sorted({g for pairs, _ in groups.values() for pair in pairs for g in pair})
    anchor = runtime.model.geom(STATIC_BOX_BODY).id
    calibration = []
    for path, (report, states, complete) in zip(args.calibration_json,
                                                 entries[1:1 + len(args.calibration_json)]):
        score = _measure(runtime, reference, states, geometries, anchor, groups,
                         radius=None)[0] if complete else None
        calibration.append({"seed": report["result"]["seed"],
            "input": str(path.resolve()), "full_window_available": complete,
            "input_rollout_passed": report["result"]["passed"],
            "input_rollout_reason": report["result"]["reason"],
            "score": score})
    radius = max(item["score"] for item in calibration) if all(
        item["score"] is not None for item in calibration) else None
    tests = []
    for path, (report, states, complete) in zip(args.test_json,
                                                 entries[1 + len(calibration):]):
        score, conditions = _measure(runtime, reference, states, geometries,
            anchor, groups, radius=radius) if complete else (None, None)
        if conditions is not None:
            for name, item in conditions.items():
                item["required_clearance"] = groups[name][1]
                item["all_sampled_bounds_pass"] = item["samples_meeting_conditional_bound"] == count
                item["observed_bound_never_exceeds_actual"] = (
                    item["minimum_observed_residual_lower_bound"]
                    <= item["minimum_actual_sampled_clearance"] + 1e-9)
        tests.append({"seed": report["result"]["seed"],
            "input": str(path.resolve()), "full_window_available": complete,
            "input_rollout_passed": report["result"]["passed"],
            "input_rollout_reason": report["result"]["reason"],
            "score": score, "inside_frozen_radius": score <= radius if score is not None
                and radius is not None else False,
            "conditions": conditions,
            "sampled_geometry_condition_met": bool(
                score is not None and radius is not None and score <= radius
                and all(item["all_sampled_bounds_pass"] for item in conditions.values())),
            "execution_certified": False})
    root = Path(__file__).resolve().parent
    sources = [Path(__file__).resolve(), root / "reconfigurable_navigation/reachability/geometry_residual.py",
               root / "reconfigurable_navigation/reachability/clearance.py",
               root / "reconfigurable_navigation/reachability/scenes.py",
               PROFILE_PATH, runtime.policy_path, runtime.config_path]
    sources.extend(path for path in (root / "robots/go2_piper").rglob("*") if path.is_file())
    output = {"schema_version": 1,
        "scope": "single new-run sampled-clearance risk bound under exchangeable whole-run scores",
        "reference_seed": seeds[0], "calibration_seeds": seeds[1:1 + len(calibration)],
        "test_seeds": seeds[1 + len(calibration):],
        "window_seconds": horizon, "window_samples": count,
        "guaranteed_marginal_score_coverage_if_exchangeable": len(calibration) / (len(calibration) + 1),
        "frozen_uniform_geometry_radius": radius,
        "missing_calibration_window_requires_rejection": radius is None,
        "calibration": calibration, "tests": tests,
        "inputs_sha256": {str(path.resolve()): sha256(path) for path in paths},
        "source_assets_sha256": {str(path.resolve()): sha256(path) for path in sources},
        "full_execution_certified": False, "continuous_trajectory_certified": False}
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x") as destination:
        json.dump(output, destination, indent=2, allow_nan=False)
    print(json.dumps({"radius": radius, "calibration": calibration, "tests": tests}, indent=2))


if __name__ == "__main__":
    main()
