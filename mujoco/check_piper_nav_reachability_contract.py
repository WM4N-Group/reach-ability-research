"""Check NAV shadow certification and static-box collision attribution."""

import numpy as np
import torch

from check_piper_nav_reachability import run_episode


def episode(
    scene: str,
    position: tuple[float, float, float],
    size: tuple[float, float, float],
    target_offset: tuple[float, float, float] = (0.06, 0.0, 0.0),
    target_mode: str = "nominal-offset",
    push_target_height_offset: float = 0.0,
    tube_base_translation_bound: float = 0.0,
    tube_base_yaw_bound: float = 0.0,
    tube_box_error_bound: float = 0.0,
    seed: int = 0,
    nav_front_standoff: float = 0.25,
    nav_lateral_offset: float = 0.0,
    diagnostic_hand_target_grid: bool = False,
    diagnostic_ik_multistart: bool = False,
    diagnostic_base_translation_error: float = 0.0,
    diagnostic_base_yaw_error: float = 0.0,
) -> dict:
    return run_episode(
        seed,
        distance=0.60,
        initial_settle_seconds=2.0,
        post_nav_settle_seconds=1.0,
        required_joint_limit_margin=0.05,
        required_self_clearance=0.05,
        required_support_margin=0.02,
        scene=scene,
        static_box_position=np.array(position),
        static_box_size=np.array(size),
        static_box_yaw=0.0,
        required_environment_clearance=0.05,
        target_offset=np.array(target_offset),
        target_mode=target_mode,
        push_approach_distance=0.10,
        nav_front_standoff=nav_front_standoff,
        nav_lateral_offset=nav_lateral_offset,
        push_target_height_offset=push_target_height_offset,
        tube_base_translation_bound=tube_base_translation_bound,
        tube_base_yaw_bound=tube_base_yaw_bound,
        tube_box_error_bound=tube_box_error_bound,
        diagnostic_hand_target_grid=diagnostic_hand_target_grid,
        diagnostic_ik_multistart=diagnostic_ik_multistart,
        diagnostic_base_translation_error=diagnostic_base_translation_error,
        diagnostic_base_yaw_error=diagnostic_base_yaw_error,
    )


