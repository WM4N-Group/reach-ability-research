"""Audit paired Isaac control-clock runs without granting contact authority."""

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def first_vector_change(reference, candidate, key, joint_names, tolerance=1e-10):
    for index, (left, right) in enumerate(zip(reference, candidate, strict=True)):
        differences = [abs(a - b) for a, b in zip(left[key], right[key], strict=True)]
        difference = max(differences)
        if difference > tolerance:
            joint_index = differences.index(difference)
            return {
                "control_step": left["push_control_step"],
                "physics_substep": left["physics_substep"],
                "max_abs_difference": difference,
                "max_difference_joint": joint_names[joint_index],
                "flat_substep_index": index + 1,
            }
    return None


def audit_seed(root, frozen_root, seed, pulse_step):
    paths = {mode: root / f"seed{seed}-{mode}.json" for mode in ("plain", "clock", "pulse")}
    paths["frozen"] = frozen_root / f"seed{seed}-plus012.json"
    reports = {mode: load(path) for mode, path in paths.items()}
    plain, clock, pulse, frozen = (reports[mode] for mode in ("plain", "clock", "pulse", "frozen"))
    common = ("outcome", "terminal", "push_executed_steps", "handoff", "trace",
              "approach_transitions", "support_trace", "hand_contact_substeps")
    instrument_matches = {key: plain.get(key) == clock.get(key) for key in common}
    historical_matches = {key: frozen.get(key) == plain.get(key) for key in common}
    prefix_rows = (pulse_step - 1) * 4
    prefix_matches = {
        "handoff": clock["handoff"] == pulse["handoff"],
        "hand_contact_substeps": (
            clock["hand_contact_substeps"][:prefix_rows]
            == pulse["hand_contact_substeps"][:prefix_rows]
        ),
        "support_trace": clock["support_trace"][:pulse_step - 1]
                         == pulse["support_trace"][:pulse_step - 1],
        "push_clock_trace": clock["push_clock_trace"][:prefix_rows]
                            == pulse["push_clock_trace"][:prefix_rows],
        "push_clock_actions": clock["push_clock_actions"][:pulse_step - 1]
                              == pulse["push_clock_actions"][:pulse_step - 1],
    }
    pulse_action = pulse["push_clock_actions"][pulse_step - 1]
    clock_action = clock["push_clock_actions"][pulse_step - 1]
    action_delta = [a - b for a, b in zip(
        pulse_action["routed_leg_action"], clock_action["routed_leg_action"], strict=True
    )]
    pulse_applied = (
        pulse_action["actor_action"] == clock_action["actor_action"]
        and abs(action_delta[0] - 0.05) < 1e-6
        and all(abs(value) < 1e-6 for value in action_delta[1:])
    )
    qualified = (all(historical_matches.values()) and all(instrument_matches.values())
                 and all(prefix_matches.values()) and pulse_applied)
    result = {
        "seed": seed,
        "pulse_control_step": pulse_step,
        "raw_report_sha256": {mode: sha256(path) for mode, path in paths.items()},
        "outcomes": {mode: reports[mode]["outcome"] for mode in reports},
        "terminal_reasons": {mode: [name for name, value in reports[mode]["terminal"].get(
            "reasons", {}).items() if value] for mode in reports},
        "instrument_matches": instrument_matches,
        "historical_matches": historical_matches,
        "pulse_prefix_matches": prefix_matches,
        "pulse_action_applied": pulse_applied,
        "recorded_prefix_qualified": qualified,
        "full_hidden_state_coupling_proven": False,
        "first_target_divergence": None,
        "first_joint_position_divergence": None,
    }
    if qualified:
        result["first_target_divergence"] = first_vector_change(
            clock["push_clock_trace"], pulse["push_clock_trace"], "joint_target_before_sim",
            clock["joint_names"]
        )
        result["first_joint_position_divergence"] = first_vector_change(
            clock["push_clock_trace"], pulse["push_clock_trace"], "joint_pos_after_update",
            clock["joint_names"]
        )
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--frozen-run-dir", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error("Output already exists")
    protocol = load(args.protocol)
    if protocol["run_denominator"] != 6 or protocol["seeds"] != [6403, 6415]:
        raise ValueError("Unexpected frozen clock-probe cohort")
    result = {
        "schema_version": 1,
        "protocol_sha256": sha256(args.protocol),
        "analysis_script_sha256": sha256(Path(__file__)),
        "scope": protocol["scope"],
        "run_denominator": 6,
        "contact_authorized": False,
        "universal_effect_delay_bound_established": False,
        "records": [audit_seed(args.run_dir, args.frozen_run_dir, seed,
                               protocol["pulse_control_steps"][str(seed)])
                    for seed in protocol["seeds"]],
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"recorded_prefix_qualified": sum(
        item["recorded_prefix_qualified"] for item in result["records"]),
                      "total": len(result["records"])}))


if __name__ == "__main__":
    main()
