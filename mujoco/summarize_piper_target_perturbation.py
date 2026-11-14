"""Validate and summarize every preregistered WBC target perturbation pair."""

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
    if (sha256(Path(protocol["baseline_entrypoint"]))
            != protocol["baseline_entrypoint_sha256"]
            or sha256(Path(protocol["candidate_entrypoint"]))
            != protocol["candidate_entrypoint_sha256"]
            or sha256(Path("mujoco/check_piper_arm_precontact_motion.py"))
            != protocol["motion_entrypoint_sha256"]):
        raise ValueError("Preregistered entrypoint changed")
    entries = []
    source_hashes = None
    for batch in protocol["batches"]:
        for seed in batch["seeds"]:
            baseline_path = args.report_dir / f"seed{seed}-baseline-v1.json"
            baseline = json.loads(baseline_path.read_text())
            if (sha256(Path(batch["contract_json"])) != batch["contract_sha256"]
                    or baseline["contract_source_sha256"] != batch["contract_sha256"]
                    or baseline["result"]["seed"] != seed):
                raise ValueError(f"Baseline contract mismatch: {seed}")
            original = baseline["arguments"]
            for name, delta in protocol["offsets_m"].items():
                path = args.report_dir / f"seed{seed}-{name}-v1.json"
                candidate = json.loads(path.read_text())
                if (candidate["source_sha256"][str(
                        Path(protocol["candidate_entrypoint"]).resolve())]
                        != protocol["candidate_entrypoint_sha256"]):
                    raise ValueError(f"Candidate source hash mismatch: {seed} {name}")
                if source_hashes is None:
                    source_hashes = candidate["source_sha256"]
                elif source_hashes != candidate["source_sha256"]:
                    raise ValueError(f"Source set changed within batch: {seed} {name}")
                result = candidate["result"]
                modified = candidate["arguments"]
                expected_target = [
                    value + shift for value, shift in zip(original["hand_target_local"], delta)
                ]
                if (candidate["protocol_sha256"] != sha256(args.protocol_json)
                        or candidate["baseline_sha256"] != sha256(baseline_path)
                        or candidate["offset"] != name
                        or candidate["offset_local_m"] != delta
                        or result["seed"] != seed
                        or modified["hand_target_local"] != expected_target
                        or {key: value for key, value in modified.items()
                            if key not in ("hand_target_local", "output_json")}
                        != {key: value for key, value in original.items()
                            if key not in ("hand_target_local", "output_json")}):
                    raise ValueError(f"Perturbation contract mismatch: {seed} {name}")
                matched = (
                    result["nav"]["trace"] == baseline["result"]["nav"]["trace"]
                    and result["candidate"]["precontact_state"]
                    == baseline["result"]["candidate"]["precontact_state"]
                )
                if (candidate["baseline_comparison"]["navigation_trace_matches"]
                        != (result["nav"]["trace"]
                            == baseline["result"]["nav"]["trace"])
                        or candidate["baseline_comparison"]["precontact_state_matches"]
                        != (result["candidate"]["precontact_state"]
                            == baseline["result"]["candidate"]["precontact_state"])):
                    raise ValueError(f"Pair record mismatch: {seed} {name}")
                motion = result["motion"]
                sweep = motion["swept_clearance"]
                safety = result["safety"]
                box = result["box_runtime"]
                held = [item for item in motion["trace"] if item["wbc_command_held"]]
                accepted = bool(
                    matched and result["reason"] == "completed" and result["passed"]
                    and sweep["passed"] and safety["first_box_contact"] is None
                    and box["stop_event"] is None
                    and not safety["contact_execution_enabled"]
                )
                entries.append({
                    "seed": seed,
                    "layout": batch["name"],
                    "offset": name,
                    "offset_local_m": delta,
                    "baseline_reason": baseline["result"]["reason"],
                    "reason": result["reason"],
                    "accepted": accepted,
                    "matched_post_nav_start": matched,
                    "baseline_sha256": sha256(baseline_path),
                    "report_sha256": sha256(path),
                    "sampled_held_points": len(held),
                    "sampled_held_max_position_error_m": max(
                        (item["hand_position_error"] for item in held), default=None
                    ),
                    "sampled_held_max_arm_speed_rad_s": max(
                        (item["arm_speed"] for item in held), default=None
                    ),
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
                })
    output = {
        "schema_version": 1,
        "scope": "Fixed whole-run 3 mm target perturbation, finite MuJoCo evidence only",
        "protocol_sha256": sha256(args.protocol_json),
        "summary_script_sha256": sha256(Path(__file__)),
        "source_sha256": source_hashes,
        "entries": entries,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x") as destination:
        json.dump(output, destination, indent=2, allow_nan=False)
        destination.write("\n")
    print(json.dumps({"pairs": len(entries),
                      "matched": sum(item["matched_post_nav_start"] for item in entries),
                      "accepted": sum(item["accepted"] for item in entries)}))


if __name__ == "__main__":
    main()
