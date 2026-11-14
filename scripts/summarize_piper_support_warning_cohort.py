"""Audit the complete-denominator 5801-5824 read-only warning cohort."""

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path

from extract_piper_support_warning_decision_states import inventory


SEEDS = tuple(range(5801, 5825))
PROTOCOL_SHA256 = "7dc46f300224453ec2a11e464a794e0394ec1f8e51258b0a5774616a23b1891a"
DIAGNOSTIC_SHA256 = "944533f0069ae944a7f0203b2ab88e8f776f5169353af2f91789a8e1f7974e0b"
NAV_SHA256 = "72d9f22c633081e8d4b9693e6fda54dba6cdd036a102f330c1bfe096e43b4da8"
PUSH_SHA256 = "b1ebb8abb5370dcd98debab85d70e05a004bb1e59b5b00710460f575174c7721"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def finite_vector(values, length):
    return len(values) == length and all(math.isfinite(value) for value in values)


def first_warning(trace, names):
    rear = (names.index("RL_foot"), names.index("RR_foot"))
    consecutive = 0
    for index, item in enumerate(trace):
        active = (not item["motion_ready"] and item["base_pos"][2] < 0.27
                  and any(item["foot_normal_forces_n"][foot] < 2.0 for foot in rear))
        consecutive = consecutive + 1 if active else 0
        if consecutive == 5:
            return index
    return None


def check_trace(report):
    trace = report["support_trace"]
    names = report["support_foot_body_names"]
    if (len(trace) != report["push_executed_steps"] or len(names) != 4
            or set(names) != {"FL_foot", "FR_foot", "RL_foot", "RR_foot"}):
        raise ValueError(f"Seed{report['seed']} invalid PUSH trace layout")
    previous_next_input = None
    sensor_errors = {name: 0.0 for name in names}
    loaded = {name: 0 for name in names}
    finite_loaded = {name: 0 for name in names}
    for index, item in enumerate(trace):
        if abs(item["push_elapsed_s"] - (index + 1) * 0.02) > 1e-8:
            raise ValueError(f"Seed{report['seed']} misaligned step {index}")
        state = item["recovery_decision_state"]
        if (not finite_vector(state["base_vel_w"], 3)
                or not finite_vector(state["base_omega_w"], 3)
                or not finite_vector(state["box_vel_w"], 3)
                or not finite_vector(state["box_omega_w"], 3)
                or not finite_vector(state["actor_input_before_action"], 226)
                or not finite_vector(state["actor_action_before_step"], 12)
                or state["arm_controller"]["safe_approach_index"] != item["arm_approach_index"]
                or state["arm_controller"]["motion_ready"] != item["motion_ready"]
                or state["arm_controller"]["reference"] != item["arm_reference"]):
            raise ValueError(f"Seed{report['seed']} invalid decision state {index}")
        if previous_next_input is not None and previous_next_input != state["actor_input_before_action"]:
            raise ValueError(f"Seed{report['seed']} actor history differs at {index}")
        previous_next_input = state["next_actor_input"]
        if index + 1 < len(trace) and not finite_vector(previous_next_input, 226):
            raise ValueError(f"Seed{report['seed']} missing next actor input at {index}")
        for foot_index, name in enumerate(names):
            contact = item["ground_contacts"][name]
            force = contact["ground_normal_force"][2]
            sensor_errors[name] = max(sensor_errors[name], abs(force - item["foot_normal_forces_n"][foot_index]))
            if force > 2.0:
                loaded[name] += 1
                if contact["ground_contact_pos"] is not None and finite_vector(contact["ground_contact_pos"], 3):
                    finite_loaded[name] += 1
    sensor_qualified = all(
        loaded[name] > 0 and finite_loaded[name] / loaded[name] >= 0.95
        and sensor_errors[name] < 1e-3 for name in names
    )
    return {
        "decision_steps": len(trace),
        "sensor_qualified": sensor_qualified,
        "loaded_ground_contact_fraction": {name: finite_loaded[name] / loaded[name]
                                           if loaded[name] else None for name in names},
        "max_abs_ground_vs_net_force_error_n": sensor_errors,
    }


def classify(report):
    if report["outcome"] == "nav_timeout":
        return "nav_timeout"
    if report["outcome"] == "push_budget_exhausted":
        return "push_budget_exhausted"
    reasons = [key for key, active in report["terminal"].get("reasons", {}).items() if active]
    if report["outcome"] == "push_terminated" and len(reasons) == 1:
        return reasons[0]
    return "other_" + report["outcome"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--diagnostic-source", type=Path, required=True)
    parser.add_argument("--report-dir", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error("Output file exists")
    if sha256(args.protocol) != PROTOCOL_SHA256 or sha256(args.diagnostic_source) != DIAGNOSTIC_SHA256:
        raise ValueError("Frozen protocol or diagnostic differs")
    rows = []
    reference_control = None
    for seed in SEEDS:
        path = args.report_dir / f"seed{seed}-baseline.json"
        report = json.loads(path.read_text(encoding="utf-8"))
        if (report["seed"] != seed or report["schema_version"] != 18
                or report["nav_actor_sha256"] != NAV_SHA256
                or report["push_checkpoint_sha256"] != PUSH_SHA256
                or not report["record_recovery_decision_state"]
                or not report["record_push_contact_load_trace"]
                or not report["record_leg_jacobian_trace"]
                or not report["record_base_contact_source"]
                or report["support_response_probe"] is not None
                or report["nav_start_x_m"] != -0.25
                or report["nav_goal_xyyaw"] != [-0.05, 0.0, 0.0]
                or report["push_budget_s"] != 12.0 or report["step_dt"] != 0.02):
            raise ValueError(f"Seed{seed} source or control contract differs")
        if reference_control is None:
            reference_control = report["control_sha256"]
        elif report["control_sha256"] != reference_control:
            raise ValueError(f"Seed{seed} control source differs")
        result = check_trace(report)
        label = classify(report)
        warning = first_warning(report["support_trace"], report["support_foot_body_names"])
        row = {
            "seed": seed,
            "report_sha256": sha256(path),
            "outcome_label": label,
            "push_elapsed_s": report["push_elapsed_s"],
            **result,
            "warning": inventory(report)["warning_features"] if warning is not None else None,
        }
        rows.append(row)
    output = {
        "schema_version": 1,
        "scope": "New seeds in one fixed scene; no-intervention calibration inventory, no fitted threshold or contact certificate",
        "analysis_sha256": sha256(Path(__file__)),
        "protocol_sha256": PROTOCOL_SHA256,
        "diagnostic_sha256": DIAGNOSTIC_SHA256,
        "control_sha256": reference_control,
        "outcome_counts": dict(Counter(row["outcome_label"] for row in rows)),
        "warning_count": sum(row["warning"] is not None for row in rows),
        "warning_by_later_outcome": dict(Counter(row["outcome_label"] for row in rows if row["warning"] is not None)),
        "qualified_push_count": sum(row["decision_steps"] > 0 and row["sensor_qualified"] for row in rows),
        "rows": rows,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x", encoding="utf-8") as stream:
        json.dump(output, stream, indent=2, allow_nan=False)
    print(json.dumps({key: output[key] for key in (
        "outcome_counts", "warning_count", "warning_by_later_outcome", "qualified_push_count"
    )}, indent=2))


if __name__ == "__main__":
    main()