def main() -> None:
    torch.set_num_threads(1)
    empty = episode("empty", (1.4, 0.4, 0.25), (0.5, 0.5, 0.5))
    safe = episode("static-box", (1.4, 0.4, 0.25), (0.5, 0.5, 0.5))
    rejected = episode("static-box", (0.8, 0.17, 0.57), (0.2, 0.24, 0.2))
    collision = episode("static-box", (0.0, 0.0, 0.35), (0.4, 0.4, 0.4))
    shifted = episode("static-box", (1.4, 0.4, 0.25), (0.5, 0.5, 0.5), (0.03, 0.03, 0.02))
    precontact = episode("static-box", (0.9, 0.0, 0.57), (0.2, 0.2, 0.2), target_mode="push-precontact")
    grounded = episode("static-box", (0.9, 0.0, 0.1), (0.2, 0.2, 0.2), target_mode="push-precontact")
    raised = episode("static-box", (0.9, 0.0, 0.1), (0.2, 0.2, 0.2), target_mode="push-precontact", push_target_height_offset=0.09)
    bounded = episode("static-box", (1.4, 0.4, 0.25), (0.5, 0.5, 0.5), tube_base_translation_bound=0.01, tube_base_yaw_bound=0.01, tube_box_error_bound=0.01)
    excessive = episode("static-box", (1.4, 0.4, 0.25), (0.5, 0.5, 0.5), tube_base_translation_bound=0.5)
    perturbed = episode(
        "static-box", (0.9, 0.0, 0.1), (0.2, 0.2, 0.2),
        target_mode="push-precontact", seed=424, nav_front_standoff=0.51,
        nav_lateral_offset=0.08, diagnostic_hand_target_grid=True,
        diagnostic_ik_multistart=True, diagnostic_base_translation_error=0.005,
        diagnostic_base_yaw_error=0.01,
    )
    assert empty["nav_succeeded"] and empty["post_nav_shadow_certified"]
    assert empty["push_target_gate_and_shadow_passed"] is None
    assert not empty["environment_clearance_checked"]
    assert safe["nav_succeeded"] and safe["post_nav_shadow_certified"]
    assert safe["actual_base_tilt_rad"] is not None and safe["actual_base_tilt_rad"] >= 0.0
    assert safe["environment_clearance_safe"] and safe["first_illegal_contact"] is None
    assert rejected["nav_succeeded"] and not rejected["post_nav_shadow_certified"]
    assert rejected["post_nav_certification_reason"] == "environment_clearance"
    assert rejected["actual_kinematic_feasible"] and rejected["self_clearance_safe"]
    assert rejected["support_safe"] and rejected["first_illegal_contact"] is None
    assert rejected["minimum_environment_clearance"] < 0.05
    assert np.allclose(safe["actual_base_pose"], rejected["actual_base_pose"])
    assert not collision["nav_succeeded"]
    assert collision["nav_reason"] == "static_box_contact"
    assert collision["actual_base_tilt_rad"] is None
    assert collision["first_illegal_contact"] is not None
    assert shifted["nav_succeeded"] and shifted["post_nav_shadow_certified"]
    assert np.allclose(np.array(shifted["task_target"]) - safe["task_target"], [-0.03, 0.03, 0.02])
    assert np.allclose(precontact["task_target"], [0.7, 0.0, 0.57])
    assert precontact["nav_succeeded"] and precontact["post_nav_shadow_certified"]
    assert precontact["push_target_in_controller_gate"] is True
    assert precontact["push_hand_in_controller_gate"] is False
    assert precontact["push_target_gate_and_shadow_passed"] is False
    assert precontact["first_illegal_contact"] is None
    assert grounded["nav_succeeded"] and grounded["actual_kinematic_feasible"]
    assert grounded["push_target_in_controller_gate"] is True
    assert grounded["push_hand_in_controller_gate"] is False
    assert grounded["push_hand_local"][0] < -0.26
    assert grounded["push_target_gate_and_shadow_passed"] is False
    assert grounded["post_nav_certification_reason"] == "self_clearance"
    assert grounded["minimum_self_clearance"] < 0.05
    assert grounded["self_clearance_pair"] is not None
    assert grounded["self_clearance_bodies"] is not None
    assert grounded["first_illegal_contact"] is None
    assert raised["nav_succeeded"] and np.allclose(raised["task_target"], [0.7, 0.0, 0.19])
    assert raised["push_target_in_controller_gate"] is False
    assert raised["push_target_gate_and_shadow_passed"] is False
    assert raised["supporting_feet"] is not None
    assert bounded["post_nav_shadow_certified"] and bounded["frozen_environment_tube_safe"]
    assert bounded["frozen_environment_clearance_lower_bound"] <= bounded["minimum_environment_clearance"]
    assert excessive["post_nav_shadow_certified"] and not excessive["frozen_environment_tube_safe"]
    assert empty["sampled_arm_path"]["samples"] == 11
    assert empty["sampled_arm_path"]["minimum_environment_clearance"] is None
    assert safe["sampled_arm_path"]["minimum_self_clearance"] <= safe["minimum_self_clearance"] + 1e-9
    assert safe["sampled_arm_path"]["minimum_environment_clearance"] <= safe["minimum_environment_clearance"] + 1e-9
    assert collision["sampled_arm_path"] is None
    candidates = [
        candidate for candidate in perturbed["hand_target_grid"]
        if candidate["sampled_arm_path"] is not None
        and candidate["sampled_arm_path"]["sampled_constraints_passed"]
    ]
    assert perturbed["nav_succeeded"] and candidates
    assert all(len(candidate["fixed_arm_base_perturbations"]) == 6 for candidate in candidates)
    paths = [
        offset["sampled_arm_path"]
        for candidate in candidates
        for offset in candidate["fixed_arm_base_perturbations"]
    ]
    assert all(path["samples"] == 101 for path in paths)
    assert all(
        offset["sampled_arm_path"]["minimum_self_clearance"]
        <= offset["minimum_self_clearance"] + 1e-9
        and offset["sampled_arm_path"]["minimum_environment_clearance"]
        <= offset["minimum_environment_clearance"] + 1e-9
        and offset["sampled_arm_path"]["minimum_support_margin"]
        <= offset["support_margin"] + 1e-9
        for candidate in candidates
        for offset in candidate["fixed_arm_base_perturbations"]
    )
    assert any(all(offset["endpoint_passed"] for offset in candidate["fixed_arm_base_perturbations"])
               for candidate in candidates)
    assert any(not offset["hand_gate_passed"] for candidate in candidates
               for offset in candidate["fixed_arm_base_perturbations"])
    print("NAV reachability contract: 11/11 passed")


if __name__ == "__main__":
    main()