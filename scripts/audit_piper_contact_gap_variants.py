"""Revalidate gap-speed reports rejected by an overstrict launcher comparison."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

from audit_piper_push_deadline import audit_report


ROOT = Path(__file__).resolve().parents[1]
GAP_OPTION = "--push-contact-gap-slowdown-start"
OUTPUT_OPTION = "--output-json"


def pinned_json(entry: dict) -> dict:
    path = ROOT / entry["path"]
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != entry["sha256"]:
        raise ValueError(f"Source hash differs: {entry['path']}")
    return json.loads(raw)


def option_value(command: list[str], name: str) -> str:
    if command.count(name) != 1:
        raise ValueError(f"Missing or duplicate command option: {name}")
    return command[command.index(name) + 1]


def audit_case(parent_plan: dict, parent: dict, case: dict) -> dict:
    plan = pinned_json(case["plan"])
    status = pinned_json(case["exit_status"])
    report = pinned_json(case["report"])
    start = case["slowdown_start_m"]
    if not isinstance(start, (int, float)) or not math.isfinite(start) or start <= 0:
        raise ValueError("Invalid slowdown start")
    if (status.get("returncode") != 0 or status.get("report_valid") is not False
            or status.get("report_sha256") != case["report"]["sha256"]
            or status.get("report_error") != ""):
        raise ValueError("Original launcher status is not the expected assertion failure")
    if (plan.get("parent_report_sha256") != case["parent_report_sha256"]
            or plan.get("contact_gap_slowdown_start") != start
            or report.get("checkpoint_sha256") != parent["checkpoint_sha256"]
            or report.get("evaluation_sha256") != parent["evaluation_sha256"]
            or report.get("control_sha256") != parent["control_sha256"]
            or report.get("locomotion_policy_sha256") != parent["locomotion_policy_sha256"]):
        raise ValueError("Policy, control or report identity differs")
    for report_key, plan_key in (("checkpoint_sha256", "checkpoint_sha256"),
                                 ("evaluation_sha256", "evaluator_sha256")):
        if report[report_key] != plan[plan_key]:
            raise ValueError(f"Plan does not match report: {report_key}")
    for report_key, plan_key in (("box_push.py", "box_push_sha256"),
                                 ("box_push_control.py", "push_control_sha256"),
                                 ("box_push_ik.py", "ik_sha256")):
        if report["control_sha256"][report_key] != plan[plan_key]:
            raise ValueError(f"Plan does not match control source: {report_key}")

    command = list(plan["command"])
    parent_command = list(parent_plan["command"])
    if float(option_value(command, GAP_OPTION)) != start:
        raise ValueError("Command slowdown start differs from plan")
    option_value(command, OUTPUT_OPTION)
    option_value(parent_command, OUTPUT_OPTION)
    command[command.index(GAP_OPTION) + 1] = parent_command[parent_command.index(GAP_OPTION) + 1]
    command[command.index(OUTPUT_OPTION) + 1] = parent_command[parent_command.index(OUTPUT_OPTION) + 1]
    if command != parent_command:
        raise ValueError("Other evaluator command arguments changed")

    physics = json.loads(json.dumps(report["actual_physics"]))
    observed_start = physics["controller_contract"]["contact_gap_slowdown_start"]
    if observed_start != start:
        raise ValueError("Runtime slowdown start differs from plan")
    physics["controller_contract"]["contact_gap_slowdown_start"] = 0.0
    if physics != parent["actual_physics"]:
        raise ValueError("Other actual physics or controller values changed")
    if (report["seed"] != parent["seed"] or report["episode_length_s"] != parent["episode_length_s"]
            or report["requested_episodes"] != 8 or report["completed_episodes"] != 8
            or report["incomplete_episodes"] != 0):
        raise ValueError("Episode contract differs")

    deadline = audit_report(report, 12.0)
    return {
        "variant": case["variant"],
        "slowdown_start_m": start,
        "report_sha256": case["report"]["sha256"],
        "launcher_report_valid": False,
        "independent_report_valid": True,
        "launcher_failure_reason": "intentional_contact_gap_slowdown_start_mismatch_only",
        "termination_reasons": report["termination_reasons"],
        "minimum_control_step_clearance_m": min(
            terminal["geometry_minimum_observed"] for terminal in report["terminal_states"]),
        "control_steps_below_35mm": sum(
            terminal["geometry_below_minimum_steps"] for terminal in report["terminal_states"]),
        "max_torque_limit_ratio": report["max_torque_limit_ratio"],
        "deadline": deadline,
        "terminal_box_displacement_x_m": {
            str(terminal["env_id"]): terminal["box_displacement"][0]
            for terminal in sorted(report["terminal_states"], key=lambda item: item["env_id"])
        },
    }


def audit(manifest: dict) -> dict:
    parent_plan = pinned_json(manifest["parent_plan"])
    parent = pinned_json(manifest["parent_report"])
    for case in manifest["cases"]:
        if case["parent_report_sha256"] != manifest["parent_report"]["sha256"]:
            raise ValueError("Case does not pin the declared parent")
    return {
        "scope": "Used-seed extended-run report revalidation, not original-deadline acceptance",
        "parent_report_sha256": manifest["parent_report"]["sha256"],
        "cases": [audit_case(parent_plan, parent, case) for case in manifest["cases"]],
        "contact_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(json.loads(args.manifest.read_text()))
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"variants": [case["variant"] for case in result["cases"]],
                      "contact_authorized": result["contact_authorized"]}))


if __name__ == "__main__":
    main()
