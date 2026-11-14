"""Apply preregistered recovery deadlines to matched hold-step reports."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from check_piper_startup import sha256


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol-json", type=Path, required=True)
    parser.add_argument("--summary-json", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error("Require a new output path")
    protocol = json.loads(args.protocol_json.read_text())
    summary = json.loads(args.summary_json.read_text())
    if (sha256(Path(__file__)) != protocol["deadline_analysis_sha256"]
            or sha256(Path(protocol["summary_script"]))
            != protocol["summary_script_sha256"]
            or summary["protocol_sha256"] != sha256(args.protocol_json)
            or summary["summary_script_sha256"] != protocol["summary_script_sha256"]):
        raise ValueError("Protocol or source hash mismatch")
    expected = {
        (seed, phase): batch["name"]
        for batch in protocol["batches"]
        for seed in batch["seeds"]
        for phase in protocol["offsets_m"]
    }
    if len(summary["entries"]) != len(expected) or len(summary["baselines"]) != 4:
        raise ValueError("Incomplete fixed batch")
    seen = set()
    rows = []
    for item in summary["entries"]:
        key = item["seed"], item["phase"]
        if key not in expected or key in seen or item["layout"] != expected[key]:
            raise ValueError(f"Unexpected or duplicate pair: {key}")
        seen.add(key)
        if item["offset_local_m"] != protocol["offsets_m"][item["phase"]]:
            raise ValueError(f"Offset changed: {key}")
        matched = bool(item["matched_pre_step_state"])
        complete = bool(item["accepted"] and matched)
        hold_start = item["final_hold_start_time"]
        delay = hold_start - item["step_time"] if complete and hold_start is not None else None
        if complete and (delay is None or delay < 0.0):
            raise ValueError(f"Completed report lacks final hold start: {key}")
        outside = item["initial_step_hand_error_m"] > protocol["hand_tolerance_m"]
        main_deadline = bool(complete and delay <= protocol["primary_deadline_seconds"])
        secondary_deadline = bool(
            complete and delay <= protocol["secondary_deadline_seconds"]
        )
        rows.append({
            "seed": item["seed"],
            "layout": item["layout"],
            "phase": item["phase"],
            "amplitude_m": abs(item["offset_local_m"][0]),
            "reason": item["reason"],
            "matched_pre_step_state": matched,
            "initial_step_hand_error_m": item["initial_step_hand_error_m"],
            "initially_outside_hand_tolerance": outside,
            "completed_original_contract": complete,
            "final_hold_start_delay_seconds": delay,
            "within_primary_deadline": main_deadline,
            "outside_then_recovered_by_primary_deadline": bool(outside and main_deadline),
            "within_secondary_deadline": secondary_deadline,
            "final_hold_max_sampled_hand_error_m":
                item["final_hold_max_sampled_hand_error_m"],
            "final_hold_max_sampled_arm_speed_rad_s":
                item["final_hold_max_sampled_arm_speed_rad_s"],
            "hold_entries_after_step": item["hold_entries_after_step"],
            "minimum_swept_self_lower_bound_m":
                item["minimum_swept_self_lower_bound_m"],
            "minimum_swept_nonhand_lower_bound_m":
                item["minimum_swept_nonhand_lower_bound_m"],
            "minimum_supporting_feet": item["minimum_supporting_feet"],
            "maximum_support_violation_seconds":
                item["maximum_support_violation_seconds"],
            "report_sha256": item["report_sha256"],
            "baseline_sha256": item["baseline_sha256"],
        })
    if seen != set(expected):
        raise ValueError(f"Missing pairs: {set(expected) - seen}")
    by_phase = []
    for phase in protocol["offsets_m"]:
        group = [item for item in rows if item["phase"] == phase]
        by_phase.append({
            "phase": phase,
            "tested": len(group),
            "original_completions": sum(item["completed_original_contract"] for item in group),
            "primary_deadline_completions": sum(
                item["within_primary_deadline"] for item in group
            ),
            "outside_then_primary_recoveries": sum(
                item["outside_then_recovered_by_primary_deadline"] for item in group
            ),
            "secondary_deadline_completions": sum(
                item["within_secondary_deadline"] for item in group
            ),
        })
    output = {
        "schema_version": 1,
        "scope": "Discrete x-negative held target steps; finite MuJoCo deadline evidence",
        "protocol_sha256": sha256(args.protocol_json),
        "full_summary_sha256": sha256(args.summary_json),
        "analysis_script_sha256": sha256(Path(__file__)),
        "baseline_count": len(summary["baselines"]),
        "baseline_completed": sum(item["passed"] for item in summary["baselines"]),
        "by_phase": by_phase,
        "entries": rows,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x") as destination:
        json.dump(output, destination, indent=2, allow_nan=False)
        destination.write("\n")
    print(json.dumps({"baselines": output["baseline_completed"],
                      "pairs": len(rows),
                      "completions": sum(item["completed_original_contract"] for item in rows),
                      "primary_deadline": sum(item["within_primary_deadline"] for item in rows),
                      "outside_then_primary": sum(
                          item["outside_then_recovered_by_primary_deadline"] for item in rows)}))


if __name__ == "__main__":
    main()
