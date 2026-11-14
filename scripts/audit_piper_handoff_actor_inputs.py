"""Validate a frozen cohort of recorded NAV-to-PUSH actor inputs."""

import argparse
import hashlib
import json
import math
from collections import Counter
from pathlib import Path


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def finite_vector(value, length):
    return isinstance(value, list) and len(value) == length and all(
        isinstance(item, (int, float)) and math.isfinite(item) for item in value
    )


def classify(report):
    if report["outcome"] == "push_terminated":
        return "box_settled" if report["terminal"]["reasons"]["box_settled"] else "push_safety_termination"
    return report["outcome"]


def inspect(path, protocol):
    with path.open(encoding="utf-8") as source:
        report = json.load(source)
    expected = protocol["control"]
    if (report["schema_version"] != 11
            or report["seed"] not in protocol["seeds"]
            or report["nav_actor_sha256"] != expected["nav_actor_sha256"]
            or report["push_checkpoint_sha256"] != expected["push_checkpoint_sha256"]
            or report["skip_nav"] or not report["nav_arm_home"]
            or report["nav_start_x_m"] != expected["nav_start_x_m"]
            or report["nav_goal_xyyaw"] != [expected["nav_goal_x_m"], 0.0, 0.0]
            or report["nav_min_translation_speed_m_s"] != expected["nav_min_translation_speed_m_s"]
            or report["nav_timeout_s"] != expected["nav_timeout_s"]
            or report["handoff_settle_stable_s"] != expected["handoff_settle_stable_s"]
            or report["push_budget_s"] != expected["push_budget_s"]
            or not report["record_push_support_trace"]
            or not report["record_push_contact_load_trace"]
            or report["hold_push_arm_at_handoff"]
            or report["pre_ready_leg_action_cap"] != 0.0
            or report["support_margin_pause_m"] != 0.0
            or report["safe_approach_arm_rate_scale"] != 1.0
            or report["nav_leg_support_until_ready"]):
        raise ValueError(f"Report does not match frozen baseline: {path}")
    handoff = report.get("handoff")
    if handoff is None:
        if report["push_executed_steps"] != 0:
            raise ValueError(f"PUSH ran without a handoff record: {path}")
    else:
        nav_input = handoff["last_nav_actor_input"]
        push_input = handoff["first_push_actor_input"]
        if (not finite_vector(nav_input, 210) or not finite_vector(push_input, 226)
                or handoff["push_actor_input_groups"] != ["policy", "box"]
                or handoff["push_observation_shape"] != [1, 226]
                or handoff["last_nav_actor_step"] + 1 != handoff["first_push_actor_step"]
                or handoff["first_push_actor_step"] != handoff["nav_steps"]
                or handoff["last_nav_actor_action_replaced_by_settle_control"] is not False
                or push_input[126:180] != handoff["push_action_history"]
                or not math.isclose(handoff["nav_elapsed_s"], handoff["nav_steps"] * report["step_dt"], abs_tol=1e-8)
                or report["push_executed_steps"] < 1):
            raise ValueError(f"Actor input provenance or handoff time failed: {path}")
    return report, {
        "seed": report["seed"],
        "report_sha256": sha256(path),
        "outcome": classify(report),
        "nav_arrived": handoff is not None,
        "nav_steps": handoff["nav_steps"] if handoff else None,
        "last_nav_actor_step": handoff["last_nav_actor_step"] if handoff else None,
        "first_push_actor_step": handoff["first_push_actor_step"] if handoff else None,
        "handoff_supported_feet_gt_2n": handoff["telemetry"]["supported_feet_gt_2n"] if handoff else None,
        "push_executed_steps": report["push_executed_steps"],
        "terminal_reasons": report["terminal"].get("reasons"),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol-json", type=Path, required=True)
    parser.add_argument("--diagnostic-script", type=Path, required=True)
    parser.add_argument("--trace-json", type=Path, nargs="+", required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if args.output_json.exists() or len(args.trace_json) != 8 or len(set(args.trace_json)) != 8:
        parser.error("Require eight distinct traces and a new output path")
    with args.protocol_json.open(encoding="utf-8") as source:
        protocol = json.load(source)
    if sha256(args.diagnostic_script) != protocol["control"]["diagnostic_sha256"]:
        raise ValueError("Diagnostic source differs from frozen protocol")
    inspected = [inspect(path, protocol) for path in args.trace_json]
    reports, cases = zip(*inspected)
    if (set(case["seed"] for case in cases) != set(protocol["seeds"])
            or len({case["seed"] for case in cases}) != len(cases)
            or len({tuple(sorted(report["control_sha256"].items())) for report in reports}) != 1):
        raise ValueError("Incomplete cohort, duplicate seed, or mixed control source")
    result = {
        "schema_version": 1,
        "analysis_sha256": sha256(Path(__file__)),
        "protocol_sha256": sha256(args.protocol_json),
        "diagnostic_sha256": sha256(args.diagnostic_script),
        "control_sha256": reports[0]["control_sha256"],
        "scope": "Read-only actor input provenance and outcomes; no fitted admission rule or reachability certificate",
        "total_runs": len(cases),
        "handoff_runs": sum(case["nav_arrived"] for case in cases),
        "outcome_counts": dict(Counter(case["outcome"] for case in cases)),
        "cases": sorted(cases, key=lambda case: case["seed"]),
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x", encoding="utf-8") as destination:
        json.dump(result, destination, indent=2, allow_nan=False)


if __name__ == "__main__":
    main()
