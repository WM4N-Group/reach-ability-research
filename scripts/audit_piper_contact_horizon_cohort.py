"""Project observed loaded-contact phases and one-control-step point reach."""

import argparse
import json
import math
from pathlib import Path

from scipy.spatial.transform import Rotation

from audit_piper_hand_contact_success_controls import classify, file_sha256
from audit_piper_right_recontact import loaded_gaps


LAYOUTS = ("center", "minus012", "plus012")


def loaded_points_box(row):
    sensor = row["hand_contact"]
    points = [point for point in row["contact_manifold"]
              if point["normal_force_n"] > 1.0]
    if not points:
        return []
    position = sensor["box_pos_w_m"]
    quaternion = sensor["box_quat_w"]
    rotation = Rotation.from_quat([*quaternion[1:], quaternion[0]])
    return [rotation.apply([point["point_w"][axis] - position[axis]
                            for axis in range(3)], inverse=True).tolist()
            for point in points]


def summarize(report, record):
    rows = report["hand_contact_substeps"]
    dt = report["scene_runtime_observation"]["physics_dt_s"]
    contract = report["hand_contact_substep_contract"]
    manifold = report["hand_contact_manifold_contract"]
    if (report["schema_version"] != 26 or dt != 0.005
            or contract["sample_phase"] != "after_scene_update_before_control_step_termination"
            or contract["control_decimation"] != 4
            or contract["sensor"] != "box_contact_hand"
            or manifold["source"] != "box_contact_hand.contact_physx_view.get_contact_data"
            or manifold["capacity_per_pair"] != 32
            or len(rows) != 4 * report["push_executed_steps"]
            or len(rows) != record["push_physics_substeps"]):
        raise ValueError("Contact sampling contract or complete clock differs")

    loaded = []
    local_points = []
    illegal = []
    maximum_spread = None
    maximum_euclidean_spread = None
    for index, row in enumerate(rows):
        if (row["push_control_step"] != index // 4 + 1
                or row["physics_substep"] != index % 4 + 1
                or len(row["contact_manifold"]) >= manifold["capacity_per_pair"]):
            raise ValueError(f"Substep clock or contact capacity differs at {index}")
        force = row["hand_contact"]["force_norm_n"]
        if not math.isfinite(force) or force < 0:
            raise ValueError(f"Invalid hand force at {index}")
        for point in row["contact_manifold"]:
            values = [point["normal_force_n"], *point["point_w"]]
            if any(not math.isfinite(value) for value in values):
                raise ValueError(f"Invalid contact point at {index}")
        points = loaded_points_box(row)
        if bool(points) != (force > 1.0):
            raise ValueError(f"Sensor and loaded manifold disagree at {index}")
        local_points.append(points)
        if force > 1.0:
            loaded.append(index)
            sensor = row["hand_contact"]["contact_pos_box_m"]
            if sensor is None or len(sensor) != 3:
                raise ValueError(f"Missing loaded sensor point at {index}")
            for point in points:
                delta = [abs(point[axis] - sensor[axis]) for axis in range(3)]
                maximum_spread = max(maximum_spread or 0.0, max(delta))
                maximum_euclidean_spread = max(
                    maximum_euclidean_spread or 0.0, math.dist(point, sensor))
        event = classify(row, dt)
        if event is not None and event["failed_legal_conditions"]:
            illegal.append((index, event))
    if (len(loaded) != record["sensor_force_above_1_n_samples"]
            or len(illegal) != record["illegal_hand_substeps"]
            or (illegal[0][1] if illegal else None) != record["first_illegal_hand_event"]
            or (maximum_euclidean_spread is None)
            != (record["maximum_sensor_to_loaded_point_m"] is None)
            or (maximum_euclidean_spread is not None and not math.isclose(
                maximum_euclidean_spread, record["maximum_sensor_to_loaded_point_m"],
                rel_tol=1e-6, abs_tol=1e-6))):
        raise ValueError("Original contact audit differs")

    gaps = loaded_gaps(rows)
    first_illegal_bout = None
    first_illegal_at_bout_start = None
    if illegal:
        index = illegal[0][0]
        start = index
        while start > 0 and rows[start - 1]["hand_contact"]["force_norm_n"] > 1.0:
            start -= 1
        first_illegal_bout = "first_contact" if start == loaded[0] else "recontact"
        first_illegal_at_bout_start = index == start

    full_horizon_loaded_anchors = 0
    full_horizon_unloaded_anchors = 0
    unloaded_anchor_followed_by_load = 0
    maximum_reach = None
    reach_witness = None
    for index in range(3, len(rows) - 4, 4):
        future = ((later, point) for later in range(index + 1, index + 5)
                  for point in local_points[later])
        if rows[index]["hand_contact"]["force_norm_n"] <= 1.0:
            full_horizon_unloaded_anchors += 1
            unloaded_anchor_followed_by_load += any(local_points[index + 1:index + 5])
            continue
        full_horizon_loaded_anchors += 1
        sensor = rows[index]["hand_contact"]["contact_pos_box_m"]
        for later, point in future:
            delta = [abs(point[axis] - sensor[axis]) for axis in range(3)]
            reach = max(delta)
            if maximum_reach is None or reach > maximum_reach:
                maximum_reach = reach
                reach_witness = {
                    "anchor_control_step": rows[index]["push_control_step"],
                    "anchor_time_s": (index + 1) * dt,
                    "future_time_s": (later + 1) * dt,
                    "future_substep_offset": later - index,
                    "lost_load_between_samples": any(
                        rows[between]["hand_contact"]["force_norm_n"] <= 1.0
                        for between in range(index + 1, later)),
                    "box_local_abs_delta_m": delta,
                }
    return {
        "seed": record["seed"],
        "layout_tag": record["layout_tag"],
        "terminal_reasons": record["terminal_reasons"],
        "report_sha256": record["report_sha256"],
        "push_physics_substeps": len(rows),
        "loaded_substeps": len(loaded),
        "loaded_bouts": len(gaps) + 1 if loaded else 0,
        "interbout_unloaded_gaps": len(gaps),
        "longest_interbout_unloaded_substeps": max(
            (gap["unloaded_substeps"] for gap in gaps), default=0),
        "first_illegal_bout": first_illegal_bout,
        "first_illegal_at_bout_start": first_illegal_at_bout_start,
        "maximum_observed_sensor_to_loaded_box_linf_m": maximum_spread,
        "full_next_20ms_loaded_control_step_ends": full_horizon_loaded_anchors,
        "full_next_20ms_unloaded_control_step_ends": full_horizon_unloaded_anchors,
        "unloaded_control_step_ends_followed_by_load": unloaded_anchor_followed_by_load,
        "maximum_observed_next_20ms_loaded_point_reach_box_linf_m": maximum_reach,
        "maximum_observed_next_20ms_reach_witness": reach_witness,
    }


