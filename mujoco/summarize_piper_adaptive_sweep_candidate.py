"""Summarize frozen-baseline and adaptive-sweep candidate rollouts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from check_piper_startup import sha256


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-json", type=Path, nargs="+", required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error("Require a new output path")
    entries = []
    seen = set()
    for path in args.candidate_json:
        report = json.loads(path.read_text())
        seed = report["result"]["seed"]
        depth = report["adaptive_sweep"]["max_depth"]
        if (seed, depth) in seen:
            raise ValueError(f"Duplicate seed and depth: {seed}, {depth}")
        seen.add((seed, depth))
        result = report["result"]
        motion = result["motion"]
        events = report["adaptive_sweep"]["events"]
        entries.append({
            "seed": seed,
            "max_depth": depth,
            "report_sha256": sha256(path),
            "input_sha256": report["input_sha256"],
            "source_sha256": report["source_sha256"],
            "baseline_reason": report["baseline_comparison"]["baseline_reason"],
            "same_result_as_baseline": report["baseline_comparison"]["same_result"],
            "candidate_reason": result["reason"],
            "candidate_passed": result["passed"],
            "elapsed_sim_time_s": result["elapsed_sim_time"],
            "checked_sweep_intervals": motion["swept_clearance"]["checked_intervals"],
            "effective_sweep_passed": motion["swept_clearance"]["passed"],
            "extra_geometry_evaluations": report["adaptive_sweep"]["extra_geometry_evaluations"],
            "refinement_events": len(events),
            "failed_refinement_events": sum(not event["passed"] for event in events),
            "minimum_sampled_self_clearance_m": motion["minimum_self_clearance"],
            "minimum_sampled_nonhand_clearance_m": motion["minimum_nonhand_environment_clearance"],
            "minimum_effective_self_sweep_bound_m": motion["swept_clearance"]["minimum_self_lower_bound"],
            "minimum_effective_nonhand_sweep_bound_m": motion["swept_clearance"]["minimum_nonhand_environment_lower_bound"],
            "final_hand_position_error_m": motion["final_hand_position_error"],
            "stable_seconds": motion["stable_seconds"],
        })
    if any(item["max_depth"] == 0 and not item["same_result_as_baseline"]
           for item in entries):
        raise ValueError("A depth-zero replay did not reproduce the frozen result")
    output = {
        "schema_version": 1,
        "scope": "Candidate MuJoCo precontact replay only; no PUSH, contact or deployment approval",
        "script_sha256": sha256(Path(__file__)),
        "entries": sorted(entries, key=lambda item: (item["seed"], item["max_depth"])),
    }
    with args.output_json.open("x") as destination:
        json.dump(output, destination, indent=2, allow_nan=False)
    print(json.dumps({"entries": len(entries),
                      "baseline_replays": sum(item["max_depth"] == 0 for item in entries),
                      "candidate_completions": [item["seed"] for item in entries
                          if item["max_depth"] > 0 and item["candidate_passed"]]}))


if __name__ == "__main__":
    main()
