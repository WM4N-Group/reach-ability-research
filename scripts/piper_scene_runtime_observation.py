"""Capture same-run Isaac scene facts without treating them as a scene certificate."""

import hashlib
import json
from dataclasses import fields, is_dataclass
from enum import Enum
from pathlib import Path


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def canonical_sha256(value):
    return sha256_bytes(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                   allow_nan=False).encode("utf-8"))


def config_value(value):
    if is_dataclass(value):
        return {field.name: config_value(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, dict):
        return {key: config_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [config_value(item) for item in value]
    if isinstance(value, Enum):
        return {"enum": f"{type(value).__module__}.{type(value).__qualname__}.{value.name}"}
    if isinstance(value, Path):
        return str(value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if callable(value):
        module = getattr(value, "__module__", None)
        name = getattr(value, "__qualname__", None)
        if module and name and "<locals>" not in name:
            return {"callable": f"{module}.{name}"}
    raise TypeError(f"Unsupported scene configuration value: {type(value).__name__}")


def loaded_layers(stage):
    layers = []
    for layer in stage.GetUsedLayers():
        path = Path(layer.realPath) if layer.realPath else None
        if path is not None and path.is_file():
            layers.append({"identifier": layer.identifier, "kind": "file",
                           "sha256": sha256_bytes(path.read_bytes())})
        else:
            content = layer.ExportToString()
            layers.append({"identifier": layer.identifier,
                           "kind": "anonymous" if layer.anonymous else "loaded_nonfile",
                           "sha256": sha256_bytes(content.encode("utf-8")) if content else None})
    return sorted(layers, key=lambda item: item["identifier"])


def scene_prims(stage, ground_prim):
    from pxr import Usd

    roots = ("/World/envs/env_0/Robot", "/World/envs/env_0/Box", ground_prim)
    for path in roots:
        if not stage.GetPrimAtPath(path).IsValid():
            raise ValueError(f"Required scene prim missing: {path}")
    collision = {}
    base_collision = "/World/envs/env_0/Robot/base/collisions/base/Scene"
    pending = [stage.GetPrimAtPath(path) for path in roots]
    while pending:
        prim = pending.pop()
        path = str(prim.GetPath())
        if path == ground_prim or any(path.startswith(root + "/") for root in roots):
            schemas = list(prim.GetAppliedSchemas())
            if "PhysicsCollisionAPI" in schemas:
                collision[path] = {"path": path, "type": prim.GetTypeName(),
                                   "applied_schemas": schemas,
                                   "instance_proxy": bool(prim.IsInstanceProxy())}
        pending.extend(prim.GetFilteredChildren(Usd.TraverseInstanceProxies()))
    prim = stage.GetPrimAtPath(base_collision)
    if prim.IsValid():
        schemas = list(prim.GetAppliedSchemas())
        if "PhysicsCollisionAPI" in schemas:
            collision[base_collision] = {"path": base_collision, "type": prim.GetTypeName(),
                                         "applied_schemas": schemas,
                                         "instance_proxy": bool(prim.IsInstanceProxy())}
    if not collision:
        raise ValueError("No collision prims found in the loaded scene")
    return [collision[path] for path in sorted(collision)]


def ground_usd_material(stage, ground_prim):
    from pxr import UsdShade

    prim = stage.GetPrimAtPath(ground_prim)
    material, binding = UsdShade.MaterialBindingAPI(prim).ComputeBoundMaterial("physics")
    if not material or not material.GetPrim().IsValid():
        return {"material_path": None, "binding_prim": None, "material_attributes": None}
    material_prim = material.GetPrim()
    attributes = {}
    for attribute in material_prim.GetAttributes():
        name = attribute.GetName()
        if name.startswith(("physics:", "physxMaterial:")):
            value = attribute.Get()
            attributes[name] = config_value(value) if value is not None else None
    return {"material_path": str(material_prim.GetPath()),
            "binding_prim": str(binding.GetPrim().GetPath()) if binding else None,
            "material_attributes": attributes}


def observe(stage, config, base, seed, ground_prim, source_paths):
    usd_path = Path(config.scene.robot.spawn.usd_path).resolve()
    if not usd_path.is_file():
        raise ValueError(f"Loaded robot USD missing: {usd_path}")
    stage_text = stage.ExportToString()
    if not stage_text:
        raise ValueError("Loaded USD stage export is empty")
    box = base.scene["box"]
    robot = base.scene["robot"]
    layers = loaded_layers(stage)
    observation = {
        "schema_version": 1,
        "scope": "same_rollout_runtime_observation_only",
        "seed": seed,
        "robot_usd": {"path": str(usd_path), "sha256": sha256_bytes(usd_path.read_bytes())},
        "used_layers": layers,
        "stage_export_sha256": sha256_bytes(stage_text.encode("utf-8")),
        "collision_prims": scene_prims(stage, ground_prim),
        "robot_mass_kg": robot.root_physx_view.get_masses().tolist(),
        "robot_material": robot.root_physx_view.get_material_properties().tolist(),
        "box_mass_kg": box.root_physx_view.get_masses().flatten().tolist(),
        "box_material": box.root_physx_view.get_material_properties().tolist(),
        "box_size_m": list(config.box_size),
        "box_spawn": {
            "mass_props": config_value(config.scene.box.spawn.mass_props),
            "collision_props": config_value(config.scene.box.spawn.collision_props),
            "physics_material": config_value(config.scene.box.spawn.physics_material),
            "initial_position_m": list(config.scene.box.init_state.pos),
        },
        "ground_prim": ground_prim,
        "ground_usd_material": ground_usd_material(stage, ground_prim),
        "ground_cfg": {
            "terrain_type": config.scene.terrain.terrain_type,
            "physics_material": config_value(config.scene.terrain.physics_material),
        },
        "physics_dt_s": float(config.sim.dt),
        "physx_cfg": config_value(config.sim.physx),
        "robot_articulation_cfg": config_value(config.scene.robot.spawn.articulation_props),
        "control_decimation": int(config.decimation),
        "control_dt_s": float(base.step_dt),
        "reset_cfg": {
            "base": config_value(config.events.reset_base.params),
            "joint_position_range": config_value(config.events.reset_robot_joints.params["position_range"]),
            "joint_velocity_range": config_value(config.events.reset_robot_joints.params["velocity_range"]),
            "box_reset_function": (config.events.reset_box.func.__module__ + "."
                                   + config.events.reset_box.func.__qualname__),
            "robot_material_randomization": {
                key: config_value(config.events.physics_material.params[key])
                for key in ("static_friction_range", "dynamic_friction_range",
                            "restitution_range", "num_buckets", "make_consistent")
            } if config.events.physics_material is not None else None,
        },
        "safety_cfg": {
            "base_contact_threshold_n": config.terminations.base_contact.params["threshold"],
            "arm_body_clearance_m": config.terminations.arm_body_clearance.params["min_distance"],
            "active_terms": list(base.termination_manager.active_terms),
            "contact_history_length": config.scene.contact_forces.history_length,
            "contact_update_period_s": config.scene.contact_forces.update_period,
            "safe_approach_waypoints": config_value(config.actions.joint_pos.safe_approach_waypoints),
            "safe_approach_position_tolerance_rad":
                config.actions.joint_pos.safe_approach_position_tolerance,
            "safe_approach_velocity_tolerance_rad_s":
                config.actions.joint_pos.safe_approach_velocity_tolerance,
        },
        "source_sha256": {name: sha256_bytes(Path(path).read_bytes())
                          for name, path in sorted(source_paths.items())},
        "unresolved_layers": any(layer["sha256"] is None for layer in layers),
        "scene_contract_sha256": None,
        "entry_distribution_sha256": None,
    }
    if abs(observation["physics_dt_s"] * observation["control_decimation"]
           - observation["control_dt_s"]) > 1e-9:
        raise ValueError("Physics and control grids differ")
    return observation
