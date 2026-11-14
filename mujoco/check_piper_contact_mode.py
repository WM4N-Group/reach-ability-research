"""Checks for conditional Isaac PUSH contact geometry classification."""

import json
from pathlib import Path
import unittest

from reconfigurable_navigation.reachability.contact_mode import (
    FrontContactGeometry,
    classify_contact_maintenance_geometry,
    classify_front_contact_geometry,
    classify_loaded_front_contact_geometry,
)


GEOMETRY = FrontContactGeometry((1.2, 1.2, 0.2), height_margin_m=0.01)


def classify(point, radius, *, observed=True):
    return classify_front_contact_geometry(
        GEOMETRY, contact_observed=observed,
        contact_point_box_m=point, local_position_error_bound_m=radius,
    )


def classify_loaded(point, sensor_radius, spread, *, observed=True):
    return classify_loaded_front_contact_geometry(
        GEOMETRY, contact_observed=observed,
        sensor_point_box_m=point, sensor_position_error_bound_m=sensor_radius,
        loaded_point_spread_bound_m=spread,
    )


def classify_maintenance(point, sensor_radius, spread, future_reach, *,
                         observed=True, ever_loaded=True, previous_loaded=True):
    return classify_contact_maintenance_geometry(
        GEOMETRY, contact_observed=observed,
        ever_loaded_before_current=ever_loaded,
        previous_substep_loaded=previous_loaded,
        sensor_point_box_m=point,
        sensor_position_error_bound_m=sensor_radius,
        loaded_point_spread_bound_m=spread,
        decision_horizon_s=0.02,
        future_loaded_point_reach_bound_m=future_reach,
    )


