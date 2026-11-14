"""Audit frozen signed arm-command probes against prior read-only baselines."""

import argparse
import json
from pathlib import Path

from audit_piper_push_arm_command_clock import (
    comparable_layers,
    first_illegal_sensor_sample,
    load,
    sha256,
)


def first_common_vector_difference(left, right, field, names, tolerance=1e-10):
    for old, new in zip(left, right):
        differences = [abs(a - b) for a, b in zip(old[field], new[field], strict=True)]
        largest = max(differences)
        if largest > tolerance:
            return {
                "push_control_step": old["push_control_step"],
                "physics_substep": old["physics_substep"],
                "max_abs_difference": largest,
                "max_difference_name": names[differences.index(largest)],
            }
    return None


def audit_seed(protocol, baseline_dir, run_dir, seed):
    baseline_path = baseline_dir / f"seed{seed}-arm_clock.json"
    pulse_path = run_dir / f"seed{seed}-arm_negative.json"
    if sha256(baseline_path) != protocol["source_sha256"][f"baseline_{seed}"]:
        raise ValueError(f"Frozen seed{seed} baseline report differs")
    baseline, pulse = load(baseline_path), load(pulse_path)
    pulse_step = protocol["pulse_control_steps"][str(seed)]
    prefix_substeps = (pulse_step - 1) * protocol["control_decimation"]
    prefix = {
        "handoff": baseline["handoff"] == pulse["handoff"],
        "hand_contact_substeps": baseline["hand_contact_substeps"][:prefix_substeps]
                                 == pulse["hand_contact_substeps"][:prefix_substeps],
        "support_trace": baseline["support_trace"][:pulse_step - 1]
                         == pulse["support_trace"][:pulse_step - 1],
        "push_clock_actions": baseline["push_clock_actions"][:pulse_step - 1]
                              == pulse["push_clock_actions"][:pulse_step - 1],
        "push_clock_trace": baseline["push_clock_trace"][:prefix_substeps]
                            == pulse["push_clock_trace"][:prefix_substeps],
    }
    old_scene = baseline["scene_runtime_observation"]
    new_scene = pulse["scene_runtime_observation"]
    scene_fields = set(old_scene) - {"used_layers", "source_sha256", "stage_export_sha256"}
    scene = {
        "other_scene_fields_match": all(old_scene[key] == new_scene.get(key) for key in scene_fields),
        "used_layer_content_matches": comparable_layers(old_scene["used_layers"])
                                      == comparable_layers(new_scene["used_layers"]),
        "source_hashes_match": old_scene["source_sha256"] == new_scene["source_sha256"],
        "stage_export_sha256_matches": old_scene["stage_export_sha256"]
                                       == new_scene["stage_export_sha256"],
    }
    contract = pulse["push_arm_command_pulse"]
    source_ok = (pulse["control_sha256"] == baseline["control_sha256"]
                 and pulse["nav_actor_sha256"] == protocol["source_sha256"]["nav_actor"]
                 and pulse["push_checkpoint_sha256"] == protocol["source_sha256"]["push_checkpoint"])
    pulse_ok = (contract == {"control_step": pulse_step, "joint": protocol["pulse_joint"],
                             "target_delta_rad": protocol["pulse_target_delta_rad"]}
                and pulse["push_arm_command_pulse_count"] == 1
                and baseline["push_arm_command_pulse_count"] == 0)
    joint_index = baseline["joint_names"].index(protocol["pulse_joint"])
    baseline_target = next(row["joint_target_before_sim"][joint_index]
                           for row in baseline["push_clock_trace"]
                           if row["push_control_step"] == pulse_step and row["physics_substep"] == 1)
    pulse_target = next(row["joint_target_before_sim"][joint_index]
                        for row in pulse["push_clock_trace"]
                        if row["push_control_step"] == pulse_step and row["physics_substep"] == 1)
    signed_target_difference = pulse_target - baseline_target
    pulse_ok &= abs(signed_target_difference - protocol["pulse_target_delta_rad"]) < 1e-6
    lag_names = baseline["push_arm_clock_contract"]["actuators"]
    lag_values = {
        mode: {name: sorted({row["arm_delay_substeps"][name] for row in report["push_clock_trace"]})
               for name in lag_names}
        for mode, report in (("baseline", baseline), ("negative", pulse))
    }
    lag_ok = lag_values["baseline"] == lag_values["negative"] and all(
        len(values) == 1 for values in lag_values["negative"].values()
    )
    qualified = (all(prefix.values()) and all(value for key, value in scene.items()
                                             if key != "stage_export_sha256_matches")
                 and source_ok and pulse_ok and lag_ok)
    clocks = baseline["push_clock_trace"], pulse["push_clock_trace"]
    hand_rows = baseline["hand_contact_substeps"], pulse["hand_contact_substeps"]
    names = baseline["joint_names"]
    differences = {}
    for output, field in (
        ("first_target_difference", "joint_target_before_sim"),
        ("first_computed_torque_difference", "computed_torque_before_sim"),
        ("first_applied_torque_difference", "applied_torque_before_sim"),
        ("first_joint_position_difference", "joint_pos_after_update"),
    ):
        differences[output] = first_common_vector_difference(*clocks, field, names)
    differences["first_hand_origin_difference"] = first_common_vector_difference(
        *hand_rows, "hand_body_origin_box_m", ["x", "y", "z"]
    )
    differences["first_hand_contact_record_difference"] = next((
        {"push_control_step": left["push_control_step"],
         "physics_substep": left["physics_substep"]}
        for left, right in zip(*hand_rows)
        if left["hand_contact"] != right["hand_contact"]
    ), None)
    return {
        "seed": seed,
        "raw_report_sha256": {"baseline": sha256(baseline_path), "negative": sha256(pulse_path)},
        "recorded_prefix_matches": prefix,
        "scene_match": scene,
        "source_match": source_ok,
        "pulse_contract_match": pulse_ok,
        "signed_joint3_target_difference_rad": signed_target_difference,
        "arm_delay_substeps": lag_values,
        "arm_delay_match": lag_ok,
        "recorded_mechanism_qualified": qualified,
        "full_hidden_state_coupling_proven": False,
        "outcome": {"baseline": baseline["outcome"], "negative": pulse["outcome"]},
        "terminal_reasons": {
            mode: [name for name, active in report["terminal"]["reasons"].items() if active]
            for mode, report in (("baseline", baseline), ("negative", pulse))
        },
        "first_illegal_hand_sensor_sample": {
            mode: first_illegal_sensor_sample(report["hand_contact_substeps"])
            for mode, report in (("baseline", baseline), ("negative", pulse))
        },
        "hand_substep_counts": {"baseline": len(hand_rows[0]), "negative": len(hand_rows[1])},
        **differences,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--prior-audit", type=Path, required=True)
    parser.add_argument("--baseline-dir", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error("Output file already exists")
    protocol = load(args.protocol)
    if protocol["seeds"] != [6403, 6415] or protocol["run_denominator"] != 2:
        raise ValueError("Unexpected signed arm command protocol")
    if sha256(args.prior_audit) != protocol["source_sha256"]["prior_audit"]:
        raise ValueError("Prior audit differs from frozen protocol")
    records = [audit_seed(protocol, args.baseline_dir, args.run_dir, seed)
               for seed in protocol["seeds"]]
    result = {
        "schema_version": 1,
        "protocol_sha256": sha256(args.protocol),
        "analysis_script_sha256": sha256(Path(__file__)),
        "run_denominator": protocol["run_denominator"],
        "contact_authorized": False,
        "deployment_latency_bound_established": False,
        "records": records,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"qualified": sum(row["recorded_mechanism_qualified"] for row in records),
                      "total": len(records)}))


if __name__ == "__main__":
    main()
