"""Evaluate initial-state-conditioned WBC geometry residuals on new seeds."""

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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--calibration-json", type=Path, nargs="+", required=True)
    parser.add_argument("--test-json", type=Path, nargs="+", required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    paths = args.calibration_json + args.test_json
    if args.output_json.exists() or len({p.resolve() for p in paths}) != len(paths):
        parser.error("Require distinct inputs and a new output")
    reports = [json.loads(p.read_text()) for p in paths]
    seeds = [r["result"]["seed"] for r in reports]
    if len(set(seeds)) != len(seeds):
        parser.error("Calibration and test seeds must be unique")
    contract = {k: v for k, v in reports[0]["arguments"].items() if k not in ("seed", "output_json")}
    for report in reports:
        if {k: v for k, v in report["arguments"].items() if k not in ("seed", "output_json")} != contract:
            parser.error("Controller and scene contracts must match")
        if not report["replay_comparison"]["same_result"]:
            parser.error("Each trace must reproduce its source result exactly")
        for source, expected in report["source_sha256"].items():
            if sha256(Path(source)) != expected:
                raise ValueError(f"Input source hash mismatch: {source}")
    if contract["box_mode"] != "movable" or contract["arm_controller"] != "unified-wbc":
        parser.error("Require movable-box unified WBC")
    runtime = make_movable_box_navigation_runtime(
        seed=seeds[0], box_position=np.asarray(contract["static_box_position"]),
        box_size=np.asarray(contract["static_box_size"]), box_yaw=contract["static_box_yaw"],
        box_mass=contract["box_mass"], config_path=DEPLOY / "config_wbc.yaml",
        physics_substeps=contract["physics_substeps"],
    )
    for report in reports:
        for key, path in (("policy_sha256", runtime.policy_path), ("config_sha256", runtime.config_path),
                          ("profile_sha256", PROFILE_PATH)):
            if report["result"][key] != sha256(path):
                raise ValueError(f"Asset mismatch: {key}")
    horizon = float(contract["wbc_command_ramp_seconds"])
    steps = int(round(horizon / runtime.sim_dt))
    if steps < 1 or not np.isclose(steps * runtime.sim_dt, horizon, rtol=0, atol=1e-10):
        parser.error("Invalid fixed ramp horizon")
    count = steps + 1
    states = []
    incomplete = []
    for report in reports:
        trace = report["trace"]
        if sha256(Path(trace["path"])) != trace["sha256"]:
            raise ValueError("Trace hash mismatch")
        with np.load(trace["path"], allow_pickle=False) as data:
            qpos, time = data["qpos"], data["time"]
        if (qpos.shape != (len(time), runtime.model.nq) or len(time) < 1
                or not np.isfinite(qpos).all() or not np.isfinite(time).all()
                or not np.allclose(np.diff(time), runtime.sim_dt, rtol=0, atol=1e-10)
                or not trace["first_sample_is_motion_start"]):
            raise ValueError("Invalid physics trace")
        states.append(qpos[:count])
        incomplete.append(len(time) < count)
    calibration_count = len(args.calibration_json)
    if any(incomplete[:calibration_count]):
        parser.error("Calibration traces must cover the full fixed window")
    checkers = {
        "self": PiperSelfClearanceChecker(runtime),
        "nonhand_environment": PiperArmClearanceChecker(runtime,
            protected_body_names=frozenset({STATIC_BOX_BODY}),
            arm_body_names=ARM_BODY_NAMES - frozenset({"link7", "link8"})),
        "finger_environment": PiperArmClearanceChecker(runtime,
            protected_body_names=frozenset({STATIC_BOX_BODY}),
            arm_body_names=frozenset({"link7", "link8"})),
    }
    pairs = {name: [(a, b) for a in checker.arm_geometries for b in checker.protected_geometries]
             for name, checker in checkers.items()}
    geometries = sorted({g for group in pairs.values() for pair in group for g in pair})
    gindex = {g: i for i, g in enumerate(geometries)}
    anchor = runtime.model.geom(STATIC_BOX_BODY).id
    initial_data, current_data, predicted_data = [], [], []
    for state in states:
        initial = mujoco.MjData(runtime.model)
        initial.qpos[:] = state[0]
        mujoco.mj_kinematics(runtime.model, initial)
        initial_data.append(initial)
        current_data.append(mujoco.MjData(runtime.model))
        predicted_data.append(mujoco.MjData(runtime.model))
    residuals = [np.empty((len(state), len(geometries))) for state in states]
    nominal = [{name: np.empty((len(state), len(group))) for name, group in pairs.items()}
               for state in states]
    actual = [{name: np.empty(len(state)) for name in pairs} for state in states]
    for step in range(count):
        for index, state in enumerate(states):
            if step >= len(state):
                continue
            current_data[index].qpos[:] = state[step]
            mujoco.mj_kinematics(runtime.model, current_data[index])
        for index, state in enumerate(states):
            if step >= len(state):
                continue
            predicted, measured = conditioned_geometry_poses(
                runtime.model, initial_data[0], current_data[0], initial_data[index],
                current_data[index], geometry_ids=geometries, anchor_geometry=anchor)
            residuals[index][step] = [measured[g] for g in geometries]
            for geometry, (position, rotation) in predicted.items():
                predicted_data[index].geom_xpos[geometry] = position
                predicted_data[index].geom_xmat[geometry] = rotation.ravel()
            for name, group in pairs.items():
                nominal[index][name][step] = [mujoco.mj_geomDistance(runtime.model,
                    predicted_data[index], a, b, float("inf"), None) for a, b in group]
                actual[index][name][step] = min(mujoco.mj_geomDistance(runtime.model,
                    current_data[index], a, b, float("inf"), None) for a, b in group)
    envelope = np.max(np.stack(residuals[:calibration_count]), axis=0)
    tests = []
    for index in range(calibration_count, len(states)):
        n = len(states[index])
        excess = residuals[index] - envelope[:n]
        all_inside = np.all(excess <= 1e-12, axis=1)
        conditions = {}
        for name, group in pairs.items():
            selected = sorted({gindex[g] for pair in group for g in pair})
            inside = np.all(excess[:, selected] <= 1e-12, axis=1)
            losses = np.stack([envelope[:n, gindex[a]] + envelope[:n, gindex[b]]
                               for a, b in group], axis=1)
            lower = np.min(nominal[index][name] - losses, axis=1)
            measured_losses = np.stack([residuals[index][:, gindex[a]]
                                        + residuals[index][:, gindex[b]]
                                        for a, b in group], axis=1)
            observed_lower = np.min(nominal[index][name] - measured_losses, axis=1)
            threshold = 0.02 if name == "finger_environment" else 0.05
            conditions[name] = {
                "required_clearance": threshold,
                "samples_inside_budget": int(inside.sum()),
                "samples_with_safe_conditional_lower_bound": int(np.sum(lower >= threshold)),
                "samples_meeting_both": int(np.sum(inside & (lower >= threshold))),
                "minimum_conditional_lower_bound": float(lower.min()),
                "minimum_observed_residual_lower_bound": float(observed_lower.min()),
                "samples_with_safe_observed_residual_lower_bound": int(np.sum(observed_lower >= threshold)),
                "minimum_actual_sampled_clearance": float(actual[index][name].min()),
            }
        tests.append({"seed": seeds[index], "input_rollout_passed": reports[index]["result"]["passed"],
                      "input_rollout_reason": reports[index]["result"]["reason"],
                      "full_window_available": not incomplete[index],
                      "evaluated_samples": n, "samples_inside_all_budgets": int(all_inside.sum()),
                      "first_outside_time": float(np.flatnonzero(~all_inside)[0] * runtime.sim_dt)
                          if not all_inside.all() else None,
                      "maximum_geometry_excess": float(np.max(np.maximum(excess, 0))),
                      "exceeded_geometries": [{"geometry_id": g,
                          "body": runtime.model.body(int(runtime.model.geom_bodyid[g])).name,
                          "outside_samples": int(np.sum(excess[:, gindex[g]] > 1e-12)),
                          "maximum_excess": float(excess[:, gindex[g]].max())}
                          for g in geometries if np.any(excess[:, gindex[g]] > 1e-12)],
                      "conditions": conditions, "execution_certified": False})
    sources = [Path(__file__).resolve(), Path(__file__).parent /
               "reconfigurable_navigation/reachability/geometry_residual.py"]
    output = {"schema_version": 1, "scope": __doc__, "controller_scene_contract": contract,
              "calibration_seeds": seeds[:calibration_count], "test_seeds": seeds[calibration_count:],
              "reference_seed": seeds[0], "window_seconds": horizon, "window_samples": count,
              "alignment": "elapsed time from arm-motion start; each initial state observed at time zero",
              "test_outcomes_never_used_to_set_budgets": True,
              "observed_residual_lower_bounds_are_retrospective_only": True,
              "inputs": [{"path": str(p.resolve()), "sha256": sha256(p)} for p in paths],
              "source_sha256": {str(p): sha256(p) for p in sources},
              "geometry_ids": geometries, "frozen_time_indexed_geometry_radii": envelope.tolist(),
              "tests": tests, "continuous_trajectory_certified": False,
              "execution_certified": False}
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x") as destination:
        json.dump(output, destination, indent=2, allow_nan=False)
    print(json.dumps({"test_summary": tests}, indent=2))


if __name__ == "__main__":
    main()
