"""Retrospective control-clock projection of loaded hand height margins."""

import argparse
import json
import math
from pathlib import Path

from audit_piper_hand_contact_success_controls import classify, file_sha256


def project(report, phase_record, cohort_record):
    rows = report["hand_contact_substeps"]
    dt = report["scene_runtime_observation"]["physics_dt_s"]
    if (report["schema_version"] != 26 or dt != 0.005
            or len(rows) != 4 * report["push_executed_steps"]
            or len(rows) != phase_record["push_physics_substeps"]
            or len(rows) != cohort_record["push_physics_substeps"]
            or report["hand_contact_substep_contract"]["control_decimation"] != 4
            or report["hand_contact_substep_contract"]["sample_phase"]
            != "after_scene_update_before_control_step_termination"):
        raise ValueError("Substep clock or source contract differs")

    loaded = []
    illegal = []
    limits = set()
    for index, row in enumerate(rows):
        if (row["push_control_step"] != index // 4 + 1
                or row["physics_substep"] != index % 4 + 1):
            raise ValueError(f"Incomplete substep clock at index {index}")
        detail = row["hand_contact"]
        if detail["force_norm_n"] > 1.0:
            point = detail["contact_pos_box_m"]
            if point is None or len(point) != 3 or not all(map(math.isfinite, point)):
                raise ValueError(f"Invalid loaded contact point at index {index}")
            loaded.append(index)
            limits.add(detail["box_size_m"][2] / 2 - detail["height_margin_m"]
                       + 1.0e-4)
        event = classify(row, dt)
        if event is not None and event["failed_legal_conditions"]:
            illegal.append((index, event))
    if (len(loaded) != cohort_record["sensor_force_above_1_n_samples"]
            or len(illegal) != cohort_record["illegal_hand_substeps"]
            or (illegal[0][1] if illegal else None)
            != cohort_record["first_illegal_hand_event"]
            or (illegal[0][1] if illegal else None)
            != (phase_record["first_illegal"] or {}).get("event")
            or len(limits) > 1):
        raise ValueError("Original contact event audit differs")

    limit = next(iter(limits), None)
    control_ends = [index for index in loaded if index % 4 == 3]
    result = {
        "seed": phase_record["seed"],
        "layout_tag": phase_record["layout_tag"],
        "outcome": cohort_record["outcome"],
        "terminal_reasons": cohort_record["terminal_reasons"],
        "report_sha256": phase_record["report_sha256"],
        "height_limit_box_local_m": limit,
        "loaded_control_step_end_count": len(control_ends),
        "smallest_observed_loaded_control_end_height_margin_m": min(
            (limit - abs(rows[index]["hand_contact"]["contact_pos_box_m"][2])
             for index in control_ends), default=None),
        "first_illegal": None,
    }
    if not illegal:
        return result

    first_index, event = illegal[0]
    phase = phase_record["first_illegal"]
    offset = phase["loaded_bout_offset_substeps"]
    start = first_index - offset
    if (start < 0 or any(index not in loaded for index in range(start, first_index + 1))
            or (start > 0 and start - 1 in loaded)
            or (phase["bout_kind"] == "first_contact" and start != loaded[0])):
        raise ValueError("First-illegal loaded bout differs")
    prior_ends = [index for index in control_ends if start <= index < first_index]
    anchors = [{
        "control_step_end_s": (index + 1) * dt,
        "lead_to_first_illegal_s": (first_index - index) * dt,
        "height_margin_box_local_m": (
            limit - abs(rows[index]["hand_contact"]["contact_pos_box_m"][2])),
    } for index in prior_ends]
    if any(anchor["height_margin_box_local_m"] < 0 for anchor in anchors):
        raise ValueError("An earlier loaded control end was already illegal")
    result["first_illegal"] = {
        "time_s": event["push_elapsed_s"],
        "bout_kind": phase["bout_kind"],
        "loaded_bout_offset_substeps": offset,
        "height_margin_box_local_m": (
            limit - abs(event["contact_pos_box_m"][2])),
        "prior_legal_loaded_control_step_ends_in_same_bout": anchors,
    }
    return result


def audit(cohort_path, phase_path, report_dir):
    cohort = json.loads(cohort_path.read_text(encoding="utf-8"))
    phase = json.loads(phase_path.read_text(encoding="utf-8"))
    if (phase["cohort_result_sha256"] != file_sha256(cohort_path)
            or phase["protocol_sha256"] != cohort["protocol_sha256"]
            or cohort["complete_run_denominator"] != 36
            or phase["complete_run_denominator"] != 36
            or phase["qualified_pair_denominator"] != 10
            or phase["loaded_bout_onset_window_substeps"] != 2):
        raise ValueError("Frozen cohort or phase result differs")
    cohort_rows = {(row["seed"], row["layout_tag"]): row
                   for row in cohort["records"]}
    phase_rows = {(row["seed"], row["layout_tag"]): row
                  for row in phase["records"]}
    expected = {(seed, "plus012") for seed in cohort["qualified_seeds"]}
    if (len(cohort_rows) != 36 or len(phase_rows) != 36
            or {key for key in cohort_rows if key[1] == "plus012"} != expected
            or {key for key in phase_rows if key[1] == "plus012"} != expected):
        raise ValueError("Right-layout conditional denominator differs")
    records = []
    for seed in sorted(cohort["qualified_seeds"]):
        key = (seed, "plus012")
        source = cohort_rows[key]
        phase_record = phase_rows[key]
        path = report_dir / f"seed{seed}-plus012.json"
        log = report_dir / f"seed{seed}-plus012.log"
        if (file_sha256(path) != source["report_sha256"]
                or source["report_sha256"] != phase_record["report_sha256"]
                or file_sha256(log) != source["log_sha256"]):
            raise ValueError(f"Original hash differs for seed{seed}")
        report = json.loads(path.read_text(encoding="utf-8"))
        if report["seed"] != seed or report["box_nominal_y_m"] != 0.12:
            raise ValueError(f"Seed or layout differs for seed{seed}")
        records.append(project(report, phase_record, source))
    return {
        "schema_version": 1,
        "scope": "retrospective_seen_right_layout_loaded_height_control_clock",
        "cohort_result_sha256": file_sha256(cohort_path),
        "phase_result_sha256": file_sha256(phase_path),
        "right_layout_run_denominator": len(records),
        "sample_phase": "after_scene_update_before_control_step_termination",
        "height_margin_is_calibrated": False,
        "online_warning_validated": False,
        "contact_authorized": False,
        "records": records,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cohort-result", type=Path, required=True)
    parser.add_argument("--phase-result", type=Path, required=True)
    parser.add_argument("--report-dir", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.cohort_result, args.phase_result, args.report_dir)
    with args.output_json.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"right_layout_run_denominator": result["right_layout_run_denominator"],
                      "late_first_illegal": [row for row in result["records"]
                                             if row["first_illegal"] is not None
                                             and row["first_illegal"]["loaded_bout_offset_substeps"] >= 2]}))


if __name__ == "__main__":
    main()
