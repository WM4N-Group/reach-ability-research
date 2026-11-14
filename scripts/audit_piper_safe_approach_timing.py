"""Audit the safe-approach asset and settling time in an Isaac control-step trace."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ARM_JOINTS = tuple(f"joint{i}" for i in range(1, 7))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(plan_path: Path, report_path: Path, approach_path: Path) -> dict:
    plan = json.loads(plan_path.read_text())
    report = json.loads(report_path.read_text())
    approach = json.loads(approach_path.read_text())
    asset_hash = sha256(approach_path)
    if asset_hash != plan["approach_sha256"]:
        raise ValueError("Approach asset does not match the frozen evaluation plan")

    waypoints = approach["waypoints"]
    position_limit = approach["settle_position_tolerance_rad"]
    velocity_limit = approach["settle_velocity_tolerance_rad_s"]
    joint_indices = [report["joint_names"].index(name) for name in ARM_JOINTS]
    env_index = report["inspect_env_index"]
    trace = report[f"trace_env{env_index}"]
    dt = report["failure_history_step_dt"]
    if (env_index != plan["inspect_env_index"] or not trace or len(waypoints) < 2 or dt <= 0
            or any(len(waypoint) != len(ARM_JOINTS) for waypoint in waypoints)):
        raise ValueError("Expected a nonempty control-step trace and an approach path")
    indices = [frame["safe_approach_index"] for frame in trace]
    if any(index < 1 or index > len(waypoints) for index in indices) or indices != sorted(indices):
        raise ValueError("Approach index is out of range or not monotone")

    stages = []
    for index in range(1, len(waypoints)):
        frames = [frame for frame in trace if frame["safe_approach_index"] == index]
        if not frames:
            raise ValueError(f"No trace frames for approach waypoint {index}")
        errors = [max(abs(q - target) for q, target in zip(frame["arm_joint_position"], waypoints[index]))
                  for frame in frames]
        speeds = [max(abs(frame["full_joint_velocity"][joint]) for joint in joint_indices)
                  for frame in frames]
        position_ready = [frame["step"] for frame, error in zip(frames, errors) if error < position_limit]
        velocity_only_wait = sum(error < position_limit and speed >= velocity_limit
                                 for error, speed in zip(errors, speeds))
        stages.append({
            "waypoint_index": index,
            "start_step": frames[0]["step"],
            "last_step": frames[-1]["step"],
            "duration_s": round(len(frames) * dt, 4),
            "first_position_ready_step": min(position_ready) if position_ready else None,
            "position_ready_velocity_high_steps": velocity_only_wait,
            "position_ready_velocity_high_s": round(velocity_only_wait * dt, 4),
            "last_position_error_rad": round(errors[-1], 6),
            "last_max_joint_speed_rad_s": round(speeds[-1], 6),
            "min_reported_geometry_clearance_m": round(min(frame["geometry_clearance"] for frame in frames), 6),
        })
    if not any(frame["safe_approach_index"] == len(waypoints) for frame in trace):
        raise ValueError("Trace never completes the loaded approach path")
    return {
        "schema_version": 1,
        "scope": "Observed frozen trajectory only; velocity-high time is not proven removable",
        "plan_sha256": sha256(plan_path),
        "report_sha256": sha256(report_path),
        "approach_sha256": asset_hash,
        "inspect_env_index": env_index,
        "waypoint_count": len(waypoints),
        "control_step_dt_s": dt,
        "position_tolerance_rad": position_limit,
        "velocity_tolerance_rad_s": velocity_limit,
        "stages": stages,
        "total_approach_s": round(sum(stage["duration_s"] for stage in stages), 4),
        "total_position_ready_velocity_high_s": round(
            sum(stage["position_ready_velocity_high_s"] for stage in stages), 4),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--approach", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args.plan, args.report, args.approach), indent=2))


if __name__ == "__main__":
    main()
