"""Project loaded-contact loss and reacquisition in seen right-layout rollouts."""

import argparse
import json
from pathlib import Path

from audit_piper_hand_contact_success_controls import classify, file_sha256


def loaded_gaps(rows):
    loaded = [index for index, row in enumerate(rows)
              if row["hand_contact"]["force_norm_n"] > 1.0]
    return [{
        "previous_loaded_index": previous,
        "reacquisition_index": following,
        "unloaded_substeps": following - previous - 1,
        "zero_force_substeps": sum(
            rows[index]["hand_contact"]["force_norm_n"] == 0.0
            for index in range(previous + 1, following)),
        "unloaded_with_manifold_substeps": sum(
            bool(rows[index]["contact_manifold"])
            for index in range(previous + 1, following)),
        "unloaded_with_only_zero_force_manifold_substeps": sum(
            bool(rows[index]["contact_manifold"])
            and all(point["normal_force_n"] == 0.0
                    for point in rows[index]["contact_manifold"])
            for index in range(previous + 1, following)),
    } for previous, following in zip(loaded, loaded[1:]) if following > previous + 1]


def audit(cohort_path, report_dir):
    cohort = json.loads(cohort_path.read_text(encoding="utf-8"))
    right = [row for row in cohort["records"] if row["layout_tag"] == "plus012"]
    if (cohort["center_screen_denominator"] != 8
            or len(right) != cohort["qualified_pair_denominator"]
            or {row["seed"] for row in right} != set(cohort["qualified_seeds"])):
        raise ValueError("Conditional right-layout denominator differs")
    projections = []
    for record in right:
        seed = record["seed"]
        path = report_dir / f"seed{seed}-plus012.json"
        log = report_dir / f"seed{seed}-plus012.log"
        if (file_sha256(path) != record["report_sha256"]
                or file_sha256(log) != record["log_sha256"]):
            raise ValueError(f"Changed original for right seed{seed}")
        report = json.loads(path.read_text(encoding="utf-8"))
        rows = report["hand_contact_substeps"]
        dt = report["scene_runtime_observation"]["physics_dt_s"]
        if (report["seed"] != seed or len(rows) != 4 * report["push_executed_steps"]
                or abs(dt - 0.005) > 1e-9):
            raise ValueError(f"Incomplete clock for right seed{seed}")
        for index, row in enumerate(rows):
            if (row["push_control_step"] != index // 4 + 1
                    or row["physics_substep"] != index % 4 + 1):
                raise ValueError(f"Nonconsecutive clock for right seed{seed}")
        loaded = [index for index, row in enumerate(rows)
                  if row["hand_contact"]["force_norm_n"] > 1.0]
        if not loaded:
            raise ValueError(f"Missing loaded exposure for right seed{seed}")
        gaps = loaded_gaps(rows)
        illegal = record["first_illegal_hand_event"]
        first_illegal_index = None
        reacquisition = None
        if illegal is not None:
            first_illegal_index = (4 * (illegal["push_control_step"] - 1)
                                   + illegal["physics_substep"] - 1)
            if classify(rows[first_illegal_index], dt) != illegal:
                raise ValueError(f"First illegal event changed for right seed{seed}")
            block_start = first_illegal_index
            while (block_start > 0 and rows[block_start - 1]["hand_contact"]["force_norm_n"]
                   > 1.0):
                block_start -= 1
            preceding_gap = next((gap for gap in gaps
                                  if gap["reacquisition_index"] == block_start), None)
            if preceding_gap is not None:
                reacquisition_event = classify(rows[block_start], dt)
                reacquisition = {
                    "previous_loaded_s": (preceding_gap["previous_loaded_index"] + 1) * dt,
                    "reacquisition_s": (block_start + 1) * dt,
                    "unloaded_substeps": preceding_gap["unloaded_substeps"],
                    "zero_force_substeps": preceding_gap["zero_force_substeps"],
                    "unloaded_with_manifold_substeps":
                        preceding_gap["unloaded_with_manifold_substeps"],
                    "unloaded_with_only_zero_force_manifold_substeps":
                        preceding_gap["unloaded_with_only_zero_force_manifold_substeps"],
                    "reacquisition_contact_pos_box_m":
                        reacquisition_event["contact_pos_box_m"],
                    "reacquisition_failed_legal_conditions":
                        reacquisition_event["failed_legal_conditions"],
                    "same_control_step_as_first_illegal":
                        rows[block_start]["push_control_step"]
                        == rows[first_illegal_index]["push_control_step"],
                    "time_from_reacquisition_to_first_illegal_s":
                        (first_illegal_index - block_start) * dt,
                }
        projections.append({
            "seed": seed,
            "terminal_reasons": record["terminal_reasons"],
            "report_sha256": record["report_sha256"],
            "first_loaded_s": (loaded[0] + 1) * dt,
            "loaded_substeps": len(loaded),
            "loaded_gap_count": len(gaps),
            "longest_unloaded_gap_substeps": max(
                (gap["unloaded_substeps"] for gap in gaps), default=0),
            "first_illegal_s": (None if first_illegal_index is None
                                else (first_illegal_index + 1) * dt),
            "first_illegal_contact_pos_box_m": (
                None if illegal is None else illegal["contact_pos_box_m"]),
            "first_illegal_is_first_loaded": first_illegal_index == loaded[0],
            "preceding_reacquisition": reacquisition,
        })
    return {
        "schema_version": 1,
        "scope": "retrospective_seen_right_layout_loaded_recontact_phase_only",
        "cohort_result_sha256": file_sha256(cohort_path),
        "complete_qualified_right_denominator": len(projections),
        "loaded_force_threshold_n": 1.0,
        "unloaded_manifold_is_not_loaded_contact": True,
        "online_warning_certified": False,
        "records": projections,
        "contact_authorized": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cohort-result", type=Path, required=True)
    parser.add_argument("--report-dir", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.cohort_result, args.report_dir)
    with args.output_json.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"qualified_right": result["complete_qualified_right_denominator"],
                      "recontact_before_illegal": sum(
                          row["preceding_reacquisition"] is not None
                          for row in result["records"])}))


if __name__ == "__main__":
    main()
