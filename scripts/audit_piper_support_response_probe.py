"""Audit one same-seed support pulse against the frozen NAV-PUSH baseline."""

import argparse
import hashlib
import json
import math
from pathlib import Path


BASELINE_SHA256 = {
    5703: "c7725ab232462bad44652eba6e9ca6d3ac2184250a36487012dee2433de0f9db",
    5712: "efd907bed8e99925a71369042ce37f6e948084796aeba8b9118abb08e035f14c",
}
MODES = ("front-up", "front-down", "rear-up", "rear-down")
PROBE_KEYS = {"support_probe_applied", "support_probe_leg_actions"}


def load(path):
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return json.loads(path.read_text(encoding="utf-8")), digest


def trigger_index(trace, names):
    rear = (names.index("RL_foot"), names.index("RR_foot"))
    consecutive = 0
    for index, item in enumerate(trace):
        active = (not item["motion_ready"] and item["base_pos"][2] < 0.27
                  and any(item["foot_normal_forces_n"][foot] < 2.0 for foot in rear))
        consecutive = consecutive + 1 if active else 0
        if consecutive == 5:
            return index
    raise ValueError("Frozen trigger did not occur")


def strip_probe(item):
    return {key: value for key, value in item.items() if key not in PROBE_KEYS}


def pitch(quaternion):
    w, x, y, z = quaternion
    return math.asin(max(-1.0, min(1.0, 2.0 * (w * y - z * x))))


def state(item, names):
    forces = item["foot_normal_forces_n"]
    return {
        "base_height_m": item["base_pos"][2],
        "base_pitch_rad": pitch(item["base_quat"]),
        "front_normal_force_n": sum(forces[names.index(f"{leg}_foot")] for leg in ("FL", "FR")),
        "rear_normal_force_n": sum(forces[names.index(f"{leg}_foot")] for leg in ("RL", "RR")),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--seed", type=int, choices=BASELINE_SHA256, required=True)
    parser.add_argument("--mode", choices=MODES, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error("Output file exists")
    baseline, baseline_sha = load(args.baseline)
    candidate, candidate_sha = load(args.candidate)
    if baseline_sha != BASELINE_SHA256[args.seed]:
        raise ValueError("Frozen baseline hash differs")
    if (baseline["seed"] != candidate["seed"] or candidate["seed"] != args.seed
            or candidate["schema_version"] != 19 or candidate["support_response_probe"] != args.mode
            or baseline["step_dt"] != candidate["step_dt"] or abs(candidate["step_dt"] - 0.02) > 1e-9
            or candidate["initial_state"] != baseline["initial_state"]
            or candidate["handoff"] != baseline["handoff"]
            or candidate["support_foot_body_names"] != baseline["support_foot_body_names"]):
        raise ValueError("Unmatched seed, layout or NAV handoff")
    original = baseline["support_trace"]
    tested = candidate["support_trace"]
    if len(original) != baseline["push_executed_steps"] or len(tested) != candidate["push_executed_steps"]:
        raise ValueError("Incomplete support trace")
    first_action = next((i for i, item in enumerate(tested) if item["support_probe_applied"]), None)
    if first_action is None:
        raise ValueError("Probe did not actuate")
    trigger = trigger_index(original, baseline["support_foot_body_names"])
    if (first_action != trigger + 1 or trigger_index(tested, candidate["support_foot_body_names"]) != trigger
            or abs(candidate["support_probe_trigger_s"] - original[trigger]["push_elapsed_s"]) > 1e-8):
        raise ValueError("Action does not follow the frozen trigger on the next step")
    if any(strip_probe(item) != original[index] for index, item in enumerate(tested[:first_action])):
        raise ValueError("Candidate changed before the first probe action")
    active = [i for i, item in enumerate(tested) if item["support_probe_applied"]]
    if (active != list(range(first_action, first_action + len(active))) or len(active) > 20
            or candidate["support_probe_steps"] != len(active)
            or not 0.0 <= candidate["support_probe_max_target_delta_rad"] <= 0.0400001):
        raise ValueError("Probe duration or target bound violated")
    selected = ("FL_foot", "FR_foot") if args.mode.startswith("front") else ("RL_foot", "RR_foot")
    names = candidate["joint_names"]
    selected_joint_ids = [names.index(f"{leg}_{joint}_joint") for leg in
                          (("FL", "FR") if args.mode.startswith("front") else ("RL", "RR"))
                          for joint in ("hip", "thigh", "calf")]
    response = []
    for offset in (0, 5, 10, 20, 30):
        index = first_action + offset
        if index >= min(len(original), len(tested)):
            continue
        reference = state(original[index], baseline["support_foot_body_names"])
        observed = state(tested[index], candidate["support_foot_body_names"])
        response.append({
            "elapsed_since_first_action_s": offset * candidate["step_dt"],
            "push_elapsed_s": tested[index]["push_elapsed_s"],
            "candidate_minus_baseline": {key: observed[key] - reference[key] for key in reference},
            "maximum_abs_selected_joint_difference_rad": max(
                abs(tested[index]["joint_pos"][joint] - original[index]["joint_pos"][joint])
                for joint in selected_joint_ids
            ),
        })
    report = {
        "schema_version": 1,
        "scope": "Known-seed local response only; no holdout success estimate or viability certificate",
        "seed": args.seed,
        "mode": args.mode,
        "baseline_sha256": baseline_sha,
        "candidate_sha256": candidate_sha,
        "audit_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "trigger_s": original[trigger]["push_elapsed_s"],
        "first_action_s": tested[first_action]["push_elapsed_s"],
        "pre_action_equal_steps": first_action,
        "pulse_steps": len(active),
        "maximum_target_delta_rad": candidate["support_probe_max_target_delta_rad"],
        "selected_feet": selected,
        "baseline_outcome": baseline["outcome"],
        "candidate_outcome": candidate["outcome"],
        "baseline_terminal_reasons": baseline["terminal"].get("reasons"),
        "candidate_terminal_reasons": candidate["terminal"].get("reasons"),
        "response": response,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
    print(json.dumps({key: report[key] for key in ("seed", "mode", "trigger_s", "first_action_s",
                                                  "pulse_steps", "candidate_outcome")}, allow_nan=False))


if __name__ == "__main__":
    main()
