"""Score preregistered held-step amplitude pairs with baseline abstentions."""

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
    protocol_hash = sha256(args.protocol_json)
    if (sha256(Path(__file__)) != protocol["summary_script_sha256"]
            or sha256(Path(protocol["runner"])) != protocol["runner_sha256"]
            or sha256(Path(protocol["motion_source"])) != protocol["motion_sha256"]):
        raise ValueError("Preregistered analysis or runner changed")
    baselines = []
    entries = []
    source_hashes = None
    for batch in protocol["batches"]:
        if sha256(Path(batch["contract_json"])) != batch["contract_sha256"]:
            raise ValueError(f"Contract changed: {batch['name']}")
        for seed in batch["seeds"]:
            baseline_path = args.report_dir / f"seed{seed}-baseline-v1.json"
            baseline = json.loads(baseline_path.read_text())
            baseline_result = baseline["result"]
            baseline_event = baseline_result["motion"]["target_step_event"]
            if (baseline["seed"] != seed or baseline["phase"] != "baseline"
                    or baseline["protocol_sha256"] != protocol_hash
                    or baseline["contract_source_sha256"] != batch["contract_sha256"]
                    or (baseline_event is not None and baseline_event["applied"])
                    or (baseline_result["passed"] and baseline_event is None)):
                raise ValueError(f"Invalid baseline: {seed}")
            baseline_hash = sha256(baseline_path)
            eligible = bool(baseline_result["passed"] and baseline_event is not None)
            baselines.append({
                "seed": seed,
                "layout": batch["name"],
                "reason": baseline_result["reason"],
                "eligible": eligible,
                "probe_time": baseline_event["time"] if baseline_event else None,
                "report_sha256": baseline_hash,
            })
            for phase, delta in protocol["offsets_m"].items():
                path = args.report_dir / f"seed{seed}-{phase}-v1.json"
                report = json.loads(path.read_text())
                result = report["result"]
                motion = result["motion"]
                event = motion["target_step_event"]
                comparison = report["baseline_comparison"]
                if (report["seed"] != seed or report["phase"] != phase
                        or report["offset_local_m"] != delta
                        or report["protocol_sha256"] != protocol_hash
                        or report["contract_source_sha256"] != batch["contract_sha256"]
                        or comparison["baseline_sha256"] != baseline_hash
                        or report["source_sha256"] != baseline["source_sha256"]
                        or (event is not None and (not event["applied"]
                            or event["offset_local_m"] != delta))):
                    raise ValueError(f"Invalid candidate: {seed} {phase}")
                if source_hashes is None:
                    source_hashes = report["source_sha256"]
                    for source_path, expected in source_hashes.items():
                        if sha256(Path(source_path)) != expected:
                            raise ValueError(f"Recorded source changed: {source_path}")
                elif report["source_sha256"] != source_hashes:
                    raise ValueError(f"Source set changed: {seed} {phase}")
                matched = bool(event is not None and eligible and all(comparison[key]
                    for key in ("same_nav_trace", "same_precontact_state",
                                "same_pre_step_trace", "same_pre_step_state")))
                post_step_holds = ([item for item in motion["wbc_hold_events"]
                                    if item["time"] > event["time"]]
                                   if event else [])
                final_hold_start = (post_step_holds[-1]["time"]
                                    if result["reason"] == "completed" and post_step_holds
                                    else None)
                delay = (final_hold_start - event["time"]
                         if final_hold_start is not None and event else None)
                sweep = motion["swept_clearance"]
                safety = result["safety"]
                box = result["box_runtime"]
                full_completed = bool(matched and result["passed"]
                    and result["reason"] == "completed"
                    and motion["stable_seconds"] >= protocol["hold_seconds"]
                    and motion["wbc_hold_entries"] > event["hold_entries_before_step"]
                    and delay is not None and sweep["passed"]
                    and safety["first_box_contact"] is None
                    and box["stop_event"] is None
                    and not safety["contact_execution_enabled"])
                entries.append({
                    "seed": seed,
                    "layout": batch["name"],
                    "phase": phase,
                    "offset_local_m": delta,
                    "baseline_eligible": eligible,
                    "matched_pre_step_state": matched,
                    "reason": result["reason"],
                    "step_time": event["time"] if event else None,
                    "initial_step_hand_error_m": (
                        event["instantaneous_hand_error_m"] if event else None),
                    "final_hold_start_delay_seconds": delay,
                    "completed_original_contract": full_completed,
                    "recovered_by_deadline": bool(
                        full_completed and delay <= protocol["primary_deadline_seconds"]),
                    "post_step_hold_entries": len(post_step_holds),
                    "stable_seconds_at_stop": motion["stable_seconds"],
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
    indexed = {(item["seed"], item["phase"]): item for item in entries}
    if len(indexed) != len(entries):
        raise ValueError("Duplicate candidate")
    pair_checks = []
    for baseline in baselines:
        for smaller_phase, larger_phase in protocol["ordered_amplitude_pairs"]:
            smaller = indexed[baseline["seed"], smaller_phase]
            larger = indexed[baseline["seed"], larger_phase]
            eligible = bool(baseline["eligible"]
                and smaller["matched_pre_step_state"] and larger["matched_pre_step_state"]
                and smaller["initial_step_hand_error_m"] > protocol["hand_tolerance_m"]
                and larger["initial_step_hand_error_m"] > protocol["hand_tolerance_m"])
            pair_checks.append({
                "seed": baseline["seed"],
                "smaller_phase": smaller_phase,
                "larger_phase": larger_phase,
                "eligible": eligible,
                "smaller_recovered_by_deadline": (
                    smaller["recovered_by_deadline"] if eligible else None),
                "larger_recovered_by_deadline": (
                    larger["recovered_by_deadline"] if eligible else None),
                "nonmonotone_witness": (bool(not smaller["recovered_by_deadline"]
                    and larger["recovered_by_deadline"]) if eligible else None),
            })
    output = {
        "schema_version": 1,
        "scope": "Independent fixed-amplitude paired MuJoCo check; finite no-contact outcomes",
        "protocol_sha256": protocol_hash,
        "summary_script_sha256": sha256(Path(__file__)),
        "source_sha256": source_hashes,
        "baselines": baselines,
        "entries": entries,
        "pair_checks": pair_checks,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x") as destination:
        json.dump(output, destination, indent=2, allow_nan=False)
        destination.write("\n")
    print(json.dumps({"baselines": len(baselines),
                      "eligible_baselines": sum(item["eligible"] for item in baselines),
                      "candidates": len(entries),
                      "completed": sum(item["recovered_by_deadline"] for item in entries),
                      "eligible_pairs": sum(item["eligible"] for item in pair_checks),
                      "nonmonotone_witnesses": sum(
                          item["nonmonotone_witness"] is True for item in pair_checks)}))


if __name__ == "__main__":
    main()
