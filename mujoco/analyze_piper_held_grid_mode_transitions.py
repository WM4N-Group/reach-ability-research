"""Audit post-step hold-mode transitions in frozen accepted/rejected pairs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from check_piper_startup import sha256


def _runs(history: list[dict], field: str) -> list[dict]:
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
        if a["control_step"] != b["control_step"] or a["time"] != b["time"]:
            raise ValueError("Control histories do not align")
        if a[field] != b[field]:
            return {
                "control_step": a["control_step"], "time": a["time"],
                "accepted": a[field], "rejected": b[field],
                "accepted_hand_error_m": a["hand_position_error"],
                "rejected_hand_error_m": b["hand_position_error"],
                "accepted_arm_speed_rad_s": a["arm_speed"],
                "rejected_arm_speed_rad_s": b["arm_speed"],
            }
    return None


def _row(suffix: dict, source_sha256: str, hold_seconds: float) -> dict:
    history = suffix["control_history"]
    settled_runs = _runs(history, "settled")
    held_runs = _runs(history, "command_was_held")
    step_time = suffix["target_step_event"]["time"]
    entries = [event for event in suffix["hold_events"] if event["time"] > step_time]
    required_steps = round(hold_seconds / (history[1]["time"] - history[0]["time"]))
    return {
        "source_sha256": source_sha256,
        "reason": suffix["reason"],
        "ten_second_acceptance": suffix["ten_second_acceptance"],
        "control_steps": len(history),
        "post_step_hold_entries": len(entries),
        "first_post_step_hold_entry_delay_s": entries[0]["time"] - step_time if entries else None,
        "settled_run_count": len(settled_runs),
        "first_settled_run_steps": settled_runs[0]["steps"] if settled_runs else 0,
        "longest_settled_run_steps": max((run["steps"] for run in settled_runs), default=0),
        "required_settled_run_steps": required_steps,
        "held_command_run_count": len(held_runs),
        "settled_runs": settled_runs,
        "held_command_runs": held_runs,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol-json", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error("Require a new output path")
    protocol = json.loads(args.protocol_json.read_text())
    if sha256(Path(__file__)) != protocol["analyzer_sha256"]:
        raise ValueError("Frozen analyzer changed")
    pairs = []
    for case in protocol["pairs"]:
        context_path = Path(case["context_path"])
        if sha256(context_path) != case["context_sha256"]:
            raise ValueError(f"Frozen context changed: {context_path}")
        context = json.loads(context_path.read_text())
        loaded = []
        for side in ("accepted", "rejected"):
            path = Path(case[side]["path"])
            if sha256(path) != case[side]["sha256"]:
                raise ValueError(f"Frozen suffix changed: {path}")
            loaded.append(json.loads(path.read_text()))
        accepted, rejected = loaded
        first = accepted["target_step_event"]
        second = rejected["target_step_event"]
        if (accepted["seed"] != rejected["seed"] or accepted["seed"] != case["seed"]
                or first["closed_loop_state_v2"] != second["closed_loop_state_v2"]
                or first["closed_loop_state_v2"] != context["closed_loop_state_v2"]
                or first["time"] != second["time"]
                or context["arguments"]["hand_tracking_tolerance"]
                != case["hand_tracking_tolerance_m"]
                or context["arguments"]["arm_velocity_tolerance"]
                != case["arm_velocity_tolerance_rad_s"]
                or context["arguments"]["hold_seconds"] != protocol["hold_seconds"]
                or accepted["reason"] != "completed"
                or not accepted["ten_second_acceptance"]
                or rejected["reason"] != "arm_tracking_timeout"
                or rejected["ten_second_acceptance"]):
            raise ValueError(f"Not an accepted/rejected exact-state pair: {case['seed']}")
        left = accepted["control_history"]
        right = rejected["control_history"]
        differences = {
            field: _first_difference(left, right, field)
            for field in ("settled", "command_was_held", "hold_entry_count", "hand_gate_passed")
        }
        pairs.append({
            "seed": case["seed"], "layout": case["layout"],
            "accepted_offset_local_m": first["offset_local_m"],
            "rejected_offset_local_m": second["offset_local_m"],
            "step_time": first["time"],
            "common_control_steps": min(len(left), len(right)),
            "hand_tracking_tolerance_m": case["hand_tracking_tolerance_m"],
            "arm_velocity_tolerance_rad_s": case["arm_velocity_tolerance_rad_s"],
            "first_difference": differences,
            "accepted": _row(accepted, case["accepted"]["sha256"], protocol["hold_seconds"]),
            "rejected": _row(rejected, case["rejected"]["sha256"], protocol["hold_seconds"]),
        })
    output = {
        "schema_version": 1,
        "scope": "Retrospective post-step mode audit, not a pre-step predictor",
        "protocol_sha256": sha256(args.protocol_json),
        "analyzer_sha256": sha256(Path(__file__)),
        "pairs": pairs,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x") as destination:
        json.dump(output, destination, indent=2, allow_nan=False)
        destination.write("\n")
    print(json.dumps({"output_sha256": sha256(args.output_json), "rows": [{
        "seed": pair["seed"], "first_difference": pair["first_difference"],
        "accepted_first_settled_run": pair["accepted"]["first_settled_run_steps"],
        "rejected_first_settled_run": pair["rejected"]["first_settled_run_steps"],
        "rejected_longest_settled_run": pair["rejected"]["longest_settled_run_steps"],
    } for pair in pairs]}))


if __name__ == "__main__":
    main()
