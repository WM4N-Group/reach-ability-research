"""Validate a new-state baseline and signed front-foot pulse pair."""

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path


FEET = ("FL_foot", "FR_foot")


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path, seed):
    report = json.loads(path.read_text(encoding="utf-8"))
    if (report["seed"] != seed or len(report["support_trace"]) != report["push_executed_steps"]
            or report["step_dt"] != 0.02 or not report["record_base_contact_source"]):
        raise ValueError(f"Unexpected report layout: {path}")
    return report


def sensor_quality(report):
    names = report["support_foot_body_names"]
    if set(names) != {"FL_foot", "FR_foot", "RL_foot", "RR_foot"}:
        raise ValueError("Unexpected foot layout")
    loaded = {name: 0 for name in names}
    for sample in report["support_trace"]:
        for index, name in enumerate(names):
            contact = sample["ground_contacts"][name]
            normal = contact["ground_normal_force"][2]
            net = sample["foot_normal_forces_n"][index]
            if not math.isfinite(normal) or abs(normal - net) > 1e-3:
                raise ValueError(f"Ground/net force mismatch: {name}")
            if normal > 2:
                point = contact["ground_contact_pos"]
                if point is None or not all(math.isfinite(value) for value in point):
                    raise ValueError(f"Loaded foot lacks ground point: {name}")
                loaded[name] += 1
    if not all(loaded.values()):
        raise ValueError("No loaded samples for a foot")
    return loaded


def inspect_probe(baseline, report, direction):
    offset = 0.005 if direction == "up" else -0.005
    if (report["schema_version"] != 15 or report["front_foot_probe_offset_m"] != offset
            or report["handoff"] != baseline["handoff"]
            or report["control_sha256"] != baseline["control_sha256"]
            or report["nav_actor_sha256"] != baseline["nav_actor_sha256"]
            or report["push_checkpoint_sha256"] != baseline["push_checkpoint_sha256"]):
        raise ValueError(f"{direction} source or handoff mismatch")
    trace = report["support_trace"]
    old_trace = baseline["support_trace"]
    prefix = 0
    active = []
    peak = 0.0
    max_step = 0.0
    previous = {name: [0.0] * 3 for name in FEET}
    for index, sample in enumerate(trace):
        time = sample["push_elapsed_s"]
        if time < 4.40 - 1e-8:
            original = copy.deepcopy(sample)
            original.pop("front_foot_probe_applied")
            original.pop("front_foot_probe_leg_actions")
            if original != old_trace[index]:
                raise ValueError(f"{direction} pre-pulse sample {index} differs")
            prefix += 1
        commands = sample["front_foot_probe_leg_actions"]
        if set(commands) != set(FEET):
            raise ValueError(f"{direction} action layout differs")
        if sample["front_foot_probe_applied"]:
            active.append(time)
            if not 4.40 - 1e-8 <= time <= 4.80 + 1e-8 or sample["motion_ready"]:
                raise ValueError(f"{direction} probe outside intended phase")
        for foot in FEET:
            if len(commands[foot]) != 3:
                raise ValueError(f"{direction} leg action dimension differs")
            for value, prior in zip(commands[foot], previous[foot]):
                if not math.isfinite(value):
                    raise ValueError(f"{direction} nonfinite action")
                if sample["front_foot_probe_applied"]:
                    peak = max(peak, abs(value) * 0.25)
                if 4.40 - 1e-8 <= time <= 4.82 + 1e-8:
                    max_step = max(max_step, abs(value - prior) * 0.25)
            previous[foot] = commands[foot]
    if (prefix != 219 or not active or abs(active[0] - 4.40) > 1e-8
            or peak > 0.040001 or peak < 1e-5 or max_step > 0.020001
            or report["front_foot_probe_steps"] != len(active)
            or abs(report["front_foot_probe_max_target_delta_rad"] - peak) > 1e-6):
        raise ValueError(f"{direction} pulse schedule or limits invalid")
    after = next((sample for sample in trace if sample["push_elapsed_s"] > 4.80 + 1e-8), None)
    if after is not None and not after["motion_ready"] and any(
        abs(value) > 1e-7 for foot in FEET for value in after["front_foot_probe_leg_actions"][foot]
    ):
        raise ValueError(f"{direction} probe did not return to zero")
    return {
        "offset_m": offset,
        "pre_pulse_219_samples_equal": True,
        "pulse_steps": len(active),
        "pulse_first_s": active[0],
        "pulse_last_s": active[-1],
        "max_joint_target_offset_rad": peak,
        "max_joint_target_change_per_step_rad": max_step,
        "loaded_ground_samples_by_foot": sensor_quality(report),
        "outcome": report["outcome"],
        "push_elapsed_s": report["push_elapsed_s"],
        "terminal_reasons": report["terminal"].get("reasons", {}),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--up", type=Path, required=True)
    parser.add_argument("--down", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error("Output file exists")
    paths = {"baseline": args.baseline, "up": args.up, "down": args.down}
    reports = {name: load(path, args.seed) for name, path in paths.items()}
    baseline = reports["baseline"]
    if baseline["schema_version"] != 14 or len(baseline["support_trace"]) < 280:
        raise ValueError("Baseline is not pulse eligible")
    result = {
        "schema_version": 1,
        "seed": args.seed,
        "source_sha256": sha256(Path(__file__)),
        "input_sha256": {name: sha256(path) for name, path in paths.items()},
        "baseline": {
            "loaded_ground_samples_by_foot": sensor_quality(baseline),
            "outcome": baseline["outcome"],
            "push_elapsed_s": baseline["push_elapsed_s"],
            "terminal_reasons": baseline["terminal"].get("reasons", {}),
        },
        "up": inspect_probe(baseline, reports["up"], "up"),
        "down": inspect_probe(baseline, reports["down"], "down"),
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
    print(f"seed={args.seed} baseline={result['baseline']['outcome']} "
          f"up={result['up']['outcome']} down={result['down']['outcome']}")


if __name__ == "__main__":
    main()
