"""Describe paired signed front-foot pulse responses without fitting a gate."""

import argparse
import hashlib
import json
import math
from pathlib import Path


WINDOWS = ((4.40, 4.80), (4.80, 5.20), (5.20, 5.60))
BASELINE_SHA256 = {
    5201: "9fcf7fef65ac62c650c80dc41bd09d0115c227b77f605e0e2f52ca6e6ecd9e37",
    5124: "8a44073e44709c03a388af1cb4f1d4ac040c3f1d06e16d629c0be5a50f4c6c91",
}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pitch(quaternion):
    w, x, y, z = quaternion
    return math.asin(max(-1.0, min(1.0, 2.0 * (w * y - z * x))))


def quantities(record):
    forces = record["foot_normal_forces_n"]
    return {
        "base_height_m": record["base_pos"][2],
        "base_pitch_rad": pitch(record["base_quat"]),
        "front_force_n": sum(forces[:2]),
        "rear_force_n": sum(forces[2:]),
        "rear_force_fraction": sum(forces[2:]) / sum(forces) if sum(forces) > 0 else None,
    }


def window_delta(baseline, probe, start, end):
    rows = []
    for old, new in zip(baseline, probe):
        time = old["push_elapsed_s"]
        if start - 1e-8 <= time < end - 1e-8:
            if abs(time - new["push_elapsed_s"]) > 1e-8:
                raise ValueError("Paired sample times differ")
            original = quantities(old)
            candidate = quantities(new)
            rows.append({key: candidate[key] - original[key] for key in original
                         if candidate[key] is not None and original[key] is not None})
    if len(rows) != round((end - start) / 0.02):
        raise ValueError(f"Incomplete paired window {start}-{end}")
    return {"window_push_s": [start, end], "samples": len(rows),
            "mean_probe_minus_baseline": {
                key: sum(row[key] for row in rows) / len(rows) for key in rows[0]
            }}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--baseline-dir", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error("Output file exists")
    results = []
    for seed in (5201, 5124):
        baseline_path = args.baseline_dir / f"seed{seed}-base-contact-source.json"
        if sha256(baseline_path) != BASELINE_SHA256[seed]:
            raise ValueError(f"Seed{seed} baseline hash differs")
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
        for direction, offset in (("up", 0.005), ("down", -0.005)):
            path = args.artifact_dir / f"seed{seed}-front-{direction}.json"
            report = json.loads(path.read_text(encoding="utf-8"))
            audit = json.loads((args.artifact_dir / f"seed{seed}-front-{direction}-audit.json")
                               .read_text(encoding="utf-8"))
            if (report["seed"] != seed or report["front_foot_probe_offset_m"] != offset
                    or audit["probe_sha256"] != sha256(path)
                    or not audit["handoff_and_219_pre_pulse_samples_equal"]):
                raise ValueError(f"Seed{seed} {direction} audit mismatch")
            results.append({
                "seed": seed,
                "offset_m": offset,
                "report_sha256": sha256(path),
                "baseline_sha256": sha256(baseline_path),
                "outcome": report["outcome"],
                "termination_reasons": report["terminal"].get("reasons", {}),
                "push_elapsed_s": report["push_elapsed_s"],
                "baseline_push_elapsed_s": baseline["push_elapsed_s"],
                "termination_time_difference_s": report["push_elapsed_s"] - baseline["push_elapsed_s"],
                "pulse_steps": audit["pulse_steps"],
                "max_joint_target_offset_rad": audit["max_joint_target_offset_rad"],
                "windows": [window_delta(baseline["support_trace"], report["support_trace"], *window)
                            for window in WINDOWS],
            })
    summary = {
        "schema_version": 1,
        "scope": "Known-state signed pulse system identification; paired mean responses are descriptive and do not define control thresholds",
        "analysis_sha256": sha256(Path(__file__)),
        "results": results,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x", encoding="utf-8") as stream:
        json.dump(summary, stream, indent=2, allow_nan=False)
    print(json.dumps(results, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
