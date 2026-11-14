"""Audit the original lagged-position and arm-speed gate from WBC traces."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import mujoco
import numpy as np

from check_piper_startup import sha256
from reconfigurable_navigation.piper_locomotion_runtime import DEPLOY
from reconfigurable_navigation.reachability.scenes import make_movable_box_navigation_runtime


def analyze(path: Path, runtime) -> dict[str, object]:
    report = json.loads(path.read_text())
    if not report["replay_comparison"]["same_result"]:
        raise ValueError(f"Replay mismatch: {path}")
    trace = report["trace"]
    archive = path.parent / Path(trace["path"]).name
    if sha256(archive) != trace["sha256"]:
        raise ValueError(f"Trace checksum mismatch: {archive}")
    with np.load(archive, allow_pickle=False) as payload:
        qpos = payload["qpos"]
        qvel = payload["qvel"]
        times = payload["time"]
    if (len(times) != trace["samples"] or qpos.shape != (len(times), runtime.model.nq)
            or qvel.shape != (len(times), runtime.model.nv)
            or not np.isfinite(qpos).all() or not np.isfinite(qvel).all()
            or not np.allclose(np.diff(times), trace["sim_dt"], rtol=0, atol=1e-10)):
        raise ValueError(f"Invalid physics trace: {path}")
    contract = report["arguments"]
    if contract["hand_point"] != "piper" or contract["arm_controller"] != "unified-wbc":
        raise ValueError(f"Unexpected control contract: {path}")
    target = np.asarray(report["result"]["candidate"]["target_world"], dtype=float)
    hand_id = runtime.model.body("end_effector").id
    arm_dofs = runtime.joint_dof_adr[12:]
    data = mujoco.MjData(runtime.model)
    errors = np.empty(len(times))
    refreshed_errors = np.empty(len(times))
    speeds = np.max(np.abs(qvel[:, arm_dofs]), axis=1)
    for index, position in enumerate(qpos):
        data.qpos[:] = position
        mujoco.mj_kinematics(runtime.model, data)
        refreshed_errors[index] = np.linalg.norm(data.xpos[hand_id] - target)
    errors[0] = refreshed_errors[0]
    errors[1:] = refreshed_errors[:-1]
    original_final_error = report["result"]["motion"]["final_hand_position_error"]
    if not np.isclose(errors[-1], original_final_error, rtol=0, atol=1e-8):
        raise ValueError(f"Original hand position gate not reproduced: {path}")
    after_ramp = times - times[0] >= contract["wbc_command_ramp_seconds"] - 1e-10
    near = errors <= contract["hand_tracking_tolerance"]
    slow = speeds <= contract["arm_velocity_tolerance"]
    overlap = after_ramp & near & slow
    position_pass = after_ramp & near
    speed_pass = after_ramp & slow
    longest = current = 0
    for value in overlap:
        current = current + 1 if value else 0
        longest = max(longest, current)
    return {
        "seed": report["result"]["seed"],
        "original_reason": report["result"]["reason"],
        "trace_json_sha256": sha256(path),
        "trace_npz_sha256": trace["sha256"],
        "sampling_seconds": float(trace["sim_dt"]),
        "after_ramp_samples": int(after_ramp.sum()),
        "position_pass_samples": int(np.count_nonzero(after_ramp & near)),
        "speed_pass_samples": int(np.count_nonzero(after_ramp & slow)),
        "joint_pass_samples": int(overlap.sum()),
        "longest_joint_pass_seconds": float(longest * trace["sim_dt"]),
        "minimum_speed_when_position_passed_rad_s": (
            float(np.min(speeds[position_pass])) if np.any(position_pass) else None
        ),
        "minimum_position_error_when_speed_passed_m": (
            float(np.min(errors[speed_pass])) if np.any(speed_pass) else None
        ),
        "minimum_after_ramp_position_error_m": float(np.min(errors[after_ramp])),
        "final_position_error_m": float(errors[-1]),
        "final_refreshed_position_error_m": float(refreshed_errors[-1]),
        "final_arm_speed_rad_s": float(speeds[-1]),
        "original_stable_seconds": report["result"]["motion"]["stable_seconds"],
        "original_hold_entries": report["result"]["motion"]["wbc_hold_entries"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trace-json", type=Path, nargs="+", required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error("Require a new output path")
    source = json.loads(args.trace_json[0].read_text())
    contract = source["arguments"]
    runtime = make_movable_box_navigation_runtime(
        seed=source["result"]["seed"],
        box_position=np.asarray(contract["static_box_position"]),
        box_size=np.asarray(contract["static_box_size"]),
        box_yaw=contract["static_box_yaw"],
        box_mass=contract["box_mass"],
        config_path=DEPLOY / "config_wbc.yaml",
        physics_substeps=contract["physics_substeps"],
    )
    entries = []
    for path in args.trace_json:
        report = json.loads(path.read_text())
        if {key: value for key, value in report["arguments"].items()
                if key not in ("seed", "output_json")} != {
                    key: value for key, value in contract.items()
                    if key not in ("seed", "output_json")
                }:
            raise ValueError(f"Scene or control contract mismatch: {path}")
        entry = analyze(path, runtime)
        entries.append(entry)
        print(json.dumps(entry), flush=True)
    output = {
        "scope": "Read-only position and speed necessary gate diagnostic; other gates excluded",
        "script_sha256": sha256(Path(__file__)),
        "entries": entries,
    }
    with args.output_json.open("x") as destination:
        json.dump(output, destination, indent=2, allow_nan=False)


if __name__ == "__main__":
    main()
