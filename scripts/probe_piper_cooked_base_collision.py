"""Read the loaded base mesh's PhysX convex representation without a rollout."""

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
import omni.physx
import omni.usd
from pxr import PhysicsSchemaTools, Usd, UsdGeom, UsdPhysics, UsdUtils

import LeggedManip_Lab.tasks  # noqa: F401
from isaaclab_tasks.utils import load_cfg_from_registry
from omni.physx.bindings._physx import PhysxCollisionRepresentationResult


TASK = "GO2-PIPER-Box-Push-Tracking-Play"


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def attributes(prim):
    return {attr.GetName(): str(attr.Get()) for attr in prim.GetAttributes()
            if any(word in attr.GetName().lower()
                   for word in ("contactoffset", "restoffset", "approximation", "height", "scale"))}


def main():
    config = load_cfg_from_registry(TASK, "env_cfg_entry_point")
    config.scene.num_envs = 1
    config.sim.device = args.device
    config.observations.policy.enable_corruption = False
    usd_path = Path(config.scene.robot.spawn.usd_path)
    env = gym.make(TASK, cfg=config)
    try:
        stage = omni.usd.get_context().get_stage()
        collision_owners = [prim for prim in Usd.PrimRange(stage.GetPseudoRoot(), Usd.TraverseInstanceProxies())
                            if str(prim.GetPath()).startswith("/World/envs/env_0/Robot/base/")
                            and prim.HasAPI(UsdPhysics.MeshCollisionAPI)
                            and prim.HasAPI(UsdPhysics.CollisionAPI)]
        if len(collision_owners) != 1:
            raise RuntimeError(f"Expected one base collision owner, found {len(collision_owners)}")
        collision_owner = collision_owners[0]
        meshes = [prim for prim in Usd.PrimRange(collision_owner, Usd.TraverseInstanceProxies())
                  if prim.IsA(UsdGeom.Mesh)]
        if len(meshes) != 1:
            raise RuntimeError(f"Expected one mesh below base collision owner, found {len(meshes)}")
        base_mesh = meshes[0]
        source_mesh = UsdGeom.Mesh(base_mesh)
        cook_stage = Usd.Stage.CreateInMemory()
        cook_mesh = UsdGeom.Mesh.Define(cook_stage, "/DiagnosticBaseMesh")
        cook_mesh.CreatePointsAttr(source_mesh.GetPointsAttr().Get())
        cook_mesh.CreateFaceVertexCountsAttr(source_mesh.GetFaceVertexCountsAttr().Get())
        cook_mesh.CreateFaceVertexIndicesAttr(source_mesh.GetFaceVertexIndicesAttr().Get())
        UsdPhysics.CollisionAPI.Apply(cook_mesh.GetPrim())
        UsdPhysics.MeshCollisionAPI.Apply(cook_mesh.GetPrim()).CreateApproximationAttr().Set(
            UsdPhysics.Tokens.convexHull)
        result_holder = []

        def on_result(status, convexes):
            result_holder.append((status, convexes))

        omni.physx.get_physx_cooking_interface().request_convex_collision_representation(
            stage_id=UsdUtils.StageCache.Get().Insert(cook_stage).ToLongInt(),
            collision_prim_id=PhysicsSchemaTools.sdfPathToInt(cook_mesh.GetPath()),
            run_asynchronously=False,
            on_result=on_result,
        )
        if len(result_holder) != 1 or result_holder[0][0] != PhysxCollisionRepresentationResult.RESULT_VALID:
            raise RuntimeError(f"PhysX cooking did not return a valid result: {result_holder}")
        convexes = result_holder[0][1]
        if len(convexes) != 1:
            raise RuntimeError(f"Expected one cooked base convex, found {len(convexes)}")
        ground = [prim for prim in Usd.PrimRange(stage.GetPseudoRoot(), Usd.TraverseInstanceProxies())
                  if str(prim.GetPath()).startswith("/World/ground")
                  and prim.HasAPI(UsdPhysics.CollisionAPI)]
        if not ground:
            raise RuntimeError("No ground collision prim")
        result = {
            "schema_version": 1,
            "scope": "read_only_rollout_in_memory_clone_cooking_diagnostic",
            "task": TASK,
            "usd_sha256": sha256(usd_path),
            "probe_sha256": sha256(__file__),
            "base_collision_owner_path": str(collision_owner.GetPath()),
            "base_collision_owner_applied_schemas": list(collision_owner.GetAppliedSchemas()),
            "base_collision_owner_attributes": attributes(collision_owner),
            "base_mesh_path": str(base_mesh.GetPath()),
            "cooking_input": "loaded_mesh_points_and_faces_copied_to_in_memory_stage",
            "convexes": [{
                "vertices": [[float(v.x), float(v.y), float(v.z)] for v in convex.vertices],
                "indices": list(convex.indices),
                "polygons": [{"index_base": face.index_base,
                              "num_vertices": face.num_vertices,
                              "plane": [float(value) for value in face.plane]}
                             for face in convex.polygons],
            } for convex in convexes],
            "ground_collision_prims": [{
                "path": str(prim.GetPath()),
                "kind": prim.GetTypeName(),
                "applied_schemas": list(prim.GetAppliedSchemas()),
                "attributes": attributes(prim),
            } for prim in ground],
            "policy_loaded": False,
            "rollout_executed": False,
            "contact_authorized": False,
        }
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        with args.output_json.open("x", encoding="utf-8") as output:
            json.dump(result, output, indent=2, allow_nan=False)
            output.write("\n")
        print("COOKED_BASE_COLLISION_PROBE=" + str(args.output_json), flush=True)
    finally:
        env.close()


try:
    main()
finally:
    launcher.app.close()
