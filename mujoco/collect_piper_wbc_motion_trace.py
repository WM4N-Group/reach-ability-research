"""Replay a frozen precontact report and observe every arm-motion physics state.

The original monitor still runs, including all its failure gates. This wrapper
only copies state; it does not change the controller, policy, or simulation.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import torch

import check_piper_arm_precontact_motion as motion
from check_piper_startup import sha256
from reconfigurable_navigation.piper_robot_profile import PROFILE_PATH


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-json", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-npz", type=Path, required=True)
    args = parser.parse_args()
    if (args.output_json.exists() or args.output_npz.exists()
            or args.output_json.resolve() == args.output_npz.resolve()):
        parser.error("Require distinct new output paths")
    source = json.loads(args.input_json.read_text())
    if not source.get("source_sha256"):
        parser.error("Missing source hashes")
    for path, expected in source["source_sha256"].items():
        if sha256(Path(path)) != expected:
            raise ValueError(f"Source hash mismatch: {path}")
    contract = source["arguments"]
    if contract["locomotion_policy"] != "wbc" or contract["arm_controller"] != "unified-wbc":
        parser.error("Expected unified WBC contract")
    states, velocities, controls, times = [], [], [], []
    instances = []
    original_monitor = motion.ArmMotionMonitor

    class ObservedMonitor(original_monitor):
        def __init__(self, runtime, **kwargs):
            for key, path in (("policy_sha256", runtime.policy_path),
                              ("config_sha256", runtime.config_path),
                              ("profile_sha256", PROFILE_PATH)):
                if sha256(path) != source["result"][key]:
                    raise ValueError(f"Asset mismatch: {key}")
            super().__init__(runtime, **kwargs)
            instances.append(self)

        def record(self):
            data = self.runtime.data
            states.append(data.qpos.copy())
            velocities.append(data.qvel.copy())
            controls.append(data.ctrl.copy())
            times.append(float(data.time))

        def begin_arm_motion(self):
            super().begin_arm_motion()
            self.record()

        def __call__(self):
            try:
                super().__call__()
            finally:
                if self.stage == "arm_motion":
                    self.record()

    torch.set_num_threads(1)
    motion.ArmMotionMonitor = ObservedMonitor
    try:
        result = motion.run_episode(argparse.Namespace(**contract))
    finally:
        motion.ArmMotionMonitor = original_monitor
    model = instances[0].runtime.model
    root = Path(__file__).resolve().parent
    assets = {**source["source_sha256"], str(Path(__file__).resolve()): sha256(Path(__file__))}
    for path in (root / "robots/go2_piper").rglob("*"):
        if path.is_file():
            assets[str(path.resolve())] = sha256(path)
    for path in (instances[0].runtime.policy_path, instances[0].runtime.config_path, PROFILE_PATH):
        assets[str(path.resolve())] = sha256(path)
    args.output_npz.parent.mkdir(parents=True, exist_ok=True)
    with args.output_npz.open("xb") as destination:
        np.savez_compressed(destination, qpos=np.asarray(states).reshape(-1, model.nq),
                            qvel=np.asarray(velocities).reshape(-1, model.nv),
                            ctrl=np.asarray(controls).reshape(-1, model.nu), time=np.asarray(times))
    reference_final = source["result"]["motion"]["final_state"]
    actual_final = result["motion"]["final_state"]
    comparison = {
        "same_result": result == source["result"],
        "same_pass_and_reason": (result["passed"] == source["result"]["passed"]
                                 and result["reason"] == source["result"]["reason"]),
        "final_qpos_max_abs_difference": float(np.max(np.abs(
            np.asarray(actual_final["qpos"]) - reference_final["qpos"]))),
        "final_time_difference": actual_final["time"] - reference_final["time"],
    }
    report = {
        "schema_version": 1, "scope": "observed physics endpoints; no new execution guarantee",
        "input": str(args.input_json.resolve()), "input_sha256": sha256(args.input_json),
        "arguments": contract, "source_sha256": assets, "result": result,
        "trace": {"path": str(args.output_npz.resolve()), "sha256": sha256(args.output_npz),
                  "samples": len(times), "first_sample_is_motion_start": bool(times),
                  "sim_dt": instances[0].runtime.sim_dt},
        "replay_comparison": comparison,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x") as destination:
        json.dump(report, destination, indent=2, allow_nan=False)
    print(json.dumps({"seed": contract["seed"], "samples": len(times),
                      "passed": result["passed"], "replay_comparison": comparison}, indent=2))


if __name__ == "__main__":
    main()
