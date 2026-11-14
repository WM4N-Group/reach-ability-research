"""Retrospectively check a constant-velocity precontact height projection."""

import argparse
import hashlib
import json
from pathlib import Path


GAP_M = 0.04
REFERENCE_HEIGHT_M = 0.0901
PHYSICS_DT_S = 0.005
SUBSTEPS_PER_CONTROL = 4


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def crossing(report):
    rows = report["hand_contact_substeps"]
    if (len(rows) != SUBSTEPS_PER_CONTROL * report["push_executed_steps"]
            or abs(report["scene_runtime_observation"]["physics_dt_s"]
                   - PHYSICS_DT_S) > 1e-9):
        raise ValueError("Unexpected substep clock")
    front_x = -report["scene_runtime_observation"]["box_size_m"][0] / 2
    previous = None
    first_loaded = next((i for i, row in enumerate(rows)
                         if row["hand_contact"]["force_norm_n"] > 1), None)
    for index in range(SUBSTEPS_PER_CONTROL - 1, len(rows), SUBSTEPS_PER_CONTROL):
        row = rows[index]
        if (row["push_control_step"] != index // SUBSTEPS_PER_CONTROL + 1
                or row["physics_substep"] != SUBSTEPS_PER_CONTROL):
            raise ValueError("Control clock discontinuity")
        if not row["motion_ready"]:
            previous = None
            continue
        height = row["hand_body_origin_box_m"][2]
        gap = front_x - row["hand_body_origin_box_m"][0]
        if previous is not None and previous["gap_m"] > GAP_M >= gap:
            elapsed = (index - previous["index"]) * PHYSICS_DT_S
            closing_speed = (previous["gap_m"] - gap) / elapsed
            vertical_speed = (height - previous["height_m"]) / elapsed
            if closing_speed <= 0:
                raise ValueError("Non-closing gap at crossing")
            projected_height = height + gap * vertical_speed / closing_speed
            return {
                "time_s": (index + 1) * PHYSICS_DT_S,
                "lead_to_first_loaded_contact_s": (
                    (first_loaded - index) * PHYSICS_DT_S
                    if first_loaded is not None else None),
                "before_first_loaded_contact": first_loaded is None or index < first_loaded,
                "gap_m": gap,
                "hand_origin_height_box_m": height,
                "closing_speed_m_s": closing_speed,
                "vertical_speed_m_s": vertical_speed,
                "projected_hand_origin_height_at_front_face_m": projected_height,
                "above_reference_height": projected_height > REFERENCE_HEIGHT_M,
            }
        previous = {"index": index, "gap_m": gap, "height_m": height}
    return None


def audit(cohort_path, report_dir):
    cohort = json.loads(cohort_path.read_text(encoding="utf-8"))
    records = [row for row in cohort["records"] if row["layout_tag"] == "plus012"]
    if (cohort["scope"] != "independent_center_screen_conditional_lateral_pose_pairs_only"
            or cohort["qualified_pair_denominator"] != 10
            or len(records) != 10
            or len({row["seed"] for row in records}) != 10):
        raise ValueError("Unexpected secondary cohort denominator")
    results = []
    for row in sorted(records, key=lambda item: item["seed"]):
        report_path = report_dir / f"seed{row['seed']}-plus012.json"
        if sha256(report_path) != row["report_sha256"]:
            raise ValueError(f"Report hash mismatch: {report_path}")
        report = json.loads(report_path.read_text(encoding="utf-8"))
        results.append({
            "seed": row["seed"],
            "terminal_reasons": row["terminal_reasons"],
            "report_sha256": row["report_sha256"],
            "first_gap_crossing": crossing(report),
        })
    if any(row["first_gap_crossing"] is None
           or not row["first_gap_crossing"]["before_first_loaded_contact"]
           for row in results):
        raise ValueError("Missing precontact crossing in complete secondary cohort")
    failures = [row for row in results
                if "invalid_hand_contact" in row["terminal_reasons"]]
    settled = [row for row in results if row["terminal_reasons"] == ["box_settled"]]
    if len(failures) + len(settled) != len(results):
        raise ValueError("Unexpected outcome class")
    return {
        "schema_version": 1,
        "scope": "retrospective_secondary_cohort_constant_velocity_projection",
        "cohort_sha256": sha256(cohort_path),
        "verified_report_count": len(results),
        "qualified_right_layout_count": len(results),
        "formula": "z_hat = z_hand + gap * v_z / v_close at first ready control end crossing 0.04 m gap",
        "reference_height_m": REFERENCE_HEIGHT_M,
        "reference_caveat": "The reference is a contact-point height limit, while the score projects the hand origin.",
        "confusion_counts": {
            "invalid_above_reference": sum(r["first_gap_crossing"]["above_reference_height"]
                                           for r in failures),
            "invalid_at_or_below_reference": sum(
                not r["first_gap_crossing"]["above_reference_height"] for r in failures),
            "settled_above_reference": sum(r["first_gap_crossing"]["above_reference_height"]
                                           for r in settled),
            "settled_at_or_below_reference": sum(
                not r["first_gap_crossing"]["above_reference_height"] for r in settled),
        },
        "records": results,
        "online_warning_validated": False,
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
    print(json.dumps(result["confusion_counts"]))


if __name__ == "__main__":
    main()
