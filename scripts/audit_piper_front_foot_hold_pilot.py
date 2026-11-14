"""Audit a bounded front-foot hold against its frozen known-state baseline."""

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


def check(baseline_path, hold_path, seed):
    if sha256(baseline_path) != BASELINE_SHA256[seed]:
        raise ValueError(f"Seed{seed} baseline hash differs")
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    hold = json.loads(hold_path.read_text(encoding="utf-8"))
    if (baseline["seed"] != seed or hold["seed"] != seed or hold["schema_version"] != 16
            or hold["front_foot_hold_offset_m"] != -0.005
            or hold["handoff"] != baseline["handoff"]
            or hold["control_sha256"] != baseline["control_sha256"]
            or hold["nav_actor_sha256"] != baseline["nav_actor_sha256"]
            or hold["push_checkpoint_sha256"] != baseline["push_checkpoint_sha256"]
            or len(hold["support_trace"]) != hold["push_executed_steps"]):
        raise ValueError(f"Seed{seed} source or handoff mismatch")
    active = []
    peak = 0.0
    max_step = 0.0
    previous = {foot: [0.0] * 3 for foot in FEET}
    prefix = 0
    loaded = {name: 0 for name in hold["support_foot_body_names"]}
    for index, sample in enumerate(hold["support_trace"]):
        time = sample["push_elapsed_s"]
        if time < 4.40 - 1e-8:
            original = copy.deepcopy(sample)
            original.pop("front_foot_hold_applied")
            original.pop("front_foot_hold_leg_actions")
            if original != baseline["support_trace"][index]:
                raise ValueError(f"Seed{seed} pre-hold sample {index} differs")
            prefix += 1
        commands = sample["front_foot_hold_leg_actions"]
        if set(commands) != set(FEET):
            raise ValueError(f"Seed{seed} action layout differs")
        if sample["front_foot_hold_applied"]:
            active.append(time)
            if not 4.40 - 1e-8 <= time <= 6.20 + 1e-8 or sample["motion_ready"]:
                raise ValueError(f"Seed{seed} hold outside intended phase")
        for foot in FEET:
            if len(commands[foot]) != 3:
                raise ValueError(f"Seed{seed} action dimension differs")
            for value, prior in zip(commands[foot], previous[foot]):
                if not math.isfinite(value):
                    raise ValueError(f"Seed{seed} nonfinite action")
                if sample["front_foot_hold_applied"]:
                    peak = max(peak, abs(value) * 0.25)
                if 4.40 - 1e-8 <= time <= 6.22 + 1e-8:
                    max_step = max(max_step, abs(value - prior) * 0.25)
            previous[foot] = commands[foot]
        for foot_index, foot in enumerate(hold["support_foot_body_names"]):
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
            or not all(loaded.values()) or peak < 1e-5 or peak > 0.040001
            or max_step > 0.020001 or hold["front_foot_hold_steps"] != len(active)
            or abs(hold["front_foot_hold_max_target_delta_rad"] - peak) > 1e-6):
        raise ValueError(f"Seed{seed} hold schedule, sensors or limits invalid")
    after = next((sample for sample in hold["support_trace"] if sample["push_elapsed_s"] > 6.20 + 1e-8), None)
    if after is not None and not after["motion_ready"] and any(
        abs(value) > 1e-7 for foot in FEET for value in after["front_foot_hold_leg_actions"][foot]
    ):
        raise ValueError(f"Seed{seed} hold did not return to zero")
    return {
        "schema_version": 1,
        "seed": seed,
        "audit_source_sha256": sha256(Path(__file__)),
        "baseline_sha256": sha256(baseline_path),
        "hold_sha256": sha256(hold_path),
        "handoff_and_219_pre_hold_samples_equal": True,
        "hold_steps": len(active),
        "hold_first_s": active[0],
        "hold_last_s": active[-1],
        "hold_interrupted_before_ramp_out": active[-1] < 6.00 - 1e-8,
        "max_joint_target_offset_rad": peak,
        "max_joint_target_change_per_step_rad": max_step,
        "loaded_ground_samples_by_foot": loaded,
        "baseline_outcome": baseline["outcome"],
        "baseline_push_elapsed_s": baseline["push_elapsed_s"],
        "hold_outcome": hold["outcome"],
        "hold_push_elapsed_s": hold["push_elapsed_s"],
        "hold_terminal_reasons": hold["terminal"].get("reasons", {}),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, choices=tuple(BASELINE_SHA256), required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--hold", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error("Output file exists")
    result = check(args.baseline, args.hold, args.seed)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
