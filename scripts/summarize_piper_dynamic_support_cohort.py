"""Make an outcome-complete descriptive comparison from frozen PUSH feature traces."""

import argparse
import json
import statistics
from collections import Counter
from pathlib import Path

from analyze_piper_isaac_support_dynamics import sha256


FEATURES = (
    "contact_mean_margin_m",
    "margin_rate_0p2_m_s",
    "com_speed_0p2_m_s",
    "supported_feet_gt_2n",
    "minimum_foot_normal_force_n",
    "max_leg_target_error_rad",
    "arm_approach_index",
    "remaining_push_s",
)
LEADS_S = (1.0, 0.5, 0.2)
SUSTAINED_STEPS = 10
DT_S = 0.02


def sample_at(result, time_s):
    index = round(time_s / DT_S) - 1
    if index < 0 or index >= result["feature_count"]:
        return None
    sample = result["features"][index]
    if abs(sample["push_elapsed_s"] - time_s) > DT_S / 2 + 1e-8:
        raise ValueError(f"Time alignment failed for seed {result['seed']}")
    return sample


def first_sustained_loss(result):
    run = 0
    for sample in result["features"]:
        run = run + 1 if sample["supported_feet_gt_2n"] < 4 else 0
        if run == SUSTAINED_STEPS:
            return round(sample["push_elapsed_s"] - (SUSTAINED_STEPS - 1) * DT_S, 2)
    return None


def reference(successes, time_s):
    samples = [sample_at(result, time_s) for result in successes]
    if any(sample is None for sample in samples):
        raise ValueError(f"Success comparator missing at PUSH {time_s:.2f}s")
    summary = {}
    for key in FEATURES:
        values = [sample[key] for sample in samples if sample[key] is not None]
        summary[key] = {
            "minimum": min(values),
            "median": statistics.median(values),
            "maximum": max(values),
            "available": len(values),
        } if values else None
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature-json", type=Path, required=True)
    parser.add_argument("--quality-json", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error("Require a new output path")
    with args.feature_json.open(encoding="utf-8") as source:
        features = json.load(source)
    with args.quality_json.open(encoding="utf-8") as source:
        quality = json.load(source)
    results = features["results"]
    quality_by_seed = {result["seed"]: result for result in quality["results"]}
    push_seeds = {result["seed"] for result in results if result["feature_count"]}
    if (features["protocol_sha256"] is None or len(results) != 24
            or len({result["seed"] for result in results}) != 24
            or len(quality_by_seed) != len(quality["results"])
            or push_seeds != set(quality_by_seed)
            or not all(result["sensor_qualified"] for result in quality_by_seed.values())
            or any(result["input_sha256"] != quality_by_seed[result["seed"]]["input_sha256"]
                   for result in results if result["seed"] in quality_by_seed)):
        raise ValueError("Incomplete cohort or unqualified PUSH telemetry")
    successes = [result for result in results if result["outcome"] == "box_settled"]
    safety_failures = [result for result in results if result["outcome"] == "push_safety_termination"]
    if not successes or not safety_failures:
        raise ValueError("Descriptive comparison requires both success and safety failure")
    cases = []
    for result in results:
        summary = {
            "seed": result["seed"],
            "raw_report_sha256": result["input_sha256"],
            "outcome": result["outcome"],
            "push_elapsed_s": result["push_elapsed_s"],
            "push_samples": result["feature_count"],
            "terminal_reasons": result["terminal_reasons"],
            "first_ten_sample_subfour_start_s": first_sustained_loss(result),
            "minimum_contact_mean_margin_5_to_7p4_m": (
                quality_by_seed[result["seed"]]["minimum_contact_mean_margin_proxy_5_to_7p4_m"]
                if result["seed"] in quality_by_seed else None
            ),
        }
        if result["outcome"] == "push_safety_termination":
            observations = []
            for lead_s in LEADS_S:
                time_s = round(result["push_elapsed_s"] - lead_s, 2)
                sample = sample_at(result, time_s)
                observations.append({
                    "lead_s": lead_s,
                    "push_time_s": time_s,
                    "failure": {key: sample[key] for key in FEATURES},
                    "success_reference_at_same_push_time": reference(successes, time_s),
                })
            loss_start = summary["first_ten_sample_subfour_start_s"]
            summary["subfour_to_terminal_lead_s"] = (
                round(result["push_elapsed_s"] - loss_start, 2) if loss_start is not None else None
            )
            summary["preterminal_observations"] = observations
        cases.append(summary)
    output = {
        "schema_version": 1,
        "analysis_sha256": sha256(Path(__file__)),
        "feature_json_sha256": sha256(args.feature_json),
        "quality_json_sha256": sha256(args.quality_json),
        "protocol_sha256": features["protocol_sha256"],
        "feature_analysis_sha256": features["analysis_sha256"],
        "quality_analysis_sha256": quality["analysis_sha256"],
        "source_hashes": features["source_hashes"],
        "scope": "Descriptive matched-PUSH-time comparison only; no fitted predictor, threshold, causal identification or reachability certificate",
        "lead_times_s": list(LEADS_S),
        "success_reference_n": len(successes),
        "outcome_counts": dict(Counter(result["outcome"] for result in results)),
        "qualified_push_traces": len(quality_by_seed),
        "cases": cases,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x", encoding="utf-8") as destination:
        json.dump(output, destination, indent=2, allow_nan=False)


if __name__ == "__main__":
    main()
