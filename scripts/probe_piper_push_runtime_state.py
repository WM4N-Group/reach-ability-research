"""Inspect the current Isaac PUSH handoff surface for one control step.

Run against the matched sim2real Isaac source on a remote GPU. This is an
interface preflight, not a NAV-to-PUSH evaluation or a PUSH policy rollout.
"""

import argparse
import hashlib
import json
from pathlib import Path

from isaaclab.app import AppLauncher


parser = argparse.ArgumentParser()
parser.add_argument("--output-json", type=Path, required=True)
parser.add_argument("--seed", type=int, default=4802)
AppLauncher.add_app_launcher_args(parser)
args = parser.parse_args()
if args.output_json.exists():
    parser.error("Output file already exists")
launcher = AppLauncher(args)

import gymnasium as gym
import torch

import isaaclab_tasks
from isaaclab_tasks.utils import load_cfg_from_registry
from isaaclab_rl.rsl_rl import RslRlVecEnvWrapper

import LeggedManip_Lab.tasks
from LeggedManip_Lab.tasks.manager_based.leggedmanip_lab.mdp import box_push


TASK = "GO2-PIPER-Box-Push-Tracking-Play"
EXPECTED_CONTROL_SHA256 = {
    "box_push.py": "889a812aa2676b8c0d3d340419af407a64dee67b8d4a07812c1ce0aa74bb1d1d",
    "box_push_ik.py": "6086163efb4d64b5a812cb2cbe506bc82eaafbca6b08186151fab7a1145f9370",
    "box_push_actions.py": "d92f8d006b1f5b74b7603501ec68a38fe88894e151c961fafcfb15adaf92d7c5",
}


def snapshot(base, observation):
    robot = base.scene["robot"]
    box = base.scene["box"]
    term = base.action_manager.get_term("joint_pos")
    controller = term.controller
    origin = base.scene.env_origins[0]
    policy = observation["policy"]
    box_obs = observation["box"]
    if policy.shape != (1, 210) or box_obs.shape != (1, 16):
        raise RuntimeError(f"Unexpected observation dimensions: {policy.shape}, {box_obs.shape}")
    if term.action_dim != 12 or term.joint_commands.shape != (1, 18):
        raise RuntimeError("Unexpected PUSH action dimensions")
    if not torch.isfinite(policy).all() or not torch.isfinite(box_obs).all():
        raise RuntimeError("Non-finite PUSH observation")
    return {
        "episode_steps": int(base.episode_length_buf[0]),
        "episode_seconds": float(base.episode_length_buf[0] * base.step_dt),
        "observation_shapes": {name: list(value.shape) for name, value in observation.items()},
        "policy_history_action_slices": [policy[0, 126 + i * 18:126 + (i + 1) * 18].tolist() for i in range(3)],
        "action_dim": term.action_dim,
        "raw_leg_action": term.raw_actions[0].tolist(),
        "combined_joint_command": term.joint_commands[0].tolist(),
        "robot_position": (robot.data.root_pos_w[0] - origin).tolist(),
        "robot_quaternion": robot.data.root_quat_w[0].tolist(),
        "robot_velocity": robot.data.root_lin_vel_w[0].tolist(),
        "robot_angular_velocity": robot.data.root_ang_vel_w[0].tolist(),
        "robot_joint_position": robot.data.joint_pos[0].tolist(),
        "robot_joint_velocity": robot.data.joint_vel[0].tolist(),
        "box_position": (box.data.root_pos_w[0] - origin).tolist(),
        "box_quaternion": box.data.root_quat_w[0].tolist(),
        "box_velocity": box.data.root_lin_vel_w[0].tolist(),
        "box_angular_velocity": box.data.root_ang_vel_w[0].tolist(),
        "controller": {
            "reference": controller.reference[0].tolist(),
            "safe_approach_index": int(controller.safe_approach_index[0]),
            "safe_approach_complete": bool(controller.safe_approach_complete[0]),
            "precontact_stage": int(controller.precontact_stage[0]),
            "precontact_ready": bool(controller.precontact_ready[0]),
            "motion_ready": bool(controller.motion_ready[0]),
            "contact_duration": float(controller.contact_duration[0]),
            "contact_memory_left": float(controller.contact_memory_left[0]),
            "drive_contact": bool(controller.drive_contact[0]),
            "leg_release_elapsed": float(controller.leg_release_elapsed[0]),
            "leg_release_blend": float(controller.leg_release_blend[0]),
            "goal_hold_active": bool(controller.goal_hold_active[0]),
            "velocity_integral": controller.velocity_integral[0].tolist(),
        },
    }


def main():
    mdp_dir = Path(box_push.__file__).resolve().parent
    actual_hashes = {
        name: hashlib.sha256((mdp_dir / name).read_bytes()).hexdigest()
        for name in EXPECTED_CONTROL_SHA256
    }
    if actual_hashes != EXPECTED_CONTROL_SHA256:
        raise RuntimeError(f"PUSH control source changed: {actual_hashes}")
    config = load_cfg_from_registry(TASK, "env_cfg_entry_point")
    config.scene.num_envs = 1
    config.seed = args.seed
    config.sim.device = args.device
    config.observations.policy.enable_corruption = False
    config.episode_length_s = 12.0
    config.push_ik_clearance_minimum = 0.10
    config.push_ik_orientation_weight = 0.5
    config.push_ik_joint_limit_solve = True
    config.push_goal_hold_pose = True
    config.push_press_on_legal_contact = True
    config.push_stop_distance = 0.11
    config.push_contact_memory_s = 0.10
    config.push_leg_release_ramp_s = 0.7
    config.push_leg_contact_ramp_s = 0.2
    config.push_forward_command_gain = 2.0
    config.push_contact_gap_slowdown_start = 0.0
    config.push_press_depth = 0.10
    config.push_hand_height_offset = 0.03
    if hasattr(config, "push_contact_height_offset"):
        config.push_contact_height_offset = 0.03
    config.actions.joint_pos.hand_pitch = 0.6
    agent_config = load_cfg_from_registry(TASK, "rsl_rl_cfg_entry_point")
    agent_config.device = args.device
    agent_config.seed = args.seed
    env = RslRlVecEnvWrapper(gym.make(TASK, cfg=config), clip_actions=agent_config.clip_actions)
    try:
        base = env.unwrapped
        with torch.inference_mode():
            before = snapshot(base, env.get_observations())
            observation, _reward, done, _extras = env.step(torch.zeros((1, 12), device=args.device))
            if bool(done[0]):
                raise RuntimeError("Environment reset during the preflight step")
            after = snapshot(base, observation)
            if after["policy_history_action_slices"][-1] != after["combined_joint_command"]:
                raise RuntimeError("PUSH observation history disagrees with the applied joint command")
        report = {
            "schema_version": 1,
            "purpose": "One-step PUSH interface preflight; no NAV or policy success claim",
            "task": TASK,
            "seed": args.seed,
            "step_dt": float(base.step_dt),
            "control_sha256": actual_hashes,
            "joint_names": list(base.scene["robot"].joint_names),
            "before": before,
            "after": after,
        }
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        with args.output_json.open("x", encoding="utf-8") as stream:
            json.dump(report, stream, indent=2, allow_nan=False)
        print("PUSH_RUNTIME_PREFLIGHT=" + str(args.output_json), flush=True)
    finally:
        env.close()


try:
    main()
finally:
    launcher.app.close()
