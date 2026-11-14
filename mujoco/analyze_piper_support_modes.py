"""Diagnose whether a calibrated switched-foot support atlas transfers across traces."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path

import numpy as np

from check_piper_startup import sha256
from reconfigurable_navigation.reachability import (
    QuasiStaticSupportResult,
    certify_fixed_contact_support_region,
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


def _hold_records(report):
    if report["schema_version"] != 1:
        raise ValueError("Expected per-step support trace schema version 1")
    for episode in report["results"]:
        if not episode["nav_and_hold_completed"]:
            raise ValueError(f"Incomplete NAV/hold episode: seed {episode['seed']}")
        for record in episode["trace"]:
            if record["phase"] == "hold":
                yield episode["seed"], record


def _atlas(calibration, required_margin):
    modes = {}
    for seed, record in _hold_records(calibration):
        mode = tuple(record["supporting_feet"])
        if len(mode) < 3:
            continue
        support = _support(record, required_margin)
        pose = np.asarray(record["base_pose_xy_yaw"])
        if mode not in modes:
            modes[mode] = {
                "reference": support,
                "reference_pose": pose,
                "foot_radius": 0.0,
                "com_radius": 0.0,
                "calibration_samples": 0,
                "seed": seed,
            }
        entry = modes[mode]
        residual = measure_fixed_contact_support_residual(
            entry["reference"], entry["reference_pose"], support, pose
        )
        entry["foot_radius"] = max(
            entry["foot_radius"], residual.maximum_contact_point_residual
        )
        entry["com_radius"] = max(entry["com_radius"], residual.center_of_mass_residual)
        entry["calibration_samples"] += 1
    return modes


def _validate(report, atlas, required_margin):
    per_seed = {}
    for seed, record in _hold_records(report):
        result = per_seed.setdefault(seed, {"steps": 0, "reasons": Counter(), "modes": Counter()})
        result["steps"] += 1
        mode = tuple(record["supporting_feet"])
        result["modes"][",".join(mode)] += 1
        if len(mode) < 3:
            reason = "fewer_than_three_feet"
        elif mode not in atlas:
            reason = "uncalibrated_mode"
        else:
            entry = atlas[mode]
            support = _support(record, required_margin)
            residual = measure_fixed_contact_support_residual(
                entry["reference"], entry["reference_pose"], support,
                np.asarray(record["base_pose_xy_yaw"]),
            )
            region = certify_fixed_contact_support_region(
                entry["reference"],
                contact_point_error_radius=entry["foot_radius"],
                center_of_mass_error_radius=entry["com_radius"],
            )
            if (residual.maximum_contact_point_residual > entry["foot_radius"] + 1e-12
                    or residual.center_of_mass_residual > entry["com_radius"] + 1e-12):
                reason = "outside_calibration_residual"
            elif not region.conditional_support_safe:
                reason = "mode_margin_bound_below_requirement"
            elif not support.safe:
                reason = "observed_margin_below_requirement"
            elif support.support_margin + 1e-9 < region.margin_lower_bound:
                reason = "observed_margin_below_bound"
            else:
                reason = "passed_sampled_quasistatic_bound"
        result["reasons"][reason] += 1
    return [{"seed": seed, "steps": result["steps"],
             "reasons": dict(result["reasons"]), "modes": dict(result["modes"])}
            for seed, result in sorted(per_seed.items())]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--calibration-json", type=Path, required=True)
    parser.add_argument("--validation-json", type=Path, required=True)
    parser.add_argument("--required-margin", type=float, default=0.02)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if (not np.isfinite(args.required_margin) or args.required_margin < 0
            or args.output_json.exists()):
        parser.error("Require nonnegative finite margin and a new output path")
    with args.calibration_json.open() as source:
        calibration = json.load(source)
    with args.validation_json.open() as source:
        validation = json.load(source)
    atlas = _atlas(calibration, args.required_margin)
    if not atlas:
        parser.error("Calibration has no support mode with at least three feet")
    results = _validate(validation, atlas, args.required_margin)
    modes = {}
    for mode, entry in atlas.items():
        region = certify_fixed_contact_support_region(
            entry["reference"],
            contact_point_error_radius=entry["foot_radius"],
            center_of_mass_error_radius=entry["com_radius"],
        )
        modes[",".join(mode)] = {
            "reference_seed": entry["seed"],
            "calibration_samples": entry["calibration_samples"],
            "reference_margin": entry["reference"].support_margin,
            "foot_radius": entry["foot_radius"],
            "com_radius": entry["com_radius"],
            "margin_lower_bound": region.margin_lower_bound,
            "conditional_support_safe": region.conditional_support_safe,
        }
    report = {
        "schema_version": 1,
        "scope": "retrospective sampled quasi-static mode atlas; no between-step or dynamic stability proof",
        "required_margin": args.required_margin,
        "calibration_trace_sha256": sha256(args.calibration_json),
        "validation_trace_sha256": sha256(args.validation_json),
        "analyzer_sha256": sha256(Path(__file__)),
        "support_source_sha256": sha256(
            Path(__file__).parent / "reconfigurable_navigation/reachability/support.py"
        ),
        "modes": modes,
        "results": results,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x") as destination:
        json.dump(report, destination, indent=2, allow_nan=False)
    print(json.dumps({"modes": modes, "results": results}, indent=2))


if __name__ == "__main__":
    main()
