"""Replay a frozen causal support warning over NAV-to-PUSH feature traces."""

import argparse
import json
from collections import Counter
from pathlib import Path

from analyze_piper_isaac_support_dynamics import sha256


def first_warning(result, rule):
    run = 0
    for sample in result["features"]:
        run = run + 1 if sample["supported_feet_gt_2n"] < 4 else 0
        if (run >= rule["minimum_consecutive_subfour_samples"]
                and sample["contact_mean_margin_m"] is not None
                and sample["margin_rate_0p2_m_s"] is not None
                and sample["contact_mean_margin_m"] <= rule["maximum_contact_mean_margin_m"]
                and sample["margin_rate_0p2_m_s"] <= rule["maximum_margin_rate_m_s"]
                and sample["max_leg_target_error_rad"] >= rule["minimum_max_leg_target_error_rad"]):
            return sample["push_elapsed_s"]
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature-json", type=Path, required=True)
    parser.add_argument("--protocol-json", type=Path, required=True)
    parser.add_argument("--cohort", choices=("discovery", "holdout"), required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error("Require a new output path")
    with args.feature_json.open(encoding="utf-8") as source:
        features = json.load(source)
    with args.protocol_json.open(encoding="utf-8") as source:
        protocol = json.load(source)
    if sha256(Path(__file__)) != protocol["warning_evaluator_sha256"]:
        raise ValueError("Warning evaluator differs from frozen protocol")
    results = features["results"]
    expected_seeds = protocol["discovery_seeds"] if args.cohort == "discovery" else protocol["seeds"]
    if (sorted(result["seed"] for result in results) != sorted(expected_seeds)
            or features["analysis_sha256"] != protocol["feature_extractor_sha256"]
            or features["source_hashes"]["nav_actor_sha256"] != protocol["nav_actor_sha256"]
            or features["source_hashes"]["push_checkpoint_sha256"] != protocol["push_checkpoint_sha256"]
            or features["source_hashes"]["control_sha256"] != protocol["control_sha256"]):
        raise ValueError("Feature cohort or frozen source hashes differ from protocol")
    if args.cohort == "discovery" and features["protocol_sha256"] != protocol["discovery_protocol_sha256"]:
        raise ValueError("Discovery data differ from frozen source protocol")
    if args.cohort == "holdout" and features["protocol_sha256"] != sha256(args.protocol_json):
        raise ValueError("Holdout features differ from frozen warning protocol")
    cases = []
    for result in results:
        warning_s = first_warning(result, protocol["warning"])
        cases.append({
            "seed": result["seed"],
            "raw_report_sha256": result["input_sha256"],
            "outcome": result["outcome"],
            "terminal_reasons": result["terminal_reasons"],
            "push_elapsed_s": result["push_elapsed_s"],
            "first_warning_s": warning_s,
            "warning_to_terminal_s": (
                round(result["push_elapsed_s"] - warning_s, 2) if warning_s is not None else None
            ),
        })
    output = {
        "schema_version": 1,
        "analysis_sha256": sha256(Path(__file__)),
        "feature_json_sha256": sha256(args.feature_json),
        "protocol_sha256": sha256(args.protocol_json),
        "cohort": args.cohort,
        "scope": "Causal offline replay of a read-only warning; no control intervention, calibrated probability or reachability certificate",
        "outcome_counts": dict(Counter(case["outcome"] for case in cases)),
        "warning_counts_by_outcome": {
            outcome: sum(case["first_warning_s"] is not None for case in cases if case["outcome"] == outcome)
            for outcome in sorted({case["outcome"] for case in cases})
        },
        "cases": cases,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x", encoding="utf-8") as destination:
        json.dump(output, destination, indent=2, allow_nan=False)


if __name__ == "__main__":
    main()
