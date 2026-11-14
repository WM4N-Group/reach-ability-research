"""Audit phase-labelled command references in a pinned PUSH failure-history report."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def vector(sample: dict, name: str) -> list[float]:
    value = sample[name]
    require(isinstance(value, list) and len(value) == 6
            and all(type(item) in (int, float) and math.isfinite(item) for item in value),
            f"Invalid six-joint vector: {name}")
    return value


def gate(sample: dict, name: str) -> bool:
    value = sample[name]
    require(type(value) in (int, float) and value in (0, 1),
            f"Invalid binary gate: {name}")
    return bool(value)


def audit_report(report: dict, difference_tol_rad: float = 1e-6) -> dict:
    require(math.isfinite(difference_tol_rad) and difference_tol_rad >= 0,
            "difference_tol_rad must be finite and nonnegative")
    phase = report["failure_history_sample_phase"]
    require(isinstance(phase, str) and phase.startswith("pre_env_step;")
            and "previous command" in phase and "next action" in phase,
            "Failure history is not labelled as previous-command pre-step data")
    dt = report["failure_history_step_dt"]
    steps = report["failure_history_steps"]
    require(type(dt) in (int, float) and math.isfinite(dt) and dt > 0
            and type(steps) is int and steps > 0,
            "Invalid failure-history sampling grid")
    histories = report["failure_histories"]
    require(isinstance(histories, list) and histories,
            "No failure histories")

    totals = {"samples": 0, "ik_pre_exact_different": 0,
              "ik_pre_over_tolerance": 0, "pre_post_exact_different": 0,
              "pre_post_over_tolerance": 0, "post_reference_exact_equal": 0}
    per_env = []
    seen = set()
    for history in sorted(histories, key=lambda item: item["env_id"]):
        identity = (history["env_id"], history["episode"])
        require(identity not in seen, "Duplicate failure-history identity")
        seen.add(identity)
        samples = history["pre_step_samples"]
        require(isinstance(samples, list) and len(samples) == steps,
                "Incomplete failure-history window")
        counts = {"geometric_ready": 0, "velocity_ready": 0,
                  "both_ready": 0, "longest_both_ready_run": 0,
                  "pre_post_over_tolerance": 0}
        run = 0
        for sample in samples:
            desired = vector(sample, "debug_pose_desired")
            pre = vector(sample, "debug_reference_pre_geometry")
            post = vector(sample, "debug_reference_post_geometry")
            reference = vector(sample, "arm_joint_reference")
            ik_pre_delta = max(abs(a - b) for a, b in zip(desired, pre))
            pre_post_delta = max(abs(a - b) for a, b in zip(pre, post))
            totals["samples"] += 1
            totals["ik_pre_exact_different"] += int(desired != pre)
            totals["ik_pre_over_tolerance"] += int(ik_pre_delta > difference_tol_rad)
            totals["pre_post_exact_different"] += int(pre != post)
            changed = pre_post_delta > difference_tol_rad
            totals["pre_post_over_tolerance"] += int(changed)
            counts["pre_post_over_tolerance"] += int(changed)
            totals["post_reference_exact_equal"] += int(post == reference)
            geometric = gate(sample, "debug_gate_geometric_ready")
            velocity = gate(sample, "debug_gate_velocity_ready")
            counts["geometric_ready"] += int(geometric)
            counts["velocity_ready"] += int(velocity)
            counts["both_ready"] += int(geometric and velocity)
            run = run + 1 if geometric and velocity else 0
            counts["longest_both_ready_run"] = max(counts["longest_both_ready_run"], run)
        per_env.append({"env_id": identity[0], "episode": identity[1], **counts})
    return {"scope": "Observed terminal windows only; no actuator tracking or action enclosure proof",
            "gate_condition_scope": "Raw height-alignment conditions, which may stay true after the height gate latches; not face-ready confirmation",
            "sample_phase": phase, "step_dt_s": dt, "samples_per_history": steps,
            "difference_tol_rad": difference_tol_rad, "totals": totals,
            "per_env": per_env, "contact_authorized": False}


def audit_file(path: Path, expected_sha256: str, difference_tol_rad: float) -> dict:
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    require(digest == expected_sha256, f"Report hash differs: {path}")
    return {"report_path": str(path), "report_sha256": digest,
            **audit_report(json.loads(raw), difference_tol_rad)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--difference-tol-rad", type=float, default=1e-6)
    args = parser.parse_args()
    print(json.dumps(audit_file(args.report, args.sha256, args.difference_tol_rad),
                     indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
