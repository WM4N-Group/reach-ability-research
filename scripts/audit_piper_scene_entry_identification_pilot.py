"""Audit an independent scene/entry capture pilot without issuing a certificate."""

import argparse
import hashlib
import json
from pathlib import Path

from piper_scene_runtime_observation import canonical_sha256


SCENE_CORE_FIELDS = (
    "robot_usd", "collision_prims", "ground_prim",
    "ground_usd_material", "ground_cfg", "box_size_m", "box_spawn",
    "physics_dt_s", "physx_cfg", "robot_articulation_cfg", "control_decimation",
    "control_dt_s", "reset_cfg", "safety_cfg", "source_sha256",
)


def file_sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stable_layers(layers):
    return sorted(({
        "kind": layer["kind"],
        "identifier": (layer["identifier"].rsplit(":", 1)[-1]
                       if layer["kind"] == "anonymous" else layer["identifier"]),
        "sha256": layer["sha256"],
    } for layer in layers), key=lambda item: (item["identifier"], item["sha256"]))


def audit(protocol_path, report_dir):
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    seeds = protocol["seeds_in_order"]
    if len(seeds) != len(set(seeds)) or not seeds:
        raise ValueError("Protocol seeds are empty or repeated")
    reports = sorted(report_dir.glob("seed*.json"))
    if {path.name for path in reports} != {f"seed{seed}.json" for seed in seeds}:
        raise ValueError("Report set differs from the preregistered denominator")
    logs = sorted(report_dir.glob("seed*.log"))
    if {path.name for path in logs} != {f"seed{seed}.log" for seed in seeds}:
        raise ValueError("Log set differs from the preregistered denominator")
    records = []
    core_digests = []
    for seed in seeds:
        path = report_dir / f"seed{seed}.json"
        log_path = report_dir / f"seed{seed}.log"
        if not log_path.stat().st_size:
            raise ValueError(f"Empty log for seed{seed}")
        report = json.loads(path.read_text(encoding="utf-8"))
        observed = report["scene_runtime_observation"]
        sources = observed["source_sha256"]
        control = protocol["control"]
        if (report["schema_version"] != 23 or report["seed"] != seed
                or observed["seed"] != seed or report["task"] != protocol["task"]
                or report["nav_actor_sha256"] != protocol["nav_actor_sha256"]
                or report["push_checkpoint_sha256"] != protocol["push_checkpoint_sha256"]
                or sources["diagnostic"] != protocol["diagnostic_sha256"]
                or sources["scene_observer"] != protocol["observer_sha256"]
                or sources["piper_box_env_cfg"] != protocol["remote_source_piper_cfg_sha256"]
                or report["nav_start_x_m"] != control["nav_start_x_m"]
                or report["nav_goal_xyyaw"] != [control["nav_goal_x_m"], 0.0, 0.0]
                or report["nav_arm_home"] is not control["nav_arm_home"]
                or report["nav_timeout_s"] != control["nav_timeout_s"]
                or report["push_budget_s"] != control["push_budget_s"]
                or observed["physics_dt_s"] != control["physics_dt_s"]
                or observed["control_dt_s"] != control["control_dt_s"]
                or any(not report[key] for key in (
                    "record_push_support_trace", "record_push_contact_load_trace",
                    "record_leg_jacobian_trace", "record_base_contact_source"))
                or report["skip_nav"] or report["handoff_settle_stable_s"]
                or any(report[key] for key in (
                    "front_foot_feedback", "nav_leg_support_until_ready",
                    "pre_ready_leg_action_cap", "hold_push_arm_at_handoff",
                    "front_foot_probe_offset_m", "front_foot_hold_offset_m",
                    "support_margin_pause_m", "record_base_contact_substeps",
                    "record_base_contact_manifold", "record_recovery_decision_state"))
                or report["safe_approach_arm_rate_scale"] != 1.0):
            raise ValueError(f"Frozen input or control differs for seed{seed}")
        if (observed["scope"] != "same_rollout_runtime_observation_only"
                or observed["unresolved_layers"]
                or observed["scene_contract_sha256"] is not None
                or observed["entry_distribution_sha256"] is not None
                or canonical_sha256(observed) != report["scene_runtime_observation_sha256"]):
            raise ValueError(f"Scene observation integrity or scope differs for seed{seed}")
        collision = observed["collision_prims"]
        roots = ("/World/envs/env_0/Robot/", "/World/envs/env_0/Box/")
        paths = [item["path"] for item in collision]
        if (len(paths) != len(set(paths)) or not all(any(path.startswith(root) for root in roots)
                or path == observed["ground_prim"] for path in paths)
                or observed["ground_prim"] not in paths
                or not any(item["instance_proxy"] for item in collision)
                or not observed["ground_usd_material"]["material_path"]):
            raise ValueError(f"Collision or USD material capture is incomplete for seed{seed}")
        material = observed["ground_usd_material"]["material_attributes"]
        ground_cfg = observed["ground_cfg"]["physics_material"]
        if (material["physics:staticFriction"] != ground_cfg["static_friction"]
                or material["physics:dynamicFriction"] != ground_cfg["dynamic_friction"]
                or material["physxMaterial:frictionCombineMode"] != ground_cfg["friction_combine_mode"]):
            raise ValueError(f"Ground USD material differs from final configuration for seed{seed}")
        entered_push = "handoff" in report
        if entered_push:
            entry = report["handoff_entry_observation"]
            if canonical_sha256(entry) != report["handoff_entry_observation_sha256"]:
                raise ValueError(f"Handoff entry digest differs for seed{seed}")
        elif report["outcome"] != "nav_timeout" or "handoff_entry_observation" in report:
            raise ValueError(f"Absent handoff is not a NAV timeout for seed{seed}")
        core = {key: observed[key] for key in SCENE_CORE_FIELDS}
        core["used_layers"] = stable_layers(observed["used_layers"])
        core_digest = canonical_sha256(core)
        core_digests.append(core_digest)
        records.append({
            "seed": seed,
            "report_sha256": file_sha256(path),
            "log_sha256": file_sha256(log_path),
            "outcome": report["outcome"],
            "terminal_reasons": sorted(key for key, active in
                                       report.get("terminal", {}).get("reasons", {}).items() if active),
            "entered_push": entered_push,
            "scene_core_sha256": core_digest,
            "stage_export_sha256": observed["stage_export_sha256"],
            "robot_material_sha256": canonical_sha256(observed["robot_material"]),
            "box_material_sha256": canonical_sha256(observed["box_material"]),
            "handoff_entry_observation_sha256": report.get("handoff_entry_observation_sha256"),
        })
    return {
        "schema_version": 1,
        "scope": "independent_scene_entry_identification_pilot_only",
        "protocol_sha256": file_sha256(protocol_path),
        "scene_case": protocol["scene_case"],
        "complete_denominator": len(records),
        "scene_core_identical_across_seeds": len(set(core_digests)) == 1,
        "stage_export_identical_across_seeds": len({record["stage_export_sha256"]
                                                   for record in records}) == 1,
        "robot_material_identical_across_seeds": len({record["robot_material_sha256"]
                                                     for record in records}) == 1,
        "records": records,
        "scene_contract_sha256": None,
        "entry_distribution_sha256": None,
        "contact_authorized": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol-json", type=Path, required=True)
    parser.add_argument("--report-dir", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.protocol_json, args.report_dir)
    with args.output_json.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
    print(json.dumps({key: result[key] for key in (
        "complete_denominator", "scene_core_identical_across_seeds",
        "scene_contract_sha256", "entry_distribution_sha256")}))


if __name__ == "__main__":
    main()
