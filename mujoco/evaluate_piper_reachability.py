"""Evaluate fixed PIPER reachability labels across joint-limit thresholds."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path

from check_piper_startup import sha256


REQUIRED_RECORD_FIELDS = frozenset(
    {
        "kinematic_feasible",
        "joint_limit_margin",
        "self_clearance_checked",
        "self_clearance_safe",
        "environment_clearance_checked",
        "environment_clearance_safe",
        "scene_case",
        "nominal_base_pose",
        "target_position",
        "base_pose_offset",
    }
)
SUPPORT_RECORD_FIELDS = frozenset(
    {"support_checked", "support_margin", "required_support_margin", "support_safe"}
)


def _load_records(
    path: Path,
    split: str,
    *,
    require_quasistatic_support: bool,
) -> tuple[str, list[dict[str, object]]]:
    report = json.loads(path.read_text())
    if report.get("split") != split:
        raise ValueError(f"{path} does not belong to split {split}")
    scene_case = report.get("scene_case")
    if not isinstance(scene_case, str) or not scene_case:
        raise ValueError(f"{path} is missing scene_case")
    records = report.get("records")
    if not isinstance(records, list):
        raise ValueError(f"{path} is missing records")
    for index, record in enumerate(records):
        required_fields = REQUIRED_RECORD_FIELDS
        if require_quasistatic_support:
            required_fields = required_fields.union(SUPPORT_RECORD_FIELDS)
        missing = required_fields.difference(record)
        if missing:
            raise ValueError(f"{path} record {index} is missing {sorted(missing)}")
    return scene_case, records


def _metrics(
    records: list[dict[str, object]],
    threshold: float,
    *,
    require_quasistatic_support: bool,
) -> dict[str, int | float | bool]:
    total = len(records)
    kinematic = [record for record in records if record["kinematic_feasible"] is True]
    self_clearance = [
        record for record in kinematic if record["self_clearance_safe"] is True
    ]
    support_checked = [
        record
        for record in self_clearance
        if record.get("support_checked") is True
    ]
    support_safe = [
        record for record in support_checked if record.get("support_safe") is True
    ]
    support_eligible = support_safe if require_quasistatic_support else self_clearance
    joint_margin = [
        record
        for record in support_eligible
        if float(record["joint_limit_margin"]) >= threshold
    ]
    environment_checked = [
        record
        for record in joint_margin
        if record["environment_clearance_checked"] is True
    ]
    environment_safe = [
        record for record in environment_checked if record["environment_clearance_safe"] is True
    ]
    return {
        "joint_limit_margin_threshold": threshold,
        "total": total,
        "kinematic_feasible": len(kinematic),
        "self_clearance_safe": len(self_clearance),
        "quasistatic_support_required": require_quasistatic_support,
        "quasistatic_support_checked": len(support_checked),
        "quasistatic_support_safe": len(support_safe),
        "joint_margin_and_self_clearance_safe": len(joint_margin),
        "environment_clearance_checked": len(environment_checked),
        "joint_margin_self_and_environment_safe": len(environment_safe),
        "environment_unchecked_after_joint_screen": len(joint_margin) - len(environment_checked),
    }


def _query_key(record: dict[str, object]) -> tuple[str, tuple[float, ...], tuple[float, ...]]:
    return (
        str(record["scene_case"]),
        tuple(float(value) for value in record["nominal_base_pose"]),
        tuple(float(value) for value in record["target_position"]),
    )


def _offset(record: dict[str, object]) -> tuple[float, ...]:
    return tuple(float(value) for value in record["base_pose_offset"])


def _all_checked_geometric_constraints_pass(
    record: dict[str, object], threshold: float, *, require_quasistatic_support: bool
) -> bool:
    passed = bool(
        record["kinematic_feasible"] is True
        and float(record["joint_limit_margin"]) >= threshold
        and record["self_clearance_checked"] is True
        and record["self_clearance_safe"] is True
        and record["environment_clearance_checked"] is True
        and record["environment_clearance_safe"] is True
    )
    if require_quasistatic_support:
        passed &= bool(
            record["support_checked"] is True and record["support_safe"] is True
        )
    return passed


def _robust_metrics(
    records: list[dict[str, object]], threshold: float, *, require_quasistatic_support: bool = False
) -> dict[str, object]:
    grouped: dict[
        tuple[str, tuple[float, ...], tuple[float, ...]], list[dict[str, object]]
    ] = {}
    for record in records:
        grouped.setdefault(_query_key(record), []).append(record)
    if not grouped:
        raise ValueError("Cannot construct robust certificates from no records")

    first_key = next(iter(grouped))
    expected_offsets = tuple(sorted(_offset(record) for record in grouped[first_key]))
    if len(set(expected_offsets)) != len(expected_offsets):
        raise ValueError("Base-pose offset grid contains duplicate offsets")

    certificates = []
    for key, scenarios in sorted(grouped.items()):
        offsets = tuple(sorted(_offset(record) for record in scenarios))
        if len(set(offsets)) != len(offsets):
            raise ValueError(f"Duplicate base-pose offset for robust query {key}")
        if offsets != expected_offsets:
            raise ValueError(
                "All robust queries must use the same complete base-pose offset grid"
            )
        safe_scenarios = sum(
            _all_checked_geometric_constraints_pass(
                record,
                threshold,
                require_quasistatic_support=require_quasistatic_support,
            )
            for record in scenarios
        )
        certificates.append(
            {
                "scene_case": key[0],
                "nominal_base_pose": list(key[1]),
                "target_position": list(key[2]),
                "perturbation_count": len(scenarios),
                "safe_perturbations": safe_scenarios,
                "robust_geometric_certified": safe_scenarios == len(scenarios),
                "minimum_joint_limit_margin": min(
                    float(record["joint_limit_margin"]) for record in scenarios
                ),
                "minimum_self_clearance": min(
                    float(record["minimum_self_clearance"])
                    for record in scenarios
                    if record["minimum_self_clearance"] is not None
                ),
                "minimum_environment_clearance": min(
                    float(record["minimum_environment_clearance"])
                    for record in scenarios
                    if record["minimum_environment_clearance"] is not None
                ),
            }
        )
    robust_certified = sum(
        certificate["robust_geometric_certified"] for certificate in certificates
    )
    return {
        "joint_limit_margin_threshold": threshold,
        "quasistatic_support_required": require_quasistatic_support,
        "base_pose_offset_grid": [list(offset) for offset in expected_offsets],
        "robust_query_total": len(certificates),
        "robust_geometric_certified": robust_certified,
        "robust_geometric_rejected": len(certificates) - robust_certified,
        "certificates": certificates,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-json", type=Path, nargs="+", required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--split", choices=("calibration", "test"), required=True)
    parser.add_argument("--require-quasistatic-support", action="store_true")
    parser.add_argument(
        "--joint-limit-margins",
        type=float,
        nargs="+",
        default=(0.0, 0.01, 0.03, 0.05, 0.10),
    )
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error(f"Refusing to overwrite {args.output_json}")
    if any(threshold < 0.0 for threshold in args.joint_limit_margins):
        parser.error("joint-limit-margins must be non-negative")
    if len(set(args.input_json)) != len(args.input_json):
        parser.error("input-json paths must be unique")

    reports = [
        _load_records(
            path,
            args.split,
            require_quasistatic_support=args.require_quasistatic_support,
        )
        for path in args.input_json
    ]
    scene_cases = [scene_case for scene_case, _records in reports]
    if len(set(scene_cases)) != len(scene_cases):
        parser.error("input reports must have unique scene_case values")
    records = [record for _scene_case, report_records in reports for record in report_records]
    report = {
        "schema_version": 1,
        "scope": (
            "offline geometric coverage and finite base-pose-grid robust certificates"
            + (" with quasi-static support" if args.require_quasistatic_support else "")
            + "; "
            "no handoff, dynamic support, continuous perturbation, threshold calibration, "
            "or deployment approval"
        ),
        "split": args.split,
        "input_reports": [
            {
                "path": str(path),
                "sha256": sha256(path),
                "scene_case": scene_case,
                "records": len(report_records),
            }
            for path, (scene_case, report_records) in zip(args.input_json, reports)
        ],
        "failure_reasons": dict(
            Counter(
                record.get("failure_reason")
                for record in records
                if record["kinematic_feasible"] is not True
            )
        ),
        "threshold_metrics": [
            _metrics(
                records,
                threshold,
                require_quasistatic_support=args.require_quasistatic_support,
            )
            for threshold in sorted(set(args.joint_limit_margins))
        ],
        "finite_grid_robust_metrics": [
            _robust_metrics(
                records,
                threshold,
                require_quasistatic_support=args.require_quasistatic_support,
            )
            for threshold in sorted(set(args.joint_limit_margins))
        ],
        "evaluator_sha256": sha256(Path(__file__)),
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x") as destination:
        json.dump(report, destination, indent=2, allow_nan=False)
        destination.write("\n")
    print(json.dumps({"threshold_metrics": report["threshold_metrics"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())