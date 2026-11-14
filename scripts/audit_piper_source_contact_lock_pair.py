"""Audit the source group's contact-lock isolation as a paired stage diagnostic."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(base_summary: Path, base_status: Path, lock_summary: Path,
          lock_status: Path) -> dict:
    base = json.loads(base_summary.read_text())
    before = json.loads(base_status.read_text())
    lock = json.loads(lock_summary.read_text())
    after = json.loads(lock_status.read_text())
    if not (before["returncode"] == after["returncode"] == 0
            and before["valid"] and after["valid"]
            and after["stable_contact_environment_count"] == 6
            and after["declared_contract_difference"] == {
                "controller_contract.lock_arm_on_contact": {"before": False, "after": True}
            }
            and base["completed_episodes"] == lock["completed_episodes"] == 8
            and base["incomplete_episodes"] == lock["incomplete_episodes"] == 0
            and base["first_legal_contact_s"] == lock["first_legal_contact_s"]):
        raise ValueError("Incomplete pair or unexpected contact-lock contract")
    rows = []
    for env in range(8):
        legal = base["first_legal_contact_s"][env] >= 0
        rows.append({
            "env_id": env, "first_legal_contact_s": (base["first_legal_contact_s"][env]
                                                     if legal else None),
            "baseline_healthy_contact_s": base["final_healthy_contact_s"][env],
            "locked_healthy_contact_s": lock["final_healthy_contact_s"][env],
            "baseline_stable_contact": base["stable_contact_stage_passed"][env],
            "locked_stable_contact": lock["stable_contact_stage_passed"][env],
            "baseline_minimum_recorded_geometry_m": base["post_release_minimum_recorded_geometry_m"][env],
            "locked_minimum_recorded_geometry_m": lock["post_release_minimum_recorded_geometry_m"][env],
            "baseline_maximum_torque_ratio": base["post_release_maximum_torque_ratio"][env],
            "locked_maximum_torque_ratio": lock["post_release_maximum_torque_ratio"][env],
        })
    if not (sum(r["baseline_stable_contact"] for r in rows) == 0
            and sum(r["locked_stable_contact"] for r in rows) == 6
            and base["original_task_success"] == lock["original_task_success"] == 0
            and base["safety_failures"] == lock["safety_failures"] == {"invalid_hand_contact": 2}):
        raise ValueError("Stage result differs from frozen pair")
    return {
        "scope": "Source v147/v148 used-seed contact-lock stage isolation; different controller contract, no full PUSH success or this-group acceptance",
        "source_sha256": {"baseline_stage": digest(base_summary), "baseline_exit": digest(base_status),
                          "locked_stage": digest(lock_summary), "locked_revalidated_status": digest(lock_status),
                          "baseline_report": before["report_sha256"],
                          "locked_report": after["report_sha256"]},
        "declared_contract_difference": after["declared_contract_difference"],
        "counts": {"baseline_first_legal_contact": sum(r["first_legal_contact_s"] is not None for r in rows),
                   "locked_first_legal_contact": sum(r["first_legal_contact_s"] is not None for r in rows),
                   "baseline_stable_contact": 0, "locked_stable_contact": 6,
                   "baseline_task_success": 0, "locked_task_success": 0,
                   "invalid_hand_contact_each": 2},
        "per_env": rows,
        "limitations": "Locking after actual legal contact isolates sustained pressing load in a source-group stage diagnostic. It holds the arm and does not demonstrate box pushing or NAV handoff. The 120/140 s windows and source controller differ from our v112 pair."
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("base-summary", "base-status", "lock-summary", "lock-status"):
        parser.add_argument("--" + name, type=Path, required=True)
    a = parser.parse_args()
    print(json.dumps(audit(a.base_summary, a.base_status, a.lock_summary,
                           a.lock_status), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
