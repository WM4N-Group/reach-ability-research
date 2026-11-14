"""Replay a frozen WBC precontact input with a ten-second observation hold."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch

import check_piper_arm_precontact_motion as motion
from check_piper_startup import sha256


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-json", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error("Require a new output path")
    source = json.loads(args.input_json.read_text())
    if not source.get("source_sha256"):
        parser.error("Input lacks source hashes")
    for path, expected in source["source_sha256"].items():
        if sha256(Path(path)) != expected:
            raise ValueError(f"Frozen source or asset changed: {path}")
    baseline = source["arguments"]
    if (baseline["locomotion_policy"] != "wbc"
            or baseline["arm_controller"] != "unified-wbc"
            or not baseline["require_motion_sweep_certificate"]
            or not baseline["diagnose_designated_hand_approach"]
            or baseline["hold_seconds"] != 5.0
            or baseline["seed"] != source["result"]["seed"]):
        parser.error("Unexpected frozen precontact contract")
    candidate = dict(baseline)
    candidate["hold_seconds"] = 10.0
    candidate["output_json"] = str(args.output_json)
    if {key for key in baseline if candidate[key] != baseline[key]} != {"hold_seconds", "output_json"}:
        raise ValueError("Unexpected contract changes")
    torch.set_num_threads(1)
    result = motion.run_episode(argparse.Namespace(**candidate))
    baseline_trace = source["result"]["motion"]["trace"]
    candidate_trace = result["motion"]["trace"]
    report = {
        "schema_version": 1,
        "scope": "Extended MuJoCo precontact observation; no controller, safety or contact approval",
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
            "baseline_elapsed_sim_time": source["result"]["elapsed_sim_time"],
            "candidate_elapsed_sim_time": result["elapsed_sim_time"],
            "baseline_control_trace_is_prefix": (
                candidate_trace[:len(baseline_trace)] == baseline_trace
            ),
            "baseline_control_trace_samples": len(baseline_trace),
            "candidate_control_trace_samples": len(candidate_trace),
        },
        "result": result,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x") as destination:
        json.dump(report, destination, indent=2, allow_nan=False)
    print(json.dumps({"seed": result["seed"],
                      "baseline_reason": source["result"]["reason"],
                      "candidate_reason": result["reason"],
                      "prefix_match": report["baseline_comparison"][
                          "baseline_control_trace_is_prefix"],
                      "hold_entries": result["motion"]["wbc_hold_entries"]}, indent=2))


if __name__ == "__main__":
    main()
