"""Inspect the loaded Isaac base collider without policy rollout or training."""

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
import numpy as np
import omni.usd
from pxr import Usd, UsdGeom, UsdPhysics

import LeggedManip_Lab.tasks  # noqa: F401
from isaaclab.sensors import ContactSensorCfg
from isaaclab_tasks.utils import load_cfg_from_registry


TASK = "GO2-PIPER-Box-Push-Tracking-Play"


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def collision_owner(prim):
    owner = prim
    while owner.IsValid() and not owner.HasAPI(UsdPhysics.CollisionAPI):
        owner = owner.GetParent()
    return owner if owner.IsValid() else None


def relevant_attributes(prim):
    return {
        attribute.GetName(): str(attribute.Get())
        for attribute in prim.GetAttributes()
        if any(term in attribute.GetName().lower()
               for term in ("contactoffset", "restoffset", "approximation"))
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
        candidates = [
            prim for prim in Usd.PrimRange(stage.GetPseudoRoot(), Usd.TraverseInstanceProxies())
            if str(prim.GetPath()).endswith("/Robot/base")
            and prim.HasAPI(UsdPhysics.RigidBodyAPI)
        ]
        if len(candidates) != 1:
            raise RuntimeError(f"Expected one loaded base rigid body, found {len(candidates)}")
        base = candidates[0]
        cache = UsdGeom.XformCache()
        colliders = []
        for prim in Usd.PrimRange(base, Usd.TraverseInstanceProxies()):
            if prim.GetTypeName() not in ("Mesh", "Cube", "Sphere", "Capsule", "Cylinder"):
                continue
            owner = collision_owner(prim)
            if owner is None or not bool(UsdPhysics.CollisionAPI(owner).GetCollisionEnabledAttr().Get()):
                continue
            item = {
                "path": str(prim.GetPath()),
                "kind": prim.GetTypeName(),
                "collision_owner": str(owner.GetPath()),
                "owner_schemas": list(owner.GetAppliedSchemas()),
                "relative_transform_to_base": np.asarray(
                    cache.ComputeRelativeTransform(prim, base)[0], dtype=float).tolist(),
                "owner_contact_attributes": relevant_attributes(owner),
                "shape_contact_attributes": relevant_attributes(prim),
            }
            if prim.IsA(UsdGeom.Mesh):
                points = np.asarray(UsdGeom.Mesh(prim).GetPointsAttr().Get(), dtype=float)
                item["point_count"] = len(points)
                item["local_point_min"] = points.min(axis=0).tolist()
                item["local_point_max"] = points.max(axis=0).tolist()
                item["mesh_approximation"] = str(
                    UsdPhysics.MeshCollisionAPI(owner).GetApproximationAttr().Get())
            colliders.append(item)
        ground = [
            str(prim.GetPath())
            for prim in Usd.PrimRange(stage.GetPseudoRoot(), Usd.TraverseInstanceProxies())
            if str(prim.GetPath()).startswith("/World/ground")
            and prim.HasAPI(UsdPhysics.CollisionAPI)
        ]
        if not colliders or not ground:
            raise RuntimeError("Missing loaded base or ground collision prim")
        sensor = config.scene.contact_forces
        base_sensor = env.unwrapped.scene["diagnostic_base_offset"]
        if base_sensor.body_names != ["base"]:
            raise RuntimeError("Offset view must contain only the base rigid body")
        base_view = base_sensor.body_physx_view
        base_contact_offsets = base_view.get_contact_offsets()
        base_rest_offsets = base_view.get_rest_offsets()
        if base_contact_offsets.shape != base_rest_offsets.shape:
            raise RuntimeError("Base contact/rest offset shape mismatch")
        robot = env.unwrapped.scene["robot"]
        base_body_ids, base_body_names = robot.find_bodies("^base$")
        if len(base_body_ids) != 1 or base_body_names != ["base"]:
            raise RuntimeError("Expected one articulation base body")
        base_body_id = base_body_ids[0]
        termination = config.terminations.base_contact
        result = {
            "schema_version": 1,
            "scope": "read_only_loaded_isaac_collision_prim_probe",
            "task": TASK,
            "usd_sha256": sha256(usd_path),
            "usd_path": str(usd_path),
            "base_prim": str(base.GetPath()),
            "base_colliders": colliders,
            "base_physx_view_prim_paths": list(base_view.prim_paths),
            "base_physx_contact_offsets_m": base_contact_offsets.tolist(),
            "base_physx_rest_offsets_m": base_rest_offsets.tolist(),
            "articulation_root_body_name": robot.body_names[0],
            "base_body_index": base_body_id,
            "articulation_root_pos_w": robot.data.root_pos_w[0].tolist(),
            "articulation_root_quat_w": robot.data.root_quat_w[0].tolist(),
            "base_body_pos_w": robot.data.body_pos_w[0, base_body_id].tolist(),
            "base_body_quat_w": robot.data.body_quat_w[0, base_body_id].tolist(),
            "ground_collision_prims": ground,
            "contact_sensor_prim_path": sensor.prim_path,
            "contact_sensor_history_length": sensor.history_length,
            "contact_sensor_update_period_s": sensor.update_period,
            "lazy_sensor_update": config.scene.lazy_sensor_update,
            "base_contact_threshold_n": termination.params["threshold"],
            "physics_dt_s": config.sim.dt,
            "control_decimation": config.decimation,
            "policy_loaded": False,
            "rollout_executed": False,
            "contact_authorized": False,
        }
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        with args.output_json.open("x", encoding="utf-8") as stream:
            json.dump(result, stream, indent=2, allow_nan=False)
            stream.write("\n")
        print("BASE_COLLISION_PROBE=" + str(args.output_json), flush=True)
    finally:
        env.close()


try:
    main()
finally:
    launcher.app.close()
