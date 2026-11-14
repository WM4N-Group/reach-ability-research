"""Replay a frozen precontact run with one preregistered local target offset."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch

import check_piper_arm_precontact_motion as motion
from check_piper_startup import sha256


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol-json", type=Path, required=True)
    parser.add_argument("--baseline-json", type=Path, required=True)
    parser.add_argument("--offset", required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error("Require a new output path")
    protocol = json.loads(args.protocol_json.read_text())
    if sha256(Path(__file__)) != protocol["candidate_entrypoint_sha256"]:
        raise ValueError("Candidate entrypoint changed after preregistration")
    baseline = json.loads(args.baseline_json.read_text())
    seed = baseline["result"]["seed"]
    batch = next((batch for batch in protocol["batches"] if seed in batch["seeds"]), None)
    if batch is None or args.offset not in protocol["offsets_m"]:
        parser.error("Seed or offset is absent from the fixed protocol")
    if sha256(Path(batch["contract_json"])) != batch["contract_sha256"]:
        raise ValueError("Contract hash changed")
    if baseline["contract_source_sha256"] != batch["contract_sha256"]:
        raise ValueError("Baseline was made under a different contract")
    for path, expected in baseline["source_sha256"].items():
        if sha256(Path(path)) != expected:
            raise ValueError(f"Frozen source or asset changed: {path}")
    original = baseline["arguments"]
    if (original["locomotion_policy"] != "wbc"
            or original["arm_controller"] != "unified-wbc"
            or original["hold_seconds"] != protocol["hold_seconds"]
            or not original["require_motion_sweep_certificate"]
            or not original["diagnose_designated_hand_approach"]
            or seed != original["seed"]):
        parser.error("Unexpected frozen precontact contract")
    candidate = dict(original)
    delta = protocol["offsets_m"][args.offset]
    candidate["hand_target_local"] = [
        value + shift for value, shift in zip(original["hand_target_local"], delta)
    ]
    candidate["output_json"] = str(args.output_json)
    if {key for key in original if candidate[key] != original[key]} != {
        "hand_target_local", "output_json"
    }:
        raise ValueError("Unexpected contract changes")
    torch.set_num_threads(1)
    result = motion.run_episode(argparse.Namespace(**candidate))
    report = {
        "schema_version": 1,
        "scope": "Whole-run MuJoCo target perturbation; no invariant-set or contact claim",
        "protocol_sha256": sha256(args.protocol_json),
        "baseline": str(args.baseline_json.resolve()),
        "baseline_sha256": sha256(args.baseline_json),
        "source_sha256": {
            **baseline["source_sha256"],
            str(Path(__file__).resolve()): sha256(Path(__file__)),
        },
        "offset": args.offset,
        "offset_local_m": delta,
        "arguments": candidate,
        "baseline_comparison": {
            "baseline_reason": baseline["result"]["reason"],
            "baseline_passed": baseline["result"]["passed"],
            "navigation_trace_matches": (
                result["nav"]["trace"] == baseline["result"]["nav"]["trace"]
            ),
            "precontact_state_matches": (
                result["candidate"]["precontact_state"]
                == baseline["result"]["candidate"]["precontact_state"]
            ),
        },
        "result": result,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x") as destination:
        json.dump(report, destination, indent=2, allow_nan=False)
        destination.write("\n")
    print(json.dumps({"seed": seed, "offset": args.offset,
                      "reason": result["reason"], "passed": result["passed"],
                      "matched_precontact_state": report["baseline_comparison"][
                          "precontact_state_matches"]}))


if __name__ == "__main__":
    main()
