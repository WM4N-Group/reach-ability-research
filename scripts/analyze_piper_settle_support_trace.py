"""Audit per-step support during known-seed NAV-to-PUSH preparation pilots."""

import argparse
import json
import math
from pathlib import Path

from audit_piper_handoff_initial_state import sha256


MODES = ("nav_zero_velocity", "default_posture", "hold_last_nav")
DT_S = 0.02
FOOT_FORCE_N = 2.0


def first_time(trace, predicate):
    return next((sample["settle_elapsed_s"] for sample in trace if predicate(sample)), None)


def longest_true_run(values):
    longest = current = 0
    for value in values:
        current = current + 1 if value else 0
        longest = max(longest, current)
    return longest


def extract(path, baselines):
    with path.open(encoding="utf-8") as stream:
        report = json.load(stream)
    seed = report["seed"]
    baseline = baselines[seed]
    mode = report["handoff_settle_control"]
    if (report["schema_version"] != 10 or mode not in MODES
            or not report["record_settle_support_trace"]
            or not report["record_push_support_trace"]
            or not report["record_push_contact_load_trace"]
            or abs(report["step_dt"] - DT_S) > 1e-9
            or report["handoff_settle_stable_s"] != 0.4
            or report["handoff_settle_timeout_s"] != 3.0
            or report["initial_state"] != baseline["initial_state"]
            or report["nav_arrival"]["state"] != baseline["handoff"]["state"]
            or report["nav_arrival"]["last_nav_leg_action"]
            != baseline["handoff"]["push_action_history"][-18:-6]
            or report["nav_actor_sha256"] != baseline["nav_actor_sha256"]
            or report["push_checkpoint_sha256"] != baseline["push_checkpoint_sha256"]
            or report["control_sha256"] != baseline["control_sha256"]):
        raise ValueError(f"Trace differs from the frozen arrival or experiment: {path}")
    trace = report["settle_support_trace"]
    if not trace or report["outcome"] not in ("handoff_settle_terminated", "handoff_settle_timeout"):
        raise ValueError(f"Missing preparation trace or unexpected outcome: {path}")
    foot_names = report["support_foot_body_names"]
    leg_indices = [index for index, name in enumerate(report["joint_names"])
                   if name.endswith(("_hip_joint", "_thigh_joint", "_calf_joint"))]
    if len(foot_names) != 4 or len(leg_indices) != 12:
        raise ValueError(f"Unexpected foot or joint layout: {path}")
    for index, sample in enumerate(trace):
        if abs(sample["settle_elapsed_s"] - (index + 1) * DT_S) > 1e-8:
            raise ValueError(f"Misaligned preparation step {index}: {path}")
        forces = sample["foot_normal_forces_n"]
        if (len(forces) != 4 or any(not math.isfinite(force) or force < 0 for force in forces)
                or sample["supported_feet_gt_2n"] != sum(force > FOOT_FORCE_N for force in forces)):
            raise ValueError(f"Invalid foot force at step {index}: {path}")
        for foot_index, name in enumerate(foot_names):
            contact = sample["ground_contacts"][name]
            ground_force = contact["ground_normal_force"][2]
            if not math.isfinite(ground_force) or abs(ground_force - forces[foot_index]) > 1e-3:
                raise ValueError(f"Ground/net force mismatch at step {index}: {path}")
            if forces[foot_index] > FOOT_FORCE_N:
                point = contact["ground_contact_pos"]
                if point is None or len(point) != 3 or not all(map(math.isfinite, point)):
                    raise ValueError(f"Loaded foot lacks a valid ground contact point at step {index}: {path}")
        for key in ("joint_pos", "joint_pos_target", "computed_torque", "applied_torque"):
            if len(sample[key]) != 18 or not all(map(math.isfinite, sample[key])):
                raise ValueError(f"Invalid joint telemetry at step {index}: {path}")
        if not all(math.isfinite(value) for key in ("base_pos", "base_vel", "base_omega")
                   for value in sample[key]):
            raise ValueError(f"Invalid base telemetry at step {index}: {path}")
    omega = [math.sqrt(sum(value * value for value in sample["base_omega"])) for sample in trace]
    leg_error = [max(abs(sample["joint_pos_target"][joint] - sample["joint_pos"][joint])
                     for joint in leg_indices) for sample in trace]
    return {
        "seed": seed,
        "mode": mode,
        "raw_report_sha256": sha256(path),
        "outcome": report["outcome"],
        "terminal_reason": report["terminal"].get("reasons"),
        "nav_arrival_s": report["nav_arrival"]["elapsed_s"],
        "preparation_elapsed_s": len(trace) * DT_S,
        "first_two_or_fewer_feet_s": first_time(
            trace, lambda sample: sample["supported_feet_gt_2n"] <= 2),
        "first_base_below_0p25_m_s": first_time(
            trace, lambda sample: sample["base_pos"][2] < 0.25),
        "minimum_base_height_m": min(sample["base_pos"][2] for sample in trace),
        "maximum_leg_target_error_rad": max(leg_error),
        "maximum_base_angular_speed_rad_s": max(omega),
        "samples_below_0p15_angular_speed": sum(value < 0.15 for value in omega),
        "longest_below_0p15_angular_speed_s": longest_true_run(value < 0.15 for value in omega) * DT_S,
        "samples_with_four_feet": sum(sample["supported_feet_gt_2n"] == 4 for sample in trace),
        "sample_count": len(trace),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trace-json", type=Path, nargs="+", required=True)
    parser.add_argument("--immediate-json", type=Path, nargs="+", required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error("Output file already exists")
    baselines = {}
    baseline_paths = {}
    for path in args.immediate_json:
        with path.open(encoding="utf-8") as stream:
            report = json.load(stream)
        if report["seed"] in baselines:
            raise ValueError("Duplicate immediate-handoff seed")
        baselines[report["seed"]] = report
        baseline_paths[report["seed"]] = path
    cases = [extract(path, baselines) for path in args.trace_json]
    if (len(cases) != len(baselines) * len(MODES)
            or {(case["seed"], case["mode"]) for case in cases}
            != {(seed, mode) for seed in baselines for mode in MODES}):
        raise ValueError("Expected every preparation mode once per baseline seed")
    result = {
        "schema_version": 1,
        "analysis_sha256": sha256(Path(__file__)),
        "scope": "Known-seed descriptive support timing; 0.25 m is a post hoc diagnostic marker, not a safety limit",
        "immediate_baselines": [
            {"seed": seed, "sha256": sha256(path)} for seed, path in sorted(baseline_paths.items())
        ],
        "cases": sorted(cases, key=lambda case: (case["seed"], case["mode"])),
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)


if __name__ == "__main__":
    main()
