"""Summarize matched target steps, retaining baselines that never entered hold."""

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
    if (sha256(Path(__file__)) != protocol["summary_script_sha256"]
            or sha256(Path(protocol["runner"])) != protocol["runner_sha256"]
            or sha256(Path(protocol["motion_source"])) != protocol["motion_sha256"]):
        raise ValueError("Preregistered source changed")
    baselines = []
    entries = []
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
                    or (baseline_event is not None and baseline_event["applied"])
                    or (baseline_result["passed"] and baseline_event is None)):
                raise ValueError(f"Invalid baseline: {seed}")
            baseline_hash = sha256(baseline_path)
            baselines.append({
                "seed": seed,
                "layout": batch["name"],
                "reason": baseline_result["reason"],
                "passed": baseline_result["passed"],
                "probe_time": baseline_event["time"] if baseline_event is not None else None,
                "report_sha256": baseline_hash,
            })
            phase = protocol["phase"]
            path = args.report_dir / f"seed{seed}-{phase}-v1.json"
            report = json.loads(path.read_text())
            result = report["result"]
            event = result["motion"]["target_step_event"]
            comparison = report["baseline_comparison"]
            if (report["seed"] != seed or report["phase"] != phase
                    or report["offset_local_m"] != protocol["offsets_m"][phase]
                    or report["protocol_sha256"] != sha256(args.protocol_json)
                    or report["contract_source_sha256"] != batch["contract_sha256"]
                    or comparison["baseline_sha256"] != baseline_hash):
                raise ValueError(f"Candidate contract changed: {seed}")
            if source_hashes is None:
                source_hashes = report["source_sha256"]
            elif report["source_sha256"] != source_hashes:
                raise ValueError(f"Source set changed: {seed}")
            matched = bool(
                event is not None and event["applied"]
                and all(comparison[key] for key in (
                    "same_nav_trace", "same_precontact_state", "same_pre_step_trace",
                    "same_pre_step_state",
                ))
            )
            motion = result["motion"]
            sweep = motion["swept_clearance"]
            safety = result["safety"]
            box = result["box_runtime"]
            post_step_holds = (
                [item for item in motion["wbc_hold_events"]
                 if item["time"] > event["time"]]
                if event is not None else []
            )
            final_hold_start = (
                post_step_holds[-1]["time"]
                if result["reason"] == "completed" and post_step_holds else None
            )
            accepted = bool(
                baseline_result["passed"] and matched
                and result["passed"] and result["reason"] == "completed"
                and motion["stable_seconds"] >= protocol["hold_seconds"]
                and motion["wbc_hold_entries"] > event["hold_entries_before_step"]
                and final_hold_start is not None
                and sweep["passed"] and safety["first_box_contact"] is None
                and box["stop_event"] is None
                and not safety["contact_execution_enabled"]
            )
            entries.append({
                "seed": seed,
                "layout": batch["name"],
                "phase": phase,
                "baseline_reason": baseline_result["reason"],
                "reason": result["reason"],
                "matched_pre_step_state": matched,
                "accepted": accepted,
                "step_time": event["time"] if event is not None else None,
                "initial_step_hand_error_m": (
                    event["instantaneous_hand_error_m"] if event is not None else None
                ),
                "final_hold_start_time": final_hold_start,
                "stable_seconds_at_stop": motion["stable_seconds"],
                "post_step_hold_entries": len(post_step_holds),
                "minimum_swept_self_lower_bound_m": sweep["minimum_self_lower_bound"],
                "minimum_swept_nonhand_lower_bound_m":
                    sweep["minimum_nonhand_environment_lower_bound"],
                "sweep_passed": sweep["passed"],
                "minimum_supporting_feet": motion["minimum_supporting_feet"],
                "maximum_support_violation_seconds":
                    motion["maximum_support_violation_seconds"],
                "first_box_contact": safety["first_box_contact"],
                "box_stop_event": box["stop_event"],
                "contact_execution_enabled": safety["contact_execution_enabled"],
                "baseline_sha256": baseline_hash,
                "report_sha256": sha256(path),
            })
    output = {
        "schema_version": 1,
        "scope": "Independent held-step batch including ineligible baseline failures",
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
    print(json.dumps({"baselines": len(baselines),
                      "baseline_completed": sum(item["passed"] for item in baselines),
                      "candidates": len(entries),
                      "matched": sum(item["matched_pre_step_state"] for item in entries),
                      "completed": sum(item["accepted"] for item in entries)}))


if __name__ == "__main__":
    main()
