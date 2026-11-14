"""Audit the fixed first five seconds after matched held-target steps."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from check_piper_startup import sha256


def longest_run(flags: np.ndarray) -> int:
    longest = current = 0
    for flag in flags:
        current = current + 1 if flag else 0
        longest = max(longest, current)
    return longest


def path_metrics(points: np.ndarray) -> tuple[float, float]:
    return (float(np.linalg.norm(np.diff(points, axis=0), axis=1).sum()),
            float(np.linalg.norm(points[-1] - points[0])))


def summarize(report: dict, step_time: float, duration: float) -> dict:
    contract = report["arguments"]
    trace = report["result"]["motion"]["trace"]
    samples = [item for item in trace
               if step_time < item["time"] <= step_time + duration + 1e-8]
    times = np.asarray([item["time"] for item in samples], dtype=float)
    if (len(samples) != 50 or not np.allclose(np.diff(times), 0.1, rtol=0, atol=1e-8)
            or not np.isclose(times[-1] - step_time, duration, atol=0.1, rtol=0)
            or contract["hand_tracking_tolerance"] != 0.005
            or contract["arm_velocity_tolerance"] != 0.15):
        raise ValueError("Unexpected first-five-second trace or gate contract")
    command = np.asarray([item["commanded_world_pose"][:3] for item in samples])
    hand = np.asarray([item["hand_local"] for item in samples])
    error = np.asarray([item["hand_position_error"] for item in samples])
    speed = np.asarray([item["arm_speed"] for item in samples])
    if (command.shape != (50, 3) or hand.shape != (50, 3)
            or not all(np.isfinite(array).all() for array in (command, hand, error, speed))
            or np.any(error < 0) or np.any(speed < 0)):
        raise ValueError("Invalid sampled command or gate values")
    position_pass = error <= contract["hand_tracking_tolerance"]
    joint_pass = position_pass & (speed <= contract["arm_velocity_tolerance"])
    command_path, command_net = path_metrics(command)
    hand_path, hand_net = path_metrics(hand)
    return {
        "sample_count": len(samples),
        "first_sample_delay_seconds": float(times[0] - step_time),
        "last_sample_delay_seconds": float(times[-1] - step_time),
        "command_path_m": command_path,
        "command_net_m": command_net,
        "hand_local_path_m": hand_path,
        "hand_local_net_m": hand_net,
        "minimum_hand_error_m": float(np.min(error)),
        "maximum_hand_error_m": float(np.max(error)),
        "maximum_arm_speed_rad_s": float(np.max(speed)),
        "position_pass_samples": int(np.count_nonzero(position_pass)),
        "joint_pass_samples": int(np.count_nonzero(joint_pass)),
        "position_reentries": int(np.count_nonzero(position_pass[1:] & ~position_pass[:-1])),
        "longest_position_pass_samples": longest_run(position_pass),
        "longest_joint_pass_samples": longest_run(joint_pass),
        "held_command_samples": sum(bool(item["wbc_command_held"]) for item in samples),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol-json", type=Path, required=True)
    parser.add_argument("--report-dir", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error("Require a new output path")
    protocol = json.loads(args.protocol_json.read_text())
    if (sha256(Path(__file__)) != protocol["short_response_script_sha256"]
            or protocol["short_response_seconds"] != 5.0):
        raise ValueError("Analysis source or window changed")
    entries = []
    for batch in protocol["batches"]:
        for seed in batch["seeds"]:
            baseline_path = args.report_dir / f"seed{seed}-baseline-v1.json"
            baseline = json.loads(baseline_path.read_text())
            baseline_event = baseline["result"]["motion"]["target_step_event"]
            if (baseline["seed"] != seed or baseline["phase"] != "baseline"
                    or baseline["protocol_sha256"] != sha256(args.protocol_json)
                    or baseline["result"]["reason"] != "completed"
                    or baseline_event is None or baseline_event["applied"]):
                raise ValueError(f"Invalid baseline probe: {seed}")
            for phase, delta in protocol["offsets_m"].items():
                path = args.report_dir / f"seed{seed}-{phase}-v1.json"
                report = json.loads(path.read_text())
                event = report["result"]["motion"]["target_step_event"]
                comparison = report["baseline_comparison"]
                if (report["seed"] != seed or report["phase"] != phase
                        or report["offset_local_m"] != delta
                        or report["protocol_sha256"] != sha256(args.protocol_json)
                        or report["contract_source_sha256"] != batch["contract_sha256"]
                        or report["source_sha256"] != baseline["source_sha256"]
                        or event is None or not event["applied"]
                        or comparison["baseline_sha256"] != sha256(baseline_path)
                        or not all(comparison[key] for key in (
                            "same_nav_trace", "same_precontact_state", "same_pre_step_trace",
                            "same_pre_step_state"))):
                    raise ValueError(f"Unmatched candidate: {seed} {phase}")
                entries.append({
                    "seed": seed,
                    "layout": batch["name"],
                    "phase": phase,
                    "reason": report["result"]["reason"],
                    "step_time": event["time"],
                    "initial_step_hand_error_m": event["instantaneous_hand_error_m"],
                    "baseline_sha256": sha256(baseline_path),
                    "report_sha256": sha256(path),
                    **summarize(report, event["time"], protocol["short_response_seconds"]),
                })
    output = {
        "schema_version": 1,
        "scope": "Fixed first-five-second 100 ms sampled diagnostic; not a safety certificate",
        "protocol_sha256": sha256(args.protocol_json),
        "script_sha256": sha256(Path(__file__)),
        "entries": entries,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x") as destination:
        json.dump(output, destination, indent=2, allow_nan=False)
        destination.write("\n")
    print(json.dumps({"pairs": len(entries),
                      "completed": sum(item["reason"] == "completed" for item in entries)}))


if __name__ == "__main__":
    main()
