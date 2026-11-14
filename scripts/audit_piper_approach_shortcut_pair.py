"""Audit an isolated approach-path pilot against its frozen Isaac baseline."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from audit_piper_push_deadline import audit_report


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def normalized_command(command: list[str]) -> list[str]:
    result = command.copy()
    require(result.count("--output-json") == 1, "Missing or duplicate report option")
    result[1] = "<evaluator>"
    result[result.index("--output-json") + 1] = "<report>"
    return result


def terminal_rows(report: dict) -> dict[int, dict]:
    names = report["termination_flag_names"]
    rows = {}
    for state in report["terminal_states"]:
        env = state["env_id"]
        require(env not in rows and 0 <= env < report["num_envs"] and state["episode"] == 1,
                "Duplicate or unexpected terminal episode")
        rows[env] = {
            "termination": [name for name, flag in zip(names, state["termination_flags"]) if flag],
            "elapsed_s": state["elapsed_seconds"],
            "box_displacement_x_m": state["box_displacement"][0],
            "minimum_geometry_clearance_m": state["geometry_minimum_observed"],
            "geometry_observed_steps": state["geometry_observed_steps"],
            "safe_approach_complete": state["safe_approach_complete"],
        }
    return rows


def trace_times(report: dict) -> dict:
    env = report["inspect_env_index"]
    frames = report[f"trace_env{env}"]
    require(frames and all(frame["step"] == i and frame["env_id"] == env
                           for i, frame in enumerate(frames)), "Inspected trace is incomplete")
    require(report["failure_history_sample_phase"].startswith("pre_env_step"),
            "Unknown trace timestamp convention")
    dt = report["failure_history_step_dt"]
    def first_seconds(key: str) -> float | None:
        return next((frame["step"] * dt for frame in frames if frame[key]), None)
    support = [sum(force > 2.0 for force in frame["foot_contact_force_z"])
               for frame in frames if len(frame.get("foot_contact_force_z", [])) == 4]
    return {
        "env_id": env,
        "safe_approach_complete_s": first_seconds("safe_approach_complete"),
        "first_legal_hand_contact_s": first_seconds("hand_contact"),
        "support_observed_steps": len(support),
        "minimum_supported_feet": min(support) if support else None,
        "steps_below_three_supported_feet": sum(count < 3 for count in support) if support else None,
    }


def audit(baseline_plan_path: Path, baseline_report_path: Path,
          pilot_plan_path: Path, pilot_report_path: Path, exit_path: Path) -> dict:
    baseline_plan = json.loads(baseline_plan_path.read_text())
    pilot_plan = json.loads(pilot_plan_path.read_text())
    baseline = json.loads(baseline_report_path.read_text())
    pilot = json.loads(pilot_report_path.read_text())
    status = json.loads(exit_path.read_text())
    require(status["returncode"] == 0 and status["report_exists"]
            and status["report_sha256"] == sha256(pilot_report_path), "Pilot run is incomplete")
    removed = pilot_plan.get("removed_waypoint_indices",
                             [pilot_plan.get("removed_waypoint_index")])
    require(isinstance(removed, list) and removed
            and all(type(index) is int for index in removed)
            and removed == list(range(removed[0], removed[-1] + 1))
            and 1 <= removed[0] <= removed[-1] < 20, "Invalid removed waypoint range")
    require(pilot_plan["source_plan_sha256"] == sha256(baseline_plan_path)
            and pilot_plan["source_approach_sha256"] == baseline_plan["approach_sha256"]
            and pilot_plan["screen_result"]["edge_start_index"] == removed[0] - 1
            and pilot_plan["screen_result"]["edge_end_index"] == removed[-1] + 1
            and pilot_plan["candidate_approach_sha256"] != baseline_plan["approach_sha256"]
            and pilot_plan["screen_result"]["static_pass"], "Path provenance differs")
    require(normalized_command(baseline_plan["command"]) == normalized_command(pilot_plan["command"]),
            "Evaluator arguments differ beyond source and report paths")
    require(baseline_plan["checkpoint_sha256"] == pilot_plan["checkpoint_sha256"]
            and baseline_plan["evaluator_sha256"] == pilot_plan["evaluator_sha256"]
            and baseline_plan["ik_sha256"] == pilot_plan["ik_sha256"]
            and baseline_plan["push_control_sha256"] == pilot_plan["push_control_sha256"]
            and baseline_plan["push_config_sha256"] == pilot_plan["push_config_sha256"],
            "Frozen evaluator, policy, or control differs")
    require(baseline["checkpoint_sha256"] == pilot["checkpoint_sha256"] == pilot_plan["checkpoint_sha256"]
            and baseline["evaluation_sha256"] == pilot["evaluation_sha256"] == pilot_plan["evaluator_sha256"]
            and baseline["control_sha256"] == pilot["control_sha256"]
            and baseline["actual_physics"] == pilot["actual_physics"],
            "Runtime policy, control, or physics differs")
    require(all(baseline[key] == pilot[key] for key in
                ("seed", "num_envs", "episodes_per_env", "episode_length_s", "requested_episodes",
                 "failure_history_step_dt", "inspect_env_index")), "Pair cohort differs")
    require(baseline["requested_episodes"] == 8 and baseline["episodes_per_env"] == 1,
            "Expected the frozen 8-environment pilot")
    for report in (baseline, pilot):
        require(all(len(report[key]) == 8 for key in
                    ("push_contact_steps", "unclassified_hand_contact_steps")),
                "Available per-environment contact telemetry is incomplete")

    baseline_deadline = audit_report(baseline, 12.0)
    pilot_deadline = audit_report(pilot, 12.0)
    base_rows, pilot_rows = terminal_rows(baseline), terminal_rows(pilot)
    per_env = []
    for env in range(8):
        row = {"env_id": env, "baseline": base_rows.get(env), "candidate": pilot_rows.get(env)}
        for label, report in (("baseline", baseline), ("candidate", pilot)):
            row[label + "_legal_contact_steps"] = report["push_contact_steps"][env]
            row[label + "_unclassified_hand_contact_steps"] = report["unclassified_hand_contact_steps"][env]
        per_env.append(row)
    base_trace, pilot_trace = trace_times(baseline), trace_times(pilot)
    return {
        "scope": "Seen-seed 24 s paired path diagnostic; no original 12 s acceptance or contact authorization",
        "baseline_plan_sha256": sha256(baseline_plan_path),
        "baseline_report_sha256": sha256(baseline_report_path),
        "candidate_plan_sha256": sha256(pilot_plan_path),
        "candidate_report_sha256": sha256(pilot_report_path),
        "removed_waypoint_indices": removed,
        "baseline": {
            "completed": baseline["completed_episodes"], "incomplete": baseline["incomplete_episodes"],
            "termination_reasons": baseline["termination_reasons"], "deadline": baseline_deadline,
            "max_torque_limit_ratio": baseline["max_torque_limit_ratio"],
            "inspected_trace": base_trace,
        },
        "candidate": {
            "completed": pilot["completed_episodes"], "incomplete": pilot["incomplete_episodes"],
            "termination_reasons": pilot["termination_reasons"], "deadline": pilot_deadline,
            "max_torque_limit_ratio": pilot["max_torque_limit_ratio"],
            "inspected_trace": pilot_trace,
        },
        "paired_inspected_trace_delta_s": {
            key: None if base_trace[key] is None or pilot_trace[key] is None
            else pilot_trace[key] - base_trace[key]
            for key in ("safe_approach_complete_s", "first_legal_hand_contact_s")
        },
        "observed_goal_by_12_s_delta_in_extended_run": (
            pilot_deadline["observed_goal_by_deadline_in_extended_run"]
            - baseline_deadline["observed_goal_by_deadline_in_extended_run"]
        ),
        "per_env": per_env,
        "telemetry_coverage": {
            "per_env_support": "unavailable in frozen evaluator; inspected trace only",
            "per_env_forbidden_box_contact_steps": "unavailable; terminal contact flags checked",
            "inspected_support_threshold_n": 2.0,
            "inspected_support_phase": baseline["failure_history_sample_phase"],
        },
        "contact_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-plan", type=Path, required=True)
    parser.add_argument("--baseline-report", type=Path, required=True)
    parser.add_argument("--pilot-plan", type=Path, required=True)
    parser.add_argument("--pilot-report", type=Path, required=True)
    parser.add_argument("--exit-status", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args.baseline_plan, args.baseline_report, args.pilot_plan,
                           args.pilot_report, args.exit_status), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
