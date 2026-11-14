"""Read available PhysX shape offsets in a loaded Isaac scene, without rollout."""

import argparse
import hashlib
import json
from pathlib import Path

from isaaclab.app import AppLauncher


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output-json", type=Path, required=True)
AppLauncher.add_app_launcher_args(parser)
args = parser.parse_args()
if args.output_json.exists():
    parser.error("Output already exists")
launcher = AppLauncher(args)

import gymnasium as gym
import omni.physics.tensors as tensors
import omni.usd
from pxr import UsdShade

import LeggedManip_Lab.tasks  # noqa: F401
from isaaclab.sensors import ContactSensorCfg
from isaaclab_tasks.utils import load_cfg_from_registry


TASK = "GO2-PIPER-Box-Push-Tracking-Play"
GROUND = "/World/ground/terrain/GroundPlane/CollisionPlane"


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def rigid_shape_data(view):
    if view.count != 1 or view.max_shapes < 1:
        raise ValueError(f"Expected one rigid body with shapes, got {view.count}/{view.max_shapes}")
    contact = view.get_contact_offsets().tolist()
    rest = view.get_rest_offsets().tolist()
    material = view.get_material_properties().tolist()
    if (len(contact) != 1 or len(contact[0]) != view.max_shapes
            or len(rest) != 1 or len(rest[0]) != view.max_shapes
            or len(material) != 1 or len(material[0]) != view.max_shapes):
        raise ValueError("PhysX rigid shape tensors have inconsistent dimensions")
    return {
        "prim_paths": list(view.prim_paths),
        "shape_count": view.max_shapes,
        "contact_offsets_m": contact[0],
        "rest_offsets_m": rest[0],
        "material_properties": material[0],
    }


def authored_offsets(prim):
    return {
        attr.GetName(): str(attr.Get())
        for attr in prim.GetAttributes()
        if "contactoffset" in attr.GetName().lower()
        or "restoffset" in attr.GetName().lower()
    }


def main():
    config = load_cfg_from_registry(TASK, "env_cfg_entry_point")
    config.scene.num_envs = 1
    config.sim.device = args.device
    config.observations.policy.enable_corruption = False
    config.scene.diagnostic_base_offset = ContactSensorCfg(
        prim_path="{ENV_REGEX_NS}/Robot/base", update_period=config.sim.dt
    )
    usd_path = Path(config.scene.robot.spawn.usd_path)
    env = gym.make(TASK, cfg=config)
    try:
        stage = omni.usd.get_context().get_stage()
        ground = stage.GetPrimAtPath(GROUND)
        if not ground.IsValid():
            raise ValueError(f"Loaded ground prim missing: {GROUND}")
        material, binding = UsdShade.MaterialBindingAPI(ground).ComputeBoundMaterial("physics")
        base = env.unwrapped.scene["diagnostic_base_offset"]
        if base.body_names != ["base"]:
            raise ValueError("Base offset sensor includes unexpected bodies")
        base_shapes = rigid_shape_data(base.body_physx_view)
        box_shapes = rigid_shape_data(env.unwrapped.scene["box"].root_physx_view)

        ground_query = {"status": "not_available", "offsets": None}
        try:
            simulation_view = tensors.create_simulation_view("torch")
            ground_view = simulation_view.create_rigid_body_view(GROUND)
            if ground_view.count == 1 and ground_view.max_shapes >= 1:
                ground_query = {"status": "rigid_body_view_available",
                                "offsets": rigid_shape_data(ground_view)}
            else:
                ground_query = {"status": "no_rigid_body_view",
                                "body_count": ground_view.count,
                                "max_shapes": ground_view.max_shapes,
                                "offsets": None}
        except Exception as error:
            ground_query = {"status": "rigid_body_view_error",
                            "error": f"{type(error).__name__}: {error}", "offsets": None}

        result = {
            "schema_version": 1,
            "scope": "same_loaded_scene_read_only_shape_offset_probe",
            "task": TASK,
            "probe_sha256": sha256(__file__),
            "robot_usd_sha256": sha256(usd_path),
            "base_shapes": base_shapes,
            "box_shapes": box_shapes,
            "ground_prim": GROUND,
            "ground_prim_type": ground.GetTypeName(),
            "ground_authored_offsets": authored_offsets(ground),
            "ground_usd_physics_material_path": (
                str(material.GetPrim().GetPath()) if material and material.GetPrim().IsValid()
                else None
            ),
            "ground_usd_binding_prim": (
                str(binding.GetPrim().GetPath()) if binding else None
            ),
            "ground_physx_rigid_view_query": ground_query,
            "physics_dt_s": float(config.sim.dt),
            "control_decimation": int(config.decimation),
            "policy_loaded": False,
            "rollout_executed": False,
            "scene_contract_sha256": None,
            "entry_distribution_sha256": None,
            "contact_authorized": False,
        }
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        with args.output_json.open("x", encoding="utf-8") as output:
            json.dump(result, output, indent=2, allow_nan=False)
            output.write("\n")
        print("SCENE_SHAPE_OFFSET_PROBE=" + str(args.output_json), flush=True)
    finally:
        env.close()


try:
    main()
finally:
    launcher.app.close()
