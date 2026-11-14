"""Validate preregistered held-state target steps and their matched probes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from check_piper_startup import sha256


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol-json", type=Path, required=True)
    parser.add_argument("--report-dir", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error("Require a new output path")
    protocol = json.loads(args.protocol_json.read_text())
    if (sha256(Path(protocol["runner"])) != protocol["runner_sha256"]
            or sha256(Path(protocol["motion_source"])) != protocol["motion_sha256"]):
        raise ValueError("Preregistered source changed")
    entries = []
    baselines = []
    source_hashes = None
    for batch in protocol["batches"]:
        if sha256(Path(batch["contract_json"])) != batch["contract_sha256"]:
            raise ValueError(f"Source contract changed: {batch['name']}")
        for seed in batch["seeds"]:
            baseline_path = args.report_dir / f"seed{seed}-baseline-v1.json"
            baseline = json.loads(baseline_path.read_text())
            baseline_result = baseline["result"]
            baseline_event = baseline_result["motion"]["target_step_event"]
            if (baseline["seed"] != seed or baseline["phase"] != "baseline"
                    or baseline["protocol_sha256"] != sha256(args.protocol_json)
                    or baseline["contract_source_sha256"] != batch["contract_sha256"]
                    or baseline_event is None or baseline_event["applied"]):
                raise ValueError(f"Invalid baseline probe: {seed}")
            baselines.append({
                "seed": seed,
                "layout": batch["name"],
                "reason": baseline_result["reason"],
                "passed": baseline_result["passed"],
                "report_sha256": sha256(baseline_path),
                "probe_time": baseline_event["time"],
            })
            for phase, delta in protocol["offsets_m"].items():
                path = args.report_dir / f"seed{seed}-{phase}-v1.json"
                report = json.loads(path.read_text())
                result = report["result"]
                event = result["motion"]["target_step_event"]
                comparison = report["baseline_comparison"]
                if (report["seed"] != seed or report["phase"] != phase
                        or report["offset_local_m"] != delta
                        or report["protocol_sha256"] != sha256(args.protocol_json)
                        or report["contract_source_sha256"] != batch["contract_sha256"]
                        or comparison["baseline_sha256"] != sha256(baseline_path)
                        or event is None or not event["applied"]
                        or event["offset_local_m"] != delta):
                    raise ValueError(f"Invalid candidate report: {seed} {phase}")
                if source_hashes is None:
                    source_hashes = report["source_sha256"]
                elif source_hashes != report["source_sha256"]:
                    raise ValueError(f"Source set changed: {seed} {phase}")
                matched = all(comparison[key] for key in (
                    "same_nav_trace", "same_precontact_state", "same_pre_step_trace",
                    "same_pre_step_state",
                ))
                sweep = result["motion"]["swept_clearance"]
                safety = result["safety"]
                box = result["box_runtime"]
                first_settled = result["motion"]["target_step_first_settled_time"]
                post_step = [item for item in result["motion"]["trace"]
                             if item["time"] > event["time"]]
                post_step_hold_entries = [
                    item for item in result["motion"]["wbc_hold_events"]
                    if item["time"] > event["time"]
                ]
                final_hold_start = (
                    post_step_hold_entries[-1]["time"]
                    if result["reason"] == "completed" and post_step_hold_entries
                    else None
                )
                final_window = (
                    [item for item in result["motion"]["trace"]
                     if item["time"] > final_hold_start]
                    if final_hold_start is not None else []
                )
                accepted = bool(
                    baseline_result["passed"] and matched
                    and result["passed"] and result["reason"] == "completed"
                    and first_settled is not None
                    and result["motion"]["stable_seconds"] >= protocol["hold_seconds"]
                    and result["motion"]["wbc_hold_entries"]
                    > event["hold_entries_before_step"]
                    and sweep["passed"] and safety["first_box_contact"] is None
                    and box["stop_event"] is None
                    and not safety["contact_execution_enabled"]
                )
                entries.append({
                    "seed": seed,
                    "layout": batch["name"],
                    "phase": phase,
                    "offset_local_m": delta,
                    "baseline_reason": baseline_result["reason"],
                    "reason": result["reason"],
                    "accepted": accepted,
                    "matched_pre_step_state": matched,
                    "report_sha256": sha256(path),
                    "baseline_sha256": sha256(baseline_path),
                    "step_time": event["time"],
                    "initial_step_hand_error_m": event["instantaneous_hand_error_m"],
                    "first_settled_delay_seconds": (
                        first_settled - event["time"] if first_settled is not None else None
                    ),
                    "stable_seconds_at_stop": result["motion"]["stable_seconds"],
                    "hold_entries_after_step": (
                        result["motion"]["wbc_hold_entries"]
                        - event["hold_entries_before_step"]
                    ),
                    "first_hold_reentry_delay_seconds": (
                        post_step_hold_entries[0]["time"] - event["time"]
                        if post_step_hold_entries else None
                    ),
                    "final_hold_start_time": final_hold_start,
                    "post_step_sampled_points": len(post_step),
                    "post_step_max_sampled_hand_error_m": max(
                        (item["hand_position_error"] for item in post_step), default=None
                    ),
                    "post_step_max_sampled_arm_speed_rad_s": max(
                        (item["arm_speed"] for item in post_step), default=None
                    ),
                    "final_hold_sampled_points": len(final_window),
                    "final_hold_all_sampled_command_held": all(
                        item["wbc_command_held"] for item in final_window
                    ) if final_window else None,
                    "final_hold_max_sampled_hand_error_m": max(
                        (item["hand_position_error"] for item in final_window), default=None
                    ),
                    "final_hold_max_sampled_arm_speed_rad_s": max(
                        (item["arm_speed"] for item in final_window), default=None
                    ),
                    "minimum_swept_self_lower_bound_m": sweep["minimum_self_lower_bound"],
                    "minimum_swept_nonhand_lower_bound_m":
                        sweep["minimum_nonhand_environment_lower_bound"],
                    "sweep_passed": sweep["passed"],
                    "minimum_supporting_feet": result["motion"]["minimum_supporting_feet"],
                    "maximum_support_violation_seconds":
                        result["motion"]["maximum_support_violation_seconds"],
                    "first_box_contact": safety["first_box_contact"],
                    "box_stop_event": box["stop_event"],
                    "contact_execution_enabled": safety["contact_execution_enabled"],
                })
    output = {
        "schema_version": 1,
        "scope": "Matched one-shot held-state target steps; finite MuJoCo recovery only",
        "protocol_sha256": sha256(args.protocol_json),
        "summary_script_sha256": sha256(Path(__file__)),
        "source_sha256": source_hashes,
        "baselines": baselines,
        "entries": entries,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x") as destination:
        json.dump(output, destination, indent=2, allow_nan=False)
        destination.write("\n")
    print(json.dumps({"baselines_completed": sum(item["passed"] for item in baselines),
                      "pairs": len(entries),
                      "matched": sum(item["matched_pre_step_state"] for item in entries),
                      "accepted": sum(item["accepted"] for item in entries)}))


if __name__ == "__main__":
    main()
