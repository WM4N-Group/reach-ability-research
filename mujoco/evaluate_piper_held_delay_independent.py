"""Evaluate a frozen hold-entry delay on independently selected held states."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import torch

from check_piper_arm_precontact_motion import run_episode
from check_piper_startup import sha256
from export_piper_held_cold_context import export_context


def _accepts(reason: str, event_time: float, hold_events: list[dict], deadline: float) -> bool:
    entries = [entry for entry in hold_events if entry["time"] > event_time]
    return bool(reason == "completed" and entries
                and entries[-1]["time"] - event_time <= deadline)


def _safety_audit(suffix: dict) -> dict:
    safety = suffix["suffix_safety"]
    return {
        "monitor_counts_valid": bool(
        safety["physics_steps"] == safety["dynamic_physics_samples"]
        and 0 <= safety["sweep_intervals"] <= safety["dynamic_physics_samples"]
        ),
        "physics_steps": safety["physics_steps"],
        "sweep_intervals": safety["sweep_intervals"],
        "first_box_contact": safety["first_box_contact"],
        "first_nonfoot_ground_contact": safety["first_nonfoot_ground_contact"],
        "box_stop_event": safety["box_stop_event"],
        "failure_snapshot": safety["failure_snapshot"],
    }


def _compare_cold_original(suffix: dict, original: dict) -> dict:
    reference = original["result"]
    event_time = reference["motion"]["target_step_event"]["time"]
    reference_trace = [row for row in reference["motion"]["trace"] if row["time"] > event_time]
    current_trace = suffix["trace"]
    same_times = [row["time"] for row in current_trace] == [row["time"] for row in reference_trace]
    qpos_difference = float(np.max(np.abs(
        np.asarray(suffix["final_state"]["qpos"])
        - np.asarray(reference["motion"]["final_state"]["qpos"])
    )))
    errors = {}
    for field in ("hand_position_error", "arm_speed"):
        errors[field] = (max((abs(a[field] - b[field])
                              for a, b in zip(current_trace, reference_trace)), default=0.0)
                         if len(current_trace) == len(reference_trace) else None)
    return {
        "same_reason": suffix["reason"] == reference["reason"],
        "same_trace_times": same_times,
        "maximum_final_qpos_difference": qpos_difference,
        "maximum_sampled_hand_error_difference_m": errors["hand_position_error"],
        "maximum_sampled_arm_speed_difference_rad_s": errors["arm_speed"],
    }


def _write_json(path: Path, data: dict) -> None:
    with path.open("x") as destination:
        json.dump(data, destination, indent=2, allow_nan=False)
        destination.write("\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol-json", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error("Require a new output directory")
    protocol = json.loads(args.protocol_json.read_text())
    for name, path in (
        ("evaluator_sha256", Path(__file__)),
        ("motion_sha256", Path(protocol["motion_source"])),
        ("exporter_sha256", Path(protocol["context_exporter"])),
    ):
        if sha256(path) != protocol[name]:
            raise ValueError(f"Frozen source changed: {path}")
    torch.set_num_threads(1)
    rows = []
    outputs = []
    for item in protocol["cases"]:
        seed = item["seed"]
        baseline_path = Path(item["baseline_path"])
        original_path = Path(item["original_path"])
        if (sha256(baseline_path) != item["baseline_sha256"]
                or sha256(original_path) != item["original_sha256"]):
            raise ValueError(f"Frozen report changed: seed{seed}")
        baseline = json.loads(baseline_path.read_text())
        original = json.loads(original_path.read_text())
        baseline_result = baseline["result"]
        original_result = original["result"]
        baseline_event = baseline_result["motion"]["target_step_event"]
        original_event = original_result["motion"]["target_step_event"]
        comparison = original["baseline_comparison"]
        eligible = bool(
            baseline["seed"] == original["seed"] == seed
            and baseline["phase"] == "baseline"
            and original["phase"] == "x_minus_12mm"
            and baseline_result["reason"] == "completed"
            and baseline_event is not None and not baseline_event["applied"]
            and original_event is not None and original_event["applied"]
            and original["offset_local_m"] == protocol["offset_local_m"]
            and comparison["baseline_sha256"] == item["baseline_sha256"]
            and all(comparison[key] is True for key in (
                "same_nav_trace", "same_precontact_state", "same_pre_step_trace",
                "same_pre_step_state", "same_closed_loop_state_v2",
            ))
            and original_event["closed_loop_state_v2"] == baseline_event["closed_loop_state_v2"]
        )
        row = {"seed": seed, "layout": item["layout"], "eligible": eligible,
               "baseline_sha256": item["baseline_sha256"],
               "original_sha256": item["original_sha256"]}
        if not eligible:
            row["decision"] = "abstain_invalid_pair"
            rows.append(row)
            continue
        context = export_context(baseline_path, item["baseline_sha256"])
        run_args = argparse.Namespace(**context["arguments"])
        run_args.hold_target_step_local = protocol["offset_local_m"]
        run_args.hold_target_step_probe = False
        original_cold = run_episode(run_args, cold_context=context)
        cold_comparison = _compare_cold_original(original_cold, original)
        gates = protocol["trajectory_gates"]
        cold_verified = bool(
            original_cold["target_step_event"]["closed_loop_state_v2"]
            == context["closed_loop_state_v2"]
            and cold_comparison["same_reason"] and cold_comparison["same_trace_times"]
            and cold_comparison["maximum_final_qpos_difference"]
            <= gates["maximum_final_qpos_difference"]
            and cold_comparison["maximum_sampled_hand_error_difference_m"] is not None
            and cold_comparison["maximum_sampled_hand_error_difference_m"]
            <= gates["maximum_sampled_hand_error_difference_m"]
            and cold_comparison["maximum_sampled_arm_speed_difference_rad_s"] is not None
            and cold_comparison["maximum_sampled_arm_speed_difference_rad_s"]
            <= gates["maximum_sampled_arm_speed_difference_rad_s"]
        )
        row.update({"cold_original_verified": cold_verified,
                    "cold_original_comparison": cold_comparison})
        if not cold_verified:
            row["decision"] = "abstain_cold_original_mismatch"
            rows.append(row)
            outputs.append((seed, context, original_cold, None))
            continue
        control_dt = baseline_result["simulation"]["policy_dt"]
        delay_steps = round(protocol["fixed_delay_seconds_after_step"] / control_dt)
        first_allowed = baseline_event["control_step"] + delay_steps
        delayed = run_episode(
            run_args, cold_context=context,
            cold_hold_entry_not_before_control_step=first_allowed,
        )
        delayed_event = delayed["target_step_event"]
        delayed_entries = [entry for entry in delayed["hold_events"]
                           if entry["time"] > delayed_event["time"]]
        original_accepts = _accepts(
            original_result["reason"], original_event["time"],
            original_result["motion"]["wbc_hold_events"], protocol["primary_deadline_seconds"],
        )
        delayed_accepts = _accepts(
            delayed["reason"], delayed_event["time"], delayed["hold_events"],
            protocol["primary_deadline_seconds"],
        )
        first_new_entry = delayed_entries[0]["time"] if delayed_entries else None
        mode_valid = bool(
            delayed_event["closed_loop_state_v2"] == context["closed_loop_state_v2"]
            and delayed["diagnostic_hold_entry_not_before_control_step"] == first_allowed
            and all(entry["control_step"] >= first_allowed
                    for entry in delayed["control_history"]
                    if entry["hold_entry_count"] > delayed["prefix_hold_event_count"])
        )
        safety = _safety_audit(delayed)
        row.update({
            "decision": "evaluated" if mode_valid and safety["monitor_counts_valid"]
                        else "abstain_invalid_delayed_suffix",
            "first_allowed_hold_entry_control_step": first_allowed,
            "first_observed_hold_entry_time": first_new_entry,
            "delay_mode_valid": mode_valid,
            "delayed_suffix_safety_audit": safety,
            "original_reason": original_result["reason"],
            "delayed_reason": delayed["reason"],
            "original_ten_second_acceptance": original_accepts,
            "delayed_ten_second_acceptance": delayed_accepts,
            "outcome": ("improved" if delayed_accepts and not original_accepts else
                        "regressed" if original_accepts and not delayed_accepts else "unchanged"),
        })
        rows.append(row)
        outputs.append((seed, context, original_cold, delayed))
    args.output_dir.mkdir(parents=True)
    for seed, context, original_cold, delayed in outputs:
        path = args.output_dir / f"seed{seed}-cold-comparison-v1.json"
        _write_json(path, {"context": context, "original_cold": original_cold, "delayed": delayed})
        next(row for row in rows if row["seed"] == seed)["cold_comparison_sha256"] = sha256(path)
    counts = {name: sum(row.get("outcome") == name and row["decision"] == "evaluated"
                        for row in rows) for name in ("improved", "regressed", "unchanged")}
    summary = {
        "schema_version": 1,
        "scope": "Independent local MuJoCo held-state delay diagnosis; no contact or real-robot claim",
        "protocol_sha256": sha256(args.protocol_json),
        "evaluator_sha256": sha256(Path(__file__)),
        "counts": counts,
        "eligible_count": sum(row["eligible"] for row in rows),
        "evaluated_count": sum(row["decision"] == "evaluated" for row in rows),
        "rows": rows,
    }
    path = args.output_dir / "summary-v1.json"
    _write_json(path, summary)
    print(json.dumps({"summary_path": str(path), "summary_sha256": sha256(path),
                      "eligible_count": summary["eligible_count"],
                      "evaluated_count": summary["evaluated_count"], "counts": counts}))


if __name__ == "__main__":
    main()
