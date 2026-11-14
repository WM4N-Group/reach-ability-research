"""Probe one preregistered cold WBC hold-entry timing intervention."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch

from check_piper_arm_precontact_motion import run_episode
from check_piper_startup import sha256


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol-json", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error("Require a new output path")
    protocol = json.loads(args.protocol_json.read_text())
    if (sha256(Path(__file__)) != protocol["probe_sha256"]
            or sha256(Path(protocol["motion_source"])) != protocol["motion_sha256"]):
        raise ValueError("Frozen diagnostic source changed")
    context_path = Path(protocol["context_path"])
    original_path = Path(protocol["original_suffix_path"])
    if (sha256(context_path) != protocol["context_sha256"]
            or sha256(original_path) != protocol["original_suffix_sha256"]):
        raise ValueError("Frozen state or original suffix changed")
    context = json.loads(context_path.read_text())
    original = json.loads(original_path.read_text())
    if (context["seed"] != protocol["seed"] or original["seed"] != protocol["seed"]
            or original["phase"] != protocol["phase"]
            or original["context_sha256"] != protocol["context_sha256"]):
        raise ValueError("Diagnostic input is not the frozen exact-state pair")
    run_args = argparse.Namespace(**context["arguments"])
    run_args.hold_target_step_local = protocol["offset_local_m"]
    run_args.hold_target_step_probe = False
    torch.set_num_threads(1)
    suffix = run_episode(
        run_args, cold_context=context,
        cold_hold_entry_not_before_control_step=protocol["first_allowed_hold_entry_control_step"],
    )
    history = suffix["control_history"]
    prefix_entries = suffix["prefix_hold_event_count"]
    first_entry = next((item["control_step"] for item in history
                        if item["hold_entry_count"] > prefix_entries), None)
    safety = suffix["suffix_safety"]
    applied_as_specified = bool(
        suffix["target_step_event"]["closed_loop_state_v2"] == context["closed_loop_state_v2"]
        and suffix["diagnostic_hold_entry_not_before_control_step"]
        == protocol["first_allowed_hold_entry_control_step"]
        and (first_entry is None or first_entry >= protocol["first_allowed_hold_entry_control_step"])
    )
    safety_complete = bool(
        safety["physics_steps"] == safety["dynamic_physics_samples"]
        and safety["sweep_intervals"] == safety["dynamic_physics_samples"]
        and safety["first_box_contact"] is None
        and safety["first_nonfoot_ground_contact"] is None
        and safety["box_stop_event"] is None
    )
    output = {
        "schema_version": 1,
        "scope": "Single known-state hold-entry timing intervention; no policy approval",
        "protocol_sha256": sha256(args.protocol_json),
        "probe_sha256": sha256(Path(__file__)),
        "motion_sha256": sha256(Path(protocol["motion_source"])),
        "context_sha256": protocol["context_sha256"],
        "original_suffix_sha256": protocol["original_suffix_sha256"],
        "first_allowed_hold_entry_control_step": protocol["first_allowed_hold_entry_control_step"],
        "first_observed_post_step_hold_entry_control_step": first_entry,
        "intervention_applied_as_specified": applied_as_specified,
        "suffix_safety_checks_complete": safety_complete,
        "original_reason": original["suffix"]["reason"],
        "intervention_reason": suffix["reason"],
        "original_ten_second_acceptance": original["suffix"]["ten_second_acceptance"],
        "intervention_ten_second_acceptance": suffix["ten_second_acceptance"],
        "suffix": suffix,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x") as destination:
        json.dump(output, destination, indent=2, allow_nan=False)
        destination.write("\n")
    print(json.dumps({key: output[key] for key in (
        "intervention_applied_as_specified", "suffix_safety_checks_complete",
        "first_observed_post_step_hold_entry_control_step", "original_reason",
        "intervention_reason", "original_ten_second_acceptance",
        "intervention_ten_second_acceptance",
    )}))
    if not applied_as_specified:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
