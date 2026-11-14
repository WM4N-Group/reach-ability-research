"""Freeze body-forward held-command predictions before target-step rollouts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import mujoco
import numpy as np

from check_piper_startup import sha256


def body_forward_command(state: dict[str, object]) -> float:
    qpos = np.asarray(state["qpos"], dtype=np.float64)
    held_world = np.asarray(state["held_wbc_pose"][0], dtype=np.float64)
    if qpos.shape != (32,) or held_world.shape != (3,):
        raise ValueError("Unexpected GO2-PIPER movable-box state shape")
    rotation = np.empty(9, dtype=np.float64)
    mujoco.mju_quat2Mat(rotation, qpos[3:7])
    return float((rotation.reshape(3, 3).T @ (held_world - qpos[:3]))[0])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol-json", type=Path, required=True)
    parser.add_argument("--report-dir", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error("Require a new output path")
    protocol = json.loads(args.protocol_json.read_text())
    if sha256(Path(__file__)) != protocol["prediction_script_sha256"]:
        raise ValueError("Prediction source changed after preregistration")
    entries = []
    for batch in protocol["batches"]:
        if sha256(Path(batch["contract_json"])) != batch["contract_sha256"]:
            raise ValueError(f"Contract changed: {batch['name']}")
        for seed in batch["seeds"]:
            path = args.report_dir / f"seed{seed}-baseline-v1.json"
            baseline = json.loads(path.read_text())
            event = baseline["result"]["motion"]["target_step_event"]
            if (baseline["seed"] != seed or baseline["phase"] != "baseline"
                    or baseline["protocol_sha256"] != sha256(args.protocol_json)
                    or baseline["contract_source_sha256"] != batch["contract_sha256"]
                    or (event is not None and event["applied"])
                    or (baseline["result"]["passed"] and event is None)
                    or baseline["source_sha256"][str(Path(protocol["runner"]).resolve())]
                    != protocol["runner_sha256"]
                    or baseline["source_sha256"][str(Path(protocol["motion_source"]).resolve())]
                    != protocol["motion_sha256"]):
                raise ValueError(f"Invalid matched baseline: {seed}")
            eligible = bool(baseline["result"]["passed"] and event is not None)
            reach = body_forward_command(event["pre_step_state"]) if eligible else None
            lower, upper = protocol["body_forward_interval_m"]
            entries.append({
                "seed": seed,
                "layout": batch["name"],
                "baseline_sha256": sha256(path),
                "baseline_reason": baseline["result"]["reason"],
                "probe_time": event["time"] if event is not None else None,
                "body_forward_command_m": reach,
                "eligible": eligible,
                "predict_recovery_by_deadline": (
                    bool(lower <= reach <= upper) if eligible else None
                ),
            })
    report = {
        "schema_version": 1,
        "scope": "Prospective prediction from completed baseline probe only",
        "protocol_sha256": sha256(args.protocol_json),
        "prediction_script_sha256": sha256(Path(__file__)),
        "entries": entries,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x") as destination:
        json.dump(report, destination, indent=2, allow_nan=False)
        destination.write("\n")
    print(json.dumps({"baselines": len(entries),
                      "eligible": sum(item["eligible"] for item in entries),
                      "predicted_positive": sum(
                          item["predict_recovery_by_deadline"] is True for item in entries)}))


if __name__ == "__main__":
    main()
