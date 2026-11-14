"""Replay a frozen WBC precontact input with one isolated feedback change."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch

import check_piper_arm_precontact_motion as motion
from check_piper_startup import sha256


VARIANTS = {
    "no-integral": ("wbc_hand_feedback_integral_gain", 0.0),
    "half-proportional": ("wbc_hand_feedback_gain", 0.25),
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-json", type=Path, required=True)
    parser.add_argument("--variant", choices=tuple(VARIANTS), required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error("Require a new output path")
    source = json.loads(args.input_json.read_text())
    if not source.get("source_sha256"):
        parser.error("Input lacks recorded source hashes")
    for path, expected in source["source_sha256"].items():
        if sha256(Path(path)) != expected:
            raise ValueError(f"Frozen source or asset changed: {path}")
    baseline = source["arguments"]
    if (baseline["locomotion_policy"] != "wbc"
            or baseline["arm_controller"] != "unified-wbc"
            or not baseline["diagnose_designated_hand_approach"]
            or not baseline["require_motion_sweep_certificate"]
            or baseline["wbc_hand_feedback_gain"] != 0.5
            or baseline["wbc_hand_feedback_integral_gain"] != 0.2
            or baseline["wbc_hand_feedback_max_meters"] != 0.146
            or baseline["seed"] != source["result"]["seed"]):
        parser.error("Unexpected frozen WBC feedback contract")
    field, value = VARIANTS[args.variant]
    candidate = dict(baseline)
    candidate[field] = value
    candidate["output_json"] = str(args.output_json)
    differences = {key for key in baseline if candidate[key] != baseline[key]}
    if differences != {field, "output_json"}:
        raise ValueError(f"Unexpected contract changes: {differences}")
    torch.set_num_threads(1)
    result = motion.run_episode(argparse.Namespace(**candidate))
    report = {
        "schema_version": 1,
        "scope": "Isolated MuJoCo WBC feedback candidate; no PUSH, contact or deployment approval",
        "variant": args.variant,
        "changed_field": field,
        "baseline_value": baseline[field],
        "candidate_value": value,
        "input": str(args.input_json.resolve()),
        "input_sha256": sha256(args.input_json),
        "source_sha256": {
            **source["source_sha256"],
            str(Path(__file__).resolve()): sha256(Path(__file__)),
        },
        "arguments": candidate,
        "baseline_comparison": {
            "baseline_reason": source["result"]["reason"],
            "baseline_passed": source["result"]["passed"],
            "candidate_reason": result["reason"],
            "candidate_passed": result["passed"],
        },
        "result": result,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x") as destination:
        json.dump(report, destination, indent=2, allow_nan=False)
    print(json.dumps({"seed": result["seed"], "variant": args.variant,
                      "baseline_reason": source["result"]["reason"],
                      "candidate_reason": result["reason"],
                      "candidate_passed": result["passed"]}, indent=2))


if __name__ == "__main__":
    main()
