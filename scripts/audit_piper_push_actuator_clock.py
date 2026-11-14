"""Audit the selected Isaac delayed-PD clock against frozen paired runs."""

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def first_difference(reference, candidate, field, joint_names, tolerance=1e-10):
    for left, right in zip(reference, candidate, strict=True):
        differences = [abs(a - b) for a, b in zip(left[field], right[field], strict=True)]
        largest = max(differences)
        if largest > tolerance:
            return {
                "push_control_step": left["push_control_step"],
                "physics_substep": left["physics_substep"],
                "max_abs_difference": largest,
                "max_difference_joint": joint_names[differences.index(largest)],
            }
    return None


def comparable_layers(layers):
    return [{"kind": layer["kind"], "sha256": layer["sha256"],
             "identifier": None if layer["kind"] == "anonymous" else layer["identifier"]}
            for layer in layers]


def audit_seed(protocol, prior_audit, prior_dir, run_dir, seed):
    pulse_step = protocol["pulse_control_steps"][str(seed)]
    modes = {"actuator_clock": "clock", "actuator_pulse": "pulse"}
    prior_record = next(record for record in prior_audit["records"] if record["seed"] == seed)
    reports = {}
    hashes = {}
    reproducibility = {}
    for mode, old_mode in modes.items():
        old_path = prior_dir / f"seed{seed}-{old_mode}.json"
        new_path = run_dir / f"seed{seed}-{mode}.json"
        if sha256(old_path) != prior_record["raw_report_sha256"][old_mode]:
            raise ValueError(f"Prior {seed}/{old_mode} report no longer matches frozen audit")
        old, new = load(old_path), load(new_path)
        reports[mode] = new
        hashes[mode] = sha256(new_path)
        unchanged_fields = [key for key in old if key not in (
            "schema_version", "push_clock_trace", "scene_runtime_observation",
            "scene_runtime_observation_sha256"
        )]
        old_fields_match = all(old[key] == new.get(key) for key in unchanged_fields)
        old_clock_rows_match = (
            len(old["push_clock_trace"]) == len(new["push_clock_trace"])
            and all(all(old_row[key] == new_row.get(key) for key in old_row)
                    for old_row, new_row in zip(old["push_clock_trace"],
                                                new["push_clock_trace"], strict=True))
        )
        old_scene, new_scene = old["scene_runtime_observation"], new["scene_runtime_observation"]
        scene_fields = [key for key in old_scene if key not in (
            "used_layers", "source_sha256", "stage_export_sha256"
        )]
        old_sources, new_sources = old_scene["source_sha256"], new_scene["source_sha256"]
        common_sources = [key for key in old_sources if key != "diagnostic"]
        reproducibility[mode] = {
            "all_non_scene_old_fields_match": old_fields_match,
            "all_old_clock_rows_match": old_clock_rows_match,
            "other_scene_fields_match": all(old_scene[key] == new_scene.get(key)
                                            for key in scene_fields),
            "used_layer_content_matches": comparable_layers(old_scene["used_layers"])
                                          == comparable_layers(new_scene["used_layers"]),
            "source_hashes_match_except_diagnostic": (
                all(old_sources[key] == new_sources.get(key) for key in common_sources)
                and old_sources["diagnostic"] == protocol["source_sha256"]["previous_diagnostic"]
                and new_sources["diagnostic"] == protocol["source_sha256"]["new_diagnostic"]
            ),
            "stage_export_sha256_matches": (
                old_scene["stage_export_sha256"] == new_scene["stage_export_sha256"]
            ),
        }

    clock, pulse = reports["actuator_clock"], reports["actuator_pulse"]
    prefix_rows = (pulse_step - 1) * protocol["control_decimation"]
    prefix_matches = {
        "handoff": clock["handoff"] == pulse["handoff"],
        "hand_contact_substeps": (clock["hand_contact_substeps"][:prefix_rows]
                                  == pulse["hand_contact_substeps"][:prefix_rows]),
        "support_trace": clock["support_trace"][:pulse_step - 1]
                         == pulse["support_trace"][:pulse_step - 1],
        "push_clock_actions": clock["push_clock_actions"][:pulse_step - 1]
                              == pulse["push_clock_actions"][:pulse_step - 1],
        "push_clock_trace": clock["push_clock_trace"][:prefix_rows]
                            == pulse["push_clock_trace"][:prefix_rows],
    }
    lag_values = {mode: sorted({row["leg_delay_substeps"] for row in report["push_clock_trace"]})
                  for mode, report in reports.items()}
    observed_lag = protocol["mechanism_hypothesis_from_seen_runs"][f"{seed}_leg_delay_substeps"]
    lag_matches_hypothesis = all(values == [observed_lag] for values in lag_values.values())
    pair_has_same_fixed_lag = (len(lag_values["actuator_clock"]) == 1
                               and lag_values["actuator_clock"] == lag_values["actuator_pulse"])
    qualified = (all(all(value for key, value in check.items()
                         if key != "stage_export_sha256_matches")
                     for check in reproducibility.values())
                 and all(prefix_matches.values()) and pair_has_same_fixed_lag)
    result = {
        "seed": seed,
        "pulse_control_step": pulse_step,
        "raw_report_sha256": hashes,
        "outcomes": {mode: report["outcome"] for mode, report in reports.items()},
        "terminal_reasons": {mode: [name for name, value in report["terminal"].get(
            "reasons", {}).items() if value] for mode, report in reports.items()},
        "prior_report_reproducibility": reproducibility,
        "recorded_prefix_matches": prefix_matches,
        "leg_delay_substeps": lag_values,
        "pair_has_same_fixed_lag": pair_has_same_fixed_lag,
        "lag_matches_seen_run_hypothesis": lag_matches_hypothesis,
        "recorded_mechanism_qualified": qualified,
        "full_hidden_state_coupling_proven": False,
    }
    if qualified:
        joint_names = clock["joint_names"]
        fields = {
            "first_target_difference": "joint_target_before_sim",
            "first_computed_torque_difference": "computed_torque_before_sim",
            "first_applied_torque_difference": "applied_torque_before_sim",
            "first_joint_position_difference": "joint_pos_after_update",
        }
        for output_key, field in fields.items():
            result[output_key] = first_difference(
                clock["push_clock_trace"], pulse["push_clock_trace"], field, joint_names
            )
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
    if protocol["seeds"] != [6403, 6415] or protocol["run_denominator"] != 4:
        raise ValueError("Unexpected frozen actuator-clock protocol")
    if sha256(args.prior_audit) != protocol["source_sha256"]["previous_audit"]:
        raise ValueError("Prior audit hash differs from frozen protocol")
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