def audit(protocol_path, cohort_path, report_dir):
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    cohort = json.loads(cohort_path.read_text(encoding="utf-8"))
    if (cohort["protocol_sha256"] != file_sha256(protocol_path)
            or protocol["seeds_in_order"] != list(range(6301, 6309))
            or cohort["center_screen_denominator"] != 8
            or cohort["qualified_pair_denominator"] != len(cohort["qualified_seeds"])
            or cohort["complete_run_denominator"] != len(cohort["records"])):
        raise ValueError("Frozen cohort denominator differs")
    expected = {(seed, "center") for seed in protocol["seeds_in_order"]}
    expected.update((seed, tag) for seed in cohort["qualified_seeds"]
                    for tag in LAYOUTS[1:])
    records = {(record["seed"], record["layout_tag"]): record
               for record in cohort["records"]}
    if len(records) != len(cohort["records"]) or set(records) != expected:
        raise ValueError("Incomplete or duplicated conditional layout grid")
    stems = {f"seed{seed}-{tag}" for seed, tag in expected}
    for suffix in ("json", "log"):
        if {path.stem for path in report_dir.glob(f"seed*.{suffix}")} != stems:
            raise ValueError(f"Original {suffix} denominator differs")

    projections = []
    for seed in protocol["seeds_in_order"]:
        tags = LAYOUTS if seed in cohort["qualified_seeds"] else LAYOUTS[:1]
        for tag in tags:
            record = records[(seed, tag)]
            stem = f"seed{seed}-{tag}"
            path = report_dir / f"{stem}.json"
            log = report_dir / f"{stem}.log"
            if (file_sha256(path) != record["report_sha256"]
                    or file_sha256(log) != record["log_sha256"]):
                raise ValueError(f"Changed original for {stem}")
            report = json.loads(path.read_text(encoding="utf-8"))
            if (report["seed"] != seed or report["task"] != protocol["task"]
                    or report["box_nominal_y_m"] != next(
                        layout["nominal_box_y_m"] for layout in
                        [protocol["screen_layout"], *protocol["qualified_layouts_in_order"]]
                        if layout["tag"] == tag)):
                raise ValueError(f"Seed, layout or task differs for {stem}")
            projections.append(summarize(report, record))
    return {
        "schema_version": 1,
        "scope": "retrospective_seen_conditional_lateral_contact_phase_and_observed_one_step_reach",
        "protocol_sha256": file_sha256(protocol_path),
        "cohort_result_sha256": file_sha256(cohort_path),
        "complete_center_screen_denominator": 8,
        "qualified_pair_denominator": len(cohort["qualified_seeds"]),
        "complete_run_denominator": len(projections),
        "sensor_and_point_loaded_threshold_n": 1.0,
        "future_horizon_s": 0.02,
        "future_reach_is_model_bound": False,
        "online_warning_certified": False,
        "records": projections,
        "contact_authorized": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol-json", type=Path, required=True)
    parser.add_argument("--cohort-result", type=Path, required=True)
    parser.add_argument("--report-dir", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.protocol_json, args.cohort_result, args.report_dir)
    with args.output_json.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({
        "complete_runs": result["complete_run_denominator"],
        "interbout_gaps": sum(row["interbout_unloaded_gaps"] for row in result["records"]),
        "observed_max_next_20ms_reach_m": max(
            (row["maximum_observed_next_20ms_loaded_point_reach_box_linf_m"] or 0.0)
            for row in result["records"]),
    }))


if __name__ == "__main__":
    main()
