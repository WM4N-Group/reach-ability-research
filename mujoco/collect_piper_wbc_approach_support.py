"""Observe WBC approach support geometry without editing the control probe."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys
from types import MethodType

import mujoco
import numpy as np

import probe_piper_precontact_handoff_response as probe
from check_piper_startup import sha256
from collect_piper_post_nav_support import _refresh_data, _sample
from reconfigurable_navigation.reachability import (
    PiperQuasiStaticSupportChecker,
    certify_relative_contact_support_region,
    measure_fixed_contact_support_residual,
)


def _summarize_approach(records, samples):
    if not samples:
        return {"steps": 0}
    reference, reference_pose = samples[0]
    residuals = [
        measure_fixed_contact_support_residual(reference, reference_pose, support, pose)
        for support, pose in samples
    ]
    retained = [item for item in residuals if item.contact_set_preserved]
    relative_radius = max(
        (item.maximum_relative_contact_point_residual for item in retained), default=None
    )
    relative_region = (
        certify_relative_contact_support_region(
            reference, relative_contact_point_error_radius=relative_radius
        ) if relative_radius is not None else None
    )
    return {
        "steps": len(samples),
        "reference_feet": list(reference.supporting_feet),
        "reference_margin": reference.support_margin,
        "contact_set_preserved_steps": len(retained),
        "contact_set_counts": dict(Counter(
            ",".join(support.supporting_feet) for support, _ in samples
        )),
        "steps_without_three_feet": sum(
            len(support.supporting_feet) < 3 for support, _ in samples
        ),
        "maximum_contact_point_residual": max(
            (item.maximum_contact_point_residual for item in retained), default=None
        ),
        "maximum_center_of_mass_residual": max(
            (item.center_of_mass_residual for item in retained), default=None
        ),
        "maximum_relative_contact_point_residual": relative_radius,
        "empirical_relative_margin_lower_bound": (
            relative_region.margin_lower_bound if relative_region is not None else None
        ),
        "empirical_relative_bound_meets_margin": (
            relative_region.conditional_support_safe if relative_region is not None else False
        ),
        "minimum_observed_margin": min(
            (support.support_margin for support, _ in samples
             if support.support_margin is not None), default=None
        ),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-json", type=Path, required=True)
    parser.add_argument("--probe-output-json", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--physics-substeps", type=int, choices=(1, 2, 4), default=1)
    parser.add_argument("--target-local", type=float, nargs=3, default=(-0.09, 0.0, 0.02))
    parser.add_argument("--preparation-steps", type=int, default=100)
    parser.add_argument("--ramp-steps", type=int, default=120)
    parser.add_argument("--hold-steps", type=int, default=40)
    parser.add_argument("--position-feedback-gain", type=float, default=0.5)
    parser.add_argument("--position-feedback-max-meters", type=float, default=0.04)
    args = parser.parse_args()
    if (args.input_json in (args.probe_output_json, args.output_json)
            or args.probe_output_json == args.output_json
            or args.probe_output_json.exists() or args.output_json.exists()
            or not np.isfinite([*args.target_local, args.position_feedback_gain,
                                args.position_feedback_max_meters]).all()
            or min(args.preparation_steps, args.hold_steps) < 0 or args.ramp_steps < 1):
        parser.error("Invalid parameters or output path already exists")
    records = []
    samples = []
    original_factory = probe.make_movable_box_navigation_runtime

    def observed_factory(**kwargs):
        runtime = original_factory(**kwargs)
        fresh_data = mujoco.MjData(runtime.model)
        checker = PiperQuasiStaticSupportChecker(runtime, data=fresh_data)
        original_simulate = runtime._simulate_target

        def observed_simulate(self, target):
            callback = self.on_physics_step

            def observed_step():
                try:
                    callback()
                finally:
                    _refresh_data(self, fresh_data)
                    record, support, pose = _sample(
                        self, fresh_data, checker, "unassigned", 0.02
                    )
                    records.append(record)
                    samples.append((support, pose))

            if callback is None:
                return original_simulate(target)
            self.on_physics_step = observed_step
            try:
                return original_simulate(target)
            finally:
                self.on_physics_step = callback

        runtime._simulate_target = MethodType(observed_simulate, runtime)
        return runtime

    probe.make_movable_box_navigation_runtime = observed_factory
    previous_argv = sys.argv
    sys.argv = [str(probe.SCRIPT),
                "--input-json", str(args.input_json),
                "--output-json", str(args.probe_output_json),
                "--physics-substeps", str(args.physics_substeps),
                "--target-local", *(str(value) for value in args.target_local),
                "--preparation-steps", str(args.preparation_steps),
                "--ramp-steps", str(args.ramp_steps),
                "--hold-steps", str(args.hold_steps),
                "--position-feedback-gain", str(args.position_feedback_gain),
                "--position-feedback-max-meters", str(args.position_feedback_max_meters),
                "--provenance-source", "reachability WBC support trace",
                "--provenance-purpose", "no-contact support residual diagnosis",
                "--calibration-status", "diagnostic_only"]
    try:
        probe.main()
    finally:
        sys.argv = previous_argv
        probe.make_movable_box_navigation_runtime = original_factory
    with args.probe_output_json.open() as source:
        probe_report = json.load(source)
    original_trace = probe_report["support_trace"]
    if len(original_trace) != len(records):
        raise RuntimeError("Observed trace length differs from control probe trace")
    for record, original in zip(records, original_trace):
        if abs(record["time"] - original["time"]) > 1e-9:
            raise RuntimeError("Observed trace time differs from control probe trace")
        record["phase"] = original["phase"]
    approach_records = [record for record in records if record["phase"] == "approach"]
    approach_samples = [sample for record, sample in zip(records, samples)
                        if record["phase"] == "approach"]
    report = {
        "schema_version": 1,
        "scope": "read-only WBC no-contact support trace; no PUSH or hardware acceptance",
        "arguments": {key: str(value) if isinstance(value, Path) else value
                      for key, value in vars(args).items()},
        "input_sha256": sha256(args.input_json),
        "probe_report_sha256": sha256(args.probe_output_json),
        "probe_source_sha256": sha256(probe.SCRIPT),
        "collector_sha256": sha256(Path(__file__)),
        "support_source_sha256": sha256(
            Path(__file__).parent / "reconfigurable_navigation/reachability/support.py"
        ),
        "sampling": "every probe physics callback; independent MjData and mj_forward",
        "probe_completed_requested_steps": probe_report["completed_requested_steps"],
        "probe_stop_reason": probe_report["stop_reason"],
        "approach_summary": _summarize_approach(approach_records, approach_samples),
        "trace": records,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x") as destination:
        json.dump(report, destination, indent=2, allow_nan=False)
    print(json.dumps({"output": str(args.output_json),
                      "probe_completed_requested_steps": report["probe_completed_requested_steps"],
                      "probe_stop_reason": report["probe_stop_reason"],
                      "approach_summary": report["approach_summary"]}, indent=2))
    return 0 if report["probe_completed_requested_steps"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
