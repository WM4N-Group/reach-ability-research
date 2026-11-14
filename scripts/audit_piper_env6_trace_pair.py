"""Audit frozen env6 trace replays against their original 24 s reports."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def read_case(source_plan_path: Path, source_report_path: Path, replay_plan_path: Path,
              replay_report_path: Path, exit_path: Path) -> tuple[dict, dict]:
    source_plan = json.loads(source_plan_path.read_text())
    source_report = json.loads(source_report_path.read_text())
    replay_plan = json.loads(replay_plan_path.read_text())
    replay_report = json.loads(replay_report_path.read_text())
    status = json.loads(exit_path.read_text())
    require(status["returncode"] == 0 and status["report_exists"]
            and status["report_sha256"] == digest(replay_report_path), "Replay output is incomplete")
    require(replay_plan["source_plan_sha256"] == digest(source_plan_path)
            and replay_plan["inspect_env_index"] == replay_report["inspect_env_index"] == 6
            and replay_plan["source_inspect_env_index"] == source_report["inspect_env_index"] == 2,
            "Replay source or inspected environment differs")
    command = list(source_plan["command"])
    command[command.index("--inspect-env-index") + 1] = "6"
    replay_output = replay_plan["command"][replay_plan["command"].index("--output-json") + 1]
    require(Path(replay_output).name == replay_report_path.name == "report.json",
            "Replay report path differs")
    command[command.index("--output-json") + 1] = replay_output
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
    return replay_plan, replay_report


def event(frames: list[dict], predicate, start_x: float) -> dict | None:
    frame = next((frame for frame in frames if predicate(frame, start_x)), None)
    if frame is None:
        return None
    return {
        "step": frame["step"],
        "time_s": round(frame["step"] * 0.02, 2),
        "robot_y_m": frame["robot_position"][1],
        "box_y_m": frame["box_position"][1],
        "hand_target_error_y_m": frame["hand_target_error"][1],
        "geometry_clearance_m": frame["geometry_clearance"],
    }


def summarize(report: dict) -> dict:
    frames = report["trace_env6"]
    terminal = next(row for row in report["terminal_states"] if row["env_id"] == 6)
    require(len(frames) == round(terminal["elapsed_seconds"] / 0.02)
            and all(frame["step"] == index and frame["env_id"] == 6
                    for index, frame in enumerate(frames)), "Env6 trace is incomplete")
    start_x = frames[0]["box_position"][0]
    milestones = {
        "approach_complete": event(frames, lambda f, _: f["safe_approach_complete"], start_x),
        "first_legal_contact": event(frames, lambda f, _: f["hand_contact"], start_x),
    }
    for millimeters in (100, 200, 300, 400, 500):
        milestones[f"box_{millimeters}mm"] = event(
            frames, lambda f, x, mm=millimeters: f["box_position"][0] - x >= mm / 1000, start_x)
    contact = milestones["first_legal_contact"]
    require(contact is not None, "Expected env6 legal contact")
    window = frames[contact["step"]:contact["step"] + 150]
    require(len(window) == 150 and all(len(f["foot_contact_force_z"]) == 4
                                       and len(f["arm_torque_limit_ratio"]) == 6 for f in window),
            "First 150 contact steps lack support or torque telemetry")
    return {
        "trace_steps": len(frames),
        "terminal_box_displacement_x_m": terminal["box_displacement"][0],
        "milestones": milestones,
        "first_150_steps_after_contact": {
            "box_forward_m": window[-1]["box_position"][0] - window[0]["box_position"][0],
            "box_lateral_m": window[-1]["box_position"][1] - window[0]["box_position"][1],
            "minimum_geometry_clearance_m": min(f["geometry_clearance"] for f in window),
            "legal_contact_steps": sum(f["hand_contact"] for f in window),
            "support_below_three_steps": sum(sum(force > 2.0 for force in f["foot_contact_force_z"]) < 3
                                             for f in window),
            "joint2_saturated_steps": sum(f["arm_torque_limit_ratio"][1] >= 0.999 for f in window),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for label in ("baseline", "candidate"):
        for name in ("source_plan", "source_report", "replay_plan", "replay_report", "exit_status"):
            parser.add_argument(f"--{label}-{name.replace('_', '-')}", type=Path, required=True)
    args = parser.parse_args()
    results = {}
    reports = {}
    for label in ("baseline", "candidate"):
        paths = {name: getattr(args, f"{label}_{name}") for name in
                 ("source_plan", "source_report", "replay_plan", "replay_report", "exit_status")}
        _, report = read_case(*(paths[name] for name in
                                ("source_plan", "source_report", "replay_plan", "replay_report", "exit_status")))
        reports[label] = report
        results[label] = {"source_report_sha256": digest(paths["source_report"]),
                          "replay_plan_sha256": digest(paths["replay_plan"]),
                          "replay_report_sha256": digest(paths["replay_report"]),
                          **summarize(report)}
    require(reports["baseline"]["actual_physics"] == reports["candidate"]["actual_physics"]
            and reports["baseline"]["checkpoint_sha256"] == reports["candidate"]["checkpoint_sha256"]
            and reports["baseline"]["evaluation_sha256"] == reports["candidate"]["evaluation_sha256"]
            and reports["baseline"]["control_sha256"] == reports["candidate"]["control_sha256"]
            and all(reports["baseline"][key] == reports["candidate"][key] for key in
                    ("seed", "num_envs", "episodes_per_env", "episode_length_s")),
            "Pair policy, physics, control, or cohort differs")
    print(json.dumps({"scope": "Seen env6 24 s contact-phase diagnostic; not safety acceptance",
                      "baseline": results["baseline"], "candidate": results["candidate"]},
                     indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
