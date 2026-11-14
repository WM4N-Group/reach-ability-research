"""Locate hybrid WBC hold-mode divergence in a frozen adjacent-amplitude pair."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from check_piper_startup import sha256


def _runs(history: list[dict], field: str) -> list[dict[str, object]]:
    runs = []
    start = None
    for index, item in enumerate(history):
        if item[field] and start is None:
            start = index
        if start is not None and (not item[field] or index == len(history) - 1):
            end = index if item[field] and index == len(history) - 1 else index - 1
            runs.append({
                "start_control_step": history[start]["control_step"],
                "end_control_step": history[end]["control_step"],
                "steps": end - start + 1,
                "start_time": history[start]["time"],
                "end_time": history[end]["time"],
            })
            start = None
    return runs


def _first_difference(left: list[dict], right: list[dict], field: str) -> dict | None:
    for a, b in zip(left, right):
        if a["control_step"] != b["control_step"]:
            raise ValueError("Mismatched control step indices")
        if a[field] != b[field]:
            return {
                "control_step": a["control_step"],
                "time": a["time"],
                "smaller": a[field],
                "larger": b[field],
                "smaller_hand_error_m": a["hand_position_error"],
                "larger_hand_error_m": b["hand_position_error"],
                "smaller_arm_speed_rad_s": a["arm_speed"],
                "larger_arm_speed_rad_s": b["arm_speed"],
            }
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol-json", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error("Require a new output path")
    protocol = json.loads(args.protocol_json.read_text())
    if sha256(Path(__file__)) != protocol["analyzer_sha256"]:
        raise ValueError("Analyzer changed")
    paths = [Path(item["path"]) for item in protocol["ordered_pair"]]
    for path, item in zip(paths, protocol["ordered_pair"]):
        if sha256(path) != item["sha256"]:
            raise ValueError(f"Frozen suffix changed: {path}")
    smaller, larger = (json.loads(path.read_text()) for path in paths)
    if (smaller["seed"] != larger["seed"]
            or smaller["seed"] != protocol["seed"]
            or smaller["context_sha256"] != larger["context_sha256"]
            or smaller["suffix"]["target_step_event"]["closed_loop_state_v2"]
            != larger["suffix"]["target_step_event"]["closed_loop_state_v2"]):
        raise ValueError("Pair does not share an exact held-step state")
    left = smaller["suffix"]["control_history"]
    right = larger["suffix"]["control_history"]
    fields = ("settled", "command_was_held", "hold_entry_count", "hand_gate_passed")
    comparisons = {field: _first_difference(left, right, field) for field in fields}
    event_time = smaller["suffix"]["target_step_event"]["time"]
    output = {
        "schema_version": 1,
        "scope": "Post-step hybrid-mode attribution from two known trajectories; not a pre-step predictor",
        "protocol_sha256": sha256(args.protocol_json),
        "analyzer_sha256": sha256(Path(__file__)),
        "seed": protocol["seed"],
        "shared_context_sha256": smaller["context_sha256"],
        "step_time": event_time,
        "first_control_step": left[0]["control_step"],
        "common_recorded_steps": min(len(left), len(right)),
        "first_difference": comparisons,
        "rows": [],
    }
    for report, history in ((smaller, left), (larger, right)):
        suffix = report["suffix"]
        settled_runs = _runs(history, "settled")
        held_runs = _runs(history, "command_was_held")
        post_step_entries = [item for item in suffix["hold_events"]
                             if item["time"] > event_time]
        output["rows"].append({
            "phase": report["phase"],
            "reason": suffix["reason"],
            "ten_second_acceptance": suffix["ten_second_acceptance"],
            "control_steps": len(history),
            "settled_runs": settled_runs,
            "held_command_runs": held_runs,
            "settled_run_count": len(settled_runs),
            "longest_settled_run_steps": max((item["steps"] for item in settled_runs), default=0),
            "post_step_hold_entry_times": [item["time"] for item in post_step_entries],
            "final_hold_start_delay_s": (
                post_step_entries[-1]["time"] - event_time if post_step_entries else None
            ),
            "source_sha256": sha256(paths[len(output["rows"])]),
        })
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x") as destination:
        json.dump(output, destination, indent=2, allow_nan=False)
        destination.write("\n")
    print(json.dumps({
        "first_difference": comparisons,
        "summary": [{key: row[key] for key in (
            "phase", "reason", "settled_run_count", "longest_settled_run_steps",
            "final_hold_start_delay_s",
        )} for row in output["rows"]],
    }))


if __name__ == "__main__":
    main()
