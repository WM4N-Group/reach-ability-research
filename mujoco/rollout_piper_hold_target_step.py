"""Run matched WBC hold-state probes and preregistered target steps."""

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
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--phase", required=True)
    parser.add_argument("--baseline-json", type=Path)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error("Require a new output path")
    protocol = json.loads(args.protocol_json.read_text())
    if (sha256(Path(__file__)) != protocol["runner_sha256"]
            or sha256(Path(motion.__file__)) != protocol["motion_sha256"]):
        raise ValueError("Preregistered runner or motion source changed")
    batch = next((item for item in protocol["batches"] if args.seed in item["seeds"]), None)
    if batch is None or args.phase not in ("baseline", *protocol["offsets_m"]):
        parser.error("Seed or phase absent from protocol")
    if (args.phase == "baseline") == (args.baseline_json is not None):
        parser.error("Candidate requires baseline JSON; baseline cannot supply one")
    source_path = Path(batch["contract_json"])
    if sha256(source_path) != batch["contract_sha256"]:
        raise ValueError("Original contract changed")
    source = json.loads(source_path.read_text())
    motion_path = str(Path(motion.__file__).resolve())
    if source["source_sha256"][motion_path] != protocol["previous_motion_sha256"]:
        raise ValueError("Original contract has an unexpected motion source")
    for path, expected in source["source_sha256"].items():
        if path != motion_path and sha256(Path(path)) != expected:
            raise ValueError(f"Frozen source or asset changed: {path}")
    original = source["arguments"]
    if (original["locomotion_policy"] != "wbc"
            or original["arm_controller"] != "unified-wbc"
            or not original["wbc_hold_on_gate"]
            or not original["require_motion_sweep_certificate"]
            or original["hold_seconds"] != protocol["hold_seconds"]):
        parser.error("Unexpected original precontact contract")
    baseline = None
    if args.baseline_json is not None:
        baseline = json.loads(args.baseline_json.read_text())
        if (baseline["seed"] != args.seed or baseline["phase"] != "baseline"
                or baseline["protocol_sha256"] != sha256(args.protocol_json)
                or baseline["contract_source_sha256"] != batch["contract_sha256"]):
            raise ValueError("Baseline is outside this preregistered pair")
    delta = protocol["offsets_m"].get(args.phase, [0.0, 0.0, 0.0])
    run_args = dict(original)
    run_args.update({
        "seed": args.seed,
        "output_json": str(args.output_json),
        "hold_target_step_local": delta,
        "hold_target_step_after_seconds": protocol["step_after_hold_seconds"],
        "hold_target_step_probe": True,
    })
    if baseline is not None and protocol.get("restore_from_baseline", False):
        run_args["hold_state_restore_json"] = str(args.baseline_json)
        run_args["hold_state_restore_mode"] = protocol.get("restore_mode", "inplace")
    torch.set_num_threads(1)
    result = motion.run_episode(argparse.Namespace(**run_args))
    event = result["motion"]["target_step_event"]
    state_version = protocol.get("required_state_schema_version")
    if (state_version is not None and event is not None
            and event["closed_loop_state_v2"]["schema_version"] != state_version):
        raise ValueError("Held-step state snapshot has an unexpected schema version")
    comparison = None
    if baseline is not None:
        baseline_result = baseline["result"]
        baseline_event = baseline_result["motion"]["target_step_event"]
        before = ([item for item in result["motion"]["trace"]
                   if event is not None and item["time"] <= event["time"]]
                  if event is not None else result["motion"]["trace"])
        baseline_before = (
            [item for item in baseline_result["motion"]["trace"]
             if event is not None and item["time"] <= event["time"]]
            if event is not None else baseline_result["motion"]["trace"][:len(before)]
        )
        comparison = {
            "baseline_sha256": sha256(args.baseline_json),
            "baseline_reason": baseline_result["reason"],
            "same_nav_trace": result["nav"]["trace"] == baseline_result["nav"]["trace"],
            "same_precontact_state": (
                result["candidate"]["precontact_state"]
                == baseline_result["candidate"]["precontact_state"]
            ),
            "same_pre_step_trace": before == baseline_before,
            "same_pre_step_state": (
                event is not None and baseline_event is not None
                and event["time"] == baseline_event["time"]
                and event["control_step"] == baseline_event["control_step"]
                and event["previous_target_world"] == baseline_event["previous_target_world"]
                and event["pre_step_state"] == baseline_event["pre_step_state"]
            ),
            "same_closed_loop_state_v2": (
                event is not None and baseline_event is not None
                and event["time"] == baseline_event["time"]
                and event["control_step"] == baseline_event["control_step"]
                and event["closed_loop_state_v2"] == baseline_event["closed_loop_state_v2"]
            ) if state_version == 2 else None,
            "restore_roundtrip_verified": (
                event.get("restore_roundtrip_verified") is True
                if event is not None else False
            ) if protocol.get("restore_from_baseline", False) else None,
        }
    report = {
        "schema_version": 1,
        "scope": "Matched held-state target step in MuJoCo; no invariant-set or contact claim",
        "seed": args.seed,
        "phase": args.phase,
        "offset_local_m": delta,
        "protocol_sha256": sha256(args.protocol_json),
        "contract_source": str(source_path.resolve()),
        "contract_source_sha256": sha256(source_path),
        "source_sha256": {
            **source["source_sha256"],
            motion_path: sha256(Path(motion.__file__)),
            str(Path(__file__).resolve()): sha256(Path(__file__)),
        },
        "arguments": run_args,
        "baseline_comparison": comparison,
        "result": result,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x") as destination:
        json.dump(report, destination, indent=2, allow_nan=False)
        destination.write("\n")
    print(json.dumps({"seed": args.seed, "phase": args.phase,
                      "reason": result["reason"], "step_applied": bool(
                          event is not None and event["applied"]),
                      "comparison": comparison}))


if __name__ == "__main__":
    main()
