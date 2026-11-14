"""Compare a source group's static path-bank screen with its paired dynamic diagnostic."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError(message)


def audit(bank_path: Path, stage_path: Path, contact_path: Path, exit_path: Path) -> dict:
    bank, stage, contact, status = (json.loads(p.read_text()) for p in
                                    (bank_path, stage_path, contact_path, exit_path))
    require(status["returncode"] == 0 and status["valid"] and
            contact["report_sha256"] == status["report_sha256"],
            "Dynamic diagnostic is incomplete or contact audit differs")
    static = bank["results"]
    dynamic = contact["results"]
    require(len(static) == len(dynamic) == stage["completed_episodes"] == 8
            and stage["incomplete_episodes"] == 0
            and sorted(row["env_id"] for row in static) == list(range(8))
            and sorted(row["env_id"] for row in dynamic) == list(range(8)),
            "Expected complete seen eight-environment cohort")
    require(all(row["sampled_static_screen_passed"] for row in static),
            "Path bank does not pass the source static screen")
    by_env = {row["env_id"]: row for row in dynamic}
    rows = []
    for entry in sorted(static, key=lambda r: r["env_id"]):
        env = entry["env_id"]
        outcome = by_env[env]
        legal = stage["first_legal_contact_s"][env] >= 0
        require(legal == (outcome["first_legal"] is not None), "Contact telemetry differs")
        require(bool(stage["stable_contact_stage_passed"][env]) is False,
                "Unexpected healthy sustained contact")
        rows.append({
            "env_id": env,
            "static_passed": entry["sampled_static_screen_passed"],
            "minimum_static_protected_m": entry["actual_path_geometry_minimum_m"][0],
            "minimum_static_box_m": entry["actual_path_geometry_minimum_m"][1],
            "first_legal_contact_s": stage["first_legal_contact_s"][env] if legal else None,
            "maximum_healthy_contact_s": stage["maximum_healthy_contact_s"][env],
            "stable_contact_passed": stage["stable_contact_stage_passed"][env],
            "termination": outcome["termination_flags"],
            "post_release_minimum_recorded_geometry_m": stage["post_release_minimum_recorded_geometry_m"][env],
            "post_release_maximum_torque_ratio": stage["post_release_maximum_torque_ratio"][env],
            "terminal_tip_distance_m": (outcome["contact_classifier"] or {}).get("tip_distance_m"),
            "terminal_near_tip": (outcome["contact_classifier"] or {}).get("near_tip"),
        })
    return {
        "scope": "Source v146/v147 used-seed static-to-dynamic diagnostic; not this group's frozen path pair or acceptance",
        "source_sha256": {
            "static_bank": digest(bank_path), "dynamic_stage": digest(stage_path),
            "contact_audit": digest(contact_path), "exit_status": digest(exit_path),
            "dynamic_report": status["report_sha256"],
        },
        "counts": {
            "static_passed": sum(row["static_passed"] for row in rows),
            "first_legal_contact": sum(row["first_legal_contact_s"] is not None for row in rows),
            "stable_contact": sum(row["stable_contact_passed"] for row in rows),
            "original_task_success": stage["original_task_success"],
            "invalid_hand_contact": sum("invalid_hand_contact" in row["termination"] for row in rows),
        },
        "per_env": rows,
        "limitations": "State-conditioned static feasibility is necessary only. The source controller, task, 140 s diagnostic window and physical configuration differ from this group's v112 pair; the two results are not pooled. No calibrated online gate or safety gain follows."
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("bank", "stage", "contact", "exit"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args.bank, args.stage, args.contact, args.exit),
                     indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
