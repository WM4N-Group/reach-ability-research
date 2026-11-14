"""Conditional geometry classification for the frozen Isaac PUSH front face."""

from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class FrontContactGeometry:
    """Isaac valid_front_contact spatial limits, in the box-local frame (metres)."""

    box_size_m: tuple[float, float, float]
    height_margin_m: float
    front_tolerance_m: float = 0.02
    height_comparison_slack_m: float = 1.0e-4

    def __post_init__(self) -> None:
        if (len(self.box_size_m) != 3
                or any(not math.isfinite(value) or value <= 0 for value in self.box_size_m)
                or not math.isfinite(self.height_margin_m)
                or not 0 <= self.height_margin_m < self.box_size_m[2] / 2
                or not math.isfinite(self.front_tolerance_m)
                or self.front_tolerance_m <= 0
                or not math.isfinite(self.height_comparison_slack_m)
                or self.height_comparison_slack_m < 0):
            raise ValueError("Invalid front-contact geometry")


@dataclass(frozen=True)
class ContactGeometryAssessment:
    state: str
    nominal_margins_m: tuple[float, float, float] | None
    local_position_error_bound_m: float | None
    contact_authorized: bool = False


@dataclass(frozen=True)
class ContactMaintenanceAssessment:
    phase: str
    state: str
    nominal_margins_m: tuple[float, float, float] | None
    future_loaded_point_radius_m: float | None
    contact_authorized: bool = False


def classify_front_contact_geometry(
    geometry: FrontContactGeometry,
    *,
    contact_observed: bool,
    contact_point_box_m: tuple[float, float, float] | None,
    local_position_error_bound_m: float | None,
) -> ContactGeometryAssessment:
    """Classify every point in a caller-bounded L-infinity box around one contact.

    The bound must include contact sensing and box pose/transform error. Even an
    all-inside result says nothing about force, support, future contacts, or
    whether this bound has been calibrated. No-contact is a valid approach mode.
    """
    if not isinstance(geometry, FrontContactGeometry):
        raise TypeError("geometry must be FrontContactGeometry")
    if not isinstance(contact_observed, bool):
        raise TypeError("contact_observed must be Boolean")
    if not contact_observed:
        if contact_point_box_m is not None:
            raise ValueError("A contact point requires an observed contact")
        return ContactGeometryAssessment("await_contact", None, None)
    if (contact_point_box_m is None or len(contact_point_box_m) != 3
            or any(not math.isfinite(value) for value in contact_point_box_m)):
        return ContactGeometryAssessment("invalid_contact_measurement", None, None)
    x, y, z = contact_point_box_m
    sx, sy, sz = geometry.box_size_m
    margins = (
        geometry.front_tolerance_m - abs(x + sx / 2),
        sy / 2 - abs(y),
        sz / 2 - geometry.height_margin_m + geometry.height_comparison_slack_m - abs(z),
    )
    if local_position_error_bound_m is None:
        return ContactGeometryAssessment("abstain_missing_error_bound", margins, None)
    radius = float(local_position_error_bound_m)
    if not math.isfinite(radius) or radius < 0:
        raise ValueError("Local contact-point error bound must be finite and nonnegative")
    # X/Y are strict inequalities in the frozen Isaac rule; Z is inclusive.
    if margins[0] <= -radius or margins[1] <= -radius or margins[2] < -radius:
        state = "outside_geometry_for_all_positions"
    elif margins[0] > radius and margins[1] > radius and margins[2] >= radius:
        state = "inside_geometry_for_all_positions"
    else:
        state = "uncertain_geometry"
    return ContactGeometryAssessment(state, margins, radius)


