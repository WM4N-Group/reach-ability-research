"""Run and compare prefix-free held-step WBC suffixes against frozen candidates."""

from __future__ import annotations

import argparse
from argparse import Namespace
import json
from pathlib import Path

import numpy as np
import torch

from check_piper_arm_precontact_motion import run_episode
from check_piper_startup import sha256


def _maximum_difference(left: list[dict], right: list[dict], field: str) -> float | None:
    if len(left) != len(right):
        return None
    return max((abs(a[field] - b[field]) for a, b in zip(left, right)), default=0.0)


def _reference_accepts(result: dict, deadline: float) -> bool:
    event = result["motion"]["target_step_event"]
    entries = [item for item in result["motion"]["wbc_hold_events"]
               if item["time"] > event["time"]]
    return bool(result["reason"] == "completed" and entries
                and entries[-1]["time"] - event["time"] <= deadline)


def _control_history_valid(history: list[dict], start_step: int, end_step: int) -> bool:
    if len(history) != end_step - start_step + 1:
        return False
    previous_stable = 0
    previous_entries = 0
    for index, item in enumerate(history):
        if item["control_step"] != start_step + index:
            return False
        if item["stable_steps"] != (previous_stable + 1 if item["settled"] else 0):
            return False
        if item["hold_entry_count"] < previous_entries:
            return False
        previous_stable = item["stable_steps"]
        previous_entries = item["hold_entry_count"]
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol-json", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    protocol = json.loads(args.protocol_json.read_text())
    if (sha256(Path(__file__)) != protocol["evaluator_sha256"]
            or sha256(Path(protocol["motion_source"])) != protocol["motion_sha256"]):
        raise ValueError("Frozen continuation source changed")
    if args.output_dir.exists():
        parser.error("Require a new output directory")
    torch.set_num_threads(1)
    outputs = []
    for item in protocol["cases"]:
        context_path = Path(item["context_path"])
        reference_path = Path(item["reference_path"])
        if (sha256(context_path) != item["context_sha256"]
                or sha256(reference_path) != item["reference_sha256"]):
            raise ValueError("Frozen context or reference changed")
        context = json.loads(context_path.read_text())
        reference = json.loads(reference_path.read_text())
        if (context["seed"] != item["seed"] or reference["seed"] != item["seed"]
                or reference["phase"] != item["phase"]
                or context["cold_continuation_verified"]
                or context["complete_prefix_accumulators_available"]):
            raise ValueError("Invalid cold continuation case")
        episode_args = Namespace(**context["arguments"])
        episode_args.hold_target_step_local = item["offset_local_m"]
        episode_args.hold_target_step_probe = False
        suffix = run_episode(episode_args, cold_context=context)
        event = suffix["target_step_event"]
        reference_result = reference["result"]
        reference_event = reference_result["motion"]["target_step_event"]
        reference_trace = [row for row in reference_result["motion"]["trace"]
                           if row["time"] > reference_event["time"]]
        trace = suffix["trace"]
        hand_difference = _maximum_difference(trace, reference_trace, "hand_position_error")
        speed_difference = _maximum_difference(trace, reference_trace, "arm_speed")
        qpos = suffix["final_state"]["qpos"]
        reference_qpos = reference_result["motion"]["final_state"]["qpos"]
        qpos_difference = float(np.max(np.abs(np.asarray(qpos) - np.asarray(reference_qpos))))
        history = suffix["control_history"]
        history_valid = _control_history_valid(
            history, suffix["start_control_step"], suffix["last_control_step"]
        )
        safety = suffix["suffix_safety"]
        safety_valid = bool(
            safety["physics_steps"] == safety["dynamic_physics_samples"]
            and safety["sweep_intervals"] == safety["dynamic_physics_samples"]
            and safety["first_box_contact"] is None
            and safety["first_nonfoot_ground_contact"] is None
            and safety["box_stop_event"] is None
        )
        same_times = [row["time"] for row in trace] == [row["time"] for row in reference_trace]
        gates = protocol["trajectory_gates"]
        passed = bool(
            event is not None and event["applied"]
            and event["closed_loop_state_v2"] == context["closed_loop_state_v2"]
            and event["time"] == reference_event["time"]
            and event["offset_local_m"] == item["offset_local_m"]
            and suffix["reason"] == reference_result["reason"]
            and suffix["ten_second_acceptance"] == _reference_accepts(
                reference_result, protocol["primary_deadline_seconds"]
            )
            and history_valid and safety_valid and same_times
            and hand_difference is not None
            and hand_difference <= gates["maximum_sampled_hand_error_difference_m"]
            and speed_difference is not None
            and speed_difference <= gates["maximum_sampled_arm_speed_difference_rad_s"]
            and qpos_difference <= gates["maximum_final_qpos_difference"]
        )
        outputs.append({
            "seed": item["seed"], "phase": item["phase"], "passed": passed,
            "reason": suffix["reason"],
            "ten_second_acceptance": suffix["ten_second_acceptance"],
            "same_boundary_state": event["closed_loop_state_v2"] == context["closed_loop_state_v2"],
            "control_history_valid": history_valid,
            "physics_step_safety_valid": safety_valid,
            "same_sample_times": same_times,
            "maximum_sampled_hand_error_difference_m": hand_difference,
            "maximum_sampled_arm_speed_difference_rad_s": speed_difference,
            "maximum_final_qpos_difference": qpos_difference,
            "context_sha256": item["context_sha256"],
            "reference_sha256": item["reference_sha256"],
            "suffix": suffix,
        })
    args.output_dir.mkdir(parents=True)
    for row in outputs:
        path = args.output_dir / f"seed{row['seed']}-{row['phase']}-cold-suffix-v1.json"
        with path.open("x") as destination:
            json.dump(row, destination, indent=2, allow_nan=False)
            destination.write("\n")
        print(f"{path}: {sha256(path)} passed={row['passed']}")
    summary = {
        "schema_version": 1,
        "scope": "Known held-step states, no NAV/IK prefix, no contact or PUSH actor",
        "protocol_sha256": sha256(args.protocol_json),
        "evaluator_sha256": sha256(Path(__file__)),
        "motion_sha256": sha256(Path(protocol["motion_source"])),
        "all_passed": all(row["passed"] for row in outputs),
        "rows": [{key: value for key, value in row.items() if key != "suffix"} for row in outputs],
    }
    path = args.output_dir / "summary-v1.json"
    with path.open("x") as destination:
        json.dump(summary, destination, indent=2, allow_nan=False)
        destination.write("\n")
    print(f"{path}: {sha256(path)} all_passed={summary['all_passed']}")
    if not summary["all_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
