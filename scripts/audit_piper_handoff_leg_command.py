"""Audit the first NAV-to-PUSH leg target change in frozen Isaac traces."""

import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path

from audit_piper_handoff_initial_state import handoff_case, sha256


DEFAULT_LEG_TARGETS = {
    "FL_hip_joint": 0.1, "FR_hip_joint": -0.1,
    "RL_hip_joint": 0.1, "RR_hip_joint": -0.1,
    "FL_thigh_joint": 0.8, "FR_thigh_joint": 0.8,
    "RL_thigh_joint": 1.0, "RR_thigh_joint": 1.0,
    "FL_calf_joint": -1.5, "FR_calf_joint": -1.5,
    "RL_calf_joint": -1.5, "RR_calf_joint": -1.5,
}
ACTION_SCALE_RAD = 0.25


def audit(path):
    case, report = handoff_case(path)
    if case is None:
        return None, report
    trace = report.get("support_trace")
    if not trace or len(report["handoff"]["push_action_history"]) != 54:
        raise ValueError(f"Missing PUSH trace or three-frame action history: {path}")
    joint_names = report["joint_names"]
    leg_indices = [index for index, name in enumerate(joint_names) if name in DEFAULT_LEG_TARGETS]
    if len(leg_indices) != 12:
        raise ValueError(f"Unexpected leg joint layout: {path}")
    first = trace[0]
    target = first.get("joint_pos_target")
    if target is None or len(target) != len(joint_names) or first["motion_ready"]:
        raise ValueError(f"First PUSH step is not a recorded pre-ready target: {path}")
    if first["push_elapsed_s"] != 0.02:
        raise ValueError(f"Unexpected PUSH control interval: {path}")
    if any(abs(target[index] - DEFAULT_LEG_TARGETS[joint_names[index]]) > 1e-5
           for index in leg_indices):
        raise ValueError(f"First PUSH target differs from default leg posture: {path}")
    last_nav_leg_action = report["handoff"]["push_action_history"][-18:-6]
    return {
        "seed": case["seed"],
        "outcome": case["outcome"],
        "raw_report_sha256": case["raw_report_sha256"],
        "last_nav_leg_action_max_abs": max(map(abs, last_nav_leg_action)),
        "first_push_leg_target_change_max_rad": ACTION_SCALE_RAD * max(map(abs, last_nav_leg_action)),
        "first_push_motion_ready": first["motion_ready"],
    }, report


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
        case, report = audit(path)
        sources.add((report["nav_actor_sha256"], report["push_checkpoint_sha256"],
                     tuple(sorted(report["control_sha256"].items()))))
        if case is None:
            excluded.append({"seed": report["seed"], "outcome": report["outcome"],
                             "raw_report_sha256": sha256(path)})
        else:
            cases.append(case)
    if len(sources) != 1 or len({case["seed"] for case in cases} |
                            {case["seed"] for case in excluded}) != len(args.trace_json):
        raise ValueError("Mixed source hashes or duplicate seeds")
    groups = defaultdict(list)
    for case in cases:
        groups[case["outcome"]].append(case["first_push_leg_target_change_max_rad"])
    result = {
        "schema_version": 1,
        "analysis_sha256": sha256(Path(__file__)),
        "scope": "Recorded target change at immediate handoff; descriptive, not a causal test",
        "action_scale_rad": ACTION_SCALE_RAD,
        "total_runs": len(args.trace_json),
        "handoff_runs": len(cases),
        "excluded_before_handoff": sorted(excluded, key=lambda item: item["seed"]),
        "summaries": {
            name: {"count": len(values), "median_rad": statistics.median(values),
                   "range_rad": [min(values), max(values)]}
            for name, values in sorted(groups.items())
        },
        "cases": sorted(cases, key=lambda case: case["seed"]),
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)


if __name__ == "__main__":
    main()
