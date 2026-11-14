"""Compare a diagnostic cooked convex with known loaded base-ground contacts."""

import argparse
import json
from pathlib import Path

import numpy as np
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation

from analyze_piper_base_contact_surface_alignment import digest, load, lower_surface_at_xy, norm


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cooked-report", type=Path, required=True)
    parser.add_argument("--runtime-frame", type=Path, required=True)
    parser.add_argument("--manifold-report", type=Path, required=True)
    parser.add_argument("--raw-alignment", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error("Output already exists")
    cooked, frame, report, raw = [load(path) for path in (
        args.cooked_report, args.runtime_frame, args.manifold_report, args.raw_alignment)]
    if (cooked["usd_sha256"] != frame["usd_sha256"]
            or cooked["scope"] != "read_only_rollout_in_memory_clone_cooking_diagnostic"
            or len(cooked["convexes"]) != 1
            or raw["manifold_report_sha256"] != digest(args.manifold_report)
            or raw["runtime_frame_report_sha256"] != digest(args.runtime_frame)
            or raw["seed"] != report["seed"]):
        raise ValueError("Cooked, frame, manifold or raw-alignment provenance mismatch")
    vertices = np.asarray(cooked["convexes"][0]["vertices"], dtype=float)
    if vertices.ndim != 2 or vertices.shape[1] != 3 or not np.isfinite(vertices).all():
        raise ValueError("Invalid cooked convex vertices")
    hull = ConvexHull(vertices)
    threshold = report["base_contact_substep_contract"]["threshold_n"]
    event = next((row for row in report["base_contact_substeps"]
                  if norm(row["net_force_w"]) > threshold), None)
    if event is None or not report["terminal"]["reasons"]["base_contact"]:
        raise ValueError("Expected a known terminal base-ground contact")
    rotation = Rotation.from_quat(event["base_quat"], scalar_first=True)
    vertices_w = rotation.apply(vertices) + np.asarray(event["base_pos"], dtype=float)
    normals_w = rotation.apply(hull.equations[:, :3])
    lowest = vertices_w[int(np.argmin(vertices_w[:, 2]))]
    checked_lowest = lower_surface_at_xy(vertices_w, hull.simplices, normals_w, lowest[:2])
    if checked_lowest is None or abs(checked_lowest - lowest[2]) > 1e-6:
        raise ValueError("Cooked lower surface failed lowest-vertex self-check")
    loaded = [point for point in event["contact_manifold"]["ground"]
              if point["normal_force_n"] > threshold]
    if len(loaded) != len(raw["loaded_ground_points"]) or event["contact_manifold"]["box"]:
        raise ValueError("Loaded ground contact count changed")
    comparisons = []
    for point, raw_point in zip(loaded, raw["loaded_ground_points"]):
        if point["point_w"] != raw_point["point_w"]:
            raise ValueError("Contact point order or value changed")
        xy = np.asarray(point["point_w"][:2], dtype=float)
        cooked_height = lower_surface_at_xy(vertices_w, hull.simplices, normals_w, xy)
        comparisons.append({
            "point_w": point["point_w"],
            "normal_force_n": point["normal_force_n"],
            "physx_separation_m": point["separation_m"],
            "raw_hull_lower_surface_m": raw_point["raw_hull_lower_surface_at_contact_xy_m"],
            "diagnostic_cooked_lower_surface_m": cooked_height,
            "cooked_minus_raw_surface_m": (
                cooked_height - raw_point["raw_hull_lower_surface_at_contact_xy_m"]
                if cooked_height is not None else None),
            "physx_separation_minus_cooked_surface_m": (
                point["separation_m"] - cooked_height if cooked_height is not None else None),
        })
    result = {
        "schema_version": 1,
        "seed": report["seed"],
        "scope": "known_contact_same_xy_diagnostic_cooked_convex_comparison",
        "cooked_report_sha256": digest(args.cooked_report),
        "runtime_frame_report_sha256": digest(args.runtime_frame),
        "manifold_report_sha256": digest(args.manifold_report),
        "raw_alignment_report_sha256": digest(args.raw_alignment),
        "analysis_source_sha256": digest(Path(__file__)),
        "cooked_vertex_count": len(vertices),
        "cooked_global_lowest_point_w": lowest.tolist(),
        "loaded_ground_points": comparisons,
        "runtime_collider_equivalence_proven": False,
        "contact_authorized": False,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x", encoding="utf-8") as output:
        json.dump(result, output, indent=2, allow_nan=False)
        output.write("\n")
    print(json.dumps({"seed": report["seed"], "loaded_points": len(comparisons),
                      "cooked_surface_found": all(point["diagnostic_cooked_lower_surface_m"]
                                                  is not None for point in comparisons)}))


if __name__ == "__main__":
    main()
