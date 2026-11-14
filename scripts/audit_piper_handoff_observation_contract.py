"""Audit logged PUSH decision observations without inferring a reachability bound."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def finite_vector(values: object, size: int) -> bool:
    return (isinstance(values, list) and len(values) == size
            and all(isinstance(value, (int, float)) and not isinstance(value, bool)
                    and math.isfinite(value) for value in values))


def audit_trace(report: dict, seed: int) -> int:
    trace = report["support_trace"]
    if (not report["record_recovery_decision_state"]
            or report["schema_version"] != 18
            or report["front_foot_feedback"] is not False
            or report.get("support_response_probe") is not None
            or len(trace) != report["push_executed_steps"]):
        raise ValueError(f"seed{seed}: incomplete decision-state recording")
    if report["outcome"] == "nav_timeout":
        if trace or report["push_executed_steps"]:
            raise ValueError(f"seed{seed}: NAV timeout has PUSH samples")
        return 0
    if report["outcome"] != "push_terminated" or not trace:
        raise ValueError(f"seed{seed}: unexpected PUSH outcome or empty trace")
    handoff = report["handoff"]
    if (handoff["push_actor_input_groups"] != ["policy", "box"]
            or handoff["push_observation_shape"] != [1, 226]
            or handoff["first_push_actor_input"]
            != trace[0]["recovery_decision_state"]["actor_input_before_action"]):
        raise ValueError(f"seed{seed}: PUSH actor input grouping or handoff differs")

    step_dt = report["step_dt"]
    budget = report["push_budget_s"]
    if step_dt != 0.02 or budget != 12.0 or len(trace) * step_dt > budget + 1e-9:
        raise ValueError(f"seed{seed}: PUSH timing or budget differs")
    previous_next_input = None
    for index, record in enumerate(trace):
        decision = record["recovery_decision_state"]
        if not isinstance(decision, dict):
            raise ValueError(f"seed{seed}: missing decision state at step {index}")
        arm = decision["arm_controller"]
        vectors = (
            (record["base_pos"], 3), (record["base_quat"], 4),
            (record["foot_normal_forces_n"], 4),
            (record["joint_pos"], 18), (record["joint_vel"], 18),
            (record["joint_pos_target"], 18),
            (decision["base_vel_w"], 3), (decision["base_omega_w"], 3),
            (decision["box_pos"], 3), (decision["box_quat"], 4),
            (decision["box_vel_w"], 3), (decision["box_omega_w"], 3),
            (decision["actor_input_before_action"], 226),
            (decision["actor_action_before_step"], 12),
            (arm["reference"], 6), (arm["velocity_integral"], 2),
        )
        if any(not finite_vector(values, size) for values, size in vectors):
            raise ValueError(f"seed{seed}: missing or nonfinite decision vector at step {index}")
        if (not isinstance(decision["settled_contact_seen"], bool)
                or not isinstance(decision["settled_duration_s"], (int, float))
                or not math.isfinite(decision["settled_duration_s"])):
            raise ValueError(f"seed{seed}: invalid terminal monitor memory at step {index}")
        if (not math.isclose(record["push_elapsed_s"], (index + 1) * step_dt,
                             rel_tol=0.0, abs_tol=1e-8)
                or arm["safe_approach_index"] != record["arm_approach_index"]
                or arm["motion_ready"] != record["motion_ready"]
                or arm["reference"] != record["arm_reference"]
                or (previous_next_input is not None
                    and previous_next_input != decision["actor_input_before_action"])):
            raise ValueError(f"seed{seed}: time, controller or actor history mismatch at step {index}")
        next_input = decision["next_actor_input"]
        if index + 1 < len(trace) and not finite_vector(next_input, 226):
            raise ValueError(f"seed{seed}: missing next actor input at step {index}")
        if index + 1 == len(trace) and next_input is not None:
            raise ValueError(f"seed{seed}: terminal step unexpectedly has a next actor input")
        previous_next_input = next_input
    return len(trace)


def audit(manifest_path: Path, report_dir: Path) -> dict:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest["schema_version"] != 1 or len(manifest["reports"]) != 24:
        raise ValueError("Expected frozen 24-seed cohort manifest")
    outcomes = Counter()
    rows = []
    source_sha256 = None
    for entry in manifest["reports"]:
        seed = entry["seed"]
        report_path = report_dir / f"seed{seed}-baseline.json"
        if sha256(report_path) != entry["sha256"]:
            raise ValueError(f"seed{seed}: report SHA-256 differs from frozen manifest")
        report = json.loads(report_path.read_text(encoding="utf-8"))
        if report["seed"] != seed or not 5801 <= seed <= 5824:
            raise ValueError(f"seed{seed}: seed identity differs")
        source = {
            "control": report["control_sha256"],
            "nav_actor": report["nav_actor_sha256"],
            "push_checkpoint": report["push_checkpoint_sha256"],
        }
        if source_sha256 is None:
            source_sha256 = source
        elif source_sha256 != source:
            raise ValueError(f"seed{seed}: policy or control source differs")
        samples = audit_trace(report, seed)
        if entry["outcome"] == "nav_timeout":
            if report["outcome"] != "nav_timeout":
                raise ValueError(f"seed{seed}: NAV outcome differs")
        elif (report["outcome"] != "push_terminated"
              or report["terminal"]["reasons"].get(entry["outcome"]) is not True):
            raise ValueError(f"seed{seed}: PUSH terminal reason differs")
        outcomes[entry["outcome"]] += 1
        rows.append({"seed": seed, "outcome": entry["outcome"],
                     "decision_samples": samples, "report_sha256": entry["sha256"]})
    if (len({row["seed"] for row in rows}) != 24 or source_sha256 is None
            or dict(outcomes) != manifest["outcome_counts"]
            or sum(row["decision_samples"] > 0 for row in rows) != manifest["push_entrants"]):
        raise ValueError("Cohort denominator, source or outcome mismatch")
    return {
        "schema_version": 1,
        "scope": "logged_observation_projection_only",
        "cohort_manifest_sha256": sha256(manifest_path),
        "audit_script_sha256": sha256(Path(__file__)),
        "source_sha256": source_sha256,
        "total_nav_starts": len(rows),
        "push_entrants": manifest["push_entrants"],
        "complete_decision_traces": sum(row["decision_samples"] > 0 for row in rows),
        "total_decision_samples": sum(row["decision_samples"] for row in rows),
        "outcome_counts": dict(outcomes),
        "field_contract": {
            "base_position_quaternion": [3, 4],
            "base_linear_angular_velocity_world": [3, 3],
            "box_position_quaternion_linear_angular_velocity": [3, 4, 3, 3],
            "foot_normal_forces": 4,
            "joint_position_velocity_target": [18, 18, 18],
            "actor_input_action": [226, 12],
            "actor_input_groups": {"policy": 210, "box": 16},
            "next_actor_input_nonterminal": 226,
            "arm_reference_velocity_integral": [6, 2],
            "step_dt_s": 0.02,
            "push_budget_s": 12.0,
        },
        "full_physx_markov_state_recorded": False,
        "deployment_sensor_contract_validated": False,
        "joint_state_transition_observation_coverage_bound": None,
        "control_delay_bound_steps": None,
        "contact_authorized": False,
        "rows": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("report_dir", type=Path)
    parser.add_argument("--output-json", type=Path)
    args = parser.parse_args()
    result = audit(args.manifest, args.report_dir)
    rendered = json.dumps(result, indent=2, allow_nan=False) + "\n"
    if args.output_json:
        args.output_json.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
