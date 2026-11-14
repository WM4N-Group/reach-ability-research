"""Contract checks for finite-grid PIPER reachability certificates."""

import unittest

from evaluate_piper_reachability import _robust_metrics


def record(
    *,
    target_x: float,
    offset_x: float,
    environment_safe: bool = True,
    support_safe: bool = True,
) -> dict[str, object]:
    return {
        "scene_case": "synthetic-scene",
        "nominal_base_pose": [0.0, 0.0, 0.0],
        "target_position": [target_x, 0.0, 0.5],
        "base_pose_offset": [offset_x, 0.0, 0.0],
        "kinematic_feasible": True,
        "joint_limit_margin": 0.10,
        "self_clearance_checked": True,
        "self_clearance_safe": True,
        "environment_clearance_checked": True,
        "environment_clearance_safe": environment_safe,
        "support_checked": True,
        "support_margin": 0.08 if support_safe else -0.01,
        "required_support_margin": 0.02,
        "support_safe": support_safe,
        "minimum_self_clearance": 0.08,
        "minimum_environment_clearance": 0.08 if environment_safe else -0.01,
    }


class PiperReachabilityEvaluationChecks(unittest.TestCase):
    def test_certifies_only_when_every_offset_in_the_grid_is_safe(self):
        metrics = _robust_metrics(
            [
                record(target_x=0.2, offset_x=-0.04),
                record(target_x=0.2, offset_x=0.04),
                record(target_x=0.3, offset_x=-0.04),
                record(target_x=0.3, offset_x=0.04, environment_safe=False),
            ],
            threshold=0.05,
        )
        self.assertEqual(metrics["robust_query_total"], 2)
        self.assertEqual(metrics["robust_geometric_certified"], 1)
        self.assertEqual(metrics["robust_geometric_rejected"], 1)
        self.assertEqual(
            metrics["base_pose_offset_grid"],
            [[-0.04, 0.0, 0.0], [0.04, 0.0, 0.0]],
        )

    def test_rejects_queries_with_an_incomplete_offset_grid(self):
        with self.assertRaisesRegex(ValueError, "same complete"):
            _robust_metrics(
                [
                    record(target_x=0.2, offset_x=-0.04),
                    record(target_x=0.2, offset_x=0.04),
                    record(target_x=0.3, offset_x=-0.04),
                ],
                threshold=0.05,
            )

    def test_support_requirement_rejects_an_unsafe_support_scenario(self):
        metrics = _robust_metrics(
            [
                record(target_x=0.2, offset_x=-0.04),
                record(target_x=0.2, offset_x=0.04, support_safe=False),
            ],
            threshold=0.05,
            require_quasistatic_support=True,
        )
        self.assertTrue(metrics["quasistatic_support_required"])
        self.assertEqual(metrics["robust_geometric_certified"], 0)


if __name__ == "__main__":
    unittest.main()