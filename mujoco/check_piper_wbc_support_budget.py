"""Check a frozen foot-to-COM error budget against independent WBC traces."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from check_piper_startup import sha256
from reconfigurable_navigation.reachability import (
    QuasiStaticSupportResult,
    certify_relative_contact_support_region,
    measure_fixed_contact_support_residual,
)


def _support(record, required_margin):
    return QuasiStaticSupportResult(
        supporting_feet=tuple(record["supporting_feet"]),
        support_points=np.asarray(record["support_points_xy"]),
        center_of_mass_xy=np.asarray(record["center_of_mass_xy"]),
        support_margin=record["support_margin"],
        required_margin=required_margin,
    )


def _check_trace(path, radius, required_margin, support_source_hash):
    with path.open() as source:
        report = json.load(source)
    if report["support_source_sha256"] != support_source_hash:
        raise ValueError(f"Support source hash mismatch: {path}")
    steps = [record for record in report["trace"] if record["phase"] == "approach"]
    if not steps:
        raise ValueError(f"Missing WBC approach samples: {path}")
    reference = _support(steps[0], required_margin)
    reference_pose = np.asarray(steps[0]["base_pose_xy_yaw"])
    region = certify_relative_contact_support_region(
        reference, relative_contact_point_error_radius=radius
    )
    failed = []
    maximum_residual = 0.0
    minimum_margin = float("inf")
    for index, record in enumerate(steps):
        support = _support(record, required_margin)
        residual = measure_fixed_contact_support_residual(
            reference, reference_pose, support,
            np.asarray(record["base_pose_xy_yaw"]),
        )
        if not residual.contact_set_preserved:
            failed.append({"step": index, "reason": "contact_set_changed"})
            continue
        maximum_residual = max(
            maximum_residual, residual.maximum_relative_contact_point_residual
        )
        if support.support_margin is not None:
            minimum_margin = min(minimum_margin, support.support_margin)
        if residual.maximum_relative_contact_point_residual > radius + 1e-12:
            failed.append({"step": index, "reason": "relative_error_budget_exceeded"})
        elif not support.safe:
            failed.append({"step": index, "reason": "observed_margin_below_requirement"})
        elif (region.margin_lower_bound is not None
              and support.support_margin + 1e-9 < region.margin_lower_bound):
            failed.append({"step": index, "reason": "observed_margin_below_bound"})
    return {
        "trace": str(path),
        "trace_sha256": sha256(path),
        "probe_completed_requested_steps": report["probe_completed_requested_steps"],
        "probe_stop_reason": report["probe_stop_reason"],
        "approach_steps": len(steps),
        "reference_feet": list(reference.supporting_feet),
        "reference_margin": reference.support_margin,
        "margin_lower_bound": region.margin_lower_bound,
        "maximum_observed_relative_residual": maximum_residual,
        "minimum_observed_margin": minimum_margin if np.isfinite(minimum_margin) else None,
        "failed_steps": len(failed),
        "first_failure": failed[0] if failed else None,
        "passed": bool(report["probe_completed_requested_steps"]
                       and report["probe_stop_reason"] is None
                       and region.conditional_support_safe and not failed),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trace-json", type=Path, nargs="+", required=True)
    parser.add_argument("--relative-error-budget", type=float, required=True)
    parser.add_argument("--required-margin", type=float, default=0.02)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if (args.output_json.exists() or len(set(args.trace_json)) != len(args.trace_json)
            or not np.isfinite([args.relative_error_budget, args.required_margin]).all()
            or min(args.relative_error_budget, args.required_margin) < 0):
        parser.error("Require distinct traces, finite nonnegative budgets and a new output path")
    support_path = Path(__file__).parent / "reconfigurable_navigation/reachability/support.py"
    support_hash = sha256(support_path)
    results = [
        _check_trace(path, args.relative_error_budget, args.required_margin, support_hash)
        for path in args.trace_json
    ]
    report = {
        "schema_version": 1,
        "scope": "sampled conditional quasi-static bound; no between-step, dynamic or contact proof",
        "relative_error_budget": args.relative_error_budget,
        "required_margin": args.required_margin,
        "checker_sha256": sha256(Path(__file__)),
        "support_source_sha256": support_hash,
        "results": results,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x") as destination:
        json.dump(report, destination, indent=2, allow_nan=False)
    print(json.dumps(results, indent=2))
    return 0 if all(item["passed"] for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
