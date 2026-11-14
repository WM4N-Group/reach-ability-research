"""Audit the env3 contact failure against frozen baseline and shortcut replays."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ENV = 3


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def read_case(source_plan_path: Path, source_report_path: Path, replay_plan_path: Path,
              replay_report_path: Path, exit_path: Path) -> tuple[dict, list[dict]]:
    source_plan = json.loads(source_plan_path.read_text())
    source_report = json.loads(source_report_path.read_text())
    replay_plan = json.loads(replay_plan_path.read_text())
    replay_report = json.loads(replay_report_path.read_text())
    status = json.loads(exit_path.read_text())
    require(status["returncode"] == 0 and status["report_exists"]
            and status["report_sha256"] == digest(replay_report_path), "Replay output is incomplete")
    require(replay_plan["source_plan_sha256"] == digest(source_plan_path)
            and replay_plan["inspect_env_index"] == replay_report["inspect_env_index"] == ENV
            and replay_plan["source_inspect_env_index"] == source_report["inspect_env_index"] == 2,
            "Replay source or inspected environment differs")
    command = source_plan["command"].copy()
    command[command.index("--inspect-env-index") + 1] = str(ENV)
    command[command.index("--output-json") + 1] = replay_plan["command"][
        replay_plan["command"].index("--output-json") + 1]
    require(command == replay_plan["command"], "Replay changed another evaluator argument")
    require(replay_report["terminal_states"] == source_report["terminal_states"]
            and replay_report["termination_reasons"] == source_report["termination_reasons"]
            and replay_report["completed_episodes"] == source_report["completed_episodes"] == 8
            and replay_report["incomplete_episodes"] == source_report["incomplete_episodes"] == 0,
            "Replay does not reproduce the original terminal states")
    for key in ("seed", "num_envs", "episodes_per_env", "episode_length_s", "actual_physics",
                "checkpoint_sha256", "evaluation_sha256", "control_sha256"):
        require(replay_report[key] == source_report[key], f"Replay provenance differs: {key}")
    require(source_report["checkpoint_sha256"] == source_plan["checkpoint_sha256"]
            and source_report["evaluation_sha256"] == source_plan["evaluator_sha256"],
            "Source report does not match its frozen plan")
    terminal = next(row for row in replay_report["terminal_states"] if row["env_id"] == ENV)
    frames = replay_report[f"trace_env{ENV}"]
    dt = replay_report["failure_history_step_dt"]
    require(len(frames) == round(terminal["elapsed_seconds"] / dt)
            and all(frame["step"] == i and frame["env_id"] == ENV
                    for i, frame in enumerate(frames)), "Env3 trace is incomplete")
    require(replay_report["failure_history_sample_phase"].startswith("pre_env_step"),
            "Unknown trace timestamp convention")
    return replay_report, frames


def sample(frame: dict, dt: float) -> dict:
    return {
        "time_s": round(frame["step"] * dt, 2),
        "box_x_m": frame["box_position"][0],
        "box_y_m": frame["box_position"][1],
        "robot_y_m": frame["robot_position"][1],
        "hand_z_m": frame["hand_position"][2],
        "hand_target_error_y_m": frame["hand_target_error"][1],
        "hand_target_error_z_m": frame["hand_target_error"][2],
        "geometry_clearance_m": frame["geometry_clearance"],
        "legal_hand_contact": frame["hand_contact"],
    }


def summarize(report: dict, frames: list[dict]) -> dict:
    terminal = next(row for row in report["terminal_states"] if row["env_id"] == ENV)
    dt = report["failure_history_step_dt"]
    start_x = frames[0]["box_position"][0]
    def first(predicate) -> dict | None:
        frame = next((frame for frame in frames if predicate(frame)), None)
        return sample(frame, dt) if frame is not None else None
    tail = frames[max(0, len(frames) - 150):]
    return {
        "terminal_s": terminal["elapsed_seconds"],
        "terminal_flags": [name for name, flag in zip(report["termination_flag_names"],
                                                       terminal["termination_flags"]) if flag],
        "terminal_box_displacement_x_m": terminal["box_displacement"][0],
        "trace_steps": len(frames),
        "safe_approach_complete": first(lambda f: f["safe_approach_complete"]),
        "first_legal_contact": first(lambda f: f["hand_contact"]),
        "box_400mm": first(lambda f: f["box_position"][0] - start_x >= 0.4),
        "box_450mm": first(lambda f: f["box_position"][0] - start_x >= 0.45),
        "last_pre_step_sample": sample(frames[-1], dt),
        "last_150_steps": {
            "legal_contact_steps": sum(f["hand_contact"] for f in tail),
            "minimum_geometry_clearance_m": min(f["geometry_clearance"] for f in tail),
            "minimum_hand_z_m": min(f["hand_position"][2] for f in tail),
            "maximum_abs_hand_target_error_y_m": max(abs(f["hand_target_error"][1]) for f in tail),
            "support_below_three_steps": sum(sum(force > 2.0 for force in f["foot_contact_force_z"]) < 3
                                             for f in tail),
            "joint2_saturated_steps": sum(f["arm_torque_limit_ratio"][1] >= 0.999 for f in tail),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for label in ("baseline", "candidate"):
        for name in ("source_plan", "source_report", "replay_plan", "replay_report", "exit_status"):
            parser.add_argument(f"--{label}-{name.replace('_', '-')}", type=Path, required=True)
    args = parser.parse_args()
    result = {}
    reports = {}
    for label in ("baseline", "candidate"):
        paths = {name: getattr(args, f"{label}_{name}") for name in
                 ("source_plan", "source_report", "replay_plan", "replay_report", "exit_status")}
        report, frames = read_case(*(paths[name] for name in
                                     ("source_plan", "source_report", "replay_plan", "replay_report", "exit_status")))
        reports[label] = report
        result[label] = {
            "source_report_sha256": digest(paths["source_report"]),
            "replay_plan_sha256": digest(paths["replay_plan"]),
            "replay_report_sha256": digest(paths["replay_report"]),
            "exit_status_sha256": digest(paths["exit_status"]),
            **summarize(report, frames),
        }
    require(all(reports["baseline"][key] == reports["candidate"][key] for key in
                ("seed", "num_envs", "episodes_per_env", "episode_length_s", "actual_physics",
                 "checkpoint_sha256", "evaluation_sha256", "control_sha256")),
            "Pair policy, physics, control, or cohort differs")
    print(json.dumps({"scope": "Seen env3 contact diagnostic; not a causal safety threshold",
                      "sample_phase": reports["baseline"]["failure_history_sample_phase"],
                      **result}, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
