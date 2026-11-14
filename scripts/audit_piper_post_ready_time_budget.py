"""Audit a constant post-readiness time budget over frozen NAV-to-PUSH cohorts."""

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path

from audit_piper_pre_ready_support_warning import COHORTS, outcome, sha256


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--warning-evidence", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error("Output file exists")

    frozen = json.loads(args.warning_evidence.read_text(encoding="utf-8"))
    warning_script = Path(__file__).with_name("audit_piper_pre_ready_support_warning.py")
    if frozen["analysis_sha256"] != sha256(warning_script):
        raise ValueError("Warning audit source has changed")
    expected_cohorts = {cohort["name"]: cohort for cohort in frozen["cohorts"]}
    if set(expected_cohorts) != {name for name, _, _ in COHORTS}:
        raise ValueError("Unexpected cohort manifest")

    cohorts = []
    rows = []
    expected_sources = None
    for name, relative_path, first_seed in COHORTS:
        report_hashes = []
        cohort_rows = []
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
                    or report["step_dt"] != 0.02 or report["push_budget_s"] != 12.0
                    or report["pre_ready_leg_action_cap"] != 0.0
                    or report.get("handoff_settle_stable_s", 0.0) != 0.0
                    or len(report["support_trace"]) != report["push_executed_steps"]):
                raise ValueError(f"Cohort contract differs for seed {seed}")
            label = outcome(report)
            ready = report.get("motion_ready_s")
            terminal = report["push_elapsed_s"]
            if ready is not None and (label == "nav_timeout" or not 0 < ready <= terminal <= 12.0
                                      or not math.isclose(ready / 0.02, round(ready / 0.02), abs_tol=1e-7)):
                raise ValueError(f"Invalid readiness timestamp for seed {seed}")
            if label == "box_settled" and ready is None:
                raise ValueError(f"Missing readiness for settled seed {seed}")
            cohort_rows.append({
                "seed": seed,
                "outcome": label,
                "motion_ready_s": ready,
                "time_left_at_ready_s": 12.0 - ready if ready is not None else None,
                "ready_to_terminal_s": terminal - ready if ready is not None else None,
            })
        manifest = hashlib.sha256("".join(report_hashes).encode()).hexdigest()
        if manifest != expected_cohorts[name]["report_hash_manifest_sha256"]:
            raise ValueError(f"Report manifest changed for cohort {name}")
        rows.extend(cohort_rows)
        cohorts.append({"name": name, "report_hash_manifest_sha256": manifest,
                        "rows": cohort_rows})

    calibration = [row["ready_to_terminal_s"] for row in cohorts[2]["rows"]
                   if row["outcome"] == "box_settled"]
    if cohorts[2]["name"] != "5701-5724" or len(calibration) != 17:
        raise ValueError("Expected 5701 calibration successes")
    threshold = round(max(calibration), 2)
    if not math.isclose(max(calibration), threshold, abs_tol=1e-7):
        raise ValueError("Calibration duration does not match the 20 ms clock")

    for cohort in cohorts:
        selected = cohort.pop("rows")
        for row in selected:
            row["gate"] = ("not_evaluated" if row["motion_ready_s"] is None else
                           "allow" if row["time_left_at_ready_s"] + 1e-7 >= threshold else "abstain")
        cohort["outcomes"] = dict(sorted(Counter(row["outcome"] for row in selected).items()))
        cohort["ready_count"] = sum(row["motion_ready_s"] is not None for row in selected)
        cohort["gate_by_outcome"] = {
            label: dict(sorted(Counter(row["gate"] for row in selected if row["outcome"] == label).items()))
            for label in sorted({row["outcome"] for row in selected})
        }
    result = {
        "schema_version": 1,
        "scope": "Retrospective time-only classification, not an intervention or a completion guarantee",
        "analysis_sha256": sha256(Path(__file__)),
        "warning_evidence_sha256": sha256(args.warning_evidence),
        "total_nav_starts": len(rows),
        "rule": "At first motion_ready, allow if 12 s minus elapsed PUSH time is at least the largest 5701 settled post-ready duration",
        "calibration": {"cohort": "5701-5724", "settled_count": len(calibration),
                        "observed_ready_to_settled_s_range": [round(min(calibration), 2), threshold],
                        "required_remaining_s": threshold},
        "cohorts": cohorts,
        "gate_by_outcome": {
            label: dict(sorted(Counter(row["gate"] for row in rows if row["outcome"] == label).items()))
            for label in sorted({row["outcome"] for row in rows})
        },
        "abstained_after_ready": [row for row in rows if row["gate"] == "abstain"],
        "post_ready_failures_allowed": [row for row in rows if row["motion_ready_s"] is not None
                                        and row["outcome"] != "box_settled" and row["gate"] == "allow"],
        "interpretation": "The constant duration is calibrated only on observed successes in one same-scene cohort. It cannot prevent failures before readiness, may reject a later success, and cannot prove safety or deadline feasibility. No control action was applied.",
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({key: result[key] for key in
                      ("calibration", "gate_by_outcome", "abstained_after_ready",
                       "post_ready_failures_allowed")}, indent=2))


if __name__ == "__main__":
    main()
