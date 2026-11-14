"""Compare loaded PhysX contact points with the raw USD convex-hull lower surface."""

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def norm(vector):
    return math.sqrt(sum(value * value for value in vector))


def lower_surface_at_xy(vertices_w, facets, normals_w, xy):
    heights = []
    for indices, normal in zip(facets, normals_w):
        if normal[2] >= -1e-9:
            continue
        triangle = vertices_w[indices]
        matrix = np.column_stack((triangle[1, :2] - triangle[0, :2],
                                  triangle[2, :2] - triangle[0, :2]))
        if abs(np.linalg.det(matrix)) < 1e-12:
            continue
        weights = np.linalg.solve(matrix, xy - triangle[0, :2])
        barycentric = np.array((1.0 - weights.sum(), weights[0], weights[1]))
        if np.min(barycentric) >= -1e-5:
            heights.append(float(barycentric @ triangle[:, 2]))
    return min(heights) if heights else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--collision-profile", type=Path, required=True)
    parser.add_argument("--runtime-frame", type=Path, required=True)
    parser.add_argument("--manifold-report", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error("Output file already exists")

    profile, frame, report = [load(path) for path in
                              (args.collision_profile, args.runtime_frame, args.manifold_report)]
    if (frame["usd_sha256"] not in profile["usd_sha256"].values()
            or frame["articulation_root_body_name"] != "base" or frame["base_body_index"] != 0
            or frame["articulation_root_pos_w"] != frame["base_body_pos_w"]
            or frame["articulation_root_quat_w"] != frame["base_body_quat_w"]):
        raise ValueError("Runtime USD or base/root frame contract changed")
    if report["base_physx_contact_offset_m"] != frame["base_physx_contact_offsets_m"][0][0]:
        raise ValueError("Runtime base contact offset changed")
    shapes = [shape for shape in profile["shapes"] if shape["body"] == "base_link"]
    if (len(shapes) != 1 or shapes[0]["position"] != [0.0, 0.0, 0.0]
            or shapes[0]["quaternion"] != [1.0, 0.0, 0.0, 0.0]):
        raise ValueError("Expected one base-frame convex-hull mesh")
    vertices = np.asarray(shapes[0]["vertices"], dtype=float)
    if vertices.shape != (1194, 3) or not np.isfinite(vertices).all():
        raise ValueError("Unexpected base convex-hull vertices")
    hull = ConvexHull(vertices)
    threshold = report["base_contact_substep_contract"]["threshold_n"]
    event = next((row for row in report["base_contact_substeps"]
                  if norm(row["net_force_w"]) > threshold), None)
    if event is None or not report["terminal"]["reasons"]["base_contact"]:
        raise ValueError("Expected one known base-contact event")

    rotation = Rotation.from_quat(event["base_quat"], scalar_first=True)
    vertices_w = rotation.apply(vertices) + np.asarray(event["base_pos"], dtype=float)
    normals_w = rotation.apply(hull.equations[:, :3])
    lowest = vertices_w[int(np.argmin(vertices_w[:, 2]))]
    checked_lowest = lower_surface_at_xy(vertices_w, hull.simplices, normals_w, lowest[:2])
    if checked_lowest is None or abs(checked_lowest - lowest[2]) > 1e-6:
        raise ValueError("Raw convex-hull lower-surface interpolation failed its lowest-vertex check")
    loaded = []
    for contact in event["contact_manifold"]["ground"]:
        if contact["normal_force_n"] <= threshold:
            continue
        point = np.asarray(contact["point_w"], dtype=float)
        raw_height = lower_surface_at_xy(vertices_w, hull.simplices, normals_w, point[:2])
        loaded.append({
            "point_w": point.tolist(),
            "normal_force_n": contact["normal_force_n"],
            "physx_separation_m": contact["separation_m"],
            "xy_distance_from_global_lowest_m": float(np.linalg.norm(point[:2] - lowest[:2])),
            "raw_hull_lower_surface_at_contact_xy_m": raw_height,
            "physx_separation_minus_raw_surface_m": (
                contact["separation_m"] - raw_height if raw_height is not None else None
            ),
        })
    if not loaded or event["contact_manifold"]["box"]:
        raise ValueError("Expected loaded ground points and no box points")

    result = {
        "schema_version": 1,
        "seed": report["seed"],
        "collision_profile_sha256": digest(args.collision_profile),
        "runtime_frame_report_sha256": digest(args.runtime_frame),
        "manifold_report_sha256": digest(args.manifold_report),
        "analysis_source_sha256": digest(Path(__file__)),
        "base_root_pose_equal_in_runtime_probe": True,
        "event_push_control_step": event["push_control_step"],
        "event_physics_substep": event["physics_substep"],
        "raw_hull_global_lowest_point_w": lowest.tolist(),
        "loaded_ground_points": loaded,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x", encoding="utf-8") as output:
        json.dump(result, output, indent=2, allow_nan=False)
    print(json.dumps({"seed": report["seed"], "loaded_points": len(loaded),
                      "raw_lower_surface_found": all(point["raw_hull_lower_surface_at_contact_xy_m"]
                                                     is not None for point in loaded)}))


if __name__ == "__main__":
    main()
