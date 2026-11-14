"""Replay one frozen preparation warning over four unmodified Isaac cohorts."""

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path


COHORTS = (
    ("5101-5124", "2026-10-03/dynamic-warning-holdout-5101-5124", 5101),
    ("5201-5224", "2026-10-03/phase-warning-holdout-5201-5224", 5201),
    ("5701-5724", "2026-10-04/nav-push-baseline-5701-5724", 5701),
    ("5801-5824", "2026-10-04/support-warning-cohort-5801-5824", 5801),
)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def outcome(report):
    if report["outcome"] != "push_terminated":
        return report["outcome"]
    reasons = report["terminal"]["reasons"]
    if reasons["box_settled"]:
        return "box_settled"
    if any(value for key, value in reasons.items() if key != "box_settled"):
        return "safety_termination"
    raise ValueError(f"Unclassified PUSH terminal for seed {report['seed']}")


def first_warning(trace, step_dt):
    consecutive = 0
    for step, sample in enumerate(trace, start=1):
        if (not math.isclose(sample["push_elapsed_s"], step * step_dt, abs_tol=1e-7)
                or not math.isfinite(sample["base_pos"][2])
                or len(sample["foot_normal_forces_n"]) != 4
                or not all(math.isfinite(force) for force in sample["foot_normal_forces_n"])):
            raise ValueError(f"Invalid support sample at PUSH step {step}")
        forces = sample["foot_normal_forces_n"]
        active = (not sample["motion_ready"] and sample["base_pos"][2] < 0.27
                  and (forces[2] < 2.0 or forces[3] < 2.0))
        consecutive = consecutive + 1 if active else 0
        if consecutive == 5:
            return sample["push_elapsed_s"]
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error("Output file exists")

    expected_sources = None
    cohorts = []
    all_rows = []
    for name, relative_path, first_seed in COHORTS:
        rows = []
        report_hashes = []
        for seed in range(first_seed, first_seed + 24):
            path = args.artifact_root / relative_path / f"seed{seed}-baseline.json"
            report_hashes.append(f"{seed}:{sha256(path)}\n")
            report = json.loads(path.read_text(encoding="utf-8"))
            sources = (report["nav_actor_sha256"], report["push_checkpoint_sha256"],
                       tuple(sorted(report["control_sha256"].items())))
            if expected_sources is None:
                expected_sources = sources
            if (report["seed"] != seed or sources != expected_sources
                    or report["nav_start_x_m"] != -0.25
                    or report["nav_goal_xyyaw"] != [-0.05, 0.0, 0.0]
                    or report["step_dt"] != 0.02
                    or report["push_budget_s"] != 12.0
                    or report["pre_ready_leg_action_cap"] != 0.0
                    or report.get("handoff_settle_stable_s", 0.0) != 0.0
                    or len(report["support_trace"]) != report["push_executed_steps"]):
                raise ValueError(f"Cohort contract differs for seed {seed}")
            label = outcome(report)
            warning_s = first_warning(report["support_trace"], report["step_dt"])
            if warning_s is not None and label in ("nav_timeout", "nav_terminated"):
                raise ValueError(f"Warning before PUSH for seed {seed}")
            rows.append({"seed": seed, "outcome": label, "warning_push_s": warning_s,
                         "safe_approach_complete_s": report.get("safe_approach_complete_s"),
                         "motion_ready_s": report.get("motion_ready_s"),
                         "warning_before_safe_approach_complete": (
                             report.get("safe_approach_complete_s") is None
                             or warning_s < report["safe_approach_complete_s"]
                         ) if warning_s is not None else None,
                         "terminal_push_s": report["push_elapsed_s"] if report["push_executed_steps"] else None})
        all_rows.extend(rows)
        cohorts.append({
            "name": name,
            "source_dir": f"../artifacts/go2-piper/{relative_path}",
            "report_hash_manifest_sha256": hashlib.sha256("".join(report_hashes).encode()).hexdigest(),
            "outcomes": dict(sorted(Counter(row["outcome"] for row in rows).items())),
            "warning_by_outcome": dict(sorted(Counter(row["outcome"] for row in rows
                                                   if row["warning_push_s"] is not None).items())),
            "warning_before_safe_approach_complete_by_outcome": dict(sorted(Counter(
                row["outcome"] for row in rows
                if row["warning_before_safe_approach_complete"]).items())),
            "warning_cases": [row for row in rows if row["warning_push_s"] is not None],
        })

    safety_leads = [row["terminal_push_s"] - row["warning_push_s"] for row in all_rows
                    if row["outcome"] == "safety_termination" and row["warning_push_s"] is not None]
    result = {
        "schema_version": 1,
        "scope": "Retrospective, read-only same-scene replay; warning detection is not action benefit",
        "analysis_sha256": sha256(Path(__file__)),
        "rule": "Before motion_ready: five consecutive 20 ms post-step samples with base z < 0.27 m and RL or RR normal force < 2 N",
        "shared_nav_actor_sha256": expected_sources[0],
        "shared_push_checkpoint_sha256": expected_sources[1],
        "shared_control_sha256": dict(expected_sources[2]),
        "total_nav_starts": len(all_rows),
        "outcomes": dict(sorted(Counter(row["outcome"] for row in all_rows).items())),
        "warning_by_outcome": dict(sorted(Counter(row["outcome"] for row in all_rows
                                               if row["warning_push_s"] is not None).items())),
        "warning_before_safe_approach_complete_by_outcome": dict(sorted(Counter(
            row["outcome"] for row in all_rows
            if row["warning_before_safe_approach_complete"]).items())),
        "safety_warning_to_terminal_s_range": [min(safety_leads), max(safety_leads)],
        "cohorts": cohorts,
        "interpretation": "The 5101/5201 checks are retrospective after choosing this rule; 5701 is exploratory replay, and 5801 froze the rule before collecting its new seeds. All share one scene. False alarms and response dynamics matter; no safe fallback or time guarantee is established.",
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({key: result[key] for key in
                      ("total_nav_starts", "outcomes", "warning_by_outcome",
                       "warning_before_safe_approach_complete_by_outcome",
                       "safety_warning_to_terminal_s_range")}, indent=2))


if __name__ == "__main__":
    main()
