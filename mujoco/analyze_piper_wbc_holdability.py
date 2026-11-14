"""Measure the best recorded window for joint position and arm-speed gates."""

from __future__ import annotations

import argparse
from collections import deque
import json
from pathlib import Path

import numpy as np

from check_piper_startup import sha256


def window_maxima(values: np.ndarray, width: int) -> np.ndarray:
    """Return all fixed-width maxima in linear time."""
    if width < 1 or width > len(values):
        raise ValueError("Invalid window width")
    candidates = deque()
    result = np.empty(len(values) - width + 1)
    for index, value in enumerate(values):
        while candidates and values[candidates[-1]] <= value:
            candidates.pop()
        candidates.append(index)
        while candidates[0] <= index - width:
            candidates.popleft()
        if index >= width - 1:
            result[index - width + 1] = values[candidates[0]]
    return result


def summarize(path: Path) -> dict[str, object]:
    report = json.loads(path.read_text())
    contract = report["arguments"]
    if (contract["arm_controller"] != "unified-wbc"
            or not contract["diagnose_designated_hand_approach"]
            or report["result"]["seed"] != contract["seed"]):
        raise ValueError(f"Unexpected WBC contract: {path}")
    trace = report["result"]["motion"]["trace"]
    after_ramp = [item for item in trace if item["wbc_command_ramp_fraction"] >= 1.0]
    times = np.asarray([item["time"] for item in after_ramp], dtype=float)
    if len(times) < 2 or not np.allclose(np.diff(times), 0.1, rtol=0, atol=1e-8):
        raise ValueError(f"Expected 100 ms control trace after ramp: {path}")
    width = round(contract["hold_seconds"] / 0.1)
    if not np.isclose(width * 0.1, contract["hold_seconds"], rtol=0, atol=1e-10):
        raise ValueError(f"Hold duration does not align with 100 ms trace: {path}")
    position = np.asarray([item["hand_position_error"] for item in after_ramp])
    speed = np.asarray([item["arm_speed"] for item in after_ramp])
    orientation = np.asarray([item["end_effector_orientation_error"] for item in after_ramp])
    hand_gate = np.asarray([item["hand_gate_passed"] for item in after_ramp], dtype=bool)
    if (not np.isfinite(position).all() or not np.isfinite(speed).all()
            or not np.isfinite(orientation).all()
            or np.any(position < 0) or np.any(speed < 0)):
        raise ValueError(f"Invalid recorded gate values: {path}")
    position_ratio = position / contract["hand_tracking_tolerance"]
    speed_ratio = speed / contract["arm_velocity_tolerance"]
    joint_ratio = np.maximum(position_ratio, speed_ratio)
    position_window = window_maxima(position, width)
    speed_window = window_maxima(speed, width)
    ratio_window = window_maxima(joint_ratio, width)
    index = int(np.argmin(ratio_window))
    minimum_speed_frozen_position = speed_window[position_window <= contract["hand_tracking_tolerance"]]
    minimum_position_frozen_speed = position_window[speed_window <= contract["arm_velocity_tolerance"]]
    longest = current = 0
    for value in joint_ratio <= 1.0:
        current = current + 1 if value else 0
        longest = max(longest, current)
    return {
        "seed": contract["seed"],
        "original_reason": report["result"]["reason"],
        "original_stable_seconds": report["result"]["motion"]["stable_seconds"],
        "input_sha256": sha256(path),
        "observed_after_ramp_samples": len(after_ramp),
        "sample_spacing_seconds": 0.1,
        "window_samples": width,
        "best_single_sample_joint_ratio": float(np.min(joint_ratio)),
        "best_window_joint_ratio": float(ratio_window[index]),
        "best_window_start_time": float(times[index]),
        "best_window_end_time": float(times[index + width - 1]),
        "best_window_maximum_position_error_m": float(position_window[index]),
        "best_window_maximum_arm_speed_rad_s": float(speed_window[index]),
        "longest_joint_gate_run_samples": longest,
        "minimum_position_budget_with_original_speed_m": (
            float(np.min(minimum_position_frozen_speed))
            if len(minimum_position_frozen_speed) else None
        ),
        "minimum_speed_budget_with_original_position_rad_s": (
            float(np.min(minimum_speed_frozen_position))
            if len(minimum_speed_frozen_position) else None
        ),
        "orientation_pass_samples": int(np.count_nonzero(
            orientation <= contract["orientation_tracking_tolerance"])),
        "hand_gate_pass_samples": int(np.count_nonzero(hand_gate)),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-json", type=Path, nargs="+", required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error("Require a new output path")
    source = json.loads(args.input_json[0].read_text())
    source_hashes = source["source_sha256"]
    for path, expected in source_hashes.items():
        if sha256(Path(path)) != expected:
            raise ValueError(f"Recorded source or asset changed: {path}")
    source_contract = {key: value for key, value in source["arguments"].items()
                       if key not in ("seed", "output_json")}
    entries = []
    seen = set()
    for path in args.input_json:
        report = json.loads(path.read_text())
        seed = report["result"]["seed"]
        if (seed in seen or report["source_sha256"] != source_hashes
                or {key: value for key, value in report["arguments"].items()
                    if key not in ("seed", "output_json")} != source_contract):
            raise ValueError(f"Duplicate seed or changed source/contract: {path}")
        seen.add(seed)
        entry = summarize(path)
        entries.append(entry)
        print(json.dumps({key: entry[key] for key in (
            "seed", "original_reason", "best_single_sample_joint_ratio",
            "best_window_joint_ratio", "longest_joint_gate_run_samples")}), flush=True)
    output = {
        "schema_version": 1,
        "scope": "Retrospective sampled necessary hold gate; no controller, safety or acceptance change",
        "script_sha256": sha256(Path(__file__)),
        "source_sha256": source_hashes,
        "entries": sorted(entries, key=lambda entry: entry["seed"]),
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x") as destination:
        json.dump(output, destination, indent=2, allow_nan=False)


if __name__ == "__main__":
    main()
