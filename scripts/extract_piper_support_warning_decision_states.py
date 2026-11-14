"""Inventory decision-time observables at six previously identified PUSH warnings."""

import argparse
import hashlib
import json
import math
from pathlib import Path


SEEDS = (5701, 5703, 5712, 5716, 5717, 5723)
KNOWN_PAIR = {5703, 5712}


def load(path):
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return json.loads(path.read_text(encoding="utf-8")), digest


def warning_index(report):
    names = report["support_foot_body_names"]
    rear = (names.index("RL_foot"), names.index("RR_foot"))
    consecutive = 0
    for index, item in enumerate(report["support_trace"]):
        active = (not item["motion_ready"] and item["base_pos"][2] < 0.27
                  and any(item["foot_normal_forces_n"][foot] < 2.0 for foot in rear))
        consecutive = consecutive + 1 if active else 0
        if consecutive == 5:
            return index
    raise ValueError(f"Seed{report['seed']} did not meet the frozen warning")


def pitch(quaternion):
    w, x, y, z = quaternion
    return math.asin(max(-1.0, min(1.0, 2.0 * (w * y - z * x))))


def inventory(report):
    index = warning_index(report)
    item = report["support_trace"][index]
    physical = item["recovery_decision_state"]
    names = report["support_foot_body_names"]
    forces = item["foot_normal_forces_n"]
    positive = [max(0.0, force) for force in forces]
    rear = sum(positive[names.index(f"{leg}_foot")] for leg in ("RL", "RR"))
    leg_joint_ids = [report["joint_names"].index(f"{leg}_{joint}_joint")
                     for leg in ("FL", "FR", "RL", "RR")
                     for joint in ("hip", "thigh", "calf")]
    if (report["schema_version"] != 18 or report["step_dt"] != 0.02
            or len(report["support_trace"]) != report["push_executed_steps"]
            or len(physical["actor_input_before_action"]) != 226
            or len(physical["actor_action_before_step"]) != 12):
        raise ValueError(f"Seed{report['seed']} invalid decision trace")
    features = {
        "push_elapsed_s": item["push_elapsed_s"],
        "remaining_push_budget_s": report["push_budget_s"] - item["push_elapsed_s"],
        "base_height_m": item["base_pos"][2],
        "base_pitch_rad": pitch(item["base_quat"]),
        "base_vz_w_m_s": physical["base_vel_w"][2],
        "base_omega_y_w_rad_s": physical["base_omega_w"][1],
        "foot_normal_forces_n": forces,
        "rear_positive_force_share": rear / sum(positive) if sum(positive) > 0.0 else None,
        "supported_feet_gt_2n": item["supported_feet_gt_2n"],
        "arm_approach_index": item["arm_approach_index"],
        "motion_ready": item["motion_ready"],
        "maximum_leg_target_tracking_error_rad": max(
            abs(item["joint_pos_target"][joint] - item["joint_pos"][joint])
            for joint in leg_joint_ids
        ),
    }
    if not all(math.isfinite(value) for value in features.values()
               if isinstance(value, (int, float))):
        raise ValueError(f"Seed{report['seed']} non-finite warning feature")
    reasons = report["terminal"].get("reasons", {})
    positive_reasons = [name for name, active in reasons.items() if active]
    return {
        "seed": report["seed"],
        "warning_trace_index": index,
        "warning_features": features,
        "later_outcome_label": {
            "outcome": report["outcome"],
            "terminal_reasons": positive_reasons,
            "push_elapsed_s": report["push_elapsed_s"],
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--known-pair-dir", type=Path, required=True)
    parser.add_argument("--remaining-dir", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error("Output file exists")
    rows = []
    for seed in SEEDS:
        directory = args.known_pair_dir if seed in KNOWN_PAIR else args.remaining_dir
        report, report_sha = load(directory / f"seed{seed}-decision-state.json")
        audit, audit_sha = load(directory / f"seed{seed}-decision-state-audit.json")
        if (report["seed"] != seed or audit["seed"] != seed
                or audit["candidate_sha256"] != report_sha
                or audit["old_report_fields_equal"] is not True):
            raise ValueError(f"Seed{seed} decision-state audit failed")
        row = inventory(report)
        row["report_sha256"] = report_sha
        row["audit_sha256"] = audit_sha
        rows.append(row)
    result = {
        "schema_version": 1,
        "scope": "All six previously inspected support warnings; observable-state inventory, not a trained or tested predictor",
        "analysis_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "rows": rows,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
    print(json.dumps([{"seed": row["seed"], **row["warning_features"],
                       "later_outcome_label": row["later_outcome_label"]["terminal_reasons"]}
                      for row in rows], indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
