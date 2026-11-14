"""Audit a selected arm command pulse against the frozen Isaac clock runs."""

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def first_vector_difference(left, right, field, names, tolerance=1e-10):
    for old, new in zip(left, right, strict=True):
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


def comparable_layers(layers):
    return [{"kind": item["kind"], "sha256": item["sha256"],
             "identifier": None if item["kind"] == "anonymous" else item["identifier"]}
            for item in layers]


def first_illegal_sensor_sample(rows):
    for row in rows:
        contact = row["hand_contact"]
        force = contact["force_norm_n"]
        if force <= 1.0:
            continue
        x, y, z = contact["contact_pos_box_m"]
        length, width, height = contact["box_size_m"]
        valid = (
            contact["contact_to_hand_m"] < contact["tip_radius_limit_m"]
            and contact["resisting_force_n"] > 1.0
            and contact["resisting_force_n"] > 0.8 * force
            and abs(x + length / 2) < 0.02
            and abs(y) < width / 2
            and abs(z) <= height / 2 - contact["height_margin_m"] + 1e-4
        )
        if not valid:
            return {"push_control_step": row["push_control_step"],
                    "physics_substep": row["physics_substep"],
                    "contact_height_box_m": z,
                    "allowed_height_with_epsilon_m": height / 2 - contact["height_margin_m"] + 1e-4}
    return None


