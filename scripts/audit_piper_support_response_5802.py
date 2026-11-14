"""Audit signed known-state foot pulses against the frozen seed5802 baseline."""

import argparse
import hashlib
import json
import math
from pathlib import Path


BASELINE_SHA256 = "4746bfcbbba37cfe89154447a51357c09678b4bbd58addaecf6e193739881392"
MODES = ("front-up", "front-down")
BASELINE_ONLY = {"recovery_decision_state"}
PROBE_ONLY = {"support_probe_applied", "support_probe_leg_actions", "support_probe_dynamics"}


def load(path):
    raw = path.read_bytes()
    return json.loads(raw), hashlib.sha256(raw).hexdigest()


def first_warning(trace, names):
    rear = (names.index("RL_foot"), names.index("RR_foot"))
    consecutive = 0
    for index, item in enumerate(trace):
        active = (not item["motion_ready"] and item["base_pos"][2] < 0.27
                  and any(item["foot_normal_forces_n"][foot] < 2.0 for foot in rear))
        consecutive = consecutive + 1 if active else 0
        if consecutive == 5:
            return index
    raise ValueError("Frozen warning did not occur")


def pitch(quaternion):
    w, x, y, z = quaternion
    return math.asin(max(-1.0, min(1.0, 2.0 * (w * y - z * x))))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--mode", choices=MODES, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error("Output file exists")
    baseline, baseline_sha = load(args.baseline)
    candidate, candidate_sha = load(args.candidate)
    if baseline_sha != BASELINE_SHA256:
        raise ValueError("Frozen baseline hash differs")
    if (baseline["seed"] != candidate["seed"] or candidate["seed"] != 5802
            or baseline["schema_version"] != 18 or candidate["schema_version"] != 20
            or candidate["support_response_probe"] != args.mode
            or candidate["record_recovery_decision_state"]
            or baseline["nav_actor_sha256"] != candidate["nav_actor_sha256"]
            or baseline["push_checkpoint_sha256"] != candidate["push_checkpoint_sha256"]
            or baseline["control_sha256"] != candidate["control_sha256"]
            or baseline["initial_state"] != candidate["initial_state"]
            or baseline["handoff"] != candidate["handoff"]
            or baseline["support_foot_body_names"] != candidate["support_foot_body_names"]
            or baseline["push_budget_s"] != candidate["push_budget_s"]
            or baseline["step_dt"] != candidate["step_dt"]
            or baseline["nav_start_x_m"] != candidate["nav_start_x_m"]
            or baseline["nav_goal_xyyaw"] != candidate["nav_goal_xyyaw"]
            or set(baseline["terminal"]["reasons"]) != set(candidate["terminal"]["reasons"])):
        raise ValueError("Candidate changed the frozen source, handoff or termination contract")
    original = baseline["support_trace"]
    tested = candidate["support_trace"]
    if (len(original) != baseline["push_executed_steps"]
            or len(tested) != candidate["push_executed_steps"]):
        raise ValueError("Incomplete PUSH trace")
    trigger = first_warning(original, baseline["support_foot_body_names"])
    first_action = next((index for index, item in enumerate(tested)
                         if item["support_probe_applied"]), None)
    if (first_action is None or first_action != trigger + 1
            or first_warning(tested, candidate["support_foot_body_names"]) != trigger
            or abs(candidate["support_probe_trigger_s"] - original[trigger]["push_elapsed_s"]) > 1e-8):
        raise ValueError("Pulse did not begin on the first step after the frozen warning")
    for index in range(first_action):
        reference = {key: value for key, value in original[index].items()
                     if key not in BASELINE_ONLY}
        observed = {key: value for key, value in tested[index].items()
                    if key not in PROBE_ONLY}
        if reference != observed:
            raise ValueError(f"Pre-action physical trace changed at PUSH step {index}")
    active = [index for index, item in enumerate(tested) if item["support_probe_applied"]]
    if (active != list(range(first_action, first_action + len(active)))
            or not 1 <= len(active) <= 20 or candidate["support_probe_steps"] != len(active)
            or not 0.0 < candidate["support_probe_max_target_delta_rad"] <= 0.0400001):
        raise ValueError("Pulse length or joint-target bound invalid")
    for index, item in enumerate(tested):
        dynamics = item["support_probe_dynamics"]
        if not all(len(dynamics[key]) == 3 and all(math.isfinite(value) for value in dynamics[key])
                   for key in ("base_vel_w", "base_omega_w")):
            raise ValueError(f"Invalid direct velocity at PUSH step {index}")
        if index < first_action:
            reference = original[index]["recovery_decision_state"]
            if any(dynamics[key] != reference[key] for key in dynamics):
                raise ValueError(f"Pre-action direct velocity changed at PUSH step {index}")
    response = []
    for offset in (0, 5, 10, 15, 20):
        index = first_action + offset
        if index >= min(len(original), len(tested)):
            continue
        reference = original[index]
        observed = tested[index]
        reference_dynamics = reference["recovery_decision_state"]
        observed_dynamics = observed["support_probe_dynamics"]
        response.append({
            "since_first_action_s": offset * candidate["step_dt"],
            "push_elapsed_s": observed["push_elapsed_s"],
            "base_height_delta_m": observed["base_pos"][2] - reference["base_pos"][2],
            "base_pitch_delta_rad": pitch(observed["base_quat"]) - pitch(reference["base_quat"]),
            "base_vertical_velocity_delta_m_s": (observed_dynamics["base_vel_w"][2]
                                                 - reference_dynamics["base_vel_w"][2]),
            "base_y_angular_velocity_delta_rad_s": (observed_dynamics["base_omega_w"][1]
                                                    - reference_dynamics["base_omega_w"][1]),
            "rear_normal_force_delta_n": sum(observed["foot_normal_forces_n"][2:])
                                         - sum(reference["foot_normal_forces_n"][2:]),
        })
    result = {
        "schema_version": 1,
        "scope": "Inspected seed5802 mechanism probe only; no independent validation or contact release",
        "mode": args.mode,
        "baseline_sha256": baseline_sha,
        "candidate_sha256": candidate_sha,
        "audit_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "pre_action_equal_steps": first_action,
        "warning_push_s": original[trigger]["push_elapsed_s"],
        "first_action_push_s": tested[first_action]["push_elapsed_s"],
        "pulse_steps": len(active),
        "maximum_target_delta_rad": candidate["support_probe_max_target_delta_rad"],
        "baseline_outcome": baseline["outcome"],
        "baseline_terminal_reasons": baseline["terminal"]["reasons"],
        "baseline_terminal_push_s": baseline["push_elapsed_s"],
        "candidate_outcome": candidate["outcome"],
        "candidate_terminal_reasons": candidate["terminal"]["reasons"],
        "candidate_terminal_push_s": candidate["push_elapsed_s"],
        "response": response,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
    print(json.dumps({key: result[key] for key in ("mode", "warning_push_s", "pulse_steps",
                                                    "candidate_outcome", "candidate_terminal_push_s")}))


if __name__ == "__main__":
    main()
