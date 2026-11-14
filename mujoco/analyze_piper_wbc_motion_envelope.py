"""Test time-indexed geometry budgets on a fixed WBC command-ramp window.

This checks sampled configurations only. It does not certify between samples,
contact persistence, dynamics, joint limits, or future controller deviations.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import mujoco
import numpy as np

from analyze_piper_wbc_endpoint_envelope import _load
from check_piper_startup import sha256
from reconfigurable_navigation.piper_locomotion_runtime import DEPLOY
from reconfigurable_navigation.piper_robot_profile import PROFILE_PATH
from reconfigurable_navigation.reachability.clearance import (
    ARM_BODY_NAMES, PiperArmClearanceChecker, PiperSelfClearanceChecker,
)
from reconfigurable_navigation.reachability.geometry_residual import anchored_geometry_displacement_bounds
from reconfigurable_navigation.reachability.scenes import STATIC_BOX_BODY, make_movable_box_navigation_runtime


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--calibration-json", type=Path, nargs="+", required=True)
    parser.add_argument("--test-json", type=Path, nargs="+", required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    paths = args.calibration_json + args.test_json
    if args.output_json.exists() or len(set(p.resolve() for p in paths)) != len(paths):
        parser.error("Require new output and distinct calibration/test inputs")
    reports = [_load(p) for p in paths]
    contract = {k: v for k, v in reports[0]["arguments"].items() if k not in ("seed", "output_json")}
    seeds = [r["result"]["seed"] for r in reports]
    if len(set(seeds)) != len(seeds):
        parser.error("Require disjoint unique seeds")
    for report in reports:
        if {k: v for k, v in report["arguments"].items() if k not in ("seed", "output_json")} != contract:
            parser.error("Controller and scene contracts must match")
        if not report["replay_comparison"]["same_result"]:
            parser.error("Replay must reproduce original result exactly")
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
    # Chosen from the frozen controller contract, never from test durations.
    horizon = float(contract["wbc_command_ramp_seconds"])
    steps = int(round(horizon / runtime.sim_dt))
    if steps < 1 or not np.isclose(steps * runtime.sim_dt, horizon, rtol=0, atol=1e-10):
        parser.error("Ramp horizon must be a positive integer number of physics steps")
    count = steps + 1
    states = []
    for report in reports:
        trace = report["trace"]
        if sha256(Path(trace["path"])) != trace["sha256"]:
            raise ValueError("Trace hash mismatch")
        with np.load(trace["path"], allow_pickle=False) as data:
            qpos, time = data["qpos"], data["time"]
        if (len(time) < count or qpos.shape != (len(time), runtime.model.nq)
                or not np.isfinite(qpos).all() or not np.isfinite(time).all()
                or not np.allclose(np.diff(time), runtime.sim_dt, rtol=0, atol=1e-10)
                or not trace["first_sample_is_motion_start"]):
            raise ValueError("Trace lacks a valid complete fixed-time window")
        states.append(qpos[:count])
    checkers = {
        "self": PiperSelfClearanceChecker(runtime),
        "nonhand_environment": PiperArmClearanceChecker(runtime,
            protected_body_names=frozenset({STATIC_BOX_BODY}),
            arm_body_names=ARM_BODY_NAMES - frozenset({"link7", "link8"})),
        "finger_environment": PiperArmClearanceChecker(runtime,
            protected_body_names=frozenset({STATIC_BOX_BODY}), arm_body_names=frozenset({"link7", "link8"})),
    }
    pairs = {name: [(a, b) for a in checker.arm_geometries for b in checker.protected_geometries]
             for name, checker in checkers.items()}
    geometries = sorted({g for group in pairs.values() for pair in group for g in pair})
    indices = {g: i for i, g in enumerate(geometries)}
    anchor = runtime.model.geom(STATIC_BOX_BODY).id
    calibration_count = len(args.calibration_json)
    # Kinematics uses private data and preserves the exact copied configurations.
    data = [mujoco.MjData(runtime.model) for _ in states]
    all_residuals = np.zeros((len(states), count, len(geometries)))
    nominal_distances = {name: np.empty((count, len(group))) for name, group in pairs.items()}
    actual_minima = {name: np.full(len(states), np.inf) for name in pairs}
    for step in range(count):
        for index, state in enumerate(states):
            data[index].qpos[:] = state[step]
            mujoco.mj_kinematics(runtime.model, data[index])
        for index, observed in enumerate(data):
            residual = anchored_geometry_displacement_bounds(runtime.model, data[0], observed,
                geometry_ids=geometries, anchor_geometry=anchor)
            all_residuals[index, step] = [residual[g] for g in geometries]
            for name, group in pairs.items():
                distances = [mujoco.mj_geomDistance(runtime.model, observed, a, b, float("inf"), None)
                             for a, b in group]
                actual_minima[name][index] = min(actual_minima[name][index], min(distances))
                if index == 0:
                    nominal_distances[name][step] = distances
    envelope = all_residuals[:calibration_count].max(axis=0)
    constraints = {}
    for name, group in pairs.items():
        radii = np.asarray([envelope[:, indices[a]] + envelope[:, indices[b]] for a, b in group]).T
        lower = (nominal_distances[name] - radii).min(axis=1)
        threshold = 0.02 if name == "finger_environment" else 0.05
        constraints[name] = {
            "required_clearance": threshold, "minimum_conditional_lower_bound": float(lower.min()),
            "conditional_safe_samples": int(np.sum(lower >= threshold)),
            "first_conditional_rejection_time": float(np.flatnonzero(lower < threshold)[0] * runtime.sim_dt)
                if np.any(lower < threshold) else None,
            "lower_bounds": lower.tolist(),
        }
    tests = []
    for index in range(calibration_count, len(states)):
        excess = all_residuals[index] - envelope
        membership = np.all(excess <= 1e-12, axis=1)
        tests.append({
            "seed": seeds[index], "samples_inside_all_geometry_budgets": int(membership.sum()),
            "first_outside_time": float(np.flatnonzero(~membership)[0] * runtime.sim_dt)
                if not membership.all() else None,
            "maximum_excess": float(np.max(np.maximum(excess, 0))),
            "exceeded_geometries": [{
                "geometry_id": g,
                "body_name": runtime.model.body(int(runtime.model.geom_bodyid[g])).name,
                "outside_samples": int(np.sum(excess[:, indices[g]] > 1e-12)),
                "maximum_excess": float(excess[:, indices[g]].max()),
                "initial_excess": float(excess[0, indices[g]]),
            } for g in geometries if np.any(excess[:, indices[g]] > 1e-12)],
            "constraints": {name: {
                "samples_inside_geometry_budgets": int(np.all(
                    excess[:, sorted({indices[g] for pair in group for g in pair})] <= 1e-12, axis=1).sum()),
                "actual_sampled_minimum_clearance": float(actual_minima[name][index]),
                "samples_meeting_conditional_clearance_and_budget": int(np.sum(
                    np.all(excess[:, sorted({indices[g] for pair in group for g in pair})] <= 1e-12, axis=1)
                    & (np.asarray(constraints[name]["lower_bounds"]) >= constraints[name]["required_clearance"]))),
            } for name, group in pairs.items()},
            "execution_certified": False,
        })
    sources = [Path(__file__).resolve(), Path(__file__).with_name("analyze_piper_wbc_endpoint_envelope.py"),
               Path(__file__).parent / "reconfigurable_navigation/reachability/geometry_residual.py"]
    output = {
        "schema_version": 1, "scope": __doc__, "controller_scene_contract": contract,
        "reference_seed": seeds[0], "calibration_seeds": seeds[:calibration_count],
        "window_seconds": horizon, "samples": count, "alignment": "elapsed physics time from arm-motion start",
        "time_warp_or_test_recentering": False,
        "inputs": [{"path": str(p.resolve()), "sha256": sha256(p)} for p in paths],
        "source_sha256": {str(p.resolve()): sha256(p) for p in sources},
        "geometry_ids": geometries,
        "geometry_bodies": {g: runtime.model.body(int(runtime.model.geom_bodyid[g])).name for g in geometries},
        "frozen_time_indexed_geometry_radii": envelope.tolist(),
        "constraints": constraints, "tests": tests,
        "continuous_trajectory_certified": False, "execution_certified": False,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x") as destination:
        json.dump(output, destination, indent=2, allow_nan=False)
    print(json.dumps({"samples": count, "window_seconds": horizon,
        "constraints": {name: {k: v for k, v in value.items() if k != "lower_bounds"}
                        for name, value in constraints.items()}, "tests": tests}, indent=2))


if __name__ == "__main__":
    main()
