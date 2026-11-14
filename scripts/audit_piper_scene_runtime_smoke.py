"""Verify the seen-seed scene capture against its frozen baseline and evidence index."""

import argparse
import hashlib
import json
from pathlib import Path

from piper_scene_runtime_observation import canonical_sha256


BASELINE_FIELDS = (
    "outcome", "handoff", "support_trace", "terminal", "push_executed_steps",
    "push_elapsed_s",
)


def file_sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(report_path, baseline_path, evidence_path):
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    if (file_sha256(report_path) != evidence["report_sha256"]
            or file_sha256(baseline_path) != evidence["baseline_report_sha256"]):
        raise ValueError("Report or baseline hash differs from the evidence index")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    if (report["seed"] != evidence["seed"] or baseline["seed"] != evidence["seed"]
            or report["schema_version"] != 23
            or any(report[key] != baseline[key] for key in BASELINE_FIELDS)
            or list(BASELINE_FIELDS) != evidence["baseline_comparison"]["fields"]
            or evidence["baseline_comparison"]["exactly_equal"] is not True):
        raise ValueError("Seen-seed trajectory differs from the frozen baseline")
    observation = report["scene_runtime_observation"]
    if (observation["scope"] != "same_rollout_runtime_observation_only"
            or observation["seed"] != evidence["seed"]
            or observation["scene_contract_sha256"] is not None
            or observation["entry_distribution_sha256"] is not None
            or evidence["scene_contract_sha256"] is not None
            or evidence["entry_distribution_sha256"] is not None
            or evidence["contact_authorized"] is not False):
        raise ValueError("Runtime observation was misrepresented as a certificate")
    for key, value in (("scene_runtime_observation", observation),
                       ("handoff_entry_observation", report["handoff_entry_observation"])):
        digest = canonical_sha256(value)
        if digest != report[key + "_sha256"] or digest != evidence[key + "_sha256"]:
            raise ValueError(f"{key} digest differs")
    if (observation["robot_usd"]["sha256"] != evidence["robot_usd_sha256"]
            or observation["source_sha256"] != evidence["runtime_source_sha256"]
            or observation["source_sha256"]["diagnostic"] != evidence["diagnostic_sha256"]
            or observation["source_sha256"]["scene_observer"] != evidence["observer_sha256"]
            or len(observation["used_layers"]) != evidence["used_layers"]
            or observation["unresolved_layers"] is not evidence["unresolved_layers"]
            or len(observation["collision_prims"]) != evidence["selected_collision_prims"]
            or observation["box_mass_kg"] != [evidence["actual_box_mass_kg"]]
            or observation["box_material"][0][0][:2] != evidence["actual_box_static_dynamic_friction"]
            or observation["physics_dt_s"] != evidence["physics_dt_s"]
            or observation["control_decimation"] != evidence["control_decimation"]):
        raise ValueError("Runtime physics facts differ from the evidence index")
    if evidence.get("runtime_config_observed"):
        if (len(observation["robot_mass_kg"][0]) != evidence["robot_body_count"]
                or len(observation["robot_material"][0]) != evidence["robot_material_entries"]
                or observation["source_sha256"]["safe_approach_resource"]
                != evidence["safe_approach_resource_sha256"]
                or observation["physx_cfg"]["solver_type"] != evidence["physx_solver_type"]
                or observation["reset_cfg"]["base"]["pose_range"] != evidence["base_reset_pose_range"]
                or observation["safety_cfg"]["base_contact_threshold_n"]
                != evidence["base_contact_threshold_n"]
                or observation["safety_cfg"]["arm_body_clearance_m"]
                != evidence["arm_body_clearance_m"]
                or len(observation["safety_cfg"]["safe_approach_waypoints"])
                != evidence["safe_approach_waypoint_count"]):
            raise ValueError("Runtime configuration facts differ from the evidence index")
    if evidence.get("runtime_usd_binding_observed"):
        if (observation["ground_usd_material"] != evidence["ground_usd_material"]
                or sum(prim["instance_proxy"] for prim in observation["collision_prims"])
                != evidence["instance_proxy_collision_prims"]):
            raise ValueError("Runtime USD binding or instance collision inventory differs")
    return {"seed": evidence["seed"], "baseline_fields_equal": True,
            "layers_hashed": len(observation["used_layers"]),
            "scene_contract_sha256": None, "entry_distribution_sha256": None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report-json", type=Path, required=True)
    parser.add_argument("--baseline-json", type=Path, required=True)
    parser.add_argument("--evidence-json", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args.report_json, args.baseline_json, args.evidence_json)))


if __name__ == "__main__":
    main()
