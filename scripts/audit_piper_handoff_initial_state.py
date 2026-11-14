"""Describe the NAV-to-PUSH handoff projection across frozen Isaac cohorts."""

import argparse
import hashlib
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def outcome(report):
    if report["outcome"] == "push_terminated":
        return "box_settled" if report["terminal"]["reasons"]["box_settled"] else "push_safety_termination"
    return report["outcome"]


def handoff_case(path):
    with path.open(encoding="utf-8") as stream:
        report = json.load(stream)
    if (report["skip_nav"] or report["hold_push_arm_at_handoff"]
            or report["pre_ready_leg_action_cap"] != 0
            or report["support_margin_pause_m"] != 0
            or report.get("safe_approach_arm_rate_scale", 1.0) != 1.0
            or report.get("handoff_settle_stable_s", 0.0) != 0.0):
        raise ValueError(f"Not an immediate unmodified handoff baseline: {path}")
    handoff = report.get("handoff")
    if handoff is None:
        return None, report
    state = handoff["state"]
    initial = report["initial_state"]
    names = report["joint_names"]
    leg_indices = [index for index, name in enumerate(names)
                   if name.endswith(("_hip_joint", "_thigh_joint", "_calf_joint"))]
    if len(leg_indices) != 12:
        raise ValueError(f"Unexpected joint layout in {path}")
    telemetry = handoff["telemetry"]
    case = {
        "seed": report["seed"],
        "raw_report_sha256": sha256(path),
        "outcome": outcome(report),
        "nav_elapsed_s": handoff["nav_elapsed_s"],
        "planar_speed_m_s": math.hypot(*state["base_vel"][:2]),
        "base_angular_speed_rad_s": math.sqrt(sum(value * value for value in state["base_omega"])),
        "arm_joint_speed_max_rad_s": telemetry["arm_approach"]["joint_velocity_max_abs"],
        "arm_home_error_max_rad": telemetry["arm_approach"]["waypoint_joint_distance_max_abs"][0],
        "supported_feet_gt_2n": telemetry["supported_feet_gt_2n"],
        "leg_position_change_from_nav_reset_max_rad": max(
            abs(state["joint_pos"][index] - initial["joint_pos"][index]) for index in leg_indices
        ),
        "handoff_action_history_max_abs": max(map(abs, handoff["push_action_history"])),
    }
    return case, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trace-json", type=Path, nargs="+", required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if args.output_json.exists() or len(set(args.trace_json)) != len(args.trace_json):
        parser.error("Require distinct traces and a new output path")
    cases = []
    excluded = []
    sources = set()
    for path in args.trace_json:
        case, report = handoff_case(path)
        sources.add((report["nav_actor_sha256"], report["push_checkpoint_sha256"],
                     tuple(sorted(report["control_sha256"].items()))))
        if case is None:
            excluded.append({"seed": report["seed"], "outcome": report["outcome"],
                             "raw_report_sha256": sha256(path)})
        else:
            cases.append(case)
    if len(sources) != 1 or len({case["seed"] for case in cases} | {case["seed"] for case in excluded}) != len(args.trace_json):
        raise ValueError("Mixed source hashes or duplicate seeds")
    groups = defaultdict(list)
    for case in cases:
        groups[case["outcome"]].append(case)
    fields = ("planar_speed_m_s", "base_angular_speed_rad_s", "arm_joint_speed_max_rad_s",
              "arm_home_error_max_rad", "leg_position_change_from_nav_reset_max_rad")
    summaries = {
        name: {
            "count": len(items),
            "median": {field: statistics.median(item[field] for item in items) for field in fields},
            "range": {field: [min(item[field] for item in items), max(item[field] for item in items)]
                      for field in fields},
        }
        for name, items in sorted(groups.items())
    }
    result = {
        "schema_version": 1,
        "analysis_sha256": sha256(Path(__file__)),
        "scope": "Descriptive recorded handoff projection; NAV reset is not a matched PUSH reset or full controller state",
        "total_runs": len(args.trace_json),
        "handoff_runs": len(cases),
        "excluded_before_handoff": excluded,
        "summaries": summaries,
        "cases": sorted(cases, key=lambda case: case["seed"]),
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)


if __name__ == "__main__":
    main()
