"""Audit a seen-seed hand-contact substep trace against its frozen rollout."""

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mujoco"))
from reconfigurable_navigation.reachability.contact_mode import (  # noqa: E402
    FrontContactGeometry,
    classify_front_contact_geometry,
)


MATCHED_FIELDS = (
    "initial_state", "trace", "approach_transitions", "handoff", "support_trace",
    "outcome", "push_executed_steps", "push_elapsed_s", "terminal_telemetry", "terminal",
)


def file_sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(protocol_path, diagnostic_path, reference_path, report_path, log_path):
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    if (file_sha256(diagnostic_path) != protocol["diagnostic_sha256"]
            or file_sha256(reference_path) != protocol["reference_report_sha256"]
            or not log_path.stat().st_size):
        raise ValueError("Frozen source/reference hash differs or run log is empty")
    reference = json.loads(reference_path.read_text(encoding="utf-8"))
    report = json.loads(report_path.read_text(encoding="utf-8"))
    control = protocol["control"]
    if (reference["schema_version"] != 24 or report["schema_version"] != 25
            or reference["seed"] != report["seed"] or report["seed"] != protocol["seed"]
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
        raise ValueError("Frozen input, control or diagnostic schema differs")
    if any(report[key] != reference[key] for key in MATCHED_FIELDS):
        raise ValueError("Instrumented rollout differs from the frozen reference")

    contract = report["hand_contact_substep_contract"]
    if (contract["physics_dt_s"] != control["physics_dt_s"]
            or contract["control_decimation"] != 4
            or contract["sensor"] != "box_contact_hand"
            or contract["sample_phase"] != "after_scene_update_before_control_step_termination"):
        raise ValueError("Unexpected hand sensor sampling contract")
    rows = report["hand_contact_substeps"]
    if len(rows) != report["push_executed_steps"] * 4:
        raise ValueError("Missing or duplicate PUSH physics substeps")
    if rows[-1]["hand_contact"] != report["terminal"]["invalid_hand_contact_detail"]:
        raise ValueError("Last hand sensor sample is not the terminal sensor sample")
    geometry = FrontContactGeometry(
        tuple(rows[-1]["hand_contact"]["box_size_m"]),
        rows[-1]["hand_contact"]["height_margin_m"],
    )
    events = []
    for index, row in enumerate(rows):
        step, substep = divmod(index, 4)
        if row["push_control_step"] != step + 1 or row["physics_substep"] != substep + 1:
            raise ValueError("Hand substep order differs from the control clock")
        detail = row["hand_contact"]
        force = detail["force_w_n"]
        if (len(force) != 3 or not all(math.isfinite(value) for value in force)
                or not math.isclose(math.sqrt(sum(value * value for value in force)),
                                    detail["force_norm_n"], rel_tol=1e-6, abs_tol=1e-5)
                or len(row["hand_body_origin_box_m"]) != 3
                or not all(math.isfinite(value) for value in row["hand_body_origin_box_m"])):
            raise ValueError("Non-finite or inconsistent hand sample")
        if detail["force_norm_n"] <= 1.0:
            continue
        local = detail["contact_pos_box_m"]
        classification = classify_front_contact_geometry(
            geometry, contact_observed=True,
            contact_point_box_m=tuple(local) if local is not None else None,
            local_position_error_bound_m=0.0,
        )
        events.append({
            "push_elapsed_s": (step * 4 + substep + 1) * control["physics_dt_s"],
            "push_control_step": step + 1,
            "physics_substep": substep + 1,
            "force_norm_n": detail["force_norm_n"],
            "contact_pos_box_m": local,
            "nominal_geometry_state": classification.state,
            "nominal_margins_m": classification.nominal_margins_m,
            "arm_approach_index": row["arm_approach_index"],
            "motion_ready": row["motion_ready"],
            "foot_normal_forces_n": row["foot_normal_forces_n"],
            "hand_body_origin_box_m": row["hand_body_origin_box_m"],
        })
    if not events or events[-1]["nominal_geometry_state"] != "outside_geometry_for_all_positions":
        raise ValueError("Terminal invalid hand contact was not observed in the substep trace")
    return {
        "schema_version": 1,
        "scope": "seen_seed_read_only_hand_contact_substep_mechanism",
        "protocol_sha256": file_sha256(protocol_path),
        "diagnostic_sha256": file_sha256(diagnostic_path),
        "reference_report_sha256": file_sha256(reference_path),
        "report_sha256": file_sha256(report_path),
        "log_sha256": file_sha256(log_path),
        "seed": report["seed"],
        "matched_fields": list(MATCHED_FIELDS),
        "physics_substeps": len(rows),
        "force_above_1_n_samples": len(events),
        "events": events,
        "scene_contract_sha256": None,
        "entry_distribution_sha256": None,
        "contact_authorized": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol-json", type=Path, required=True)
    parser.add_argument("--diagnostic", type=Path, required=True)
    parser.add_argument("--reference-json", type=Path, required=True)
    parser.add_argument("--report-json", type=Path, required=True)
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.protocol_json, args.diagnostic, args.reference_json,
                   args.report_json, args.log)
    with args.output_json.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"seed": result["seed"],
                      "physics_substeps": result["physics_substeps"],
                      "force_above_1_n_samples": result["force_above_1_n_samples"]}))


if __name__ == "__main__":
    main()
