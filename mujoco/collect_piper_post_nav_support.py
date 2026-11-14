"""Collect independent per-physics-step PIPER support geometry after box NAV."""

from __future__ import annotations

import argparse
from collections import Counter
import json
import math
from pathlib import Path
import sys

import mujoco
import numpy as np
import torch

from check_piper_locomotion import PhysicsMonitor, RolloutFailure
from check_piper_navigation import observation
from check_piper_startup import sha256
from reconfigurable_navigation.piper_robot_profile import PROFILE_PATH
from reconfigurable_navigation.reachability import (
    PiperQuasiStaticSupportChecker,
    STATIC_BOX_BODY,
    make_static_box_navigation_runtime,
    measure_fixed_contact_support_residual,
)
from reconfigurable_navigation.representations import SkillAction, SkillType
from reconfigurable_navigation.skills.base import SkillStatus
from reconfigurable_navigation.skills.navigate import NavigateSkill


def _base_pose(runtime, data) -> np.ndarray:
    base = int(runtime.env.robot_qpos_adr)
    rotation = data.xmat[runtime.base_id].reshape(3, 3)
    return np.array([
        data.qpos[base], data.qpos[base + 1],
        math.atan2(rotation[1, 0], rotation[0, 0]),
    ])


def _refresh_data(runtime, data):
    data.qpos[:] = runtime.data.qpos
    data.qvel[:] = runtime.data.qvel
    data.ctrl[:] = runtime.data.ctrl
    mujoco.mj_forward(runtime.model, data)


def _sample(runtime, data, checker, phase: str, required_margin: float):
    support = checker.evaluate(required_margin=required_margin)
    pose = _base_pose(runtime, data)
    return {
        "phase": phase,
        "time": float(runtime.data.time),
        "supporting_feet": list(support.supporting_feet),
        "support_points_xy": support.support_points.tolist(),
        "center_of_mass_xy": support.center_of_mass_xy.tolist(),
        "base_pose_xy_yaw": pose.tolist(),
        "support_margin": support.support_margin,
    }, support, pose


def _summarize_hold(records, samples, required_margin):
    if not records:
        return {"reference_step": None, "contact_set_preserved_steps": 0}
    reference, reference_pose = samples[0]
    residuals = [
        measure_fixed_contact_support_residual(reference, reference_pose, support, pose)
        for support, pose in samples
    ]
    for record, residual in zip(records, residuals):
        record["contact_set_preserved"] = residual.contact_set_preserved
        record["contact_point_residual"] = residual.maximum_contact_point_residual
        record["center_of_mass_residual"] = residual.center_of_mass_residual
    retained = [item for item in residuals if item.contact_set_preserved]
    margins = [item.support_margin for item, _ in samples if item.support_margin is not None]
    contact_sets = Counter(",".join(item.supporting_feet) for item, _ in samples)
    longest_run = 0
    run = 0
    previous_feet = None
    for item, _ in samples:
        run = run + 1 if item.supporting_feet == previous_feet else 1
        longest_run = max(longest_run, run)
        previous_feet = item.supporting_feet
    foot_radius = max((item.maximum_contact_point_residual for item in retained), default=None)
    com_radius = max((item.center_of_mass_residual for item in retained), default=None)
    empirical_lower_bound = (
        reference.support_margin - foot_radius - com_radius
        if reference.support_margin is not None and foot_radius is not None
        and com_radius is not None and reference.support_margin >= foot_radius + com_radius
        else None
    )
    return {
        "reference_step": 0,
        "reference_feet": list(reference.supporting_feet),
        "reference_margin": reference.support_margin,
        "hold_steps": len(records),
        "contact_set_preserved_steps": len(retained),
        "all_steps_preserved": len(retained) == len(records),
        "contact_set_counts": dict(contact_sets),
        "longest_unchanged_contact_set_steps": longest_run,
        "maximum_contact_point_residual": foot_radius,
        "maximum_center_of_mass_residual": com_radius,
        "empirical_lower_bound_for_preserved_steps": empirical_lower_bound,
        "minimum_preserved_margin": min(
            (item.observed_support_margin for item in retained
             if item.observed_support_margin is not None), default=None
        ),
        "minimum_observed_margin": min(margins, default=None),
        "steps_without_three_feet": sum(
            len(item.supporting_feet) < 3 for item, _ in samples
        ),
        "steps_below_required_margin": sum(
            item.support_margin is None or item.support_margin < required_margin
            for item, _ in samples
        ),
    }


