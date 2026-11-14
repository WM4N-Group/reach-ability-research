"""Summarize all eight registered independent front-foot response states."""

import argparse
import hashlib
import json
from pathlib import Path

from analyze_piper_front_foot_response import pitch


SEEDS = range(5501, 5509)
TIMES = (4.60, 5.20, 5.60)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def quantities(sample):
    force = sample["foot_normal_forces_n"]
    return {
        "base_pitch_rad": pitch(sample["base_quat"]),
        "base_height_m": sample["base_pos"][2],
        "front_height_relative_to_base_m": sum(
            sample["foot_body_pos"][index][2] - sample["base_pos"][2] for index in (0, 1)
        ) / 2,
        "front_normal_force_n": sum(force[:2]),
        "rear_normal_force_n": sum(force[2:]),
    }


def response(reports, time):
    index = round(time / 0.02) - 1
    if any(len(report["support_trace"]) <= index for report in reports.values()):
        return None
    samples = {name: report["support_trace"][index] for name, report in reports.items()}
    if any(abs(sample["push_elapsed_s"] - time) > 1e-8 for sample in samples.values()):
        raise ValueError(f"Sample time differs at {time}")
    measured = {name: quantities(sample) for name, sample in samples.items()}
    return {key: {
        "baseline": measured["baseline"][key],
        "odd_half_difference": (measured["up"][key] - measured["down"][key]) / 2,
        "even_remainder": (measured["up"][key] + measured["down"][key]) / 2
        - measured["baseline"][key],
    } for key in measured["baseline"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error("Output file exists")
    results = []
    for seed in SEEDS:
        baseline_path = args.artifact_dir / f"seed{seed}-baseline.json"
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
        if baseline["seed"] != seed or not baseline["record_base_contact_source"]:
            raise ValueError(f"Invalid seed{seed} baseline")
        trace = baseline["support_trace"]
        eligible = len(trace) >= 280 and not trace[219]["motion_ready"]
        result = {
            "seed": seed,
            "baseline_sha256": sha256(baseline_path),
            "baseline_outcome": baseline["outcome"],
            "baseline_push_steps": baseline["push_executed_steps"],
            "baseline_terminal_reasons": baseline["terminal"].get("reasons", {}),
            "pulse_eligible_from_baseline": eligible,
        }
        if eligible:
            paths = {name: args.artifact_dir / f"seed{seed}-{name}.json"
                     for name in ("front-up", "front-down")}
            audit_path = args.artifact_dir / f"seed{seed}-pair-audit.json"
            audit = json.loads(audit_path.read_text(encoding="utf-8"))
            if (audit["seed"] != seed or audit["input_sha256"]["baseline"] != sha256(baseline_path)
                    or any(audit["input_sha256"][name.removeprefix("front-")] != sha256(path)
                           for name, path in paths.items())):
                raise ValueError(f"Seed{seed} pair audit mismatch")
            reports = {"baseline": baseline, **{
                name.removeprefix("front-"): json.loads(path.read_text(encoding="utf-8"))
                for name, path in paths.items()
            }}
            result["pair_audit_sha256"] = sha256(audit_path)
            result["probe_sha256"] = {name.removeprefix("front-"): sha256(path)
                                      for name, path in paths.items()}
            result["probe_outcomes"] = {name: report["outcome"] for name, report in reports.items()
                                         if name != "baseline"}
            result["probe_terminal_reasons"] = {name: report["terminal"].get("reasons", {})
                                                 for name, report in reports.items() if name != "baseline"}
            result["pulse_window_torque_clipping_samples"] = {
                name: sum(
                    any(abs(computed - applied) > 1e-5 for computed, applied in
                        zip(sample["computed_torque"], sample["applied_torque"]))
                    for sample in report["support_trace"]
                    if 4.40 - 1e-8 <= sample["push_elapsed_s"] <= 4.80 + 1e-8
                ) for name, report in reports.items() if name != "baseline"
            }
            result["response_by_push_time_s"] = {str(time): response(reports, time) for time in TIMES}
        results.append(result)
    primary = [row["response_by_push_time_s"]["4.6"] for row in results
               if row["pulse_eligible_from_baseline"] and row["response_by_push_time_s"]["4.6"] is not None]
    output = {
        "schema_version": 1,
        "scope": "All eight preregistered seeds, including ineligible baseline states; signed response is descriptive, not a control certificate",
        "analysis_sha256": sha256(Path(__file__)),
        "registered_seed_count": len(SEEDS),
        "baseline_pulse_eligible_count": sum(row["pulse_eligible_from_baseline"] for row in results),
        "primary_response_evaluable_count": len(primary),
        "primary_sign_counts": {
            "up_increases_base_pitch": sum(row["base_pitch_rad"]["odd_half_difference"] > 0 for row in primary),
            "up_lowers_base_height": sum(row["base_height_m"]["odd_half_difference"] < 0 for row in primary),
            "up_raises_front_foot_relative_to_base": sum(
                row["front_height_relative_to_base_m"]["odd_half_difference"] > 0 for row in primary
            ),
        },
        "results": results,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x", encoding="utf-8") as stream:
        json.dump(output, stream, indent=2, allow_nan=False)
    print(json.dumps({key: output[key] for key in ("registered_seed_count", "baseline_pulse_eligible_count",
                                                 "primary_response_evaluable_count", "primary_sign_counts")}, indent=2))


if __name__ == "__main__":
    main()
