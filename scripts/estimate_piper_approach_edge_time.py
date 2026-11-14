"""Fit a descriptive waypoint-time model and freeze one direct-edge prediction."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fit(rows: list[dict]) -> tuple[float, float]:
    n = len(rows)
    sx = sum(row["joint_linf_rad"] for row in rows)
    sy = sum(row["duration_s"] for row in rows)
    sxx = sum(row["joint_linf_rad"] ** 2 for row in rows)
    sxy = sum(row["joint_linf_rad"] * row["duration_s"] for row in rows)
    denominator = n * sxx - sx * sx
    if n < 3 or denominator <= 0:
        raise ValueError("Insufficient variation for the waypoint-time fit")
    slope = (n * sxy - sx * sy) / denominator
    intercept = (sy - slope * sx) / n
    if not math.isfinite(slope) or not math.isfinite(intercept) or slope <= 0 or intercept < 0:
        raise ValueError("Waypoint-time fit is not physically interpretable")
    return intercept, slope


def audit(approach_path: Path, pairs: list[tuple[Path, Path]], start: int, end: int) -> dict:
    approach = json.loads(approach_path.read_text())
    waypoints = approach["waypoints"]
    if len(waypoints) != 21 or not 1 <= start < end - 1 < 20 or len(pairs) != 2:
        raise ValueError("Expected two frozen traces and an interior long edge")
    distances = {
        stage: max(abs(a - b) for a, b in zip(waypoints[stage - 1], waypoints[stage], strict=True))
        for stage in range(1, 21)
    }
    rows = []
    cases = []
    for plan_path, report_path in pairs:
        plan = json.loads(plan_path.read_text())
        report = json.loads(report_path.read_text())
        env = report["inspect_env_index"]
        if (plan["approach_sha256"] != sha256(approach_path)
                or plan["inspect_env_index"] != env
                or not report["failure_history_sample_phase"].startswith("pre_env_step")
                or report["seed"] != 3701 or report["requested_episodes"] != 8):
            raise ValueError("Trace provenance differs from the frozen cohort")
        trace = report[f"trace_env{env}"]
        if not trace or any(frame["step"] != index or frame["env_id"] != env
                            for index, frame in enumerate(trace)):
            raise ValueError("Expected a complete ordered control-step trace")
        dt = report["failure_history_step_dt"]
        if dt <= 0:
            raise ValueError("Expected a positive control-step duration")
        stages = []
        for stage in range(1, 21):
            frames = [frame for frame in trace if frame["safe_approach_index"] == stage]
            if not frames:
                raise ValueError(f"Missing stage {stage} in env {env}")
            row = {"env_id": env, "stage": stage, "joint_linf_rad": distances[stage],
                   "duration_s": len(frames) * dt}
            # Stage 1 also contains entry initialization, outside the direct-edge transition.
            if stage >= 2:
                rows.append(row)
            stages.append(row)
        cases.append({"env_id": env, "plan_sha256": sha256(plan_path),
                      "report_sha256": sha256(report_path),
                      "baseline_block_s": sum(row["duration_s"] for row in stages
                                              if start < row["stage"] <= end),
                      "removed_stage_s": sum(row["duration_s"] for row in stages
                                             if start < row["stage"] < end)})

    intercept, slope = fit(rows)
    residuals = [row["duration_s"] - (intercept + slope * row["joint_linf_rad"]) for row in rows]
    held_out = []
    for stage in range(2, 21):
        training = [row for row in rows if row["stage"] != stage]
        held_intercept, held_slope = fit(training)
        held_out.extend(row["duration_s"] - held_intercept - held_slope * row["joint_linf_rad"]
                        for row in rows if row["stage"] == stage)
    direct_distance = max(abs(a - b) for a, b in zip(waypoints[start], waypoints[end], strict=True))
    predicted_s = intercept + slope * direct_distance
    for case in cases:
        case["predicted_block_s"] = predicted_s
        case["predicted_saving_s"] = case["baseline_block_s"] - predicted_s
    return {
        "scope": "Seen-route descriptive linear fit; direct-edge timing prediction is unvalidated",
        "approach_sha256": sha256(approach_path),
        "edge": [start, end],
        "fit_formula": "duration_s = intercept_s + slope_s_per_rad * max_j(abs(q_end_j - q_start_j))",
        "fit_stage_count": 19,
        "fit_stage_range": [2, 20],
        "fit_trace_count": len(pairs),
        "intercept_s": intercept,
        "slope_s_per_rad": slope,
        "training_rmse_s": math.sqrt(sum(error * error for error in residuals) / len(residuals)),
        "leave_one_stage_out_mae_s": sum(abs(error) for error in held_out) / len(held_out),
        "leave_one_stage_out_max_abs_error_s": max(abs(error) for error in held_out),
        "direct_joint_linf_rad": direct_distance,
        "predicted_direct_edge_s": predicted_s,
        "cases": cases,
        "limitations": "Fitted only to sequential baseline stages in two seen traces. A direct edge can change base motion, support, actuator limits, settling, and later contact, so this estimate is not a measured saving, bound, safety gate, or 12 s acceptance result."
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approach", type=Path, required=True)
    parser.add_argument("--plan", type=Path, action="append", required=True)
    parser.add_argument("--report", type=Path, action="append", required=True)
    parser.add_argument("--edge-start-index", type=int, required=True)
    parser.add_argument("--edge-end-index", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or len(args.plan) != len(args.report):
        parser.error("Use matched plans/reports and a new output")
    result = audit(args.approach, list(zip(args.plan, args.report, strict=True)),
                   args.edge_start_index, args.edge_end_index)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"predicted_direct_edge_s": result["predicted_direct_edge_s"],
                      "predicted_saving_s": [case["predicted_saving_s"] for case in result["cases"]],
                      "leave_one_stage_out_max_abs_error_s": result["leave_one_stage_out_max_abs_error_s"]}))


if __name__ == "__main__":
    main()
