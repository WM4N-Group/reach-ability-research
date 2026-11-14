"""Audit post-warning support traces under the unchanged NAV-to-PUSH controller."""

import argparse
import json
from pathlib import Path

from analyze_piper_isaac_support_dynamics import sha256


def audit_case(case, result, sample_period_s=0.02):
    warning_s = case["first_warning_s"]
    if warning_s is None:
        return None
    samples = result["features"]
    warning_index = next(
        (index for index, sample in enumerate(samples)
         if abs(sample["push_elapsed_s"] - warning_s) < sample_period_s / 4), None
    )
    if warning_index is None:
        raise ValueError(f"Missing warning sample for seed {case['seed']}")
    post = samples[warning_index:]
    first_four_foot_run_s = None
    four_foot_run = 0
    longest_four_foot_run = 0
    for sample in post:
        four_foot_run = four_foot_run + 1 if sample["supported_feet_gt_2n"] == 4 else 0
        longest_four_foot_run = max(longest_four_foot_run, four_foot_run)
        if four_foot_run == 10 and first_four_foot_run_s is None:
            first_four_foot_run_s = round(sample["push_elapsed_s"] - 9 * sample_period_s, 2)
    landmark = samples[warning_index]
    margins = [sample["contact_mean_margin_m"] for sample in post
               if sample["contact_mean_margin_m"] is not None]
    return {
        "seed": case["seed"],
        "raw_report_sha256": case["raw_report_sha256"],
        "outcome": case["outcome"],
        "terminal_reasons": case["terminal_reasons"],
        "warning_s": warning_s,
        "terminal_s": case["push_elapsed_s"],
        "landmark": {
            key: landmark[key] for key in (
                "arm_approach_index", "motion_ready", "remaining_push_s",
                "supported_feet_gt_2n", "foot_normal_forces_n", "contact_mean_margin_m",
                "margin_rate_0p2_m_s", "max_leg_target_error_rad",
                "com_speed_0p2_m_s",
            )
        },
        "post_warning": {
            "minimum_supported_feet_gt_2n": min(sample["supported_feet_gt_2n"] for sample in post),
            "minimum_contact_mean_margin_m": min(margins) if margins else None,
            "maximum_contact_mean_margin_m": max(margins) if margins else None,
            "first_0p2s_four_foot_run_start_s": first_four_foot_run_s,
            "longest_four_foot_run_s": round(longest_four_foot_run * sample_period_s, 2),
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pair", nargs=2, action="append", metavar=("FEATURES", "WARNINGS"), required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error("Require a new output path")
    cases = []
    sources = []
    seen_seeds = set()
    for feature_name, warning_name in args.pair:
        feature_path, warning_path = Path(feature_name), Path(warning_name)
        with feature_path.open(encoding="utf-8") as stream:
            features = json.load(stream)
        with warning_path.open(encoding="utf-8") as stream:
            warnings = json.load(stream)
        if warnings["feature_json_sha256"] != sha256(feature_path):
            raise ValueError(f"Warning results do not match features: {warning_path}")
        feature_cases = {item["seed"]: item for item in features["results"]}
        warning_cases = {item["seed"]: item for item in warnings["cases"]}
        if len(feature_cases) != len(features["results"]) or feature_cases.keys() != warning_cases.keys():
            raise ValueError(f"Missing or duplicate seed in {feature_path} or {warning_path}")
        if seen_seeds.intersection(feature_cases):
            raise ValueError("Cohorts share a seed")
        seen_seeds.update(feature_cases)
        for seed in sorted(feature_cases):
            result, case = feature_cases[seed], warning_cases[seed]
            if (case["raw_report_sha256"] != result["input_sha256"]
                    or case["outcome"] != result["outcome"]
                    or case["push_elapsed_s"] != result["push_elapsed_s"]):
                raise ValueError(f"Feature and warning case differ for seed {seed}")
            audited = audit_case(case, result)
            if audited is not None:
                cases.append(audited)
        sources.append({"features_sha256": sha256(feature_path),
                        "warnings_sha256": sha256(warning_path),
                        "seed_count": len(feature_cases)})
    output = {
        "schema_version": 1,
        "analysis_sha256": sha256(Path(__file__)),
        "scope": "Descriptive post-warning audit under unchanged control; future samples are not predictive features or intervention evidence",
        "sources": sources,
        "warned_cases": cases,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x", encoding="utf-8") as stream:
        json.dump(output, stream, indent=2, allow_nan=False)


if __name__ == "__main__":
    main()
