"""Audit observed PUSH goal times in pinned extended-run reports."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def audit_report(report: dict, deadline_s: float) -> dict:
    require(math.isfinite(deadline_s) and deadline_s > 0.0,
            "deadline_s must be finite and positive")
    requested = report["requested_episodes"]
    completed = report["completed_episodes"]
    incomplete = report["incomplete_episodes"]
    require(all(type(value) is int and value >= 0
                for value in (requested, completed, incomplete))
            and requested > 0 and completed + incomplete == requested,
            "Report denominator is incomplete or inconsistent")
    duration = report["episode_length_s"]
    require(isinstance(duration, (int, float)) and math.isfinite(duration)
            and duration > deadline_s,
            "Report episode length must exceed the audited deadline")
    names = report["termination_flag_names"]
    require(isinstance(names, list) and len(names) == len(set(names))
            and "box_settled" in names, "Missing or duplicate termination flags")
    terminals = report["terminal_states"]
    require(isinstance(terminals, list) and len(terminals) == completed,
            "Terminal-state count does not match completed episodes")
    seen = set()
    counts = {name: 0 for name in names}
    goal_times = []
    early_non_goal = 0
    for terminal in terminals:
        identity = (terminal["env_id"], terminal["episode"])
        require(identity not in seen, "Duplicate terminal episode identity")
        seen.add(identity)
        elapsed = terminal["elapsed_seconds"]
        require(isinstance(elapsed, (int, float)) and math.isfinite(elapsed)
                and 0.0 <= elapsed <= duration + 1e-4,
                "Terminal time is outside the reported episode")
        flags = terminal["termination_flags"]
        require(isinstance(flags, list) and len(flags) == len(names)
                and all(type(flag) is bool for flag in flags),
                "Malformed terminal flags")
        for name, flag in zip(names, flags):
            counts[name] += int(flag)
        if flags[names.index("box_settled")]:
            goal_times.append(elapsed)
        elif elapsed <= deadline_s:
            early_non_goal += 1
    require(counts == report["termination_reasons"],
            "Terminal flags disagree with termination counts")
    require(len(goal_times) == report["successful_episodes"],
            "Reported successes disagree with terminal goals")
    on_time = sum(time <= deadline_s for time in goal_times)
    return {
        "seed": report["seed"],
        "requested_episodes": requested,
        "completed_episodes": completed,
        "incomplete_episodes": incomplete,
        "report_episode_length_s": duration,
        "deadline_s": deadline_s,
        "observed_goal_by_deadline_in_extended_run": on_time,
        "observed_goal_after_deadline_in_extended_run": len(goal_times) - on_time,
        "observed_non_goal_terminal_by_deadline": early_non_goal,
        "unresolved_at_deadline_in_extended_run": requested - on_time - early_non_goal,
        "earliest_reported_goal_s": min(goal_times) if goal_times else None,
        "latest_reported_goal_s": max(goal_times) if goal_times else None,
        "original_deadline_acceptance": "not_evaluated",
        "contact_authorized": False,
    }


def audit_file(path: Path, expected_sha256: str, deadline_s: float) -> dict:
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    require(digest == expected_sha256, f"Report hash differs: {path}")
    result = audit_report(json.loads(raw), deadline_s)
    return {"report_path": str(path), "report_sha256": digest, **result}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", nargs=2, action="append", required=True,
                        metavar=("REPORT_JSON", "SHA256"))
    parser.add_argument("--deadline-s", type=float, required=True)
    args = parser.parse_args()
    result = {"scope": "Observed terminal timing in extended runs, not a deadline rerun",
              "cases": [audit_file(Path(path), digest, args.deadline_s)
                        for path, digest in args.case]}
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
