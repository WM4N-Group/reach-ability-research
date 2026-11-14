"""Audit a contact-phase progress budget on an inspected Isaac control-step trace."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-json", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--env", type=int, required=True)
    parser.add_argument("--window-steps", type=int, default=20)
    parser.add_argument("--persistence-steps", type=int, default=20)
    parser.add_argument("--minimum-base-advance-m", type=float, default=0.02)
    parser.add_argument("--maximum-gap-residual-m", type=float, default=0.01)
    parser.add_argument("--stop-distance-m", type=float, default=0.11)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error(f"Refusing to overwrite {args.output_json}")
    if args.window_steps < 1 or args.persistence_steps < 1:
        parser.error("Window and persistence must be positive")
    if not (0 < args.minimum_base_advance_m < 1 and 0 < args.maximum_gap_residual_m < 1
            and 0 < args.stop_distance_m < 0.6):
        parser.error("Invalid progress-budget thresholds")

    report = json.loads(args.input_json.read_text())
    if report.get("inspect_env_index") != args.env:
        raise ValueError("Requested environment was not inspected")
    trace = report.get(f"trace_env{args.env}")
    if not trace or [row["step"] for row in trace] != list(range(len(trace))):
        raise ValueError("Expected a complete, consecutive control-step trace")
    if report.get("task") != "GO2-PIPER-Box-Push-Tracking-Play":
        raise ValueError("Expected ordinary GO2-PIPER PUSH")
    push_distance = float(report["actual_physics"]["push_distance"])
    if not math.isfinite(push_distance) or args.stop_distance_m >= push_distance:
        raise ValueError("Stop distance must be below the task push distance")
    dt = float(report["failure_history_step_dt"])
    if not math.isfinite(dt) or dt <= 0:
        raise ValueError("Invalid control-step duration")
    goal_threshold_x = float(trace[0]["box_position"][0]) + push_distance - args.stop_distance_m
    first_contact = next((i for i, row in enumerate(trace) if row["hand_contact"]), None)
    terminal = next((row for row in report["terminal_states"] if row["env_id"] == args.env), None)
    if first_contact is None or terminal is None:
        raise ValueError("Missing inspected hand contact or terminal state")
    outcome = dict(zip(report["termination_flag_names"], terminal["termination_flags"], strict=True))

    records = []
    streak = 0
    max_streak = 0
    first_persistent = None
    for index in range(first_contact + args.window_steps, len(trace)):
        now, before = trace[index], trace[index - args.window_steps]
        if not all(row["hand_contact"] for row in trace[index - args.window_steps:index + 1]):
            streak = 0
            continue
        base_advance = float(now["robot_position"][0] - before["robot_position"][0])
        box_advance = float(now["box_position"][0] - before["box_position"][0])
        gap_delta = float(now["face_local"][0] - before["face_local"][0])
        gap_residual = gap_delta - (box_advance - base_advance)
        remaining = max(0.0, goal_threshold_x - float(now["box_position"][0]))
        slack = float(now["face_local"][0]) - 0.43
        if (base_advance < args.minimum_base_advance_m or abs(gap_residual) > args.maximum_gap_residual_m
                or remaining <= 0 or slack <= 0):
            streak = 0
            continue
        required_efficiency = remaining / (remaining + slack)
        measured_efficiency = box_advance / base_advance
        warning = measured_efficiency < required_efficiency
        streak = streak + 1 if warning else 0
        max_streak = max(max_streak, streak)
        row = {
            "step": index,
            "time_s": index * dt,
            "remaining_to_control_stop_m": remaining,
            "stop_headroom_m": slack,
            "base_advance_window_m": base_advance,
            "box_advance_window_m": box_advance,
            "gap_identity_residual_m": gap_residual,
            "measured_progress_ratio": measured_efficiency,
            "required_progress_ratio": required_efficiency,
            "warning": warning,
            "warning_streak_steps": streak,
        }
        records.append(row)
        if first_persistent is None and streak >= args.persistence_steps:
            first_persistent = row

    first_stop = next((row["step"] for row in trace[first_contact:]
                       if row["hand_contact"] and row["face_local"][0] <= 0.43
                       and row["velocity_command"][0] <= 0), None)
    output = {
        "schema_version": 1,
        "scope": "Retrospective shadow audit of a constant progress-ratio budget; no control action, dynamic counterfactual or safety certificate",
        "source_report": str(args.input_json.resolve()),
        "source_report_sha256": sha256(args.input_json),
        "script_sha256": sha256(Path(__file__)),
        "env": args.env,
        "terminal_flags": outcome,
        "protocol": {
            "window_steps": args.window_steps,
            "persistence_steps": args.persistence_steps,
            "minimum_base_advance_m": args.minimum_base_advance_m,
            "maximum_gap_identity_residual_m": args.maximum_gap_residual_m,
            "stop_distance_m": args.stop_distance_m,
            "controller_minimum_face_gap_m": 0.43,
            "control_step_dt_s": dt,
            "formula": "For face_gap > 0.43 m, required_ratio = remaining_to_control_stop / (remaining_to_control_stop + face_gap - 0.43); measured_ratio = window_box_advance / window_base_advance",
        },
        "first_hand_contact_step": first_contact,
        "first_controller_stop_step": first_stop,
        "first_persistent_warning": first_persistent,
        "max_warning_streak_steps": max_streak,
        "valid_window_count": len(records),
        "warning_window_count": sum(row["warning"] for row in records),
        "records": records,
        "limitations": "Assumes the recent box/base progress ratio remains constant to the control stop target. The budget is undefined at or inside the 0.43 m stop line. World-X displacement approximates the controller face-gap change; windows with over 1 cm identity residual are excluded. Success may follow a temporary low-ratio interval, so warnings do not prove impossibility.",
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x") as destination:
        json.dump(output, destination, indent=2, allow_nan=False)
        destination.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
