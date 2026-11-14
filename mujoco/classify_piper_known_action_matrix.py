"""Classify frozen matched actions from an already audited response matrix."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from reconfigurable_navigation.reachability.bounded_handoff import (
    MatchedActionWitness,
    classify_matched_action_witness,
)


def classify(matrix_path: Path, manifest_path: Path) -> dict:
    matrix_bytes = matrix_path.read_bytes()
    manifest = json.loads(manifest_path.read_text())
    matrix = json.loads(matrix_bytes)
    matrix_sha256 = hashlib.sha256(matrix_bytes).hexdigest()
    if matrix_sha256 != manifest["output_sha256"]:
        raise ValueError("Matrix SHA-256 does not match the frozen result manifest")
    if matrix["schema_version"] != 1 or manifest["paired_rows"] != len(matrix["rows"]):
        raise ValueError("Unexpected matrix schema or row count")
    if any(matrix[key] != manifest[key] for key in (
            "protocol_sha256", "analysis_sha256", "old_manifest_sha256",
            "new_manifest_sha256")):
        raise ValueError("Matrix provenance differs from the frozen manifest")
    expected_steps = manifest["pre_action_equal_steps_by_seed"]
    expected_reasons = manifest["terminal_reasons_by_seed_and_mode"]
    if len(expected_reasons) != len(matrix["rows"]):
        raise ValueError("Frozen outcome inventory is incomplete")

    rows = []
    seen = set()
    for row in matrix["rows"]:
        identity = f"{row['seed']}-{row['mode']}"
        if identity in seen or identity not in expected_reasons:
            raise ValueError(f"Unexpected or duplicate action: {identity}")
        seen.add(identity)
        if (row["pre_action_equal_steps"] != expected_steps[str(row["seed"])]
                or row["pre_action_equal_steps"] <= 0
                or row["candidate_terminal_reason"] != expected_reasons[identity]):
            raise ValueError(f"Unmatched or changed action result: {identity}")
        witness = MatchedActionWitness(
            matching_audit_sha256=row["prior_audit_sha256"],
            candidate_report_sha256=row["candidate_sha256"],
            action_id=identity,
            pre_action_trace_equal=True,
            terminal_reason=row["candidate_terminal_reason"],
        )
        rows.append({"action_id": identity, "verdict": classify_matched_action_witness(witness),
                     "terminal_reason": row["candidate_terminal_reason"]})
    if seen != set(expected_reasons):
        raise ValueError("Missing frozen action results")
    return {"matrix_sha256": matrix_sha256, "scope": "inspected_state_action_only",
            "joint_bound_available": False, "contact_authorized": False, "rows": rows}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("matrix", type=Path)
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    print(json.dumps(classify(args.matrix, args.manifest), indent=2))
