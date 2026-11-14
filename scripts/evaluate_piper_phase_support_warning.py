"""Evaluate a frozen pre-ready phase condition on an existing read-only warning."""

import argparse
import json
from collections import Counter
from pathlib import Path

from analyze_piper_isaac_support_dynamics import sha256


DT_S = 0.02


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature-json", type=Path, required=True)
    parser.add_argument("--base-warning-json", type=Path, required=True)
    parser.add_argument("--protocol-json", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error("Require a new output path")
    with args.feature_json.open(encoding="utf-8") as source:
        features = json.load(source)
    with args.base_warning_json.open(encoding="utf-8") as source:
        warnings = json.load(source)
    with args.protocol_json.open(encoding="utf-8") as source:
        protocol = json.load(source)
    protocol_hash = sha256(args.protocol_json)
    if (sha256(Path(__file__)) != protocol["phase_evaluator_sha256"]
            or features["protocol_sha256"] != protocol_hash
            or features["analysis_sha256"] != protocol["feature_extractor_sha256"]
            or warnings["protocol_sha256"] != protocol_hash
            or warnings["analysis_sha256"] != protocol["warning_evaluator_sha256"]
            or warnings["feature_json_sha256"] != sha256(args.feature_json)
            or protocol["phase_condition"] != "motion_ready_false"):
        raise ValueError("Analysis source or protocol mismatch")
    by_seed = {case["seed"]: case for case in warnings["cases"]}
    results = features["results"]
    if (sorted(result["seed"] for result in results) != sorted(protocol["seeds"])
            or set(by_seed) != set(protocol["seeds"])):
        raise ValueError("Incomplete or duplicate holdout seeds")
    cases = []
    for result in results:
        baseline = by_seed[result["seed"]]
        if (baseline["raw_report_sha256"] != result["input_sha256"]
                or baseline["outcome"] != result["outcome"]):
            raise ValueError(f"Warning/report mismatch for seed {result['seed']}")
        ready_seen = False
        for sample in result["features"]:
            if ready_seen and not sample["motion_ready"]:
                raise ValueError(f"Nonmonotone motion_ready for seed {result['seed']}")
            ready_seen = ready_seen or sample["motion_ready"]
        first_base_s = baseline["first_warning_s"]
        if first_base_s is None:
            ready_at_warning = None
        else:
            index = round(first_base_s / DT_S) - 1
            sample = result["features"][index]
            if abs(sample["push_elapsed_s"] - first_base_s) > 1e-8:
                raise ValueError(f"Warning time mismatch for seed {result['seed']}")
            ready_at_warning = sample["motion_ready"]
        phase_warning_s = first_base_s if ready_at_warning is False else None
        cases.append({
            "seed": result["seed"],
            "raw_report_sha256": result["input_sha256"],
            "outcome": result["outcome"],
            "terminal_reasons": result["terminal_reasons"],
            "push_elapsed_s": result["push_elapsed_s"],
            "base_warning_s": first_base_s,
            "motion_ready_at_base_warning": ready_at_warning,
            "pre_ready_warning_s": phase_warning_s,
            "pre_ready_warning_to_terminal_s": (
                round(result["push_elapsed_s"] - phase_warning_s, 2)
                if phase_warning_s is not None else None
            ),
        })
    output = {
        "schema_version": 1,
        "analysis_sha256": sha256(Path(__file__)),
        "feature_json_sha256": sha256(args.feature_json),
        "base_warning_json_sha256": sha256(args.base_warning_json),
        "protocol_sha256": protocol_hash,
        "scope": "Read-only causal replay of a phase-conditioned warning; rule selected after inspecting earlier cohorts",
        "outcome_counts": dict(Counter(case["outcome"] for case in cases)),
        "base_warning_counts_by_outcome": warnings["warning_counts_by_outcome"],
        "pre_ready_warning_counts_by_outcome": {
            outcome: sum(case["pre_ready_warning_s"] is not None
                         for case in cases if case["outcome"] == outcome)
            for outcome in sorted({case["outcome"] for case in cases})
        },
        "cases": cases,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x", encoding="utf-8") as destination:
        json.dump(output, destination, indent=2, allow_nan=False)


if __name__ == "__main__":
    main()
