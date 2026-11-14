"""Read-only base-collider height projection from frozen PUSH control-step logs."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation


ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def projected_state(state: dict, vertices: np.ndarray, fixed_index: int) -> dict:
    position = np.asarray(state["base_pos"], dtype=float)
    quaternion = np.asarray(state["base_quat"], dtype=float)
    velocity = np.asarray(state["base_vel_w"], dtype=float)
    omega = np.asarray(state["base_omega_w"], dtype=float)
    if (any(value.shape != (size,) for value, size in
            ((position, 3), (quaternion, 4), (velocity, 3), (omega, 3)))
            or not all(np.isfinite(value).all() for value in
                       (position, quaternion, velocity, omega))
            or np.linalg.norm(quaternion) < 1e-8):
        raise ValueError("Invalid root pose or world velocity")
    rotation = Rotation.from_quat(quaternion, scalar_first=True).as_matrix()
    heights = position[2] + vertices @ rotation[2]
    active = int(np.argmin(heights))
    fixed_arm = rotation @ vertices[fixed_index]
    return {
        "active_vertex": active,
        "minimum_height_m": float(heights[active]),
        "fixed_height_m": float(heights[fixed_index]),
        "fixed_height_rate_m_s": float(velocity[2] + np.cross(omega, fixed_arm)[2]),
    }


def analyze(manifest_path: Path, projection_path: Path, projection_summary_path: Path,
            profile_path: Path) -> dict:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    projection_summary = json.loads(projection_summary_path.read_text(encoding="utf-8"))
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    if (projection_summary["output_jsonl_sha256"] != sha256(projection_path)
            or projection_summary["cohort_manifest_sha256"] != sha256(manifest_path)
            or projection_summary["contact_authorized"]
            or projection_summary["full_physx_markov_state_recorded"]):
        raise ValueError("Frozen projection provenance or diagnostic scope changed")
    for relative, expected in profile["usd_sha256"].items():
        if sha256(ROOT / relative) != expected:
            raise ValueError(f"USD asset changed: {relative}")
    base_shapes = [shape for shape in profile["shapes"] if shape["body"] == "base_link"]
    if (len(base_shapes) != 1 or base_shapes[0]["kind"] != "Mesh"
            or base_shapes[0]["position"] != [0.0, 0.0, 0.0]
            or base_shapes[0]["quaternion"] != [1.0, 0.0, 0.0, 0.0]):
        raise ValueError("Expected one base-frame convex-hull mesh")
    vertices = np.asarray(base_shapes[0]["vertices"], dtype=float)
    if vertices.ndim != 2 or vertices.shape[1] != 3 or not np.isfinite(vertices).all():
        raise ValueError("Invalid base hull vertices")
    reports = {row["seed"]: row for row in manifest["reports"]}
    if len(reports) != manifest["complete_denominator"]:
        raise ValueError("Manifest denominator mismatch")
    states: dict[int, dict] = {}
    pairs = 0
    with projection_path.open(encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            seed = row["seed"]
            if seed not in reports or row["source_report_sha256"] != reports[seed]["sha256"]:
                raise ValueError("Transition report is outside the frozen cohort")
            pre = row["pre_action_physical_projection"]
            post = row["post_action_physical_projection"]
            if seed not in states:
                if reports[seed]["outcome"] == "nav_timeout":
                    raise ValueError("NAV timeout has a PUSH transition")
                initial = projected_state(pre, vertices, 0)
                fixed_index = initial["active_vertex"]
                first = projected_state(pre, vertices, fixed_index)
                states[seed] = {
                    "fixed_vertex_index": fixed_index,
                    "samples": 1,
                    "sampled_minimum_height_m": first["minimum_height_m"],
                    "sampled_fixed_minimum_height_m": first["fixed_height_m"],
                    "active_vertex_switches": 0,
                    "last_active_vertex": first["active_vertex"],
                    "last_post": pre,
                    "terminal": first,
                    "terminal_time_s": row["pre_time_s"],
                }
            record = states[seed]
            if pre != record["last_post"]:
                raise ValueError("Nonconsecutive physical projection")
            current = projected_state(post, vertices, record["fixed_vertex_index"])
            record["samples"] += 1
            record["sampled_minimum_height_m"] = min(
                record["sampled_minimum_height_m"], current["minimum_height_m"])
            record["sampled_fixed_minimum_height_m"] = min(
                record["sampled_fixed_minimum_height_m"], current["fixed_height_m"])
            record["active_vertex_switches"] += (
                current["active_vertex"] != record["last_active_vertex"])
            record["last_active_vertex"] = current["active_vertex"]
            record["last_post"] = post
            record["terminal"] = current
            record["terminal_time_s"] = row["post_time_s"]
            pairs += 1
    if pairs != projection_summary["aligned_transition_pairs"]:
        raise ValueError("Transition count mismatch")
    result_rows = []
    for seed, source in sorted(reports.items()):
        record = states.get(seed)
        if (record is None) != (source["outcome"] == "nav_timeout"):
            raise ValueError("PUSH entrant count does not match outcome")
        if record is not None:
            del record["last_post"]
            del record["last_active_vertex"]
        result_rows.append({"seed": seed, "outcome": source["outcome"],
                            "geometry": record})
    return {
        "schema_version": 1,
        "scope": "sampled_base_hull_height_diagnostic_only",
        "manifest_sha256": sha256(manifest_path),
        "projection_sha256": sha256(projection_path),
        "profile_sha256": sha256(profile_path),
        "base_hull_vertices": len(vertices),
        "total_nav_starts": len(result_rows),
        "push_entrants": len(states),
        "aligned_transition_pairs": pairs,
        "rows": result_rows,
        "base_contact_event_bridge_proven": False,
        "dynamics_bound_proven": False,
        "contact_authorized": False,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("projection", type=Path)
    parser.add_argument("projection_summary", type=Path)
    parser.add_argument("profile", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = analyze(args.manifest, args.projection, args.projection_summary,
                     args.profile)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({key: result[key] for key in
                      ("scope", "total_nav_starts", "push_entrants",
                       "aligned_transition_pairs", "contact_authorized")}, indent=2))
