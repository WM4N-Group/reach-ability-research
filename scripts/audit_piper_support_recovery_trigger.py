"""Replay one frozen read-only support-recovery trigger on archived Isaac baselines."""

import argparse
import hashlib
import json
import math
from collections import Counter
from pathlib import Path


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def classify(report):
    if report["outcome"] == "push_terminated":
        return "box_settled" if report["terminal"]["reasons"]["box_settled"] else "push_safety_termination"
    return report["outcome"]


def first_trigger(report, trigger):
    if report["push_executed_steps"] == 0:
        return None
    names = report["support_foot_body_names"]
    if len(names) != 4 or set(names) != {"FL_foot", "FR_foot", "RL_foot", "RR_foot"}:
        raise ValueError(f"Unexpected foot order for seed {report['seed']}")
    rear = (names.index("RL_foot"), names.index("RR_foot"))
    run = 0
    for index, record in enumerate(report["support_trace"]):
        values = record["foot_normal_forces_n"]
        if (len(values) != 4 or not all(math.isfinite(value) for value in values)
                or not math.isfinite(record["base_pos"][2])
                or abs(record["push_elapsed_s"] - (index + 1) * trigger["control_step_s"]) > 1e-8):
            raise ValueError(f"Invalid support sample for seed {report['seed']}")
        active = (not record["motion_ready"]
                  and record["base_pos"][2] < trigger["base_height_below_m"]
                  and any(values[foot] < trigger["rear_foot_force_below_n"] for foot in rear))
        run = run + 1 if active else 0
        if run == trigger["consecutive_control_steps"]:
            return {
                "confirmed_at_push_s": record["push_elapsed_s"],
                "condition_start_push_s": record["push_elapsed_s"]
                - (trigger["consecutive_control_steps"] - 1) * trigger["control_step_s"],
            }
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol-json", type=Path, required=True)
    parser.add_argument("--quality-json", type=Path, nargs=4, required=True)
    parser.add_argument("--trace-json", type=Path, nargs="+", required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if args.output_json.exists() or len(args.trace_json) != 80 or len(set(args.trace_json)) != 80:
        parser.error("Require 80 distinct frozen baselines and a new output path")
    protocol = json.loads(args.protocol_json.read_text(encoding="utf-8"))
    trigger = protocol["trigger"]
    if (trigger["phase"] != "PUSH before motion_ready"
            or trigger["rear_foot_condition"] != "RL or RR"
            or trigger["control_step_s"] != 0.02):
        raise ValueError("Unsupported trigger protocol")
    expected = {
        seed: name
        for name, (first, last) in protocol["retrospective_cohorts"].items()
        for seed in range(first, last + 1)
    }
    if len(expected) != 80:
        raise ValueError("Overlapping or incomplete protocol cohorts")
    quality = {}
    for path in args.quality_json:
        parsed = json.loads(path.read_text(encoding="utf-8"))
        for item in parsed["results"]:
            if item["seed"] in quality:
                raise ValueError("Duplicate sensor qualification")
            quality[item["seed"]] = item
    cases = []
    source_hashes = set()
    for path in args.trace_json:
        report = json.loads(path.read_text(encoding="utf-8"))
        seed = report["seed"]
        if (seed not in expected or any(case["seed"] == seed for case in cases)
                or report["skip_nav"] or not report["nav_arm_home"]
                or report["nav_start_x_m"] != -0.25
                or report["nav_goal_xyyaw"] != [-0.05, 0.0, 0.0]
                or report["pre_ready_leg_action_cap"] != 0.0
                or report["support_margin_pause_m"] != 0.0
                or report["hold_push_arm_at_handoff"]
                or report.get("safe_approach_arm_rate_scale", 1.0) != 1.0
                or report.get("handoff_settle_stable_s", 0.0) != 0.0
                or report.get("nav_leg_support_until_ready", False)
                or not report["record_push_support_trace"]
                or not report["record_push_contact_load_trace"]
                or len(report["support_trace"]) != report["push_executed_steps"]):
            raise ValueError(f"Not a frozen immediate baseline: {path}")
        source_hashes.add((report["nav_actor_sha256"], report["push_checkpoint_sha256"],
                           tuple(sorted(report["control_sha256"].items()))))
        digest = sha256(path)
        if report["push_executed_steps"]:
            if (seed not in quality or not quality[seed]["sensor_qualified"]
                    or quality[seed]["input_sha256"] != digest):
                raise ValueError(f"Unqualified PUSH trace: {path}")
        elif seed in quality:
            raise ValueError(f"Sensor qualification exists without PUSH: {path}")
        event = first_trigger(report, trigger)
        outcome = classify(report)
        cases.append({
            "seed": seed,
            "cohort": expected[seed],
            "report_sha256": digest,
            "outcome": outcome,
            "trigger": event,
            "push_elapsed_s": report["push_elapsed_s"],
            "lead_to_terminal_s": (report["push_elapsed_s"] - event["confirmed_at_push_s"])
            if event is not None and outcome == "push_safety_termination" else None,
            "terminal_reasons": report["terminal"].get("reasons"),
        })
    if len(cases) != 80 or len(source_hashes) != 1 or set(quality) != {
            case["seed"] for case in cases if case["push_elapsed_s"] > 0}:
        raise ValueError("Incomplete cohort, mixed sources, or missing sensor qualification")
    cohorts = {}
    for name in protocol["retrospective_cohorts"]:
        group = [case for case in cases if case["cohort"] == name]
        cohorts[name] = {
            "runs": len(group),
            "outcomes": dict(Counter(case["outcome"] for case in group)),
            "triggered_safety_terminations": sum(
                case["outcome"] == "push_safety_termination" and case["trigger"] is not None for case in group
            ),
            "safety_terminations": sum(case["outcome"] == "push_safety_termination" for case in group),
            "triggered_box_settled": sum(
                case["outcome"] == "box_settled" and case["trigger"] is not None for case in group
            ),
            "box_settled": sum(case["outcome"] == "box_settled" for case in group),
        }
    result = {
        "schema_version": 1,
        "analysis_sha256": sha256(Path(__file__)),
        "protocol_sha256": sha256(args.protocol_json),
        "quality_json_sha256": [sha256(path) for path in args.quality_json],
        "scope": "Retrospective read-only trigger falsification on previously inspected seed blocks; no control or admission permission",
        "source_hashes": list(source_hashes)[0],
        "total_runs": len(cases),
        "qualified_push_traces": len(quality),
        "cohorts": cohorts,
        "cases": sorted(cases, key=lambda case: case["seed"]),
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x", encoding="utf-8") as destination:
        json.dump(result, destination, indent=2, allow_nan=False)


if __name__ == "__main__":
    main()
