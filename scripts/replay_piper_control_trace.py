"""Replay identical joint targets in Isaac without actor feedback or resets."""

import argparse
import hashlib
import json
from pathlib import Path

from isaaclab.app import AppLauncher


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--trace-json", type=Path, required=True)
parser.add_argument("--output-json", type=Path, required=True)
AppLauncher.add_app_launcher_args(parser)
args = parser.parse_args()
if args.output_json.exists():
    parser.error("Require a new output")
launcher = AppLauncher(args)

import gymnasium as gym
import torch
import isaaclab_tasks
from isaaclab_tasks.utils import load_cfg_from_registry
from isaaclab.utils.math import quat_apply, quat_apply_inverse
import LeggedManip_Lab.tasks
import omni.usd
from pxr import PhysxSchema, Usd, UsdPhysics


def main():
    trace = json.loads(args.trace_json.read_text())
    config = load_cfg_from_registry("GO2-PIPER-Box-Climb-Play", "env_cfg_entry_point")
    config.scene.num_envs = 1
    config.sim.device = args.device
    config.sim.dt = trace["physics_dt"]
    config.seed = 60
    config.events.add_base_mass = None
    config.observations.policy.enable_corruption = False
    env = gym.make("GO2-PIPER-Box-Climb-Play", cfg=config).unwrapped
    try:
        env.reset()
        robot = env.scene["robot"]
        names = trace["joint_names"]
        joint_ids = [robot.joint_names.index(name) for name in names]
        state = robot.data.default_root_state.clone()
        initial = trace["initial_state"]
        state[0, :7] = torch.tensor(initial["root_pose"], device=args.device)
        state[:, :3] += env.scene.env_origins
        velocity = torch.tensor(initial["root_velocity"], device=args.device).unsqueeze(0)
        state[:, 7:10] = velocity[:, :3]
        state[:, 10:13] = quat_apply(state[:, 3:7], velocity[:, 3:6])
        positions = robot.data.default_joint_pos.clone()
        velocities = torch.zeros_like(positions)
        positions[0, joint_ids] = torch.tensor(initial["joint_positions"], device=args.device)
        velocities[0, joint_ids] = torch.tensor(initial["joint_velocities"], device=args.device)
        robot.write_root_state_to_sim(state)
        robot.write_joint_state_to_sim(positions, velocities)
        robot.reset()
        delay_by_native_joint = torch.zeros(robot.num_joints, dtype=torch.long, device=args.device)
        delay_by_native_joint[joint_ids] = torch.tensor(trace["actuator_delay_steps"], device=args.device)
        all_joints = torch.arange(robot.num_joints, device=args.device)
        for actuator in robot.actuators.values():
            delays = delay_by_native_joint[all_joints[actuator.joint_indices]].unique()
            if delays.numel() != 1:
                raise ValueError("Expected one delay per native actuator group")
            for buffer_name in ("positions_delay_buffer", "velocities_delay_buffer", "efforts_delay_buffer"):
                buffer = getattr(actuator, buffer_name)
                buffer.set_time_lag(int(delays.item()))
                buffer.reset()
        robot.set_joint_position_target(positions)
        env.sim.forward()
        env.scene.update(0.0)
        measured_initial = {
            "root_pose": torch.cat((robot.data.root_pos_w[0] - env.scene.env_origins[0], robot.data.root_quat_w[0])).tolist(),
            "joint_positions": robot.data.joint_pos[0, joint_ids].tolist(),
            "joint_velocities": robot.data.joint_vel[0, joint_ids].tolist(),
        }
        collider_offsets = []
        stage = omni.usd.get_context().get_stage()
        for prim in Usd.PrimRange.Stage(stage, Usd.TraverseInstanceProxies()):
            if "/env_0/Robot/" not in str(prim.GetPath()) or not prim.HasAPI(UsdPhysics.CollisionAPI):
                continue
            collision = PhysxSchema.PhysxCollisionAPI(prim)
            collider_offsets.append({
                "prim": str(prim.GetPath()),
                "contact_offset": collision.GetContactOffsetAttr().Get(),
                "rest_offset": collision.GetRestOffsetAttr().Get(),
                "offsets_explicitly_set": collision.GetContactOffsetAttr().HasAuthoredValueOpinion() and collision.GetRestOffsetAttr().HasAuthoredValueOpinion(),
            })
        if not collider_offsets:
            raise ValueError("No native colliders found; contact-offset evidence is incomplete")
        contacts = env.scene["contact_forces"]
        rows = []
        for source in trace["steps"]:
            positions[0, joint_ids] = torch.tensor(source["target"], device=args.device)
            robot.set_joint_position_target(positions)
            env.scene.write_data_to_sim()
            torque = robot.data.applied_torque[0, joint_ids].tolist()
            env.sim.step(render=False)
            env.scene.update(config.sim.dt)
            root_position = robot.data.root_pos_w[0] - env.scene.env_origins[0]
            quaternion = robot.data.root_quat_w[0]
            angular = quat_apply_inverse(quaternion.unsqueeze(0), robot.data.root_ang_vel_w)[0]
            rows.append({
                "physics_step": source["physics_step"], "time": (source["physics_step"] + 1) * config.sim.dt,
                "root_pose": torch.cat((root_position, quaternion)).tolist(),
                "root_velocity": torch.cat((robot.data.root_link_lin_vel_w[0], angular)).tolist(),
                "target": source["target"], "torque": torque,
                "solver_positions": robot.data.joint_pos[0, joint_ids].tolist(),
                "solver_velocities": robot.data.joint_vel[0, joint_ids].tolist(),
                "body_positions": (robot.data.body_pos_w[0] - env.scene.env_origins[0]).tolist(),
                "contact_forces": contacts.data.net_forces_w[0].tolist(),
            })
        report = {
            "schema_version": 1, "backend": "isaac", "diagnostic_only": True,
            "trace_sha256": hashlib.sha256(args.trace_json.read_bytes()).hexdigest(),
            "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "physics_dt": config.sim.dt, "joint_names": names, "initial_state": initial,
            "measured_initial_state": measured_initial,
            "joint_ranges": robot.root_physx_view.get_dof_limits()[0, joint_ids].tolist(),
            "collider_offsets": collider_offsets, "contact_body_names": list(contacts.body_names),
            "masses": robot.root_physx_view.get_masses()[0].tolist(),
            "body_names": list(robot.body_names), "steps": rows,
        }
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        with args.output_json.open("x") as destination:
            json.dump(report, destination, indent=2, allow_nan=False)
        print(f"PIPER_REPLAY steps={len(rows)} output={args.output_json}", flush=True)
    finally:
        env.close()


try:
    main()
finally:
    launcher.app.close()