"""Compare loaded PhysX hand contact points for the frozen signed arm probes."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def box_local(point_w, contact):
    quaternion = contact["box_quat_w"]
    rotation = Rotation.from_quat([*quaternion[1:], quaternion[0]])
    return rotation.inv().apply(np.asarray(point_w) - contact["box_pos_w_m"])


def summarize(report, event):
    row = next(item for item in report["hand_contact_substeps"]
               if item["push_control_step"] == event["push_control_step"]
               and item["physics_substep"] == event["physics_substep"])
    contact = row["hand_contact"]
    manifold = row["contact_manifold"]
    if not manifold or contact["force_norm_n"] <= 1.0:
        raise ValueError("Expected a loaded hand contact manifold at the frozen event")
    force_sum = sum(point["normal_force_n"] for point in manifold)
    mean_world = np.mean([point["point_w"] for point in manifold], axis=0)
    loaded = [point for point in manifold if point["normal_force_n"] > 1e-6]
    if abs(force_sum - contact["force_norm_n"]) > 1e-3:
        raise ValueError("Manifold and original sensor force differ")
    if np.linalg.norm(mean_world - contact["contact_pos_w_m"]) > 1e-6:
        raise ValueError("Original sensor point is not the candidate-point mean")
    sensor_local_error = np.linalg.norm(
        box_local(contact["contact_pos_w_m"], contact) - contact["contact_pos_box_m"]
    )
    if sensor_local_error > 1e-6:
        raise ValueError("Box-frame transform differs from the recorded sensor point")
    size = contact["box_size_m"]
    allowed_height = size[2] / 2 - contact["height_margin_m"] + 1e-4
    loaded_points = []
    for point in loaded:
        local = box_local(point["point_w"], contact)
        loaded_points.append({
            "normal_force_n": point["normal_force_n"],
            "point_box_m": local.tolist(),
            "front_face_error_m": float(abs(local[0] + size[0] / 2)),
            "height_excess_m": float(abs(local[2]) - allowed_height),
        })
    sensor_local = contact["contact_pos_box_m"]
    return {
        "event": event,
        "candidate_count": len(manifold),
        "loaded_count": len(loaded),
        "normal_force_sum_n": force_sum,
        "sensor_force_norm_n": contact["force_norm_n"],
        "candidate_mean_to_sensor_m": float(np.linalg.norm(mean_world - contact["contact_pos_w_m"])),
        "sensor_local_projection_error_m": float(sensor_local_error),
        "allowed_height_m": allowed_height,
        "sensor_point_box_m": sensor_local,
        "sensor_height_excess_m": abs(sensor_local[2]) - allowed_height,
        "loaded_points": loaded_points,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--positive-audit", type=Path, required=True)
    parser.add_argument("--signed-audit", type=Path, required=True)
    parser.add_argument("--baseline-dir", type=Path, required=True)
    parser.add_argument("--signed-dir", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error("Output file already exists")
    positive, signed = load(args.positive_audit), load(args.signed_audit)
    if positive["run_denominator"] != 4 or signed["run_denominator"] != 2:
        raise ValueError("Unexpected source audit denominator")
    records = []
    for seed in (6403, 6415):
        positive_row = next(row for row in positive["records"] if row["seed"] == seed)
        signed_row = next(row for row in signed["records"] if row["seed"] == seed)
        if not positive_row["recorded_mechanism_qualified"] or not signed_row["recorded_mechanism_qualified"]:
            raise ValueError(f"seed{seed} paired mechanism audit failed")
        event = positive_row["first_illegal_hand_sensor_sample"]["arm_clock"]
        event_tick = {key: event[key] for key in ("push_control_step", "physics_substep")}
        modes = {
            "baseline": (args.baseline_dir / f"seed{seed}-arm_clock.json",
                         positive_row["raw_report_sha256"]["arm_clock"]),
            "positive": (args.baseline_dir / f"seed{seed}-arm_pulse.json",
                         positive_row["raw_report_sha256"]["arm_pulse"]),
            "negative": (args.signed_dir / f"seed{seed}-arm_negative.json",
                         signed_row["raw_report_sha256"]["negative"]),
        }
        summaries = {}
        hashes = {}
        for name, (path, expected) in modes.items():
            actual = sha256(path)
            if actual != expected:
                raise ValueError(f"seed{seed} {name} report differs from frozen audit")
            report = load(path)
            summaries[name] = summarize(report, event_tick)
            hashes[name] = actual
            audited_event = (positive_row["first_illegal_hand_sensor_sample"]["arm_pulse"]
                             if name == "positive" else signed_row["first_illegal_hand_sensor_sample"]["negative"]
                             if name == "negative" else event)
            if any(audited_event[key] != event_tick[key] for key in event_tick):
                raise ValueError(f"seed{seed} {name} first illegal event shifted")
        records.append({"seed": seed, "raw_report_sha256": hashes, "modes": summaries})
    result = {
        "schema_version": 1,
        "positive_audit_sha256": sha256(args.positive_audit),
        "signed_audit_sha256": sha256(args.signed_audit),
        "analysis_script_sha256": sha256(Path(__file__)),
        "contact_authorized": False,
        "records": records,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"seeds": len(records), "loaded_points": [
        [len(mode["loaded_points"]) for mode in row["modes"].values()] for row in records]}))


if __name__ == "__main__":
    main()
