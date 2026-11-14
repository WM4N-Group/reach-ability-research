"""Compare live PhysX base ray hits with a diagnostic cooked convex at rest."""

import argparse
import hashlib
import json
from pathlib import Path

from isaaclab.app import AppLauncher


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--cooked-report", type=Path, required=True)
parser.add_argument("--manifold-report", type=Path, action="append", required=True)
parser.add_argument("--output-json", type=Path, required=True)
AppLauncher.add_app_launcher_args(parser)
args = parser.parse_args()
if args.output_json.exists():
    parser.error("Output already exists")
launcher = AppLauncher(args)

import gymnasium as gym
import numpy as np
import omni.physx
import omni.usd
from pxr import Gf, UsdGeom
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation

import LeggedManip_Lab.tasks  # noqa: F401
from isaaclab_tasks.utils import load_cfg_from_registry

from analyze_piper_base_contact_surface_alignment import lower_surface_at_xy, norm


TASK = "GO2-PIPER-Box-Push-Tracking-Play"


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def first_loaded_contact(report):
    threshold = report["base_contact_substep_contract"]["threshold_n"]
    event = next((row for row in report["base_contact_substeps"]
                  if norm(row["net_force_w"]) > threshold), None)
    if event is None or not report["terminal"]["reasons"]["base_contact"]:
        raise ValueError("Expected a known terminal base contact")
    point = next((point for point in event["contact_manifold"]["ground"]
                  if point["normal_force_n"] > threshold), None)
    if point is None:
        raise ValueError("Expected a loaded ground contact point")
    return event, point


def raycast_all(origin, length):
    hits = []

    def on_hit(hit):
        hits.append({
            "collision": hit.collision,
            "rigid_body": hit.rigid_body,
            "position_w": [float(hit.position.x), float(hit.position.y), float(hit.position.z)],
            "normal_w": [float(hit.normal.x), float(hit.normal.y), float(hit.normal.z)],
            "distance_m": float(hit.distance),
        })
        return True

    found = omni.physx.get_physx_scene_query_interface().raycast_all(
        Gf.Vec3f(*origin), Gf.Vec3f(0.0, 0.0, 1.0), length, on_hit, True)
    return bool(found), hits


def stage_base_pose():
    stage = omni.usd.get_context().get_stage()
    base = stage.GetPrimAtPath("/World/envs/env_0/Robot/base")
    matrix = UsdGeom.XformCache().GetLocalToWorldTransform(base)
    position = matrix.ExtractTranslation()
    quaternion = matrix.ExtractRotationQuat()
    return np.asarray([position[0], position[1], position[2]], dtype=float), np.asarray(
        [quaternion.GetReal(), *quaternion.GetImaginary()], dtype=float)


def probe_samples(paths, base_pos, base_quat, vertices, hull):
    rotation = Rotation.from_quat(base_quat, scalar_first=True)
    vertices_w = rotation.apply(vertices) + base_pos
    normals_w = rotation.apply(hull.equations[:, :3])
    samples = []
    for path in paths:
        report = json.loads(path.read_text(encoding="utf-8"))
        event, point = first_loaded_contact(report)
        event_rotation = Rotation.from_quat(event["base_quat"], scalar_first=True)
        point_local = event_rotation.inv().apply(
            np.asarray(point["point_w"], dtype=float) - np.asarray(event["base_pos"], dtype=float))
        current_xy = rotation.apply([point_local[0], point_local[1], 0.0])[:2] + base_pos[:2]
        origin = [float(current_xy[0]), float(current_xy[1]), float(base_pos[2] - 0.7)]
        found, hits = raycast_all(origin, 1.4)
        base_hits = [hit for hit in hits if hit["rigid_body"] == "/World/envs/env_0/Robot/base"]
        cooked_height = lower_surface_at_xy(vertices_w, hull.simplices, normals_w, current_xy)
        samples.append({
            "seed_source": report["seed"],
            "manifold_report_sha256": sha256(path),
            "event_contact_point_local": point_local.tolist(),
            "ray_origin_w": origin,
            "ray_length_m": 1.4,
            "scene_query_found": found,
            "hits": hits,
            "base_hits": base_hits,
            "diagnostic_cooked_lower_surface_m": cooked_height,
        })
    return samples


def main():
    cooked = json.loads(args.cooked_report.read_text(encoding="utf-8"))
    if (cooked["scope"] != "read_only_rollout_in_memory_clone_cooking_diagnostic"
            or len(cooked["convexes"]) != 1):
        raise ValueError("Unexpected diagnostic cooked convex report")
    vertices = np.asarray(cooked["convexes"][0]["vertices"], dtype=float)
    hull = ConvexHull(vertices)
    config = load_cfg_from_registry(TASK, "env_cfg_entry_point")
    config.scene.num_envs = 1
    config.sim.device = args.device
    config.sim.enable_scene_query_support = True
    config.observations.policy.enable_corruption = False
    usd_path = Path(config.scene.robot.spawn.usd_path)
    if sha256(usd_path) != cooked["usd_sha256"]:
        raise ValueError("Loaded robot USD differs from cooked input")
    env = gym.make(TASK, cfg=config)
    try:
        robot = env.unwrapped.scene["robot"]
        base_ids, names = robot.find_bodies("^base$")
        if len(base_ids) != 1 or names != ["base"]:
            raise RuntimeError("Expected one base rigid body")
        def snapshot():
            base_pos = np.asarray(robot.data.body_pos_w[0, base_ids[0]].tolist(), dtype=float)
            base_quat = np.asarray(robot.data.body_quat_w[0, base_ids[0]].tolist(), dtype=float)
            usd_pos, usd_quat = stage_base_pose()
            return {
                "base_pos_w": base_pos.tolist(),
                "base_quat_wxyz": base_quat.tolist(),
                "usd_stage_base_pos_w": usd_pos.tolist(),
                "usd_stage_base_quat_wxyz": usd_quat.tolist(),
                "samples_at_tensor_pose": probe_samples(
                    args.manifold_report, base_pos, base_quat, vertices, hull),
                "samples_at_usd_pose": probe_samples(
                    args.manifold_report, usd_pos, usd_quat, vertices, hull),
            }

        before_step = snapshot()
        env.unwrapped.sim.step(render=False)
        robot.update(config.sim.dt)
        after_step = snapshot()
        omni.physx.get_physx_interface().update_transformations(True, True)
        after_writeback = snapshot()
        result = {
            "schema_version": 3,
            "scope": "diagnostic_physx_scene_raycast_before_after_one_step_and_writeback",
            "task": TASK,
            "scene_query_support_enabled_for_diagnostic": True,
            "usd_sha256": sha256(usd_path),
            "cooked_report_sha256": sha256(args.cooked_report),
            "probe_sha256": sha256(__file__),
            "before_step": before_step,
            "after_one_physics_step": after_step,
            "after_physx_transform_writeback": after_writeback,
            "physics_steps_executed": 1,
            "policy_loaded": False,
            "policy_rollout_executed": False,
            "contact_authorized": False,
        }
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        with args.output_json.open("x", encoding="utf-8") as output:
            json.dump(result, output, indent=2, allow_nan=False)
            output.write("\n")
        print("BASE_SCENE_RAYCAST_PROBE=" + str(args.output_json), flush=True)
    finally:
        env.close()


try:
    main()
finally:
    launcher.app.close()
