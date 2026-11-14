"""Replay a frozen WBC precontact input with optional adaptive Euler sweep bounds."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import mujoco
import numpy as np
import torch

import check_piper_arm_precontact_motion as motion
from check_piper_startup import sha256
from reconfigurable_navigation.reachability.sweep_refinement import refine_euler_clearance


def make_monitor(max_depth: int):
    original = motion.ArmMotionMonitor

    class AdaptiveMonitor(original):
        def __init__(self, runtime, **kwargs):
            super().__init__(runtime, **kwargs)
            self.raw_minimum_swept_bounds = [float("inf")] * len(self.sweep_checkers)
            self.adaptive_sweep_events = []
            self.adaptive_sweep_geometry_evaluations = 0

        def _check_swept_clearance(
            self, self_result, environment_result, support_result,
            finger_environment_result=None, nonhand_environment_result=None,
        ) -> None:
            current = self.runtime.data.qpos
            previous_qpos = self.sweep_previous_qpos
            previous_clearances = self.sweep_previous_clearances
            velocity = self.runtime.data.qvel
            duration = self.runtime.sim_dt
            predicted = previous_qpos.copy()
            mujoco.mj_integratePos(self.runtime.model, predicted, velocity, duration)
            residual = float(np.max(np.abs(predicted - current)))
            self.maximum_integration_residual = max(self.maximum_integration_residual, residual)
            free_joints = np.flatnonzero(
                self.runtime.model.jnt_type == mujoco.mjtJoint.mjJNT_FREE)
            angular_step = max(
                float(np.linalg.norm(velocity[
                    int(self.runtime.model.jnt_dofadr[joint]) + 3:
                    int(self.runtime.model.jnt_dofadr[joint]) + 6])) * duration
                for joint in free_joints
            )
            if residual > 1.0e-12 or angular_step >= math.pi:
                raise motion.RolloutFailure("motion_sweep_integration_mismatch")
            clearances = [self_result.minimum_clearance, environment_result.minimum_clearance]
            checkers = [self.self_clearance, self.environment_clearance]
            enforced = {0: (self.required_self_clearance, "dynamic_swept_self_clearance")}
            if self.diagnose_designated_hand_approach:
                clearances.extend((finger_environment_result.minimum_clearance,
                                   nonhand_environment_result.minimum_clearance))
                checkers.extend((self.finger_environment_clearance,
                                 self.nonhand_environment_clearance))
                enforced.update({
                    2: (0.0, "dynamic_swept_finger_contact"),
                    3: (self.required_environment_clearance,
                        "dynamic_swept_nonhand_environment_clearance"),
                })
            else:
                enforced[1] = (self.required_environment_clearance,
                               "dynamic_swept_environment_clearance")
            lower_bounds = [
                min(previous, current_clearance)
                - sweep.nearest_endpoint_motion_bound(previous_qpos, current)
                for previous, current_clearance, sweep in zip(
                    previous_clearances, clearances, self.sweep_checkers)
            ]
            for index, lower in enumerate(lower_bounds):
                self.raw_minimum_swept_bounds[index] = min(
                    self.raw_minimum_swept_bounds[index], lower)
            for index, (threshold, reason) in enforced.items():
                if lower_bounds[index] >= threshold:
                    continue
                result = refine_euler_clearance(
                    checkers[index], self.sweep_checkers[index], previous_qpos,
                    velocity, duration, previous_clearances[index],
                    clearances[index], threshold, max_depth=max_depth)
                self.adaptive_sweep_geometry_evaluations += result.geometry_evaluations
                self.adaptive_sweep_events.append({
                    "time": float(self.runtime.data.time),
                    "constraint": reason,
                    "original_lower_bound": lower_bounds[index],
                    "refined_lower_bound": result.lower_bound,
                    "required_clearance": threshold,
                    "passed": result.passed,
                    "geometry_evaluations": result.geometry_evaluations,
                    "maximum_depth_used": result.maximum_depth_used,
                })
                lower_bounds[index] = result.lower_bound
            self.clearance_data.qpos[:] = current
            mujoco.mj_kinematics(self.runtime.model, self.clearance_data)
            self.minimum_swept_self_clearance = min(
                self.minimum_swept_self_clearance, lower_bounds[0])
            self.minimum_swept_environment_clearance = min(
                self.minimum_swept_environment_clearance, lower_bounds[1])
            if self.diagnose_designated_hand_approach:
                self.minimum_swept_finger_environment_clearance = min(
                    self.minimum_swept_finger_environment_clearance, lower_bounds[2])
                self.minimum_swept_nonhand_environment_clearance = min(
                    self.minimum_swept_nonhand_environment_clearance, lower_bounds[3])
            self.sweep_intervals += 1
            self.sweep_previous_qpos = current.copy()
            self.sweep_previous_clearances = tuple(clearances)
            for index, (threshold, reason) in enforced.items():
                if lower_bounds[index] < threshold:
                    self._record_failure(reason, self_result, environment_result, support_result)
                    raise motion.RolloutFailure(reason)

    return AdaptiveMonitor


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-json", type=Path, required=True)
    parser.add_argument("--max-depth", type=int, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    if args.output_json.exists() or args.max_depth < 0:
        parser.error("Require a new output path and nonnegative maximum depth")
    source = json.loads(args.input_json.read_text())
    for path, expected in source["source_sha256"].items():
        if sha256(Path(path)) != expected:
            raise ValueError(f"Frozen source or asset changed: {path}")
    contract = source["arguments"]
    if not contract["require_motion_sweep_certificate"]:
        parser.error("Input must enable the original sweep certificate")
    original_monitor = motion.ArmMotionMonitor
    instances = []
    adaptive_type = make_monitor(args.max_depth)

    class ObservedMonitor(adaptive_type):
        def __init__(self, runtime, **kwargs):
            super().__init__(runtime, **kwargs)
            instances.append(self)

    torch.set_num_threads(1)
    motion.ArmMotionMonitor = ObservedMonitor
    try:
        result = motion.run_episode(argparse.Namespace(**contract))
    finally:
        motion.ArmMotionMonitor = original_monitor
    monitor = instances[0]
    raw_names = ("self", "environment", "finger_environment", "nonhand_environment")
    report = {
        "schema_version": 1,
        "scope": "Candidate WBC precontact rollout; no contact, PUSH or deployment approval",
        "input": str(args.input_json.resolve()),
        "input_sha256": sha256(args.input_json),
        "source_sha256": {
            **source["source_sha256"],
            str(Path(__file__).resolve()): sha256(Path(__file__)),
            str((Path(__file__).parent / "reconfigurable_navigation/reachability/sweep_refinement.py").resolve()):
                sha256(Path(__file__).parent / "reconfigurable_navigation/reachability/sweep_refinement.py"),
        },
        "arguments": contract,
        "adaptive_sweep": {
            "max_depth": args.max_depth,
            "extra_geometry_evaluations": monitor.adaptive_sweep_geometry_evaluations,
            "events": monitor.adaptive_sweep_events,
            "minimum_original_lower_bounds": {
                name: monitor.finite_minimum(value)
                for name, value in zip(raw_names, monitor.raw_minimum_swept_bounds)
            },
        },
        "baseline_comparison": {
            "same_result": result == source["result"],
            "baseline_reason": source["result"]["reason"],
            "candidate_reason": result["reason"],
        },
        "result": result,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x") as destination:
        json.dump(report, destination, indent=2, allow_nan=False)
    print(json.dumps({"seed": result["seed"], "passed": result["passed"],
                      "reason": result["reason"],
                      "same_result": report["baseline_comparison"]["same_result"],
                      "extra_geometry_evaluations": monitor.adaptive_sweep_geometry_evaluations,
                      "events": monitor.adaptive_sweep_events}, indent=2))


if __name__ == "__main__":
    main()
