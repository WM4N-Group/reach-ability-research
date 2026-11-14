"""Apply fixed-contract binomial bounds to existing NAV-to-PUSH rollout groups."""

import argparse
import hashlib
import json
from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mujoco"))
from reconfigurable_navigation.reachability.execution_risk import (  # noqa: E402
    lower_success_probability,
    minimum_all_successes,
)


COHORTS = ((5001, 5024), (5101, 5124), (5201, 5224))
PAIRED_SEEDS = range(5301, 5309)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def score(outcomes, alpha, target):
    successes = sum(outcome == "box_settled" for outcome in outcomes)
    lower = lower_success_probability(successes, len(outcomes), alpha)
    return {
        "successes": successes,
        "trials": len(outcomes),
        "observed_fraction": successes / len(outcomes),
        "one_sided_lower_probability": lower,
        "meets_numeric_target_under_iid_assumption": lower >= target,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--handoff-audit", type=Path, required=True)
    parser.add_argument("--nav-goal-summary", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--alpha", type=float, default=0.05)
    parser.add_argument("--target", type=float, default=0.95)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error("Output already exists")
    audit = json.loads(args.handoff_audit.read_text(encoding="utf-8"))
    pair = json.loads(args.nav_goal_summary.read_text(encoding="utf-8"))
    if audit["total_runs"] != 72 or audit["handoff_runs"] != 55 or len(pair["cases"]) != 8:
        raise ValueError("Unexpected frozen cohort sizes")
    outcomes = {case["seed"]: case["outcome"] for case in audit["cases"]}
    for case in audit["excluded_before_handoff"]:
        if case["seed"] in outcomes:
            raise ValueError("Duplicate seed in handoff audit")
        outcomes[case["seed"]] = case["outcome"]
    expected = {seed for first, last in COHORTS for seed in range(first, last + 1)}
    if set(outcomes) != expected or len({case["seed"] for case in pair["cases"]}) != 8:
        raise ValueError("Frozen seed partition mismatch")
    if set(case["seed"] for case in pair["cases"]) != set(PAIRED_SEEDS):
        raise ValueError("NAV-goal pilot seed mismatch")
    grouped = {
        f"immediate_{first}_{last}": score(
            [outcomes[seed] for seed in range(first, last + 1)], args.alpha, args.target
        )
        for first, last in COHORTS
    }
    grouped["immediate_all_72_descriptive"] = score(
        [outcomes[seed] for first, last in COHORTS for seed in range(first, last + 1)],
        args.alpha, args.target,
    )
    grouped["push_given_nav_arrival_55_descriptive"] = score(
        [case["outcome"] for case in audit["cases"]], args.alpha, args.target
    )
    for condition in ("baseline", "farther"):
        grouped[f"nav_goal_{condition}_8_exploratory"] = score(
            [case["conditions"][condition]["outcome"] for case in pair["cases"]],
            args.alpha, args.target,
        )
    paired_changes = {
        "gained_successes": sum(
            case["conditions"]["baseline"]["outcome"] != "box_settled"
            and case["conditions"]["farther"]["outcome"] == "box_settled"
            for case in pair["cases"]
        ),
        "lost_successes": sum(
            case["conditions"]["baseline"]["outcome"] == "box_settled"
            and case["conditions"]["farther"]["outcome"] != "box_settled"
            for case in pair["cases"]
        ),
    }
    result = {
        "schema_version": 1,
        "scope": "Numerical binomial limits only; not a handoff or deployment certificate",
        "assumptions": [
            "fixed policy, controller, task, scene distribution, and outcome definition within a group",
            "independent identically distributed random-seed trials within a group",
            "hypothesis and group fixed before using an independent evaluation set for certification",
        ],
        "alpha": args.alpha,
        "target_probability": args.target,
        "minimum_trials_if_all_succeed": minimum_all_successes(args.target, args.alpha),
        "handoff_audit_sha256": sha256(args.handoff_audit),
        "nav_goal_summary_sha256": sha256(args.nav_goal_summary),
        "analysis_sha256": sha256(Path(__file__)),
        "groups": grouped,
        "nav_goal_paired_changes": paired_changes,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
    print(json.dumps({"groups": grouped, "nav_goal_paired_changes": paired_changes}, indent=2))


if __name__ == "__main__":
    main()
