"""Minimal PIPER NAV scenes with provenance-visible reachability objects."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import mujoco
import numpy as np
import yaml

from ..locomotion_runtime import LocomotionRuntime
from ..piper_locomotion_runtime import DEPLOY, JOINT_NAMES, ROOT
from ..piper_robot_profile import PROFILE_PATH, apply_piper_robot_profile


STATIC_BOX_BODY = "reachability_box"
STATIC_BOX_GEOMETRY = "reachability_box"


def make_static_box_navigation_runtime(
    *,
    seed: int,
    box_position: np.ndarray,
    box_size: np.ndarray,
    box_yaw: float,
    config_path: Path = DEPLOY / "config.yaml",
    profile_path: Path = PROFILE_PATH,
    physics_substeps: int = 1,
) -> LocomotionRuntime:
    """Build an initialized PIPER NAV runtime with one static scene box.

    The box is an immutable MuJoCo world object, not a PUSH task object. The
    function copies PIPER's published initialization contract and only extends
    the scene geometry needed for reachability shadow checks.
    """
    return _make_box_navigation_runtime(
        seed=seed, box_position=box_position, box_size=box_size, box_yaw=box_yaw,
        config_path=config_path, profile_path=profile_path,
        physics_substeps=physics_substeps, box_mass=None,
    )


def make_movable_box_navigation_runtime(
    *,
    seed: int,
    box_position: np.ndarray,
    box_size: np.ndarray,
    box_yaw: float,
    box_mass: float = 1.0,
    config_path: Path = DEPLOY / "config.yaml",
    profile_path: Path = PROFILE_PATH,
    physics_substeps: int = 1,
) -> LocomotionRuntime:
    """Build the same NAV robot with one free box, without a PUSH controller."""
    if not np.isfinite(box_mass) or box_mass <= 0.0:
        raise ValueError("box_mass must be finite and positive")
    return _make_box_navigation_runtime(
        seed=seed, box_position=box_position, box_size=box_size, box_yaw=box_yaw,
        config_path=config_path, profile_path=profile_path,
        physics_substeps=physics_substeps, box_mass=float(box_mass),
    )


def _make_box_navigation_runtime(
    *, seed: int, box_position: np.ndarray, box_size: np.ndarray, box_yaw: float,
    config_path: Path, profile_path: Path, physics_substeps: int,
    box_mass: float | None,
) -> LocomotionRuntime:
    if seed < 0:
        raise ValueError("seed must be non-negative")
    position = _vector(box_position, "box_position")
    size = _vector(box_size, "box_size")
    if np.any(size <= 0.0) or not np.isfinite(box_yaw):
        raise ValueError("box_size must be positive and box_yaw must be finite")
    config_path = Path(config_path).resolve()
    with config_path.open() as source:
        config = yaml.safe_load(source)
    policy_path = Path(config["policy_path"].replace("{CURRENT_ROOT_DIR}", str(ROOT)))
    scene_path = Path(config["xml_path"].replace("{CURRENT_ROOT_DIR}", str(ROOT)))
    specification = mujoco.MjSpec.from_file(str(scene_path))
    apply_piper_robot_profile(specification, profile_path)
    box = specification.worldbody.add_body(name=STATIC_BOX_BODY, pos=position)
    if box_mass is not None:
        box.add_freejoint(name="reachability_box_joint")
    geometry = box.add_geom(
        name=STATIC_BOX_GEOMETRY,
        type=mujoco.mjtGeom.mjGEOM_BOX,
        size=size / 2.0,
        quat=[np.cos(box_yaw / 2.0), 0.0, 0.0, np.sin(box_yaw / 2.0)],
        contype=1,
        conaffinity=1,
        friction=[0.6, 0.0, 0.0],
        condim=3,
    )
    if box_mass is not None:
        geometry.mass = box_mass
    model = specification.compile()
    data = mujoco.MjData(model)
    base_id = model.body("base_link").id
    root_joint = int(model.body_jntadr[base_id])
    if root_joint < 0 or model.jnt_type[root_joint] != mujoco.mjtJoint.mjJNT_FREE:
        raise ValueError("PIPER base_link must have a free joint")
    root_qpos = int(model.jnt_qposadr[root_joint])
    joint_ids = np.array([model.joint(name).id for name in JOINT_NAMES])
    if not np.array_equal(model.actuator_trnid[:, 0], joint_ids):
        raise ValueError("PIPER actuator/joint mapping does not match the configuration")
    generator = np.random.default_rng(seed)
    yaw = generator.uniform(-0.15, 0.15)
    data.qpos[root_qpos : root_qpos + 3] = [0.0, 0.0, 0.35]
    data.qpos[root_qpos + 3 : root_qpos + 7] = [
        np.cos(yaw / 2.0),
        0.0,
        0.0,
        np.sin(yaw / 2.0),
    ]
    angles = np.asarray(config["default_angles"], dtype=np.float64)
    angles += generator.uniform(-0.015, 0.015, 18)
    data.qpos[model.jnt_qposadr[joint_ids]] = np.clip(
        angles,
        model.jnt_range[joint_ids, 0],
        model.jnt_range[joint_ids, 1],
    )
    mujoco.mj_forward(model, data)
    environment = SimpleNamespace(
        model=model,
        data=data,
        deploy_cfg=config,
        robot_joint_id=root_joint,
        robot_qpos_adr=root_qpos,
    )
    runtime = LocomotionRuntime(
        environment,
        policy_path,
        joint_names=JOINT_NAMES,
        base_body_name="base_link",
        physics_substeps=physics_substeps,
    )
    runtime.config_path = config_path
    runtime.policy_path = policy_path
    runtime.scene_path = scene_path
    runtime.profile_path = Path(profile_path).resolve()
    return runtime


def _vector(value: np.ndarray, name: str) -> np.ndarray:
    vector = np.asarray(value, dtype=np.float64)
    if vector.shape != (3,) or not np.isfinite(vector).all():
        raise ValueError(f"{name} must contain three finite values")
    return vector.copy()