class ContactModeTests(unittest.TestCase):
    def test_no_contact_is_not_illegal_contact(self):
        self.assertEqual(classify(None, None, observed=False).state, "await_contact")

    def test_missing_bound_and_invalid_measurement_abstain(self):
        self.assertEqual(classify((-0.6, 0, 0), None).state, "abstain_missing_error_bound")
        self.assertEqual(classify((float("nan"), 0, 0), 0).state, "invalid_contact_measurement")
        with self.assertRaises(ValueError):
            classify((-0.6, 0, 0), -0.001)

    def test_strict_front_and_lateral_edges_differ_from_inclusive_height_edge(self):
        self.assertEqual(classify((-0.58, 0, 0), 0).state,
                         "outside_geometry_for_all_positions")
        self.assertEqual(classify((-0.6, 0.6, 0), 0).state,
                         "outside_geometry_for_all_positions")
        self.assertEqual(classify((-0.6, 0, 0.0901), 0).state,
                         "inside_geometry_for_all_positions")

    def test_interval_quantifiers_across_front_and_top_boundaries(self):
        self.assertEqual(classify((-0.6, 0, 0.07), 0.01).state,
                         "inside_geometry_for_all_positions")
        self.assertEqual(classify((-0.6, 0, 0.085), 0.01).state,
                         "uncertain_geometry")
        self.assertEqual(classify((-0.54, 0, 0), 0.02).state,
                         "outside_geometry_for_all_positions")
        self.assertEqual(classify((-0.54, 0, 0), 0.05).state,
                         "uncertain_geometry")

    def test_sensor_mean_cannot_certify_every_loaded_point_without_spread(self):
        sensor = (-0.6, 0, 0.08)
        loaded = (-0.6, 0, 0.105)
        self.assertEqual(classify(sensor, 0).state,
                         "inside_geometry_for_all_positions")
        self.assertEqual(classify(loaded, 0).state,
                         "outside_geometry_for_all_positions")
        self.assertEqual(classify_loaded(sensor, 0, None).state,
                         "abstain_missing_loaded_point_spread_bound")
        self.assertEqual(classify_loaded(sensor, None, 0.025).state,
                         "abstain_missing_error_bound")
        self.assertEqual(classify_loaded(sensor, 0, 0.025).state,
                         "uncertain_geometry")
        self.assertEqual(classify_loaded(sensor, 0.005, 0.005).local_position_error_bound_m,
                         0.01)

    def test_loaded_bound_edges_and_no_load(self):
        self.assertEqual(classify_loaded(None, None, None, observed=False).state,
                         "await_contact")
        self.assertEqual(classify_loaded((float("nan"), 0, 0), 0, None).state,
                         "invalid_contact_measurement")
        self.assertEqual(classify_loaded((-0.6, 0, 0.0901), 0, 0).state,
                         "inside_geometry_for_all_positions")
        self.assertEqual(classify_loaded((-0.58, 0, 0), 0, 0).state,
                         "outside_geometry_for_all_positions")
        self.assertEqual(classify_loaded((-0.6, 0, 0.07), 0.005, 0.005).state,
                         "inside_geometry_for_all_positions")
        self.assertEqual(classify_loaded((-0.54, 0, 0), 0.005, 0.005).state,
                         "outside_geometry_for_all_positions")
        self.assertEqual(classify_loaded((-0.6, 0, 0.11), 0, 0.0199).state,
                         "uncertain_geometry")
        with self.assertRaises(ValueError):
            classify_loaded((-0.6, 0, 0), 0, -0.001)
        with self.assertRaises(ValueError):
            classify_loaded((-0.6, 0, 0), 0, float("inf"))

    def test_seen_5904_is_nominally_outside_without_claiming_calibration(self):
        evidence = Path(__file__).resolve().parents[1] / (
            "evidence/2026-10-08/invalid-hand-contact-5904-known-state-results.json"
        )
        detail = json.loads(evidence.read_text(encoding="utf-8"))["detail"]
        geometry = FrontContactGeometry(tuple(detail["box_size_m"]),
                                        detail["height_margin_m"])
        result = classify_front_contact_geometry(
            geometry, contact_observed=True,
            contact_point_box_m=tuple(detail["contact_pos_box_m"]),
            local_position_error_bound_m=0.0,
        )
        self.assertEqual(result.state, "outside_geometry_for_all_positions")
        self.assertAlmostEqual(result.nominal_margins_m[0], -0.0114867258071899)
        self.assertAlmostEqual(result.nominal_margins_m[2], -0.01109228065013885)
        self.assertFalse(result.contact_authorized)
        self.assertEqual(classify_front_contact_geometry(
            geometry, contact_observed=True,
            contact_point_box_m=tuple(detail["contact_pos_box_m"]),
            local_position_error_bound_m=None,
        ).state, "abstain_missing_error_bound")

        # The observed sensor point is not a calibrated envelope for loaded points.
        self.assertEqual(classify_loaded_front_contact_geometry(
            geometry, contact_observed=True,
            sensor_point_box_m=tuple(detail["contact_pos_box_m"]),
            sensor_position_error_bound_m=0.0,
            loaded_point_spread_bound_m=None,
        ).state, "abstain_missing_loaded_point_spread_bound")
        manifold = Path(__file__).resolve().parents[1] / (
            "evidence/2026-10-08/hand-contact-manifold-5904-known-state-results.json"
        )
        terminal = json.loads(manifold.read_text(encoding="utf-8"))[
            "force_above_1_n_events"
        ][-1]
        loaded_point = tuple(terminal["loaded_points"][0]["point_box_m"])
        self.assertGreater(max(abs(a - b) for a, b in zip(
            detail["contact_pos_box_m"], loaded_point)), 0.008)
        self.assertEqual(classify_front_contact_geometry(
            geometry, contact_observed=True, contact_point_box_m=loaded_point,
            local_position_error_bound_m=0.0,
        ).state, "outside_geometry_for_all_positions")

    def test_recontact_pending_has_no_loaded_point_anchor(self):
        result = classify_maintenance(None, None, None, None,
                                      observed=False, previous_loaded=False)
        self.assertEqual(result.phase, "recontact_pending")
        self.assertEqual(result.state, "abstain_no_loaded_anchor")
        self.assertFalse(result.contact_authorized)
        self.assertEqual(classify_maintenance(None, None, None, None, observed=False,
                                              ever_loaded=False, previous_loaded=False).phase,
                         "approach")
        with self.assertRaisesRegex(ValueError, "Zero-load manifold"):
            classify_maintenance((-0.6, 0, 0.09), 0, 0, 0,
                                 observed=False, previous_loaded=False)

    def test_contact_maintenance_requires_future_branch_enclosure(self):
        point = (-0.6, 0, 0.07)
        self.assertEqual(classify_maintenance(point, 0.001, 0.001, None).state,
                         "abstain_missing_future_loaded_reach_bound")
        safe = classify_maintenance(point, 0.001, 0.001, 0.005)
        self.assertEqual(safe.state, "future_loaded_geometry_inside_under_bound")
        self.assertAlmostEqual(safe.future_loaded_point_radius_m, 0.007)
        self.assertFalse(safe.contact_authorized)
        self.assertEqual(classify_maintenance((-0.6, 0, 0.088), 0.001, 0.001, 0.005).state,
                         "abstain_future_loaded_geometry_not_enclosed")
        with self.assertRaises(ValueError):
            classify_maintenance(point, 0, 0, -0.001)

    def test_seen_6303_recontact_edge_is_uncertain_without_tight_bounds(self):
        evidence = Path(__file__).resolve().parents[1] / (
            "evidence/2026-10-08/lateral-right-recontact-6301-6308-projection.json"
        )
        record = next(row for row in json.loads(evidence.read_text(encoding="utf-8"))["records"]
                      if row["seed"] == 6303)
        recontact = record["preceding_reacquisition"]
        self.assertEqual(recontact["unloaded_substeps"], 28)
        self.assertEqual(recontact["zero_force_substeps"], 28)
        self.assertEqual(recontact["unloaded_with_only_zero_force_manifold_substeps"], 28)
        self.assertTrue(recontact["same_control_step_as_first_illegal"])
        point = tuple(recontact["reacquisition_contact_pos_box_m"])
        self.assertEqual(classify_maintenance(point, None, None, None,
                                              previous_loaded=False).state,
                         "abstain_missing_error_bound")
        self.assertEqual(classify_maintenance(point, 0.0001, 0, 0,
                                              previous_loaded=False).state,
                         "uncertain_geometry")
        retrospective_displacement = abs(
            record["first_illegal_contact_pos_box_m"][2] - point[2])
        self.assertEqual(classify_maintenance(point, 0, 0, retrospective_displacement,
                                              previous_loaded=False).state,
                         "abstain_future_loaded_geometry_not_enclosed")


if __name__ == "__main__":
    unittest.main()
