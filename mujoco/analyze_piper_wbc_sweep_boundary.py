"""Refine one stopped Euler position-update interval without rerunning control."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

import mujoco
import numpy as np

from check_piper_startup import sha256
from reconfigurable_navigation.piper_locomotion_runtime import DEPLOY
from reconfigurable_navigation.piper_robot_profile import PROFILE_PATH
from reconfigurable_navigation.reachability.clearance import (
    ARM_BODY_NAMES, PiperArmClearanceChecker, PiperSelfClearanceChecker,
)
from reconfigurable_navigation.reachability.scenes import STATIC_BOX_BODY, make_movable_box_navigation_runtime
from reconfigurable_navigation.reachability.sweep import PiperConfigurationSweep
from reconfigurable_navigation.reachability.sweep_refinement import refine_euler_clearance


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-json", type=Path, required=True)
    parser.add_argument("--segments", type=int, default=1000)
    parser.add_argument("--adaptive-max-depth", type=int)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if (args.output_json.exists() or args.segments < 1
            or (args.adaptive_max_depth is not None and args.adaptive_max_depth < 0)):
        parser.error("Require a new output path, positive segments and nonnegative depth")
    report = json.loads(args.input_json.read_text())
    reason = report["result"]["reason"]
    if (reason not in ("dynamic_swept_nonhand_environment_clearance",
                       "dynamic_swept_self_clearance")
            or not report["replay_comparison"]["same_result"]):
        parser.error("Expected an exactly replayed self or nonhand sweep rejection")
    for source, expected in report["source_sha256"].items():
        if sha256(Path(source)) != expected:
            raise ValueError(f"Source hash mismatch: {source}")
    trace = report["trace"]
    if sha256(Path(trace["path"])) != trace["sha256"]:
        raise ValueError("Trace hash mismatch")
    with np.load(trace["path"], allow_pickle=False) as data:
        qpos = data["qpos"]
        qvel = data["qvel"]
        times = data["time"]
    if len(times) < 2 or not np.isclose(times[-1] - times[-2], trace["sim_dt"], atol=1e-10):
        raise ValueError("Missing final physics interval")
    contract = report["arguments"]
    scene = report["result"]["scene"]
    runtime = make_movable_box_navigation_runtime(
        seed=contract["seed"], box_position=np.asarray(scene["requested_box_position"]),
        box_size=np.asarray(scene["box_size"]), box_yaw=scene["requested_box_yaw"],
        box_mass=scene["box_mass"], config_path=DEPLOY / "config_wbc.yaml",
        physics_substeps=contract["physics_substeps"],
    )
    for key, asset in (("policy_sha256", runtime.policy_path),
                       ("config_sha256", runtime.config_path),
                       ("profile_sha256", PROFILE_PATH)):
        if report["result"][key] != sha256(asset):
            raise ValueError(f"Asset mismatch: {key}")
    predicted = qpos[-2].copy()
    mujoco.mj_integratePos(runtime.model, predicted, qvel[-1], trace["sim_dt"])
    residual = float(np.max(np.abs(predicted - qpos[-1])))
    if residual > 1e-12:
        raise ValueError(f"Euler integration residual: {residual}")
    scratch = mujoco.MjData(runtime.model)
    checker = (PiperSelfClearanceChecker(runtime, data=scratch)
        if reason == "dynamic_swept_self_clearance"
        else PiperArmClearanceChecker(runtime, data=scratch,
            protected_body_names=frozenset({STATIC_BOX_BODY}),
            arm_body_names=ARM_BODY_NAMES - frozenset({"link7", "link8"})))
    sweep = PiperConfigurationSweep(checker, moving_body_names=frozenset({STATIC_BOX_BODY}))
    states, clearances, bodies = [], [], []
    for fraction in np.linspace(0.0, 1.0, args.segments + 1):
        state = qpos[-2].copy()
        mujoco.mj_integratePos(runtime.model, state, qvel[-1], trace["sim_dt"] * fraction)
        scratch.qpos[:] = state
        mujoco.mj_kinematics(runtime.model, scratch)
        evaluated = checker.evaluate_current_configuration(required_clearance=0.0)
        states.append(state)
        clearances.append(evaluated.minimum_clearance)
        bodies.append((evaluated.arm_body, evaluated.protected_body))
    lower = min(min(clearances[index], clearances[index + 1])
                - sweep.nearest_endpoint_motion_bound(states[index], states[index + 1])
                for index in range(args.segments))
    threshold = (contract["required_self_clearance"]
        if reason == "dynamic_swept_self_clearance" else contract["required_environment_clearance"])
    adaptive = (refine_euler_clearance(
        checker, sweep, qpos[-2], qvel[-1], trace["sim_dt"],
        clearances[0], clearances[-1], threshold,
        max_depth=args.adaptive_max_depth)
        if args.adaptive_max_depth is not None else None)
    limiting = int(np.argmin(clearances))
    root = Path(__file__).resolve().parent
    sources = [Path(__file__).resolve(), root / "reconfigurable_navigation/reachability/sweep.py",
               root / "reconfigurable_navigation/reachability/sweep_refinement.py",
               root / "reconfigurable_navigation/reachability/clearance.py",
               root / "reconfigurable_navigation/reachability/scenes.py",
               PROFILE_PATH, runtime.policy_path, runtime.config_path]
    sources.extend(path for path in (root / "robots/go2_piper").rglob("*") if path.is_file())
    output = {"schema_version": 1,
        "scope": "original stopped Euler position-update curve only; no changed rollout result",
        "input": str(args.input_json.resolve()), "input_sha256": sha256(args.input_json),
        "trace_sha256": trace["sha256"], "source_assets_sha256": {
            str(path.resolve()): sha256(path) for path in sources},
        "failure_time": float(times[-1]), "interval_start_time": float(times[-2]),
        "integration_endpoint_residual": residual,
        "segments": args.segments,
        "stopped_constraint": reason,
        "required_clearance": threshold,
        "original_swept_lower_bound": report["result"]["motion"]["swept_clearance"][
            "minimum_self_lower_bound" if reason == "dynamic_swept_self_clearance"
            else "minimum_nonhand_environment_lower_bound"],
        "refined_continuous_numerical_segment_lower_bound": float(lower),
        "adaptive_refinement": asdict(adaptive) if adaptive is not None else None,
        "minimum_sampled_clearance": float(clearances[limiting]),
        "minimum_sampled_fraction": limiting / args.segments,
        "limiting_bodies": bodies[limiting],
        "original_rollout_passed": report["result"]["passed"],
        "full_execution_certified": False,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x") as destination:
        json.dump(output, destination, indent=2, allow_nan=False)
    print(json.dumps({key: value for key, value in output.items()
        if key not in ("source_assets_sha256",)}, indent=2))


if __name__ == "__main__":
    main()
