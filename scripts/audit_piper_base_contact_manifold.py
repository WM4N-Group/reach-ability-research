"""Audit read-only PhysX base contact points against frozen substep forces."""

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
    parser.add_argument("--reference-substeps", type=Path, required=True)
    parser.add_argument("--manifold-report", type=Path, required=True)
    parser.add_argument("--runtime-offset", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error("Output file already exists")

    reference = load(args.reference_substeps)
    trial = load(args.manifold_report)
    runtime = load(args.runtime_offset)
    if not trial.get("record_base_contact_manifold") or reference["seed"] != trial["seed"]:
        raise ValueError("Manifold trace is absent or seed changed")
    for key in ("handoff", "support_trace", "terminal", "outcome", "push_executed_steps",
                "base_contact_substep_contract"):
        if reference[key] != trial[key]:
            raise ValueError(f"Frozen control-step result changed: {key}")
    if runtime["base_physx_view_prim_paths"] != ["/World/envs/env_0/Robot/base"]:
        raise ValueError("Runtime offset view does not isolate the base")
    contact_offsets = runtime["base_physx_contact_offsets_m"]
    rest_offsets = runtime["base_physx_rest_offsets_m"]
    if (len(contact_offsets) != 1 or len(contact_offsets[0]) != 1
            or len(rest_offsets) != 1 or len(rest_offsets[0]) != 1
            or trial["base_physx_contact_offset_m"] != contact_offsets[0][0]
            or trial["base_physx_rest_offset_m"] != rest_offsets[0][0]):
        raise ValueError("PhysX base offsets differ between static and rollout probes")

    reference_rows, rows = reference["base_contact_substeps"], trial["base_contact_substeps"]
    if len(reference_rows) != len(rows):
        raise ValueError("Substep count changed")
    sources = ("ground", "box")
    capacity = trial["base_contact_manifold_capacity_per_pair"]
    max_count = {name: 0 for name in sources}
    saturated = {name: 0 for name in sources}
    rows_with_candidates = {name: 0 for name in sources}
    rows_with_positive_force = {name: 0 for name in sources}
    max_force_residual = {name: 0.0 for name in sources}
    first_exceed = None
    threshold = trial["base_contact_substep_contract"]["threshold_n"]
    for index, row in enumerate(rows):
        old = {key: value for key, value in row.items() if key != "contact_manifold"}
        if old != reference_rows[index]:
            raise ValueError(f"Physical substep changed at row {index}")
        if set(row["contact_manifold"]) != set(sources):
            raise ValueError("Missing base contact source")
        for name in sources:
            contacts = row["contact_manifold"][name]
            count = len(contacts)
            if count > capacity[name]:
                raise ValueError(f"PhysX contact buffer overflow for {name}")
            max_count[name] = max(max_count[name], count)
            saturated[name] += count == capacity[name]
            rows_with_candidates[name] += count > 0
            rows_with_positive_force[name] += any(point["normal_force_n"] > threshold for point in contacts)
            reconstructed = [0.0, 0.0, 0.0]
            for point in contacts:
                force = point["normal_force_n"]
                if (not math.isfinite(force) or not math.isfinite(point["separation_m"])
                        or len(point["point_w"]) != 3 or len(point["normal_w"]) != 3
                        or not all(math.isfinite(value) for value in point["point_w"] + point["normal_w"])):
                    raise ValueError("Non-finite or malformed contact point")
                for axis in range(3):
                    reconstructed[axis] += force * point["normal_w"][axis]
            residual = norm([a - b for a, b in zip(reconstructed, row["filtered_force_w"][name])])
            max_force_residual[name] = max(max_force_residual[name], residual)
            if residual > 0.01 and count < capacity[name]:
                raise ValueError(f"Point forces disagree with {name} filtered force at row {index}")
        if first_exceed is None and norm(row["net_force_w"]) > threshold:
            first_exceed = {
                "push_control_step": row["push_control_step"],
                "physics_substep": row["physics_substep"],
                "base_force_n": norm(row["net_force_w"]),
                "loaded_ground_points": [
                    point for point in row["contact_manifold"]["ground"]
                    if point["normal_force_n"] > threshold
                ],
                "loaded_box_points": [
                    point for point in row["contact_manifold"]["box"]
                    if point["normal_force_n"] > threshold
                ],
            }

    report = {
        "schema_version": 1,
        "seed": trial["seed"],
        "reference_substeps_sha256": digest(args.reference_substeps),
        "manifold_report_sha256": digest(args.manifold_report),
        "runtime_offset_report_sha256": digest(args.runtime_offset),
        "audit_source_sha256": digest(Path(__file__)),
        "control_and_substep_fields_exactly_match": True,
        "base_physx_contact_offset_m": trial["base_physx_contact_offset_m"],
        "base_physx_rest_offset_m": trial["base_physx_rest_offset_m"],
        "max_contact_count_per_pair": max_count,
        "saturated_substeps": saturated,
        "substeps_with_contact_candidates": rows_with_candidates,
        "substeps_with_points_over_threshold": rows_with_positive_force,
        "max_point_force_reconstruction_residual_n": max_force_residual,
        "first_base_force_over_threshold": first_exceed,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x", encoding="utf-8") as output:
        json.dump(report, output, indent=2, allow_nan=False)
    print(json.dumps({"seed": trial["seed"], "first_exceed": first_exceed is not None,
                      "saturated": saturated, "max_residual": max_force_residual}))


if __name__ == "__main__":
    main()
