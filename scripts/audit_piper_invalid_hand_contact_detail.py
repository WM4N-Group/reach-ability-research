"""Audit a seen-seed terminal hand contact snapshot against its frozen rollout."""

import argparse
import hashlib
import json
from pathlib import Path


MATCHED_FIELDS = (
    "initial_state", "trace", "approach_transitions", "handoff", "support_trace",
    "outcome", "push_executed_steps", "push_elapsed_s", "terminal_telemetry",
)


def file_sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def contact_conditions(detail):
    local = detail["contact_pos_box_m"]
    force = detail["force_norm_n"]
    resisting = detail["resisting_force_n"]
    size = detail["box_size_m"]
    return {
        "force_above_invalid_threshold": force > 1.0,
        "finite_contact_point": local is not None,
        "near_hand_tip": (detail["contact_to_hand_m"] is not None
                          and detail["contact_to_hand_m"] < detail["tip_radius_limit_m"]),
        "resisting_force_above_1_n": resisting > 1.0,
        "resisting_fraction_above_0_8": resisting > 0.8 * force,
        "front_face_within_20_mm": local is not None and abs(local[0] + size[0] / 2.0) < 0.02,
        "within_lateral_half_width": local is not None and abs(local[1]) < size[1] / 2.0,
        "within_height_margin": (local is not None and abs(local[2])
                                 <= size[2] / 2.0 - detail["height_margin_m"] + 1.0e-4),
    }


def audit(protocol_path, diagnostic_path, baseline_path, report_path, log_path):
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    if file_sha256(diagnostic_path) != protocol["diagnostic_sha256"]:
        raise ValueError("Diagnostic source hash differs")
    if file_sha256(baseline_path) != protocol["baseline_report_sha256"]:
        raise ValueError("Frozen baseline report hash differs")
    if not log_path.stat().st_size:
        raise ValueError("Remote run log is empty")
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    report = json.loads(report_path.read_text(encoding="utf-8"))
    control = protocol["control"]
    if (baseline["schema_version"] != 23 or report["schema_version"] != 24
            or baseline["seed"] != report["seed"] or report["seed"] != protocol["seed"]
            or report["nav_actor_sha256"] != protocol["nav_actor_sha256"]
            or report["push_checkpoint_sha256"] != protocol["push_checkpoint_sha256"]
            or report["nav_start_x_m"] != control["nav_start_x_m"]
            or report["nav_goal_xyyaw"] != [control["nav_goal_x_m"], 0.0, 0.0]
            or report["nav_arm_home"] is not control["nav_arm_home"]
            or report["nav_timeout_s"] != control["nav_timeout_s"]
            or report["push_budget_s"] != control["push_budget_s"]
            or any(report[key] is not value for key, value in control.items()
                   if key.startswith("record_"))):
        raise ValueError("Frozen input or control differs")
    if any(report[key] != baseline[key] for key in MATCHED_FIELDS):
        raise ValueError("Observed rollout differs from the frozen baseline")
    terminal = dict(report["terminal"])
    detail = terminal.pop("invalid_hand_contact_detail", None)
    if terminal != baseline["terminal"] or detail is None:
        raise ValueError("Terminal state differs or hand contact detail is missing")
    conditions = contact_conditions(detail)
    if (not terminal["reasons"].get("invalid_hand_contact")
            or not conditions["force_above_invalid_threshold"]
            or all(value for key, value in conditions.items()
                   if key != "force_above_invalid_threshold")):
        raise ValueError("Recorded contact does not reproduce invalid_hand_contact")
    return {
        "schema_version": 1,
        "scope": "seen_seed_read_only_terminal_contact_decomposition",
        "protocol_sha256": file_sha256(protocol_path),
        "diagnostic_sha256": file_sha256(diagnostic_path),
        "baseline_report_sha256": file_sha256(baseline_path),
        "report_sha256": file_sha256(report_path),
        "log_sha256": file_sha256(log_path),
        "seed": report["seed"],
        "matched_fields": list(MATCHED_FIELDS) + ["terminal_except_contact_detail"],
        "conditions": conditions,
        "failed_legal_contact_conditions": [key for key, value in conditions.items()
                                            if key != "force_above_invalid_threshold" and not value],
        "detail": detail,
        "scene_contract_sha256": None,
        "entry_distribution_sha256": None,
        "contact_authorized": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol-json", type=Path, required=True)
    parser.add_argument("--diagnostic", type=Path, required=True)
    parser.add_argument("--baseline-json", type=Path, required=True)
    parser.add_argument("--report-json", type=Path, required=True)
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.protocol_json, args.diagnostic, args.baseline_json,
                   args.report_json, args.log)
    with args.output_json.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"seed": result["seed"],
                      "failed_legal_contact_conditions": result["failed_legal_contact_conditions"]}))


if __name__ == "__main__":
    main()
