"""Replay an older frozen support trigger on the new baseline cohort."""

import argparse
import json
from collections import Counter
from pathlib import Path

from audit_piper_nav_push_baseline_cohort import sha256
from audit_piper_support_recovery_trigger import first_trigger


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cohort-audit", type=Path, required=True)
    parser.add_argument("--trigger-protocol", type=Path, required=True)
    parser.add_argument("--reports-dir", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error("Output file already exists")
    cohort = json.loads(args.cohort_audit.read_text(encoding="utf-8"))
    trigger_protocol = json.loads(args.trigger_protocol.read_text(encoding="utf-8"))
    if (cohort["total_runs"] != 24 or cohort["qualified_push_traces"] != cohort["push_entrants"]
            or trigger_protocol["trigger"]["control_step_s"] != 0.02):
        raise ValueError("Unexpected cohort or frozen trigger contract")
    cases = []
    for case in cohort["cases"]:
        path = args.reports_dir / f"seed{case['seed']}-baseline.json"
        if sha256(path) != case["report_sha256"]:
            raise ValueError(f"Seed{case['seed']} raw report differs from qualification")
        report = json.loads(path.read_text(encoding="utf-8"))
        event = first_trigger(report, trigger_protocol["trigger"])
        cases.append({
            "seed": case["seed"],
            "category": case["category"],
            "report_sha256": case["report_sha256"],
            "trigger": event,
            "push_elapsed_s": case["push_elapsed_s"],
            "lead_to_terminal_s": case["push_elapsed_s"] - event["confirmed_at_push_s"]
            if event is not None and case["category"] == "push_safety_termination" else None,
            "terminal_reasons": case["terminal_reasons"],
        })
    counts = Counter((case["category"], case["trigger"] is not None) for case in cases)
    summary = {
        category: {
            "runs": sum(case["category"] == category for case in cases),
            "triggered": counts[(category, True)],
        }
        for category in sorted({case["category"] for case in cases})
    }
    result = {
        "schema_version": 1,
        "analysis_sha256": sha256(Path(__file__)),
        "cohort_audit_sha256": sha256(args.cohort_audit),
        "trigger_protocol_sha256": sha256(args.trigger_protocol),
        "trigger": trigger_protocol["trigger"],
        "summary": summary,
        "cases": cases,
        "scope": "Post-outcome exploratory replay of a previously frozen read-only trigger; selection of this replay after seeing the cohort prevents treating it as preregistered validation, and a trigger does not prove irrecoverability or authorize control",
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
