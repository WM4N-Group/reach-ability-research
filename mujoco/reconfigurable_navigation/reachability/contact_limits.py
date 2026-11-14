"""Caller-declared contact limits and latched stop diagnostics, without execution permission."""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields

import numpy as np


@dataclass(frozen=True)
class ContactLimits:
    """Required declared limits in N, m/s, rad, and m; no deployment defaults."""
    maximum_normal_force: float
    maximum_tangential_force: float
    maximum_normal_speed: float
    maximum_tangential_speed: float
    maximum_orientation_error: float
    maximum_tip_distance: float

    def __post_init__(self):
        for field in fields(self):
            value = float(getattr(self, field.name))
            if not np.isfinite(value) or value < 0.0:
                raise ValueError("Contact limits must be finite and non-negative")
            object.__setattr__(self, field.name, value)


@dataclass(frozen=True)
class ContactLimitProvenance:
    """Traceability for caller-declared limits; never an execution approval."""

    source: str
    purpose: str
    calibration_status: str

    def __post_init__(self):
        for value, name in (
            (self.source, "source"),
            (self.purpose, "purpose"),
            (self.calibration_status, "calibration_status"),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Contact limit {name} must be a non-empty string")
        if self.calibration_status not in (
            "diagnostic_only", "simulation_calibrated", "hardware_calibrated"
        ):
            raise ValueError("Unknown contact limit calibration status")


@dataclass(frozen=True)
class ContactLimitDeclaration:
    """Limits plus provenance; this declaration still grants no execution permission."""

    limits: ContactLimits
    provenance: ContactLimitProvenance

    def __post_init__(self):
        if not isinstance(self.limits, ContactLimits):
            raise TypeError("limits must be ContactLimits")
        if not isinstance(self.provenance, ContactLimitProvenance):
            raise TypeError("provenance must be ContactLimitProvenance")


class ContactLimitMonitor:
    """Check declared bounds and retain STOP until an explicit fresh re-observation."""

    def __init__(
        self, limits: ContactLimits | ContactLimitDeclaration,
        provenance: ContactLimitProvenance | None = None,
    ):
        if isinstance(limits, ContactLimitDeclaration):
            if provenance is not None:
                raise ValueError("Do not provide provenance twice")
            self.limits = limits.limits
            self.provenance = limits.provenance
        elif isinstance(limits, ContactLimits):
            self.limits = limits
            self.provenance = provenance
        else:
            raise TypeError("limits must be ContactLimits or ContactLimitDeclaration")
        self.last_time = None
        self.stop_reasons = []

    def observe(
        self, samples, *, time: float, snapshot_valid: bool,
        support_valid: bool, nonhand_clearance_valid: bool,
    ) -> dict[str, object]:
        reasons = []
        if not np.isfinite(time) or (self.last_time is not None and time < self.last_time):
            reasons.append("invalid_observation_time")
        else:
            self.last_time = float(time)
        for valid, reason in (
            (snapshot_valid, "invalid_box_snapshot"),
            (support_valid, "invalid_support"),
            (nonhand_clearance_valid, "invalid_nonhand_clearance"),
        ):
            if not bool(valid):
                reasons.append(reason)
        total_normal_force = 0.0
        total_tangential_force = 0.0
        for sample in samples:
            names = (
                "normal_force", "tangential_force", "normal_speed", "tangential_speed",
                "orientation_error", "tip_distance",
            )
            if not sample.get("measurement_valid", False) or any(name not in sample for name in names):
                reasons.append("invalid_contact_measurement")
                continue
            values = np.asarray([sample[name] for name in names], dtype=np.float64)
            if not np.isfinite(values).all() or np.any(values[[1, 3, 4, 5]] < 0.0):
                reasons.append("invalid_contact_measurement")
                continue
            if not sample.get("region_matched", False):
                reasons.append("contact_outside_designated_region")
            if sample["normal_force"] < 0.0:
                reasons.append("outward_normal_force")
            total_normal_force += max(0.0, sample["normal_force"])
            total_tangential_force += sample["tangential_force"]
            for measured, allowed, reason in (
                (abs(sample["normal_speed"]), self.limits.maximum_normal_speed, "normal_speed_exceeded"),
                (sample["tangential_speed"], self.limits.maximum_tangential_speed, "tangential_speed_exceeded"),
                (sample["orientation_error"], self.limits.maximum_orientation_error, "orientation_error_exceeded"),
                (sample["tip_distance"], self.limits.maximum_tip_distance, "contact_too_far_from_native_hand"),
            ):
                if measured > allowed:
                    reasons.append(reason)
        if total_normal_force > self.limits.maximum_normal_force:
            reasons.append("normal_force_exceeded")
        if total_tangential_force > self.limits.maximum_tangential_force:
            reasons.append("tangential_force_exceeded")
        if reasons:
            self.stop_reasons = list(dict.fromkeys([*self.stop_reasons, *reasons]))
        stopped = bool(self.stop_reasons)
        return {
            "state": "stop_reobserve" if stopped else "within_declared_limits" if samples else "await_contact",
            "within_declared_limits": False if stopped else True if samples else None,
            "stop_reasons": self.stop_reasons.copy(),
            "reobserve_required": stopped,
            "total_normal_force": total_normal_force,
            "total_tangential_force": total_tangential_force,
            "limits": asdict(self.limits),
            "limits_provenance": (
                asdict(self.provenance) if self.provenance is not None else None
            ),
            "contact_execution_enabled": False,
            "scope": "Caller-declared diagnostic limits only; not calibrated force control or skill approval",
        }

    def reset_after_reobservation(self, *, time: float, snapshot_valid: bool) -> None:
        if (
            not snapshot_valid or not np.isfinite(time)
            or (self.last_time is not None and time <= self.last_time)
        ):
            raise ValueError("Reset requires a fresh valid snapshot")
        self.last_time = float(time)
        self.stop_reasons.clear()


class ContactHandoffGuard:
    """Fail-closed precontact handoff gate; never grants execution permission."""

    def __init__(self, limits: ContactLimits):
        self.monitor = ContactLimitMonitor(limits)
        self.stop_reasons = []

    def check_precontact(
        self, *, time: float, snapshot_valid: bool, support_valid: bool,
        nonhand_clearance_valid: bool, designated_face_ready: bool,
        native_orientation_valid: bool, contact_free: bool,
    ) -> dict[str, object]:
        assessment = self.monitor.observe(
            [], time=time, snapshot_valid=snapshot_valid,
            support_valid=support_valid,
            nonhand_clearance_valid=nonhand_clearance_valid,
        )
        reasons = list(assessment["stop_reasons"])
        for valid, reason in (
            (designated_face_ready, "invalid_designated_contact_face"),
            (native_orientation_valid, "invalid_native_hand_orientation"),
            (contact_free, "unexpected_precontact_contact"),
        ):
            if not bool(valid):
                reasons.append(reason)
        self.stop_reasons = list(dict.fromkeys([*self.stop_reasons, *reasons]))
        stopped = bool(self.stop_reasons)
        return {
            "state": "stop_reobserve" if stopped else "ready_for_contact",
            "ready_for_contact": not stopped,
            "within_declared_limits": None if not stopped else False,
            "stop_reasons": self.stop_reasons.copy(),
            "reobserve_required": stopped,
            "contact_execution_enabled": False,
            "limits": assessment["limits"],
            "limits_provenance": assessment["limits_provenance"],
            "scope": (
                "Precontact handoff prerequisites only; caller-declared diagnostic limits; "
                "not calibrated force control or skill approval"
            ),
        }

    def observe_contact(self, samples, **conditions) -> dict[str, object]:
        """Evaluate contact samples after handoff while preserving any latched stop."""
        assessment = self.monitor.observe(samples, **conditions)
        self.stop_reasons = list(dict.fromkeys([
            *self.stop_reasons, *assessment["stop_reasons"]
        ]))
        assessment["stop_reasons"] = self.stop_reasons.copy()
        assessment["state"] = (
            "stop_reobserve" if self.stop_reasons else assessment["state"]
        )
        assessment["within_declared_limits"] = (
            False if self.stop_reasons else assessment["within_declared_limits"]
        )
        return assessment

    def reset_after_reobservation(
        self, *, time: float, snapshot_valid: bool, support_valid: bool,
        nonhand_clearance_valid: bool, designated_face_ready: bool,
        native_orientation_valid: bool, contact_free: bool,
    ) -> None:
        if not all((
            snapshot_valid, support_valid, nonhand_clearance_valid,
            designated_face_ready, native_orientation_valid, contact_free,
        )):
            raise ValueError("Reset requires valid fresh handoff observations")
        self.monitor.reset_after_reobservation(
            time=time, snapshot_valid=snapshot_valid,
        )
        self.stop_reasons.clear()