"""Score a frozen paired NAV-goal pilot, retaining end-to-end failures."""

import argparse
import hashlib
import json
from pathlib import Path


SEEDS = range(5301, 5309)
GOALS = {"baseline": -0.05, "farther": -0.10}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def classify(report):
    if report["outcome"] != "push_terminated":
        return report["outcome"]
    return "box_settled" if report["terminal"]["reasons"].get("box_settled") else "push_safety_termination"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report-dir", type=Path, required=True)
    parser.add_argument("--protocol-json", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error("Output already exists")
    protocol = json.loads(args.protocol_json.read_text(encoding="utf-8"))
    if protocol["seeds"] != list(SEEDS) or {
        key: item["nav_goal_x_m"] for key, item in protocol["conditions"].items()
    } != GOALS:
        raise ValueError("Protocol differs from frozen runner")
    cases = []
    source_contracts = set()
    for seed in SEEDS:
        reports = {}
        for condition, goal in GOALS.items():
            path = args.report_dir / f"seed{seed}-{condition}.json"
            report = json.loads(path.read_text(encoding="utf-8"))
            if (report["seed"] != seed or report["skip_nav"] or not report["nav_arm_home"]
                    or report["nav_goal_xyyaw"] != [goal, 0.0, 0.0]
                    or report["nav_min_translation_speed_m_s"] != 0.0
                    or report["handoff_settle_stable_s"] != 0.0
                    or report["push_budget_s"] != 12.0
                    or not report["record_push_support_trace"]
                    or not report["record_push_contact_load_trace"]):
                raise ValueError(f"Condition mismatch: {path}")
            source_contracts.add((report["nav_actor_sha256"], report["push_checkpoint_sha256"],
                                  tuple(sorted(report["control_sha256"].items()))))
            reports[condition] = report
        if reports["baseline"]["initial_state"] != reports["farther"]["initial_state"]:
            raise ValueError(f"Initial scene differs for seed {seed}")
        cases.append({
            "seed": seed,
            "same_initial_state": True,
            "conditions": {
                condition: {
                    "report_sha256": sha256(args.report_dir / f"seed{seed}-{condition}.json"),
                    "outcome": classify(report),
                    "nav_arrived": "handoff" in report,
                    "nav_elapsed_s": report.get("handoff", {}).get("nav_elapsed_s"),
                    "push_elapsed_s": report["push_elapsed_s"],
                    "terminal_reasons": report.get("terminal", {}).get("reasons"),
                    "support_sample_count": len(report.get("support_trace", [])),
                }
                for condition, report in reports.items()
            },
        })
    if len(source_contracts) != 1:
        raise ValueError("Mixed source contracts")
    counts = {
        condition: {
            outcome: sum(case["conditions"][condition]["outcome"] == outcome for case in cases)
            for outcome in sorted({case["conditions"][condition]["outcome"] for case in cases})
        }
        for condition in GOALS
    }
    result = {
        "schema_version": 1,
        "scope": "Exploratory paired end-to-end NAV goal comparison in one Isaac scene",
        "protocol_sha256": sha256(args.protocol_json),
        "analysis_sha256": sha256(Path(__file__)),
        "source_contract": next(iter(source_contracts)),
        "counts": counts,
        "cases": cases,
        "farther_advances_to_new_seed_confirmation": (
            counts["farther"].get("box_settled", 0) - counts["baseline"].get("box_settled", 0) >= 2
            and counts["farther"].get("nav_timeout", 0) <= counts["baseline"].get("nav_timeout", 0)
            and counts["farther"].get("push_safety_termination", 0)
            <= counts["baseline"].get("push_safety_termination", 0)
        ),
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
    print(json.dumps(counts, indent=2))


if __name__ == "__main__":
    main()
