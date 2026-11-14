"""Audit adaptive Euler sweep refinement over a recorded WBC motion trace."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import mujoco
import numpy as np

from check_piper_startup import sha256
from reconfigurable_navigation.piper_locomotion_runtime import DEPLOY
from reconfigurable_navigation.reachability.clearance import (
    ARM_BODY_NAMES, PiperArmClearanceChecker, PiperSelfClearanceChecker,
)
from reconfigurable_navigation.reachability.scenes import (
    STATIC_BOX_BODY, make_movable_box_navigation_runtime,
)
from reconfigurable_navigation.reachability.sweep import PiperConfigurationSweep
from reconfigurable_navigation.reachability.sweep_refinement import refine_euler_clearance


def audit(path: Path, max_depth: int) -> dict[str, object]:
    report = json.loads(path.read_text())
    if not report["replay_comparison"]["same_result"]:
        raise ValueError(f"Original rollout not reproduced: {path}")
    for source, expected in report["source_sha256"].items():
        if sha256(Path(source)) != expected:
            raise ValueError(f"Source or asset checksum mismatch: {source}")
    contract = report["arguments"]
    if not contract["diagnose_designated_hand_approach"] or not contract["require_motion_sweep_certificate"]:
        raise ValueError(f"Unexpected sweep contract: {path}")
    trace = report["trace"]
    archive = path.parent / Path(trace["path"]).name
    if sha256(archive) != trace["sha256"]:
        raise ValueError(f"Trace checksum mismatch: {archive}")
    with np.load(archive, allow_pickle=False) as payload:
        states, velocities, times = payload["qpos"], payload["qvel"], payload["time"]
    if (len(times) != trace["samples"] or len(states) != len(times)
            or len(velocities) != len(times)
            or not np.isfinite(states).all() or not np.isfinite(velocities).all()
            or not np.allclose(np.diff(times), trace["sim_dt"], rtol=0, atol=1e-10)):
        raise ValueError(f"Invalid trace: {path}")
    scene = report["result"]["scene"]
    runtime = make_movable_box_navigation_runtime(
        seed=contract["seed"], box_position=np.asarray(scene["requested_box_position"]),
        box_size=np.asarray(scene["box_size"]), box_yaw=scene["requested_box_yaw"],
        box_mass=scene["box_mass"], config_path=DEPLOY / "config_wbc.yaml",
        physics_substeps=contract["physics_substeps"],
    )
    scratch = mujoco.MjData(runtime.model)
    checks = {
        "self": (PiperSelfClearanceChecker(runtime, data=scratch),
                 contract["required_self_clearance"]),
        "finger": (PiperArmClearanceChecker(
            runtime, data=scratch, protected_body_names=frozenset({STATIC_BOX_BODY}),
            arm_body_names=frozenset({"link7", "link8"})), 0.0),
        "nonhand": (PiperArmClearanceChecker(
            runtime, data=scratch, protected_body_names=frozenset({STATIC_BOX_BODY}),
            arm_body_names=ARM_BODY_NAMES - frozenset({"link7", "link8"})),
            contract["required_environment_clearance"]),
    }
    sweeps = {name: PiperConfigurationSweep(checker,
        moving_body_names=frozenset({STATIC_BOX_BODY}))
        for name, (checker, _) in checks.items()}

    def clearances(state):
        scratch.qpos[:] = state
        mujoco.mj_kinematics(runtime.model, scratch)
        return {name: checker.evaluate_current_configuration(
            required_clearance=0.0).minimum_clearance
            for name, (checker, _) in checks.items()}

    previous = clearances(states[0])
    counts = {name: {"original_rejections": 0, "adaptive_rejections": 0,
                     "extra_geometry_evaluations": 0, "maximum_depth_used": 0,
                     "minimum_original_bound_m": float("inf"),
                     "minimum_adaptive_bound_m": float("inf")}
              for name in checks}
    maximum_endpoint_error = 0.0
    for index in range(1, len(times)):
        current = clearances(states[index])
        predicted = states[index - 1].copy()
        mujoco.mj_integratePos(runtime.model, predicted, velocities[index], trace["sim_dt"])
        residual = float(np.max(np.abs(predicted - states[index])))
        maximum_endpoint_error = max(maximum_endpoint_error, residual)
        if residual > 1e-12:
            raise ValueError(f"Euler endpoint mismatch at interval {index}: {residual}")
        for name, (checker, threshold) in checks.items():
            sweep = sweeps[name]
            original = (min(previous[name], current[name])
                        - sweep.nearest_endpoint_motion_bound(states[index - 1], states[index]))
            item = counts[name]
            item["minimum_original_bound_m"] = min(item["minimum_original_bound_m"], original)
            refined = original
            if original < threshold:
                item["original_rejections"] += 1
                result = refine_euler_clearance(
                    checker, sweep, states[index - 1], velocities[index], trace["sim_dt"],
                    previous[name], current[name], threshold, max_depth=max_depth)
                item["extra_geometry_evaluations"] += result.geometry_evaluations
                item["maximum_depth_used"] = max(item["maximum_depth_used"],
                                                   result.maximum_depth_used)
                item["adaptive_rejections"] += int(not result.passed)
                refined = result.lower_bound
            item["minimum_adaptive_bound_m"] = min(item["minimum_adaptive_bound_m"], refined)
        previous = current
    original_rollout = report["result"]["motion"]["swept_clearance"]
    expected_bounds = {
        "self": original_rollout["minimum_self_lower_bound"],
        "finger": original_rollout["minimum_finger_environment_lower_bound"],
        "nonhand": original_rollout["minimum_nonhand_environment_lower_bound"],
    }
    if (len(times) - 1 != original_rollout["checked_intervals"]
            or any(not np.isclose(counts[name]["minimum_original_bound_m"], expected,
                                   rtol=0, atol=1e-10)
                   for name, expected in expected_bounds.items())):
        raise ValueError(f"Original sweep bounds not reproduced: {path}")
    return {"seed": report["result"]["seed"], "original_reason": report["result"]["reason"],
            "trace_json_sha256": sha256(path), "trace_npz_sha256": trace["sha256"],
            "intervals": len(times) - 1, "base_geometry_evaluations": len(times) * len(checks),
            "maximum_euler_endpoint_error": maximum_endpoint_error, "groups": counts,
            "original_rollout_sweep": original_rollout}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trace-json", type=Path, nargs="+", required=True)
    parser.add_argument("--max-depth", type=int, default=2)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if args.output_json.exists() or args.max_depth < 0:
        parser.error("Require a new output path and nonnegative maximum depth")
    entries = [audit(path, args.max_depth) for path in args.trace_json]
    output = {"scope": "Recorded Euler numerical curves only; original rollouts unchanged",
              "script_sha256": sha256(Path(__file__)), "max_depth": args.max_depth,
              "entries": entries}
    with args.output_json.open("x") as destination:
        json.dump(output, destination, indent=2, allow_nan=False)
    for entry in entries:
        print(json.dumps({"seed": entry["seed"], "intervals": entry["intervals"],
            "groups": entry["groups"]}), flush=True)


if __name__ == "__main__":
    main()
