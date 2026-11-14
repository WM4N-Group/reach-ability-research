"""Focused checks for optional same-run scene observation capture."""

import sys
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from piper_scene_runtime_observation import canonical_sha256, config_value, observe


class Prim:
    def __init__(self, path, valid=True, collision=False, children=(), proxy=False):
        self.path = path
        self.valid = valid
        self.collision = collision
        self.children = children
        self.proxy = proxy

    def IsValid(self):
        return self.valid

    def GetPath(self):
        return self.path

    def GetTypeName(self):
        return "Mesh"

    def GetAppliedSchemas(self):
        return ["PhysicsCollisionAPI"] if self.collision else []

    def GetFilteredChildren(self, predicate):
        return self.children

    def IsInstanceProxy(self):
        return self.proxy


class Stage:
    def __init__(self, layer_path, ground=True):
        self.layer_path = layer_path
        self.ground = ground

    def GetUsedLayers(self):
        return [SimpleNamespace(identifier=str(self.layer_path), realPath=str(self.layer_path),
                                anonymous=False),
                SimpleNamespace(identifier="remote:test.usd", realPath="", anonymous=False,
                                ExportToString=lambda: "#usda 1.0\n")]

    def ExportToString(self):
        return "#usda 1.0\n"

    def GetPrimAtPath(self, path):
        if path == "/World/envs/env_0/Robot":
            return Prim(path, children=[Prim(path + "/base/collision", collision=True, proxy=True)])
        if path == "/World/envs/env_0/Box":
            return Prim(path, children=[Prim(path + "/shape", collision=True)])
        if path == "/World/ground/collision":
            return Prim(path, valid=self.ground, collision=True)
        return Prim(path, collision=path == "/World/envs/env_0/Robot/base/collisions/base/Scene")


class Tensor:
    def __init__(self, value):
        self.value = value

    def flatten(self):
        return self

    def tolist(self):
        return self.value


