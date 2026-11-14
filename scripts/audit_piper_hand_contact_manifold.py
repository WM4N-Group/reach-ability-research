"""Audit a read-only PhysX hand manifold against a matched sensor substep trace."""

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation


MATCHED_FIELDS = (
    "initial_state", "trace", "approach_transitions", "handoff", "support_trace",
    "outcome", "push_executed_steps", "push_elapsed_s", "terminal_telemetry", "terminal",
)


def file_sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def summarize(row):
    contacts = row["contact_manifold"]
    sensor = row["hand_contact"]
    sensor_point = sensor["contact_pos_w_m"]
    nearest = min((math.dist(contact["point_w"], sensor_point)
                   for contact in contacts), default=None) if sensor_point is not None else None
    mean_point = ([sum(contact["point_w"][axis] for contact in contacts) / len(contacts)
                   for axis in range(3)] if contacts else None)
    loaded = []
    quat = sensor["box_quat_w"]
    rotation = Rotation.from_quat([*quat[1:], quat[0]])
    for contact in contacts:
        if contact["normal_force_n"] <= 1.0:
            continue
        local = rotation.apply(np.asarray(contact["point_w"])
                               - np.asarray(sensor["box_pos_w_m"]), inverse=True)
        sx, sy, sz = sensor["box_size_m"]
        loaded.append({
            "normal_force_n": contact["normal_force_n"],
            "point_box_m": local.tolist(),
            "front_margin_m": 0.02 - abs(float(local[0]) + sx / 2),
            "lateral_margin_m": sy / 2 - abs(float(local[1])),
            "height_margin_m": (sz / 2 - sensor["height_margin_m"] + 1.0e-4
                                - abs(float(local[2]))),
            "separation_m": contact["separation_m"],
        })
    return {
        "push_control_step": row["push_control_step"],
        "physics_substep": row["physics_substep"],
        "sensor_force_norm_n": sensor["force_norm_n"],
        "sensor_contact_pos_w_m": sensor_point,
        "point_count": len(contacts),
        "sum_point_normal_force_n": sum(contact["normal_force_n"] for contact in contacts),
        "nearest_point_to_sensor_m": nearest,
        "mean_candidate_point_w_m": mean_point,
        "mean_candidate_to_sensor_m": (math.dist(mean_point, sensor_point)
                                       if mean_point is not None and sensor_point is not None else None),
        "loaded_points": loaded,
        "contact_manifold": contacts,
    }


def audit(protocol_path, diagnostic_path, reference_path, report_path, log_path):
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    if (file_sha256(diagnostic_path) != protocol["diagnostic_sha256"]
            or file_sha256(reference_path) != protocol["reference_report_sha256"]
            or not log_path.stat().st_size):
        raise ValueError("Frozen diagnostic/reference hash differs or log is empty")
    reference = json.loads(reference_path.read_text(encoding="utf-8"))
    report = json.loads(report_path.read_text(encoding="utf-8"))
    control = protocol["control"]
    if (reference["schema_version"] != 25 or report["schema_version"] != 26
            or reference["seed"] != protocol["seed"] or report["seed"] != protocol["seed"]
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
        raise ValueError("Physical rollout differs from the frozen sensor trace")

    contract = report["hand_contact_manifold_contract"]
    if (contract["source"] != "box_contact_hand.contact_physx_view.get_contact_data"
            or contract["capacity_per_pair"] != 32
            or len(contract["prim_paths"]) != 1
            or not contract["prim_paths"][0].endswith("/Robot/link6")
            or not contract["filter_prim_paths_expr"]):
        raise ValueError("Unexpected PhysX hand-box contact view")
    if report["hand_contact_substep_contract"] != reference["hand_contact_substep_contract"]:
        raise ValueError("Hand sensor sampling phase differs")
    old_rows, new_rows = reference["hand_contact_substeps"], report["hand_contact_substeps"]
    if len(old_rows) != 1392 or len(new_rows) != len(old_rows):
        raise ValueError("Missing or extra hand physics substeps")
    point_samples = 0
    at_capacity = []
    events = []
    for index, (old_row, new_row) in enumerate(zip(old_rows, new_rows)):
        common = {key: value for key, value in new_row.items() if key != "contact_manifold"}
        if common != old_row:
            raise ValueError(f"Original hand sensor or physical state differs at substep {index}")
        contacts = new_row["contact_manifold"]
        if len(contacts) > contract["capacity_per_pair"]:
            raise ValueError(f"PhysX hand contact buffer exceeds its capacity at {index}")
        if contacts:
            point_samples += 1
        if len(contacts) == contract["capacity_per_pair"]:
            at_capacity.append(index)
        for contact in contacts:
            values = [contact["normal_force_n"], contact["separation_m"],
                      *contact["point_w"], *contact["normal_w"]]
            if len(values) != 8 or not all(math.isfinite(value) for value in values):
                raise ValueError(f"Non-finite PhysX contact at substep {index}")
        if old_row["hand_contact"]["force_norm_n"] > 1.0:
            events.append(summarize(new_row))
    if len(events) != 5:
        raise ValueError("Five original over-threshold hand sensor events were not reproduced")
    for event in events:
        if (event["mean_candidate_to_sensor_m"] is None
                or event["mean_candidate_to_sensor_m"] > 1.0e-6
                or len(event["loaded_points"]) != 1
                or not math.isclose(event["sum_point_normal_force_n"],
                                    event["sensor_force_norm_n"], rel_tol=1.0e-6, abs_tol=1.0e-4)):
            raise ValueError("Hand sensor point/force is not explained by the same-step manifold")
    if (new_rows[-1]["hand_contact"] != report["terminal"]["invalid_hand_contact_detail"]
            or new_rows[1383]["push_control_step"] != 346
            or new_rows[1383]["physics_substep"] != 4
            or new_rows[1383]["hand_contact"]["force_norm_n"] != 0.0):
        raise ValueError("Terminal alignment or the 6.920-s zero-force sample differs")
    return {
        "schema_version": 1,
        "scope": "seen_seed_read_only_physx_hand_contact_manifold",
        "protocol_sha256": file_sha256(protocol_path),
        "diagnostic_sha256": file_sha256(diagnostic_path),
        "reference_report_sha256": file_sha256(reference_path),
        "report_sha256": file_sha256(report_path),
        "log_sha256": file_sha256(log_path),
        "seed": report["seed"],
        "matched_fields": list(MATCHED_FIELDS),
        "physics_substeps": len(new_rows),
        "manifold_nonempty_samples": point_samples,
        "manifold_capacity_reached_substep_indices": at_capacity,
        "force_above_1_n_events": events,
        "control_step_346_final_substep": summarize(new_rows[1383]),
        "manifold_contract": contract,
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
                      "manifold_nonempty_samples": result["manifold_nonempty_samples"],
                      "event_point_counts": [event["point_count"]
                                             for event in result["force_above_1_n_events"]]}))


if __name__ == "__main__":
    main()
