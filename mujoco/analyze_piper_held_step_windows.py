"""Audit sampled joint hold gates in existing paired target-step reports."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from analyze_piper_wbc_holdability import window_maxima
from check_piper_startup import sha256


def sampled_window(trace: list[dict], contract: dict, *, start_time: float | None,
                   deadline_seconds: float) -> dict:
    samples = [item for item in trace if item["wbc_command_ramp_fraction"] >= 1.0
               and (start_time is None or item["time"] > start_time)]
    times = np.asarray([item["time"] for item in samples], dtype=float)
    if len(times) > 1 and not np.allclose(np.diff(times), 0.1, rtol=0, atol=1e-8):
        raise ValueError("Expected uninterrupted 100 ms sampled trace")
    width = round(contract["hold_seconds"] / 0.1)
    if (width != 50 or not np.isclose(width * 0.1, contract["hold_seconds"])
            or contract["hand_tracking_tolerance"] != 0.005
            or contract["arm_velocity_tolerance"] != 0.15):
        raise ValueError("Unexpected hold gate contract")
    position = np.asarray([item["hand_position_error"] for item in samples], dtype=float)
    speed = np.asarray([item["arm_speed"] for item in samples], dtype=float)
    if (not np.isfinite(position).all() or not np.isfinite(speed).all()
            or np.any(position < 0) or np.any(speed < 0)):
        raise ValueError("Invalid sampled gate values")
    ratio = np.maximum(position / contract["hand_tracking_tolerance"],
                       speed / contract["arm_velocity_tolerance"])
    passing = ratio <= 1.0
    longest = current = 0
    for value in passing:
        current = current + 1 if value else 0
        longest = max(longest, current)
    output = {
        "sample_count": len(samples),
        "first_sample_delay_seconds": float(times[0] - start_time)
        if start_time is not None and len(times) else None,
        "best_single_joint_ratio": float(np.min(ratio)) if len(ratio) else None,
        "longest_joint_gate_run_samples": longest,
        "position_pass_samples": int(np.count_nonzero(
            position <= contract["hand_tracking_tolerance"])),
        "speed_pass_samples": int(np.count_nonzero(
            speed <= contract["arm_velocity_tolerance"])),
        "joint_pass_samples": int(np.count_nonzero(passing)),
        "best_50_sample_joint_ratio": None,
        "best_50_sample_start_delay_seconds": None,
        "best_50_sample_joint_ratio_within_deadline": None,
        "first_passing_50_sample_start_delay_seconds": None,
    }
    if len(samples) >= width:
        maxima = window_maxima(ratio, width)
        best = int(np.argmin(maxima))
        starts = times[:len(maxima)] - (start_time or 0.0)
        eligible = starts <= deadline_seconds + 1e-8
        passing_windows = np.flatnonzero((maxima <= 1.0) & eligible)
        output.update({
            "best_50_sample_joint_ratio": float(maxima[best]),
            "best_50_sample_start_delay_seconds": float(starts[best]),
            "best_50_sample_joint_ratio_within_deadline": (
                float(np.min(maxima[eligible])) if np.any(eligible) else None),
            "first_passing_50_sample_start_delay_seconds": (
                float(starts[passing_windows[0]]) if len(passing_windows) else None),
        })
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch", nargs=2, action="append", metavar=("SUMMARY", "REPORT_DIR"),
                        required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error("Require a new output path")
    entries = []
    sources = set()
    for summary_name, directory_name in args.batch:
        summary_path, directory = Path(summary_name), Path(directory_name)
        summary = json.loads(summary_path.read_text())
        for baseline in summary["baselines"]:
            seed = baseline["seed"]
            candidate = next((entry for entry in summary["entries"]
                              if entry["seed"] == seed and entry["phase"] == "x_minus_12mm"),
                             None)
            if candidate is None:
                raise ValueError(f"Missing x-12 mm candidate for seed {seed}")
            baseline_path = directory / f"seed{seed}-baseline-v1.json"
            candidate_path = directory / f"seed{seed}-x_minus_12mm-v1.json"
            if (sha256(baseline_path) != baseline["report_sha256"]
                    or sha256(candidate_path) != candidate["report_sha256"]
                    or candidate["baseline_sha256"] != baseline["report_sha256"]):
                raise ValueError(f"Report hash mismatch for seed {seed}")
            original = json.loads(baseline_path.read_text())
            stepped = json.loads(candidate_path.read_text())
            if (original["seed"] != seed or stepped["seed"] != seed
                    or original["protocol_sha256"] != summary["protocol_sha256"]
                    or stepped["protocol_sha256"] != summary["protocol_sha256"]
                    or original["source_sha256"] != stepped["source_sha256"]
                    or stepped["source_sha256"] != summary["source_sha256"]
                    or original["result"]["reason"] != baseline["reason"]
                    or stepped["result"]["reason"] != candidate["reason"]):
                raise ValueError(f"Source or outcome mismatch for seed {seed}")
            for path, expected in stepped["source_sha256"].items():
                if sha256(Path(path)) != expected:
                    raise ValueError(f"Recorded source changed: {path}")
            sources.add(summary["protocol_sha256"])
            baseline_event = original["result"]["motion"]["target_step_event"]
            event = stepped["result"]["motion"]["target_step_event"]
            if ((baseline_event is None) != (event is None)
                    or (event is not None and (not event["applied"]
                        or not candidate["matched_pre_step_state"]))
                    or (baseline_event is not None and baseline_event["applied"])):
                raise ValueError(f"Invalid paired probe for seed {seed}")
            baseline_window = sampled_window(original["result"]["motion"]["trace"],
                                             original["arguments"], start_time=None,
                                             deadline_seconds=10.0)
            post_step = (sampled_window(stepped["result"]["motion"]["trace"],
                                        stepped["arguments"], start_time=event["time"],
                                        deadline_seconds=10.0) if event is not None else None)
            entries.append({
                "seed": seed,
                "layout": baseline["layout"],
                "baseline_reason": baseline["reason"],
                "baseline_entered_probe": baseline_event is not None,
                "baseline_sampled_gates": baseline_window,
                "candidate_reason": candidate["reason"],
                "matched_pre_step_state": candidate["matched_pre_step_state"],
                "step_time": event["time"] if event is not None else None,
                "post_step_sampled_gates": post_step,
                "reported_final_hold_start_delay_seconds": (
                    candidate["final_hold_start_time"] - event["time"]
                    if event is not None and candidate["final_hold_start_time"] is not None
                    else None),
                "baseline_report_sha256": baseline["report_sha256"],
                "candidate_report_sha256": candidate["report_sha256"],
                "summary_sha256": sha256(summary_path),
            })
    if len(entries) != 16 or len({item["seed"] for item in entries}) != 16:
        raise ValueError("Expected sixteen distinct paired seeds")
    output = {
        "schema_version": 1,
        "scope": "Retrospective 100 ms sampled position/speed gates; not full-step acceptance",
        "script_sha256": sha256(Path(__file__)),
        "protocol_sha256": sorted(sources),
        "window_samples": 50,
        "hold_start_deadline_seconds": 10.0,
        "entries": sorted(entries, key=lambda item: item["seed"]),
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x") as destination:
        json.dump(output, destination, indent=2, allow_nan=False)
        destination.write("\n")
    print(json.dumps({"pairs": len(entries),
                      "baseline_probes": sum(item["baseline_entered_probe"] for item in entries),
                      "candidate_completions": sum(item["candidate_reason"] == "completed"
                                                   for item in entries)}))


if __name__ == "__main__":
    main()
