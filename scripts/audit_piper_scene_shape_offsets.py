"""Audit the frozen read-only PhysX shape-offset probe."""

import argparse
import hashlib
import json
import math
from pathlib import Path


def file_sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_shape(shape, expected_path):
    if (shape["prim_paths"] != [expected_path] or shape["shape_count"] != 1
            or any(len(shape[key]) != 1 for key in (
                "contact_offsets_m", "rest_offsets_m", "material_properties"))
            or len(shape["material_properties"][0]) != 3):
        raise ValueError(f"Unexpected PhysX shape view for {expected_path}")
    values = (shape["contact_offsets_m"] + shape["rest_offsets_m"]
              + shape["material_properties"][0])
    if any(not math.isfinite(value) for value in values):
        raise ValueError(f"Non-finite PhysX shape value for {expected_path}")
    if shape["contact_offsets_m"][0] < 0:
        raise ValueError(f"Negative contact offset for {expected_path}")


def audit(protocol_path, report_path, log_path):
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    report = json.loads(report_path.read_text(encoding="utf-8"))
    probe_path = Path(__file__).with_name("probe_piper_scene_shape_offsets.py")
    if (protocol["schema_version"] != 1
            or file_sha256(probe_path) != protocol["probe_sha256"]
            or report["probe_sha256"] != protocol["probe_sha256"]
            or report["robot_usd_sha256"] != protocol["robot_usd_sha256"]
            or report["schema_version"] != 1
            or report["scope"] != "same_loaded_scene_read_only_shape_offset_probe"
            or report["task"] != protocol["task"]
            or report["physics_dt_s"] != 0.005
            or report["control_decimation"] != 4
            or report["policy_loaded"] or report["rollout_executed"]
            or report["scene_contract_sha256"] is not None
            or report["entry_distribution_sha256"] is not None
            or report["contact_authorized"]):
        raise ValueError("Frozen source, runtime grid or probe scope differs")
    if (not log_path.stat().st_size or
            "SCENE_SHAPE_OFFSET_PROBE=" not in log_path.read_text(encoding="utf-8")):
        raise ValueError("Probe completion marker missing from nonempty log")
    check_shape(report["base_shapes"], "/World/envs/env_0/Robot/base")
    check_shape(report["box_shapes"], "/World/envs/env_0/Box")
    if (report["ground_prim"] != protocol["ground_prim"]
            or report["ground_prim_type"] != "Plane"
            or not report["ground_usd_physics_material_path"]):
        raise ValueError("Loaded ground prim or USD material differs")
    ground = report["ground_physx_rigid_view_query"]
    if ground["status"] == "rigid_body_view_available":
        check_shape(ground["offsets"], protocol["ground_prim"])
        ground_offsets = ground["offsets"]
    elif ground["status"] in ("no_rigid_body_view", "rigid_body_view_error"):
        if ground["offsets"] is not None:
            raise ValueError("Unavailable ground view must not carry offsets")
        ground_offsets = None
    else:
        raise ValueError("Unexpected ground query status")
    return {
        "schema_version": 1,
        "scope": "read_only_shape_offset_probe_audit",
        "protocol_sha256": file_sha256(protocol_path),
        "probe_sha256": report["probe_sha256"],
        "report_sha256": file_sha256(report_path),
        "log_sha256": file_sha256(log_path),
        "robot_usd_sha256": report["robot_usd_sha256"],
        "base_contact_offset_m": report["base_shapes"]["contact_offsets_m"][0],
        "base_rest_offset_m": report["base_shapes"]["rest_offsets_m"][0],
        "box_contact_offset_m": report["box_shapes"]["contact_offsets_m"][0],
        "box_rest_offset_m": report["box_shapes"]["rest_offsets_m"][0],
        "ground_query_status": ground["status"],
        "ground_runtime_offsets": ground_offsets,
        "ground_usd_authored_offsets": report["ground_authored_offsets"],
        "scene_contract_sha256": None,
        "entry_distribution_sha256": None,
        "contact_authorized": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol-json", type=Path, required=True)
    parser.add_argument("--report-json", type=Path, required=True)
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.protocol_json, args.report_json, args.log)
    with args.output_json.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({key: result[key] for key in (
        "base_contact_offset_m", "box_contact_offset_m", "ground_query_status",
        "scene_contract_sha256")}))


if __name__ == "__main__":
    main()
