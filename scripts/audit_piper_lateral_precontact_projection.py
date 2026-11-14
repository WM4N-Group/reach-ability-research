"""Project seen right-stratum hand trajectories around first loaded contact."""

import argparse
import json
from pathlib import Path

from audit_piper_hand_contact_success_controls import file_sha256


def audit(cohort_result_path, report_dir):
    cohort = json.loads(cohort_result_path.read_text(encoding="utf-8"))
    seeds = cohort["qualified_seeds"]
    right = {row["seed"]: row for row in cohort["records"]
             if row["layout_tag"] == "plus012"}
    if (cohort["scope"] != "independent_center_screen_conditional_lateral_pose_pairs_only"
            or set(right) != set(seeds) or len(seeds) != cohort["qualified_pair_denominator"]):
        raise ValueError("Right-stratum cohort identity differs")
    records = []
    for seed in seeds:
        path = report_dir / f"seed{seed}-plus012.json"
        if file_sha256(path) != right[seed]["report_sha256"]:
            raise ValueError(f"Original right-stratum report changed for seed{seed}")
        report = json.loads(path.read_text(encoding="utf-8"))
        rows = report["hand_contact_substeps"]
        indices = [index for index, row in enumerate(rows)
                   if row["hand_contact"]["force_norm_n"] > 1.0]
        if not indices or indices[0] < 20 or len(rows) != 4 * report["push_executed_steps"]:
            raise ValueError(f"First loaded contact or complete substep clock missing for seed{seed}")
        first = indices[0]
        samples = {}
        for elapsed_ms, offset in ((-100, 20), (-20, 4), (0, 0)):
            row = rows[first - offset]
            step, substep = divmod(first - offset, 4)
            if (row["push_control_step"] != step + 1
                    or row["physics_substep"] != substep + 1
                    or row["motion_ready"] is not True):
                raise ValueError(f"Hand clock or preparation phase differs for seed{seed}")
            samples[str(elapsed_ms)] = {
                "push_elapsed_s": (first - offset + 1) * report["scene_runtime_observation"]["physics_dt_s"],
                "hand_body_origin_box_m": row["hand_body_origin_box_m"],
                "front_face_gap_from_hand_origin_m":
                    -report["scene_runtime_observation"]["box_size_m"][0] / 2
                    - row["hand_body_origin_box_m"][0],
                "foot_normal_forces_n": row["foot_normal_forces_n"],
            }
        records.append({
            "seed": seed,
            "right_outcome": right[seed]["terminal_reasons"],
            "report_sha256": file_sha256(path),
            "first_loaded_hand_force_n": rows[first]["hand_contact"]["force_norm_n"],
            "first_loaded_contact_pos_box_m":
                rows[first]["hand_contact"]["contact_pos_box_m"],
            "samples_by_ms_before_first_loaded_contact": samples,
        })
    return {
        "schema_version": 1,
        "scope": "retrospective_seen_right_stratum_first_contact_alignment_only",
        "cohort_result_sha256": file_sha256(cohort_result_path),
        "complete_qualified_right_denominator": len(records),
        "uses_future_first_contact_for_alignment": True,
        "online_warning_certified": False,
        "records": records,
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
    print(json.dumps({"complete_qualified_right_denominator":
                      result["complete_qualified_right_denominator"],
                      "online_warning_certified": result["online_warning_certified"]}))


if __name__ == "__main__":
    main()
