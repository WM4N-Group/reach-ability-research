"""Summarize preregistered paired five- and ten-second precontact holds."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from check_piper_startup import sha256


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol-json", type=Path, required=True)
    parser.add_argument("--candidate-json", type=Path, nargs="+", required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error("Require a new output path")
    protocol = json.loads(args.protocol_json.read_text())
    expected = {seed: batch for batch in protocol["batches"] for seed in batch["seeds"]}
    entries = []
    seen = set()
    for path in args.candidate_json:
        candidate = json.loads(path.read_text())
        result = candidate["result"]
        seed = result["seed"]
        if seed not in expected or seed in seen:
            raise ValueError(f"Unexpected or duplicate seed: {seed}")
        seen.add(seed)
        baseline_path = Path(candidate["input"])
        if sha256(baseline_path) != candidate["input_sha256"]:
            raise ValueError(f"Baseline hash mismatch: {seed}")
        baseline = json.loads(baseline_path.read_text())
        if (baseline["result"]["seed"] != seed
                or baseline["contract_source_sha256"] != expected[seed]["contract_sha256"]
                or baseline["arguments"]["hold_seconds"] != protocol["baseline_hold_seconds"]
                or candidate["arguments"]["hold_seconds"] != protocol["candidate_hold_seconds"]
                or {key: value for key, value in candidate["arguments"].items()
                    if key not in ("hold_seconds", "output_json")}
                    != {key: value for key, value in baseline["arguments"].items()
                        if key not in ("hold_seconds", "output_json")}):
            raise ValueError(f"Candidate contract mismatch: {seed}")
        original_trace = baseline["result"]["motion"]["trace"]
        trace = result["motion"]["trace"]
        prefix_matches = trace[:len(original_trace)] == original_trace
        if prefix_matches != candidate["baseline_comparison"]["baseline_control_trace_is_prefix"]:
            raise ValueError(f"Recorded prefix comparison mismatch: {seed}")
        extra = trace[len(original_trace):]
        if not extra:
            raise ValueError(f"No added observation window: {seed}")
        motion = result["motion"]
        entries.append({
            "seed": seed,
            "layout": expected[seed]["name"],
            "report_sha256": sha256(path),
            "baseline_sha256": candidate["input_sha256"],
            "source_sha256": candidate["source_sha256"],
            "baseline_reason": baseline["result"]["reason"],
            "candidate_reason": result["reason"],
            "baseline_control_trace_is_prefix": prefix_matches,
            "baseline_hold_entries": baseline["result"]["motion"]["wbc_hold_entries"],
            "candidate_hold_entries": motion["wbc_hold_entries"],
            "baseline_stable_seconds": baseline["result"]["motion"]["stable_seconds"],
            "candidate_stable_seconds": motion["stable_seconds"],
            "extra_control_samples": len(extra),
            "extra_all_command_held": all(item["wbc_command_held"] for item in extra),
            "extra_all_hand_gate_passed": all(item["hand_gate_passed"] for item in extra),
            "extra_minimum_hand_position_error_m": min(
                item["hand_position_error"] for item in extra),
            "extra_maximum_hand_position_error_m": max(
                item["hand_position_error"] for item in extra),
            "extra_maximum_arm_speed_rad_s": max(item["arm_speed"] for item in extra),
            "extra_maximum_orientation_error_rad": max(
                item["end_effector_orientation_error"] for item in extra),
            "extra_minimum_sampled_self_clearance_m": min(
                item["self_clearance"] for item in extra),
            "extra_minimum_sampled_nonhand_clearance_m": min(
                item["nonhand_environment_clearance"] for item in extra),
            "full_minimum_swept_self_lower_bound_m":
                motion["swept_clearance"]["minimum_self_lower_bound"],
            "full_minimum_swept_nonhand_lower_bound_m":
                motion["swept_clearance"]["minimum_nonhand_environment_lower_bound"],
            "full_sweep_passed": motion["swept_clearance"]["passed"],
            "full_minimum_supporting_feet": motion["minimum_supporting_feet"],
            "full_maximum_support_violation_seconds":
                motion["maximum_support_violation_seconds"],
            "first_box_contact": result["safety"]["first_box_contact"],
            "box_stop_event": result["box_runtime"]["stop_event"],
            "contact_execution_enabled": result["safety"]["contact_execution_enabled"],
        })
    if seen != set(expected):
        raise ValueError(f"Missing preregistered seeds: {set(expected) - seen}")
    output = {
        "schema_version": 1,
        "scope": "Matched MuJoCo extended precontact observation; no invariant-set or contact claim",
        "protocol_sha256": sha256(args.protocol_json),
        "script_sha256": sha256(Path(__file__)),
        "entries": sorted(entries, key=lambda item: item["seed"]),
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x") as destination:
        json.dump(output, destination, indent=2, allow_nan=False)
    print(json.dumps({"entries": len(entries),
                      "matched_prefixes": sum(item["baseline_control_trace_is_prefix"]
                                              for item in entries),
                      "ten_second_completions": sum(item["candidate_reason"] == "completed"
                                                    for item in entries)}))


if __name__ == "__main__":
    main()
