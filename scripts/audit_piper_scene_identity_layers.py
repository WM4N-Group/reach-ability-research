"""Separate observed scene configuration, episode instance and handoff entry."""

import argparse
import json
from pathlib import Path

from audit_piper_scene_entry_identification_pilot import (
    SCENE_CORE_FIELDS, audit as audit_pilot, file_sha256, stable_layers,
)
from piper_scene_runtime_observation import canonical_sha256


UNRESOLVED_QUALIFICATION = (
    "runtime_solver_cooked_collision_shapes",
    "runtime_ground_contact_and_rest_offsets",
    "layout_random_stream_and_instance_generation_contract",
    "conditional_nav_handoff_entry_distribution",
    "joint_state_transition_observation_contact_and_delay_coverage",
)


def project_layers(report):
    observed = report["scene_runtime_observation"]
    if (observed["schema_version"] != 1
            or observed["scope"] != "same_rollout_runtime_observation_only"
            or observed["seed"] != report["seed"]
            or observed["unresolved_layers"]
            or observed["scene_contract_sha256"] is not None
            or observed["entry_distribution_sha256"] is not None
            or canonical_sha256(observed) != report["scene_runtime_observation_sha256"]):
        raise ValueError("Same-run scene observation integrity or scope differs")

    core = {key: observed[key] for key in SCENE_CORE_FIELDS}
    core["used_layers"] = stable_layers(observed["used_layers"])
    configuration = {
        "scene_core_sha256": canonical_sha256(core),
        "nav_actor_sha256": report["nav_actor_sha256"],
        "push_checkpoint_sha256": report["push_checkpoint_sha256"],
        "control_sha256": report["control_sha256"],
    }
    instance = {
        "stage_export_sha256": observed["stage_export_sha256"],
        "robot_mass_kg": observed["robot_mass_kg"],
        "robot_material": observed["robot_material"],
        "box_mass_kg": observed["box_mass_kg"],
        "box_material": observed["box_material"],
        "initial_state": report["initial_state"],
    }
    if "handoff" in report:
        entry = report["handoff_entry_observation"]
        if canonical_sha256(entry) != report["handoff_entry_observation_sha256"]:
            raise ValueError("Same-run handoff entry digest differs")
        entry_digest = canonical_sha256(entry)
    elif report["outcome"] == "nav_timeout" and "handoff_entry_observation" not in report:
        entry_digest = None
    else:
        raise ValueError("Handoff entry missing without NAV timeout")
    return {
        "configuration_sha256": canonical_sha256(configuration),
        "scene_core_sha256": configuration["scene_core_sha256"],
        "instance_observation_sha256": canonical_sha256(instance),
        "entry_observation_sha256": entry_digest,
        "full_scene_observation_sha256": report["scene_runtime_observation_sha256"],
    }


def audit(protocol_path, report_dir):
    pilot = audit_pilot(protocol_path, report_dir)
    records = []
    for source in pilot["records"]:
        path = report_dir / f"seed{source['seed']}.json"
        if file_sha256(path) != source["report_sha256"]:
            raise ValueError("Pilot report changed during layered audit")
        report = json.loads(path.read_text(encoding="utf-8"))
        layers = project_layers(report)
        if (layers["scene_core_sha256"] != source["scene_core_sha256"]
                or layers["entry_observation_sha256"]
                != source["handoff_entry_observation_sha256"]):
            raise ValueError("Layer projection differs from pilot audit")
        records.append({
            "seed": source["seed"],
            "report_sha256": source["report_sha256"],
            "outcome": source["outcome"],
            "entered_push": source["entered_push"],
            **layers,
        })
    return {
        "schema_version": 1,
        "scope": "observed_identity_layers_only",
        "protocol_sha256": pilot["protocol_sha256"],
        "complete_denominator": pilot["complete_denominator"],
        "configuration_groups": len({row["configuration_sha256"] for row in records}),
        "instance_observations": len({row["instance_observation_sha256"] for row in records}),
        "handoff_entry_observations": len({row["entry_observation_sha256"] for row in records
                                           if row["entry_observation_sha256"] is not None}),
        "records": records,
        "unresolved_qualification": list(UNRESOLVED_QUALIFICATION),
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
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({key: result[key] for key in (
        "complete_denominator", "configuration_groups", "instance_observations",
        "handoff_entry_observations", "scene_contract_sha256")}))


if __name__ == "__main__":
    main()
