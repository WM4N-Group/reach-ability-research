"""Audit matched full-control-step load traces against their frozen PUSH parent."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def pinned_json(entry: dict) -> dict:
    path = ROOT / entry["path"]
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != entry["sha256"]:
        raise ValueError(f"Source hash differs: {entry['path']}")
    return json.loads(raw)


def check_pinned_file(entry: dict) -> None:
    if hashlib.sha256((ROOT / entry["path"]).read_bytes()).hexdigest() != entry["sha256"]:
        raise ValueError(f"Source hash differs: {entry['path']}")


def first_step(samples: list[dict], predicate) -> int | None:
    return next((sample["step"] for sample in samples if predicate(sample)), None)


def audit_case(parent: dict, case: dict) -> dict:
    plan = pinned_json(case["plan"])
    status = pinned_json(case["exit_status"])
    report = pinned_json(case["report"])
    check_pinned_file(case["run_log"])
    env_id = case["env_id"]
    trace_key = f"trace_env{env_id}"
    if (status.get("returncode") != 0 or status.get("report_valid") is not True
            or status.get("report_sha256") != case["report"]["sha256"]):
        raise ValueError(f"Invalid launcher result: {case['variant']}")
    if (plan.get("parent_report_sha256") != case["parent_sha256"]
            or plan.get("checkpoint_sha256") != report.get("checkpoint_sha256")
            or plan.get("evaluator_sha256") != report.get("evaluation_sha256")
            or plan.get("ik_sha256") != report["control_sha256"]["box_push_ik.py"]
            or plan.get("box_push_sha256") != report["control_sha256"]["box_push.py"]):
        raise ValueError(f"Plan/source identity differs: {case['variant']}")
    if (report["actual_physics"] != parent["actual_physics"]
            or report["control_sha256"] != parent["control_sha256"]
            or report["checkpoint_sha256"] != parent["checkpoint_sha256"]
            or report["terminal_states"] != parent["terminal_states"]
            or report["termination_reasons"] != parent["termination_reasons"]
            or report["completed_episodes"] != 8 or report["incomplete_episodes"] != 0
            or report["inspect_env_index"] != env_id):
        raise ValueError(f"Full physical outcome differs from parent: {case['variant']}")
    command = plan["command"]
    if command.count("--inspect-env-index") != 1 or int(command[command.index("--inspect-env-index") + 1]) != env_id:
        raise ValueError(f"Inspected environment differs from plan: {case['variant']}")

    samples = report[trace_key]
    if not samples or any(sample["step"] != index or sample["env_id"] != env_id
                          for index, sample in enumerate(samples)):
        raise ValueError(f"Trace is not one complete ordered prefix: {case['variant']}")
    terminal = next(item for item in report["terminal_states"] if item["env_id"] == env_id)
    dt = report["failure_history_step_dt"]
    if not math.isclose(len(samples) * dt, terminal["elapsed_seconds"], abs_tol=1e-4):
        raise ValueError(f"Trace length differs from terminal clock: {case['variant']}")

    for sample in samples:
        if (len(sample["face_local"]) != 3 or len(sample["velocity_command"]) != 3
                or len(sample["arm_torque_limit_ratio"]) != 6
                or not all(math.isfinite(value) for key in ("face_local", "velocity_command",
                                                      "arm_torque_limit_ratio", "box_position")
                            for value in sample[key])):
            raise ValueError(f"Missing or nonfinite trace fields: {case['variant']}")
    loaded = [sample for sample in samples if sample["hand_contact"]]
    gap_stop = [sample for sample in loaded if sample["face_local"][0] <= 0.43]
    if any(sample["velocity_command"][0] > 0.001 for sample in gap_stop):
        raise ValueError(f"Positive forward command below stop line: {case['variant']}")
    j2_limited = [sample for sample in loaded if sample["arm_torque_limit_ratio"][1] >= 0.999]
    first_gap = gap_stop[0] if gap_stop else None
    return {
        "variant": case["variant"],
        "env_id": env_id,
        "report_sha256": case["report"]["sha256"],
        "terminal_reason": next(name for name, active in zip(report["termination_flag_names"],
                                                             terminal["termination_flags"]) if active),
        "sample_count": len(samples),
        "control_step_dt_s": dt,
        "first_face_ready_step": first_step(samples, lambda sample: sample["approach_face_ready"]),
        "first_hand_contact_step": first_step(samples, lambda sample: sample["hand_contact"]),
        "first_loaded_joint2_limit_step": first_step(loaded, lambda sample: sample["arm_torque_limit_ratio"][1] >= 0.999),
        "loaded_contact_steps": len(loaded),
        "loaded_joint2_limit_steps": len(j2_limited),
        "loaded_gap_at_or_below_043_steps": len(gap_stop),
        "first_loaded_gap_at_or_below_043_step": None if first_gap is None else first_gap["step"],
        "box_goal_remaining_x_at_first_gap_m": None if first_gap is None else terminal["box_goal"][0] - first_gap["box_position"][0],
        "box_displacement_x_m": terminal["box_displacement"][0],
        "box_goal_error_m": terminal["box_goal_error"],
        "last_128_box_advance_x_m": samples[-1]["box_position"][0] - samples[-128]["box_position"][0],
        "last_128_zero_forward_steps": sum(sample["velocity_command"][0] <= 0.001 for sample in samples[-128:]),
        "last_128_joint2_limit_steps": sum(sample["arm_torque_limit_ratio"][1] >= 0.999 for sample in samples[-128:]),
    }


def audit(manifest: dict) -> dict:
    parent = pinned_json(manifest["parent_report"])
    cases = []
    for case in manifest["cases"]:
        if case["parent_sha256"] != manifest["parent_report"]["sha256"]:
            raise ValueError("Case does not pin the declared parent")
        cases.append(audit_case(parent, case))
    if {case["env_id"] for case in cases} != {1, 2}:
        raise ValueError("Expected the fixed successful and timeout pair")
    return {
        "scope": "Used-seed matched control-step traces; no physical-substep or counterfactual claim",
        "parent_report_sha256": manifest["parent_report"]["sha256"],
        "cases": cases,
        "contact_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(json.loads(args.manifest.read_text()))
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"cases": [case["variant"] for case in result["cases"]],
                      "contact_authorized": result["contact_authorized"]}))


if __name__ == "__main__":
    main()
