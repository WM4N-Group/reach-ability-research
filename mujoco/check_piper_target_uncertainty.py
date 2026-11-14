"""Geometry and scope checks for the static-box target-error bound."""

from __future__ import annotations

import unittest

import mujoco
import numpy as np

from reconfigurable_navigation.reachability import (
    STATIC_BOX_BODY,
    PiperArmClearanceChecker,
    PiperPositionReachabilityOracle,
    PiperSelfClearanceChecker,
    ReachabilityQuery,
    bound_static_box_precontact_errors,
    bound_static_box_target_error,
    certify_frozen_precontact_region,
    make_static_box_navigation_runtime,
)


def _yaw_rotation(yaw: float) -> np.ndarray:
    cosine, sine = np.cos(yaw), np.sin(yaw)
    return np.array([[cosine, -sine, 0.0], [sine, cosine, 0.0], [0.0, 0.0, 1.0]])


class TargetUncertaintyChecks(unittest.TestCase):
    def test_paired_bounds_feed_actual_piper_frozen_certificate(self) -> None:
        box_position = np.array([0.9, 0.0, 0.1])
        box_size = np.array([0.2, 0.2, 0.2])
        runtime = make_static_box_navigation_runtime(
            seed=3, box_position=box_position, box_size=box_size, box_yaw=0.0,
        )
        oracle = PiperPositionReachabilityOracle(runtime)
        self_checker = PiperSelfClearanceChecker(runtime)
        environment_checker = PiperArmClearanceChecker(
            runtime, protected_body_names=frozenset({STATIC_BOX_BODY}),
        )
        base = np.zeros(3)
        arm = runtime.default_qpos[12:].copy()
        hand, hand_quaternion = oracle.end_effector_pose(
            ReachabilityQuery(base, np.zeros(3)), arm,
        )
        local_target = hand - box_position
        bounds = bound_static_box_precontact_errors(
            local_target, box_size,
            box_translation_error_bound_m=0.002,
            box_yaw_error_bound_rad=0.03,
            local_target_error_bound_m=0.0005,
        )
        certificate = certify_frozen_precontact_region(
            oracle, self_checker, environment_checker,
            ReachabilityQuery(base, hand), arm,
            target_quaternion=hand_quaternion,
            translation_radius=0.0, yaw_radius=0.0,
            target_position_error_radius=bounds.target_position_error_radius,
            target_orientation_error_radius=0.0,
            external_geometry_error_radius=bounds.external_geometry_error_radius,
            required_position_tolerance=0.1, required_orientation_tolerance=0.1,
            required_joint_margin=0.0, required_self_clearance=0.0,
            required_environment_clearance=0.0,
        )
        self.assertTrue(certificate.geometric_precontact_safe)
        geometry = runtime.model.geom(STATIC_BOX_BODY).id
        nominal_geom_pos = runtime.model.geom_pos[geometry].copy()
        nominal_geom_quat = runtime.model.geom_quat[geometry].copy()
        try:
            for yaw, translation in (
                (0.03, np.array([0.002, 0.0, 0.0])),
                (-0.03, np.array([0.0, -0.002, 0.0])),
            ):
                runtime.model.geom_pos[geometry] = nominal_geom_pos + translation
                runtime.model.geom_quat[geometry] = [
                    np.cos(yaw / 2), 0.0, 0.0, np.sin(yaw / 2),
                ]
                mujoco.mj_forward(runtime.model, runtime.data)
                actual_target = (
                    box_position + translation + _yaw_rotation(yaw)
                    @ (local_target + np.array([0.0005, 0.0, 0.0]))
                )
                self.assertLessEqual(
                    np.linalg.norm(hand - actual_target),
                    certificate.position_error_upper_bound + 1e-10,
                )
                actual_clearance = environment_checker.evaluate(
                    base, arm, required_clearance=0.0,
                )
                self.assertGreaterEqual(
                    actual_clearance.minimum_clearance,
                    certificate.environment_tube.clearance_lower_bound - 1e-10,
                )
        finally:
            runtime.model.geom_pos[geometry] = nominal_geom_pos
            runtime.model.geom_quat[geometry] = nominal_geom_quat
            mujoco.mj_forward(runtime.model, runtime.data)

    def test_paired_bounds_cover_mujoco_box_vertices_and_target(self) -> None:
        size = np.array([0.2, 0.24, 0.3])
        model = mujoco.MjModel.from_xml_string(
            '<mujoco><worldbody><geom name="box" type="box" '
            'size="0.1 0.12 0.15" pos="0.8 0.1 0.3"/>'
            '</worldbody></mujoco>'
        )
        data = mujoco.MjData(model)
        geom = model.geom("box").id
        np.testing.assert_allclose(model.geom_size[geom], size / 2.0)
        local_target = np.array([-0.16225, 0.02, 0.03])
        translation_limit, yaw_limit, command_limit = 0.002, 0.03, 0.0005
        bounds = bound_static_box_precontact_errors(
            local_target, size,
            box_translation_error_bound_m=translation_limit,
            box_yaw_error_bound_rad=yaw_limit,
            local_target_error_bound_m=command_limit,
        )
        self.assertAlmostEqual(bounds.box_corner_xy_radius_m, np.hypot(0.1, 0.12))
        self.assertFalse(bounds.handoff_certified)
        corners = np.array([
            [sx * size[0] / 2, sy * size[1] / 2, sz * size[2] / 2]
            for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)
        ])
        mujoco.mj_forward(model, data)
        nominal_vertices = data.geom_xpos[geom] + corners @ data.geom_xmat[geom].reshape(3, 3).T
        nominal_target = data.geom_xpos[geom] + local_target
        for yaw in (-yaw_limit, 0.0, yaw_limit):
            for translation in (
                np.array([translation_limit, 0.0, 0.0]),
                np.array([0.0, -translation_limit, 0.0]),
                np.array([0.0, 0.0, translation_limit]),
            ):
                model.geom_pos[geom] = np.array([0.8, 0.1, 0.3]) + translation
                model.geom_quat[geom] = [np.cos(yaw / 2), 0.0, 0.0, np.sin(yaw / 2)]
                mujoco.mj_forward(model, data)
                actual_vertices = data.geom_xpos[geom] + corners @ data.geom_xmat[geom].reshape(3, 3).T
                vertex_errors = np.linalg.norm(actual_vertices - nominal_vertices, axis=1)
                self.assertLessEqual(max(vertex_errors), bounds.external_geometry_error_radius + 1e-12)
                actual_target = (data.geom_xpos[geom]
                                 + data.geom_xmat[geom].reshape(3, 3)
                                 @ (local_target + np.array([command_limit, 0.0, 0.0])))
                self.assertLessEqual(
                    np.linalg.norm(actual_target - nominal_target),
                    bounds.target_position_error_radius + 1e-12,
                )

    def test_paired_bounds_reject_invalid_size_and_preserve_zero_error(self) -> None:
        with self.assertRaisesRegex(ValueError, "box_size"):
            bound_static_box_precontact_errors(
                np.zeros(3), np.array([0.2, 0.0, 0.3]),
                box_translation_error_bound_m=0.0,
                box_yaw_error_bound_rad=0.0,
                local_target_error_bound_m=0.0,
            )
        bounds = bound_static_box_precontact_errors(
            np.zeros(3), np.array([0.2, 0.2, 0.3]),
            box_translation_error_bound_m=0.0,
            box_yaw_error_bound_rad=0.0,
            local_target_error_bound_m=0.0,
        )
        self.assertEqual(bounds.target_position_error_radius, 0.0)
        self.assertEqual(bounds.external_geometry_error_radius, 0.0)

    def test_bound_covers_joint_translation_yaw_and_local_command_errors(self) -> None:
        target = np.array([-0.16225, 0.0, 0.02])
        translation_limit = 0.002
        yaw_limit = 0.02
        command_limit = 0.0005
        result = bound_static_box_target_error(
            target,
            box_translation_error_bound_m=translation_limit,
            box_yaw_error_bound_rad=yaw_limit,
            local_target_error_bound_m=command_limit,
        )
        nominal = np.array([0.9, 0.1, 0.12]) + _yaw_rotation(-0.03) @ target
        for direction in (np.array([1.0, 0.0, 0.0]),
                          np.array([0.0, 1.0, 0.0]),
                          np.array([0.0, 0.0, 1.0])):
            for yaw_shift in (-yaw_limit, 0.0, yaw_limit):
                for command_direction in (direction, -direction):
                    actual = (
                        np.array([0.9, 0.1, 0.12]) + translation_limit * direction
                        + _yaw_rotation(-0.03 + yaw_shift)
                        @ (target + command_limit * command_direction)
                    )
                    self.assertLessEqual(
                        np.linalg.norm(actual - nominal),
                        result.world_target_error_upper_bound_m + 1e-12,
                    )
        self.assertFalse(result.handoff_certified)

    def test_pi_yaw_boundary_covers_opposite_point(self) -> None:
        result = bound_static_box_target_error(
            np.array([0.2, 0.0, 0.0]),
            box_translation_error_bound_m=0.0,
            box_yaw_error_bound_rad=np.pi,
            local_target_error_bound_m=0.0,
        )
        self.assertAlmostEqual(result.world_target_error_upper_bound_m, 0.4)

    def test_rejects_invalid_or_unbounded_inputs(self) -> None:
        with self.assertRaisesRegex(ValueError, "local_target"):
            bound_static_box_target_error(
                np.array([np.nan, 0.0, 0.0]),
                box_translation_error_bound_m=0.0,
                box_yaw_error_bound_rad=0.0,
                local_target_error_bound_m=0.0,
            )
        with self.assertRaisesRegex(ValueError, "yaw"):
            bound_static_box_target_error(
                np.zeros(3),
                box_translation_error_bound_m=0.0,
                box_yaw_error_bound_rad=np.pi + 0.01,
                local_target_error_bound_m=0.0,
            )
        with self.assertRaisesRegex(ValueError, "translation"):
            bound_static_box_target_error(
                np.zeros(3),
                box_translation_error_bound_m=-0.01,
                box_yaw_error_bound_rad=0.0,
                local_target_error_bound_m=0.0,
            )


if __name__ == "__main__":
    unittest.main()
