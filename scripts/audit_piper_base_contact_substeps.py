"""Audit read-only PUSH contact substeps against a frozen control-step report."""

import argparse
import hashlib
import json
import math
from pathlib import Path


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def norm(vector):
    return math.sqrt(sum(value * value for value in vector))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--substeps", type=Path, required=True)
    parser.add_argument("--collision-profile", type=Path)
    parser.add_argument("--runtime-report", type=Path)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error("Output file already exists")
    if (args.collision_profile is None) != (args.runtime_report is None):
        parser.error("Collision profile and runtime report must be provided together")

    baseline, trial = load(args.baseline), load(args.substeps)
    if baseline["seed"] != trial["seed"]:
        raise ValueError("Seed mismatch")
    excluded_telemetry = []
    if baseline.get("record_recovery_decision_state") and not trial.get("record_recovery_decision_state"):
        if (not all("recovery_decision_state" in row for row in baseline["support_trace"])
                or "recovery_decision_state" not in baseline["terminal"]["support_snapshot"]):
            raise ValueError("Incomplete baseline recovery-only telemetry")
        baseline["support_trace"] = [
            {key: value for key, value in row.items() if key != "recovery_decision_state"}
            for row in baseline["support_trace"]
        ]
        baseline["terminal"]["support_snapshot"].pop("recovery_decision_state")
        excluded_telemetry.append("baseline recovery_decision_state")
    for key in ("handoff", "support_trace", "terminal", "outcome", "push_executed_steps"):
        if baseline[key] != trial[key]:
            raise ValueError(f"Frozen control-step result changed: {key}")

    contract = trial["base_contact_substep_contract"]
    decimation = contract["control_decimation"]
    threshold = contract["threshold_n"]
    if decimation != 4 or contract["sensor_history_length"] != 3:
        raise ValueError("Unexpected substep/history contract")
    rows = trial["base_contact_substeps"]
    control_steps = trial["push_executed_steps"]
    if len(rows) != control_steps * decimation or len(trial["support_trace"]) != control_steps:
        raise ValueError("Incomplete PUSH substep or control-step trace")

    exceed = []
    first_only = []
    detected = []
    max_net = 0.0
    max_filter_residual = 0.0
    for index, row in enumerate(rows):
        step, substep = divmod(index, decimation)
        if row["push_control_step"] != step + 1 or row["physics_substep"] != substep + 1:
            raise ValueError(f"Substep index mismatch at row {index}")
        history = row["net_force_history_w"]
        if len(history) != contract["sensor_history_length"] or history[0] != row["net_force_w"]:
            raise ValueError(f"Current force/history mismatch at row {index}")
        if index >= 2 and history != [rows[index - lag]["net_force_w"] for lag in range(3)]:
            raise ValueError(f"Sensor history did not roll at row {index}")
        force = norm(row["net_force_w"])
        max_net = max(max_net, force)
        if force > threshold:
            exceed.append({"push_control_step": step + 1, "physics_substep": substep + 1,
                           "net_force_n": force})
        source = row["filtered_force_w"]
        residual = [row["net_force_w"][axis] - source["ground"][axis] - source["box"][axis]
                    for axis in range(3)]
        max_filter_residual = max(max_filter_residual, norm(residual))

    for step in range(control_steps):
        group = rows[step * decimation:(step + 1) * decimation]
        final_history = group[-1]["net_force_history_w"]
        recorded_history = trial["support_trace"][step]["base_contact_source"]["net_force_history_w"]
        if final_history != recorded_history:
            raise ValueError(f"Control-step history mismatch at PUSH step {step + 1}")
        if max(map(norm, final_history)) > threshold:
            detected.append(step + 1)
        forces = [norm(row["net_force_w"]) for row in group]
        if forces[0] > threshold and max(forces[1:]) <= threshold:
            first_only.append(step + 1)

    geometry = None
    if args.collision_profile is not None:
        import numpy as np
        from scipy.spatial.transform import Rotation

        profile, runtime = load(args.collision_profile), load(args.runtime_report)
        if runtime["usd_sha256"] not in profile["usd_sha256"].values():
            raise ValueError("Runtime USD does not match the convex-hull profile")
        shapes = [shape for shape in profile["shapes"] if shape["body"] == "base_link"]
        if (len(shapes) != 1 or shapes[0]["position"] != [0.0, 0.0, 0.0]
                or shapes[0]["quaternion"] != [1.0, 0.0, 0.0, 0.0]):
            raise ValueError("Expected one base-frame collision mesh")
        vertices = np.asarray(shapes[0]["vertices"], dtype=float)
        if vertices.shape != (1194, 3):
            raise ValueError("Unexpected base convex-hull vertices")
        minimum_heights = []
        for row in rows:
            rotation = Rotation.from_quat(row["base_quat"], scalar_first=True).as_matrix()
            minimum_heights.append(float(row["base_pos"][2] + np.min(vertices @ rotation[2])))
        for event in exceed:
            index = ((event["push_control_step"] - 1) * decimation
                     + event["physics_substep"] - 1)
            event["minimum_hull_height_m"] = minimum_heights[index]
        geometry = {
            "collision_profile_sha256": digest(args.collision_profile),
            "runtime_report_sha256": digest(args.runtime_report),
            "base_hull_vertices": len(vertices),
            "minimum_sampled_hull_height_m": min(minimum_heights),
            "minimum_preterminal_control_step_hull_height_m": (
                min(minimum_heights[:-decimation]) if len(minimum_heights) > decimation else None
            ),
            "previous_control_step_hull_heights_m": minimum_heights[-2 * decimation:-decimation],
            "terminal_control_step_hull_heights_m": minimum_heights[-decimation:],
        }

    report = {
        "schema_version": 1,
        "seed": trial["seed"],
        "baseline_sha256": digest(args.baseline),
        "substep_report_sha256": digest(args.substeps),
        "audit_source_sha256": digest(Path(__file__)),
        "shared_control_step_fields_exactly_match": True,
        "baseline_only_read_only_fields_excluded": excluded_telemetry,
        "push_control_steps": control_steps,
        "push_physics_substeps": len(rows),
        "terminal_reasons": trial["terminal"]["reasons"],
        "threshold_n": threshold,
        "exceeding_substeps": exceed,
        "first_substep_only_exceed_control_steps": first_only,
        "detected_exceed_control_steps": detected,
        "max_net_force_n": max_net,
        "max_ground_box_filter_residual_n": max_filter_residual,
        "geometry_projection": geometry,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x", encoding="utf-8") as output:
        json.dump(report, output, indent=2, allow_nan=False)
    print(json.dumps({"seed": trial["seed"], "exceeding_substeps": len(exceed),
                      "first_only": len(first_only), "detected_steps": len(detected)}))


if __name__ == "__main__":
    main()
