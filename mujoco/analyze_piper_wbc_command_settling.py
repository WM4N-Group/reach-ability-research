"""Compare recorded WBC world commands with the executed precontact hand path."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import mujoco
import numpy as np

from analyze_piper_wbc_settling import analyze as analyze_gates
from check_piper_startup import sha256
from reconfigurable_navigation.piper_locomotion_runtime import DEPLOY
from reconfigurable_navigation.reachability.scenes import make_movable_box_navigation_runtime


def summarize(path: Path, runtime) -> dict[str, object]:
    report = json.loads(path.read_text())
    if not report["replay_comparison"]["same_result"]:
        raise ValueError(f"Frozen replay mismatch: {path}")
    trace = report["trace"]
    archive = path.parent / Path(trace["path"]).name
    if sha256(archive) != trace["sha256"]:
        raise ValueError(f"Trace hash mismatch: {archive}")
    with np.load(archive, allow_pickle=False) as payload:
        qpos = payload["qpos"]
        times = payload["time"]
    if (qpos.shape != (trace["samples"], runtime.model.nq)
            or times.shape != (trace["samples"],)
            or not np.isfinite(qpos).all() or not np.isfinite(times).all()
            or not np.all(np.diff(times) > 0)):
        raise ValueError(f"Invalid recorded states: {archive}")
    target = np.asarray(report["result"]["candidate"]["target_world"], dtype=float)
    hand_id = runtime.model.body("end_effector").id
    data = mujoco.MjData(runtime.model)
    records = []
    for item in report["result"]["motion"]["trace"]:
        if item["commanded_world_pose"] is None:
            raise ValueError("Expected a WBC world pose command")
        index = int(np.searchsorted(times, item["time"]))
        if index <= 0 or index >= len(times) or abs(times[index] - item["time"]) > 1e-8:
            raise ValueError(f"Command and physics trace times differ: {path}")
        # The original monitor reads geometry cached before this physics update.
        data.qpos[:] = qpos[index - 1]
        mujoco.mj_kinematics(runtime.model, data)
        hand = data.xpos[hand_id].copy()
        hand_error = float(np.linalg.norm(hand - target))
        if not np.isclose(hand_error, item["hand_position_error"], rtol=0, atol=1e-8):
            raise ValueError(f"Original hand error not reproduced: {path}")
        command = np.asarray(item["commanded_world_pose"][:3], dtype=float)
        records.append({
            "time": item["time"],
            "after_ramp": item["wbc_command_ramp_fraction"] >= 1.0,
            "hand_position": hand,
            "command_position": command,
            "hand_error": hand_error,
            "command_to_hand": float(np.linalg.norm(command - hand)),
            "command_to_target": float(np.linalg.norm(command - target)),
            "arm_speed": item["arm_speed"],
            "orientation_error": item["end_effector_orientation_error"],
            "hand_gate": item["hand_gate_passed"],
            "command_held": item["wbc_command_held"],
        })
    if not records:
        raise ValueError(f"No control trace: {path}")
    after_ramp = [item for item in records if item["after_ramp"]]
    if not after_ramp:
        raise ValueError(f"Command ramp did not finish: {path}")
    late = [item for item in records if item["time"] >= records[-1]["time"] - 5.0]
    contract = report["arguments"]
    position_threshold = contract["hand_tracking_tolerance"]
    speed_threshold = contract["arm_velocity_tolerance"]
    orientation_threshold = contract["orientation_tracking_tolerance"]

    def path_length(field: str) -> float:
        return float(sum(np.linalg.norm(right[field] - left[field])
                         for left, right in zip(late, late[1:])))

    return {
        "seed": report["result"]["seed"],
        "original_reason": report["result"]["reason"],
        "trace_json_sha256": sha256(path),
        "trace_npz_sha256": trace["sha256"],
        "control_samples_after_ramp": len(after_ramp),
        "late_window_seconds": 5.0,
        "late_window_control_samples": len(late),
        "late_command_path_length_m": path_length("command_position"),
        "late_hand_path_length_m": path_length("hand_position"),
        "late_command_net_displacement_m": float(np.linalg.norm(
            late[-1]["command_position"] - late[0]["command_position"])),
        "late_hand_net_displacement_m": float(np.linalg.norm(
            late[-1]["hand_position"] - late[0]["hand_position"])),
        "late_median_command_to_hand_m": float(np.median(
            [item["command_to_hand"] for item in late])),
        "late_median_command_to_target_m": float(np.median(
            [item["command_to_target"] for item in late])),
        "late_median_hand_error_m": float(np.median(
            [item["hand_error"] for item in late])),
        "late_median_arm_speed_rad_s": float(np.median(
            [item["arm_speed"] for item in late])),
        "late_command_held_samples": sum(item["command_held"] for item in late),
        "final_command_to_hand_m": records[-1]["command_to_hand"],
        "final_command_to_target_m": records[-1]["command_to_target"],
        "final_hand_error_m": records[-1]["hand_error"],
        "coarse_position_pass_samples": sum(
            item["hand_error"] <= position_threshold for item in after_ramp),
        "coarse_speed_pass_samples": sum(
            item["arm_speed"] <= speed_threshold for item in after_ramp),
        "coarse_orientation_pass_samples": sum(
            item["orientation_error"] <= orientation_threshold for item in after_ramp),
        "coarse_hand_gate_pass_samples": sum(item["hand_gate"] for item in after_ramp),
        "coarse_all_gate_pass_samples": sum(
            item["hand_error"] <= position_threshold
            and item["arm_speed"] <= speed_threshold
            and item["orientation_error"] <= orientation_threshold
            and item["hand_gate"] for item in after_ramp),
        "physics_position_speed_gates": analyze_gates(path, runtime),
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
    source_hashes = source["source_sha256"]
    for path, expected in source_hashes.items():
        if sha256(Path(path)) != expected:
            raise ValueError(f"Recorded source or asset changed: {path}")
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
        if report["source_sha256"] != source_hashes:
            raise ValueError(f"Recorded source set differs: {path}")
        if {key: value for key, value in report["arguments"].items()
                if key not in ("seed", "output_json")} != {
                    key: value for key, value in contract.items()
                    if key not in ("seed", "output_json")
                }:
            raise ValueError(f"Scene or control contract mismatch: {path}")
        entry = summarize(path, runtime)
        entries.append(entry)
        print(json.dumps({key: entry[key] for key in (
            "seed", "original_reason", "final_command_to_hand_m",
            "late_median_arm_speed_rad_s", "coarse_all_gate_pass_samples")}), flush=True)
    output = {
        "schema_version": 1,
        "scope": "Read-only WBC world-command and executed hand diagnostic; no control changes",
        "script_sha256": sha256(Path(__file__)),
        "entries": entries,
    }
    with args.output_json.open("x") as destination:
        json.dump(output, destination, indent=2, allow_nan=False)


if __name__ == "__main__":
    main()