def run_episode(seed, args):
    runtime = make_static_box_navigation_runtime(
        seed=seed,
        box_position=np.asarray(args.box_position),
        box_size=np.asarray(args.box_size),
        box_yaw=args.box_yaw,
    )
    monitor = PhysicsMonitor(runtime, np.zeros(3))
    box_geometry = runtime.model.geom(STATIC_BOX_BODY).id
    fresh_data = mujoco.MjData(runtime.model)
    checker = PiperQuasiStaticSupportChecker(runtime, data=fresh_data)
    records = []
    hold_samples = []

    def on_step():
        monitor()
        _refresh_data(runtime, fresh_data)
        for contact_index in range(fresh_data.ncon):
            contact = fresh_data.contact[contact_index]
            if contact.dist <= 0 and box_geometry in (contact.geom1, contact.geom2):
                raise RolloutFailure("static_box_contact")
        if monitor.stage not in ("post_nav_settle", "hold"):
            return
        record, support, pose = _sample(
            runtime, fresh_data, checker, monitor.stage, args.required_margin
        )
        records.append(record)
        if monitor.stage == "hold":
            hold_samples.append((support, pose))

    runtime.on_physics_step = on_step
    box_position = np.asarray(args.box_position)
    box_size = np.asarray(args.box_size)
    forward = np.array([math.cos(args.box_yaw), math.sin(args.box_yaw)])
    lateral = np.array([-forward[1], forward[0]])
    target_xy = box_position[:2] - (
        box_size[0] / 2 + args.front_standoff
    ) * forward + args.lateral_offset * lateral
    target = np.array([*target_xy, args.box_yaw])
    skill = NavigateSkill()
    action = SkillAction(SkillType.NAV, target)
    reason = "completed"
    try:
        for _ in range(round(args.initial_settle / runtime.control_dt)):
            runtime.hold_default()
        if not skill.can_execute(observation(runtime, target), action):
            raise RolloutFailure("navigation_rejected")
        skill.reset(action)
        monitor.stage = "navigation"
        for _ in range(skill.config.timeout_steps):
            command = skill.step(observation(runtime, target))
            runtime.step(command.velocity, command.end_effector_pose)
            if skill.status != SkillStatus.RUNNING:
                break
        if skill.status != SkillStatus.SUCCEEDED:
            raise RolloutFailure(skill.failure_reason or "navigation_timeout")
        monitor.stage = "post_nav_settle"
        for _ in range(round(args.post_nav_settle / runtime.control_dt)):
            runtime.step(np.zeros(3))
        monitor.stage = "hold"
        for _ in range(round(args.hold / runtime.control_dt)):
            runtime.step(np.zeros(3))
    except RolloutFailure as error:
        reason = str(error)

    hold_records = [record for record in records if record["phase"] == "hold"]
    return {
        "seed": seed,
        "reason": reason,
        "nav_and_hold_completed": reason == "completed" and bool(hold_records),
        "target_base_pose": target.tolist(),
        "final_base_pose": _base_pose(runtime, runtime.data).tolist(),
        "elapsed_sim_time": float(runtime.data.time),
        "physics_steps": monitor.physics_steps,
        "min_base_height": monitor.min_height,
        "max_tilt_rad": monitor.max_tilt,
        "first_illegal_contact": monitor.first_illegal_contact,
        "policy_sha256": sha256(runtime.policy_path),
        "config_sha256": sha256(runtime.config_path),
        "hold_summary": _summarize_hold(hold_records, hold_samples, args.required_margin),
        "trace": records,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, default=1)
    parser.add_argument("--seed-offset", type=int, default=0)
    parser.add_argument("--initial-settle", type=float, default=2.0)
    parser.add_argument("--post-nav-settle", type=float, default=1.0)
    parser.add_argument("--hold", type=float, default=2.0)
    parser.add_argument("--required-margin", type=float, default=0.02)
    parser.add_argument("--box-position", type=float, nargs=3, default=(1.4, 0.4, 0.25))
    parser.add_argument("--box-size", type=float, nargs=3, default=(0.5, 0.5, 0.5))
    parser.add_argument("--box-yaw", type=float, default=0.0)
    parser.add_argument("--front-standoff", type=float, default=0.65)
    parser.add_argument("--lateral-offset", type=float, default=0.0)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    numeric = [args.initial_settle, args.post_nav_settle, args.hold,
               args.required_margin, *args.box_position, *args.box_size,
               args.box_yaw, args.front_standoff, args.lateral_offset]
    if (args.seeds < 1 or args.seed_offset < 0 or not np.isfinite(numeric).all()
            or min(args.initial_settle, args.post_nav_settle, args.required_margin) < 0
            or args.hold <= 0 or args.front_standoff <= 0
            or min(args.box_size) <= 0 or args.output_json.exists()):
        parser.error("Invalid parameters or output path already exists")
    torch.set_num_threads(1)
    results = []
    for seed in range(args.seed_offset, args.seed_offset + args.seeds):
        result = run_episode(seed, args)
        results.append(result)
        print(f"seed={seed} reason={result['reason']} hold={result['hold_summary']}",
              file=sys.stderr, flush=True)
    root = Path(__file__).parent
    paths = [Path(__file__), root / "check_piper_locomotion.py",
             root / "check_piper_navigation.py", PROFILE_PATH]
    paths.extend(root / "reconfigurable_navigation" / name for name in (
        "reachability/support.py", "reachability/scenes.py", "piper_robot_profile.py",
        "piper_locomotion_runtime.py", "locomotion_runtime.py", "skills/navigate.py",
    ))
    paths.extend(path for path in (root / "robots/go2_piper").rglob("*") if path.is_file())
    report = {
        "schema_version": 1,
        "scope": "post-NAV fixed-foot support observation; no arm approach, PUSH, or hardware acceptance",
        "arguments": {key: str(value) if isinstance(value, Path) else value
                      for key, value in vars(args).items() if key != "output_json"},
        "sampling": "every physics step; qpos/qvel/ctrl copied to independent MjData then mj_forward",
        "source_assets_sha256": {str(path): sha256(path) for path in paths},
        "backend": {"mujoco": mujoco.__version__, "numpy": np.__version__,
                    "torch": torch.__version__},
        "completed_episodes": sum(item["nav_and_hold_completed"] for item in results),
        "failures": dict(Counter(item["reason"] for item in results
                                 if not item["nav_and_hold_completed"])),
        "results": results,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x") as destination:
        json.dump(report, destination, indent=2, allow_nan=False)
    print(json.dumps({"output": str(args.output_json),
                      "completed_episodes": report["completed_episodes"],
                      "failures": report["failures"]}, indent=2))
    return 0 if report["completed_episodes"] == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
