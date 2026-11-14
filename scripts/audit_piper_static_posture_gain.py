"""Compare old contact holds with candidate loaded endpoints at the same force grid."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path



def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(initial_path: Path, endpoint_path: Path) -> dict:
    initial = json.loads(initial_path.read_text())
    endpoint = json.loads(endpoint_path.read_text())
    if not (initial["source_report_sha256"] == endpoint["source_report_sha256"]
            and initial["profile_sha256"] == endpoint["profile_sha256"]
            and initial["arm_effort_limits_Nm"] == endpoint["arm_effort_limits_Nm"]
            and endpoint["all_eight_0_and_20N_passed"]
            and len(endpoint["endpoint_checks"]) == 8
            and all(row["geometry_screen_passed"] for row in endpoint["endpoint_checks"])):
        raise ValueError("Loaded endpoint model or geometry contract differs")
    def force_rows(source: dict) -> list[dict]:
        by_env = {env: [] for env in range(8)}
        for item in source["cases"]:
            by_env[item["env_id"]].append(item)
        results = []
        for env in range(8):
            cases = sorted(by_env[env], key=lambda x: x["assumed_resisting_force_N"])
            if ([x["assumed_resisting_force_N"] for x in cases] != [0, 5, 10, 15, 20, 25, 30]
                    or any(not x["support_feasible"] for x in cases)
                    or any(a["maximum_arm_ratio"] >= b["maximum_arm_ratio"]
                           for a, b in zip(cases, cases[1:]))):
                raise ValueError("Force grid or static support differs")
            def crossing(limit: float) -> float | None:
                if cases[0]["maximum_arm_ratio"] >= limit:
                    return 0.0
                for before, after in zip(cases, cases[1:]):
                    lo, hi = before["maximum_arm_ratio"], after["maximum_arm_ratio"]
                    if lo < limit <= hi:
                        return before["assumed_resisting_force_N"] + (limit - lo) * 5 / (hi - lo)
                return None
            results.append({
                "env_id": env, "ratio20": cases[4]["maximum_arm_ratio"],
                "budget90": crossing(0.9), "pass20": cases[4]["planning_screen_passed"],
            })
        return results
    old, new = force_rows(initial), force_rows(endpoint)
    rows = []
    for before, after in zip(old, new):
        if before["env_id"] != after["env_id"]:
            raise ValueError("Source environment order differs")
        rows.append({
            "env_id": before["env_id"],
            "held_posture_20N_joint2_ratio": before["ratio20"],
            "candidate_endpoint_20N_joint2_ratio": after["ratio20"],
            "candidate_minus_held_20N_ratio": (after["ratio20"]
                                                - before["ratio20"]),
            "held_posture_interpolated_90pct_force_N": before["budget90"],
            "candidate_endpoint_interpolated_90pct_force_N": after["budget90"],
        })
    return {
        "scope": "Seen source static endpoint design comparison; same 0-30 N hypothetical force grid, matched source report/profile/effort limits, no continuous path or dynamics",
        "source_sha256": {"held_posture": digest(initial_path), "candidate_endpoints": digest(endpoint_path),
                          "profile": initial["profile_sha256"],
                          "source_report": initial["source_report_sha256"]},
        "counts_at_20N": {"held_90pct_pass": sum(x["pass20"] for x in old),
                          "endpoint_90pct_pass": sum(x["pass20"] for x in new),
                          "held_over_hard_limit": sum(x["ratio20"] > 1 for x in old),
                          "endpoint_over_hard_limit": sum(x["ratio20"] > 1 for x in new)},
        "minimum_interpolated_90pct_force_N": {
            "held": min(x["budget90"] for x in old),
            "endpoint": min(x["budget90"] for x in new)},
        "per_env": rows,
        "limitations": "Endpoints were chosen using related static criteria on these seen states. The nearest contact witness changes with posture. This is a design check, not independent validation, continuous loaded motion, measured push force, or task improvement."
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--held-sweep", type=Path, required=True)
    parser.add_argument("--endpoint-audit", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args.held_sweep, args.endpoint_audit),
                     indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
