"""Compare frozen push traces at equal box progress, without fitting a safety gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path


PROGRESS_M = (0.2, 0.3, 0.4, 0.45)
TIP_RADIUS_M = 0.07  # Frozen tracking task uses the box_push.py default.


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def trace(report: dict, env: int) -> tuple[list[dict], dict]:
    terminal = [row for row in report["terminal_states"] if row["env_id"] == env]
    require(len(terminal) == 1 and terminal[0]["episode"] == 1, "Missing unique terminal")
    frames = report[f"trace_env{env}"]
    dt = report["failure_history_step_dt"]
    require(report["inspect_env_index"] == env and frames
            and len(frames) == round(terminal[0]["elapsed_seconds"] / dt)
            and all(frame["env_id"] == env and frame["step"] == i
                    for i, frame in enumerate(frames)), "Incomplete inspected trace")
    require(report["failure_history_sample_phase"].startswith("pre_env_step"),
            "Unknown sample phase")
    return frames, terminal[0]


def tip_margin(frame: dict) -> float | None:
    contact = frame.get("hand_contact_position")
    hand = frame.get("hand_position")
    if (not frame.get("hand_contact_position_valid") or contact is None
            or hand is None or not all(math.isfinite(x) for x in (*contact, *hand))):
        return None
    return TIP_RADIUS_M - math.dist(contact, hand)


def minimum_legal_tip_margin(frames: list[dict]) -> float | None:
    margins = [tip_margin(f) for f in frames if f["hand_contact"]]
    require(all(m is not None for m in margins), "Legal contact lacks finite position")
    return min(margins) if margins else None


def milestone(frames: list[dict], progress: float, dt: float) -> dict | None:
    start_x = frames[0]["box_position"][0]
    frame = next((f for f in frames if f["box_position"][0] - start_x >= progress), None)
    if frame is None:
        return None
    require(len(frame["arm_torque_limit_ratio"]) == 6, "Missing torque telemetry")
    return {
        "time_s": round(frame["step"] * dt, 2),
        "box_displacement_x_m": frame["box_position"][0] - start_x,
        "hand_height_m": frame["hand_position"][2],
        "hand_target_error_y_m": frame["hand_target_error"][1],
        "hand_target_error_z_m": frame["hand_target_error"][2],
        "joint2_torque_limit_ratio": frame["arm_torque_limit_ratio"][1],
        "legal_hand_contact": frame["hand_contact"],
        "tip_margin_m": tip_margin(frame),
    }


def audit(baseline_path: Path, candidate_path: Path, env: int, label: str) -> dict:
    base, cand = (json.loads(path.read_text()) for path in (baseline_path, candidate_path))
    for key in ("seed", "num_envs", "episodes_per_env", "episode_length_s", "actual_physics",
                "checkpoint_sha256", "evaluation_sha256", "control_sha256",
                "failure_history_step_dt", "failure_history_sample_phase"):
        require(base[key] == cand[key], f"Frozen cohort or control differs: {key}")
    require(base["num_envs"] == 8 and base["episodes_per_env"] == 1
            and base["episode_length_s"] == 24.0, "Unexpected paired diagnostic")
    bf, bt = trace(base, env)
    cf, ct = trace(cand, env)
    require(base["termination_flag_names"] == cand["termination_flag_names"],
            "Termination definitions differ")
    names = base["termination_flag_names"]
    def flags(row: dict) -> list[str]:
        return [name for name, value in zip(names, row["termination_flags"]) if value]
    rows = []
    for progress in PROGRESS_M:
        b = milestone(bf, progress, base["failure_history_step_dt"])
        c = milestone(cf, progress, cand["failure_history_step_dt"])
        rows.append({
            "target_progress_m": progress, "baseline": b, "candidate": c,
            "candidate_minus_baseline_hand_height_m": (
                None if b is None or c is None else c["hand_height_m"] - b["hand_height_m"]),
            "candidate_minus_baseline_time_s": (
                None if b is None or c is None else c["time_s"] - b["time_s"]),
        })
    return {
        "scope": "Seen-seed equal-progress descriptive comparison; no independent calibration, gate, or causal attribution",
        "candidate_label": label, "env_id": env,
        "baseline_report_sha256": sha256(baseline_path),
        "candidate_report_sha256": sha256(candidate_path),
        "baseline_terminal": flags(bt), "candidate_terminal": flags(ct),
        "baseline_terminal_time_s": bt["elapsed_seconds"],
        "candidate_terminal_time_s": ct["elapsed_seconds"],
        "tip_radius_m": TIP_RADIUS_M,
        "baseline_minimum_legal_tip_margin_m": minimum_legal_tip_margin(bf),
        "candidate_minimum_legal_tip_margin_m": minimum_legal_tip_margin(cf),
        "baseline_last_pre_step_tip_margin_m": tip_margin(bf[-1]),
        "candidate_last_pre_step_tip_margin_m": tip_margin(cf[-1]),
        "baseline_terminal_tip_margin_m": tip_margin(bt),
        "candidate_terminal_tip_margin_m": tip_margin(ct),
        "baseline_terminal_hand_contact_valid": bt["hand_contact_valid"],
        "candidate_terminal_hand_contact_valid": ct["hand_contact_valid"],
        "milestones": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-report", type=Path, required=True)
    parser.add_argument("--candidate-report", type=Path, required=True)
    parser.add_argument("--env", type=int, required=True)
    parser.add_argument("--candidate-label", required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args.baseline_report, args.candidate_report,
                           args.env, args.candidate_label), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
