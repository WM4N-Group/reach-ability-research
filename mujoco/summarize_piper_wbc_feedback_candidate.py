"""Summarize all candidates in a preregistered WBC feedback contrast."""

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
    expected = {
        (entry["seed"], variant): entry["baseline_sha256"]
        for entry in protocol["inputs"] for variant in protocol["variants"]
    }
    entries = []
    seen = set()
    for path in args.candidate_json:
        report = json.loads(path.read_text())
        result = report["result"]
        key = (result["seed"], report["variant"])
        if key not in expected or key in seen:
            raise ValueError(f"Unexpected or duplicate candidate: {key}")
        seen.add(key)
        if sha256(Path(report["input"])) != expected[key] or report["input_sha256"] != expected[key]:
            raise ValueError(f"Frozen input hash mismatch: {key}")
        baseline = json.loads(Path(report["input"]).read_text())
        changed = protocol["variants"][report["variant"]]
        if (report["baseline_comparison"]["baseline_reason"] != baseline["result"]["reason"]
                or report["baseline_comparison"]["baseline_passed"] != baseline["result"]["passed"]
                or report["arguments"]["seed"] != result["seed"]
                or {name: value for name, value in report["arguments"].items()
                    if name not in (*changed, "output_json")}
                    != {name: value for name, value in baseline["arguments"].items()
                        if name not in (*changed, "output_json")}
                or any(report["arguments"][name] != value for name, value in changed.items())):
            raise ValueError(f"Candidate violates frozen protocol: {key}")
        motion = result["motion"]
        sweep = motion["swept_clearance"]
        entries.append({
            "seed": result["seed"],
            "variant": report["variant"],
            "report_sha256": sha256(path),
            "input_sha256": report["input_sha256"],
            "source_sha256": report["source_sha256"],
            "baseline_reason": baseline["result"]["reason"],
            "baseline_passed": baseline["result"]["passed"],
            "candidate_reason": result["reason"],
            "candidate_passed": result["passed"],
            "final_hand_position_error_m": motion["final_hand_position_error"],
            "final_end_effector_orientation_error_rad":
                motion["final_end_effector_orientation_error"],
            "stable_seconds": motion["stable_seconds"],
            "wbc_hold_entries": motion["wbc_hold_entries"],
            "maximum_arm_speed_rad_s": motion["maximum_arm_speed"],
            "minimum_self_clearance_m": motion["minimum_self_clearance"],
            "minimum_nonhand_environment_clearance_m":
                motion["minimum_nonhand_environment_clearance"],
            "minimum_swept_self_lower_bound_m": sweep["minimum_self_lower_bound"],
            "minimum_swept_nonhand_lower_bound_m":
                sweep["minimum_nonhand_environment_lower_bound"],
            "sweep_passed": sweep["passed"],
            "minimum_supporting_feet": motion["minimum_supporting_feet"],
            "minimum_support_margin_m": motion["minimum_support_margin"],
            "first_box_contact": result["safety"]["first_box_contact"],
            "contact_execution_enabled": result["safety"]["contact_execution_enabled"],
        })
    if seen != set(expected):
        raise ValueError(f"Missing preregistered candidates: {set(expected) - seen}")
    output = {
        "schema_version": 1,
        "scope": "Exploratory MuJoCo precontact feedback contrast; no acceptance claim",
        "protocol_sha256": sha256(args.protocol_json),
        "script_sha256": sha256(Path(__file__)),
        "entries": sorted(entries, key=lambda entry: (entry["seed"], entry["variant"])),
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x") as destination:
        json.dump(output, destination, indent=2, allow_nan=False)
    print(json.dumps({"entries": len(entries),
                      "candidate_completions": [
                          [entry["seed"], entry["variant"]] for entry in entries
                          if entry["candidate_passed"]]}))


if __name__ == "__main__":
    main()
