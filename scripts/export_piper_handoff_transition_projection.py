"""Export causally aligned, incomplete-state PUSH transitions from a frozen cohort."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from audit_piper_handoff_observation_contract import audit, sha256


def post_step_projection(record: dict) -> dict:
    physical = record["recovery_decision_state"]
    return {
        "base_pos": record["base_pos"],
        "base_quat": record["base_quat"],
        "base_vel_w": physical["base_vel_w"],
        "base_omega_w": physical["base_omega_w"],
        "box_pos": physical["box_pos"],
        "box_quat": physical["box_quat"],
        "box_vel_w": physical["box_vel_w"],
        "box_omega_w": physical["box_omega_w"],
        "joint_pos": record["joint_pos"],
        "joint_vel": record["joint_vel"],
        "joint_pos_target": record["joint_pos_target"],
        "foot_normal_forces_n": record["foot_normal_forces_n"],
        "arm_controller": physical["arm_controller"],
        "settled_duration_s": physical["settled_duration_s"],
        "settled_contact_seen": physical["settled_contact_seen"],
    }


def export(manifest_path: Path, report_dir: Path, output_jsonl: Path, summary_json: Path) -> dict:
    if output_jsonl.resolve() == summary_json.resolve():
        raise ValueError("Transition data and summary need distinct paths")
    if output_jsonl.exists() or summary_json.exists():
        raise FileExistsError("Transition output already exists")
    cohort = audit(manifest_path, report_dir)
    if cohort["full_physx_markov_state_recorded"] or cohort["contact_authorized"]:
        raise ValueError("Expected a diagnostic-only, incomplete-state cohort")
    pairs = 0
    with output_jsonl.open("x", encoding="utf-8") as stream:
        for item in cohort["rows"]:
            if item["decision_samples"] == 0:
                continue
            report_path = report_dir / f"seed{item['seed']}-baseline.json"
            if sha256(report_path) != item["report_sha256"]:
                raise ValueError("Frozen report changed after cohort audit")
            report = json.loads(report_path.read_text(encoding="utf-8"))
            trace = report["support_trace"]
            if len(trace) != item["decision_samples"]:
                raise ValueError("Frozen report length changed after audit")
            for index in range(1, len(trace)):
                before, after = trace[index - 1], trace[index]
                action = after["recovery_decision_state"]
                if (before["recovery_decision_state"]["next_actor_input"]
                        != action["actor_input_before_action"]
                        or abs(after["push_elapsed_s"] - before["push_elapsed_s"]
                               - report["step_dt"]) > 1e-8):
                    raise ValueError("Actor input or physical step timing is misaligned")
                sample = {
                    "seed": item["seed"],
                    "source_report_sha256": item["report_sha256"],
                    "action_step_index_zero_based": index,
                    "pre_time_s": before["push_elapsed_s"],
                    "post_time_s": after["push_elapsed_s"],
                    "pre_action_physical_projection": post_step_projection(before),
                    "actor_input_before_action": action["actor_input_before_action"],
                    "actor_action_before_step": action["actor_action_before_step"],
                    "post_action_physical_projection": post_step_projection(after),
                    "next_actor_input": action["next_actor_input"],
                }
                stream.write(json.dumps(sample, separators=(",", ":"), allow_nan=False) + "\n")
                pairs += 1
    expected = sum(max(0, item["decision_samples"] - 1) for item in cohort["rows"])
    if pairs != expected:
        raise ValueError("Transition count does not match frozen cohort")
    summary = {
        "schema_version": 1,
        "scope": "causally_aligned_incomplete_state_projection_only",
        "cohort_manifest_sha256": cohort["cohort_manifest_sha256"],
        "source_sha256": cohort["source_sha256"],
        "total_nav_starts": cohort["total_nav_starts"],
        "push_entrants": cohort["push_entrants"],
        "total_decision_steps": cohort["total_decision_samples"],
        "aligned_transition_pairs": pairs,
        "output_jsonl_sha256": sha256(output_jsonl),
        "full_physx_markov_state_recorded": False,
        "counterfactual_action_branches_observed": False,
        "joint_coverage_bound": None,
        "contact_authorized": False,
    }
    summary_json.write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("report_dir", type=Path)
    parser.add_argument("output_jsonl", type=Path)
    parser.add_argument("summary_json", type=Path)
    args = parser.parse_args()
    print(json.dumps(export(args.manifest, args.report_dir,
                            args.output_jsonl, args.summary_json), indent=2))
