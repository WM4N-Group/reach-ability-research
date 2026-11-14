"""Record compiled PIPER contact-model parameters without stepping or executing PUSH."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from check_piper_startup import sha256
from reconfigurable_navigation.piper_box_runtime import DEPLOY, ROOT, make_episode
from reconfigurable_navigation.piper_robot_profile import PROFILE_PATH
from reconfigurable_navigation.reachability.contact_limits import ContactLimitProvenance


SCRIPT = Path(__file__).resolve()
POLICY_DEFAULT = SCRIPT.parent / "deploy/policy/go2_piper/policy.pt"


def record(args: argparse.Namespace) -> dict[str, object]:
    provenance = ContactLimitProvenance(
        source=args.provenance_source,
        purpose=args.provenance_purpose,
        calibration_status=args.calibration_status,
    )
    runtime = make_episode(
        "push",
        str(args.policy),
        args.seed,
        push_ik_mode="pose",
        native_collisions=True,
        contact_time_constant=args.contact_time_constant,
        contact_damping_ratio=args.contact_damping_ratio,
        contact_impedance=args.contact_impedance,
        contact_width=args.contact_width,
        contact_margin=args.contact_margin,
    )
    model = runtime.model
    box_geometry = model.geom("push_box").id
    floor_geometry = model.geom("floor").id
    robot_body_ids = {
        body_id for body_id in range(model.nbody)
        if model.body(body_id).name not in ("world", "push_box")
    }
    robot_geometries = [
        geometry for geometry in range(model.ngeom)
        if int(model.geom_bodyid[geometry]) in robot_body_ids
    ]
    source_paths = [
        SCRIPT,
        ROOT / "reconfigurable_navigation/piper_box_runtime.py",
        ROOT / "reconfigurable_navigation/box_push_runtime.py",
        ROOT / "reconfigurable_navigation/piper_robot_profile.py",
        PROFILE_PATH,
        DEPLOY / "config.yaml",
        args.policy,
    ]
    return {
        "schema_version": 1,
        "scope": "Compiled MuJoCo contact-model manifest only; no stepping, contact calibration, or PUSH execution",
        "contact_execution_enabled": False,
        "stepped": False,
        "seed": args.seed,
        "policy_sha256": sha256(args.policy),
        "provenance": provenance.__dict__,
        "requested_parameters": {
            "contact_time_constant": args.contact_time_constant,
            "contact_damping_ratio": args.contact_damping_ratio,
            "contact_impedance": args.contact_impedance,
            "contact_width": args.contact_width,
            "contact_margin": args.contact_margin,
        },
        "compiled_parameters": {
            "geom_solref_unique": np.unique(model.geom_solref, axis=0).tolist(),
            "geom_solimp_unique": np.unique(model.geom_solimp, axis=0).tolist(),
            "box_geom_margin": float(model.geom_margin[box_geometry]),
            "floor_geom_margin": float(model.geom_margin[floor_geometry]),
            "robot_geom_margin_unique": np.unique(model.geom_margin[robot_geometries]).tolist(),
            "box_geom_friction": model.geom_friction[box_geometry].tolist(),
        },
        "scope_notes": {
            "contact_margin": "robot geometries only; box and floor remain zero",
            "contact_force": "not measured",
            "contact_speed": "not measured",
            "box_motion": "not measured",
        },
        "simulation": {
            "mujoco_timestep": float(model.opt.timestep),
            "integrator": int(model.opt.integrator),
            "box_geometry": int(box_geometry),
            "floor_geometry": int(floor_geometry),
            "time": float(runtime.data.time),
        },
        "source_sha256": {str(Path(path).resolve()): sha256(Path(path)) for path in source_paths},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--policy", type=Path, default=POLICY_DEFAULT)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--provenance-source", required=True)
    parser.add_argument("--provenance-purpose", required=True)
    parser.add_argument(
        "--calibration-status",
        choices=("diagnostic_only", "simulation_calibrated", "hardware_calibrated"),
        required=True,
    )
    parser.add_argument("--contact-time-constant", type=float, required=True)
    parser.add_argument("--contact-damping-ratio", type=float, required=True)
    parser.add_argument("--contact-impedance", type=float, required=True)
    parser.add_argument("--contact-width", type=float, required=True)
    parser.add_argument("--contact-margin", type=float, required=True)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error(f"Refusing to overwrite {args.output_json}")
    if args.seed < 0 or not args.policy.is_file():
        parser.error("Seed must be non-negative and policy must exist")
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    report = record(args)
    with args.output_json.open("x") as destination:
        json.dump(report, destination, indent=2, allow_nan=False)
        destination.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