class RuntimeObservationChecks(unittest.TestCase):
    def setUp(self):
        material_prim = SimpleNamespace(
            IsValid=lambda: True, GetPath=lambda: "/World/ground/material",
            GetAttributes=lambda: [SimpleNamespace(GetName=lambda: "physics:staticFriction",
                                                   Get=lambda: 1.0)])
        bound = SimpleNamespace(GetPrim=lambda: material_prim)
        binding = SimpleNamespace(GetPrim=lambda: SimpleNamespace(
            GetPath=lambda: "/World/ground/collision"))

        def compute_bound_material(purpose):
            self.assertEqual(purpose, "physics")
            return bound, binding

        usd_shade = SimpleNamespace(MaterialBindingAPI=lambda prim: SimpleNamespace(
            ComputeBoundMaterial=compute_bound_material))
        modules = {"pxr": SimpleNamespace(Usd=SimpleNamespace(
            TraverseInstanceProxies=lambda: "instance_proxies"), UsdShade=usd_shade)}
        self.pxr_patch = patch.dict(sys.modules, modules)
        self.pxr_patch.start()
        self.addCleanup(self.pxr_patch.stop)

    def test_config_values_are_structured_and_unknown_types_refused(self):
        @dataclass
        class Settings:
            threshold: float
            ranges: tuple

        self.assertEqual(config_value(Settings(0.5, (0.1, 0.2))),
                         {"threshold": 0.5, "ranges": [0.1, 0.2]})
        self.assertEqual(config_value(canonical_sha256),
                         {"callable": "piper_scene_runtime_observation.canonical_sha256"})
        with self.assertRaisesRegex(TypeError, "Unsupported scene configuration"):
            config_value(object())

    def test_same_run_observation_is_hashed_and_not_certified(self):
        with tempfile.TemporaryDirectory() as temp:
            usd = Path(temp) / "robot.usd"
            usd.write_bytes(b"robot")
            source = Path(temp) / "control.py"
            source.write_bytes(b"control")
            material = {"static_friction": 1.0, "dynamic_friction": 1.0, "restitution": 0.0}
            box_spawn = SimpleNamespace(mass_props={"mass": 5.0},
                                        collision_props={"contact_offset": 0.002},
                                        physics_material={"static_friction": 0.4})
            config = SimpleNamespace(
                scene=SimpleNamespace(
                    robot=SimpleNamespace(spawn=SimpleNamespace(
                        usd_path=str(usd), articulation_props={"solver_position_iteration_count": 8})),
                    box=SimpleNamespace(spawn=box_spawn, init_state=SimpleNamespace(pos=(1.1, 0, 0.1))),
                    terrain=SimpleNamespace(physics_material=material, terrain_type="plane"),
                    contact_forces=SimpleNamespace(history_length=3, update_period=0.005)),
                sim=SimpleNamespace(dt=0.005, physx={"solver_type": 1}),
                events=SimpleNamespace(
                    reset_base=SimpleNamespace(params={"pose_range": {"x": (-0.03, 0.03)}}),
                    reset_robot_joints=SimpleNamespace(params={"position_range": (0.95, 1.05),
                                                               "velocity_range": (0, 0)}),
                    reset_box=SimpleNamespace(func=canonical_sha256),
                    physics_material=SimpleNamespace(params={
                        "static_friction_range": (0.5, 1.2),
                        "dynamic_friction_range": (0.5, 1.2),
                        "restitution_range": (0.0, 0.1),
                        "num_buckets": 64, "make_consistent": True})),
                terminations=SimpleNamespace(
                    base_contact=SimpleNamespace(params={"threshold": 0.5}),
                    arm_body_clearance=SimpleNamespace(params={"min_distance": 0.08})),
                actions=SimpleNamespace(joint_pos=SimpleNamespace(
                    safe_approach_waypoints=((0.0,) * 6,),
                    safe_approach_position_tolerance=0.04,
                    safe_approach_velocity_tolerance=0.12)),
                decimation=4, box_size=(1.2, 1.2, 0.2))
            physx = SimpleNamespace(get_masses=lambda: Tensor([5.0]),
                                    get_material_properties=lambda: Tensor([[[0.4, 0.4, 0.0]]]))
            base = SimpleNamespace(scene={"box": SimpleNamespace(root_physx_view=physx),
                                          "robot": SimpleNamespace(root_physx_view=physx)},
                                   termination_manager=SimpleNamespace(active_terms=["base_contact"]),
                                   step_dt=0.02)
            stage = Stage(usd)
            observed = observe(stage, config, base, 5901, "/World/ground/collision",
                               {"control": source})
            self.assertEqual(observed["scope"], "same_rollout_runtime_observation_only")
            self.assertEqual(observed["box_mass_kg"], [5.0])
            self.assertEqual(observed["reset_cfg"]["joint_position_range"], [0.95, 1.05])
            self.assertEqual(observed["safety_cfg"]["base_contact_threshold_n"], 0.5)
            self.assertEqual(len(observed["collision_prims"]), 4)
            self.assertTrue(observed["collision_prims"][1]["instance_proxy"])
            self.assertEqual(observed["ground_usd_material"]["material_attributes"],
                             {"physics:staticFriction": 1.0})
            self.assertEqual(observed["scene_contract_sha256"], None)
            self.assertEqual(observed["entry_distribution_sha256"], None)
            self.assertEqual(observed["used_layers"][1]["kind"], "loaded_nonfile")
            self.assertFalse(observed["unresolved_layers"])
            self.assertEqual(canonical_sha256(observed), canonical_sha256(dict(observed)))
            with self.assertRaisesRegex(ValueError, "Required scene prim missing"):
                observe(Stage(usd, ground=False), config, base, 5901,
                        "/World/ground/collision", {"control": source})
            base.step_dt = 0.01
            with self.assertRaisesRegex(ValueError, "Physics and control grids differ"):
                observe(stage, config, base, 5901, "/World/ground/collision", {"control": source})


if __name__ == "__main__":
    unittest.main()
