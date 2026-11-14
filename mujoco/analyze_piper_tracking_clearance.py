"""Measure conditional tracking-error capacity of saved PIPER IK candidates."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path

import mujoco
import numpy as np

from check_piper_startup import sha256
from reconfigurable_navigation.piper_locomotion_runtime import DEPLOY
from reconfigurable_navigation.piper_robot_profile import PROFILE_PATH
from reconfigurable_navigation.reachability.clearance import (
    ARM_BODY_NAMES, PiperArmClearanceChecker, PiperSelfClearanceChecker,
)
from reconfigurable_navigation.reachability.scenes import (
    STATIC_BOX_BODY, make_movable_box_navigation_runtime,
)
from reconfigurable_navigation.reachability.tracking_clearance import PiperTrackingClearance


def analyze(path, args):
    report = json.loads(path.read_text())
    sources = report.get("source_sha256", {})
    if not sources:
        raise ValueError(f"Missing input source hashes: {path}")
    for source, expected in sources.items():
        if sha256(Path(source)) != expected:
            raise ValueError(f"Input source hash mismatch: {source}")
    result = report["result"]
    if not result["candidate"]["kinematic_feasible"]:
        raise ValueError("Input must have a solved IK candidate")
    scene = result["scene"]
    if scene["box_mode"] != "movable":
        raise ValueError("This diagnostic expects a movable-box snapshot")
    runtime = make_movable_box_navigation_runtime(
        seed=result["seed"], box_position=np.asarray(scene["requested_box_position"]),
        box_size=np.asarray(scene["box_size"]), box_yaw=scene["requested_box_yaw"],
        box_mass=scene["box_mass"], config_path=DEPLOY / "config_wbc.yaml",
        physics_substeps=report["arguments"]["physics_substeps"],
    )
    for name, file in (("policy_sha256", runtime.policy_path),
                       ("config_sha256", runtime.config_path), ("profile_sha256", PROFILE_PATH)):
        if sha256(file) != result[name]:
            raise ValueError(f"Input runtime asset mismatch: {name}")
    nominal = np.asarray(result["candidate"]["precontact_state"]["qpos"], dtype=float)
    if nominal.shape != (runtime.model.nq,) or not np.isfinite(nominal).all():
        raise ValueError("Invalid snapshot qpos")
    start = nominal.copy()
    nominal[runtime.joint_qpos_adr[12:]] = result["candidate"]["joint_solution"]
    checkers = {
        "self": PiperSelfClearanceChecker(runtime),
        "nonhand_environment": PiperArmClearanceChecker(
            runtime, protected_body_names=frozenset({STATIC_BOX_BODY}),
            arm_body_names=ARM_BODY_NAMES - frozenset({"link7", "link8"}),
        ),
        "finger_environment": PiperArmClearanceChecker(
            runtime, protected_body_names=frozenset({STATIC_BOX_BODY}),
            arm_body_names=frozenset({"link7", "link8"}),
        ),
    }
    capacities = {}
    for name, checker in checkers.items():
        bound = PiperTrackingClearance(checker, moving_body_names=frozenset({STATIC_BOX_BODY}))
        budgets = dict(
            base_translation_radius=args.base_translation_radius,
            base_rotation_radius=args.base_rotation_radius,
            external_point_error_radius=args.object_point_error_radius if name != "self" else 0,
            required_clearance=(args.required_finger_clearance if name == "finger_environment"
                                else args.required_clearance),
            required_joint_margin=args.required_joint_margin,
        )
        capacity = bound.maximum_uniform_arm_error(
            nominal, leg_error_radii=np.full(12, args.leg_error_radius), **budgets
        )
        trials = []
        for radius in args.arm_error_radii:
            certificate = bound.evaluate(nominal, joint_error_radii=np.r_[
                np.full(12, args.leg_error_radius), np.full(6, radius)
            ], **budgets)
            trials.append({
                "arm_error_radius": radius, **asdict(certificate),
                "conditional_clearance_safe": certificate.conditional_clearance_safe,
                "limiting_geometry_names": [runtime.model.geom(g).name or f"geom_{g}"
                                            for g in certificate.limiting_geometry_pair],
                "limiting_body_names": [runtime.model.body(int(runtime.model.geom_bodyid[g])).name
                                        for g in certificate.limiting_geometry_pair],
            })
        path_capacity = bound.maximum_uniform_arm_error_on_joint_path(
            start, nominal, samples=args.path_samples,
            leg_error_radii=np.full(12, args.leg_error_radius), **budgets,
        )
        path_zero_arm_error = bound.evaluate_joint_path(
            start, nominal, samples=args.path_samples,
            joint_error_radii=np.r_[np.full(12, args.leg_error_radius), np.zeros(6)],
            **budgets,
        )
        capacities[name] = {
            "maximum_uniform_arm_error": capacity, "trials": trials,
            "reference_path_maximum_uniform_arm_error": path_capacity,
            "reference_path_with_zero_arm_error": {
                **asdict(path_zero_arm_error),
                "conditional_clearance_safe": path_zero_arm_error.conditional_clearance_safe,
            },
        }
    joint_ids = runtime.model.dof_jntid[runtime.joint_dof_adr]
    available = [item["maximum_uniform_arm_error"] for item in capacities.values()]
    path_available = [item["reference_path_maximum_uniform_arm_error"] for item in capacities.values()]
    endpoint_radius = min(available) if all(x is not None for x in available) else None
    actual_qpos = np.asarray(result["motion"]["final_state"]["qpos"], dtype=float)
    if actual_qpos.shape != nominal.shape or not np.isfinite(actual_qpos).all():
        raise ValueError("Invalid executed final state")
    joint_errors = np.abs(actual_qpos[runtime.joint_qpos_adr] - nominal[runtime.joint_qpos_adr])
    base = runtime.env.robot_qpos_adr
    rotation_vector = np.empty(3)
    mujoco.mju_subQuat(rotation_vector, actual_qpos[base + 3:base + 7], nominal[base + 3:base + 7])
    translation_error = float(np.linalg.norm(actual_qpos[base:base + 3] - nominal[base:base + 3]))
    rotation_error = float(np.linalg.norm(rotation_vector))
    endpoint_robot_membership = bool(
        endpoint_radius is not None and np.max(joint_errors[12:]) <= endpoint_radius
        and np.max(joint_errors[:12]) <= args.leg_error_radius
        and translation_error <= args.base_translation_radius
        and rotation_error <= args.base_rotation_radius
    )
    return {
        "input": str(path.resolve()), "input_sha256": sha256(path),
        "seed": result["seed"], "scene": scene,
        "nominal_state": "NAV snapshot legs/base/object with candidate IK arm substituted; not executed",
        "joint_order": [runtime.model.joint(int(j)).name for j in joint_ids],
        "policy_sha256": sha256(runtime.policy_path),
        "config_sha256": sha256(runtime.config_path), "profile_sha256": sha256(PROFILE_PATH),
        "capacities": capacities,
        "combined_maximum_uniform_arm_error": endpoint_radius,
        "reference_path": "joint-linear NAV snapshot to IK arm; fixed nominal base/legs/object; not WBC rollout",
        "combined_path_maximum_uniform_arm_error": (
            min(path_available) if all(x is not None for x in path_available) else None
        ),
        "controller_meets_budget": None,
        "executed_endpoint_comparison": {
            "reference": "the input report's candidate IK arm and precontact base/legs",
            "scope": "robot coordinates at final time only; no path-wide or object-budget assertion",
            "maximum_leg_joint_error": float(np.max(joint_errors[:12])),
            "maximum_arm_joint_error": float(np.max(joint_errors[12:])),
            "base_translation_error": translation_error,
            "base_rotation_error": rotation_error,
            "inside_endpoint_robot_budgets": endpoint_robot_membership,
            "input_rollout_passed_its_own_criteria": result["passed"],
        },
        "execution_certified": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-json", type=Path, nargs="+", required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--leg-error-radius", type=float, default=0.002)
    parser.add_argument("--arm-error-radii", type=float, nargs="+", default=[0.002, 0.01, 0.02])
    parser.add_argument("--base-translation-radius", type=float, default=0.005)
    parser.add_argument("--base-rotation-radius", type=float, default=0.01)
    parser.add_argument("--object-point-error-radius", type=float, default=0.002)
    parser.add_argument("--required-clearance", type=float, default=0.05)
    parser.add_argument("--required-finger-clearance", type=float, default=0.02)
    parser.add_argument("--required-joint-margin", type=float, default=0.05)
    parser.add_argument("--path-samples", type=int, default=51)
    args = parser.parse_args()
    scalars = [args.leg_error_radius, *args.arm_error_radii, args.base_translation_radius,
               args.base_rotation_radius, args.object_point_error_radius,
               args.required_clearance, args.required_finger_clearance, args.required_joint_margin]
    if args.output_json.exists() or not np.isfinite(scalars).all() or min(scalars) < 0 or args.path_samples < 2:
        parser.error("Require finite nonnegative budgets and a new output path")
    results = [analyze(path, args) for path in args.input_json]
    root = Path(__file__).resolve().parent
    paths = [Path(__file__).resolve(), PROFILE_PATH, root / "check_piper_startup.py"]
    paths.extend(root / "reconfigurable_navigation" / name for name in (
        "reachability/tracking_clearance.py", "reachability/sweep.py", "reachability/clearance.py",
        "reachability/scenes.py", "piper_robot_profile.py", "piper_locomotion_runtime.py",
        "locomotion_runtime.py",
    ))
    paths.extend(p for p in (root / "robots/go2_piper").rglob("*") if p.is_file())
    report = {
        "schema_version": 1,
        "scope": "conditional static geometry/limit capacity; supplied budgets are not calibrated controller errors",
        "arguments": {k: [str(p) for p in v] if k == "input_json" else str(v) if isinstance(v, Path) else v
                      for k, v in vars(args).items()},
        "source_assets_sha256": {str(p.resolve()): sha256(p) for p in paths},
        "backend": {"mujoco": mujoco.__version__, "numpy": np.__version__},
        "results": results,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x") as output:
        json.dump(report, output, indent=2, allow_nan=False)
    print(json.dumps([{ "seed": item["seed"], "input": item["input"],
                       "maximum_uniform_arm_error": item["combined_maximum_uniform_arm_error"],
                       "path_maximum_uniform_arm_error": item["combined_path_maximum_uniform_arm_error"],
                       "executed_endpoint_comparison": item["executed_endpoint_comparison"],
                       "capacity_by_constraint": {k: v["maximum_uniform_arm_error"]
                                                  for k, v in item["capacities"].items()}}
                     for item in results], indent=2))


if __name__ == "__main__":
    main()
