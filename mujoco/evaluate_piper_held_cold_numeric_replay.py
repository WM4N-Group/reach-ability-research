"""Replay frozen near-threshold held suffixes in a fresh process."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import torch

from check_piper_arm_precontact_motion import run_episode
from check_piper_startup import sha256


def _write(path: Path, value: dict) -> str:
    with path.open("x") as destination:
        json.dump(value, destination, indent=2, allow_nan=False)
        destination.write("\n")
    return sha256(path)


def _maximum_difference(left: list[dict], right: list[dict], field: str) -> float | None:
    if len(left) != len(right):
        return None
    return max((abs(a[field] - b[field]) for a, b in zip(left, right)), default=0.0)


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
        raise ValueError("Frozen source changed")
    torch.set_num_threads(1)
    args.output_dir.mkdir(parents=True)
    rows = []
    for case in protocol["cases"]:
        context_path = Path(case["context_path"])
        reference_path = Path(case["reference_path"])
        if (sha256(context_path) != case["context_sha256"]
                or sha256(reference_path) != case["reference_sha256"]):
            raise ValueError(f"Frozen input changed: seed{case['seed']}")
        context = json.loads(context_path.read_text())
        reference = json.loads(reference_path.read_text())
        if (context["seed"] != reference["seed"] or context["seed"] != case["seed"]
                or reference["target_step_event"]["closed_loop_state_v2"]
                != context["closed_loop_state_v2"]
                or reference["target_step_event"]["offset_local_m"]
                != case["offset_local_m"]):
            raise ValueError("Reference is not from the frozen context")
        run_args = argparse.Namespace(**context["arguments"])
        run_args.hold_target_step_local = case["offset_local_m"]
        run_args.hold_target_step_probe = False
        replay = run_episode(run_args, cold_context=context)
        path = args.output_dir / f"seed{case['seed']}-{case['name']}-replay-v1.json"
        report_sha256 = _write(path, replay)
        history = replay["control_history"]
        original_history = reference["control_history"]
        same_history_times = [row["time"] for row in history] == [
            row["time"] for row in original_history
        ]
        same_history_modes = bool(
            len(history) == len(original_history)
            and all(all(a[key] == b[key] for key in (
                "control_step", "settled", "stable_steps", "command_was_held",
                "hold_entry_count", "hand_gate_passed",
            )) for a, b in zip(history, original_history))
        )
        hand_difference = _maximum_difference(history, original_history, "hand_position_error")
        speed_difference = _maximum_difference(history, original_history, "arm_speed")
        qpos_difference = float(np.max(np.abs(
            np.asarray(replay["final_state"]["qpos"])
            - np.asarray(reference["final_state"]["qpos"])
        )))
        safety = replay["suffix_safety"]
        reference_safety = reference["suffix_safety"]
        safety_valid = bool(
            safety["physics_steps"] == safety["dynamic_physics_samples"]
            == safety["sweep_intervals"] == reference_safety["physics_steps"]
            and safety["first_box_contact"] is None
            and safety["first_nonfoot_ground_contact"] is None
            and safety["box_stop_event"] is None
            and safety["failure_snapshot"] is None
        )
        gates = protocol["trajectory_gates"]
        valid = bool(
            replay["target_step_event"]["closed_loop_state_v2"]
            == context["closed_loop_state_v2"]
            and replay["reason"] == reference["reason"]
            and replay["ten_second_acceptance"] == reference["ten_second_acceptance"]
            and same_history_times and same_history_modes and safety_valid
            and hand_difference is not None
            and hand_difference <= gates["maximum_control_hand_error_difference_m"]
            and speed_difference is not None
            and speed_difference <= gates["maximum_control_arm_speed_difference_rad_s"]
            and qpos_difference <= gates["maximum_final_qpos_difference"]
        )
        row = {
            "seed": case["seed"], "name": case["name"],
            "offset_local_m": case["offset_local_m"], "valid": valid,
            "same_history_times": same_history_times,
            "same_history_modes": same_history_modes,
            "physics_step_safety_valid": safety_valid,
            "reason": replay["reason"],
            "ten_second_acceptance": replay["ten_second_acceptance"],
            "maximum_control_hand_error_difference_m": hand_difference,
            "maximum_control_arm_speed_difference_rad_s": speed_difference,
            "maximum_final_qpos_difference": qpos_difference,
            "reference_sha256": case["reference_sha256"],
            "context_sha256": case["context_sha256"],
            "replay_sha256": report_sha256,
        }
        rows.append(row)
        print(json.dumps(row), flush=True)
    summary = {
        "schema_version": 1,
        "scope": "Fresh-process numeric repeatability of known held-state suffixes",
        "protocol_sha256": sha256(args.protocol_json),
        "evaluator_sha256": sha256(Path(__file__)),
        "motion_sha256": sha256(Path(protocol["motion_source"])),
        "all_valid": all(row["valid"] for row in rows),
        "rows": rows,
    }
    path = args.output_dir / "summary-v1.json"
    print(json.dumps({"summary_path": str(path), "summary_sha256": _write(path, summary),
                      "all_valid": summary["all_valid"]}), flush=True)
    if not summary["all_valid"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
