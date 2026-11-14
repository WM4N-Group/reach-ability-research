"""Extract time-aligned dynamic support features from frozen Isaac NAV/PUSH traces."""

import argparse
import json
import math
from pathlib import Path

from analyze_piper_isaac_support_dynamics import contact_mean_margin_proxy, sha256


WINDOWS_S = (0.2, 0.5)
SUPPORT_FORCE_N = 2.0
LEG_SUFFIXES = ("_hip_joint", "_thigh_joint", "_calf_joint")


def outcome_category(report):
    if report["outcome"] == "push_terminated":
        return "box_settled" if report["terminal"]["reasons"]["box_settled"] else "push_safety_termination"
    return report["outcome"]


def trailing_rate(values, index, steps, dt):
    if index < steps or values[index] is None or values[index - steps] is None:
        return None
    return (values[index] - values[index - steps]) / (steps * dt)


def extract(path, protocol=None):
    with path.open(encoding="utf-8") as source:
        report = json.load(source)
    if protocol:
        conditions = protocol["conditions"]
        expected = {
            "nav_start_x_m": conditions["nav_start_x_m"],
            "nav_arm_home": conditions["nav_arm_home"],
            "nav_min_translation_speed_m_s": conditions["nav_min_translation_speed_m_s"],
            "nav_timeout_s": conditions["nav_timeout_s"],
            "push_budget_s": conditions["push_budget_s"],
            "record_push_support_trace": conditions["record_push_support_trace"],
            "record_push_contact_load_trace": conditions["record_push_contact_load_trace"],
            "ground_filter_prim": conditions["ground_filter_prim"],
            "support_margin_pause_m": conditions["support_margin_pause_m"],
            "support_margin_resume_m": conditions["support_margin_resume_m"],
            "nav_actor_sha256": protocol["nav_actor_sha256"],
            "push_checkpoint_sha256": protocol["push_checkpoint_sha256"],
        }
        if (any(report.get(key) != value for key, value in expected.items())
                or report["nav_goal_xyyaw"] != [conditions["nav_goal_x_m"], 0.0, 0.0]
                or report["skip_nav"]):
            raise ValueError(f"Report differs from frozen protocol: {path}")
    if (report["schema_version"] != 10 or not report["record_push_support_trace"]
            or not report["record_push_contact_load_trace"] or report["support_margin_pause_m"] != 0
            or report["support_margin_resume_m"] != 0 or report["hold_push_arm_at_handoff"]
            or report["pre_ready_leg_action_cap"] != 0
            or report.get("safe_approach_arm_rate_scale", 1.0) != 1.0
            or report.get("handoff_settle_stable_s", 0.0) != 0.0):
        raise ValueError(f"Not an unmodified contact-trace baseline: {path}")
    dt = report["step_dt"]
    if abs(dt - 0.02) > 1e-9 or len(report["support_trace"]) != report["push_executed_steps"]:
        raise ValueError(f"Unexpected sample period or count: {path}")
    if report["support_trace"] and abs(report["support_trace"][-1]["push_elapsed_s"]
                                       - report["push_elapsed_s"]) > 1e-8:
        raise ValueError(f"PUSH duration differs from last sample: {path}")
    leg_ids = [index for index, name in enumerate(report["joint_names"]) if name.endswith(LEG_SUFFIXES)]
    if len(leg_ids) != 12 or len(report["support_foot_body_names"]) != 4:
        raise ValueError(f"Unexpected leg or foot layout: {path}")
    trace = report["support_trace"]
    foot_names = report["support_foot_body_names"]
    margins = []
    centers = []
    for index, record in enumerate(trace):
        if abs(record["push_elapsed_s"] - (index + 1) * dt) > 1e-8:
            raise ValueError(f"Misaligned PUSH sample {index}: {path}")
        if (len(record["foot_normal_forces_n"]) != 4
                or not all(math.isfinite(force) and force >= 0 for force in record["foot_normal_forces_n"])
                or record["supported_feet_gt_2n"] != sum(
                    force > SUPPORT_FORCE_N for force in record["foot_normal_forces_n"])
                or len(record["robot_com_pos"]) != 3
                or not all(map(math.isfinite, record["robot_com_pos"]))):
            raise ValueError(f"Invalid support state at sample {index}: {path}")
        for foot_index, name in enumerate(foot_names):
            contact = record["ground_contacts"][name]
            force = contact["ground_normal_force"][2]
            if not math.isfinite(force) or abs(force - record["foot_normal_forces_n"][foot_index]) > 1e-3:
                raise ValueError(f"Ground/net force mismatch at sample {index}: {path}")
            if force > SUPPORT_FORCE_N and (contact["ground_contact_pos"] is None
                                            or not all(map(math.isfinite, contact["ground_contact_pos"]))):
                raise ValueError(f"Missing loaded contact at sample {index}: {path}")
        for key in ("joint_pos", "joint_pos_target", "computed_torque", "applied_torque"):
            if len(record[key]) != 18 or not all(map(math.isfinite, record[key])):
                raise ValueError(f"Invalid joint telemetry at sample {index}: {path}")
        margins.append(contact_mean_margin_proxy(record, foot_names))
        centers.append(record["robot_com_pos"][:2])
    features = []
    for index, record in enumerate(trace):
        sample = {
            "push_elapsed_s": record["push_elapsed_s"],
            "arm_approach_index": record["arm_approach_index"],
            "motion_ready": record["motion_ready"],
            "remaining_push_s": max(0.0, report["push_budget_s"] - record["push_elapsed_s"]),
            "contact_mean_margin_m": margins[index],
            "supported_feet_gt_2n": record["supported_feet_gt_2n"],
            "foot_normal_forces_n": dict(zip(foot_names, record["foot_normal_forces_n"])),
            "minimum_foot_normal_force_n": min(record["foot_normal_forces_n"]),
            "max_leg_target_error_rad": max(abs(record["joint_pos_target"][joint] - record["joint_pos"][joint])
                                            for joint in leg_ids),
        }
        for window_s in WINDOWS_S:
            steps = round(window_s / dt)
            key = str(window_s).replace(".", "p")
            sample[f"margin_rate_{key}_m_s"] = trailing_rate(margins, index, steps, dt)
            sample[f"com_speed_{key}_m_s"] = (
                math.dist(centers[index], centers[index - steps]) / (steps * dt)
                if index >= steps else None
            )
            for axis, coordinate in (("x", 0), ("y", 1)):
                sample[f"com_velocity_{axis}_{key}_m_s"] = (
                    (centers[index][coordinate] - centers[index - steps][coordinate]) / (steps * dt)
                    if index >= steps else None
                )
        features.append(sample)
    return {
        "input_path": str(path),
        "input_sha256": sha256(path),
        "seed": report["seed"],
        "outcome": outcome_category(report),
        "push_elapsed_s": report["push_elapsed_s"],
        "terminal_reasons": report["terminal"].get("reasons"),
        "nav_actor_sha256": report["nav_actor_sha256"],
        "push_checkpoint_sha256": report["push_checkpoint_sha256"],
        "control_sha256": report["control_sha256"],
        "feature_count": len(features),
        "features": features,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trace-json", type=Path, nargs="+", required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--protocol-json", type=Path)
    args = parser.parse_args()
    if args.output_json.exists() or len(set(args.trace_json)) != len(args.trace_json):
        parser.error("Require distinct input paths and a new output path")
    protocol = None
    if args.protocol_json:
        with args.protocol_json.open(encoding="utf-8") as source:
            protocol = json.load(source)
        diagnostic = Path(__file__).with_name("diagnose_piper_nav_push_handoff.py")
        if sha256(diagnostic) != protocol["script_sha256"]:
            raise ValueError("Diagnostic script differs from frozen protocol")
    results = [extract(path, protocol) for path in args.trace_json]
    if len({result["seed"] for result in results}) != len(results):
        raise ValueError("Require one trajectory per seed")
    sources = {(result["nav_actor_sha256"], result["push_checkpoint_sha256"],
                tuple(sorted(result["control_sha256"].items()))) for result in results}
    if len(sources) != 1:
        raise ValueError("Mixed policy or control source hashes")
    if protocol:
        if sorted(result["seed"] for result in results) != sorted(protocol["seeds"]):
            raise ValueError("Input seeds differ from frozen protocol")
    output = {
        "schema_version": 1,
        "analysis_sha256": sha256(Path(__file__)),
        "protocol_sha256": sha256(args.protocol_json) if args.protocol_json else None,
        "source_hashes": {
            "nav_actor_sha256": results[0]["nav_actor_sha256"],
            "push_checkpoint_sha256": results[0]["push_checkpoint_sha256"],
            "control_sha256": results[0]["control_sha256"],
        },
        "geometry": "Signed COM projection margin against the convex hull of loaded foot-ground mean contact positions",
        "support_force_threshold_n": SUPPORT_FORCE_N,
        "trailing_windows_s": list(WINDOWS_S),
        "scope": "Descriptive features only; no learned model, threshold or viability certification",
        "results": results,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x", encoding="utf-8") as destination:
        json.dump(output, destination, indent=2, allow_nan=False)


if __name__ == "__main__":
    main()
