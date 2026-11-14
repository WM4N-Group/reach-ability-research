"""Probe MuJoCo PIPER contact response without policies, skills, or execution permission."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import mujoco
import numpy as np

from check_piper_startup import sha256
from reconfigurable_navigation.piper_locomotion_runtime import DEPLOY
from reconfigurable_navigation.reachability.contact_geometry import PiperContactGeometryReader
from reconfigurable_navigation.reachability.scenes import make_movable_box_navigation_runtime
from reconfigurable_navigation.reachability.contact_limits import ContactLimitProvenance


SCRIPT = Path(__file__).resolve()


def _robot_geometry_ids(model, excluded_body: str) -> list[int]:
    excluded = {"world", excluded_body}
    robot_body_ids = {
        body_id for body_id in range(model.nbody)
        if model.body(body_id).name not in excluded
    }
    return [
        geometry for geometry in range(model.ngeom)
        if int(model.geom_bodyid[geometry]) in robot_body_ids
    ]


def _configure_contact_model(runtime, args: argparse.Namespace) -> None:
    runtime.model.geom_solref[:, 0] = args.contact_time_constant
    runtime.model.geom_solref[:, 1] = args.contact_damping_ratio
    runtime.model.geom_solimp[:, 0] = args.contact_impedance
    runtime.model.geom_solimp[:, 2] = args.contact_width
    robot_geometries = _robot_geometry_ids(runtime.model, "reachability_box")
    runtime.model.geom_margin[robot_geometries] = args.contact_margin


def _run_case(args: argparse.Namespace, penetration: float) -> dict[str, object]:
    runtime = make_movable_box_navigation_runtime(
        seed=args.seed,
        box_position=np.array([0.9, 0.0, 0.12]),
        box_size=np.array([0.2, 0.2, 0.24]),
        box_yaw=0.0,
        box_mass=args.box_mass,
        config_path=DEPLOY / "config_wbc.yaml",
        physics_substeps=args.physics_substeps,
    )
    _configure_contact_model(runtime, args)
    for _ in range(args.settle_steps):
        runtime.hold_default()
    reader = PiperContactGeometryReader(runtime)
    box_geometry = runtime.model.geom("reachability_box").id
    box_body = int(runtime.model.geom_bodyid[box_geometry])
    box_joint = int(runtime.model.body_jntadr[box_body])
    box_qpos = int(runtime.model.jnt_qposadr[box_joint])
    box_dof = int(runtime.model.jnt_dofadr[box_joint])
    finger_geometry = reader.finger_geometries[0]
    finger_center = runtime.data.geom_xpos[finger_geometry].copy()
    initial_box_position = np.array(
        [finger_center[0] + 0.1 - penetration, finger_center[1], finger_center[2]],
        dtype=np.float64,
    )
    runtime.data.qpos[box_qpos : box_qpos + 3] = initial_box_position
    runtime.data.qpos[box_qpos + 3 : box_qpos + 7] = [1.0, 0.0, 0.0, 0.0]
    runtime.data.qvel.fill(0.0)
    mujoco.mj_forward(runtime.model, runtime.data)
    target = runtime.data.qpos[runtime.joint_qpos_adr].copy()
    samples = []
    box_states = []

    def on_physics_step():
        measurement = reader.read()
        box_states.append({
            "time": float(runtime.data.time),
            "position": runtime.data.qpos[box_qpos : box_qpos + 3].tolist(),
            "velocity": runtime.data.qvel[box_dof : box_dof + 6].tolist(),
        })
        if measurement["contact_samples"]:
            samples.extend(
                {"time": float(runtime.data.time), "sample": sample}
                for sample in measurement["contact_samples"]
            )

    runtime.on_physics_step = on_physics_step
    for _ in range(args.control_steps):
        runtime._simulate_target(target)
    final_position = runtime.data.qpos[box_qpos : box_qpos + 3].copy()
    measured_samples = [entry["sample"] for entry in samples]
    normal_forces = [float(sample["normal_force"]) for sample in measured_samples]
    tangential_forces = [float(sample["tangential_force"]) for sample in measured_samples]
    normal_speeds = [float(sample["normal_speed"]) for sample in measured_samples]
    tangential_speeds = [float(sample["tangential_speed"]) for sample in measured_samples]
    return {
        "penetration": penetration,
        "finger_geometry": runtime.model.geom(finger_geometry).name,
        "finger_center_world": finger_center.tolist(),
        "injected_box_position": initial_box_position.tolist(),
        "final_box_position": final_position.tolist(),
        "box_displacement": float(np.linalg.norm(final_position - initial_box_position)),
        "contact_sample_count": len(samples),
        "contact_bodies": sorted({sample["body"] for sample in measured_samples}),
        "region_matched_samples": sum(bool(sample["region_matched"]) for sample in measured_samples),
        "force_and_speed_peaks": {
            "normal_force": max(normal_forces, default=0.0),
            "tangential_force": max(tangential_forces, default=0.0),
            "normal_speed_abs": max((abs(value) for value in normal_speeds), default=0.0),
            "tangential_speed": max(tangential_speeds, default=0.0),
        },
        "contact_samples": samples,
        "box_state_trace": box_states,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--physics-substeps", type=int, choices=(1, 2, 4), default=1)
    parser.add_argument("--settle-steps", type=int, default=50)
    parser.add_argument("--control-steps", type=int, default=4)
    parser.add_argument("--box-mass", type=float, default=1.0)
    parser.add_argument("--penetrations", type=float, nargs="+", required=True)
    parser.add_argument("--contact-time-constant", type=float, required=True)
    parser.add_argument("--contact-damping-ratio", type=float, required=True)
    parser.add_argument("--contact-impedance", type=float, required=True)
    parser.add_argument("--contact-width", type=float, required=True)
    parser.add_argument("--contact-margin", type=float, required=True)
    parser.add_argument("--provenance-source", required=True)
    parser.add_argument("--provenance-purpose", required=True)
    parser.add_argument(
        "--calibration-status",
        choices=("diagnostic_only", "simulation_calibrated", "hardware_calibrated"),
        required=True,
    )
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error(f"Refusing to overwrite {args.output_json}")
    if args.seed < 0 or args.settle_steps < 0 or args.control_steps < 1 or args.box_mass <= 0.0:
        parser.error("Seed, step counts and mass must be positive where required")
    if args.calibration_status != "diagnostic_only":
        parser.error("This injected fixed-arm probe only produces diagnostic_only results")
    if not np.isfinite(args.penetrations).all():
        parser.error("Penetrations must be finite")
    if not np.isfinite([
        args.contact_time_constant, args.contact_damping_ratio,
        args.contact_impedance, args.contact_width, args.contact_margin,
    ]).all():
        parser.error("Contact model parameters must be finite")
    provenance = ContactLimitProvenance(
        source=args.provenance_source,
        purpose=args.provenance_purpose,
        calibration_status=args.calibration_status,
    )
    results = [_run_case(args, float(penetration)) for penetration in args.penetrations]
    source_paths = [
        SCRIPT,
        DEPLOY / "config_wbc.yaml",
        Path(__file__).resolve().parent / "deploy/policy/go2_piper/wbc/policy.pt",
        Path(__file__).resolve().parent / "reconfigurable_navigation/reachability/contact_geometry.py",
        Path(__file__).resolve().parent / "reconfigurable_navigation/reachability/scenes.py",
    ]
    report = {
        "schema_version": 1,
        "scope": "Injected fixed-arm contact response probe; no policy, PUSH skill, contact handoff, or execution permission",
        "contact_execution_enabled": False,
        "stepped": True,
        "policy_executed": False,
        "push_actor_executed": False,
        "provenance": provenance.__dict__,
        "model_parameters": {
            "contact_time_constant": args.contact_time_constant,
            "contact_damping_ratio": args.contact_damping_ratio,
            "contact_impedance": args.contact_impedance,
            "contact_width": args.contact_width,
            "contact_margin": args.contact_margin,
        },
        "probe": {
            "seed": args.seed,
            "physics_substeps": args.physics_substeps,
            "settle_steps": args.settle_steps,
            "control_steps": args.control_steps,
            "box_mass": args.box_mass,
            "penetrations": list(map(float, args.penetrations)),
            "geometry_injection": "box front face placed at first active finger geometry center minus penetration along world x",
        },
        "results": results,
        "source_sha256": {str(Path(path).resolve()): sha256(Path(path)) for path in source_paths},
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x") as destination:
        json.dump(report, destination, indent=2, allow_nan=False)
        destination.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
