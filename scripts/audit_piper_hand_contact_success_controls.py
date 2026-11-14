"""Audit seen successful rollouts for hand events hidden between control checks."""

import argparse
import hashlib
import json
import math
from pathlib import Path

from audit_piper_invalid_hand_contact_detail import contact_conditions


MATCHED_FIELDS = (
    "initial_state", "trace", "approach_transitions", "handoff", "support_trace",
    "outcome", "push_executed_steps", "push_elapsed_s", "terminal_telemetry", "terminal",
)


def file_sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def classify(row, physics_dt_s):
    detail = row["hand_contact"]
    force = detail["force_norm_n"]
    if not math.isfinite(force) or force < 0:
        raise ValueError("Invalid hand sensor force")
    if force <= 1.0:
        return None
    conditions = contact_conditions(detail)
    failed = [key for key, value in conditions.items()
              if key != "force_above_invalid_threshold" and not value]
    return {
        "push_elapsed_s": ((row["push_control_step"] - 1) * 4
                           + row["physics_substep"]) * physics_dt_s,
        "push_control_step": row["push_control_step"],
        "physics_substep": row["physics_substep"],
        "force_norm_n": force,
        "contact_pos_box_m": detail["contact_pos_box_m"],
        "failed_legal_conditions": failed,
        "arm_approach_index": row["arm_approach_index"],
        "motion_ready": row["motion_ready"],
    }


def audit(protocol_path, diagnostic_path, reference_dir, report_dir):
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    if file_sha256(diagnostic_path) != protocol["diagnostic_sha256"]:
        raise ValueError("Frozen diagnostic hash differs")
    seeds = protocol["seeds_in_order"]
    if seeds != [5901, 5902, 5903]:
        raise ValueError("Unexpected seen-control denominator")
    if ({path.name for path in report_dir.glob("seed*.json")}
            != {f"seed{seed}.json" for seed in seeds}
            or {path.name for path in report_dir.glob("seed*.log")}
            != {f"seed{seed}.log" for seed in seeds}):
        raise ValueError("New report or log set differs from the frozen denominator")
    records = []
    control = protocol["control"]
    for seed in seeds:
        reference_path = reference_dir / f"seed{seed}.json"
        report_path = report_dir / f"seed{seed}.json"
        log_path = report_dir / f"seed{seed}.log"
        if (file_sha256(reference_path) != protocol["reference_report_sha256"][str(seed)]
                or not log_path.stat().st_size):
            raise ValueError(f"Frozen reference hash or log differs for seed{seed}")
        reference = json.loads(reference_path.read_text(encoding="utf-8"))
        report = json.loads(report_path.read_text(encoding="utf-8"))
        if (reference["schema_version"] != 23 or report["schema_version"] != 25
                or report["seed"] != seed or reference["seed"] != seed
                or report["nav_actor_sha256"] != protocol["nav_actor_sha256"]
                or report["push_checkpoint_sha256"] != protocol["push_checkpoint_sha256"]
                or report["control_sha256"] != reference["control_sha256"]
                or report["nav_start_x_m"] != control["nav_start_x_m"]
                or report["nav_goal_xyyaw"] != [control["nav_goal_x_m"], 0.0, 0.0]
                or report["nav_arm_home"] is not control["nav_arm_home"]
                or report["nav_timeout_s"] != control["nav_timeout_s"]
                or report["push_budget_s"] != control["push_budget_s"]
                or report["step_dt"] != control["control_dt_s"]
                or any(report[key] is not value for key, value in control.items()
                       if key.startswith("record_"))):
            raise ValueError(f"Frozen input or control differs for seed{seed}")
        if any(report[key] != reference[key] for key in MATCHED_FIELDS):
            raise ValueError(f"Observed rollout differs from reference for seed{seed}")
        if (report["outcome"] != "push_terminated"
                or not report["terminal"]["reasons"]["box_settled"]
                or report["terminal"]["reasons"]["invalid_hand_contact"]):
            raise ValueError(f"Seen success-control outcome differs for seed{seed}")
        contract = report["hand_contact_substep_contract"]
        if (contract["physics_dt_s"] != control["physics_dt_s"]
                or contract["control_decimation"] != 4
                or contract["sensor"] != "box_contact_hand"):
            raise ValueError(f"Unexpected substep sensor contract for seed{seed}")
        rows = report["hand_contact_substeps"]
        if len(rows) != 4 * report["push_executed_steps"]:
            raise ValueError(f"Missing PUSH physics substeps for seed{seed}")
        events = []
        hidden_steps = []
        for index, row in enumerate(rows):
            step, substep = divmod(index, 4)
            if row["push_control_step"] != step + 1 or row["physics_substep"] != substep + 1:
                raise ValueError(f"Substep time order differs for seed{seed}")
            event = classify(row, control["physics_dt_s"])
            if event is not None:
                events.append(event)
        for step in range(report["push_executed_steps"]):
            samples = [event for event in events if event["push_control_step"] == step + 1]
            if (any(event["failed_legal_conditions"] for event in samples)
                    and not any(event["physics_substep"] == 4
                                and event["failed_legal_conditions"] for event in samples)):
                hidden_steps.append(step + 1)
        illegal = [event for event in events if event["failed_legal_conditions"]]
        records.append({
            "seed": seed,
            "reference_report_sha256": file_sha256(reference_path),
            "report_sha256": file_sha256(report_path),
            "log_sha256": file_sha256(log_path),
            "outcome": report["outcome"],
            "physics_substeps": len(rows),
            "force_above_1_n_samples": len(events),
            "illegal_hand_samples": len(illegal),
            "substep_only_illegal_control_steps": hidden_steps,
            "first_illegal_event": illegal[0] if illegal else None,
            "max_illegal_force_n": max((event["force_norm_n"] for event in illegal), default=None),
        })
    return {
        "schema_version": 1,
        "scope": "seen_box_settled_controls_read_only_hand_substep_audit",
        "protocol_sha256": file_sha256(protocol_path),
        "diagnostic_sha256": file_sha256(diagnostic_path),
        "complete_denominator": len(records),
        "records": records,
        "scene_contract_sha256": None,
        "entry_distribution_sha256": None,
        "contact_authorized": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol-json", type=Path, required=True)
    parser.add_argument("--diagnostic", type=Path, required=True)
    parser.add_argument("--reference-dir", type=Path, required=True)
    parser.add_argument("--report-dir", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.protocol_json, args.diagnostic, args.reference_dir, args.report_dir)
    with args.output_json.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"complete_denominator": result["complete_denominator"],
                      "illegal_hand_samples": [record["illegal_hand_samples"]
                                               for record in result["records"]]}))


if __name__ == "__main__":
    main()
