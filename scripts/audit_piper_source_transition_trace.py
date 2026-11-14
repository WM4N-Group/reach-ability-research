"""Check source-group transition events against their 50 Hz control trace."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def same_vector(left: object, right: object, name: str) -> None:
    if not isinstance(left, list) or not isinstance(right, list) or len(left) != len(right):
        raise ValueError(f"{name}: missing or mismatched vector")
    if not all(type(a) in (int, float) and type(b) in (int, float)
               and math.isfinite(a) and math.isfinite(b)
               and math.isclose(a, b, abs_tol=1e-6, rel_tol=0) for a, b in zip(left, right)):
        raise ValueError(f"{name}: report and control trace differ")


def audit(report_path: Path, trace_path: Path) -> dict:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    dt = report.get("control_dt")
    if type(dt) not in (int, float) or not math.isfinite(dt) or dt <= 0:
        raise ValueError("Invalid control period")
    rows = []
    with trace_path.open(encoding="utf-8") as stream:
        for line in stream:
            rows.append(json.loads(line))
    if not rows or report.get("samples") != len(rows):
        raise ValueError("Control trace count differs from report")
    for index, row in enumerate(rows):
        if row.get("step") != index or not math.isclose(row.get("time_s", -1), index * dt,
                                                       abs_tol=1e-6, rel_tol=0):
            raise ValueError(f"Non-contiguous physical clock at control step {index}")
    events = report.get("events")
    if not isinstance(events, list) or not events or events[0].get("event") != "transition_started":
        raise ValueError("Missing transition start event")
    names = []
    identity = None
    for event in events:
        step = event.get("step")
        if type(step) is not int or not 0 <= step < len(rows):
            raise ValueError("Event references missing control sample")
        if event.get("contract_version") != 1 or not math.isclose(event.get("time_s", -1),
                                                                  rows[step]["time_s"], abs_tol=1e-6,
                                                                  rel_tol=0):
            raise ValueError("Event contract or time differs from trace")
        current_identity = (event.get("source_id"), event.get("object_id"),
                            event.get("source_skill"), event.get("destination_skill"))
        if not all(current_identity) or (identity is not None and current_identity != identity):
            raise ValueError("Event source or object binding changed")
        identity = current_identity
        name = event.get("event")
        names.append(name)
        if name in ("transition_ready", "transition_ready_refreshed"):
            state = event.get("entry_state")
            if not isinstance(state, dict) or state.get("step") != step or not math.isclose(
                    state.get("physical_time_s", -1), rows[step]["time_s"], abs_tol=1e-6, rel_tol=0):
                raise ValueError("READY state was not sampled at event time")
            if (state.get("source_id"), state.get("object_id")) != identity[:2]:
                raise ValueError("READY state source or object differs")
            for field, trace_field in (("joint_position", "q"), ("joint_velocity", "dq"),
                                       ("applied_position_target", "pd_target"),
                                       ("applied_torque", "torque")):
                same_vector(state.get(field), rows[step].get(trace_field), field)
            if (state.get("gates") != rows[step].get("gates")
                    or state.get("history_valid_frames") != rows[step].get("history_valid_frames")
                    or not math.isclose(state.get("stable_seconds", -1),
                                        rows[step].get("stable_seconds", -2), abs_tol=1e-6, rel_tol=0)):
                raise ValueError("READY gate or history differs from trace")
    outcome = report.get("outcome")
    terminal = report.get("terminal")

    def push_started_after_ready() -> bool:
        if names != ["transition_started", "transition_ready"]:
            return False
        ready = events[-1]
        activation = [item for item in report.get("control_events", [])
                      if item.get("event") == "push_activated"]
        return (len(activation) == 1 and activation[0].get("step") == ready["step"]
                and math.isclose(activation[0].get("time_s", -1), ready["time_s"],
                                 abs_tol=1e-6, rel_tol=0)
                and math.isclose(report.get("push_activation_time_s", -1), ready["time_s"],
                                 abs_tol=1e-6, rel_tol=0)
                and ready["step"] < len(rows) - 1
                and rows[ready["step"]].get("push_active") is False
                and all(row.get("push_active") is True for row in rows[ready["step"] + 1:])
                and report.get("physical_resets_after_initial") == 0)

    if outcome == "entry_ready_probe_only":
        if names[-1] != "transition_ready" or terminal != {}:
            raise ValueError("READY probe has unexpected terminal or start event")
    elif outcome == "native_termination_before_entry":
        if names[-1] != "transition_failed" or "transition_ready" in names or not isinstance(terminal, dict):
            raise ValueError("Pre-entry failure has inconsistent events")
        if not any(value is True for key, value in terminal.items() if key != "time_out"):
            raise ValueError("Pre-entry failure lacks native safety termination")
    elif outcome == "entry_timeout":
        if (names != ["transition_started", "transition_failed"]
                or events[-1].get("reason") != "ENTRY_TIMEOUT"
                or not isinstance(terminal, dict) or terminal.get("time_out") is not True
                or any(value is True for key, value in terminal.items() if key != "time_out")
                or report.get("entry_state") is not None):
            raise ValueError("Entry timeout has inconsistent events or terminal outcome")
    elif outcome == "runtime_error":
        pre_entry = names == ["transition_started"] and report.get("entry_state") is None
        post_entry = push_started_after_ready() and isinstance(report.get("entry_state"), dict)
        if not (pre_entry or post_entry) or terminal != {} or not report.get("error") and post_entry:
            raise ValueError("Runtime error has inconsistent entry, activation or terminal outcome")
    elif outcome == "native_termination_during_push":
        state = report.get("entry_state")
        if (not push_started_after_ready()
                or not isinstance(state, dict) or state.get("step") != events[-1]["step"]
                or not math.isclose(state.get("time_s", -1), events[-1]["time_s"],
                                    abs_tol=1e-6, rel_tol=0)
                or not isinstance(terminal, dict)
                or terminal.get("box_settled") is True
                or terminal.get("time_out") is True
                or sum(value is True for key, value in terminal.items()
                       if key not in ("box_settled", "time_out")) != 1):
            raise ValueError("PUSH activation or native failure is inconsistent")
        for field in ("q", "dq", "pd_target", "torque"):
            same_vector(state.get(field), rows[events[-1]["step"]].get(field),
                        f"activation {field}")
    elif outcome in ("nav_to_push_settled_no_exit", "native_termination_during_exit",
                     "push_exit_stable_arm_extended_no_nav"):
        if not push_started_after_ready() or not isinstance(terminal, dict):
            raise ValueError("Continuous PUSH outcome has inconsistent activation or terminal state")
        if outcome == "nav_to_push_settled_no_exit":
            if (terminal.get("box_settled") is not True
                    or any(value is True for key, value in terminal.items() if key != "box_settled")
                    or rows[-1].get("phase") != "push_v212"):
                raise ValueError("Continuous PUSH outcome has inconsistent activation or terminal state")
        elif outcome == "native_termination_during_exit":
            exit_events = [item for item in report.get("control_events", [])
                           if item.get("event") == "native_push_settled_exit_requested"]
            settled = report.get("push_settled_state")
            if (len(exit_events) != 1 or terminal.get("invalid_hand_contact") is not True
                    or any(value is True for key, value in terminal.items()
                           if key != "invalid_hand_contact")
                    or report.get("push_settled_time_s") != exit_events[0].get("time_s")
                    or not isinstance(exit_events[0].get("step"), int)
                    or not events[-1]["step"] < exit_events[0]["step"] < len(rows) - 1
                    or not math.isclose(exit_events[0]["time_s"],
                                        rows[exit_events[0]["step"]]["time_s"],
                                        abs_tol=1e-6, rel_tol=0)
                    or not isinstance(settled, dict)
                    or settled.get("step") != exit_events[0]["step"]
                    or not math.isclose(settled.get("time_s", -1), exit_events[0]["time_s"],
                                        abs_tol=1e-6, rel_tol=0)
                    or rows[exit_events[0]["step"]].get("native_push_settled") is not True
                    or not all(row.get("exit_requested") is True
                               for row in rows[exit_events[0]["step"]:])
                    or rows[-1].get("exit_hold") is not False):
                raise ValueError("Exit safety termination has inconsistent event or trace")
            for field, trace_field in (("q", "q"), ("dq", "dq"),
                                       ("pd_target", "pd_target"), ("torque", "torque")):
                same_vector(settled.get(field), rows[exit_events[0]["step"]].get(trace_field),
                            f"settled {field}")
        else:
            controls = report.get("control_events", [])
            names_after_push = [item.get("event") for item in controls]
            state = report.get("exit_state")
            final = rows[-1]
            if (terminal != {}
                    or names_after_push[-3:] != ["native_push_settled_exit_requested",
                                                  "exit_four_contact_braking_started_not_ready",
                                                  "exit_loaded_hold_requested"]
                    or not isinstance(state, dict) or state.get("step") != final["step"]
                    or not math.isclose(state.get("time_s", -1), final["time_s"],
                                        abs_tol=1e-6, rel_tol=0)
                    or state.get("exit_stable_gates") != final.get("exit_stable_gates")
                    or not isinstance(state.get("exit_stable_gates"), dict)
                    or not all(value is True for value in state["exit_stable_gates"].values())
                    or not math.isclose(state.get("exit_stable_seconds", -1),
                                        final.get("exit_stable_seconds", -2),
                                        abs_tol=1e-6, rel_tol=0)
                    or state["exit_stable_seconds"] < 0.5
                    or state.get("exit_hold") is not True
                    or state.get("exit_brake_hold") is not True
                    or final.get("exit_hold") is not True
                    or final.get("native_push_settled") is not True
                    or report.get("push_settled_time_s") != controls[-3].get("time_s")
                    or final.get("phase") != "exit_loaded_hold_arm_extended"):
                raise ValueError("Stable extended-arm exit has inconsistent state or trace")
            for field in ("q", "dq", "pd_target", "torque"):
                same_vector(state.get(field), final.get(field), f"exit {field}")
    elif outcome == "nav_push_stow_nav_target_stable":
        required = ["push_activated", "native_push_settled_exit_requested",
                    "exit_four_contact_braking_started_not_ready", "exit_loaded_hold_requested",
                    "exit_retraction_started", "return_nav_requested_after_stowed_ready",
                    "return_nav_activated_after_three_real_history_frames",
                    "return_nav_arrival_four_contact_braking"]
        controls = report.get("control_events", [])
        selected = [item for item in controls if item.get("event") in required]
        if (not push_started_after_ready() or terminal != {}
                or [item["event"] for item in selected] != required
                or any(not isinstance(item.get("step"), int)
                       or not events[-1]["step"] <= item["step"] < len(rows)
                       or not math.isclose(item.get("time_s", -1), rows[item["step"]]["time_s"],
                                           abs_tol=1e-6, rel_tol=0)
                       for item in selected)
                or any(a["step"] > b["step"] for a, b in zip(selected, selected[1:]))):
            raise ValueError("Full-chain event sequence or PUSH activation is inconsistent")
        by_name = {item["event"]: item for item in selected}
        snapshots = (("entry_state", "push_activated"),
                     ("push_settled_state", "native_push_settled_exit_requested"),
                     ("exit_loaded_stable_state", "exit_retraction_started"),
                     ("stowed_exit_state", "return_nav_requested_after_stowed_ready"))
        for field, event_name in snapshots:
            step = by_name[event_name]["step"]
            if report.get(field) != rows[step]:
                raise ValueError(f"Full-chain {field} differs from control trace")
        settled = rows[by_name["native_push_settled_exit_requested"]["step"]]
        exit_ready = rows[by_name["exit_retraction_started"]["step"]]
        stowed = rows[by_name["return_nav_requested_after_stowed_ready"]["step"]]
        nav_start = rows[by_name["return_nav_activated_after_three_real_history_frames"]["step"]]
        exit_gates = exit_ready.get("exit_stable_gates")
        if (settled.get("native_push_settled") is not True
                or not isinstance(exit_gates, dict) or not exit_gates
                or not all(value is True for value in exit_gates.values())
                or exit_ready.get("exit_stable_seconds", 0) < 0.5
                or stowed.get("retracted_ready") is not True
                or stowed.get("retracted_ready_seconds", 0) < 0.5
                or nav_start.get("history_valid_frames", 0) < 3):
            raise ValueError("Full-chain settled, exit or NAV entry state is inconsistent")
        final = rows[-1]
        returned = final.get("return_nav")
        gates = final.get("exit_stable_gates")
        feet = final.get("foot_forces")
        if (report.get("return_nav_final_state") != final
                or final.get("phase") != "return_nav_arrival_brake"
                or final.get("native_push_settled") is not True
                or final.get("retracted_ready") is not True
                or final.get("retracted_ready_seconds", 0) < 0.5
                or not isinstance(gates, dict) or not gates
                or not all(value is True for value in gates.values())
                or not isinstance(returned, dict) or returned.get("active") is not False
                or returned.get("arrival_brake") is not True
                or returned.get("goal_error_m", math.inf) >= 0.05
                or returned.get("travel_m", -math.inf) < 0.2
                or final.get("return_nav_stable_seconds", 0) < 0.5
                or not isinstance(feet, list) or len(feet) != 4
                or any(not isinstance(foot, list) or len(foot) != 3
                       or type(foot[2]) not in (int, float)
                       or not math.isfinite(foot[2]) or foot[2] < 2 for foot in feet)
                or by_name["return_nav_activated_after_three_real_history_frames"]["step"]
                   >= by_name["return_nav_arrival_four_contact_braking"]["step"]):
            raise ValueError("Full-chain return state or stable goal is inconsistent")
    else:
        raise ValueError(f"Unsupported source diagnostic outcome: {outcome}")
    if outcome not in ("runtime_error", "native_termination_during_push",
                       "nav_to_push_settled_no_exit", "native_termination_during_exit",
                       "push_exit_stable_arm_extended_no_nav",
                       "nav_push_stow_nav_target_stable") and events[-1]["step"] != rows[-1]["step"]:
        raise ValueError("Final event does not match final control sample")
    return {
        "scope": "Read-only source transition trace audit; no selector benefit inferred",
        "seed": report.get("seed"),
        "outcome": outcome,
        "event_names": names,
        "control_samples": len(rows),
        "final_time_s": rows[-1]["time_s"],
        "ready_probe_only": outcome == "entry_ready_probe_only",
        "pre_entry_safety_failure": outcome == "native_termination_before_entry",
        "entry_timeout": outcome == "entry_timeout",
        "incomplete_runtime_error": outcome == "runtime_error",
        "post_entry_runtime_error": outcome == "runtime_error" and "transition_ready" in names,
        "push_safety_termination": outcome == "native_termination_during_push",
        "push_settled_no_exit": outcome == "nav_to_push_settled_no_exit",
        "exit_safety_termination": outcome == "native_termination_during_exit",
        "extended_arm_exit_stable": outcome == "push_exit_stable_arm_extended_no_nav",
        "full_chain_target_stable": outcome == "nav_push_stow_nav_target_stable",
        "return_nav_executed": False if outcome in ("nav_to_push_settled_no_exit",
                                                    "native_termination_during_exit",
                                                    "push_exit_stable_arm_extended_no_nav")
        else True if outcome == "nav_push_stow_nav_target_stable" else None,
        "source_id": identity[0],
        "report_sha256": sha256(report_path),
        "control_trace_sha256": sha256(trace_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--control-trace", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error("Output file exists")
    try:
        result = audit(args.report, args.control_trace)
    except ValueError as error:
        parser.error(str(error))
    result["analysis_sha256"] = sha256(Path(__file__))
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
