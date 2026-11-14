"""Test a frozen command grid on previously paired independent held states."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import torch

from check_piper_arm_precontact_motion import run_episode
from check_piper_startup import sha256
from export_piper_held_cold_context import export_context


def _write(path: Path, value: dict) -> str:
    with path.open("x") as destination:
        json.dump(value, destination, indent=2, allow_nan=False)
        destination.write("\n")
    return sha256(path)


def _accepts(suffix: dict, deadline: float) -> bool:
    event = suffix["target_step_event"]
    entries = [item for item in suffix["hold_events"] if item["time"] > event["time"]]
    return bool(suffix["reason"] == "completed" and entries
                and entries[-1]["time"] - event["time"] <= deadline)


def _valid_suffix(suffix: dict, context: dict, offset: list[float], deadline: float) -> bool:
    event = suffix["target_step_event"]
    history = suffix["control_history"]
    safety = suffix["suffix_safety"]
    return bool(
        event is not None and event["applied"]
        and event["offset_local_m"] == offset
        and event["closed_loop_state_v2"] == context["closed_loop_state_v2"]
        and suffix["ten_second_acceptance"] == _accepts(suffix, deadline)
        and len(history) == suffix["last_control_step"] - suffix["start_control_step"] + 1
        and all(row["control_step"] == suffix["start_control_step"] + index
                for index, row in enumerate(history))
        and all(row["stable_steps"] == (
            history[index - 1]["stable_steps"] + 1 if row["settled"] else 0
        ) for index, row in enumerate(history) if index > 0)
        and safety["physics_steps"] == safety["dynamic_physics_samples"]
        == safety["sweep_intervals"]
    )


def _anchor_difference(suffix: dict, original: dict) -> dict:
    motion = original["result"]["motion"]
    event_time = motion["target_step_event"]["time"]
    reference_trace = [row for row in motion["trace"] if row["time"] > event_time]
    trace = suffix["trace"]
    differences = {}
    for field in ("hand_position_error", "arm_speed"):
        differences[field] = (max((abs(a[field] - b[field])
                                   for a, b in zip(trace, reference_trace)), default=0.0)
                              if len(trace) == len(reference_trace) else None)
    return {
        "same_reason": suffix["reason"] == original["result"]["reason"],
        "same_sample_times": [row["time"] for row in trace]
        == [row["time"] for row in reference_trace],
        "maximum_final_qpos_difference": float(np.max(np.abs(
            np.asarray(suffix["final_state"]["qpos"])
            - np.asarray(motion["final_state"]["qpos"])
        ))),
        "maximum_sampled_hand_error_difference_m": differences["hand_position_error"],
        "maximum_sampled_arm_speed_difference_rad_s": differences["arm_speed"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol-json", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error("Require a new output directory")
    protocol = json.loads(args.protocol_json.read_text())
    for key, path in (
        ("evaluator_sha256", Path(__file__)),
        ("motion_sha256", Path(protocol["motion_source"])),
        ("context_exporter_sha256", Path(protocol["context_exporter"])),
    ):
        if sha256(path) != protocol[key]:
            raise ValueError(f"Frozen source changed: {path}")
    torch.set_num_threads(1)
    args.output_dir.mkdir(parents=True)
    rows = []
    for case in protocol["cases"]:
        seed = case["seed"]
        baseline_path = Path(case["baseline_path"])
        original_path = Path(case["original_path"])
        if (sha256(baseline_path) != case["baseline_sha256"]
                or sha256(original_path) != case["original_sha256"]):
            raise ValueError(f"Frozen report changed: seed{seed}")
        baseline = json.loads(baseline_path.read_text())
        original = json.loads(original_path.read_text())
        baseline_event = baseline["result"]["motion"]["target_step_event"]
        original_event = original["result"]["motion"]["target_step_event"]
        comparison = original["baseline_comparison"]
        eligible = bool(
            baseline["seed"] == original["seed"] == seed
            and baseline["phase"] == "baseline"
            and original["phase"] == "x_minus_12mm"
            and baseline["result"]["reason"] == "completed"
            and baseline_event is not None and not baseline_event["applied"]
            and original_event is not None and original_event["applied"]
            and original["offset_local_m"] == protocol["anchor_offset_local_m"]
            and comparison["baseline_sha256"] == case["baseline_sha256"]
            and all(comparison[key] is True for key in (
                "same_nav_trace", "same_precontact_state", "same_pre_step_trace",
                "same_pre_step_state", "same_closed_loop_state_v2",
            ))
            and original_event["closed_loop_state_v2"] == baseline_event["closed_loop_state_v2"]
        )
        row = {"seed": seed, "layout": case["layout"], "eligible": eligible,
               "baseline_sha256": case["baseline_sha256"],
               "original_sha256": case["original_sha256"], "grid": []}
        rows.append(row)
        if not eligible:
            row["decision"] = "abstain_invalid_pair"
            continue
        context = export_context(baseline_path, case["baseline_sha256"])
        context_path = args.output_dir / f"seed{seed}-context-v1.json"
        row["context_sha256"] = _write(context_path, context)
        run_args = argparse.Namespace(**context["arguments"])
        run_args.hold_target_step_local = protocol["anchor_offset_local_m"]
        run_args.hold_target_step_probe = False
        anchor = run_episode(run_args, cold_context=context)
        anchor_path = args.output_dir / f"seed{seed}-anchor-suffix-v1.json"
        row["anchor_suffix_sha256"] = _write(anchor_path, anchor)
        anchor_comparison = _anchor_difference(anchor, original)
        row["anchor_comparison"] = anchor_comparison
        gates = protocol["anchor_trajectory_gates"]
        anchor_valid = bool(
            _valid_suffix(anchor, context, protocol["anchor_offset_local_m"],
                          protocol["primary_deadline_seconds"])
            and anchor_comparison["same_reason"] and anchor_comparison["same_sample_times"]
            and anchor_comparison["maximum_final_qpos_difference"]
            <= gates["maximum_final_qpos_difference"]
            and anchor_comparison["maximum_sampled_hand_error_difference_m"] is not None
            and anchor_comparison["maximum_sampled_hand_error_difference_m"]
            <= gates["maximum_sampled_hand_error_difference_m"]
            and anchor_comparison["maximum_sampled_arm_speed_difference_rad_s"] is not None
            and anchor_comparison["maximum_sampled_arm_speed_difference_rad_s"]
            <= gates["maximum_sampled_arm_speed_difference_rad_s"]
        )
        row["anchor_valid"] = anchor_valid
        if not anchor_valid:
            row["decision"] = "abstain_anchor_mismatch"
            print(json.dumps({"seed": seed, "decision": row["decision"]}), flush=True)
            continue
        row["anchor_acceptance"] = anchor["ten_second_acceptance"]
        for target in protocol["grid"]:
            run_args.hold_target_step_local = target["offset_local_m"]
            suffix = run_episode(run_args, cold_context=context)
            suffix_path = args.output_dir / f"seed{seed}-{target['name']}-suffix-v1.json"
            report_sha256 = _write(suffix_path, suffix)
            safety = suffix["suffix_safety"]
            item = {
                "name": target["name"], "offset_local_m": target["offset_local_m"],
                "valid": _valid_suffix(suffix, context, target["offset_local_m"],
                                       protocol["primary_deadline_seconds"]),
                "reason": suffix["reason"],
                "ten_second_acceptance": suffix["ten_second_acceptance"],
                "first_box_contact": safety["first_box_contact"],
                "first_nonfoot_ground_contact": safety["first_nonfoot_ground_contact"],
                "box_stop_event": safety["box_stop_event"],
                "failure_snapshot": safety["failure_snapshot"],
                "physics_steps": safety["physics_steps"],
                "minimum_self_clearance_m": safety["minimum_self_clearance"],
                "minimum_environment_clearance_m": safety["minimum_environment_clearance"],
                "minimum_support_margin_m": safety["minimum_support_margin"],
                "suffix_sha256": report_sha256,
            }
            row["grid"].append(item)
            print(json.dumps({"seed": seed, **item}), flush=True)
        row["decision"] = "evaluated" if all(item["valid"] for item in row["grid"]) else "invalid_suffix"
    summary = {
        "schema_version": 1,
        "scope": "Frozen command offsets on independently paired held states; no contact or deployment",
        "protocol_sha256": sha256(args.protocol_json),
        "evaluator_sha256": sha256(Path(__file__)),
        "evaluated_count": sum(row.get("decision") == "evaluated" for row in rows),
        "rows": rows,
    }
    summary_path = args.output_dir / "summary-v1.json"
    print(json.dumps({"summary_path": str(summary_path),
                      "summary_sha256": _write(summary_path, summary),
                      "evaluated_count": summary["evaluated_count"]}), flush=True)
    if summary["evaluated_count"] != len(protocol["cases"]):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
