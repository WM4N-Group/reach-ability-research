"""Audit one known-state warning-triggered arm hold against its frozen baseline."""

import argparse
import hashlib
import json
import math
from pathlib import Path


BASELINE_SHA256 = "4746bfcbbba37cfe89154447a51357c09678b4bbd58addaecf6e193739881392"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def warning_index(trace, names):
    rear = (names.index("RL_foot"), names.index("RR_foot"))
    consecutive = 0
    for index, sample in enumerate(trace):
        active = (not sample["motion_ready"] and sample["base_pos"][2] < 0.27
                  and any(sample["foot_normal_forces_n"][foot] < 2.0 for foot in rear))
        consecutive = consecutive + 1 if active else 0
        if consecutive == 5:
            return index
    raise ValueError("The frozen support warning did not trigger")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error("Output file exists")

    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    if (protocol["ordered_pilots"][0]["seed"] != 5802
            or protocol["ordered_pilots"][0]["baseline_report_sha256"] != BASELINE_SHA256
            or sha256(args.baseline) != BASELINE_SHA256):
        raise ValueError("Frozen baseline or protocol differs")
    baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
    candidate = json.loads(args.candidate.read_text(encoding="utf-8"))
    if (baseline["seed"] != candidate["seed"] or candidate["seed"] != 5802
            or candidate["schema_version"] != 30
            or not candidate["hold_arm_on_support_warning"]
            or candidate["nav_actor_sha256"] != baseline["nav_actor_sha256"]
            or candidate["push_checkpoint_sha256"] != baseline["push_checkpoint_sha256"]
            or candidate["control_sha256"] != baseline["control_sha256"]
            or candidate["initial_state"] != baseline["initial_state"]
            or candidate["handoff"] != baseline["handoff"]
            or candidate["step_dt"] != baseline["step_dt"]
            or candidate["push_budget_s"] != baseline["push_budget_s"]
            or candidate["support_foot_body_names"] != baseline["support_foot_body_names"]):
        raise ValueError("Policy, control, state or task contract differs")
    if (candidate["nav_actor_sha256"] != protocol["control"]["nav_actor_sha256"]
            or candidate["push_checkpoint_sha256"] != protocol["control"]["push_checkpoint_sha256"]
            or candidate["control_sha256"] != protocol["control_sha256"]):
        raise ValueError("Candidate differs from the frozen protocol")

    original = baseline["support_trace"]
    tested = candidate["support_trace"]
    if (len(original) != baseline["push_executed_steps"]
            or len(tested) != candidate["push_executed_steps"]
            or candidate["outcome"] not in ("push_terminated", "push_budget_exhausted")):
        raise ValueError("Incomplete PUSH report")
    trigger = warning_index(original, baseline["support_foot_body_names"])
    if (trigger >= len(tested) or warning_index(tested, candidate["support_foot_body_names"]) != trigger
            or not math.isclose(candidate["warning_arm_hold_trigger_s"],
                                original[trigger]["push_elapsed_s"], abs_tol=1e-8)):
        raise ValueError("Trigger is not paired with the baseline")
    for index in range(trigger + 1):
        baseline_sample = dict(original[index])
        candidate_sample = dict(tested[index])
        if ("recovery_decision_state" not in baseline_sample
                or baseline_sample.pop("recovery_decision_state") is None
                or candidate_sample.pop("warning_arm_hold_steps") != 0
                or candidate_sample != baseline_sample):
            raise ValueError(f"Candidate differs before the first held action at step {index + 1}")

    first_action = trigger + 1
    reference = candidate["warning_arm_hold_reference"]
    if (first_action >= len(tested) or len(reference) != 6
            or reference != original[trigger]["arm_reference"]
            or not all(math.isfinite(value) for value in reference)):
        raise ValueError("Held reference or first action is missing")
    for index, sample in enumerate(tested[first_action:], start=first_action):
        if (sample["warning_arm_hold_steps"] != index - trigger
                or sample["arm_reference"] != reference
                or not all(math.isfinite(value) for value in sample["joint_pos_target"])):
            raise ValueError(f"Arm hold contract violated at step {index + 1}")
    if candidate["warning_arm_hold_steps"] != len(tested) - first_action:
        raise ValueError("Held action count differs from the trace")
    if candidate["outcome"] == "push_terminated" and (
            not candidate["terminal"].get("reasons")
            or candidate["terminal"].get("warning_arm_hold_steps") != candidate["warning_arm_hold_steps"]):
        raise ValueError("Native termination snapshot is missing")

    result = {
        "schema_version": 1,
        "scope": "One inspected state; arm hold cannot complete the original PUSH task",
        "baseline_sha256": sha256(args.baseline),
        "candidate_sha256": sha256(args.candidate),
        "protocol_sha256": sha256(args.protocol),
        "audit_sha256": sha256(Path(__file__)),
        "trigger_s": original[trigger]["push_elapsed_s"],
        "first_held_action_s": tested[first_action]["push_elapsed_s"],
        "pre_action_equal_steps": first_action,
        "held_action_steps": candidate["warning_arm_hold_steps"],
        "baseline_outcome": baseline["outcome"],
        "baseline_terminal_reasons": baseline["terminal"].get("reasons"),
        "candidate_outcome": candidate["outcome"],
        "candidate_terminal_reasons": candidate["terminal"].get("reasons"),
        "candidate_push_elapsed_s": candidate["push_elapsed_s"],
        "candidate_safe_approach_complete_s": candidate.get("safe_approach_complete_s"),
        "candidate_motion_ready_s": candidate.get("motion_ready_s"),
        "interpretation": "Compare native safety termination and support response only. Budget exhaustion or absence of base contact is not PUSH success. Do not run the second pilot without reviewing this report.",
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({key: result[key] for key in
                      ("trigger_s", "first_held_action_s", "held_action_steps",
                       "candidate_outcome", "candidate_terminal_reasons")}, allow_nan=False))


if __name__ == "__main__":
    main()
