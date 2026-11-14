"""Evaluate a necessary state-conditioned geometric margin from a frozen audit."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


# These are the v146 planning reserves, not general GO2-PIPER acceptance limits.
GEOMETRY_RESERVE_M = (0.06, 0.01, 0.10)  # protected, box, body center
ENTRY_TOLERANCE_M = (0.05, 0.08, 0.045)  # x, y, z


def audit(path: Path) -> dict:
    source = json.loads(path.read_text())
    rows = source["results"]
    if len(rows) != 8 or sorted(row["env_id"] for row in rows) != list(range(8)):
        raise ValueError("Expected eight distinct actual preparation states")
    results = []
    for row in sorted(rows, key=lambda r: r["env_id"]):
        geometry = row["actual_path_geometry_minimum_m"]
        entry = row["entry_position_error_m"]
        if len(geometry) != 3 or len(entry) != 3 or not row["path_available"]:
            raise ValueError("Missing path geometry or entry measurements")
        reserves = [observed - limit for observed, limit in zip(geometry, GEOMETRY_RESERVE_M)]
        entry_reserves = [limit - abs(error) for error, limit in zip(entry, ENTRY_TOLERANCE_M)]
        margin = min(*reserves, *entry_reserves)
        results.append({
            "env_id": row["env_id"],
            "geometry_reserves_m": reserves,
            "entry_reserves_m": entry_reserves,
            "minimum_necessary_margin_m": margin,
            "necessary_geometry_and_entry_pass": margin >= 0,
            "source_full_static_screen_passed": row["sampled_static_screen_passed"],
        })
    return {
        "scope": "Source v146 seen actual states; necessary static geometry and entry screen only, no dynamic or task claim",
        "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "geometry_reserve_m": GEOMETRY_RESERVE_M,
        "entry_tolerance_m": ENTRY_TOLERANCE_M,
        "results": results,
        "joint_margin_m": min(row["minimum_necessary_margin_m"] for row in results),
        "passing_env_ids": [row["env_id"] for row in results if row["necessary_geometry_and_entry_pass"]],
        "source_static_passing_env_ids": [row["env_id"] for row in results if row["source_full_static_screen_passed"]],
        "limitations": "The numeric reserves belong to the source group's v146 design. Passing this necessary screen does not establish support, torque, collisions, controller tracking, contact, or task success."
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-audit", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args.source_audit), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
