"""Compare bounded front-foot hold trajectories with archived same-seed baselines."""

import argparse
import hashlib
import json
from pathlib import Path

from analyze_piper_front_foot_response import pitch


BASELINES = {
    5503: ("front-foot-response-holdout-5501-5508/seed5503-baseline.json",
           "bf9669306af36b0ac53b379f8acce1d9110298bf66cf0d3990e8f9cfac0139f0"),
    5506: ("front-foot-response-holdout-5501-5508/seed5506-baseline.json",
           "f867c7d4958816c31ed014f972ee9676c125c2e8031dfb237751e9edf5acc490"),
    5201: ("base-contact-source-known-state/seed5201-base-contact-source.json",
           "9fcf7fef65ac62c650c80dc41bd09d0115c227b77f605e0e2f52ca6e6ecd9e37"),
    5124: ("base-contact-source-known-state/seed5124-base-contact-source.json",
           "8a44073e44709c03a388af1cb4f1d4ac040c3f1d06e16d629c0be5a50f4c6c91"),
}
TIMES_S = (4.60, 5.20, 5.60, 5.80)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot(sample):
    forces = sample["foot_normal_forces_n"]
    return {
        "base_pitch_rad": pitch(sample["base_quat"]),
        "base_height_m": sample["base_pos"][2],
        "front_force_n": sum(forces[:2]),
        "rear_force_n": sum(forces[2:]),
        "supported_feet_gt_2n": sample["supported_feet_gt_2n"],
        "arm_approach_index": sample["arm_approach_index"],
        "motion_ready": sample["motion_ready"],
    }


def outcome(report):
    reasons = report["terminal"].get("reasons", {})
    if reasons.get("box_settled"):
        return "box_settled"
    for reason in ("base_contact", "invalid_hand_contact", "box_contact", "bad_orientation",
                   "box_tipped", "low_posture", "arm_body_clearance"):
        if reasons.get(reason):
            return reason
    return report["outcome"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--hold-dir", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error("Output file already exists")
    results = []
    for seed, (baseline_name, baseline_hash) in BASELINES.items():
        baseline_path = args.artifact_root / baseline_name
        hold_path = args.hold_dir / f"seed{seed}-front-hold.json"
        audit_path = args.hold_dir / f"seed{seed}-front-hold-audit.json"
        if sha256(baseline_path) != baseline_hash:
            raise ValueError(f"Seed{seed} baseline hash differs")
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
        hold = json.loads(hold_path.read_text(encoding="utf-8"))
        audit = json.loads(audit_path.read_text(encoding="utf-8"))
        if (audit["baseline_sha256"] != baseline_hash or audit["hold_sha256"] != sha256(hold_path)
                or not audit["handoff_and_219_pre_hold_samples_equal"]
                or hold["seed"] != seed or baseline["seed"] != seed):
            raise ValueError(f"Seed{seed} source or audit mismatch")
        comparisons = []
        for time in TIMES_S:
            index = round(time / hold["step_dt"]) - 1
            if index >= min(len(baseline["support_trace"]), len(hold["support_trace"])):
                continue
            old = baseline["support_trace"][index]
            new = hold["support_trace"][index]
            if abs(old["push_elapsed_s"] - time) > 1e-8 or abs(new["push_elapsed_s"] - time) > 1e-8:
                raise ValueError(f"Seed{seed} sample time differs at {time}")
            old_values = snapshot(old)
            new_values = snapshot(new)
            comparisons.append({
                "push_elapsed_s": time,
                "baseline": old_values,
                "hold": new_values,
                "hold_minus_baseline": {
                    key: new_values[key] - old_values[key]
                    for key in ("base_pitch_rad", "base_height_m", "front_force_n", "rear_force_n")
                },
            })
        results.append({
            "seed": seed,
            "baseline_sha256": baseline_hash,
            "hold_sha256": sha256(hold_path),
            "audit_sha256": sha256(audit_path),
            "baseline_outcome": outcome(baseline),
            "baseline_push_elapsed_s": baseline["push_elapsed_s"],
            "hold_outcome": outcome(hold),
            "hold_push_elapsed_s": hold["push_elapsed_s"],
            "hold_steps": audit["hold_steps"],
            "hold_max_joint_target_offset_rad": audit["max_joint_target_offset_rad"],
            "comparisons": comparisons,
        })
    summary = {
        "schema_version": 1,
        "scope": "Known-state descriptive comparison; no closed-loop control or independent validation",
        "analysis_sha256": sha256(Path(__file__)),
        "results": results,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x", encoding="utf-8") as stream:
        json.dump(summary, stream, indent=2, allow_nan=False)
    print(json.dumps([{key: row[key] for key in ("seed", "baseline_outcome", "hold_outcome",
                                               "hold_push_elapsed_s")} for row in results], indent=2))


if __name__ == "__main__":
    main()
