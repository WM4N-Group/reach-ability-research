"""Screen skipped approach waypoints in recorded Isaac poses with MuJoCo geometry."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from unittest.mock import patch

import mujoco
import numpy as np
import torch


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sample_frames(trace: list[dict], stage: int, per_stage: int) -> list[dict]:
    frames = [frame for frame in trace if frame["safe_approach_index"] == stage]
    if not frames:
        raise ValueError(f"No frames for stage {stage}")
    positions = np.linspace(0, len(frames) - 1, per_stage).round().astype(int)
    return [frames[index] for index in sorted(set(positions))]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-mujoco-root", type=Path, required=True)
    parser.add_argument("--approach", type=Path, required=True)
    parser.add_argument("--plan", type=Path, action="append", required=True)
    parser.add_argument("--report", type=Path, action="append", required=True)
    parser.add_argument("--first-skip", type=int, default=15)
    parser.add_argument("--last-skip", type=int, default=19)
    parser.add_argument("--edge-start-index", type=int)
    parser.add_argument("--edge-end-index", type=int)
    parser.add_argument("--samples-per-stage", type=int, default=2)
    parser.add_argument("--joint-increment-rad", type=float, default=0.02)
    parser.add_argument("--box-shift-x-m", type=float, default=0.0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if (args.output.exists() or len(args.plan) != len(args.report) or args.samples_per_stage < 1
            or not 0.005 <= args.joint_increment_rad <= 0.04
            or not -0.10 <= args.box_shift_x_m <= 0.10):
        parser.error("Use matched plans/reports, a new output, and bounded interpolation")

    approach = json.loads(args.approach.read_text())
    waypoints = np.asarray(approach["waypoints"], dtype=float)
    if waypoints.shape != (21, 6):
        raise ValueError("Expected the 21-waypoint frozen approach and interior skip indices")
    if (args.edge_start_index is None) != (args.edge_end_index is None):
        parser.error("Specify both edge endpoints")
    if args.edge_start_index is not None:
        if not 1 <= args.edge_start_index < args.edge_end_index - 1 < len(waypoints) - 1:
            parser.error("The edge must skip at least one interior waypoint and retain the final waypoint")
        edges = [(args.edge_start_index, args.edge_end_index)]
    else:
        if not 2 <= args.first_skip <= args.last_skip < len(waypoints) - 1:
            parser.error("Recorded traces have no stage 0; screen skip indices 2 through 19")
        edges = [(skip - 1, skip + 1) for skip in range(args.first_skip, args.last_skip + 1)]
    cases = []
    for plan_path, report_path in zip(args.plan, args.report, strict=True):
        plan = json.loads(plan_path.read_text())
        report = json.loads(report_path.read_text())
        if plan["approach_sha256"] != digest(args.approach) or plan["inspect_env_index"] != report["inspect_env_index"]:
            raise ValueError("Approach or inspected environment differs from the frozen plan")
        for relative, key in (("robots/go2_piper/go2piper.xml", "geometry_scene_sha256"),
                              ("deploy/piper_robot_profile.json", "geometry_robot_profile_sha256"),
                              ("deploy/piper_collision_profile.json", "geometry_collision_profile_sha256")):
            if digest(args.source_mujoco_root / relative) != plan[key]:
                raise ValueError(f"Geometry asset differs from the frozen plan: {relative}")
        names = report["joint_names"]
        if len(names) != 18 or len(set(names)) != 18 or not set(f"joint{i}" for i in range(1, 7)) <= set(names):
            raise ValueError("Unexpected robot joint mapping")
        cases.append((plan_path, report_path, report))

    sys.path.insert(0, str(args.source_mujoco_root))
    from reconfigurable_navigation.piper_box_runtime import make_episode
    from reconfigurable_navigation.piper_locomotion_runtime import JOINT_NAMES

    if any(set(report["joint_names"]) != set(JOINT_NAMES) for _, _, report in cases):
        raise ValueError("Frozen report and source runtime joint names differ")

    with patch("reconfigurable_navigation.climb_runtime.torch.jit.load", return_value=torch.nn.Identity()):
        runtime = make_episode("push", "geometry-only.pt", 1708, push_ik_mode="pose", native_collisions=True)
    model, data, arm = runtime.model, runtime.data, runtime.arm
    box_geom = arm.box_geom
    results = []
    for start, end in edges:
        first, second = waypoints[start], waypoints[end]
        count = max(1, int(np.ceil(np.max(np.abs(second - first)) / args.joint_increment_rad)))
        minimum_protected = (float("inf"), None)
        minimum_box = (float("inf"), None)
        largest_fk_error = 0.0
        state_count = 0
        for _, report_path, report in cases:
            env = report["inspect_env_index"]
            trace = report[f"trace_env{env}"]
            frames = [frame for stage in range(start, end + 1)
                      for frame in sample_frames(trace, stage, args.samples_per_stage)]
            joint_names = report["joint_names"]
            for frame in frames:
                named = dict(zip(joint_names, frame["full_joint_position"], strict=True))
                data.qpos[:3] = frame["robot_position"]
                data.qpos[3:7] = frame["robot_quaternion"]
                data.qpos[runtime.joint_qpos_adr] = [named[name] for name in JOINT_NAMES]
                data.joint("push_box_joint").qpos[:3] = frame["box_position"]
                data.joint("push_box_joint").qpos[0] += args.box_shift_x_m
                data.joint("push_box_joint").qpos[3:7] = frame["box_quaternion"]
                mujoco.mj_forward(model, data)
                fk_error = float(np.linalg.norm(arm.hand_position() - frame["hand_position"]))
                largest_fk_error = max(largest_fk_error, fk_error)
                if fk_error >= 1e-3:
                    raise ValueError(f"Isaac/MuJoCo hand FK mismatch at env {env} step {frame['step']}: {fk_error}")
                state_count += 1
                for fraction in np.linspace(0.0, 1.0, count + 1):
                    data.qpos[arm.arm_qpos] = first * (1.0 - fraction) + second * fraction
                    mujoco.mj_forward(model, data)
                    protected = min(float(mujoco.mj_geomDistance(model, data, a, b, 1.0, None))
                                    for a in arm.collision_arm_geoms for b in arm.collision_protected_geoms)
                    box = min(float(mujoco.mj_geomDistance(model, data, a, box_geom, 1.0, None))
                              for a in arm.collision_arm_geoms)
                    state = {"env": env, "step": frame["step"], "fraction": round(float(fraction), 4)}
                    if protected < minimum_protected[0]:
                        minimum_protected = (protected, state)
                    if box < minimum_box[0]:
                        minimum_box = (box, state)
        results.append({
            "skip_waypoint_index": start + 1 if end == start + 2 else None,
            "skipped_waypoint_indices": list(range(start + 1, end)),
            "edge_start_index": start,
            "edge_end_index": end,
            "interpolation_segments": count,
            "sampled_recorded_states": state_count,
            "max_fk_error_m": largest_fk_error,
            "minimum_protected_clearance_m": minimum_protected[0],
            "minimum_protected_state": minimum_protected[1],
            "minimum_box_clearance_m": minimum_box[0],
            "minimum_box_state": minimum_box[1],
            "static_pass": minimum_protected[0] >= 0.02 and minimum_box[0] >= 0.01,
        })
    output = {
        "schema_version": 1,
        "scope": "Recorded-pose MuJoCo geometry screen, not a dynamic or support certificate",
        "approach_sha256": digest(args.approach),
        "source_scene_sha256": digest(args.source_mujoco_root / "robots/go2_piper/go2piper.xml"),
        "source_runtime_sha256": digest(args.source_mujoco_root / "reconfigurable_navigation/box_push_runtime.py"),
        "source_collision_profile_sha256": digest(args.source_mujoco_root / "deploy/piper_collision_profile.json"),
        "cases": [{"plan_sha256": digest(plan), "report_sha256": digest(report),
                   "env": data["inspect_env_index"]} for plan, report, data in cases],
        "samples_per_stage": args.samples_per_stage,
        "joint_increment_rad": args.joint_increment_rad,
        "box_shift_x_m": args.box_shift_x_m,
        "protected_minimum_m": 0.02,
        "box_minimum_m": 0.01,
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"output": str(args.output),
                      "pass_indices": [row["skip_waypoint_index"] for row in results
                                       if row["static_pass"] and row["skip_waypoint_index"] is not None],
                      "pass_edges": [[row["edge_start_index"], row["edge_end_index"]]
                                     for row in results if row["static_pass"]]}))


if __name__ == "__main__":
    main()
