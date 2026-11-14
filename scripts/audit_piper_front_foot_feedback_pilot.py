"""Audit a bounded state feedback pilot against a frozen same-seed baseline."""

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path


BASELINE_SHA256 = {
    5201: "9fcf7fef65ac62c650c80dc41bd09d0115c227b77f605e0e2f52ca6e6ecd9e37",
    5124: "8a44073e44709c03a388af1cb4f1d4ac040c3f1d06e16d629c0be5a50f4c6c91",
    5503: "bf9669306af36b0ac53b379f8acce1d9110298bf66cf0d3990e8f9cfac0139f0",
    5506: "f867c7d4958816c31ed014f972ee9676c125c2e8031dfb237751e9edf5acc490",
}
FEET = ("FL_foot", "FR_foot")


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(seed, baseline_path, candidate_path):
    if sha256(baseline_path) != BASELINE_SHA256[seed]:
        raise ValueError(f"Seed{seed} baseline hash differs")
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    if (baseline["seed"] != seed or candidate["seed"] != seed
            or candidate["schema_version"] != 17 or not candidate["front_foot_feedback"]
            or candidate["handoff"] != baseline["handoff"]
            or candidate["control_sha256"] != baseline["control_sha256"]
            or candidate["nav_actor_sha256"] != baseline["nav_actor_sha256"]
            or candidate["push_checkpoint_sha256"] != baseline["push_checkpoint_sha256"]
            or len(candidate["support_trace"]) != candidate["push_executed_steps"]):
        raise ValueError(f"Seed{seed} source or handoff mismatch")
    active = []
    unqualified = 0
    peak_joint_offset = 0.0
    max_joint_step = 0.0
    max_foot_step = 0.0
    previous_actions = {foot: [0.0] * 3 for foot in FEET}
    previous_offset = 0.0
    loaded = {name: 0 for name in candidate["support_foot_body_names"]}
    prefix = 0
    for index, sample in enumerate(candidate["support_trace"]):
        time = sample["push_elapsed_s"]
        if time < 4.40 - 1e-8:
            original = copy.deepcopy(sample)
            original.pop("front_foot_feedback")
            original.pop("front_foot_feedback_leg_actions")
            if original != baseline["support_trace"][index]:
                raise ValueError(f"Seed{seed} pre-feedback sample {index} differs")
            prefix += 1
        state = sample["front_foot_feedback"]
        if state is not None:
            active.append(time)
            if not 4.40 - 1e-8 <= time <= 6.20 + 1e-8 or sample["motion_ready"]:
                raise ValueError(f"Seed{seed} feedback outside intended phase")
            values = [state["base_pitch_rad_before_action"],
                      state["world_y_angular_velocity_rad_s_before_action"],
                      state["total_foot_normal_force_n_before_action"],
                      state["risk_demand"], state["applied_world_foot_z_target_offset_m"]]
            if not all(math.isfinite(value) for value in values):
                raise ValueError(f"Seed{seed} nonfinite feedback state")
            total_force = state["total_foot_normal_force_n_before_action"]
            if (total_force < 0 or state["support_input_qualified"] != (total_force >= 20.0)
                    or not 0 <= state["risk_demand"] <= 1
                    or not -0.0050001 <= values[-1] <= 1e-8):
                raise ValueError(f"Seed{seed} feedback command outside range")
            if state["support_input_qualified"]:
                if (state["rear_normal_force_fraction_before_action"] is None
                        or not 0 <= state["rear_normal_force_fraction_before_action"] <= 1):
                    raise ValueError(f"Seed{seed} invalid rear load share")
            else:
                unqualified += 1
                if state["risk_demand"] != 0 or state["rear_normal_force_fraction_before_action"] is not None:
                    raise ValueError(f"Seed{seed} unqualified support was used")
            clamp = lambda value: min(max(value, 0.0), 1.0)
            expected_risk = max(
                clamp((state["base_pitch_rad_before_action"] - 0.06) / 0.10),
                clamp((state["world_y_angular_velocity_rad_s_before_action"] - 0.02) / 0.20),
                clamp((0.30 - state["rear_normal_force_fraction_before_action"]) / 0.20),
            ) if state["support_input_qualified"] else 0.0
            envelope = clamp((6.20 - time) / 0.20)
            desired = -0.005 * expected_risk * envelope
            expected_offset = min(max(desired, previous_offset - 0.0005), previous_offset + 0.0005)
            if (abs(state["risk_demand"] - expected_risk) > 1e-6
                    or abs(values[-1] - expected_offset) > 1e-6):
                raise ValueError(f"Seed{seed} feedback law differs from frozen protocol")
            max_foot_step = max(max_foot_step, abs(values[-1] - previous_offset))
            previous_offset = values[-1]
        commands = sample["front_foot_feedback_leg_actions"]
        if set(commands) != set(FEET):
            raise ValueError(f"Seed{seed} action layout differs")
        for foot in FEET:
            if len(commands[foot]) != 3 or not all(math.isfinite(value) for value in commands[foot]):
                raise ValueError(f"Seed{seed} nonfinite or malformed leg command")
            for value, previous in zip(commands[foot], previous_actions[foot]):
                if state is not None:
                    peak_joint_offset = max(peak_joint_offset, abs(value) * 0.25)
                if 4.40 - 1e-8 <= time <= 6.22 + 1e-8:
                    max_joint_step = max(max_joint_step, abs(value - previous) * 0.25)
            previous_actions[foot] = commands[foot]
        for foot_index, foot in enumerate(candidate["support_foot_body_names"]):
            contact = sample["ground_contacts"][foot]
            normal = contact["ground_normal_force"][2]
            if not math.isfinite(normal) or abs(normal - sample["foot_normal_forces_n"][foot_index]) > 1e-3:
                raise ValueError(f"Seed{seed} invalid filtered ground force: {foot}")
            if normal > 2:
                point = contact["ground_contact_pos"]
                if point is None or not all(math.isfinite(value) for value in point):
                    raise ValueError(f"Seed{seed} loaded foot lacks ground point: {foot}")
                loaded[foot] += 1
    if (prefix != 219 or not active or abs(active[0] - 4.40) > 1e-8
            or not all(loaded.values()) or unqualified
            or peak_joint_offset > 0.040001 or max_joint_step > 0.020001
            or max_foot_step > 0.000501 or candidate["front_foot_feedback_steps"] != len(active)
            or abs(candidate["front_foot_feedback_max_target_delta_rad"] - peak_joint_offset) > 1e-6):
        raise ValueError(f"Seed{seed} feedback schedule, sensors or limits invalid")
    return {
        "schema_version": 1,
        "seed": seed,
        "analysis_sha256": sha256(Path(__file__)),
        "baseline_sha256": sha256(baseline_path),
        "candidate_sha256": sha256(candidate_path),
        "handoff_and_219_pre_feedback_samples_equal": True,
        "active_steps": len(active),
        "first_active_push_s": active[0],
        "last_active_push_s": active[-1],
        "unqualified_support_input_steps": unqualified,
        "max_foot_offset_step_m": max_foot_step,
        "max_joint_target_offset_rad": peak_joint_offset,
        "max_joint_target_change_per_step_rad": max_joint_step,
        "loaded_ground_samples_by_foot": loaded,
        "baseline_outcome": baseline["outcome"],
        "baseline_push_elapsed_s": baseline["push_elapsed_s"],
        "candidate_outcome": candidate["outcome"],
        "candidate_push_elapsed_s": candidate["push_elapsed_s"],
        "candidate_terminal_reasons": candidate["terminal"].get("reasons", {}),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, choices=tuple(BASELINE_SHA256), required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error("Output file already exists")
    result = check(args.seed, args.baseline, args.candidate)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
    print(f"seed={args.seed} baseline={result['baseline_outcome']} "
          f"candidate={result['candidate_outcome']} active_steps={result['active_steps']}")


if __name__ == "__main__":
    main()
