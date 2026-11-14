"""Summarize Isaac PUSH support traces with a descriptive foot-body geometry proxy."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.spatial import ConvexHull, QhullError


SAMPLE_TIMES_S = (6.0, 6.6, 7.0, 7.4)
SUPPORT_FORCE_N = 2.0
SUSTAINED_STEPS = 10


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def signed_margin(points, center):
    points = np.asarray(points, dtype=float)
    center = np.asarray(center, dtype=float)[:2]
    if len(points) < 3:
        return None
    try:
        vertices = points[ConvexHull(points).vertices]
    except QhullError:
        return None
    edges = np.roll(vertices, -1, axis=0) - vertices
    signed_area = np.sum(vertices[:, 0] * np.roll(vertices[:, 1], -1)
                         - vertices[:, 1] * np.roll(vertices[:, 0], -1))
    if signed_area < 0:
        vertices = vertices[::-1]
        edges = np.roll(vertices, -1, axis=0) - vertices
    offsets = center - vertices
    distances = (edges[:, 0] * offsets[:, 1] - edges[:, 1] * offsets[:, 0]) / np.linalg.norm(edges, axis=1)
    return float(distances.min())


def foot_body_margin_proxy(record):
    forces = np.asarray(record["foot_normal_forces_n"], dtype=float)
    points = np.asarray(record["foot_body_pos"], dtype=float)[forces > SUPPORT_FORCE_N, :2]
    return signed_margin(points, record["robot_com_pos"])


def contact_mean_margin_proxy(record, foot_names):
    points = []
    for name in foot_names:
        contact = record["ground_contacts"][name]
        if contact["ground_normal_force"][2] > SUPPORT_FORCE_N:
            point = contact["ground_contact_pos"]
            if point is None or not np.isfinite(point).all():
                return None
            points.append(point[:2])
    return signed_margin(points, record["robot_com_pos"])


def first_sustained_loss(trace):
    run = 0
    for record in trace:
        if record["push_elapsed_s"] < 5.0:
            continue
        run = run + 1 if record["supported_feet_gt_2n"] < 4 else 0
        if run == SUSTAINED_STEPS:
            return round(record["push_elapsed_s"] - (SUSTAINED_STEPS - 1) * 0.02, 2)
    return None


def describe(path):
    with path.open(encoding="utf-8") as source:
        report = json.load(source)
    trace = report["support_trace"]
    step_dt = report["step_dt"]
    if (report["schema_version"] not in (9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20) or not report["record_push_support_trace"]
            or len(trace) != report["push_executed_steps"] or len(report["support_foot_body_names"]) != 4
            or abs(step_dt - 0.02) > 1e-9):
        raise ValueError(f"Unexpected support trace layout: {path}")
    has_contact = report.get("record_push_contact_load_trace", False)
    if has_contact and report["schema_version"] not in (10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20):
        raise ValueError(f"Contact trace requires schema 10 through 20: {path}")
    for index, record in enumerate(trace):
        if (abs(record["push_elapsed_s"] - (index + 1) * step_dt) > 1e-8
                or len(record["foot_normal_forces_n"]) != 4 or len(record["foot_body_pos"]) != 4):
            raise ValueError(f"Invalid sample {index} in {path}")
    margins = [foot_body_margin_proxy(record) for record in trace]
    contact_margins = ([contact_mean_margin_proxy(record, report["support_foot_body_names"])
                        for record in trace] if has_contact else None)
    snapshots = []
    for seconds in SAMPLE_TIMES_S:
        index = round(seconds / step_dt) - 1
        if index >= len(trace):
            continue
        record = trace[index]
        snapshot = {
            "time_s": seconds,
            "arm_approach_index": record["arm_approach_index"],
            "supported_feet_gt_2n": record["supported_feet_gt_2n"],
            "foot_normal_forces_n": record["foot_normal_forces_n"],
            "robot_com_xy_m": record["robot_com_pos"][:2],
            "base_height_m": record["base_pos"][2],
            "foot_body_margin_proxy_m": margins[index],
        }
        if has_contact:
            snapshot["contact_mean_margin_proxy_m"] = contact_margins[index]
        snapshots.append(snapshot)
    approach_margins = [margin for record, margin in zip(trace, margins)
                        if 5.0 <= record["push_elapsed_s"] <= 7.4 and margin is not None]
    result = {
        "input_path": str(path),
        "input_sha256": sha256(path),
        "seed": report["seed"],
        "hold_push_arm_at_handoff": report["hold_push_arm_at_handoff"],
        "outcome": report["outcome"],
        "push_elapsed_s": report["push_elapsed_s"],
        "terminal_reasons": report["terminal"].get("reasons"),
        "sample_count": len(trace),
        "foot_names": report["support_foot_body_names"],
        "robot_mass_kg": sum(report["robot_body_mass_kg"]),
        "first_sustained_below_four_feet_after_5s": first_sustained_loss(trace),
        "minimum_foot_body_margin_proxy_5_to_7p4_m": min(approach_margins) if approach_margins else None,
        "snapshots": snapshots,
    }
    if has_contact:
        contact_approach_margins = [margin for record, margin in zip(trace, contact_margins)
                                    if 5.0 <= record["push_elapsed_s"] <= 7.4 and margin is not None]
        result["minimum_contact_mean_margin_proxy_5_to_7p4_m"] = (
            min(contact_approach_margins) if contact_approach_margins else None
        )
        result["contact_sensor_quality"] = {}
        for index, name in enumerate(report["support_foot_body_names"]):
            loaded = [record["ground_contacts"][name] for record in trace
                      if record["ground_contacts"][name]["ground_normal_force"][2] > SUPPORT_FORCE_N]
            finite = sum(bool(contact["ground_contact_pos"] is not None
                              and np.isfinite(contact["ground_contact_pos"]).all()) for contact in loaded)
            max_force_error = max(abs(record["ground_contacts"][name]["ground_normal_force"][2]
                                      - record["foot_normal_forces_n"][index]) for record in trace)
            result["contact_sensor_quality"][name] = {
                "loaded_samples": len(loaded),
                "finite_contact_points_when_loaded": finite,
                "max_abs_ground_vs_net_normal_force_error_n": max_force_error,
                "qualified": bool(loaded and finite / len(loaded) >= 0.95 and max_force_error < 1e-3),
            }
        torque_differences = [
            max(abs(computed - applied) for computed, applied in
                zip(record["computed_torque"], record["applied_torque"]))
            for record in trace
        ]
        result["torque_clipping"] = {
            "samples_with_difference_gt_1e-5_nm": sum(value > 1e-5 for value in torque_differences),
            "first_difference_time_s": next((record["push_elapsed_s"] for record, value in
                                             zip(trace, torque_differences) if value > 1e-5), None),
            "max_computed_vs_applied_difference_nm": max(torque_differences),
        }
        result["finite_joint_telemetry"] = all(
            len(record[key]) == 18 and bool(np.isfinite(record[key]).all())
            for record in trace for key in ("joint_pos_target", "computed_torque", "applied_torque")
        )
        result["sensor_qualified"] = (result["finite_joint_telemetry"]
                                      and all(item["qualified"] for item in result["contact_sensor_quality"].values()))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trace-json", type=Path, nargs="+", required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if args.output_json.exists() or len(set(args.trace_json)) != len(args.trace_json):
        parser.error("Require distinct traces and a new output path")
    summaries = [describe(path) for path in args.trace_json]
    result = {
        "schema_version": 1,
        "scope": "Descriptive robot COM projection against supporting foot-body centers or mean ground-contact positions; neither is a contact patch, dynamic stability test or reachability certificate",
        "analysis_sha256": sha256(Path(__file__)),
        "support_force_threshold_n": SUPPORT_FORCE_N,
        "sustained_loss_steps": SUSTAINED_STEPS,
        "results": summaries,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x", encoding="utf-8") as destination:
        json.dump(result, destination, indent=2, allow_nan=False)
    print(json.dumps(summaries, indent=2))


if __name__ == "__main__":
    main()
