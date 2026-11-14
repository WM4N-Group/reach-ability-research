"""Audit complete NAV-to-PUSH baseline cohorts without discarding failed episodes."""

import argparse
import hashlib
import json
import math
from collections import Counter
from pathlib import Path


CONTROL_SHA256 = {
    "box_push.py": "889a812aa2676b8c0d3d340419af407a64dee67b8d4a07812c1ce0aa74bb1d1d",
    "box_push_control.py": "92d5135c09feaff66ae848709588f1d2aa75af40e55f7e4428445fb95c0c5b3d",
    "box_push_ik.py": "6086163efb4d64b5a812cb2cbe506bc82eaafbca6b08186151fab7a1145f9370",
    "box_push_actions.py": "d92f8d006b1f5b74b7603501ec68a38fe88894e151c961fafcfb15adaf92d7c5",
}
FEET = ("FL_foot", "FR_foot", "RL_foot", "RR_foot")


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def describe(seed, path, protocol):
    report = json.loads(path.read_text(encoding="utf-8"))
    control = protocol["control"]
    if (report["seed"] != seed or report["schema_version"] != 14
            or report["nav_actor_sha256"] != control["nav_actor_sha256"]
            or report["push_checkpoint_sha256"] != control["push_checkpoint_sha256"]
            or report["control_sha256"] != CONTROL_SHA256
            or report["skip_nav"] or not report["nav_arm_home"]
            or report["nav_start_x_m"] != control["nav_start_x_m"]
            or report["nav_goal_xyyaw"][0] != control["nav_goal_x_m"]
            or report["push_budget_s"] != control["push_budget_s"]
            or report["front_foot_feedback"] or report["front_foot_hold_offset_m"]
            or report["front_foot_probe_offset_m"]
            or not report["record_push_support_trace"]
            or not report["record_push_contact_load_trace"]
            or not report["record_leg_jacobian_trace"]
            or not report["record_base_contact_source"]
            or abs(report["step_dt"] - 0.02) > 1e-9
            or set(report["support_foot_body_names"]) != set(FEET)):
        raise ValueError(f"Seed{seed} source or baseline contract differs")
    trace = report["support_trace"]
    if len(trace) != report["push_executed_steps"]:
        raise ValueError(f"Seed{seed} incomplete PUSH trace")
    reasons = report["terminal"].get("reasons", {})
    if report["outcome"] == "nav_timeout":
        if trace or "handoff" in report:
            raise ValueError(f"Seed{seed} NAV timeout unexpectedly entered PUSH")
        category = "nav_timeout"
    elif report["outcome"] == "push_budget_exhausted":
        if not trace or abs(report["push_elapsed_s"] - 12.0) > 1e-8:
            raise ValueError(f"Seed{seed} invalid PUSH budget outcome")
        category = "push_budget_exhausted"
    elif report["outcome"] == "push_terminated":
        if not trace or not any(reasons.values()):
            raise ValueError(f"Seed{seed} missing PUSH termination reason")
        category = "box_settled" if reasons.get("box_settled") and sum(bool(v) for v in reasons.values()) == 1 else "push_safety_termination"
    else:
        category = report["outcome"]
    loaded = {foot: 0 for foot in FEET}
    max_force_error = 0.0
    for index, sample in enumerate(trace):
        if (abs(sample["push_elapsed_s"] - (index + 1) * 0.02) > 1e-8
                or len(sample["foot_normal_forces_n"]) != 4
                or len(sample["joint_pos_target"]) != 18
                or len(sample["computed_torque"]) != 18
                or len(sample["applied_torque"]) != 18):
            raise ValueError(f"Seed{seed} malformed PUSH sample {index}")
        for key in ("joint_pos_target", "computed_torque", "applied_torque"):
            if not all(math.isfinite(value) for value in sample[key]):
                raise ValueError(f"Seed{seed} nonfinite joint telemetry at sample {index}")
        for foot_index, foot in enumerate(report["support_foot_body_names"]):
            contact = sample["ground_contacts"][foot]
            net_force = sample["foot_normal_forces_n"][foot_index]
            ground_force = contact["ground_normal_force"][2]
            if not math.isfinite(net_force) or not math.isfinite(ground_force):
                raise ValueError(f"Seed{seed} nonfinite foot force at sample {index}")
            max_force_error = max(max_force_error, abs(net_force - ground_force))
            if ground_force > 2.0:
                point = contact["ground_contact_pos"]
                if point is None or len(point) != 3 or not all(math.isfinite(value) for value in point):
                    raise ValueError(f"Seed{seed} loaded foot lacks finite ground point at sample {index}")
                loaded[foot] += 1
    sensor_qualified = not trace or (all(loaded.values()) and max_force_error < 1e-3)
    return {
        "seed": seed,
        "report_sha256": sha256(path),
        "outcome": report["outcome"],
        "category": category,
        "push_elapsed_s": report["push_elapsed_s"],
        "push_samples": len(trace),
        "terminal_reasons": reasons,
        "sensor_qualified": sensor_qualified,
        "loaded_ground_samples_by_foot": loaded if trace else None,
        "max_abs_ground_vs_net_normal_force_error_n": max_force_error if trace else None,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol-json", type=Path, required=True)
    parser.add_argument("--reports-dir", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error("Output file already exists")
    protocol = json.loads(args.protocol_json.read_text(encoding="utf-8"))
    seeds = protocol["seeds_in_order"]
    if (seeds != list(range(5701, 5725)) or len(set(seeds)) != len(seeds)
            or len(list(args.reports_dir.glob("seed*-baseline.json"))) != len(seeds)):
        raise ValueError("Incomplete or unexpected baseline cohort")
    cases = [describe(seed, args.reports_dir / f"seed{seed}-baseline.json", protocol)
             for seed in seeds]
    result = {
        "schema_version": 1,
        "analysis_sha256": sha256(Path(__file__)),
        "protocol_sha256": sha256(args.protocol_json),
        "total_runs": len(cases),
        "push_entrants": sum(case["push_samples"] > 0 for case in cases),
        "qualified_push_traces": sum(case["push_samples"] > 0 and case["sensor_qualified"] for case in cases),
        "outcome_counts": dict(Counter(case["category"] for case in cases)),
        "cases": cases,
        "interpretation": protocol["interpretation"],
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
    print(json.dumps({key: result[key] for key in ("total_runs", "push_entrants", "qualified_push_traces", "outcome_counts")}))


if __name__ == "__main__":
    main()
