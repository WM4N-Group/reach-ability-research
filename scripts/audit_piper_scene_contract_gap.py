"""Audit which scene identity facts are actually recorded by a NAV-to-PUSH cohort."""

import argparse
import hashlib
import json
import math
import re
from pathlib import Path

from audit_piper_nav_push_baseline_cohort import describe


MISSING_PROOF = (
    "rollout_bound_robot_usd_and_all_used_layer_hashes",
    "rollout_bound_box_geometry_mass_and_material",
    "rollout_bound_ground_geometry_and_material",
    "rollout_bound_layout_generator_and_reset_distribution",
    "rollout_bound_solver_contact_and_physics_configuration",
    "runtime_probe_to_each_rollout_identity_link",
    "nav_handoff_entry_distribution_contract",
)
IDENTITY_FIELDS = (
    "scene_case",
    "scene_contract_sha256",
    "entry_distribution_sha256",
    "robot_usd_sha256",
    "scene_manifest_sha256",
)


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def common(reports, key):
    values = [report.get(key) for report in reports]
    if any(value is None for value in values) or any(value != values[0] for value in values[1:]):
        raise ValueError(f"Missing or inconsistent cohort field: {key}")
    return values[0]


def absent_identity_fields(reports):
    present = {key: [report["seed"] for report in reports if key in report]
               for key in IDENTITY_FIELDS}
    present = {key: seeds for key, seeds in present.items() if seeds}
    if present:
        raise ValueError(f"Historical reports now contain scene identity fields: {present}")
    return list(IDENTITY_FIELDS)


def validate_probe(probe, task, ground_prim, step_dt):
    usd_hash = probe.get("usd_sha256")
    if (probe.get("scope") != "read_only_loaded_isaac_collision_prim_probe"
            or probe.get("policy_loaded") is not False
            or probe.get("rollout_executed") is not False
            or probe.get("task") != task
            or ground_prim not in probe.get("ground_collision_prims", [])
            or not isinstance(usd_hash, str)
            or not re.fullmatch(r"[0-9a-f]{64}", usd_hash)):
        raise ValueError("Runtime probe provenance, task or loaded ground prim differs")
    physics_dt = probe.get("physics_dt_s")
    decimation = probe.get("control_decimation")
    if (isinstance(physics_dt, bool) or not isinstance(physics_dt, (int, float))
            or not math.isfinite(physics_dt) or physics_dt <= 0
            or isinstance(decimation, bool) or not isinstance(decimation, int) or decimation <= 0
            or not math.isclose(physics_dt * decimation, step_dt, rel_tol=0, abs_tol=1e-9)):
        raise ValueError("Runtime probe physics grid differs from cohort control grid")
    return physics_dt, decimation


def audit(protocol_path, reports_dir, probe_path):
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    seeds = protocol["seeds_in_order"]
    if (seeds != list(range(5701, 5725)) or len(set(seeds)) != len(seeds)
            or len(list(reports_dir.glob("seed*-baseline.json"))) != len(seeds)):
        raise ValueError("Expected the complete frozen seed5701-5724 baseline")
    paths = [reports_dir / f"seed{seed}-baseline.json" for seed in seeds]
    cases = [describe(seed, path, protocol) for seed, path in zip(seeds, paths)]
    reports = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
    probe = json.loads(probe_path.read_text(encoding="utf-8"))

    task = common(reports, "task")
    step_dt = common(reports, "step_dt")
    ground_prim = common(reports, "ground_filter_prim")
    control = common(reports, "control_sha256")
    nav_actor = common(reports, "nav_actor_sha256")
    push_checkpoint = common(reports, "push_checkpoint_sha256")
    absent_fields = absent_identity_fields(reports)
    physics_dt, decimation = validate_probe(probe, task, ground_prim, step_dt)

    return {
        "schema_version": 1,
        "scope": "read_only_scene_contract_gap_audit",
        "protocol_sha256": sha256(protocol_path),
        "runtime_probe_sha256": sha256(probe_path),
        "cohort_size": len(cases),
        "report_sha256_by_seed": {str(case["seed"]): case["report_sha256"] for case in cases},
        "qualified_push_traces": sum(case["push_samples"] > 0 and case["sensor_qualified"] for case in cases),
        "report_identity_fields_absent": absent_fields,
        "observed_provenance_not_identity_proof": {
            "task": task,
            "nav_actor_sha256": nav_actor,
            "push_checkpoint_sha256": push_checkpoint,
            "control_sha256": control,
            "control_step_dt_s": step_dt,
            "probe_physics_dt_s": physics_dt,
            "probe_control_decimation": decimation,
            "ground_collision_prim": ground_prim,
            "probe_robot_usd_sha256": probe["usd_sha256"],
        },
        "probe_was_same_rollout": False,
        "missing_proof": list(MISSING_PROOF),
        "scene_contract_sha256": None,
        "entry_distribution_sha256": None,
        "decision": "abstain_scene_and_entry_identity_unqualified",
        "interpretation": (
            "A later read-only runtime probe matches task, grid and ground prim but is not linked "
            "to any cohort rollout. Its USD hash cannot be assigned to those rollouts. "
            "No scene or entry-distribution identity is certified."
        ),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol-json", type=Path, required=True)
    parser.add_argument("--reports-dir", type=Path, required=True)
    parser.add_argument("--runtime-probe-json", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error("Output already exists")
    result = audit(args.protocol_json, args.reports_dir, args.runtime_probe_json)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")
    print(json.dumps({key: result[key] for key in (
        "cohort_size", "qualified_push_traces", "decision", "scene_contract_sha256"
    )}))


if __name__ == "__main__":
    main()
