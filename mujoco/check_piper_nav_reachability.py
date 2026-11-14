"""Shadow-check PIPER reachability after actual NAV arrival without contact."""

from __future__ import annotations

import argparse
from collections import Counter
import json
import math
from pathlib import Path

import mujoco
import numpy as np
import torch

from check_piper_locomotion import PhysicsMonitor, RolloutFailure
from check_piper_navigation import observation
from check_piper_startup import sha256
from reconfigurable_navigation.box_push_runtime import CONTROL, CONTROL_PATH, batch
from reconfigurable_navigation.piper_locomotion_runtime import PiperLocomotionRuntime
from reconfigurable_navigation.piper_robot_profile import PROFILE_PATH
from reconfigurable_navigation.reachability import (
    PiperArmClearanceChecker,
    PiperPositionReachabilityOracle,
    PiperQuasiStaticSupportChecker,
    PiperSelfClearanceChecker,
    ReachabilityQuery,
    STATIC_BOX_BODY,
    make_static_box_navigation_runtime,
)
from reconfigurable_navigation.representations import SkillAction, SkillType
from reconfigurable_navigation.skills.base import SkillStatus
from reconfigurable_navigation.skills.navigate import NavigateSkill, wrap_angle


def _base_pose(runtime, target: np.ndarray) -> np.ndarray:
    robot_state = observation(runtime, target).robot_state
    return np.array([robot_state[0], robot_state[1], robot_state[5]], dtype=np.float64)


def _reason(
    result,
    *,
    joint_limit_margin: float,
    self_clearance,
    support,
    environment_clearance,
) -> str:
    if not result.kinematic_feasible:
        return result.failure_reason or "position_ik_unreachable"
    if result.joint_limit_margin < joint_limit_margin:
        return "joint_limit_margin"
    if not self_clearance.safe:
        return "self_clearance"
    if environment_clearance is not None and not environment_clearance.safe:
        return "environment_clearance"
    if not support.safe:
        return "quasistatic_support"
    return "certified"