def audit_seed(protocol, prior_audit, prior_dir, run_dir, seed):
    old_path = prior_dir / f"seed{seed}-actuator_clock.json"
    expected_hash = next(item for item in prior_audit["records"]
                         if item["seed"] == seed)["raw_report_sha256"]["actuator_clock"]
    if sha256(old_path) != expected_hash:
        raise ValueError(f"Prior seed{seed} report differs from its frozen audit")
    old = load(old_path)
    paths = {mode: run_dir / f"seed{seed}-{mode}.json"
             for mode in protocol["modes_per_seed"]}
    reports = {mode: load(path) for mode, path in paths.items()}
    base, pulse = reports["arm_clock"], reports["arm_pulse"]
    pulse_step = protocol["pulse_control_steps"][str(seed)]
    prefix_substeps = (pulse_step - 1) * protocol["control_decimation"]
    old_excluded = {
        "schema_version", "push_clock_trace", "scene_runtime_observation",
        "scene_runtime_observation_sha256",
    }
    old_fields_match = all(old[key] == base.get(key) for key in old if key not in old_excluded)
    old_clock_match = (
        len(old["push_clock_trace"]) == len(base["push_clock_trace"])
        and all(all(value == new.get(key) for key, value in row.items())
                for row, new in zip(old["push_clock_trace"],
                                    base["push_clock_trace"], strict=True))
    )
    old_scene, new_scene = old["scene_runtime_observation"], base["scene_runtime_observation"]
    scene_fields = [key for key in old_scene if key not in (
        "used_layers", "source_sha256", "stage_export_sha256")]
    old_sources, new_sources = old_scene["source_sha256"], new_scene["source_sha256"]
    scene_check = {
        "other_scene_fields_match": all(old_scene[key] == new_scene.get(key)
                                        for key in scene_fields),
        "used_layer_content_matches": comparable_layers(old_scene["used_layers"])
                                      == comparable_layers(new_scene["used_layers"]),
        "source_hashes_match_except_diagnostic": all(
            value == new_sources.get(key) for key, value in old_sources.items()
            if key != "diagnostic"
        ) and new_sources["diagnostic"] == protocol["source_sha256"]["new_diagnostic"],
        "stage_export_sha256_matches": old_scene["stage_export_sha256"]
                                       == new_scene["stage_export_sha256"],
    }
    prefix_check = {
        "handoff": base["handoff"] == pulse["handoff"],
        "hand_contact_substeps": base["hand_contact_substeps"][:prefix_substeps]
                                 == pulse["hand_contact_substeps"][:prefix_substeps],
        "support_trace": base["support_trace"][:pulse_step - 1]
                         == pulse["support_trace"][:pulse_step - 1],
        "push_clock_actions": base["push_clock_actions"][:pulse_step - 1]
                              == pulse["push_clock_actions"][:pulse_step - 1],
        "push_clock_trace": base["push_clock_trace"][:prefix_substeps]
                            == pulse["push_clock_trace"][:prefix_substeps],
    }
    lag_values = {mode: {name: sorted({row["arm_delay_substeps"][name]
                                       for row in report["push_clock_trace"]})
                         for name in base["push_arm_clock_contract"]["actuators"]}
                  for mode, report in reports.items()}
    stable_lag = all(len(values) == 1 for lag in lag_values.values()
                     for values in lag.values())
    same_lag = lag_values["arm_clock"] == lag_values["arm_pulse"]
    qualified = (old_fields_match and old_clock_match
                 and all(value for key, value in scene_check.items()
                         if key != "stage_export_sha256_matches")
                 and all(prefix_check.values()) and stable_lag and same_lag
                 and base["push_arm_command_pulse_count"] == 0
                 and pulse["push_arm_command_pulse_count"] == 1)
    result = {
        "seed": seed,
        "pulse_control_step": pulse_step,
        "raw_report_sha256": {mode: sha256(path) for mode, path in paths.items()},
        "outcomes": {mode: report["outcome"] for mode, report in reports.items()},
        "terminal_reasons": {mode: [name for name, value in report["terminal"].get(
            "reasons", {}).items() if value] for mode, report in reports.items()},
        "prior_report_reproducibility": {
            "all_non_scene_old_fields_match": old_fields_match,
            "all_old_clock_rows_match": old_clock_match,
            **scene_check,
        },
        "recorded_prefix_matches": prefix_check,
        "arm_delay_substeps": lag_values,
        "stable_and_paired_arm_lag": stable_lag and same_lag,
        "first_illegal_hand_sensor_sample": {
            mode: first_illegal_sensor_sample(report["hand_contact_substeps"])
            for mode, report in reports.items()
        },
        "recorded_mechanism_qualified": qualified,
        "full_hidden_state_coupling_proven": False,
    }
    if qualified:
        clocks = (base["push_clock_trace"], pulse["push_clock_trace"])
        names = base["joint_names"]
        for output, field in (
            ("first_target_difference", "joint_target_before_sim"),
            ("first_computed_torque_difference", "computed_torque_before_sim"),
            ("first_applied_torque_difference", "applied_torque_before_sim"),
            ("first_joint_position_difference", "joint_pos_after_update"),
        ):
            result[output] = first_vector_difference(*clocks, field, names)
        hand_rows = (base["hand_contact_substeps"], pulse["hand_contact_substeps"])
        result["first_hand_origin_difference"] = first_vector_difference(
            *hand_rows, "hand_body_origin_box_m", ["x", "y", "z"]
        )
        result["first_hand_contact_record_difference"] = next((
            {"push_control_step": left["push_control_step"],
             "physics_substep": left["physics_substep"]}
            for left, right in zip(*hand_rows, strict=True)
            if left["hand_contact"] != right["hand_contact"]
        ), None)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--prior-audit", type=Path, required=True)
    parser.add_argument("--prior-run-dir", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error("Output already exists")
    protocol = load(args.protocol)
    if (protocol["seeds"] != [6403, 6415] or protocol["run_denominator"] != 4
            or protocol["modes_per_seed"] != ["arm_clock", "arm_pulse"]):
        raise ValueError("Unexpected frozen arm-clock protocol")
    if sha256(args.prior_audit) != protocol["source_sha256"]["previous_audit"]:
        raise ValueError("Prior audit differs from frozen protocol")
    prior_audit = load(args.prior_audit)
    result = {
        "schema_version": 1,
        "protocol_sha256": sha256(args.protocol),
        "analysis_script_sha256": sha256(Path(__file__)),
        "prior_audit_sha256": sha256(args.prior_audit),
        "run_denominator": protocol["run_denominator"],
        "contact_authorized": False,
        "deployment_latency_bound_established": False,
        "records": [audit_seed(protocol, prior_audit, args.prior_run_dir, args.run_dir, seed)
                    for seed in protocol["seeds"]],
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"qualified": sum(item["recorded_mechanism_qualified"]
                                       for item in result["records"]),
                      "total": len(result["records"])}))


if __name__ == "__main__":
    main()
