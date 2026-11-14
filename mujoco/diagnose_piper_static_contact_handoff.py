"""Diagnose a static native-PIPER contact handoff candidate without execution."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import mujoco
import numpy as np

from check_piper_startup import sha256
from reconfigurable_navigation.piper_locomotion_runtime import DEPLOY
from reconfigurable_navigation.reachability import PiperPositionReachabilityOracle, ReachabilityQuery
from reconfigurable_navigation.reachability.clearance import PiperArmClearanceChecker, PiperSelfClearanceChecker, ARM_BODY_NAMES
from reconfigurable_navigation.reachability.contact_geometry import PiperContactGeometryReader, native_push_orientation
from reconfigurable_navigation.reachability.contact_limits import ContactLimitDeclaration, ContactLimitMonitor, ContactLimitProvenance, ContactLimits
from reconfigurable_navigation.reachability.scenes import make_movable_box_navigation_runtime
from reconfigurable_navigation.reachability.support import PiperQuasiStaticSupportChecker


SCRIPT = Path(__file__).resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-json", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--target-local", type=float, nargs=3, default=(-0.106, 0.0, 0.02))
    parser.add_argument("--provenance-source", required=True)
    parser.add_argument("--provenance-purpose", required=True)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error(f"Refusing to overwrite {args.output_json}")
    report = json.loads(args.input_json.read_text())
    result = report["result"]
    state = result["candidate"]["precontact_state"]
    scene = result["scene"]
    runtime = make_movable_box_navigation_runtime(
        seed=int(result["seed"]),
        box_position=np.asarray(scene["requested_box_position"], dtype=np.float64),
        box_size=np.asarray(scene["box_size"], dtype=np.float64),
        box_yaw=float(scene["requested_box_yaw"]),
        box_mass=float(scene["box_mass"]),
        config_path=DEPLOY / "config_wbc.yaml",
    )
    for field in ("qpos", "qvel", "ctrl"):
        getattr(runtime.data, field)[:] = np.asarray(state[field], dtype=np.float64)
    runtime.data.time = float(state["time"])
    mujoco.mj_forward(runtime.model, runtime.data)
    box = runtime.model.geom("reachability_box").id
    base = runtime.env.robot_qpos_adr
    rotation = runtime.data.xmat[runtime.base_id].reshape(3, 3)
    base_pose = np.array([
        runtime.data.qpos[base], runtime.data.qpos[base + 1],
        np.arctan2(rotation[1, 0], rotation[0, 0]),
    ])
    box_rotation = runtime.data.geom_xmat[box].reshape(3, 3)
    box_quaternion = np.empty(4)
    mujoco.mju_mat2Quat(box_quaternion, box_rotation.ravel())
    target_local = np.asarray(args.target_local, dtype=np.float64)
    target_world = runtime.data.geom_xpos[box] + box_rotation @ target_local
    oracle = PiperPositionReachabilityOracle(runtime)
    candidate = oracle.solve(
        ReachabilityQuery(base_pose, target_world),
        initial_joint_positions=np.asarray(result["candidate"]["joint_solution"], dtype=np.float64),
        target_quaternion=native_push_orientation(box_quaternion),
    )
    if not candidate.kinematic_feasible:
        raise RuntimeError("Static contact handoff target has no pose-IK solution")
    runtime.data.qpos[runtime.joint_qpos_adr[12:]] = candidate.joint_solution
    runtime.data.qvel.fill(0.0)
    mujoco.mj_forward(runtime.model, runtime.data)
    reader = PiperContactGeometryReader(runtime)
    self_clearance = PiperSelfClearanceChecker(runtime).evaluate_current_configuration(required_clearance=0.05)
    nonhand_clearance = PiperArmClearanceChecker(
        runtime,
        protected_body_names=frozenset({"reachability_box"}),
        arm_body_names=ARM_BODY_NAMES - reader.region.hand_bodies,
    ).evaluate_current_configuration(required_clearance=0.05)
    support = PiperQuasiStaticSupportChecker(runtime).evaluate(required_margin=0.02)
    geometry = reader.read()
    declaration = ContactLimitDeclaration(
        ContactLimits(10.0, 2.0, 0.02, 0.01, 0.15, 0.07),
        ContactLimitProvenance(
            source=args.provenance_source,
            purpose=args.provenance_purpose,
            calibration_status="diagnostic_only",
        ),
    )
    limits = ContactLimitMonitor(declaration).observe(
        geometry["contact_samples"], time=float(runtime.data.time),
        snapshot_valid=True, support_valid=support.safe,
        nonhand_clearance_valid=nonhand_clearance.safe,
    )
    output = {
        "schema_version": 1,
        "scope": "Static native-PIPER contact handoff candidate; no dynamics, policy, or execution permission",
        "contact_execution_enabled": False,
        "input_report": str(args.input_json.resolve()),
        "input_report_sha256": sha256(args.input_json),
        "provenance": declaration.provenance.__dict__,
        "target_local": target_local.tolist(),
        "candidate": {
            "position_error": candidate.position_error,
            "orientation_error": candidate.orientation_error,
            "joint_limit_margin": candidate.joint_limit_margin,
            "joint_solution": candidate.joint_solution.tolist(),
        },
        "safety": {
            "self_clearance": self_clearance.minimum_clearance,
            "nonhand_clearance": nonhand_clearance.minimum_clearance,
            "supporting_feet": list(support.supporting_feet),
            "support_margin": support.support_margin,
            "designated_face_ready": all(
                sample["region_matched"] and sample["body"] in reader.region.hand_bodies
                for sample in geometry["contact_samples"]
            ) if geometry["contact_samples"] else False,
            "contact_sample_count": len(geometry["contact_samples"]),
        },
        "contact_geometry": geometry,
        "contact_limits_assessment": limits,
        "source_sha256": {
            str(SCRIPT): sha256(SCRIPT),
            str(args.input_json.resolve()): sha256(args.input_json),
        },
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x") as destination:
        json.dump(output, destination, indent=2, allow_nan=False, default=lambda value: value.item() if isinstance(value, np.generic) else (_ for _ in ()).throw(TypeError(type(value).__name__)))
        destination.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