def run_episode(
    seed: int,
    *,
    distance: float,
    initial_settle_seconds: float,
    post_nav_settle_seconds: float,
    required_joint_limit_margin: float,
    required_self_clearance: float,
    required_support_margin: float,
    scene: str,
    static_box_position: np.ndarray,
    static_box_size: np.ndarray,
    static_box_yaw: float,
    required_environment_clearance: float,
    target_offset: np.ndarray,
    target_mode: str,
    push_approach_distance: float,
    nav_front_standoff: float = 0.65,
    nav_lateral_offset: float = 0.0,
    push_target_height_offset: float = 0.0,
    tube_base_translation_bound: float = 0.0,
    tube_base_yaw_bound: float = 0.0,
    tube_box_error_bound: float = 0.0,
    diagnostic_ik_multistart: bool = False,
    diagnostic_hand_target_grid: bool = False,
    diagnostic_base_translation_error: float = 0.0,
    diagnostic_base_yaw_error: float = 0.0,
) -> dict[str, object]:
    static_box_position = np.asarray(static_box_position, dtype=np.float64)
    static_box_size = np.asarray(static_box_size, dtype=np.float64)
    target_offset = np.asarray(target_offset, dtype=np.float64)
    runtime = (
        PiperLocomotionRuntime(seed=seed, profile_path=PROFILE_PATH)
        if scene == "empty"
        else make_static_box_navigation_runtime(
            seed=seed,
            box_position=static_box_position,
            box_size=static_box_size,
            box_yaw=static_box_yaw,
        )
    )
    monitor = PhysicsMonitor(runtime, np.zeros(3))
    if scene == "static-box":
        box_geometry = runtime.model.geom(STATIC_BOX_BODY).id

        def monitor_with_box_contact() -> None:
            monitor()
            for contact_index, contact in enumerate(runtime.data.contact):
                if box_geometry not in (contact.geom1, contact.geom2) or contact.dist > 0:
                    continue
                other_geometry = contact.geom2 if contact.geom1 == box_geometry else contact.geom1
                force = np.zeros(6)
                mujoco.mj_contactForce(runtime.model, runtime.data, contact_index, force)
                monitor.first_illegal_contact = {
                    "time": float(runtime.data.time),
                    "body": runtime.model.body(
                        int(runtime.model.geom_bodyid[other_geometry])
                    ).name,
                    "normal_force": float(force[0]),
                    "depth": float(-contact.dist),
                }
                raise RolloutFailure("static_box_contact")

        runtime.on_physics_step = monitor_with_box_contact
    else:
        runtime.on_physics_step = monitor
    oracle = PiperPositionReachabilityOracle(runtime)
    self_clearance_checker = PiperSelfClearanceChecker(runtime)
    support_checker = PiperQuasiStaticSupportChecker(runtime)
    environment_checker = (
        PiperArmClearanceChecker(
            runtime,
            protected_body_names=frozenset({STATIC_BOX_BODY}),
        )
        if scene == "static-box"
        else None
    )
    nav_reason = "completed"
    planned_base_pose = np.zeros(3, dtype=np.float64)
    task_target = np.zeros(3, dtype=np.float64)
    planned_result = None
    actual_base_pose = np.zeros(3, dtype=np.float64)
    actual_base_tilt_rad = None
    actual_result = None
    self_clearance = None
    support = None
    environment_clearance = None
    environment_tube = None
    sampled_arm_path = None
    alternative_ik_diagnostic = None
    hand_ik_diagnostic = None
    hand_target_grid = None
    push_target_in_approach_window = None
    push_target_proxy_approach_ready = None
    push_hand_local = None
    push_hand_in_controller_gate = None
    try:
        for _ in range(round(initial_settle_seconds / runtime.control_dt)):
            runtime.hold_default()
        start_pose = _base_pose(runtime, np.zeros(3))
        planned_base_pose = np.array(
            [
                start_pose[0] + distance * math.cos(start_pose[2]),
                start_pose[1] + distance * math.sin(start_pose[2]),
                start_pose[2],
            ],
            dtype=np.float64,
        )
        if target_mode == "push-precontact":
            planned_base_pose = np.array([
                static_box_position[0] - (static_box_size[0] / 2.0 + nav_front_standoff) * math.cos(static_box_yaw) - nav_lateral_offset * math.sin(static_box_yaw),
                static_box_position[1] - (static_box_size[0] / 2.0 + nav_front_standoff) * math.sin(static_box_yaw) + nav_lateral_offset * math.cos(static_box_yaw),
                static_box_yaw,
            ])
        nominal_target = oracle.end_effector_position(
            ReachabilityQuery(planned_base_pose, np.zeros(3))
        )
        if target_mode == "push-precontact":
            task_target = static_box_position - (
                static_box_size[0] / 2.0 + push_approach_distance
            ) * np.array([math.cos(static_box_yaw), math.sin(static_box_yaw), 0.0])
            task_target[2] += push_target_height_offset
            cosine, sine = math.cos(static_box_yaw), math.sin(static_box_yaw)
            local_target = np.array([
                cosine * (task_target[0] - static_box_position[0]) + sine * (task_target[1] - static_box_position[1]),
                -sine * (task_target[0] - static_box_position[0]) + cosine * (task_target[1] - static_box_position[1]),
                task_target[2] - static_box_position[2],
            ])
            push_target_in_approach_window = bool(CONTROL["side_approach_ready"](
                torch.as_tensor(local_target[None], dtype=torch.float64),
                static_box_size[0] / 2.0,
                push_approach_distance,
            )[0])
            push_target_proxy_approach_ready = bool(CONTROL["side_approach_ready"](
                torch.tensor([[-static_box_size[0] / 2.0 - push_approach_distance, 0.0, push_target_height_offset]], dtype=torch.float64),
                static_box_size[0] / 2.0,
                push_approach_distance,
            )[0]) and abs(push_target_height_offset) < 0.06
        else:
            task_target = nominal_target + target_offset
        planned_result = oracle.solve(ReachabilityQuery(planned_base_pose, task_target))
        if not planned_result.kinematic_feasible and target_mode != "push-precontact":
            raise RolloutFailure("planned_target_kinematically_unreachable")

        skill = NavigateSkill()
        action = SkillAction(SkillType.NAV, planned_base_pose)
        if not skill.can_execute(observation(runtime, planned_base_pose), action):
            raise RolloutFailure("navigation_rejected")
        skill.reset(action)
        monitor.stage = "navigation"
        for _ in range(skill.config.timeout_steps):
            command = skill.step(observation(runtime, planned_base_pose))
            runtime.step(command.velocity, command.end_effector_pose)
            if skill.status != SkillStatus.RUNNING:
                break
        if skill.status != SkillStatus.SUCCEEDED:
            raise RolloutFailure(skill.failure_reason or "navigation_timeout")

        monitor.stage = "post_navigation_settle"
        for _ in range(round(post_nav_settle_seconds / runtime.control_dt)):
            runtime.step(np.zeros(3))
        actual_base_pose = _base_pose(runtime, planned_base_pose)
        base_quaternion = runtime.data.qpos[
            self_clearance_checker.base_qpos_adr + 3 : self_clearance_checker.base_qpos_adr + 7
        ]
        base_rotation = np.empty(9, dtype=np.float64)
        mujoco.mju_quat2Mat(base_rotation, base_quaternion)
        actual_base_tilt_rad = float(np.arccos(np.clip(base_rotation[8], -1.0, 1.0)))
        starting_arm = runtime.data.qpos[self_clearance_checker.arm_qpos_adr].copy()
        actual_result = oracle.solve(ReachabilityQuery(actual_base_pose, task_target))
        box_rotation = np.array([
            [math.cos(static_box_yaw), -math.sin(static_box_yaw), 0.0],
            [math.sin(static_box_yaw), math.cos(static_box_yaw), 0.0],
            [0.0, 0.0, 1.0],
        ])

        def hand_gate(joints):
            hand_world = oracle.hand_position(
                ReachabilityQuery(actual_base_pose, task_target), joints,
            )
            hand_local = box_rotation.T @ (hand_world - static_box_position)
            ready = bool(bool(CONTROL["side_approach_ready"](
                batch(hand_local), static_box_size[0] / 2.0, push_approach_distance,
            )[0]) and abs(hand_local[2]) < 0.06)
            return hand_local.tolist(), ready

        if diagnostic_ik_multistart:
            candidates = []
            hand_candidates = []
            for shoulder, elbow in ((0.6, -0.6), (0.6, -1.2), (1.2, -0.6), (1.2, -1.2)):
                initial = np.clip(
                    runtime.default_qpos[12:] + np.array([0.0, shoulder, elbow, 0.0, 0.0, 0.0]),
                    oracle.arm_low,
                    oracle.arm_high,
                )
                candidate = oracle.solve(
                    ReachabilityQuery(actual_base_pose, task_target),
                    initial_joint_positions=initial,
                )
                record = {
                    "initial_joint_positions": initial.tolist(),
                    "kinematic_feasible": candidate.kinematic_feasible,
                    "position_error": candidate.position_error,
                    "joint_limit_margin": candidate.joint_limit_margin,
                    "minimum_self_clearance": None,
                    "minimum_environment_clearance": None,
                    "support_margin": None,
                    "static_constraints_passed": False,
                }
                if candidate.kinematic_feasible:
                    record["push_hand_local"], record["push_hand_in_controller_gate"] = hand_gate(
                        candidate.joint_solution,
                    )
                    candidate_self = self_clearance_checker.evaluate(
                        actual_base_pose, candidate.joint_solution,
                        required_clearance=required_self_clearance,
                    )
                    candidate_support = support_checker.evaluate_configuration(
                        actual_base_pose, candidate.joint_solution,
                        required_margin=required_support_margin,
                    )
                    candidate_environment = environment_checker.evaluate(
                        actual_base_pose, candidate.joint_solution,
                        required_clearance=required_environment_clearance,
                    ) if environment_checker is not None else None
                    record.update({
                        "minimum_self_clearance": candidate_self.minimum_clearance,
                        "minimum_environment_clearance": (
                            candidate_environment.minimum_clearance
                            if candidate_environment is not None else None
                        ),
                        "support_margin": candidate_support.support_margin,
                        "static_constraints_passed": bool(
                            candidate.joint_limit_margin >= required_joint_limit_margin
                            and candidate_self.safe and candidate_support.safe
                            and (candidate_environment is None or candidate_environment.safe)
                        ),
                    })
                candidates.append(record)
                hand_candidate = oracle.solve(
                    ReachabilityQuery(actual_base_pose, task_target),
                    initial_joint_positions=initial, hand_offset=(0.15, 0.0, 0.0),
                )
                hand_record = {
                    "initial_joint_positions": initial.tolist(),
                    "kinematic_feasible": hand_candidate.kinematic_feasible,
                    "position_error": hand_candidate.position_error,
                    "joint_limit_margin": hand_candidate.joint_limit_margin,
                    "minimum_self_clearance": None,
                    "minimum_environment_clearance": None,
                    "support_margin": None,
                    "push_hand_local": None,
                    "push_hand_in_controller_gate": None,
                    "static_constraints_passed": False,
                }
                if hand_candidate.kinematic_feasible:
                    hand_record["push_hand_local"], hand_record["push_hand_in_controller_gate"] = hand_gate(
                        hand_candidate.joint_solution,
                    )
                    hand_self = self_clearance_checker.evaluate(
                        actual_base_pose, hand_candidate.joint_solution,
                        required_clearance=required_self_clearance,
                    )
                    hand_support = support_checker.evaluate_configuration(
                        actual_base_pose, hand_candidate.joint_solution,
                        required_margin=required_support_margin,
                    )
                    hand_environment = environment_checker.evaluate(
                        actual_base_pose, hand_candidate.joint_solution,
                        required_clearance=required_environment_clearance,
                    ) if environment_checker is not None else None
                    hand_record.update({
                        "minimum_self_clearance": hand_self.minimum_clearance,
                        "minimum_environment_clearance": (
                            hand_environment.minimum_clearance
                            if hand_environment is not None else None
                        ),
                        "support_margin": hand_support.support_margin,
                        "static_constraints_passed": bool(
                            hand_candidate.joint_limit_margin >= required_joint_limit_margin
                            and hand_self.safe and hand_support.safe
                            and (hand_environment is None or hand_environment.safe)
                            and hand_record["push_hand_in_controller_gate"]
                        ),
                    })
                hand_candidates.append(hand_record)
            alternative_ik_diagnostic = candidates
            hand_ik_diagnostic = hand_candidates
        if diagnostic_hand_target_grid:
            hand_target_grid = []
            for forward in (-static_box_size[0] / 2 - push_approach_distance - 0.059,
                            -static_box_size[0] / 2 - push_approach_distance - 0.055,
                            -static_box_size[0] / 2 - push_approach_distance - 0.05,
                            -static_box_size[0] / 2 - push_approach_distance,
                            -static_box_size[0] / 2 - 0.04):
                for lateral in (-0.06, 0.0, 0.06):
                    for height in (-0.02, 0.0, 0.02):
                        local_target = np.array([forward, lateral, height])
                        if not bool(CONTROL["side_approach_ready"](
                            batch(local_target), static_box_size[0] / 2, push_approach_distance,
                        )[0]):
                            continue
                        world_target = static_box_position + box_rotation @ local_target
                        initial_positions = [None]
                        if diagnostic_ik_multistart:
                            initial_positions.extend(
                                np.clip(
                                    runtime.default_qpos[12:] + np.array([0.0, shoulder, elbow, 0.0, 0.0, 0.0]),
                                    oracle.arm_low, oracle.arm_high,
                                )
                                for shoulder, elbow in ((0.6, -0.6), (0.6, -1.2), (1.2, -0.6), (1.2, -1.2))
                            )
                        for initial in initial_positions:
                            candidate = oracle.solve(
                                ReachabilityQuery(actual_base_pose, world_target),
                                hand_offset=(0.15, 0.0, 0.0),
                                initial_joint_positions=initial,
                            )
                            record = {
                                "target_local": local_target.tolist(),
                                "initial_joint_positions": initial.tolist() if initial is not None else None,
                                "kinematic_feasible": candidate.kinematic_feasible,
                                "position_error": candidate.position_error,
                                "joint_limit_margin": candidate.joint_limit_margin,
                                "push_hand_in_controller_gate": None,
                                "minimum_self_clearance": None,
                                "self_clearance_bodies": None,
                                "minimum_environment_clearance": None,
                                "support_margin": None,
                                "static_constraints_passed": False,
                                "joint_solution": None,
                                "sampled_arm_path": None,
                            }
                            if candidate.kinematic_feasible:
                                _, record["push_hand_in_controller_gate"] = hand_gate(candidate.joint_solution)
                                candidate_self = self_clearance_checker.evaluate(
                                    actual_base_pose, candidate.joint_solution,
                                    required_clearance=required_self_clearance,
                                )
                                candidate_support = support_checker.evaluate_configuration(
                                    actual_base_pose, candidate.joint_solution,
                                    required_margin=required_support_margin,
                                )
                                candidate_environment = environment_checker.evaluate(
                                    actual_base_pose, candidate.joint_solution,
                                    required_clearance=required_environment_clearance,
                                ) if environment_checker is not None else None
                                record.update({
                                    "joint_solution": candidate.joint_solution.tolist(),
                                    "minimum_self_clearance": candidate_self.minimum_clearance,
                                    "self_clearance_bodies": [candidate_self.arm_body, candidate_self.protected_body],
                                    "minimum_environment_clearance": (
                                        candidate_environment.minimum_clearance
                                        if candidate_environment is not None else None
                                    ),
                                    "support_margin": candidate_support.support_margin,
                                    "static_constraints_passed": bool(
                                        candidate.joint_limit_margin >= required_joint_limit_margin
                                        and candidate_self.safe and candidate_support.safe
                                        and (candidate_environment is None or candidate_environment.safe)
                                        and record["push_hand_in_controller_gate"]
                                    ),
                                })
                                if record["static_constraints_passed"]:
                                    path_self = []
                                    path_environment = []
                                    path_support = []
                                    for fraction in np.linspace(0.0, 1.0, 101):
                                        arm = starting_arm + fraction * (candidate.joint_solution - starting_arm)
                                        path_self.append(self_clearance_checker.evaluate(
                                            actual_base_pose, arm, required_clearance=required_self_clearance,
                                        ).minimum_clearance)
                                        path_environment.append(environment_checker.evaluate(
                                            actual_base_pose, arm, required_clearance=required_environment_clearance,
                                        ).minimum_clearance)
                                        path_support.append(support_checker.evaluate_configuration(
                                            actual_base_pose, arm, required_margin=required_support_margin,
                                        ).support_margin)
                                    record["sampled_arm_path"] = {
                                        "samples": 101,
                                        "minimum_self_clearance": min(path_self),
                                        "minimum_environment_clearance": min(path_environment),
                                        "minimum_support_margin": min(path_support),
                                        "sampled_constraints_passed": bool(
                                            min(path_self) >= required_self_clearance
                                            and min(path_environment) >= required_environment_clearance
                                            and min(path_support) >= required_support_margin
                                        ),
                                    }
                                    if (record["sampled_arm_path"]["sampled_constraints_passed"]
                                            and (diagnostic_base_translation_error or diagnostic_base_yaw_error)):
                                        perturbations = []
                                        for offset in (
                                            (diagnostic_base_translation_error, 0.0, 0.0),
                                            (-diagnostic_base_translation_error, 0.0, 0.0),
                                            (0.0, diagnostic_base_translation_error, 0.0),
                                            (0.0, -diagnostic_base_translation_error, 0.0),
                                            (0.0, 0.0, diagnostic_base_yaw_error),
                                            (0.0, 0.0, -diagnostic_base_yaw_error),
                                        ):
                                            if not any(offset):
                                                continue
                                            perturbed_base = actual_base_pose + offset
                                            hand_world = oracle.hand_position(
                                                ReachabilityQuery(perturbed_base, world_target), candidate.joint_solution,
                                            )
                                            hand_local = box_rotation.T @ (hand_world - static_box_position)
                                            hand_ready = bool(bool(CONTROL["side_approach_ready"](
                                                batch(hand_local), static_box_size[0] / 2, push_approach_distance,
                                            )[0]) and abs(hand_local[2]) < 0.06)
                                            perturbed_self = self_clearance_checker.evaluate(
                                                perturbed_base, candidate.joint_solution,
                                                required_clearance=required_self_clearance,
                                            )
                                            perturbed_environment = environment_checker.evaluate(
                                                perturbed_base, candidate.joint_solution,
                                                required_clearance=required_environment_clearance,
                                            )
                                            perturbed_support = support_checker.evaluate_configuration(
                                                perturbed_base, candidate.joint_solution,
                                                required_margin=required_support_margin,
                                            )
                                            perturbed_path_self = []
                                            perturbed_path_environment = []
                                            perturbed_path_support = []
                                            for fraction in np.linspace(0.0, 1.0, 101):
                                                arm = starting_arm + fraction * (candidate.joint_solution - starting_arm)
                                                perturbed_path_self.append(self_clearance_checker.evaluate(
                                                    perturbed_base, arm,
                                                    required_clearance=required_self_clearance,
                                                ).minimum_clearance)
                                                perturbed_path_environment.append(environment_checker.evaluate(
                                                    perturbed_base, arm,
                                                    required_clearance=required_environment_clearance,
                                                ).minimum_clearance)
                                                perturbed_path_support.append(support_checker.evaluate_configuration(
                                                    perturbed_base, arm,
                                                    required_margin=required_support_margin,
                                                ).support_margin)
                                            perturbed_path = {
                                                "samples": 101,
                                                "minimum_self_clearance": min(perturbed_path_self),
                                                "minimum_environment_clearance": min(perturbed_path_environment),
                                                "minimum_support_margin": min(perturbed_path_support),
                                                "sampled_constraints_passed": bool(
                                                    min(perturbed_path_self) >= required_self_clearance
                                                    and min(perturbed_path_environment) >= required_environment_clearance
                                                    and min(perturbed_path_support) >= required_support_margin
                                                ),
                                            }
                                            perturbations.append({
                                                "base_offset": list(offset),
                                                "hand_local": hand_local.tolist(),
                                                "hand_position_error": float(np.linalg.norm(hand_world - world_target)),
                                                "hand_gate_passed": hand_ready,
                                                "minimum_self_clearance": perturbed_self.minimum_clearance,
                                                "minimum_environment_clearance": perturbed_environment.minimum_clearance,
                                                "support_margin": perturbed_support.support_margin,
                                                "endpoint_passed": bool(
                                                    hand_ready and perturbed_self.safe
                                                    and perturbed_environment.safe and perturbed_support.safe
                                                ),
                                                "sampled_arm_path": perturbed_path,
                                            })
                                        record["fixed_arm_base_perturbations"] = perturbations
                            hand_target_grid.append(record)
        if actual_result.kinematic_feasible:
            if target_mode == "push-precontact":
                push_hand_local, push_hand_in_controller_gate = hand_gate(
                    actual_result.joint_solution,
                )
            sampled_self_clearances = []
            sampled_environment_clearances = []
            for fraction in np.linspace(0.0, 1.0, 11):
                arm = starting_arm + fraction * (actual_result.joint_solution - starting_arm)
                sampled_self_clearances.append(self_clearance_checker.evaluate(
                    actual_base_pose, arm, required_clearance=required_self_clearance,
                ).minimum_clearance)
                if environment_checker is not None:
                    sampled_environment_clearances.append(environment_checker.evaluate(
                        actual_base_pose, arm, required_clearance=required_environment_clearance,
                    ).minimum_clearance)
            sampled_arm_path = {
                "samples": 11,
                "minimum_self_clearance": min(sampled_self_clearances),
                "minimum_environment_clearance": (
                    min(sampled_environment_clearances) if sampled_environment_clearances else None
                ),
            }
            self_clearance = self_clearance_checker.evaluate(
                actual_base_pose,
                actual_result.joint_solution,
                required_clearance=required_self_clearance,
            )
            support = support_checker.evaluate_configuration(
                actual_base_pose,
                actual_result.joint_solution,
                required_margin=required_support_margin,
            )
            if environment_checker is not None:
                environment_clearance = environment_checker.evaluate(
                    actual_base_pose,
                    actual_result.joint_solution,
                    required_clearance=required_environment_clearance,
                )
                environment_tube = environment_checker.certify_frozen_configuration_tube(
                    actual_base_pose,
                    actual_result.joint_solution,
                    base_pose_offset=np.array([tube_base_translation_bound, 0.0, tube_base_yaw_bound]),
                    required_clearance=required_environment_clearance,
                    external_geometry_error_bound=tube_box_error_bound,
                )
    except RolloutFailure as error:
        nav_reason = str(error)

    if actual_result is None:
        actual_certification_reason = nav_reason
    elif not actual_result.kinematic_feasible:
        actual_certification_reason = actual_result.failure_reason or "position_ik_unreachable"
    else:
        actual_certification_reason = _reason(
            actual_result,
            joint_limit_margin=required_joint_limit_margin,
            self_clearance=self_clearance,
            support=support,
            environment_clearance=environment_clearance,
        )
    push_target_in_controller_gate = None
    if target_mode == "push-precontact":
        box_rotation = np.array([
            [math.cos(static_box_yaw), -math.sin(static_box_yaw), 0.0],
            [math.sin(static_box_yaw), math.cos(static_box_yaw), 0.0],
            [0.0, 0.0, 1.0],
        ])
        target_local = box_rotation.T @ (task_target - static_box_position)
        push_target_in_controller_gate = bool(CONTROL["side_approach_ready"](
            batch(target_local), static_box_size[0] / 2.0, push_approach_distance
        )[0])
    return {
        "seed": seed,
        "nav_succeeded": nav_reason == "completed",
        "nav_reason": nav_reason,
        "post_nav_shadow_certified": actual_certification_reason == "certified",
        "post_nav_certification_reason": actual_certification_reason,
        "planned_base_pose": planned_base_pose.tolist(),
        "actual_base_pose": actual_base_pose.tolist(),
        "actual_base_tilt_rad": actual_base_tilt_rad,
        "base_position_error": float(
            np.linalg.norm(actual_base_pose[:2] - planned_base_pose[:2])
        ),
        "base_yaw_error": abs(
            wrap_angle(float(actual_base_pose[2] - planned_base_pose[2]))
        ),
        "task_target": task_target.tolist(),
        "push_target_in_approach_window": push_target_in_approach_window,
        "push_target_proxy_approach_ready": push_target_proxy_approach_ready,
        "push_target_in_controller_gate": push_target_in_controller_gate,
        "push_hand_local": push_hand_local,
        "push_hand_in_controller_gate": push_hand_in_controller_gate,
        "push_target_gate_and_shadow_passed": (
            actual_certification_reason == "certified"
            and push_target_in_controller_gate and push_hand_in_controller_gate
            if target_mode == "push-precontact" else None
        ),
        "planned_joint_limit_margin": (
            planned_result.joint_limit_margin if planned_result is not None else None
        ),
        "actual_kinematic_feasible": (
            actual_result.kinematic_feasible if actual_result is not None else False
        ),
        "actual_joint_limit_margin": (
            actual_result.joint_limit_margin if actual_result is not None else None
        ),
        "self_clearance_safe": (
            self_clearance.safe if self_clearance is not None else None
        ),
        "minimum_self_clearance": (
            self_clearance.minimum_clearance if self_clearance is not None else None
        ),
        "self_clearance_pair": (
            [self_clearance.arm_geometry, self_clearance.protected_geometry]
            if self_clearance is not None else None
        ),
        "self_clearance_bodies": (
            [self_clearance.arm_body, self_clearance.protected_body]
            if self_clearance is not None else None
        ),
        "support_safe": support.safe if support is not None else None,
        "supporting_feet": list(support.supporting_feet) if support is not None else None,
        "support_margin": support.support_margin if support is not None else None,
        "environment_clearance_checked": environment_clearance is not None,
        "environment_clearance_safe": (
            environment_clearance.safe if environment_clearance is not None else None
        ),
        "minimum_environment_clearance": (
            environment_clearance.minimum_clearance
            if environment_clearance is not None
            else None
        ),
        "sampled_arm_path": sampled_arm_path,
        "alternative_ik_diagnostic": alternative_ik_diagnostic,
        "hand_ik_diagnostic": hand_ik_diagnostic,
        "hand_target_grid": hand_target_grid,
        "frozen_environment_clearance_lower_bound": (
            environment_tube.clearance_lower_bound if environment_tube is not None else None
        ),
        "frozen_environment_tube_safe": (
            environment_tube.safe if environment_tube is not None else None
        ),
        "elapsed_seconds": float(runtime.data.time),
        "physical_initializations": 1,
        "min_base_height": monitor.min_height,
        "max_tilt_rad": monitor.max_tilt,
        "first_illegal_contact": monitor.first_illegal_contact,
        "policy_sha256": sha256(runtime.policy_path),
        "config_sha256": sha256(runtime.config_path),
        "profile_sha256": sha256(PROFILE_PATH),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--seeds", type=int, default=1)
    parser.add_argument("--seed-offset", type=int, default=0)
    parser.add_argument("--distance", type=float, default=0.60)
    parser.add_argument("--initial-settle-seconds", type=float, default=2.0)
    parser.add_argument("--post-nav-settle-seconds", type=float, default=1.0)
    parser.add_argument("--required-joint-limit-margin", type=float, default=0.05)
    parser.add_argument("--required-self-clearance", type=float, default=0.05)
    parser.add_argument("--required-support-margin", type=float, default=0.02)
    parser.add_argument("--scene", choices=("empty", "static-box"), default="empty")
    parser.add_argument("--static-box-position", type=float, nargs=3, default=(1.40, 0.40, 0.25))
    parser.add_argument("--static-box-size", type=float, nargs=3, default=(0.50, 0.50, 0.50))
    parser.add_argument("--static-box-yaw", type=float, default=0.0)
    parser.add_argument("--required-environment-clearance", type=float, default=0.05)
    parser.add_argument("--tube-base-translation-bound", type=float, default=0.0)
    parser.add_argument("--tube-base-yaw-bound", type=float, default=0.0)
    parser.add_argument("--tube-box-error-bound", type=float, default=0.0)
    parser.add_argument("--diagnostic-ik-multistart", action="store_true")
    parser.add_argument("--diagnostic-hand-target-grid", action="store_true")
    parser.add_argument("--diagnostic-base-translation-error", type=float, default=0.0)
    parser.add_argument("--diagnostic-base-yaw-error", type=float, default=0.0)
    parser.add_argument("--target-offset", type=float, nargs=3, default=(0.06, 0.0, 0.0))
    parser.add_argument("--target-mode", choices=("nominal-offset", "push-precontact"), default="nominal-offset")
    parser.add_argument("--push-approach-distance", type=float, default=0.10)
    parser.add_argument("--push-target-height-offset", type=float, default=0.0)
    parser.add_argument("--nav-front-standoff", type=float, default=0.65)
    parser.add_argument("--nav-lateral-offset", type=float, default=0.0)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error(f"Refusing to overwrite {args.output_json}")
    if args.seeds < 1 or args.seed_offset < 0 or args.distance <= 0.0:
        parser.error("Require positive seeds, nonnegative seed offset, and positive distance")
    if not np.isfinite(
        [
            args.distance,
            args.initial_settle_seconds,
            args.post_nav_settle_seconds,
            args.required_joint_limit_margin,
            args.required_self_clearance,
            args.required_support_margin,
            args.static_box_yaw,
            args.required_environment_clearance,
            args.tube_base_translation_bound,
            args.tube_base_yaw_bound,
            args.tube_box_error_bound,
            args.diagnostic_base_translation_error,
            args.diagnostic_base_yaw_error,
            *args.static_box_position,
            *args.static_box_size,
            *args.target_offset,
            args.push_approach_distance,
            args.push_target_height_offset,
            args.nav_front_standoff,
            args.nav_lateral_offset,
        ]
    ).all() or min(
        args.initial_settle_seconds,
        args.post_nav_settle_seconds,
        args.required_joint_limit_margin,
        args.required_self_clearance,
        args.required_support_margin,
        args.required_environment_clearance,
        args.tube_base_translation_bound,
        args.tube_base_yaw_bound,
        args.tube_box_error_bound,
        args.diagnostic_base_translation_error,
        args.diagnostic_base_yaw_error,
        args.push_approach_distance,
        args.nav_front_standoff,
    ) < 0.0:
        parser.error("All thresholds and settle durations must be finite and non-negative")
    if args.target_mode == "push-precontact" and args.scene != "static-box":
        parser.error("PUSH precontact target requires a static-box scene")
    if args.diagnostic_ik_multistart and args.target_mode != "push-precontact":
        parser.error("Multi-start IK diagnostic requires a PUSH precontact target")
    if args.diagnostic_hand_target_grid and args.target_mode != "push-precontact":
        parser.error("Hand target grid requires a PUSH precontact target")
    if (args.diagnostic_base_translation_error or args.diagnostic_base_yaw_error) and not args.diagnostic_hand_target_grid:
        parser.error("Base perturbation diagnostic requires the hand target grid")
    if args.target_mode == "push-precontact" and (args.push_approach_distance <= 0 or args.nav_front_standoff <= 0):
        parser.error("PUSH approach distance and NAV front standoff must be positive")
    if args.target_mode == "push-precontact" and abs(args.push_target_height_offset) > args.static_box_size[2] / 2:
        parser.error("PUSH target height must stay within the box face")
    if args.tube_base_yaw_bound > math.pi:
        parser.error("Tube yaw error bound must be at most pi radians")
    if args.scene != "static-box" and any((args.tube_base_translation_bound, args.tube_base_yaw_bound, args.tube_box_error_bound)):
        parser.error("Environment tube requires a static-box scene")

    torch.set_num_threads(1)
    results = [
        run_episode(
            seed,
            distance=args.distance,
            initial_settle_seconds=args.initial_settle_seconds,
            post_nav_settle_seconds=args.post_nav_settle_seconds,
            required_joint_limit_margin=args.required_joint_limit_margin,
            required_self_clearance=args.required_self_clearance,
            required_support_margin=args.required_support_margin,
            scene=args.scene,
            static_box_position=np.asarray(args.static_box_position, dtype=np.float64),
            static_box_size=np.asarray(args.static_box_size, dtype=np.float64),
            static_box_yaw=args.static_box_yaw,
            required_environment_clearance=args.required_environment_clearance,
            target_offset=np.asarray(args.target_offset, dtype=np.float64),
            target_mode=args.target_mode,
            push_approach_distance=args.push_approach_distance,
            nav_front_standoff=args.nav_front_standoff,
            nav_lateral_offset=args.nav_lateral_offset,
            push_target_height_offset=args.push_target_height_offset,
            tube_base_translation_bound=args.tube_base_translation_bound,
            tube_base_yaw_bound=args.tube_base_yaw_bound,
            tube_box_error_bound=args.tube_box_error_bound,
            diagnostic_ik_multistart=args.diagnostic_ik_multistart,
            diagnostic_hand_target_grid=args.diagnostic_hand_target_grid,
            diagnostic_base_translation_error=args.diagnostic_base_translation_error,
            diagnostic_base_yaw_error=args.diagnostic_base_yaw_error,
        )
        for seed in range(args.seed_offset, args.seed_offset + args.seeds)
    ]
    root = Path(__file__).resolve().parent
    source_paths = (
        Path(__file__),
        root / "check_piper_navigation.py",
        root / "check_piper_locomotion.py",
        root / "reconfigurable_navigation/piper_locomotion_runtime.py",
        root / "reconfigurable_navigation/reachability/oracle.py",
        root / "reconfigurable_navigation/reachability/clearance.py",
        root / "reconfigurable_navigation/reachability/support.py",
        root / "reconfigurable_navigation/reachability/scenes.py",
        root / "reconfigurable_navigation/piper_box_runtime.py",
        root / "reconfigurable_navigation/box_push_runtime.py",
            root.parent / "source/LeggedManip_Lab/LeggedManip_Lab/tasks/manager_based/leggedmanip_lab/mdp/box_push_control.py",
        CONTROL_PATH,
    )
    report = {
        "schema_version": 1,
        "scope": (
            "NAV arrival shadow revalidation of position IK, joint margin, self-clearance, "
            "quasi-static support, and static-box environment clearance when selected; "
            "frozen environment tube is a separate conditional bound for fixed arm/legs, "
            "fixed base height and roll/pitch, bounded planar base error, and bounded "
            "displacement of every protected box geometry; "
            "PUSH precontact mode uses only the position-mode target of a fixed box proxy; "
                        "proxy approach readiness tests target coordinates against the PUSH side gate, "
                        "not the actual offset hand tip or reachable pose; "
            "joint gate-and-shadow result also checks the offset PUSH hand tool point; "
            "fixed-arm base perturbations check endpoints and 101-point joint-linear paths "
            "at six axial offsets, not continuous errors, swept-volume clearance, tracking, "
            "or re-solved IK; "
            "no pose IK, moving box, contact handoff, or deployment approval"
        ),
        "thresholds": {
            "joint_limit_margin": args.required_joint_limit_margin,
            "self_clearance": args.required_self_clearance,
            "quasistatic_support_margin": args.required_support_margin,
            "environment_clearance": args.required_environment_clearance,
        },
        "target_offset": list(args.target_offset) if args.target_mode == "nominal-offset" else None,
        "target_mode": args.target_mode,
        "diagnostic_ik_multistart": args.diagnostic_ik_multistart,
        "diagnostic_hand_target_grid": args.diagnostic_hand_target_grid,
        "diagnostic_fixed_arm_base_error": {
            "translation": args.diagnostic_base_translation_error,
            "yaw": args.diagnostic_base_yaw_error,
        },
        "push_approach_distance": args.push_approach_distance if args.target_mode == "push-precontact" else None,
        "push_target_height_offset": args.push_target_height_offset if args.target_mode == "push-precontact" else None,
        "frozen_environment_tube_budgets": {
            "base_translation": args.tube_base_translation_bound,
            "base_yaw": args.tube_base_yaw_bound,
            "box_geometry": args.tube_box_error_bound,
        } if args.scene == "static-box" else None,
        "nav_front_standoff": args.nav_front_standoff if args.target_mode == "push-precontact" else None,
        "nav_lateral_offset": args.nav_lateral_offset if args.target_mode == "push-precontact" else None,
        "scene": (
            {"kind": "empty"}
            if args.scene == "empty"
            else {
                "kind": "static-box",
                "body": STATIC_BOX_BODY,
                "position": list(args.static_box_position),
                "size": list(args.static_box_size),
                "yaw": args.static_box_yaw,
            }
        ),
        "settle_seconds": {
            "initial": args.initial_settle_seconds,
            "post_navigation": args.post_nav_settle_seconds,
        },
        "shadow_certified_episodes": sum(
            result["post_nav_shadow_certified"] for result in results
        ),
        "evaluated_episodes": len(results),
        "failure_reasons": dict(
            Counter(
                result["post_nav_certification_reason"]
                for result in results
                if not result["post_nav_shadow_certified"]
            )
        ),
        "source_sha256": {str(path): sha256(path) for path in source_paths},
        "results": results,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x") as destination:
        json.dump(report, destination, indent=2, allow_nan=False)
        destination.write("\n")
    print(
        json.dumps(
            {
                "shadow_certified_episodes": report["shadow_certified_episodes"],
                "evaluated_episodes": report["evaluated_episodes"],
                "failure_reasons": report["failure_reasons"],
            },
            indent=2,
        )
    )
    return 0 if all(result["nav_succeeded"] for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())