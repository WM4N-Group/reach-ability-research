"""Audit one stopped rear-support pilot against its known-state baselines."""

import argparse
import hashlib
import json
import math
from pathlib import Path


EXPECTED_SHA256 = {
    "failure": "ef72841ca7700e1ca1d369ad50b4e4149c8e0441bb651497358c5b9efad8ab0c",
    "candidate": "87d8e8e874230bb862f241c666ffa57adcbad289b6067095197b7641f306bac6",
    "success": "b541f293014ddebe8425a68a6662ae9e837702a9491bfc2f8009b15218353944",
}
SAMPLE_TIMES_S = (5.0, 5.26, 5.6)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_report(path, label, seed):
    digest = sha256(path)
    if digest != EXPECTED_SHA256[label]:
        raise ValueError(f"Unexpected {label} report hash: {digest}")
    with path.open(encoding="utf-8") as stream:
        report = json.load(stream)
    if (report["seed"] != seed or abs(report["step_dt"] - 0.02) > 1e-9
            or len(report["support_trace"]) != report["push_executed_steps"]):
        raise ValueError(f"Unexpected {label} report layout")
    return report, digest


def pitch(quaternion):
    w, x, y, z = quaternion
    return math.asin(max(-1.0, min(1.0, 2.0 * (w * y - z * x))))


def first_time(trace, predicate):
    return next((item["push_elapsed_s"] for item in trace
                 if item["push_elapsed_s"] >= 4.0 and predicate(item)), None)


def snapshot(report, time_s):
    item = report["support_trace"][round(time_s / report["step_dt"]) - 1]
    names = report["support_foot_body_names"]
    front = sum(item["foot_normal_forces_n"][names.index(f"{leg}_foot")] for leg in ("FL", "FR"))
    rear = sum(item["foot_normal_forces_n"][names.index(f"{leg}_foot")] for leg in ("RL", "RR"))
    return {
        "push_elapsed_s": time_s,
        "base_height_m": item["base_pos"][2],
        "base_pitch_rad": pitch(item["base_quat"]),
        "front_normal_force_n": front,
        "rear_normal_force_n": rear,
        "rear_fraction_of_four_foot_normal_force": rear / (front + rear) if front + rear > 0 else None,
    }


def timeline(report):
    trace = report["support_trace"]
    names = report["support_foot_body_names"]
    rear = [names.index(f"{leg}_foot") for leg in ("RL", "RR")]
    return {
        "first_base_pitch_gt_0p15_s": first_time(trace, lambda item: pitch(item["base_quat"]) > 0.15),
        "first_base_height_lt_0p27_s": first_time(trace, lambda item: item["base_pos"][2] < 0.27),
        "first_rear_total_force_lt_10n_s": first_time(
            trace, lambda item: sum(item["foot_normal_forces_n"][index] for index in rear) < 10.0
        ),
        "first_both_rear_forces_lt_2n_s": first_time(
            trace, lambda item: all(item["foot_normal_forces_n"][index] < 2.0 for index in rear)
        ),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--failure", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--success", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error("Output file already exists")
    failure, failure_hash = load_report(args.failure, "failure", 5201)
    candidate, candidate_hash = load_report(args.candidate, "candidate", 5201)
    success, success_hash = load_report(args.success, "success", 5124)
    if (failure["handoff"] != candidate["handoff"]
            or failure["initial_state"] != candidate["initial_state"]
            or failure["support_foot_body_names"] != candidate["support_foot_body_names"]):
        raise ValueError("Failure and candidate entry states differ")
    candidate_trace = candidate["support_trace"]
    failure_trace = failure["support_trace"]
    first_action_index = next((index for index, item in enumerate(candidate_trace)
                               if item["rear_support_feedback_applied"]), None)
    if first_action_index is None or len(candidate_trace) != len(failure_trace):
        raise ValueError("Missing intervention or unmatched PUSH sample count")
    feedback_keys = {"rear_support_feedback_applied", "rear_support_feedback_leg_actions"}
    if any({key: value for key, value in item.items() if key not in feedback_keys} != baseline
           for item, baseline in zip(candidate_trace[:first_action_index], failure_trace[:first_action_index])):
        raise ValueError("Candidate differs before first feedback action")
    names = candidate["support_foot_body_names"]
    rear_indices = [names.index(f"{leg}_foot") for leg in ("RL", "RR")]
    consecutive = 0
    first_trigger = None
    for item in candidate_trace:
        condition = (not item["motion_ready"] and item["base_pos"][2] < 0.27
                     and any(item["foot_normal_forces_n"][index] < 2 for index in rear_indices))
        consecutive = consecutive + 1 if condition else 0
        if consecutive == 5:
            first_trigger = item["push_elapsed_s"]
            break
    if first_trigger is None or abs(first_trigger + 0.02 - candidate_trace[first_action_index]["push_elapsed_s"]) > 1e-8:
        raise ValueError("First action does not follow the first qualified trigger")
    robot_names = candidate["joint_names"]
    rear_joint_ids = [robot_names.index(f"{leg}_{joint}_joint")
                      for leg in ("RL", "RR") for joint in ("hip", "thigh", "calf")]
    after = zip(candidate_trace[first_action_index:], failure_trace[first_action_index:])
    actual_joint_delta = max(abs(item["joint_pos"][joint] - baseline["joint_pos"][joint])
                             for item, baseline in after for joint in rear_joint_ids)
    response = {}
    for foot in ("RL_foot", "RR_foot"):
        foot_index = names.index(foot)
        candidate_window = candidate_trace[first_action_index:]
        baseline_window = failure_trace[first_action_index:]
        response[foot] = {
            "maximum_abs_foot_body_height_difference_m": max(
                abs(item["foot_body_pos"][foot_index][2] - baseline["foot_body_pos"][foot_index][2])
                for item, baseline in zip(candidate_window, baseline_window)
            ),
            "candidate_loaded_steps_gt_2n": sum(
                item["foot_normal_forces_n"][foot_index] > 2 for item in candidate_window
            ),
            "baseline_loaded_steps_gt_2n": sum(
                item["foot_normal_forces_n"][foot_index] > 2 for item in baseline_window
            ),
        }
    result = {
        "schema_version": 1,
        "scope": "Known-state descriptive response; thresholds and phase comparison are retrospective, not a controller gate or reachability certificate",
        "analysis_sha256": sha256(Path(__file__)),
        "input_sha256": {"failure": failure_hash, "candidate": candidate_hash, "success": success_hash},
        "pre_action_push_samples_equal": first_action_index,
        "first_trigger_s_reconstructed": first_trigger,
        "first_feedback_action_s": candidate_trace[first_action_index]["push_elapsed_s"],
        "stored_trigger_s_overwritten": candidate["rear_support_feedback_trigger_s"],
        "feedback_steps": candidate["rear_support_feedback_steps"],
        "maximum_actual_rear_joint_difference_rad": actual_joint_delta,
        "rear_foot_response": response,
        "timelines": {"failure": timeline(failure), "candidate": timeline(candidate), "success": timeline(success)},
        "phase_snapshots": {label: [snapshot(report, time_s) for time_s in SAMPLE_TIMES_S]
                            for label, report in (("failure", failure), ("candidate", candidate), ("success", success))},
        "terminal_reasons": {label: report["terminal"].get("reasons")
                             for label, report in (("failure", failure), ("candidate", candidate), ("success", success))},
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
    print(json.dumps({"first_action_s": result["first_feedback_action_s"],
                      "timelines": result["timelines"], "rear_foot_response": response}, indent=2))


if __name__ == "__main__":
    main()
