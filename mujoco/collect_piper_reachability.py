"""Collect provenance-bound PIPER position-IK and self-clearance labels."""

from __future__ import annotations

import argparse
from itertools import product
import json
from pathlib import Path
import sys

import mujoco
import numpy as np
import torch

from check_piper_startup import sha256
from reconfigurable_navigation.piper_box_runtime import make_episode
from reconfigurable_navigation.piper_locomotion_runtime import PiperLocomotionRuntime
from reconfigurable_navigation.piper_robot_profile import PROFILE_PATH
from reconfigurable_navigation.reachability import (
    PiperArmClearanceChecker,
    PiperPositionReachabilityOracle,
    PiperQuasiStaticSupportChecker,
    PiperSelfClearanceChecker,
    ReachabilityQuery,
    sample_base_pose_perturbations,
)


def _offset_grid(x_offsets: list[float], y_offsets: list[float], z_offsets: list[float]) -> tuple[np.ndarray, ...]:
    return tuple(
        np.array(offset, dtype=np.float64)
        for offset in product(x_offsets, y_offsets, z_offsets)
    )


def _source_hashes(
    *,
    config_path: Path,
    policy_path: Path,
    scene_path: Path,
    scene: str,
) -> dict[str, str]:
    root = Path(__file__).resolve().parent
    sources = {
        "collector": Path(__file__),
        "profile": PROFILE_PATH,
        "runtime": root / "reconfigurable_navigation/piper_locomotion_runtime.py",
        "oracle": root / "reconfigurable_navigation/reachability/oracle.py",
        "clearance": root / "reconfigurable_navigation/reachability/clearance.py",
        "sampling": root / "reconfigurable_navigation/reachability/sampling.py",
        "config": config_path,
        "policy": policy_path,
        "scene": scene_path,
    }
    if scene == "push-box":
        sources["push_box_runtime"] = root / "reconfigurable_navigation/piper_box_runtime.py"
    return {name: sha256(path) for name, path in sources.items()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--scene-case", required=True)
    parser.add_argument("--split", choices=("calibration", "test"), required=True)
    parser.add_argument("--scene", choices=("empty", "push-box"), default="empty")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--base-pose", type=float, nargs=3, default=(0.0, 0.0, 0.0))
    parser.add_argument("--target-center", type=float, nargs=3)
    parser.add_argument("--target-x-offsets", type=float, nargs="+", default=(0.0,))
    parser.add_argument("--target-y-offsets", type=float, nargs="+", default=(0.0,))
    parser.add_argument("--target-z-offsets", type=float, nargs="+", default=(0.0,))
    parser.add_argument("--base-x-offsets", type=float, nargs="+", default=(0.0,))
    parser.add_argument("--base-y-offsets", type=float, nargs="+", default=(0.0,))
    parser.add_argument("--base-yaw-offsets", type=float, nargs="+", default=(0.0,))
    parser.add_argument("--required-self-clearance", type=float, default=0.05)
    parser.add_argument("--required-environment-clearance", type=float, default=0.05)
    parser.add_argument("--required-joint-limit-margin", type=float, default=0.05)
    parser.add_argument("--required-support-margin", type=float, default=0.02)
    parser.add_argument("--support-settle-seconds", type=float, default=2.0)
    parser.add_argument("--push-box-position", type=float, nargs=3)
    parser.add_argument("--push-box-size", type=float, nargs=3)
    parser.add_argument("--push-box-yaw", type=float, default=0.0)
    parser.add_argument("--push-box-height", type=float, default=0.20)
    args = parser.parse_args()
    if args.seed < 0:
        parser.error("seed must be non-negative")
    if args.output_json.exists():
        parser.error(f"Refusing to overwrite {args.output_json}")
    if args.required_self_clearance < 0.0:
        parser.error("required-self-clearance must be non-negative")
    if args.required_environment_clearance < 0.0:
        parser.error("required-environment-clearance must be non-negative")
    if args.required_joint_limit_margin < 0.0:
        parser.error("required-joint-limit-margin must be non-negative")
    if args.required_support_margin < 0.0:
        parser.error("required-support-margin must be non-negative")
    if args.support_settle_seconds < 0.0:
        parser.error("support-settle-seconds must be non-negative")
    if args.push_box_height <= 0.0:
        parser.error("push-box-height must be positive")
    if args.push_box_size is not None and (
        np.any(np.asarray(args.push_box_size, dtype=np.float64) <= 0.0)
    ):
        parser.error("push-box-size values must be positive")

    torch.set_num_threads(1)
    nominal_base_pose = np.asarray(args.base_pose, dtype=np.float64)
    reference_runtime = PiperLocomotionRuntime(
        seed=args.seed,
        profile_path=PROFILE_PATH,
    )
    runtime = reference_runtime
    environment_clearance = None
    scene_definition: dict[str, object] = {"kind": "empty"}
    push_box_qpos: np.ndarray | None = None
    if args.scene == "push-box":
        box_size = np.asarray(
            args.push_box_size
            if args.push_box_size is not None
            else (1.20, 1.20, args.push_box_height),
            dtype=np.float64,
        )
        runtime = make_episode(
            "push",
            reference_runtime.policy_path,
            seed=args.seed,
            height=args.push_box_height,
        )
        box_geometry = runtime.model.geom("push_box").id
        runtime.model.geom_size[box_geometry] = box_size / 2.0
        mujoco.mj_setConst(runtime.model, runtime.data)
        box_position = np.asarray(
            args.push_box_position
            if args.push_box_position is not None
            else (1.10, 0.0, box_size[2] / 2.0),
            dtype=np.float64,
        )
        push_box_qpos = np.array(
            [
                *box_position,
                np.cos(args.push_box_yaw / 2.0),
                0.0,
                0.0,
                np.sin(args.push_box_yaw / 2.0),
            ],
            dtype=np.float64,
        )
        scene_definition = {
            "kind": "push-box",
            "object_body": "push_box",
            "position": box_position.tolist(),
            "size": box_size.tolist(),
            "yaw": args.push_box_yaw,
            "placement_after_settle": True,
        }
    for _ in range(round(args.support_settle_seconds / runtime.control_dt)):
        runtime.hold_default()
    if push_box_qpos is not None:
        box_qpos = runtime.data.joint("push_box_joint").qpos
        box_qpos[:] = push_box_qpos
        runtime.data.joint("push_box_joint").qvel.fill(0.0)
        mujoco.mj_forward(runtime.model, runtime.data)
        environment_clearance = PiperArmClearanceChecker(
            runtime,
            protected_body_names=frozenset({"push_box"}),
        )
    oracle = PiperPositionReachabilityOracle(runtime)
    clearance = PiperSelfClearanceChecker(runtime)
    support = PiperQuasiStaticSupportChecker(runtime)
    target_center = (
        np.asarray(args.target_center, dtype=np.float64)
        if args.target_center is not None
        else oracle.end_effector_position(
            ReachabilityQuery(nominal_base_pose, np.zeros(3))
        )
    )
    target_offsets = _offset_grid(
        args.target_x_offsets,
        args.target_y_offsets,
        args.target_z_offsets,
    )
    base_offsets = _offset_grid(
        args.base_x_offsets,
        args.base_y_offsets,
        args.base_yaw_offsets,
    )
    records: list[dict[str, object]] = []
    for target_offset in target_offsets:
        target_position = target_center + target_offset
        sample_set = sample_base_pose_perturbations(
            oracle,
            nominal_base_pose,
            target_position,
            base_offsets,
            scene_case=args.scene_case,
            split=args.split,
            clearance_checker=clearance,
            required_self_clearance=args.required_self_clearance,
            environment_clearance_checker=environment_clearance,
            required_environment_clearance=args.required_environment_clearance,
            support_checker=support,
            required_support_margin=args.required_support_margin,
            required_joint_limit_margin=args.required_joint_limit_margin,
        )
        for record in sample_set.records():
            record["target_offset"] = target_offset.tolist()
            records.append(record)
    feasible = sum(record["kinematic_feasible"] for record in records)
    self_clearance_safe = sum(record["self_clearance_safe"] is True for record in records)
    environment_clearance_safe = sum(
        record["environment_clearance_safe"] is True for record in records
    )
    joint_limit_safe = sum(record["joint_limit_safe"] is True for record in records)
    support_safe = sum(record["support_safe"] is True for record in records)
    scope = (
        "fixed-base position IK and PIPER arm-to-body/front-leg self-clearance"
        if args.scene == "empty"
        else "fixed-base position IK, PIPER self-clearance, and arm-to-push-box clearance"
    )
    report = {
        "schema_version": 1,
        "scope": f"{scope}; no support or skill-handoff validation",
        "scene_case": args.scene_case,
        "split": args.split,
        "scene": scene_definition,
        "nominal_base_pose": nominal_base_pose.tolist(),
        "target_center": target_center.tolist(),
        "target_offset_count": len(target_offsets),
        "base_pose_offset_count": len(base_offsets),
        "required_self_clearance": args.required_self_clearance,
        "required_environment_clearance": args.required_environment_clearance,
        "required_joint_limit_margin": args.required_joint_limit_margin,
        "summary": {
            "total": len(records),
            "kinematic_feasible": feasible,
            "kinematic_unreachable": len(records) - feasible,
            "joint_limit_safe": joint_limit_safe,
            "joint_limit_unsafe_or_unreachable": len(records) - joint_limit_safe,
            "support_safe": support_safe,
            "support_unsafe_or_unchecked": len(records) - support_safe,
            "self_clearance_safe": self_clearance_safe,
            "self_clearance_unsafe_or_unchecked": len(records) - self_clearance_safe,
            "environment_clearance_safe": environment_clearance_safe,
            "environment_clearance_unsafe_or_unchecked": (
                len(records) - environment_clearance_safe
            ),
        },
        "provenance": {
            "seed": args.seed,
            "profile_path": str(PROFILE_PATH),
            "source_sha256": _source_hashes(
                config_path=reference_runtime.config_path,
                policy_path=reference_runtime.policy_path,
                scene_path=reference_runtime.scene_path,
                scene=args.scene,
            ),
            "python": sys.version,
            "python_executable": sys.executable,
            "mujoco": mujoco.__version__,
            "numpy": np.__version__,
            "torch": torch.__version__,
            "torch_threads": torch.get_num_threads(),
            "support_settle_seconds": args.support_settle_seconds,
        },
        "records": records,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x") as destination:
        json.dump(report, destination, indent=2, allow_nan=False)
        destination.write("\n")
    print(json.dumps({"summary": report["summary"], "output": str(args.output_json)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())