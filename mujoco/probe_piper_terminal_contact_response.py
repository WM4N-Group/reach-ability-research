"""Probe contact response from a measured native-PIPER precontact terminal state."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import mujoco
import numpy as np

from check_piper_startup import sha256
from reconfigurable_navigation.piper_locomotion_runtime import DEPLOY
from reconfigurable_navigation.reachability.contact_geometry import PiperContactGeometryReader
from reconfigurable_navigation.reachability.contact_limits import ContactLimitProvenance
from reconfigurable_navigation.reachability.scenes import make_movable_box_navigation_runtime


SCRIPT = Path(__file__).resolve()


def _load_report(path: Path) -> tuple[dict[str, object], dict[str, object]]:
    with path.open() as source:
        report = json.load(source)
    for source_path, expected in report.get("source_sha256", {}).items():
        if sha256(Path(source_path)) != expected:
            raise ValueError(f"Source hash mismatch: {source_path}")
    result = report.get("result")
    if not isinstance(result, dict) or not result.get("passed"):
        raise ValueError("Input must be a successful precontact report")
    state = result.get("motion", {}).get("final_state")
    if not isinstance(state, dict):
        raise ValueError("Input must contain a complete final state")
    return report, result


def _restore(runtime, state: dict[str, object]) -> None:
    for field in ("qpos", "qvel", "ctrl"):
        values = np.asarray(state[field], dtype=np.float64)
        destination = getattr(runtime.data, field)
        if values.shape != destination.shape or not np.isfinite(values).all():
            raise ValueError(f"Invalid final-state field: {field}")
        destination[:] = values
    runtime.data.time = float(state["time"])
    mujoco.mj_forward(runtime.model, runtime.data)


def _configure_model(runtime, args: argparse.Namespace) -> None:
    runtime.model.geom_solref[:, 0] = args.contact_time_constant
    runtime.model.geom_solref[:, 1] = args.contact_damping_ratio
    runtime.model.geom_solimp[:, 0] = args.contact_impedance
    runtime.model.geom_solimp[:, 2] = args.contact_width
    robot_body_ids = {
        body_id for body_id in range(runtime.model.nbody)
        if runtime.model.body(body_id).name not in ("world", "reachability_box")
    }
    robot_geometries = [
        geometry for geometry in range(runtime.model.ngeom)
        if int(runtime.model.geom_bodyid[geometry]) in robot_body_ids
    ]
    runtime.model.geom_margin[robot_geometries] = args.contact_margin


def _run_case(runtime, result, args: argparse.Namespace, penetration: float) -> dict[str, object]:
    state = result["motion"]["final_state"]
    _restore(runtime, state)
    reader = PiperContactGeometryReader(runtime)
    box_geometry = runtime.model.geom("reachability_box").id
    box_body = int(runtime.model.geom_bodyid[box_geometry])
    box_joint = int(runtime.model.body_jntadr[box_body])
    box_qpos = int(runtime.model.jnt_qposadr[box_joint])
    box_dof = int(runtime.model.jnt_dofadr[box_joint])
    box_rotation = runtime.data.geom_xmat[box_geometry].reshape(3, 3)
    before = reader.read()
    local_x = min(
        finger["finger_point_box_frame"][0]
        for finger in before["fingers"]
        if finger["separated_witnesses_valid"]
    )
    delta_local_x = local_x - (-0.1 + penetration)
    initial_box_position = runtime.data.qpos[box_qpos : box_qpos + 3].copy()
    runtime.data.qpos[box_qpos : box_qpos + 3] = (
        initial_box_position + box_rotation[:, 0] * delta_local_x
    )
    runtime.data.qvel[box_dof : box_dof + 6] = 0.0
    mujoco.mj_forward(runtime.model, runtime.data)
    initial_geometry = reader.read()
    target = runtime.data.qpos[runtime.joint_qpos_adr].copy()
    samples = []

    def on_physics_step():
        measurement = reader.read()
        samples.extend(
            {"time": float(runtime.data.time), "sample": sample}
            for sample in measurement["contact_samples"]
        )

    runtime.on_physics_step = on_physics_step
    for _ in range(args.control_steps):
        runtime._simulate_target(target)
    measured = [entry["sample"] for entry in samples]
    final_position = runtime.data.qpos[box_qpos : box_qpos + 3].copy()
    return {
        "penetration": penetration,
        "delta_box_local_x": float(delta_local_x),
        "initial_region_matched": all(
            finger.get("box_point_in_front_region", False)
            for finger in initial_geometry["fingers"]
            if finger["separated_witnesses_valid"]
        ),
        "initial_native_orientation_error": initial_geometry["native_push_orientation_error"],
        "contact_sample_count": len(measured),
        "region_matched_samples": sum(bool(sample["region_matched"]) for sample in measured),
        "contact_bodies": sorted({sample["body"] for sample in measured}),
        "force_and_speed_peaks": {
            "normal_force": max((sample["normal_force"] for sample in measured), default=0.0),
            "tangential_force": max((sample["tangential_force"] for sample in measured), default=0.0),
            "normal_speed_abs": max((abs(sample["normal_speed"]) for sample in measured), default=0.0),
            "tangential_speed": max((sample["tangential_speed"] for sample in measured), default=0.0),
            "orientation_error": max((sample["orientation_error"] for sample in measured), default=0.0),
        },
        "box_displacement": float(np.linalg.norm(final_position - initial_box_position)),
        "contact_samples": samples,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-json", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--physics-substeps", type=int, choices=(1, 2, 4), default=1)
    parser.add_argument("--control-steps", type=int, default=4)
    parser.add_argument("--penetrations", type=float, nargs="+", required=True)
    parser.add_argument("--contact-time-constant", type=float, required=True)
    parser.add_argument("--contact-damping-ratio", type=float, required=True)
    parser.add_argument("--contact-impedance", type=float, required=True)
    parser.add_argument("--contact-width", type=float, required=True)
    parser.add_argument("--contact-margin", type=float, required=True)
    parser.add_argument("--provenance-source", required=True)
    parser.add_argument("--provenance-purpose", required=True)
    parser.add_argument(
        "--calibration-status", choices=("diagnostic_only",), required=True
    )
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error(f"Refusing to overwrite {args.output_json}")
    if args.control_steps < 1 or not np.isfinite(args.penetrations).all():
        parser.error("Control steps must be positive and penetrations finite")
    provenance = ContactLimitProvenance(
        source=args.provenance_source,
        purpose=args.provenance_purpose,
        calibration_status=args.calibration_status,
    )
    report, result = _load_report(args.input_json)
    scene = result["scene"]
    runtime = make_movable_box_navigation_runtime(
        seed=int(result["seed"]),
        box_position=np.asarray(scene["requested_box_position"], dtype=np.float64),
        box_size=np.asarray(scene["box_size"], dtype=np.float64),
        box_yaw=float(scene["requested_box_yaw"]),
        box_mass=float(scene["box_mass"]),
        config_path=DEPLOY / "config_wbc.yaml",
        physics_substeps=args.physics_substeps,
    )
    _configure_model(runtime, args)
    results = [_run_case(runtime, result, args, float(penetration)) for penetration in args.penetrations]
    source_paths = [
        SCRIPT,
        args.input_json,
        Path(__file__).resolve().parent / "reconfigurable_navigation/reachability/contact_geometry.py",
        Path(__file__).resolve().parent / "reconfigurable_navigation/reachability/scenes.py",
    ]
    output = {
        "schema_version": 1,
        "scope": "Measured native-terminal contact response probe with injected box pose; no policy, PUSH skill, or handoff execution",
        "contact_execution_enabled": False,
        "policy_executed": False,
        "push_actor_executed": False,
        "input_report": str(args.input_json.resolve()),
        "input_report_sha256": sha256(args.input_json),
        "provenance": provenance.__dict__,
        "model_parameters": {
            "contact_time_constant": args.contact_time_constant,
            "contact_damping_ratio": args.contact_damping_ratio,
            "contact_impedance": args.contact_impedance,
            "contact_width": args.contact_width,
            "contact_margin": args.contact_margin,
        },
        "probe": {
            "physics_substeps": args.physics_substeps,
            "control_steps": args.control_steps,
            "penetrations": list(map(float, args.penetrations)),
            "geometry_injection": "translate the measured box snapshot along its local x axis while keeping measured robot terminal state",
        },
        "results": results,
        "source_sha256": {str(Path(path).resolve()): sha256(Path(path)) for path in source_paths},
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x") as destination:
        json.dump(output, destination, indent=2, allow_nan=False)
        destination.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
