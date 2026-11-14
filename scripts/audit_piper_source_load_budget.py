"""Derive descriptive arm-force budgets from a frozen static load sweep."""

from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path


FORCES_N = (0, 5, 10, 15, 20, 25, 30)


def crossing(rows: list[dict], limit: float) -> float | None:
    if rows[0]["maximum_arm_ratio"] >= limit:
        return 0.0
    for before, after in zip(rows, rows[1:]):
        low, high = before["maximum_arm_ratio"], after["maximum_arm_ratio"]
        if low < limit <= high:
            return (before["assumed_resisting_force_N"]
                    + (limit - low) * (after["assumed_resisting_force_N"]
                                       - before["assumed_resisting_force_N"]) / (high - low))
    return None


def audit(path: Path) -> dict:
    source = json.loads(path.read_text())
    by_env: dict[int, list[dict]] = defaultdict(list)
    for case in source["cases"]:
        by_env[case["env_id"]].append(case)
    if sorted(by_env) != list(range(8)):
        raise ValueError("Expected eight actual contact states")
    results = []
    for env in range(8):
        rows = sorted(by_env[env], key=lambda r: r["assumed_resisting_force_N"])
        if ([row["assumed_resisting_force_N"] for row in rows] != list(FORCES_N)
                or any(row["worst_arm_joint"] != "joint2" for row in rows)
                or any(not row["support_feasible"] for row in rows)
                or any(a["maximum_arm_ratio"] >= b["maximum_arm_ratio"]
                       for a, b in zip(rows, rows[1:]))):
            raise ValueError("Force grid, joint or static support differs")
        for row in rows:
            if abs(row["maximum_arm_ratio"] - max(row["arm_static_ratio"])) > 1e-10:
                raise ValueError("Per-joint arm ratios differ")
        results.append({
            "env_id": env,
            "joint2_ratio_at_0N": rows[0]["maximum_arm_ratio"],
            "joint2_ratio_at_20N": rows[4]["maximum_arm_ratio"],
            "maximum_force_for_90pct_arm_budget_interpolated_N": crossing(rows, 0.9),
            "maximum_force_for_100pct_arm_limit_interpolated_N": crossing(rows, 1.0),
            "sampled_20N_static_screen_passed": rows[4]["planning_screen_passed"],
            "sampled_20N_support_feasible": rows[4]["support_feasible"],
        })
    return {
        "scope": "Source v155 hypothetical static normal-force sweep on v153 stable contact states; interpolation within sampled grid only",
        "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "source_report_sha256": source["source_report_sha256"],
        "source_script_sha256": source["script_sha256"],
        "source_profile_sha256": source["profile_sha256"],
        "force_grid_N": FORCES_N,
        "cases": results,
        "joint_90pct_budget_force_min_N": min(row["maximum_force_for_90pct_arm_budget_interpolated_N"]
                                          for row in results),
        "joint_100pct_limit_force_min_N": min(row["maximum_force_for_100pct_arm_limit_interpolated_N"]
                                          for row in results),
        "over_100pct_at_20N_count": sum(row["joint2_ratio_at_20N"] > 1 for row in results),
        "source_20N_planning_pass_count": sum(row["sampled_20N_static_screen_passed"]
                                              for row in results),
        "limitations": "Interpolated budgets describe only the assumed contact point, normal force, matched masses and static posture. No applied force, dynamics, hand moment, locomotion, or calibrated online bound. Passing 90% is a design reserve, not original actuator limit."
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-sweep", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args.source_sweep), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
