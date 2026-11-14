"""Read-only WBC and PUSH control-contract comparison in the active Isaac tree."""

import argparse
import hashlib
import json
from pathlib import Path

from isaaclab.app import AppLauncher


parser = argparse.ArgumentParser()
parser.add_argument("--wbc-policy", type=Path, required=True)
parser.add_argument("--output-json", type=Path, required=True)
AppLauncher.add_app_launcher_args(parser)
args = parser.parse_args()
if args.output_json.exists():
    parser.error("Output already exists")
launcher = AppLauncher(args)

import torch

import LeggedManip_Lab.tasks  # noqa: F401
from isaaclab_tasks.utils import load_cfg_from_registry


EXPECTED_WBC_SHA256 = "c5f57c79bc01d8b8f2c0846163b149e3f53de39291770a1ccb230ef3be6b800e"
OBSERVATION_TERMS = (
    "base_ang_vel", "projected_gravity", "joint_pos", "joint_vel", "actions",
    "velocity_commands", "pos_commands",
)
ACTUATOR_FIELDS = (
    "joint_names_expr", "stiffness", "damping", "armature", "min_delay", "max_delay",
    "friction", "effort_limit", "effort_limit_sim", "velocity_limit", "velocity_limit_sim",
)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def plain(value):
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (list, tuple)):
        return [plain(item) for item in value]
    if isinstance(value, dict):
        return {str(key): plain(item) for key, item in value.items()}
    return repr(value)


def describe(cfg):
    policy = cfg.observations.policy
    robot = cfg.scene.robot
    action = cfg.actions.joint_pos
    return {
        "observation_history_length": policy.history_length,
        "observation_terms": [
            {
                "name": name,
                "function": f"{getattr(policy, name).func.__module__}.{getattr(policy, name).func.__qualname__}",
            }
            for name in OBSERVATION_TERMS
        ],
        "action_class": f"{action.class_type.__module__}.{action.class_type.__qualname__}",
        "action_joint_names": plain(action.joint_names),
        "action_scale": plain(action.scale),
        "action_clip": plain(action.clip),
        "robot_initial_pos": plain(robot.init_state.pos),
        "robot_initial_joint_pos": plain(robot.init_state.joint_pos),
        "self_collisions_enabled": robot.spawn.articulation_props.enabled_self_collisions,
        "solver_position_iterations": robot.spawn.articulation_props.solver_position_iteration_count,
        "solver_velocity_iterations": robot.spawn.articulation_props.solver_velocity_iteration_count,
        "actuators": {
            name: {field: plain(getattr(actuator, field, None)) for field in ACTUATOR_FIELDS}
            for name, actuator in robot.actuators.items()
        },
    }


def main():
    policy_hash = sha256(args.wbc_policy)
    if policy_hash != EXPECTED_WBC_SHA256:
        raise RuntimeError(f"Unexpected WBC policy hash: {policy_hash}")
    wbc = load_cfg_from_registry("GO2-PIPER-WBC-Play", "env_cfg_entry_point")
    push = load_cfg_from_registry("GO2-PIPER-Box-Push-Tracking-Play", "env_cfg_entry_point")
    actor = torch.jit.load(str(args.wbc_policy), map_location="cpu").eval()
    with torch.inference_mode():
        output = actor(torch.zeros(1, 210))
    if output.shape != (1, 18) or not bool(torch.isfinite(output).all()):
        raise RuntimeError("WBC actor failed the finite 210-to-18 shape check")
    result = {
        "schema_version": 1,
        "purpose": "Static source-contract comparison; no simulation rollout or control qualification",
        "wbc_policy_sha256": policy_hash,
        "wbc_zero_input_output_shape": list(output.shape),
        "wbc_zero_input_output_max_abs": float(output.abs().amax()),
        "wbc_task": describe(wbc),
        "push_task": describe(push),
    }
    result["matching_fields"] = {
        field: result["wbc_task"][field] == result["push_task"][field]
        for field in ("observation_history_length", "observation_terms", "action_joint_names",
                      "action_scale", "action_clip", "robot_initial_joint_pos",
                      "self_collisions_enabled", "solver_position_iterations",
                      "solver_velocity_iterations", "actuators")
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
    print(f"WBC_PUSH_CONTRACT={args.output_json}", flush=True)


try:
    main()
finally:
    launcher.app.close()
