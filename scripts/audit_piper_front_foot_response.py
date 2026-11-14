"""Check frozen pre-pulse identity and bounded front-foot probe commands."""

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path


BASELINE_SHA256 = {
    5201: "9fcf7fef65ac62c650c80dc41bd09d0115c227b77f605e0e2f52ca6e6ecd9e37",
    5124: "8a44073e44709c03a388af1cb4f1d4ac040c3f1d06e16d629c0be5a50f4c6c91",
}
FEET = ("FL_foot", "FR_foot")


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(baseline_path, probe_path, seed, offset):
    if sha256(baseline_path) != BASELINE_SHA256[seed]:
        raise ValueError(f"Seed{seed} baseline hash differs")
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    probe = json.loads(probe_path.read_text(encoding="utf-8"))
    if (baseline["seed"] != seed or probe["seed"] != seed or probe["schema_version"] != 15
            or probe["front_foot_probe_offset_m"] != offset or probe["handoff"] != baseline["handoff"]
            or probe["control_sha256"] != baseline["control_sha256"]
            or probe["nav_actor_sha256"] != baseline["nav_actor_sha256"]
            or probe["push_checkpoint_sha256"] != baseline["push_checkpoint_sha256"]):
        raise ValueError(f"Seed{seed} handoff/source mismatch")
    baseline_trace = baseline["support_trace"]
    trace = probe["support_trace"]
    if len(trace) != probe["push_executed_steps"] or len(trace) < 240:
        raise ValueError(f"Seed{seed} trace incomplete")
    prefix_steps = 0
    active_times = []
    peak_target_delta = 0.0
    max_step_delta = 0.0
    previous = {foot: [0.0] * 3 for foot in FEET}
    for index, sample in enumerate(trace):
        elapsed = sample["push_elapsed_s"]
        if elapsed < 4.40 - 1e-8:
            old_sample = copy.deepcopy(sample)
            old_sample.pop("front_foot_probe_applied")
            old_sample.pop("front_foot_probe_leg_actions")
            if old_sample != baseline_trace[index]:
                raise ValueError(f"Seed{seed} pre-pulse sample {index} changed")
            prefix_steps += 1
        actions = sample["front_foot_probe_leg_actions"]
        if set(actions) != set(FEET) or any(len(actions[foot]) != 3 for foot in FEET):
            raise ValueError(f"Seed{seed} front-foot action layout mismatch")
        if sample["front_foot_probe_applied"]:
            active_times.append(elapsed)
            if not 4.40 - 1e-8 <= elapsed <= 4.80 + 1e-8 or sample["motion_ready"]:
                raise ValueError(f"Seed{seed} pulse ran outside intended phase")
        elif not sample["motion_ready"] and (elapsed < 4.40 - 1e-8 or elapsed > 4.80 + 1e-8):
            if any(abs(value) > 1e-7 for foot in FEET for value in actions[foot]):
                raise ValueError(f"Seed{seed} nonzero front action outside pulse")
        for foot in FEET:
            for value, prior in zip(actions[foot], previous[foot]):
                if not math.isfinite(value):
                    raise ValueError(f"Seed{seed} nonfinite probe action")
                if sample["front_foot_probe_applied"]:
                    peak_target_delta = max(peak_target_delta, abs(value) * 0.25)
                if 4.40 - 1e-8 <= elapsed <= 4.82 + 1e-8:
                    max_step_delta = max(max_step_delta, abs(value - prior) * 0.25)
            previous[foot] = actions[foot]
        contacts = sample["ground_contacts"]
        for foot, contact in contacts.items():
            force = contact["ground_normal_force"]
            net = sample["foot_normal_forces_n"][probe["support_foot_body_names"].index(foot)]
            if len(force) != 3 or not all(math.isfinite(v) for v in force):
                raise ValueError(f"Seed{seed} invalid ground force")
            if abs(force[2] - net) > 1e-3:
                raise ValueError(f"Seed{seed} ground/net force mismatch: {foot}")
            if net > 2 and (contact["ground_contact_pos"] is None
                             or not all(math.isfinite(v) for v in contact["ground_contact_pos"])):
                raise ValueError(f"Seed{seed} loaded foot lacks contact point: {foot}")
    if (prefix_steps != 219 or len(active_times) < 18
            or active_times[0] != 4.40 or peak_target_delta < 1e-5
            or peak_target_delta > 0.040001 or max_step_delta > 0.020001
            or abs(probe["front_foot_probe_max_target_delta_rad"] - peak_target_delta) > 1e-6
            or probe["front_foot_probe_steps"] != len(active_times)):
        raise ValueError(f"Seed{seed} pulse schedule or limits invalid")
    first_after = next((sample for sample in trace if sample["push_elapsed_s"] > 4.80 + 1e-8), None)
    if first_after is None or any(abs(v) > 1e-7 for foot in FEET
                                  for v in first_after["front_foot_probe_leg_actions"][foot]):
        raise ValueError(f"Seed{seed} pulse did not return to zero")
    return {
        "seed": seed,
        "offset_m": offset,
        "baseline_sha256": sha256(baseline_path),
        "probe_sha256": sha256(probe_path),
        "handoff_and_219_pre_pulse_samples_equal": True,
        "pulse_steps": len(active_times),
        "pulse_first_s": active_times[0],
        "pulse_last_s": active_times[-1],
        "max_joint_target_offset_rad": peak_target_delta,
        "max_joint_target_step_change_rad": max_step_delta,
        "outcome": probe["outcome"],
        "terminal_reasons": probe["terminal"].get("reasons", {}),
        "push_executed_steps": probe["push_executed_steps"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--probe", type=Path, required=True)
    parser.add_argument("--seed", type=int, choices=(5201, 5124), required=True)
    parser.add_argument("--offset-m", type=float, choices=(-0.005, 0.005), required=True)
    parser.add_argument("--output-json", type=Path)
    args = parser.parse_args()
    result = check(args.baseline, args.probe, args.seed, args.offset_m)
    if args.output_json:
        with args.output_json.open("x", encoding="utf-8") as stream:
            json.dump(result, stream, indent=2, allow_nan=False)
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
