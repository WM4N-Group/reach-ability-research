"""Extract only quantities available at the old support trigger's decision step."""

import argparse
import json
import math
from pathlib import Path

from audit_piper_nav_push_baseline_cohort import sha256


FEET = ("FL_foot", "FR_foot", "RL_foot", "RR_foot")


def pitch(quat):
    w, x, y, z = quat
    return math.asin(max(-1.0, min(1.0, 2.0 * (w * y - z * x))))


def extract(record, names, remaining_s, earlier):
    forces = dict(zip(names, record["foot_normal_forces_n"]))
    positive = {name: max(forces[name], 0.0) for name in FEET}
    total = sum(positive.values())
    if total < 20.0:
        raise ValueError("Warning-time foot-force input is unqualified")
    for foot in FEET:
        contact = record["ground_contacts"][foot]
        if abs(contact["ground_normal_force"][2] - forces[foot]) > 1e-3:
            raise ValueError(f"Warning-time ground force differs: {foot}")
        if forces[foot] > 2.0 and (contact["ground_contact_pos"] is None
                                   or not all(math.isfinite(x) for x in contact["ground_contact_pos"])):
            raise ValueError(f"Warning-time loaded foot lacks ground point: {foot}")
    current_pitch = pitch(record["base_quat"])
    features = {
        "push_elapsed_s": record["push_elapsed_s"],
        "remaining_push_budget_s": remaining_s,
        "base_height_m": record["base_pos"][2],
        "base_pitch_rad": current_pitch,
        "pitch_change_over_previous_0p2_s_rad": current_pitch - pitch(earlier["base_quat"]),
        "foot_normal_forces_n": forces,
        "rear_positive_normal_force_fraction": (positive["RL_foot"] + positive["RR_foot"]) / total,
        "supported_feet_gt_2n": record["supported_feet_gt_2n"],
        "arm_approach_index": record["arm_approach_index"],
        "motion_ready": record["motion_ready"],
        "maximum_leg_joint_target_error_rad": max(
            record["leg_jacobians"][foot]["maximum_joint_target_error_rad"] for foot in FEET
        ),
    }
    if not all(math.isfinite(value) for value in (
            features["remaining_push_budget_s"], features["base_height_m"], current_pitch,
            features["pitch_change_over_previous_0p2_s_rad"],
            features["rear_positive_normal_force_fraction"],
            features["maximum_leg_joint_target_error_rad"])):
        raise ValueError("Nonfinite warning-time feature")
    return features


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replay-json", type=Path, required=True)
    parser.add_argument("--reports-dir", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error("Output file already exists")
    replay = json.loads(args.replay_json.read_text(encoding="utf-8"))
    if len(replay["cases"]) != 24:
        raise ValueError("Incomplete replay denominator")
    cases = []
    for case in replay["cases"]:
        path = args.reports_dir / f"seed{case['seed']}-baseline.json"
        if sha256(path) != case["report_sha256"]:
            raise ValueError(f"Seed{case['seed']} raw report differs")
        state = None
        if case["trigger"] is not None:
            report = json.loads(path.read_text(encoding="utf-8"))
            time_s = case["trigger"]["confirmed_at_push_s"]
            index = round(time_s / report["step_dt"]) - 1
            trace = report["support_trace"]
            if index < 10 or index >= len(trace) or abs(trace[index]["push_elapsed_s"] - time_s) > 1e-8:
                raise ValueError(f"Seed{case['seed']} warning sample does not align")
            state = extract(trace[index], report["support_foot_body_names"],
                            report["push_budget_s"] - time_s, trace[index - 10])
        cases.append({
            "seed": case["seed"],
            "category": case["category"],
            "report_sha256": case["report_sha256"],
            "warning_state": state,
        })
    result = {
        "schema_version": 1,
        "analysis_sha256": sha256(Path(__file__)),
        "replay_sha256": sha256(args.replay_json),
        "total_runs": len(cases),
        "warning_states": sum(case["warning_state"] is not None for case in cases),
        "cases": cases,
        "unobserved_restart_state": [
            "exact base linear and angular velocity at the control step",
            "NAV and PUSH policy observation/action histories",
            "arm IK, legal-contact and termination-monitor memory",
            "full physical contact state and solver memory"
        ],
        "scope": "Post-outcome descriptive decision-step projection only. Pitch change is a 0.2-s finite difference, not measured angular velocity. These records cannot restart an exact counterfactual rollout, certify reachability, or authorize contact."
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
    print(f"runs={result['total_runs']} warning_states={result['warning_states']}")


if __name__ == "__main__":
    main()
