"""Evaluate a frozen local command grid from one held WBC cold context."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import torch

from check_piper_arm_precontact_motion import run_episode
from check_piper_startup import sha256


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol-json", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error("Require a new output directory")
    protocol = json.loads(args.protocol_json.read_text())
    if (sha256(Path(__file__)) != protocol["evaluator_sha256"]
            or sha256(Path(protocol["motion_source"])) != protocol["motion_sha256"]):
        raise ValueError("Frozen evaluation source changed")
    context_path = Path(protocol["context_path"])
    if sha256(context_path) != protocol["context_sha256"]:
        raise ValueError("Frozen cold context changed")
    context = json.loads(context_path.read_text())
    if (context["seed"] != protocol["seed"]
            or context["complete_prefix_accumulators_available"]
            or context["cold_continuation_verified"]):
        raise ValueError("Invalid cold context")
    offsets = [item["offset_local_m"] for item in protocol["cases"]]
    if len({tuple(offset) for offset in offsets}) != len(offsets):
        raise ValueError("Duplicate command offsets")

    args.output_dir.mkdir(parents=True)
    torch.set_num_threads(1)
    rows = []
    for case in protocol["cases"]:
        run_args = argparse.Namespace(**context["arguments"])
        run_args.hold_target_step_local = case["offset_local_m"]
        run_args.hold_target_step_probe = False
        suffix = run_episode(run_args, cold_context=context)
        event = suffix["target_step_event"]
        history = suffix["control_history"]
        safety = suffix["suffix_safety"]
        entry_times = [item["time"] for item in suffix["hold_events"]
                       if item["time"] > event["time"]]
        last_entry_delay = entry_times[-1] - event["time"] if entry_times else None
        history_valid = bool(
            len(history) == suffix["last_control_step"] - suffix["start_control_step"] + 1
            and all(item["control_step"] == suffix["start_control_step"] + index
                    for index, item in enumerate(history))
            and all(item["stable_steps"] == (
                history[index - 1]["stable_steps"] + 1 if item["settled"] else 0
            ) for index, item in enumerate(history) if index > 0)
        )
        safety_complete = bool(
            safety["physics_steps"] == safety["dynamic_physics_samples"]
            == safety["sweep_intervals"]
            and safety["first_box_contact"] is None
            and safety["first_nonfoot_ground_contact"] is None
            and safety["box_stop_event"] is None
        )
        boundary_valid = bool(
            event is not None and event["applied"]
            and event["closed_loop_state_v2"] == context["closed_loop_state_v2"]
            and event["offset_local_m"] == case["offset_local_m"]
        )
        acceptance = bool(
            suffix["reason"] == "completed" and last_entry_delay is not None
            and last_entry_delay <= protocol["primary_deadline_seconds"]
        )
        anchor_difference = None
        if "anchor_suffix_path" in case:
            anchor_path = Path(case["anchor_suffix_path"])
            if sha256(anchor_path) != case["anchor_suffix_sha256"]:
                raise ValueError("Frozen anchor suffix changed")
            anchor = json.loads(anchor_path.read_text())["suffix"]
            anchor_difference = float(np.max(np.abs(
                np.asarray(suffix["final_state"]["qpos"])
                - np.asarray(anchor["final_state"]["qpos"])
            )))
            if (suffix["reason"] != anchor["reason"]
                    or acceptance != anchor["ten_second_acceptance"]
                    or anchor_difference > protocol["anchor_qpos_tolerance"]):
                raise ValueError("Known anchor did not reproduce")
        valid = bool(
            boundary_valid and history_valid and safety_complete
            and acceptance == suffix["ten_second_acceptance"]
        )
        report_path = args.output_dir / f"{case['name']}-suffix-v1.json"
        with report_path.open("x") as destination:
            json.dump(suffix, destination, indent=2, allow_nan=False)
            destination.write("\n")
        row = {
            "name": case["name"], "offset_local_m": case["offset_local_m"],
            "report_path": str(report_path), "report_sha256": sha256(report_path),
            "valid": valid, "boundary_valid": boundary_valid,
            "control_history_valid": history_valid,
            "physics_step_safety_complete": safety_complete,
            "reason": suffix["reason"], "ten_second_acceptance": acceptance,
            "final_hold_entry_delay_s": last_entry_delay,
            "post_step_hold_entry_count": len(entry_times),
            "physics_steps": safety["physics_steps"],
            "minimum_self_clearance_m": safety["minimum_self_clearance"],
            "minimum_environment_clearance_m": safety["minimum_environment_clearance"],
            "minimum_support_margin_m": safety["minimum_support_margin"],
            "anchor_max_final_qpos_difference": anchor_difference,
        }
        rows.append(row)
        print(json.dumps(row))
    summary = {
        "schema_version": 1,
        "scope": "Discrete command samples from one known held state, no contact or PUSH actor",
        "protocol_sha256": sha256(args.protocol_json),
        "evaluator_sha256": sha256(Path(__file__)),
        "motion_sha256": sha256(Path(protocol["motion_source"])),
        "context_sha256": sha256(context_path),
        "all_valid": all(row["valid"] for row in rows),
        "rows": rows,
    }
    summary_path = args.output_dir / "summary-v1.json"
    with summary_path.open("x") as destination:
        json.dump(summary, destination, indent=2, allow_nan=False)
        destination.write("\n")
    print(f"{summary_path}: {sha256(summary_path)} all_valid={summary['all_valid']}")
    if not summary["all_valid"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