def classify_loaded_front_contact_geometry(
    geometry: FrontContactGeometry,
    *,
    contact_observed: bool,
    sensor_point_box_m: tuple[float, float, float] | None,
    sensor_position_error_bound_m: float | None,
    loaded_point_spread_bound_m: float | None,
) -> ContactGeometryAssessment:
    """Classify all force-bearing points around a sensor aggregate point.

    Both bounds are externally certified box-local L-infinity bounds. The
    spread must cover every force-bearing point, including any offset caused
    by zero-force candidates contributing to the sensor aggregate. Observed
    contact means positive load, not merely a nonempty PhysX manifold.
    """
    sensor = classify_front_contact_geometry(
        geometry,
        contact_observed=contact_observed,
        contact_point_box_m=sensor_point_box_m,
        local_position_error_bound_m=sensor_position_error_bound_m,
    )
    if sensor.state in ("await_contact", "invalid_contact_measurement",
                        "abstain_missing_error_bound"):
        return sensor
    if loaded_point_spread_bound_m is None:
        return ContactGeometryAssessment(
            "abstain_missing_loaded_point_spread_bound", sensor.nominal_margins_m, None,
        )
    spread = float(loaded_point_spread_bound_m)
    if not math.isfinite(spread) or spread < 0:
        raise ValueError("Loaded-point spread bound must be finite and nonnegative")
    radius = sensor.local_position_error_bound_m + spread
    if not math.isfinite(radius):
        raise ValueError("Combined loaded-point error bound must be finite")
    return classify_front_contact_geometry(
        geometry,
        contact_observed=True,
        contact_point_box_m=sensor_point_box_m,
        local_position_error_bound_m=radius,
    )


def classify_contact_maintenance_geometry(
    geometry: FrontContactGeometry,
    *,
    contact_observed: bool,
    ever_loaded_before_current: bool,
    previous_substep_loaded: bool,
    sensor_point_box_m: tuple[float, float, float] | None,
    sensor_position_error_bound_m: float | None,
    loaded_point_spread_bound_m: float | None,
    decision_horizon_s: float,
    future_loaded_point_reach_bound_m: float | None,
) -> ContactMaintenanceAssessment:
    """Check the spatial part of contact maintenance through a bounded horizon.

    The external reach bound must enclose *every* future loaded point over
    decision_horizon_s relative to the current sensor point, including contact
    loss, creation, and manifold changes. A speed bound for one tracked point
    is insufficient. No-contact samples provide no loaded-point anchor, even
    if a zero-force manifold exists.
    """
    if not math.isfinite(decision_horizon_s) or decision_horizon_s <= 0:
        raise ValueError("Decision horizon must be positive and finite")
    if not isinstance(geometry, FrontContactGeometry):
        raise TypeError("geometry must be FrontContactGeometry")
    if not isinstance(contact_observed, bool):
        raise TypeError("contact_observed must be Boolean")
    if (not isinstance(ever_loaded_before_current, bool)
            or not isinstance(previous_substep_loaded, bool)):
        raise TypeError("Contact history flags must be Boolean")
    if previous_substep_loaded and not ever_loaded_before_current:
        raise ValueError("Previous loaded contact requires prior loaded history")
    if not contact_observed:
        if sensor_point_box_m is not None:
            raise ValueError("Zero-load manifold points cannot anchor a loaded-contact tube")
        phase = "recontact_pending" if ever_loaded_before_current else "approach"
        return ContactMaintenanceAssessment(phase, "abstain_no_loaded_anchor", None, None)
    phase = ("ongoing_contact" if previous_substep_loaded else
             "recontact" if ever_loaded_before_current else "first_contact")
    current = classify_loaded_front_contact_geometry(
        geometry,
        contact_observed=True,
        sensor_point_box_m=sensor_point_box_m,
        sensor_position_error_bound_m=sensor_position_error_bound_m,
        loaded_point_spread_bound_m=loaded_point_spread_bound_m,
    )
    if current.state != "inside_geometry_for_all_positions":
        return ContactMaintenanceAssessment(
            phase, current.state, current.nominal_margins_m, None,
        )
    if future_loaded_point_reach_bound_m is None:
        return ContactMaintenanceAssessment(
            phase, "abstain_missing_future_loaded_reach_bound",
            current.nominal_margins_m, None,
        )
    reach = float(future_loaded_point_reach_bound_m)
    if not math.isfinite(reach) or reach < 0:
        raise ValueError("Future loaded-point reach bound must be finite and nonnegative")
    radius = current.local_position_error_bound_m + reach
    if not math.isfinite(radius):
        raise ValueError("Combined future loaded-point radius must be finite")
    future = classify_front_contact_geometry(
        geometry,
        contact_observed=True,
        contact_point_box_m=sensor_point_box_m,
        local_position_error_bound_m=radius,
    )
    state = ("future_loaded_geometry_inside_under_bound"
             if future.state == "inside_geometry_for_all_positions"
             else "abstain_future_loaded_geometry_not_enclosed")
    return ContactMaintenanceAssessment(phase, state, future.nominal_margins_m, radius)
