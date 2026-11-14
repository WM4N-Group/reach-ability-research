"""Check read-only leg Jacobian reruns against their original Isaac trajectories."""

import argparse
import hashlib
import json
import math
from pathlib import Path


FOOT_NAMES = ("FL_foot", "FR_foot", "RL_foot", "RR_foot")


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def old_fields_match(old, new):
    if isinstance(old, dict):
        return isinstance(new, dict) and all(
            key in new and old_fields_match(value, new[key]) for key, value in old.items()
        )
    if isinstance(old, list):
        return isinstance(new, list) and len(old) == len(new) and all(
            old_fields_match(a, b) for a, b in zip(old, new)
        )
    return type(old) is type(new) and old == new


def authority(record):
    legs = record["leg_jacobians"]
    if set(legs) != set(FOOT_NAMES):
        raise ValueError("Incomplete foot Jacobian set")
    minima = []
    margins = []
    errors = []
    for name in FOOT_NAMES:
        leg = legs[name]
        values = leg["foot_position_jacobian_singular_values"]
        margin = leg["minimum_soft_joint_limit_margin_rad"]
        error = leg["maximum_joint_target_error_rad"]
        if (len(values) != 3 or not all(isinstance(value, (int, float)) and math.isfinite(value)
                                             for value in values)
                or not values[0] >= values[1] >= values[2] >= 0
                or not math.isfinite(margin) or not math.isfinite(error) or error < 0):
            raise ValueError(f"Invalid leg authority for {name}")
        minima.append(values[2])
        margins.append(margin)
        errors.append(error)
    return {
        "minimum_foot_position_jacobian_singular_value": min(minima),
        "minimum_soft_joint_limit_margin_rad": min(margins),
        "maximum_joint_target_error_rad": max(errors),
    }


def sample(trace, time_s, dt):
    index = round(time_s / dt) - 1
    if index < 0 or index >= len(trace) or abs(trace[index]["push_elapsed_s"] - time_s) > 1e-8:
        raise ValueError(f"Missing matched PUSH sample at {time_s}s")
    return {
        "push_elapsed_s": time_s,
        "supported_feet_gt_2n": trace[index]["supported_feet_gt_2n"],
        **authority(trace[index]),
    }


def inspect(old_path, new_path, expected_seed, protocol):
    old = json.loads(old_path.read_text(encoding="utf-8"))
    new = json.loads(new_path.read_text(encoding="utf-8"))
    expected = protocol["control"]
    if (old["seed"] != expected_seed or new["seed"] != expected_seed
            or new["schema_version"] != 12 or not new["record_leg_jacobian_trace"]
            or new["nav_actor_sha256"] != expected["nav_actor_sha256"]
            or new["push_checkpoint_sha256"] != expected["push_checkpoint_sha256"]
            or new["nav_goal_xyyaw"] != [expected["nav_goal_x_m"], 0.0, 0.0]
            or new["nav_start_x_m"] != expected["nav_start_x_m"]
            or not new["nav_arm_home"] or new["hold_push_arm_at_handoff"]
            or new["pre_ready_leg_action_cap"] != 0.0
            or new["support_margin_pause_m"] != 0.0
            or new["safe_approach_arm_rate_scale"] != 1.0
            or new["outcome"] != old["outcome"]
            or new["push_executed_steps"] != old["push_executed_steps"]):
        raise ValueError(f"Probe differs from frozen baseline: seed {expected_seed}")
    old.pop("schema_version")
    new.pop("schema_version")
    if not old_fields_match(old, new):
        raise ValueError(f"Original trajectory fields changed: seed {expected_seed}")
    trace = new["support_trace"]
    if len(trace) != new["push_executed_steps"] or abs(new["step_dt"] - 0.02) > 1e-9:
        raise ValueError(f"Unexpected trace duration: seed {expected_seed}")
    handoff_authority = authority(new["handoff"])
    all_authority = [authority(record) for record in trace]
    return {
        "seed": expected_seed,
        "old_report_sha256": sha256(old_path),
        "new_report_sha256": sha256(new_path),
        "legacy_fields_exact": True,
        "terminal_reasons": new["terminal"]["reasons"],
        "push_elapsed_s": new["push_elapsed_s"],
        "push_executed_steps": new["push_executed_steps"],
        "handoff_authority": handoff_authority,
        "trajectory_minimum_singular_value": min(
            item["minimum_foot_position_jacobian_singular_value"] for item in all_authority
        ),
        "trajectory_minimum_joint_limit_margin_rad": min(
            item["minimum_soft_joint_limit_margin_rad"] for item in all_authority
        ),
        "trajectory_maximum_joint_target_error_rad": max(
            item["maximum_joint_target_error_rad"] for item in all_authority
        ),
        "at_push_5p6_s": sample(trace, 5.6, new["step_dt"]),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol-json", type=Path, required=True)
    parser.add_argument("--diagnostic-script", type=Path, required=True)
    parser.add_argument("--old-5201", type=Path, required=True)
    parser.add_argument("--new-5201", type=Path, required=True)
    parser.add_argument("--old-5124", type=Path, required=True)
    parser.add_argument("--new-5124", type=Path, required=True)
    parser.add_argument("--quality-json", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error("Output already exists")
    protocol = json.loads(args.protocol_json.read_text(encoding="utf-8"))
    if protocol["seeds"] != [5201, 5124] or sha256(args.diagnostic_script) != protocol["control"]["diagnostic_sha256"]:
        raise ValueError("Protocol seed list or diagnostic source differs")
    cases = [
        inspect(args.old_5201, args.new_5201, 5201, protocol),
        inspect(args.old_5124, args.new_5124, 5124, protocol),
    ]
    quality = json.loads(args.quality_json.read_text(encoding="utf-8"))
    qualified = {item["seed"]: item for item in quality["results"]}
    if (set(qualified) != {5201, 5124}
            or any(not qualified[case["seed"]]["sensor_qualified"]
                   or qualified[case["seed"]]["input_sha256"] != case["new_report_sha256"]
                   for case in cases)):
        raise ValueError("PUSH sensor qualification failed")
    result = {
        "schema_version": 1,
        "analysis_sha256": sha256(Path(__file__)),
        "protocol_sha256": sha256(args.protocol_json),
        "diagnostic_sha256": sha256(args.diagnostic_script),
        "quality_json_sha256": sha256(args.quality_json),
        "scope": "Known-state read-only local kinematic authority; no dynamic support or feedback efficacy claim",
        "cases": cases,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x", encoding="utf-8") as destination:
        json.dump(result, destination, indent=2, allow_nan=False)


if __name__ == "__main__":
    main()
