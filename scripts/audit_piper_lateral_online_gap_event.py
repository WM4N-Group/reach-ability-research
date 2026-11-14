"""Audit seen lateral trajectories at a causal hand-to-front-face gap event."""

import argparse
import json
from pathlib import Path

from audit_piper_hand_contact_success_controls import file_sha256


GAP_M = 0.04
LAYOUTS = ("center", "minus012", "plus012")


def project(row, index, previous, dt, front_x):
    gap = front_x - row["hand_body_origin_box_m"][0]
    result = {
        "push_elapsed_s": (index + 1) * dt,
        "push_control_step": row["push_control_step"],
        "physics_substep": row["physics_substep"],
        "front_face_gap_from_hand_origin_m": gap,
        "hand_origin_height_box_m": row["hand_body_origin_box_m"][2],
        "foot_normal_forces_n": row["foot_normal_forces_n"],
        "feet_above_2_n": sum(force > 2.0 for force in row["foot_normal_forces_n"]),
        "hand_force_n": row["hand_contact"]["force_norm_n"],
    }
    if previous is not None:
        earlier = previous["hand_body_origin_box_m"]
        interval = (index - previous["index"]) * dt
        result["gap_closing_speed_m_s"] = (front_x - earlier[0] - gap) / interval
        result["hand_height_speed_m_s"] = (row["hand_body_origin_box_m"][2]
                                              - earlier[2]) / interval
    return result


def first_crossing(rows, indices, front_x):
    previous_index = None
    for index in indices:
        row = rows[index]
        if not row["motion_ready"]:
            previous_index = None
            continue
        gap = front_x - row["hand_body_origin_box_m"][0]
        if previous_index is not None:
            previous_gap = front_x - rows[previous_index]["hand_body_origin_box_m"][0]
            if previous_gap > GAP_M >= gap:
                return index, previous_index
        previous_index = index
    return None, None


def audit(cohort_path, report_dir):
    cohort = json.loads(cohort_path.read_text(encoding="utf-8"))
    qualified = cohort["qualified_seeds"]
    records = {(row["seed"], row["layout_tag"]): row for row in cohort["records"]}
    if (cohort["scope"] != "independent_center_screen_conditional_lateral_pose_pairs_only"
            or len(records) != cohort["complete_run_denominator"]
            or len(qualified) != cohort["qualified_pair_denominator"]
            or set(records) != ({(seed, "center") for seed in range(6201, 6209)}
                                | {(seed, tag) for seed in qualified
                                   for tag in LAYOUTS[1:]})):
        raise ValueError("Cohort grid or qualified denominator differs")
    expected_stems = {f"seed{seed}-{tag}" for seed, tag in records}
    for suffix in ("json", "log"):
        if {path.stem for path in report_dir.glob(f"seed*.{suffix}")} != expected_stems:
            raise ValueError(f"Incomplete or extra {suffix} originals")
    for (seed, tag), record in records.items():
        stem = f"seed{seed}-{tag}"
        for suffix in ("json", "log"):
            path = report_dir / f"{stem}.{suffix}"
            digest_key = "report_sha256" if suffix == "json" else "log_sha256"
            if file_sha256(path) != record[digest_key]:
                raise ValueError(f"Original {suffix} changed for {stem}")

    projections = []
    for seed in qualified:
        for tag in LAYOUTS:
            report = json.loads((report_dir / f"seed{seed}-{tag}.json").read_text(
                encoding="utf-8"))
            rows = report["hand_contact_substeps"]
            dt = report["scene_runtime_observation"]["physics_dt_s"]
            front_x = -report["scene_runtime_observation"]["box_size_m"][0] / 2
            if (len(rows) != 4 * report["push_executed_steps"]
                    or abs(dt - 0.005) > 1e-9
                    or abs(front_x + 0.6) > 1e-9):
                raise ValueError(f"Unexpected clock or box face for seed{seed}-{tag}")
            for index, row in enumerate(rows):
                if (row["push_control_step"] != index // 4 + 1
                        or row["physics_substep"] != index % 4 + 1):
                    raise ValueError(f"Incomplete substep clock for seed{seed}-{tag}")
            ready = next((index for index, row in enumerate(rows) if row["motion_ready"]), None)
            contact = next((index for index, row in enumerate(rows)
                            if row["hand_contact"]["force_norm_n"] > 1.0), None)
            if ready is None or contact is None:
                raise ValueError(f"Missing ready or loaded contact for seed{seed}-{tag}")
            events = {}
            for clock, indices in (("physics_substep", range(len(rows))),
                                   ("control_step_end", range(3, len(rows), 4))):
                index, prior = first_crossing(rows, indices, front_x)
                if index is None:
                    events[clock] = None
                    continue
                prior_row = dict(rows[prior], index=prior)
                event = project(rows[index], index, prior_row, dt, front_x)
                event["before_first_loaded_contact"] = index < contact
                event["retrospective_time_to_first_loaded_contact_s"] = (
                    contact - index) * dt
                events[clock] = event
            projections.append({
                "seed": seed,
                "layout_tag": tag,
                "terminal_reasons": records[(seed, tag)]["terminal_reasons"],
                "report_sha256": records[(seed, tag)]["report_sha256"],
                "first_motion_ready_s": (ready + 1) * dt,
                "first_loaded_contact_s": (contact + 1) * dt,
                "events": events,
            })
    return {
        "schema_version": 1,
        "scope": "seen_conditional_lateral_cohort_causal_gap_event_exploration",
        "cohort_result_sha256": file_sha256(cohort_path),
        "verified_original_report_count": len(records),
        "verified_original_log_count": len(records),
        "qualified_triplet_count": len(qualified),
        "fixed_seen_data_gap_m": GAP_M,
        "future_contact_used_by_trigger": False,
        "future_contact_used_for_retrospective_evaluation": True,
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
    print(json.dumps({"verified_reports": result["verified_original_report_count"],
                      "qualified_triplets": result["qualified_triplet_count"],
                      "event_counts": {clock: sum(row["events"][clock] is not None
                                                  for row in result["records"])
                                       for clock in ("physics_substep", "control_step_end")}}))


if __name__ == "__main__":
    main()
